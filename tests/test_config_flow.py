"""Tests for the MineZ config flow."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest import MonkeyPatch
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.minez as minez
from custom_components.minez import config_flow
from custom_components.minez.api import MinezApiAuthError, MinezConnectionInfo
from custom_components.minez.const import DOMAIN

ENTRY_DATA = {
    CONF_HOST: "miner.local",
    CONF_PORT: 50051,
    CONF_USERNAME: "old-user",
    CONF_PASSWORD: "old-password",
}
NEW_CREDENTIALS = {
    CONF_USERNAME: "new-user",
    CONF_PASSWORD: "new-password",
}
INVALID_CREDENTIALS = {
    CONF_USERNAME: "new-user",
    CONF_PASSWORD: "invalid-password",
}


@dataclass
class MinerApiClientStub:
    """Stub credential validation at the miner API boundary."""

    info: MinezConnectionInfo
    closed: bool = False

    async def async_validate(self) -> dict[str, str]:
        """Accept credentials unless the test password is invalid."""
        if self.info.password == INVALID_CREDENTIALS[CONF_PASSWORD]:
            raise MinezApiAuthError("invalid credentials")
        return {
            "uid": "miner-uid",
            "hostname": "miner",
            "model": "Antminer",
            "api_version": "1.0.0",
        }

    async def async_close(self) -> None:
        """Record that validation released the client."""
        self.closed = True


@pytest.fixture
def miner_api_clients(
    monkeypatch: MonkeyPatch,
) -> list[MinerApiClientStub]:
    """Replace network clients with observable API stubs."""
    clients: list[MinerApiClientStub] = []

    def create_client(info: MinezConnectionInfo) -> MinerApiClientStub:
        client = MinerApiClientStub(info)
        clients.append(client)
        return client

    monkeypatch.setattr(config_flow, "MinezApiClient", create_client)
    return clients


@pytest.fixture
def setup_entry_stub(monkeypatch: MonkeyPatch) -> None:
    """Keep a successful reauth reload inside the config-flow boundary."""

    async def async_setup_entry(
        _hass: HomeAssistant,
        _entry: ConfigEntry,
    ) -> bool:
        return True

    monkeypatch.setattr(minez, "async_setup_entry", async_setup_entry)


def add_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Add an existing MineZ entry to Home Assistant."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Miner",
        unique_id="miner-uid",
        data=ENTRY_DATA,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.mark.usefixtures("setup_entry_stub")
async def test_reauth_updates_changed_credentials(
    hass: HomeAssistant,
    miner_api_clients: list[MinerApiClientStub],
) -> None:
    """Changed credentials are validated and stored."""
    entry = add_config_entry(hass)

    result = await entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        NEW_CREDENTIALS,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == {**ENTRY_DATA, **NEW_CREDENTIALS}
    assert len(miner_api_clients) == 1
    assert miner_api_clients[0].info == MinezConnectionInfo(
        host=ENTRY_DATA[CONF_HOST],
        port=ENTRY_DATA[CONF_PORT],
        username=NEW_CREDENTIALS[CONF_USERNAME],
        password=NEW_CREDENTIALS[CONF_PASSWORD],
    )
    assert miner_api_clients[0].closed


async def test_reauth_rejects_invalid_changed_credentials(
    hass: HomeAssistant,
    miner_api_clients: list[MinerApiClientStub],
) -> None:
    """Invalid replacement credentials do not modify the config entry."""
    entry = add_config_entry(hass)

    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        INVALID_CREDENTIALS,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data == ENTRY_DATA
    assert len(miner_api_clients) == 1
    assert miner_api_clients[0].info.username == INVALID_CREDENTIALS[CONF_USERNAME]
    assert miner_api_clients[0].info.password == INVALID_CREDENTIALS[CONF_PASSWORD]
    assert miner_api_clients[0].closed
