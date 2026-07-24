"""Tests for MineZ switch entities."""

from __future__ import annotations

from homeassistant.components import switch
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.setup import async_setup_component

from custom_components.minez.switch import MinezMiningSwitch
from tests.base import MinezEntityTestBase


class TestMinezMiningSwitch(MinezEntityTestBase):
    """Test the pause and resume mining switch."""

    async def test_pause_resume_and_unsupported_status(self) -> None:
        """The switch invokes both actions and follows miner state."""
        entity = MinezMiningSwitch(self.coordinator)
        assert entity.unique_id == "miner-uid_mining"
        assert await async_setup_component(self.hass, switch.DOMAIN, {})
        component = self.hass.data[switch.DATA_COMPONENT]
        await component.async_add_entities([entity])
        self._entities.append(entity)
        assert entity.entity_id is not None
        assert self.hass.states.get(entity.entity_id).state == STATE_ON

        await self.hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity.entity_id},
            blocking=True,
        )
        await self.coordinator.async_refresh()
        await self.hass.async_block_till_done()

        assert self.api.pause_requests == 1
        assert self.hass.states.get(entity.entity_id).state == STATE_OFF

        await self.hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity.entity_id},
            blocking=True,
        )
        await self.coordinator.async_refresh()
        await self.hass.async_block_till_done()

        assert self.api.resume_requests == 1
        assert self.hass.states.get(entity.entity_id).state == STATE_ON

        self.api.status = "Restricted"
        await self.coordinator.async_refresh()
        await self.hass.async_block_till_done()

        assert self.hass.states.get(entity.entity_id).state == STATE_UNAVAILABLE
