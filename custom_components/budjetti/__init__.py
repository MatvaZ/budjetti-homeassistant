"""Budjetti: kuukauden budjetti Home Assistantiin (anturit, palvelut ja budjettikortti)."""
from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from . import services, websocket
from .api import BudjettiClient
from .const import CARD_URL, CONF_API_KEY, CONF_URL, DOMAIN
from .coordinator import BudjettiConfigEntry, BudjettiCoordinator

PLATFORMS = [Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Kerran: palvelut, websocket-komennot ja kortin JS (ladataan automaattisesti)."""
    services.async_register(hass)
    websocket.async_register(hass)
    card = Path(__file__).parent / "frontend" / "budjetti-card.js"
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(card), False)])
    integration = await async_get_integration(hass, DOMAIN)
    add_extra_js_url(hass, f"{CARD_URL}?v={integration.version}")  # välimuistin ohitus päivityksissä
    return True


async def async_setup_entry(hass: HomeAssistant, entry: BudjettiConfigEntry) -> bool:
    client = BudjettiClient(async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_API_KEY])
    coordinator = BudjettiCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: BudjettiConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
