"""BudjettiClient: virheiden luokittelu ja vanhan sovellusversion käsittely."""
import asyncio
from http import HTTPStatus

import aiohttp
import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.budjetti.api import (
    BudjettiAuthError,
    BudjettiClient,
    BudjettiError,
    BudjettiNotFoundError,
)

from .conftest import API_KEY, MONTH, URL

JSON = {"content-type": "application/json"}


@pytest.fixture
def client(hass, aioclient_mock):
    return BudjettiClient(async_get_clientsession(hass), URL + "/", API_KEY)


async def test_bearer_header_and_trailing_slash(client, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/health", json={"version": "0.4.1"}, headers=JSON)
    assert await client.health() == {"version": "0.4.1"}
    method, url, _, headers = aioclient_mock.mock_calls[0]
    assert str(url) == f"{URL}/api/health"
    assert headers["Authorization"] == f"Bearer {API_KEY}"


async def test_401_is_auth_error(client, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/auth/me", status=HTTPStatus.UNAUTHORIZED)
    with pytest.raises(BudjettiAuthError):
        await client.me()


@pytest.mark.parametrize("status", [HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED])
async def test_404_405_are_not_found(client, aioclient_mock, status):
    aioclient_mock.get(f"{URL}/api/summary", status=status, json={"detail": "Ei löydy"}, headers=JSON)
    with pytest.raises(BudjettiNotFoundError, match="Ei löydy"):
        await client.summary(MONTH)


async def test_server_error_without_json_detail(client, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/summary", status=HTTPStatus.INTERNAL_SERVER_ERROR, text="oops")
    with pytest.raises(BudjettiError, match="HTTP 500") as err:
        await client.summary(MONTH)
    assert not isinstance(err.value, BudjettiNotFoundError)


async def test_non_string_detail_falls_back_to_status(client, aioclient_mock):
    aioclient_mock.post(f"{URL}/api/transactions", status=HTTPStatus.UNPROCESSABLE_ENTITY,
                        json={"detail": [{"msg": "virhe"}]}, headers=JSON)
    with pytest.raises(BudjettiError, match="HTTP 422"):
        await client.add_transaction({})


@pytest.mark.parametrize("exc", [aiohttp.ClientConnectionError("ei yhteyttä"), asyncio.TimeoutError()])
async def test_connection_errors(client, aioclient_mock, exc):
    aioclient_mock.get(f"{URL}/api/health", exc=exc)
    with pytest.raises(BudjettiError, match="Budjettiin ei saatu yhteyttä"):
        await client.health()


async def test_204_returns_none_and_binary_returns_bytes(client, aioclient_mock):
    aioclient_mock.delete(f"{URL}/api/transactions/5", status=HTTPStatus.NO_CONTENT)
    aioclient_mock.get(f"{URL}/api/transactions/5/receipt", content=b"\xff\xd8kuva",
                       headers={"content-type": "image/jpeg"})
    assert await client.delete_transaction(5) is None
    assert await client.receipt(5) == b"\xff\xd8kuva"


async def test_set_budget_only_param(client, aioclient_mock):
    aioclient_mock.put(f"{URL}/api/budgets/Ruoka", json={}, headers=JSON)
    await client.set_budget("Ruoka", MONTH, 1000)
    await client.set_budget("Ruoka", MONTH, 1000, only=True)
    first, second = (str(c[1]) for c in aioclient_mock.mock_calls)
    assert "only" not in first
    assert "only=true" in second
    assert aioclient_mock.mock_calls[0][2] == {"amount_cents": 1000}


@pytest.mark.parametrize("status", [HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED])
async def test_upcoming_missing_on_old_backend_is_empty(client, aioclient_mock, status):
    """Budjetti < 0.4.0: /api/recurring/upcoming puuttuu -> tyhjä tulos, ei virhettä."""
    aioclient_mock.get(f"{URL}/api/recurring/upcoming", status=status)
    result = await client.upcoming(MONTH)
    assert result == {"month": MONTH, "items": [], "expense_cents": 0, "income_cents": 0,
                      "net_after_cents": None, "next": None}


async def test_upcoming_other_errors_propagate(client, aioclient_mock):
    aioclient_mock.get(f"{URL}/api/recurring/upcoming", status=HTTPStatus.INTERNAL_SERVER_ERROR)
    with pytest.raises(BudjettiError):
        await client.upcoming(MONTH)
