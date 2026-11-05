"""Yhteiset fixturet. Budjetti-taustapalvelu korvataan HTTP-tasolla valepalvelulla (FakeBudjetti),
joten testit kulkevat koko integraation läpi api.py:stä alkaen ilman oikeaa palvelinta."""
from __future__ import annotations

import copy
import re
from http import HTTPStatus

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from custom_components.budjetti.const import CONF_API_KEY, CONF_URL, DOMAIN

URL = "http://budjetti.test:8000"
API_KEY = "testiavain"
MONTH = "2026-11"

SUMMARY = {
    "month": MONTH,
    "expense_cents": 50000,
    "income_cents": 200000,
    "net_cents": 150000,
    "total_budget_cents": 100000,
    "categories": [
        {"category": "Ruoka", "spent_cents": 30000, "budget_cents": 40000},
        {"category": "Liikenne", "spent_cents": 20000, "budget_cents": None},
    ],
}
OVERVIEW = {"forecast": {"projected_expense_cents": 90000, "projected_net_cents": 110000}}
UPCOMING = {
    "month": MONTH,
    "items": [{"name": "Vuokra", "date": f"{MONTH}-20", "amount_cents": 70000, "type": "expense",
               "category": "Asuminen"}],
    "expense_cents": 70000,
    "income_cents": 0,
    "net_after_cents": 80000,
    "next": {"name": "Vuokra", "date": f"{MONTH}-20", "amount_cents": 70000, "category": "Asuminen"},
}


def tx(tx_id: int, amount_cents: int, *, type_: str = "expense", category: str = "Ruoka",
       recurring_id: int | None = None) -> dict:
    return {"id": tx_id, "date": f"{MONTH}-05", "amount_cents": amount_cents, "type": type_,
            "category": category, "note": f"tx{tx_id}", "recurring_id": recurring_id}


class FakeBudjetti:
    """Muokattava valepalvelu. Kentät voi vaihtaa kesken testin; `errors` pakottaa polulle virheen."""

    def __init__(self) -> None:
        self.version = "0.4.1"
        self.me = {"id": 7, "username": "matias", "email": "m@example.com"}
        self.summary = copy.deepcopy(SUMMARY)
        self.overview = copy.deepcopy(OVERVIEW)
        self.upcoming = copy.deepcopy(UPCOMING)
        self.transactions: list[dict] = [tx(1, 1500), tx(2, 25000)]
        self.categories = [{"name": "Ruoka", "type": "expense"}, {"name": "Palkka", "type": "income"}]
        self.budgets = [{"category": "Ruoka", "amount_cents": 40000}]
        self.errors: dict[str, int] = {}  # polku -> HTTP-tila
        self.requests: list[tuple[str, str, object]] = []
        self.next_id = 100

    def register(self, mock: AiohttpClientMocker) -> None:
        pattern = re.compile("^" + re.escape(URL) + "/api/")
        for method in ("get", "post", "put", "delete"):
            mock.request(method, pattern, side_effect=self._handle)

    @staticmethod
    def _json(method, url, data, status=HTTPStatus.OK) -> AiohttpClientMockResponse:
        return AiohttpClientMockResponse(method, url, status=status, json=data,
                                         headers={"content-type": "application/json"})

    async def _handle(self, method: str, url, data) -> AiohttpClientMockResponse:
        method = method.upper()
        path = url.path
        self.requests.append((method, path, data))
        if path in self.errors:
            status = self.errors[path]
            return self._json(method, url, {"detail": f"virhe {status}"}, status)
        routes = {
            ("GET", "/api/health"): lambda: {"status": "ok", "version": self.version},
            ("GET", "/api/auth/me"): lambda: self.me,
            ("GET", "/api/summary"): lambda: self.summary,
            ("GET", "/api/overview"): lambda: self.overview,
            ("GET", "/api/recurring/upcoming"): lambda: self.upcoming,
            ("GET", "/api/transactions"): lambda: self.transactions,
            ("GET", "/api/categories"): lambda: self.categories,
            ("GET", "/api/budgets"): lambda: self.budgets,
        }
        if method == "GET" and path.endswith("/items"):
            return self._json(method, url, [{"name": "Maito", "price_cents": 129}])
        if method == "GET" and path.endswith("/receipt"):
            return AiohttpClientMockResponse(method, url, response=b"kuva", headers={"content-type": "image/jpeg"})
        if method == "POST" and path == "/api/receipt/scan":
            return self._json(method, url, {"store": "Lidl", "amount_cents": 1290})
        if (method, path) in routes:
            return self._json(method, url, routes[(method, path)]())
        if method == "POST" and path == "/api/transactions":
            new = {"id": self.next_id, "recurring_id": None, **data}
            self.next_id += 1
            return self._json(method, url, new, HTTPStatus.CREATED)
        if method == "PUT" and path.startswith("/api/transactions/") and path.count("/") == 3:
            return self._json(method, url, {"id": int(path.rsplit("/", 1)[1]), **data})
        if method == "PUT" and path.endswith("/items"):
            return self._json(method, url, data)
        if method == "PUT" and path.startswith("/api/budgets/"):
            return self._json(method, url, {"category": path.rsplit("/", 1)[1], **data})
        if method in ("DELETE", "PUT"):  # poisto, kuitin kuva
            return AiohttpClientMockResponse(method, url, status=HTTPStatus.NO_CONTENT)
        return self._json(method, url, {"detail": "Not Found"}, HTTPStatus.NOT_FOUND)

    def calls(self, method: str, path: str) -> list:
        return [d for m, p, d in self.requests if m == method and p == path]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Lataa custom_components/budjetti testeihin."""
    yield


@pytest.fixture(autouse=True)
def fixed_month(freezer):
    """Kuukausi kiinnitetään, jotta current_month() = MONTH."""
    freezer.move_to(f"{MONTH}-15 12:00:00")


@pytest.fixture
def fake(aioclient_mock: AiohttpClientMocker) -> FakeBudjetti:
    backend = FakeBudjetti()
    backend.register(aioclient_mock)
    return backend


@pytest.fixture
def entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN, title="Budjetti (matias)", unique_id=f"{URL}#7",
        data={CONF_URL: URL, CONF_API_KEY: API_KEY},
    )


@pytest.fixture
async def setup(hass, entry, fake):
    """Integraatio asennettuna valepalvelua vasten."""
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
