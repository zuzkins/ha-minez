"""Tests for MineZ number entities."""

from __future__ import annotations

from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_HOST, CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest import MonkeyPatch
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.minez as minez
from custom_components.minez.const import DOMAIN
from tests.stubs import ACTIVE_POWER_TARGET, MinerApiStub

NEW_POWER_TARGET = 3_600


async def test_set_power_target_keeps_configured_and_active_values_distinct(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """The number controls configuration while the sensor shows active DPS."""
    api = MinerApiStub()

    class ApiClientFactoryStub:
        """Return the power-target API stub for config-entry setup."""

        @classmethod
        def from_config_entry(cls, _entry: ConfigEntry) -> MinerApiStub:
            return api

    monkeypatch.setattr(minez, "MinezApiClient", ApiClientFactoryStub)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Miner",
        unique_id="miner-uid",
        data={
            CONF_HOST: "miner.local",
            CONF_USERNAME: "user",
            CONF_PASSWORD: "password",
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    number_entity_id = registry.async_get_entity_id(
        NUMBER_DOMAIN, DOMAIN, "miner-uid_power_target"
    )
    sensor_entity_id = registry.async_get_entity_id(
        SENSOR_DOMAIN, DOMAIN, "miner-uid_power_target_w"
    )
    approximate_power_entity_id = registry.async_get_entity_id(
        SENSOR_DOMAIN, DOMAIN, "miner-uid_power_w"
    )
    assert number_entity_id == "number.miner_power_target"
    assert sensor_entity_id == "sensor.miner_current_power_target"
    assert (
        approximate_power_entity_id
        == "sensor.miner_approximate_power_consumption"
    )

    try:
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {
                ATTR_ENTITY_ID: number_entity_id,
                ATTR_VALUE: NEW_POWER_TARGET,
            },
            blocking=True,
        )
        await hass.async_block_till_done()

        assert api.set_power_targets == [NEW_POWER_TARGET]
        assert api.configured_power_target == NEW_POWER_TARGET
        assert hass.states.get(sensor_entity_id).state == str(ACTIVE_POWER_TARGET)
        assert hass.states.get(number_entity_id).state == str(NEW_POWER_TARGET)
    finally:
        assert await hass.config_entries.async_unload(entry.entry_id)

    assert api.closed
