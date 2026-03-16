"""Coordinator for the MineZ integration."""

from __future__ import annotations

import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MinezApiAuthError, MinezApiClient, MinezApiError
from .const import DOMAIN, UPDATE_INTERVAL


class MinezDataUpdateCoordinator(DataUpdateCoordinator[dict]):
    """Manage MineZ data fetching."""

    def __init__(self, hass: HomeAssistant, client: MinezApiClient) -> None:
        super().__init__(
            hass,
            logger=logging.getLogger(__name__),
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client
        self._last_success_monotonic: float | None = None

    async def _async_update_data(self) -> dict:
        try:
            data = await self.client.async_fetch_data()
        except MinezApiAuthError:
            raise
        except MinezApiError as err:
            raise UpdateFailed(str(err)) from err

        now = time.monotonic()
        interval_s = None
        if self._last_success_monotonic is not None:
            interval_s = round(now - self._last_success_monotonic, 6)
        self._last_success_monotonic = now

        data.setdefault("diagnostics", {})["last_fetch_interval_s"] = interval_s
        return data
