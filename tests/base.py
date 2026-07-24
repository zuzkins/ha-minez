"""Base classes for Home Assistant entity tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import cast

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from custom_components.minez.api import MinezApiClient
from custom_components.minez.coordinator import MinezDataUpdateCoordinator
from tests.stubs import MinerApiStub


class MinezEntityTestBase:
    """Set up a real coordinator and manage directly registered entities."""

    hass: HomeAssistant
    api: MinerApiStub
    coordinator: MinezDataUpdateCoordinator

    @pytest.fixture(autouse=True)
    async def setup_entity_test(
        self,
        hass: HomeAssistant,
    ) -> AsyncGenerator[None]:
        """Set up and tear down the entity test environment."""
        self.hass = hass
        self.api = MinerApiStub()
        self.coordinator = MinezDataUpdateCoordinator(
            hass, cast(MinezApiClient, self.api)
        )
        self._entities: list[Entity] = []
        await self.coordinator.async_refresh()

        yield

        for entity in reversed(self._entities):
            await entity.async_remove(force_remove=True)
        await self.api.async_close()
