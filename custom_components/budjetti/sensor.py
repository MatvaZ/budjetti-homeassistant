"""Anturit: kuukauden menot, tulot, saldo, kokonaisbudjetti, ennuste ja kategoriat."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BudjettiConfigEntry, BudjettiCoordinator, BudjettiData


def _eur(cents: int | None) -> float | None:
    return None if cents is None else round(cents / 100, 2)


def _pct(spent: int, budget: int | None) -> int | None:
    return round(spent * 100 / budget) if budget else None


@dataclass(frozen=True, kw_only=True)
class BudjettiSensorDescription(SensorEntityDescription):
    value: Callable[[BudjettiData], float | None]
    attrs: Callable[[BudjettiData], dict] = lambda d: {}


SENSORS = (
    BudjettiSensorDescription(
        key="expenses", translation_key="expenses",
        value=lambda d: _eur(d.summary["expense_cents"]),
    ),
    BudjettiSensorDescription(
        key="income", translation_key="income",
        value=lambda d: _eur(d.summary["income_cents"]),
    ),
    BudjettiSensorDescription(
        key="net", translation_key="net",
        value=lambda d: _eur(d.summary["net_cents"]),
    ),
    BudjettiSensorDescription(
        key="total_left", translation_key="total_left",
        value=lambda d: _eur(
            None if d.summary.get("total_budget_cents") is None
            else d.summary["total_budget_cents"] - d.summary["expense_cents"]
        ),
        attrs=lambda d: {
            "budget": _eur(d.summary.get("total_budget_cents")),
            "percent": _pct(d.summary["expense_cents"], d.summary.get("total_budget_cents")),
        },
    ),
    BudjettiSensorDescription(
        key="forecast", translation_key="forecast",
        value=lambda d: _eur(d.overview["forecast"]["projected_expense_cents"]),
        attrs=lambda d: {"projected_net": _eur(d.overview["forecast"]["projected_net_cents"])},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: BudjettiConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(BudjettiSensor(coordinator, desc) for desc in SENSORS)

    # Kategorioiden anturit: uudet lisätään, kun ne ilmestyvät budjettiin.
    known: set[str] = set()

    @callback
    def _add_categories() -> None:
        new = [
            c["category"] for c in coordinator.data.summary["categories"] if c["category"] not in known
        ]
        if new:
            known.update(new)
            async_add_entities(CategorySensor(coordinator, cat) for cat in new)

    _add_categories()
    entry.async_on_unload(coordinator.async_add_listener(_add_categories))


class _Base(CoordinatorEntity[BudjettiCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "EUR"
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: BudjettiCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Budjetti",  # anturit: sensor.budjetti_ruoka, sensor.budjetti_menot_tassa_kuussa ...
            manufacturer="Budjetti",
            sw_version=coordinator.data.version,
            configuration_url=entry.data["url"],
        )


class BudjettiSensor(_Base):
    entity_description: BudjettiSensorDescription

    def __init__(self, coordinator: BudjettiCoordinator, description: BudjettiSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict:
        return {"month": self.coordinator.data.month, **self.entity_description.attrs(self.coordinator.data)}


class CategorySensor(_Base):
    """Kategorian käyttö tässä kuussa; budjetti ja käyttöaste attribuutteina."""

    _attr_translation_key = "category"

    def __init__(self, coordinator: BudjettiCoordinator, category: str) -> None:
        super().__init__(coordinator, f"category_{category.lower()}")
        self.category = category
        self._attr_translation_placeholders = {"category": category}

    def _row(self) -> dict:
        return next(
            (c for c in self.coordinator.data.summary["categories"] if c["category"] == self.category),
            {"spent_cents": 0, "budget_cents": None},
        )

    @property
    def native_value(self) -> float | None:
        return _eur(self._row()["spent_cents"])

    @property
    def extra_state_attributes(self) -> dict:
        row = self._row()
        budget = row.get("budget_cents")
        return {
            "month": self.coordinator.data.month,
            "category": self.category,
            "budget": _eur(budget),
            "remaining": _eur(budget - row["spent_cents"]) if budget else None,
            "percent": _pct(row["spent_cents"], budget),
        }
