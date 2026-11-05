"""Palvelut add_transaction, set_budget ja delete_transaction."""
from http import HTTPStatus

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.budjetti.const import DOMAIN

from .conftest import MONTH


async def _call(hass, service, data, **kw):
    return await hass.services.async_call(DOMAIN, service, data, blocking=True, **kw)


@pytest.mark.parametrize(("kind", "amount", "cents", "tx_type"), [
    ("expense", 12.345, 1234, "expense"),
    ("income", 100, 10000, "income"),
    ("refund", 5, -500, "expense"),    # hyvitys = negatiivinen meno
    ("expense", -7.5, 750, "expense"),  # etumerkki ohitetaan
])
async def test_add_transaction(hass, setup, fake, kind, amount, cents, tx_type):
    result = await _call(hass, "add_transaction",
                         {"amount": amount, "category": "Ruoka", "note": "Lidl", "type": kind},
                         return_response=True)
    sent = fake.calls("POST", "/api/transactions")
    assert sent == [{"date": f"{MONTH}-15", "amount_cents": cents, "type": tx_type,
                     "category": "Ruoka", "note": "Lidl"}]
    assert result["transaction"]["id"] == 100


async def test_add_transaction_with_date_refreshes(hass, setup, fake):
    before = len(fake.calls("GET", "/api/summary"))
    await _call(hass, "add_transaction", {"amount": 1, "category": "Ruoka", "date": "2026-10-31"})
    assert fake.calls("POST", "/api/transactions")[0]["date"] == "2026-10-31"
    assert len(fake.calls("GET", "/api/summary")) == before + 1


async def test_add_zero_is_rejected(hass, setup, fake):
    with pytest.raises(ServiceValidationError):
        await _call(hass, "add_transaction", {"amount": 0.001, "category": "Ruoka"})
    assert fake.calls("POST", "/api/transactions") == []


async def test_backend_error_is_ha_error(hass, setup, fake):
    fake.errors["/api/transactions"] = HTTPStatus.BAD_REQUEST
    with pytest.raises(HomeAssistantError, match="virhe 400"):
        await _call(hass, "add_transaction", {"amount": 1, "category": "Tuntematon"})


async def test_set_budget(hass, setup, fake, aioclient_mock):
    await _call(hass, "set_budget", {"category": "Ruoka", "amount": 450.5, "only_this_month": True})
    assert fake.calls("PUT", "/api/budgets/Ruoka") == [{"amount_cents": 45050}]
    url = next(c[1] for c in aioclient_mock.mock_calls if c[1].path == "/api/budgets/Ruoka")
    assert url.query["month"] == MONTH and url.query["only"] == "true"


async def test_set_budget_month_validated(hass, setup):
    with pytest.raises(Exception):
        await _call(hass, "set_budget", {"category": "Ruoka", "amount": 1, "month": "11/2026"})


async def test_delete_transaction(hass, setup, fake):
    await _call(hass, "delete_transaction", {"id": 42})
    assert len(fake.calls("DELETE", "/api/transactions/42")) == 1


async def test_unknown_entry(hass, setup):
    with pytest.raises(ServiceValidationError):
        await _call(hass, "delete_transaction", {"id": 1, "config_entry_id": "ei-ole"})
