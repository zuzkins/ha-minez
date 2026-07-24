"""Tests for MineZ number entities."""

from __future__ import annotations

from homeassistant.components import number
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.setup import async_setup_component

from custom_components.minez.number import MinezPowerTargetNumber
from tests.base import MinezEntityTestBase
from tests.stubs import ACTIVE_POWER_TARGET

NEW_POWER_TARGET = 3_600


class TestMinezPowerTargetNumber(MinezEntityTestBase):
    """Test the configured power target number."""

    async def test_set_value_keeps_configured_and_active_targets_distinct(
        self,
    ) -> None:
        """The number controls configuration while DPS remains independent."""
        entity = MinezPowerTargetNumber(self.coordinator)
        assert entity.unique_id == "miner-uid_power_target"
        assert await async_setup_component(self.hass, number.DOMAIN, {})
        component = self.hass.data[number.DATA_COMPONENT]
        await component.async_add_entities([entity])
        self._entities.append(entity)
        assert entity.entity_id is not None

        await self.hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: entity.entity_id, ATTR_VALUE: NEW_POWER_TARGET},
            blocking=True,
        )
        await self.coordinator.async_refresh()
        await self.hass.async_block_till_done()

        assert self.api.set_power_targets == [NEW_POWER_TARGET]
        assert self.api.configured_power_target == NEW_POWER_TARGET
        assert (
            self.coordinator.data["performance"]["power_target_w"]
            == ACTIVE_POWER_TARGET
        )
        assert (
            self.coordinator.data["performance"]["configured_power_target_w"]
            == NEW_POWER_TARGET
        )
        assert self.hass.states.get(entity.entity_id).state == str(NEW_POWER_TARGET)
