"""Websocket-komennot budjettikortille. Kortti puhuu vain Home Assistantille, joten se toimii
myös etänä (Zima Client, Nabu Casa) ilman suoraa yhteyttä budjettiin."""
from __future__ import annotations

import base64
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from .api import BudjettiError, current_month
from .const import DOMAIN
from .coordinator import BudjettiCoordinator

MONTH = vol.Match(r"^\d{4}-\d{2}$")
DATE = vol.Match(r"^\d{4}-\d{2}-\d{2}$")
MAX_IMAGE_B64 = 14 * 1024 * 1024  # ~10 Mt kuva


def _coordinator(hass: HomeAssistant, entry_id: str | None) -> BudjettiCoordinator:
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
    for entry in entries:
        if entry_id in (None, entry.entry_id):
            return entry.runtime_data
    raise BudjettiError("Budjetti-integraatiota ei löytynyt")


def _image(msg: dict) -> tuple[bytes, str] | None:
    if not msg.get("image"):
        return None
    if len(msg["image"]) > MAX_IMAGE_B64:
        raise BudjettiError("Kuva on liian suuri")
    return base64.b64decode(msg["image"]), msg.get("media_type") or "image/jpeg"


def _handler(schema: dict):
    """Yhteinen kääre: entry_id-valinta, virheet ja asynkroninen vastaus."""

    def decorate(func):
        @websocket_api.websocket_command({**schema, vol.Optional("entry_id"): str})
        @websocket_api.async_response
        async def wrapper(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict) -> None:
            try:
                coordinator = _coordinator(hass, msg.get("entry_id"))
                connection.send_result(msg["id"], await func(hass, coordinator, msg))
            except BudjettiError as err:
                connection.send_error(msg["id"], "budjetti_error", str(err))

        return wrapper

    return decorate


@_handler({vol.Required("type"): "budjetti/month", vol.Optional("month"): MONTH})
async def ws_month(hass, coordinator: BudjettiCoordinator, msg) -> dict:
    month = msg.get("month") or current_month()
    c = coordinator.client
    return {
        "month": month,
        "summary": await c.summary(month),
        "transactions": await c.transactions(month),
        "categories": await c.categories(),
        "budgets": await c.budgets(month),
        "upcoming": await c.upcoming(month),
    }


TX_SCHEMA = {
    vol.Optional("tx_id"): int,
    vol.Required("date"): DATE,
    vol.Required("amount_cents"): int,
    vol.Required("tx_type"): vol.In(["expense", "income"]),
    vol.Required("category"): str,
    vol.Optional("note", default=""): str,
    vol.Optional("items"): [dict],
    vol.Optional("image"): str,
    vol.Optional("media_type"): str,
}


@_handler({vol.Required("type"): "budjetti/save", **TX_SCHEMA})
async def ws_save(hass, coordinator: BudjettiCoordinator, msg) -> dict:
    """Lisää tai muokkaa tapahtumaa; kuitin tuoterivit ja kuva liitetään samalla."""
    c = coordinator.client
    data = {k: msg[k] for k in ("date", "amount_cents", "category", "note")}
    data["type"] = msg["tx_type"]
    tx = await (c.update_transaction(msg["tx_id"], data) if msg.get("tx_id") else c.add_transaction(data))
    if msg.get("items"):
        items = [
            {"name": str(i.get("name") or "?"), "price_cents": i.get("price_cents"),
             "item_category": i.get("item_category")}
            for i in msg["items"]
        ]
        await c.set_items(tx["id"], items)
    image = _image(msg)
    if image:
        await c.upload_receipt(tx["id"], *image)
    await coordinator.async_refresh()  # heti, ei 10 s viiveellä
    return tx


@_handler({vol.Required("type"): "budjetti/delete", vol.Required("tx_id"): int})
async def ws_delete(hass, coordinator: BudjettiCoordinator, msg) -> dict:
    await coordinator.client.delete_transaction(msg["tx_id"])
    await coordinator.async_refresh()  # heti, ei 10 s viiveellä
    return {}


@_handler({
    vol.Required("type"): "budjetti/set_budget",
    vol.Required("category"): str,
    vol.Required("amount_cents"): vol.All(int, vol.Range(min=0)),
    vol.Optional("month"): MONTH,
    vol.Optional("only", default=False): bool,
})
async def ws_set_budget(hass, coordinator: BudjettiCoordinator, msg) -> dict:
    res = await coordinator.client.set_budget(
        msg["category"], msg.get("month") or current_month(), msg["amount_cents"], msg["only"]
    )
    await coordinator.async_refresh()  # heti, ei 10 s viiveellä
    return res


@_handler({vol.Required("type"): "budjetti/scan", vol.Required("image"): str, vol.Optional("media_type"): str})
async def ws_scan(hass, coordinator: BudjettiCoordinator, msg) -> dict:
    """Kuitti luettavaksi (budjetin kautta): palauttaa esitäytön, ei tallenna mitään."""
    image, media_type = _image(msg)
    return await coordinator.client.scan_receipt(image, media_type)


@_handler({vol.Required("type"): "budjetti/receipt", vol.Required("tx_id"): int})
async def ws_receipt(hass, coordinator: BudjettiCoordinator, msg) -> dict:
    c = coordinator.client
    items = await c.items(msg["tx_id"])
    try:
        image = base64.b64encode(await c.receipt(msg["tx_id"])).decode("ascii")
    except BudjettiError:
        image = None  # kuittia ei ole kuvana (esim. vanhat botin kuitit)
    return {"items": items, "image": image}


@callback
def async_register(hass: HomeAssistant) -> None:
    for command in (ws_month, ws_save, ws_delete, ws_set_budget, ws_scan, ws_receipt):
        websocket_api.async_register_command(hass, command)
