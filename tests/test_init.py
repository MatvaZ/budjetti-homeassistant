"""Asennus, poisto, virhetilanteet asennuksessa ja Budjetin versiovaatimus."""
from http import HTTPStatus

from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN

from custom_components.budjetti.const import CARD_URL


async def test_setup_and_unload(hass, setup):
    assert setup.state is ConfigEntryState.LOADED
    assert hass.states.get("sensor.budjetti_expenses_this_month") is not None
    assert await hass.config_entries.async_unload(setup.entry_id)
    assert setup.state is ConfigEntryState.NOT_LOADED


async def test_card_js_registered(hass, setup):
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL

    urls = hass.data[DATA_EXTRA_MODULE_URL].urls
    assert any(u.startswith(f"{CARD_URL}?v=") for u in urls)


async def test_backend_down_retries(hass, entry, fake):
    fake.errors["/api/summary"] = HTTPStatus.BAD_GATEWAY
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_revoked_key_starts_reauth(hass, entry, fake):
    fake.errors["/api/summary"] = HTTPStatus.UNAUTHORIZED
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == [SOURCE_REAUTH]


async def test_old_backend_without_upcoming(hass, entry, fake):
    """Budjetti < 0.4.0 (ei /api/recurring/upcoming): integraatio toimii, Seuraava maksu on tuntematon."""
    fake.version = "0.3.0"
    fake.errors["/api/recurring/upcoming"] = HTTPStatus.NOT_FOUND
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    state = hass.states.get("sensor.budjetti_next_payment")
    assert state.state == STATE_UNKNOWN
    assert state.attributes["upcoming_this_month"] == 0
    assert state.attributes["net_after_upcoming"] is None
    assert hass.states.get("sensor.budjetti_expenses_this_month").state == "500.0"


async def test_update_failure_makes_sensors_unavailable(hass, setup, fake):
    coordinator = setup.runtime_data
    fake.errors["/api/summary"] = HTTPStatus.BAD_GATEWAY
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.budjetti_expenses_this_month").state == STATE_UNAVAILABLE
    fake.errors.clear()
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get("sensor.budjetti_expenses_this_month").state == "500.0"
