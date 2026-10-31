"""Asetus käyttöliittymästä: budjetin osoite ja API-avain."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BudjettiAuthError, BudjettiClient, BudjettiError
from .const import CONF_API_KEY, CONF_URL, DOMAIN

SCHEMA = vol.Schema({
    vol.Required(CONF_URL, default="http://"): str,
    vol.Required(CONF_API_KEY): str,
})


class BudjettiConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, data: dict) -> tuple[dict | None, dict]:
        errors: dict[str, str] = {}
        client = BudjettiClient(async_get_clientsession(self.hass), data[CONF_URL], data[CONF_API_KEY])
        try:
            return await client.me(), errors
        except BudjettiAuthError:
            errors["base"] = "invalid_auth"
        except BudjettiError:
            errors["base"] = "cannot_connect"
        return None, errors

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input[CONF_URL] = user_input[CONF_URL].strip().rstrip("/")
            me, errors = await self._validate(user_input)
            if me:
                await self.async_set_unique_id(f"{user_input[CONF_URL]}#{me['id']}")
                self._abort_if_unique_id_configured()
                title = f"Budjetti ({me.get('username') or me['email']})"
                return self.async_create_entry(title=title, data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input), errors=errors
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Uusi API-avain, kun vanha on peruttu."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
            me, errors = await self._validate(data)
            if me:
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reauth_confirm", data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}), errors=errors
        )
