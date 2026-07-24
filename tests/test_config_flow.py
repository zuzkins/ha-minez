"""Tests for the MineZ config flow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.minez.api import MinezApiAuthError, MinezConnectionInfo
from custom_components.minez.config_flow import (
    MinezConfigFlow,
    MinezValidationClient,
)
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


class MinezConfigFlowStub(MinezConfigFlow):
    """Config flow with observable validation clients and no reload task."""

    def __init__(self) -> None:
        self.clients: list[MinerApiClientStub] = []

    def _create_validation_client(
        self, info: MinezConnectionInfo
    ) -> MinezValidationClient:
        client = MinerApiClientStub(info)
        self.clients.append(client)
        return client

    def async_update_reload_and_abort(
        self,
        entry: ConfigEntry,
        *,
        data: dict[str, Any],
        reason: str,
        **_kwargs: Any,
    ) -> config_entries.ConfigFlowResult:
        """Update the entry without scheduling integration setup."""
        self.hass.config_entries.async_update_entry(entry, data=data)
        return self.async_abort(reason=reason)


def create_flow(
    hass: HomeAssistant,
) -> tuple[MinezConfigFlowStub, MockConfigEntry]:
    """Create a reauthentication flow and its existing config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Miner",
        unique_id="miner-uid",
        data=ENTRY_DATA,
    )
    entry.add_to_hass(hass)
    flow = MinezConfigFlowStub()
    flow.hass = hass
    flow.context = {
        "source": config_entries.SOURCE_REAUTH,
        "entry_id": entry.entry_id,
        "unique_id": entry.unique_id,
    }
    return flow, entry


async def test_reauth_updates_changed_credentials(hass: HomeAssistant) -> None:
    """Changed credentials are validated and stored."""
    flow, entry = create_flow(hass)

    result = await flow.async_step_reauth(entry.data)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await flow.async_step_reauth_confirm(NEW_CREDENTIALS)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data == {**ENTRY_DATA, **NEW_CREDENTIALS}
    assert len(flow.clients) == 1
    assert flow.clients[0].info == MinezConnectionInfo(
        host=ENTRY_DATA[CONF_HOST],
        port=ENTRY_DATA[CONF_PORT],
        username=NEW_CREDENTIALS[CONF_USERNAME],
        password=NEW_CREDENTIALS[CONF_PASSWORD],
    )
    assert flow.clients[0].closed


async def test_reauth_rejects_invalid_changed_credentials(
    hass: HomeAssistant,
) -> None:
    """Invalid replacement credentials do not modify the config entry."""
    flow, entry = create_flow(hass)

    await flow.async_step_reauth(entry.data)
    result = await flow.async_step_reauth_confirm(INVALID_CREDENTIALS)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"
    assert result["errors"] == {"base": "invalid_auth"}
    assert entry.data == ENTRY_DATA
    assert len(flow.clients) == 1
    assert flow.clients[0].info.username == INVALID_CREDENTIALS[CONF_USERNAME]
    assert flow.clients[0].info.password == INVALID_CREDENTIALS[CONF_PASSWORD]
    assert flow.clients[0].closed
