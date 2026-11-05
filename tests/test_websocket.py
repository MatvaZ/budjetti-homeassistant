"""Budjettikortin websocket-komennot."""
import base64
from http import HTTPStatus

import pytest

from .conftest import MONTH


@pytest.fixture
async def ws(hass, setup, hass_ws_client):
    return await hass_ws_client(hass)


async def _cmd(ws, **msg):
    await ws.send_json_auto_id(msg)
    return await ws.receive_json()


async def test_month(ws, fake):
    res = await _cmd(ws, type="budjetti/month")
    assert res["success"]
    data = res["result"]
    assert data["month"] == MONTH
    assert data["summary"]["expense_cents"] == 50000
    assert data["upcoming"]["next"]["name"] == "Vuokra"
    assert {"transactions", "categories", "budgets"} <= data.keys()


async def test_month_old_backend_has_empty_upcoming(ws, fake):
    fake.errors["/api/recurring/upcoming"] = HTTPStatus.NOT_FOUND
    res = await _cmd(ws, type="budjetti/month", month="2026-10")
    assert res["success"]
    assert res["result"]["upcoming"]["items"] == []


async def test_save_new_with_items_and_image(ws, fake):
    image = base64.b64encode(b"kuva").decode()
    res = await _cmd(ws, type="budjetti/save", date=f"{MONTH}-03", amount_cents=1290, tx_type="expense",
                     category="Ruoka", note="Lidl", items=[{"name": "Maito", "price_cents": 129}, {}],
                     image=image, media_type="image/png")
    assert res["success"]
    assert fake.calls("POST", "/api/transactions") == [
        {"date": f"{MONTH}-03", "amount_cents": 1290, "category": "Ruoka", "note": "Lidl", "type": "expense"}
    ]
    assert fake.calls("PUT", "/api/transactions/100/items") == [[
        {"name": "Maito", "price_cents": 129, "item_category": None},
        {"name": "?", "price_cents": None, "item_category": None},
    ]]
    assert len(fake.calls("PUT", "/api/transactions/100/receipt")) == 1


async def test_save_existing_updates(ws, fake):
    res = await _cmd(ws, type="budjetti/save", tx_id=2, date=f"{MONTH}-03", amount_cents=500,
                     tx_type="income", category="Palkka")
    assert res["success"]
    assert fake.calls("PUT", "/api/transactions/2")[0]["type"] == "income"
    assert fake.calls("POST", "/api/transactions") == []


async def test_delete_and_set_budget(ws, fake):
    assert (await _cmd(ws, type="budjetti/delete", tx_id=2))["success"]
    assert len(fake.calls("DELETE", "/api/transactions/2")) == 1
    res = await _cmd(ws, type="budjetti/set_budget", category="Ruoka", amount_cents=30000)
    assert res["success"]
    assert fake.calls("PUT", "/api/budgets/Ruoka") == [{"amount_cents": 30000}]


async def test_backend_error_is_budjetti_error(ws, fake):
    fake.errors["/api/transactions/9"] = HTTPStatus.NOT_FOUND
    res = await _cmd(ws, type="budjetti/delete", tx_id=9)
    assert not res["success"]
    assert res["error"]["code"] == "budjetti_error"


async def test_scan(ws, fake):
    res = await _cmd(ws, type="budjetti/scan", image=base64.b64encode(b"kuva").decode())
    assert res["success"]
    assert res["result"] == {"store": "Lidl", "amount_cents": 1290}
    assert len(fake.calls("POST", "/api/receipt/scan")) == 1


async def test_receipt_with_image(ws, fake):
    res = await _cmd(ws, type="budjetti/receipt", tx_id=2)
    assert res["success"]
    assert res["result"] == {"items": [{"name": "Maito", "price_cents": 129}],
                             "image": base64.b64encode(b"kuva").decode()}


async def test_receipt_without_image(ws, fake):
    fake.errors["/api/transactions/2/receipt"] = HTTPStatus.NOT_FOUND
    res = await _cmd(ws, type="budjetti/receipt", tx_id=2)
    assert res["success"]
    assert res["result"]["image"] is None


async def test_too_large_image_rejected(ws, fake, monkeypatch):
    # Oikea raja (14 Mt base64) on suurempi kuin websocketin 4 Mt viestiraja, joten se pienennetään testiin.
    monkeypatch.setattr("custom_components.budjetti.websocket.MAX_IMAGE_B64", 8)
    res = await _cmd(ws, type="budjetti/scan", image="A" * 12)
    assert not res["success"]
    assert res["error"]["message"] == "Kuva on liian suuri"


async def test_unknown_entry(ws):
    res = await _cmd(ws, type="budjetti/month", entry_id="ei-ole")
    assert res["error"]["code"] == "budjetti_error"
