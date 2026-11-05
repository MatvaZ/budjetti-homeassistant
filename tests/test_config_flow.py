"""Asetus käyttöliittymästä, uusi API-avain (reauth) ja ison kulun raja (options)."""
from http import HTTPStatus

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.budjetti.const import CONF_API_KEY, CONF_LARGE_EXPENSE, CONF_URL, DOMAIN

from .conftest import API_KEY, URL


async def _start(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return result


async def test_user_flow_creates_entry(hass, fake):
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: f"  {URL}/ ", CONF_API_KEY: API_KEY}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Budjetti (matias)"
    assert result["data"] == {CONF_URL: URL, CONF_API_KEY: API_KEY}  # välilyönnit ja / poistettu
    assert result["result"].unique_id == f"{URL}#7"
    await hass.async_block_till_done()


async def test_title_falls_back_to_email(hass, fake):
    fake.me = {"id": 7, "username": None, "email": "m@example.com"}
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_API_KEY: API_KEY})
    assert result["title"] == "Budjetti (m@example.com)"
    await hass.async_block_till_done()


async def test_invalid_auth(hass, fake):
    fake.errors["/api/auth/me"] = HTTPStatus.UNAUTHORIZED
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_API_KEY: "x"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_cannot_connect_then_recover(hass, fake):
    fake.errors["/api/auth/me"] = HTTPStatus.BAD_GATEWAY
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_API_KEY: API_KEY})
    assert result["errors"] == {"base": "cannot_connect"}
    fake.errors.clear()
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_API_KEY: API_KEY})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_already_configured(hass, fake, entry):
    entry.add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_API_KEY: API_KEY})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    await hass.async_block_till_done()  # ei jää taustatehtäviä testin jälkeen


async def test_reauth_updates_key(hass, setup, fake):
    result = await setup.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"

    fake.errors["/api/auth/me"] = HTTPStatus.UNAUTHORIZED
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "huono"})
    assert result["errors"] == {"base": "invalid_auth"}

    fake.errors.clear()
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_API_KEY: "uusi"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert setup.data == {CONF_URL: URL, CONF_API_KEY: "uusi"}
    await hass.async_block_till_done()


async def test_options_flow(hass, setup):
    result = await hass.config_entries.options.async_init(setup.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_LARGE_EXPENSE: "250"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup.options == {CONF_LARGE_EXPENSE: 250.0}
