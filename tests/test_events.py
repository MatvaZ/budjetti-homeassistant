"""Koordinaattorin tapahtumat automaatioille: budjetin raja (80/100 %) ja iso kulu."""
import pytest
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.budjetti.const import (
    CONF_LARGE_EXPENSE,
    DOMAIN,
    EVENT_BUDGET_THRESHOLD,
    EVENT_LARGE_EXPENSE,
    TOTAL_BUDGET,
)

from .conftest import MONTH, tx


@pytest.fixture
def thresholds(hass):
    return async_capture_events(hass, EVENT_BUDGET_THRESHOLD)


@pytest.fixture
def large(hass):
    return async_capture_events(hass, EVENT_LARGE_EXPENSE)


def _spend(fake, category: str, cents: int, budget: int | None = ...) -> None:
    for row in fake.summary["categories"]:
        if row["category"] == category:
            row["spent_cents"] = cents
            if budget is not ...:
                row["budget_cents"] = budget


async def _refresh(hass, entry):
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()


async def test_first_run_is_silent_and_saves_state(hass, entry, fake, thresholds, large, hass_storage):
    """Asennuksen jälkeen vanhoista kirjauksista ja jo ylittyneistä budjeteista ei ilmoiteta."""
    _spend(fake, "Ruoka", 50000)  # 125 %
    fake.transactions = [tx(1, 99999)]
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert thresholds == [] and large == []
    await hass.async_block_till_done()
    stored = hass_storage[f"{DOMAIN}.{entry.entry_id}"]["data"]
    assert stored == {"month": MONTH, "levels": {"Ruoka": 100, TOTAL_BUDGET: 0}, "last_tx": 1}


async def test_threshold_80_then_100_once_each(hass, setup, fake, thresholds):
    _spend(fake, "Ruoka", 32000)  # 80 %
    await _refresh(hass, setup)
    assert [e.data for e in thresholds] == [{
        "category": "Ruoka", "threshold": 80, "percent": 80, "spent": 320.0, "budget": 400.0, "month": MONTH,
    }]
    await _refresh(hass, setup)
    assert len(thresholds) == 1  # sama raja vain kerran

    _spend(fake, "Ruoka", 42000)
    await _refresh(hass, setup)
    assert [(e.data["threshold"], e.data["percent"]) for e in thresholds] == [(80, 80), (100, 105)]


async def test_jump_straight_over_100_fires_only_100(hass, setup, fake, thresholds):
    _spend(fake, "Ruoka", 45000)
    await _refresh(hass, setup)
    assert [e.data["threshold"] for e in thresholds] == [100]


async def test_total_budget_category(hass, setup, fake, thresholds):
    fake.summary["expense_cents"] = 85000  # kokonaisbudjetti 1000 €
    await _refresh(hass, setup)
    assert [(e.data["category"], e.data["threshold"]) for e in thresholds] == [(TOTAL_BUDGET, 80)]


async def test_drop_below_allows_new_event(hass, setup, fake, thresholds):
    _spend(fake, "Ruoka", 33000)
    await _refresh(hass, setup)
    _spend(fake, "Ruoka", 10000)  # esim. kirjaus poistettiin
    await _refresh(hass, setup)
    _spend(fake, "Ruoka", 33000)
    await _refresh(hass, setup)
    assert [e.data["threshold"] for e in thresholds] == [80, 80]


async def test_budget_removed_resets_level(hass, setup, fake, thresholds):
    _spend(fake, "Ruoka", 33000)
    await _refresh(hass, setup)
    _spend(fake, "Ruoka", 33000, budget=None)
    await _refresh(hass, setup)
    _spend(fake, "Ruoka", 33000, budget=40000)
    await _refresh(hass, setup)
    assert [e.data["threshold"] for e in thresholds] == [80, 80]


async def test_new_month_resets_levels(hass, setup, fake, thresholds, freezer):
    _spend(fake, "Ruoka", 33000)
    await _refresh(hass, setup)
    freezer.move_to("2026-12-02 12:00:00")
    await _refresh(hass, setup)
    assert [(e.data["threshold"], e.data["month"]) for e in thresholds] == [(80, MONTH), (80, "2026-12")]


@pytest.mark.parametrize(("spent", "expected"), [
    (31800, []),          # 79,5 %: pyöristyy 80:een, mutta raja ei vielä täyty
    (31999, []),
    (32000, [80]),        # tasan 80 %
    (39800, [80]),        # 99,5 %: pyöristyy 100:aan, mutta budjetti ei ylity
    (39999, [80]),
    (40000, [100]),       # tasan budjetti (80 % ohitetaan, kun hypätään suoraan yli)
])
async def test_threshold_boundaries(hass, setup, fake, thresholds, spent, expected):
    """Raja täyttyy vasta, kun käyttö on oikeasti vähintään 80 % / 100 % (ei pyöristettynä)."""
    _spend(fake, "Ruoka", 31000)
    await _refresh(hass, setup)
    _spend(fake, "Ruoka", spent)
    await _refresh(hass, setup)
    assert [e.data["threshold"] for e in thresholds] == expected


async def test_large_expense(hass, setup, fake, large):
    fake.transactions += [
        tx(3, 9999),                          # alle rajan
        tx(4, 10000, recurring_id=12),        # tasan 100 €, toistuva
        tx(5, 50000, type_="income"),         # tulo ei ole kulu
        tx(6, -20000),                        # hyvitys
    ]
    await _refresh(hass, setup)
    assert [e.data for e in large] == [{
        "id": 4, "amount": 100.0, "category": "Ruoka", "note": "tx4", "date": f"{MONTH}-05", "recurring": True,
    }]
    await _refresh(hass, setup)
    assert len(large) == 1  # ei toistu


async def test_large_expense_custom_limit_and_off(hass, setup, fake, large):
    hass.config_entries.async_update_entry(setup, options={CONF_LARGE_EXPENSE: 20.0})
    fake.transactions.append(tx(3, 2000))
    await _refresh(hass, setup)
    assert [e.data["id"] for e in large] == [3]

    hass.config_entries.async_update_entry(setup, options={CONF_LARGE_EXPENSE: 0})
    fake.transactions.append(tx(4, 1_000_000))
    await _refresh(hass, setup)
    assert [e.data["id"] for e in large] == [3]


async def test_restart_does_not_repeat_events(hass, entry, fake, thresholds, large, hass_storage):
    hass_storage[f"{DOMAIN}.{entry.entry_id}"] = {
        "version": 1, "key": f"{DOMAIN}.{entry.entry_id}",
        "data": {"month": MONTH, "levels": {"Ruoka": 80}, "last_tx": 2},
    }
    _spend(fake, "Ruoka", 33000)
    fake.transactions.append(tx(3, 30000))
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert thresholds == []          # 80 % oli jo ilmoitettu
    assert [e.data["id"] for e in large] == [3]  # uusi kirjaus käynnistysten välissä ilmoitetaan
