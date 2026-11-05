"""Budjetti-sovelluksen REST-rajapinta (budjetti-backend)."""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import aiohttp

TIMEOUT = aiohttp.ClientTimeout(total=30)
SCAN_TIMEOUT = aiohttp.ClientTimeout(total=120)  # kuitin luku kestää hetken


class BudjettiError(Exception):
    """Budjettiin ei saatu yhteyttä tai se palautti virheen."""


class BudjettiAuthError(BudjettiError):
    """API-avain ei kelpaa."""


class BudjettiNotFoundError(BudjettiError):
    """Pyydettyä ei ole, esim. vanhempi sovellusversio ilman uutta rajapintaa."""


def current_month() -> str:
    return date.today().strftime("%Y-%m")


class BudjettiClient:
    def __init__(self, session: aiohttp.ClientSession, url: str, api_key: str) -> None:
        self._session = session
        self._url = url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def _request(self, method: str, path: str, *, timeout=TIMEOUT, **kwargs) -> Any:
        try:
            async with self._session.request(
                method, self._url + path, headers=self._headers, timeout=timeout, **kwargs
            ) as resp:
                if resp.status == 401:
                    raise BudjettiAuthError("API-avain ei kelpaa")
                if resp.status >= 400:
                    try:
                        detail = (await resp.json()).get("detail")
                    except (aiohttp.ContentTypeError, ValueError):
                        detail = None
                    if not isinstance(detail, str):
                        detail = f"HTTP {resp.status}"
                    raise (BudjettiNotFoundError if resp.status in (404, 405) else BudjettiError)(detail)
                if resp.status == 204:
                    return None
                if resp.content_type == "application/json":
                    return await resp.json()
                return await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise BudjettiError(f"Budjettiin ei saatu yhteyttä: {err}") from err

    # --- luku ---
    async def health(self) -> dict:
        return await self._request("GET", "/api/health")

    async def me(self) -> dict:
        return await self._request("GET", "/api/auth/me")

    async def summary(self, month: str) -> dict:
        return await self._request("GET", "/api/summary", params={"month": month})

    async def overview(self, month: str) -> dict:
        return await self._request("GET", "/api/overview", params={"month": month})

    async def upcoming(self, month: str) -> dict:
        """Kuun tulevat toistuvat. Sovellus ennen versiota 0.4.0 ei tunne tätä: tyhjä tulos."""
        try:
            return await self._request("GET", "/api/recurring/upcoming", params={"month": month})
        except BudjettiNotFoundError:
            return {"month": month, "items": [], "expense_cents": 0, "income_cents": 0,
                    "net_after_cents": None, "next": None}

    async def transactions(self, month: str) -> list[dict]:
        return await self._request("GET", "/api/transactions", params={"month": month})

    async def categories(self) -> list[dict]:
        return await self._request("GET", "/api/categories")

    async def budgets(self, month: str) -> list[dict]:
        return await self._request("GET", "/api/budgets", params={"month": month})

    async def items(self, tx_id: int) -> list[dict]:
        return await self._request("GET", f"/api/transactions/{tx_id}/items")

    async def receipt(self, tx_id: int) -> bytes:
        return await self._request("GET", f"/api/transactions/{tx_id}/receipt")

    # --- muutokset ---
    async def add_transaction(self, data: dict) -> dict:
        return await self._request("POST", "/api/transactions", json=data)

    async def update_transaction(self, tx_id: int, data: dict) -> dict:
        return await self._request("PUT", f"/api/transactions/{tx_id}", json=data)

    async def delete_transaction(self, tx_id: int) -> None:
        await self._request("DELETE", f"/api/transactions/{tx_id}")

    async def set_budget(self, category: str, month: str, amount_cents: int, only: bool = False) -> dict:
        params = {"month": month}
        if only:
            params["only"] = "true"
        return await self._request(
            "PUT", f"/api/budgets/{category}", params=params, json={"amount_cents": amount_cents}
        )

    async def scan_receipt(self, image: bytes, media_type: str) -> dict:
        form = aiohttp.FormData()
        form.add_field("file", image, filename="kuitti.jpg", content_type=media_type)
        return await self._request("POST", "/api/receipt/scan", data=form, timeout=SCAN_TIMEOUT)

    async def set_items(self, tx_id: int, items: list[dict]) -> list[dict]:
        return await self._request("PUT", f"/api/transactions/{tx_id}/items", json=items)

    async def upload_receipt(self, tx_id: int, image: bytes, media_type: str) -> None:
        form = aiohttp.FormData()
        form.add_field("file", image, filename="kuitti.jpg", content_type=media_type)
        await self._request("PUT", f"/api/transactions/{tx_id}/receipt", data=form)
