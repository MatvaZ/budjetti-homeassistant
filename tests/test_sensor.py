"""Anturien arvot ja attribuutit."""
from homeassistant.const import STATE_UNKNOWN
from homeassistant.helpers import device_registry as dr, entity_registry as er

from custom_components.budjetti.const import DOMAIN

from .conftest import MONTH, URL


def _state(hass, name):
    state = hass.states.get(f"sensor.budjetti_{name}")
    assert state is not None, name
    return state


async def test_summary_sensors(hass, setup):
    assert _state(hass, "expenses_this_month").state == "500.0"
    assert _state(hass, "income_this_month").state == "2000.0"
    net = _state(hass, "net_this_month")
    assert net.state == "1500.0"
    assert net.attributes["month"] == MONTH
    assert net.attributes["unit_of_measurement"] == "EUR"
    assert net.attributes["device_class"] == "monetary"


async def test_total_left_and_forecast(hass, setup):
    left = _state(hass, "total_budget_left")
    assert left.state == "500.0"
    assert left.attributes["budget"] == 1000.0
    assert left.attributes["percent"] == 50
    forecast = _state(hass, "expense_forecast_for_the_month")
    assert forecast.state == "900.0"
    assert forecast.attributes["projected_net"] == 1100.0


async def test_total_left_without_total_budget(hass, entry, fake):
    fake.summary["total_budget_cents"] = None
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    left = _state(hass, "total_budget_left")
    assert left.state == STATE_UNKNOWN
    assert left.attributes["budget"] is None
    assert left.attributes["percent"] is None


async def test_next_payment(hass, setup):
    nxt = _state(hass, "next_payment")
    assert nxt.state == "700.0"
    assert nxt.attributes["name"] == "Vuokra"
    assert nxt.attributes["date"] == f"{MONTH}-20"
    assert nxt.attributes["payment_category"] == "Asuminen"
    assert nxt.attributes["upcoming_this_month"] == 700.0
    assert nxt.attributes["net_after_upcoming"] == 800.0


async def test_category_sensors(hass, setup):
    food = _state(hass, "ruoka")
    assert food.state == "300.0"
    assert food.attributes["category"] == "Ruoka"
    assert food.attributes["budget"] == 400.0
    assert food.attributes["remaining"] == 100.0
    assert food.attributes["percent"] == 75
    traffic = _state(hass, "liikenne")
    assert traffic.state == "200.0"
    assert traffic.attributes["budget"] is None
    assert traffic.attributes["remaining"] is None
    assert traffic.attributes["percent"] is None


async def test_new_category_added_and_removed_category_zero(hass, setup, fake):
    fake.summary["categories"] = [{"category": "Harrastukset", "spent_cents": 1234, "budget_cents": 5000}]
    await setup.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert _state(hass, "harrastukset").state == "12.34"
    assert _state(hass, "ruoka").state == "0.0"  # poistunut kategoria jää nollaan


async def test_unique_ids_and_device(hass, setup, fake):
    ent_reg = er.async_get(hass)
    ids = {e.unique_id for e in er.async_entries_for_config_entry(ent_reg, setup.entry_id)}
    eid = setup.entry_id
    assert {f"{eid}_expenses", f"{eid}_income", f"{eid}_net", f"{eid}_total_left", f"{eid}_forecast",
            f"{eid}_next_payment", f"{eid}_category_ruoka", f"{eid}_category_liikenne"} == ids
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, eid)})
    assert device.sw_version == fake.version
    assert device.configuration_url == URL
