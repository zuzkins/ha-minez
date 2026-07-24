"""Tests for MineZ number entities."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

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

ACTIVE_POWER_TARGET = 2_300
CONFIGURED_POWER_TARGET = 3_500
NEW_POWER_TARGET = 3_600


class PowerTargetApiStub:
    """Expose distinct configured and active runtime power targets."""

    def __init__(self) -> None:
        self.configured_power_target = CONFIGURED_POWER_TARGET
        self.set_power_targets: list[float] = []
        self.closed = False

    async def async_fetch_data(self) -> dict[str, Any]:
        """Return a complete snapshot with DPS below the configured target."""
        snapshot = {
            "api_version": "1.0.0",
            "miner": {
                "uid": "miner-uid",
                "hostname": "Miner",
                "mac_address": "00:11:22:33:44:55",
                "status": "Normal",
                "brand": "MINER_BRAND_ANTMINER",
                "model": "Antminer S19",
                "name": "Antminer S19",
                "platform": "PLATFORM_AM3_AML",
                "control_board_soc_family": "CONTROL_BOARD_SOC_FAMILY_AML",
                "bos_mode": "BOS_MODE_NAND",
                "bos_version": "25.01",
                "kernel_version": "5.10",
                "serial_number": "SN123",
                "system_uptime_s": 7_200,
                "bosminer_uptime_s": 3_600,
                "sticker_hashrate_ths": 100.0,
            },
            "stats": {
                "hashrate_5m_ths": 90.0,
                "hashrate_15m_ths": 91.0,
                "hashrate_24h_ths": 92.0,
                "hashrate_since_restart_ths": 89.0,
                "nominal_hashrate_ths": 100.0,
                "error_hashrate_mhs": 0.0,
                "power_w": 2_150,
                "efficiency_jth": 24.0,
                "accepted_shares": 10,
                "rejected_shares": 0,
                "stale_shares": 0,
                "best_share": 100,
                "found_blocks": 0,
            },
            "cooling": {
                "highest_temp_c": 70.0,
                "fan_count": 0,
                "fan_rpm_avg": None,
                "fans": [],
            },
            "performance": {
                "tuner_state": "Stable",
                "mode_state": "power_target_mode_state",
                "power_target_w": ACTIVE_POWER_TARGET,
                "configured_power_target_w": self.configured_power_target,
                "hashrate_target_ths": None,
                "power_target_min_w": 2_000,
                "power_target_max_w": 4_000,
            },
            "controls": {
                "locate_device_enabled": False,
                "supports_power_target": True,
            },
            "errors": {"count": 0, "messages": []},
            "hashboards": {"count": 0, "items": []},
            "diagnostics": {},
        }
        return deepcopy(snapshot)

    async def async_set_power_target(self, watts: float) -> None:
        """Update the configured target without changing the DPS target."""
        self.set_power_targets.append(watts)
        self.configured_power_target = round(watts)

    async def async_close(self) -> None:
        """Close the API stub."""
        self.closed = True


async def test_set_power_target_number_displays_active_target(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """The number displays the active DPS target after updating configuration."""
    api = PowerTargetApiStub()

    class ApiClientFactoryStub:
        """Return the power-target API stub for config-entry setup."""

        @classmethod
        def from_config_entry(cls, _entry: ConfigEntry) -> PowerTargetApiStub:
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
    assert number_entity_id is not None
    assert sensor_entity_id is not None

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
        assert hass.states.get(number_entity_id).state == str(ACTIVE_POWER_TARGET)
    finally:
        assert await hass.config_entries.async_unload(entry.entry_id)

    assert api.closed
