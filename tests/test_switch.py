"""Tests for MineZ switch entities."""

from __future__ import annotations

from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_USERNAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest import MonkeyPatch
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.minez as minez
from custom_components.minez.const import DOMAIN
from tests.stubs import MinerApiStub


async def test_mining_switch_pauses_and_resumes_mining(
    hass: HomeAssistant,
    monkeypatch: MonkeyPatch,
) -> None:
    """The mining switch follows miner state and invokes both actions."""
    api = MinerApiStub()

    class ApiClientFactoryStub:
        """Return the mining API stub for config-entry setup."""

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
    entity_id = registry.async_get_entity_id(
        SWITCH_DOMAIN, DOMAIN, "miner-uid_mining"
    )
    assert entity_id == "switch.miner_mining"
    assert hass.states.get(entity_id).state == STATE_ON
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    try:
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_OFF,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert api.pause_requests == 1
        assert hass.states.get(entity_id).state == STATE_OFF

        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: entity_id},
            blocking=True,
        )
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert api.resume_requests == 1
        assert hass.states.get(entity_id).state == STATE_ON

        api.status = "Restricted"
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    finally:
        assert await hass.config_entries.async_unload(entry.entry_id)

    assert api.closed
