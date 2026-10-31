"""Kuluvan kuukauden tilanne minuutin välein antureita varten."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BudjettiAuthError, BudjettiClient, BudjettiError, current_month
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class BudjettiData:
    month: str
    summary: dict
    overview: dict
    version: str


class BudjettiCoordinator(DataUpdateCoordinator[BudjettiData]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: BudjettiClient) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.client = client

    async def _async_update_data(self) -> BudjettiData:
        month = current_month()
        try:
            summary = await self.client.summary(month)
            overview = await self.client.overview(month)
            health = await self.client.health()
        except BudjettiAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except BudjettiError as err:
            raise UpdateFailed(str(err)) from err
        return BudjettiData(month, summary, overview, health.get("version", "?"))


type BudjettiConfigEntry = ConfigEntry[BudjettiCoordinator]
