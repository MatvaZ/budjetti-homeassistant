"""Kuluvan kuukauden tilanne minuutin välein antureita varten. Lisäksi tapahtumat automaatioille:
budjetin raja ylittyi tai kirjattiin iso kulu."""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BudjettiAuthError, BudjettiClient, BudjettiError, current_month
from .const import (
    BUDGET_THRESHOLDS,
    CONF_LARGE_EXPENSE,
    DEFAULT_LARGE_EXPENSE,
    DOMAIN,
    EVENT_BUDGET_THRESHOLD,
    EVENT_LARGE_EXPENSE,
    TOTAL_BUDGET,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class BudjettiData:
    month: str
    summary: dict
    overview: dict
    version: str
    upcoming: dict


class BudjettiCoordinator(DataUpdateCoordinator[BudjettiData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: BudjettiClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.client = client
        # Muistissa pysyy, mistä on jo ilmoitettu, ettei uudelleenkäynnistys toista tapahtumia.
        self._store: Store[dict] = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._state: dict | None = None

    async def _async_update_data(self) -> BudjettiData:
        month = current_month()
        try:
            summary = await self.client.summary(month)
            overview = await self.client.overview(month)
            health = await self.client.health()
            upcoming = await self.client.upcoming(month)
            transactions = await self.client.transactions(month)
        except BudjettiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except BudjettiError as err:
            raise UpdateFailed(str(err)) from err
        await self._fire_events(month, summary, transactions)
        return BudjettiData(month, summary, overview, health.get("version", "?"), upcoming)

    async def _fire_events(self, month: str, summary: dict, transactions: list[dict]) -> None:
        if self._state is None:
            self._state = await self._store.async_load()
        first_run = self._state is None  # vanhoista kirjauksista ei ilmoiteta asennuksen jälkeen
        state = self._state or {"month": month, "levels": {}, "last_tx": 0}
        before = json.dumps(state, sort_keys=True)
        if state["month"] != month:
            state.update(month=month, levels={})

        rows = [(c["category"], c["spent_cents"], c.get("budget_cents")) for c in summary["categories"]]
        rows.append((TOTAL_BUDGET, summary["expense_cents"], summary.get("total_budget_cents")))
        for category, spent, budget in rows:
            if not budget:
                state["levels"].pop(category, None)
                continue
            percent = round(spent * 100 / budget)
            level = max((t for t in BUDGET_THRESHOLDS if percent >= t), default=0)
            if level > state["levels"].get(category, 0) and not first_run:
                self.hass.bus.async_fire(EVENT_BUDGET_THRESHOLD, {
                    "category": category, "threshold": level, "percent": percent,
                    "spent": round(spent / 100, 2), "budget": round(budget / 100, 2), "month": month,
                })
            state["levels"][category] = level  # lasku (esim. poisto) sallii uuden ilmoituksen

        limit = self.config_entry.options.get(CONF_LARGE_EXPENSE, DEFAULT_LARGE_EXPENSE) * 100
        for tx in sorted(transactions, key=lambda t: t["id"]):
            if tx["id"] <= state["last_tx"]:
                continue
            state["last_tx"] = tx["id"]
            if not first_run and limit > 0 and tx["type"] == "expense" and tx["amount_cents"] >= limit:
                self.hass.bus.async_fire(EVENT_LARGE_EXPENSE, {
                    "id": tx["id"], "amount": round(tx["amount_cents"] / 100, 2), "category": tx["category"],
                    "note": tx["note"], "date": tx["date"], "recurring": tx.get("recurring_id") is not None,
                })

        self._state = state
        if json.dumps(state, sort_keys=True) != before or first_run:
            await self._store.async_save(state)


type BudjettiConfigEntry = ConfigEntry[BudjettiCoordinator]
