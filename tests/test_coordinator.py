"""Tests for the MineZ data coordinator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.minez.api import (
    MinezApiAuthError,
    MinezApiClient,
    MinezApiError,
)
from custom_components.minez.coordinator import MinezDataUpdateCoordinator


@dataclass
class ApiClientStub:
    """Return queued snapshots or API failures."""

    outcomes: list[dict[str, Any] | MinezApiError]

    async def async_fetch_data(self) -> dict[str, Any]:
        """Return or raise the next queued outcome."""
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, MinezApiError):
            raise outcome
        return outcome


def create_coordinator(
    hass: HomeAssistant,
    *outcomes: dict[str, Any] | MinezApiError,
) -> tuple[MinezDataUpdateCoordinator, ApiClientStub]:
    """Create a coordinator backed by the API client stub."""
    client = ApiClientStub(list(outcomes))
    coordinator = MinezDataUpdateCoordinator(hass, cast(MinezApiClient, client))
    return coordinator, client


async def test_successful_update_adds_fetch_diagnostics(
    hass: HomeAssistant,
) -> None:
    """A successful first update records an empty fetch interval."""
    snapshot = {"miner": {"uid": "miner-uid"}, "diagnostics": {"source": "api"}}
    coordinator, client = create_coordinator(hass, snapshot)

    result = await coordinator._async_update_data()

    assert result is snapshot
    assert result["diagnostics"] == {
        "source": "api",
        "last_fetch_interval_s": None,
    }
    assert client.outcomes == []


@pytest.mark.parametrize(
    ("api_error", "expected_error", "message"),
    [
        (
            MinezApiAuthError("invalid credentials"),
            ConfigEntryAuthFailed,
            "Authentication to the miner failed",
        ),
        (
            MinezApiError("miner unavailable"),
            UpdateFailed,
            "miner unavailable",
        ),
    ],
)
async def test_update_translates_api_errors(
    hass: HomeAssistant,
    api_error: MinezApiError,
    expected_error: type[Exception],
    message: str,
) -> None:
    """API failures become the corresponding Home Assistant exception."""
    coordinator, _client = create_coordinator(hass, api_error)

    with pytest.raises(expected_error, match=message) as raised:
        await coordinator._async_update_data()

    assert raised.value.__cause__ is api_error
