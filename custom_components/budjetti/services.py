"""Palvelut automaatioihin ja skripteihin (summat euroina)."""
from __future__ import annotations

from datetime import date

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
import homeassistant.helpers.config_validation as cv

from .api import BudjettiError, current_month
from .const import DOMAIN
from .coordinator import BudjettiCoordinator

ENTRY = vol.Optional("config_entry_id")

ADD_SCHEMA = vol.Schema({
    ENTRY: cv.string,
    vol.Required("amount"): vol.Coerce(float),
    vol.Required("category"): cv.string,
    vol.Optional("note", default=""): cv.string,
    vol.Optional("date"): cv.date,
    vol.Optional("type", default="expense"): vol.In(["expense", "income", "refund"]),
})
BUDGET_SCHEMA = vol.Schema({
    ENTRY: cv.string,
    vol.Required("category"): cv.string,
    vol.Required("amount"): vol.All(vol.Coerce(float), vol.Range(min=0)),
    vol.Optional("month"): vol.Match(r"^\d{4}-\d{2}$"),
    vol.Optional("only_this_month", default=False): cv.boolean,
})
DELETE_SCHEMA = vol.Schema({ENTRY: cv.string, vol.Required("id"): vol.Coerce(int)})


def _coordinator(hass: HomeAssistant, call: ServiceCall) -> BudjettiCoordinator:
    wanted = call.data.get("config_entry_id")
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED and wanted in (None, entry.entry_id):
            return entry.runtime_data
    raise ServiceValidationError("Budjetti-integraatiota ei löytynyt")


@callback
def async_register(hass: HomeAssistant) -> None:
    async def add_transaction(call: ServiceCall) -> ServiceResponse:
        coordinator = _coordinator(hass, call)
        cents = round(abs(call.data["amount"]) * 100)
        if cents == 0:
            raise ServiceValidationError("Summa ei voi olla nolla")
        kind = call.data["type"]
        data = {
            "date": (call.data.get("date") or date.today()).isoformat(),
            "amount_cents": -cents if kind == "refund" else cents,  # hyvitys = negatiivinen meno
            "type": "income" if kind == "income" else "expense",
            "category": call.data["category"],
            "note": call.data["note"],
        }
        try:
            tx = await coordinator.client.add_transaction(data)
        except BudjettiError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_refresh()  # heti, ei 10 s viiveellä
        return {"transaction": tx}

    async def set_budget(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call)
        try:
            await coordinator.client.set_budget(
                call.data["category"], call.data.get("month") or current_month(),
                round(call.data["amount"] * 100), call.data["only_this_month"],
            )
        except BudjettiError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_refresh()  # heti, ei 10 s viiveellä

    async def delete_transaction(call: ServiceCall) -> None:
        coordinator = _coordinator(hass, call)
        try:
            await coordinator.client.delete_transaction(call.data["id"])
        except BudjettiError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_refresh()  # heti, ei 10 s viiveellä

    hass.services.async_register(
        DOMAIN, "add_transaction", add_transaction, schema=ADD_SCHEMA, supports_response=SupportsResponse.OPTIONAL
    )
    hass.services.async_register(DOMAIN, "set_budget", set_budget, schema=BUDGET_SCHEMA)
    hass.services.async_register(DOMAIN, "delete_transaction", delete_transaction, schema=DELETE_SCHEMA)
