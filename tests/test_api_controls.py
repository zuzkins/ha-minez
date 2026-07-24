"""Tests for MineZ API control commands."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from google.protobuf.message import Message

from custom_components.minez.api import MinezApiClient, MinezConnectionInfo
from custom_components.minez.bos.v1 import (
    actions_pb2,
    authentication_pb2,
    common_pb2,
    performance_pb2,
)

TOKEN = "session-token"
AUTH_METADATA = (("authorization", TOKEN),)
LOGIN_METHOD = "/braiins.bos.v1.AuthenticationService/Login"


@dataclass(frozen=True)
class RecordedCall:
    """An authenticated RPC captured by the channel stub."""

    method: str
    request: Message
    metadata: tuple[tuple[str, str], ...] | None


class ControlChannelStub:
    """Record calls made through generated gRPC service stubs."""

    def __init__(self) -> None:
        self.login_requests: list[authentication_pb2.LoginRequest] = []
        self.calls: list[RecordedCall] = []
        self.closed = False

    def unary_unary(
        self,
        method: str,
        **_kwargs: Any,
    ) -> Callable[..., Awaitable[object]]:
        """Return a coroutine that records the selected RPC."""

        async def invoke(
            request: Message,
            metadata: tuple[tuple[str, str], ...] | None = None,
        ) -> object:
            if method == LOGIN_METHOD:
                assert isinstance(request, authentication_pb2.LoginRequest)
                self.login_requests.append(request)
                return authentication_pb2.LoginResponse(token=TOKEN)

            self.calls.append(RecordedCall(method, request, metadata))
            return object()

        return invoke

    async def close(self) -> None:
        """Close the channel stub."""
        self.closed = True


def create_client() -> tuple[MinezApiClient, ControlChannelStub]:
    """Create an authenticated client backed by a recording channel."""
    channel = ControlChannelStub()
    client = MinezApiClient(
        MinezConnectionInfo(
            host="miner.local",
            username="user",
            password="password",
        )
    )
    client._channel = channel  # type: ignore[assignment]
    return client, channel


async def test_action_commands_use_authenticated_rpcs() -> None:
    """Action controls select the expected RPCs and reuse one session."""
    client, channel = create_client()

    try:
        await client.async_set_locate_device(True)
        await client.async_set_locate_device(False)
        await client.async_pause_mining()
        await client.async_resume_mining()
        await client.async_restart_bosminer()
        await client.async_reboot_miner()
    finally:
        await client.async_close()

    credentials = [
        (request.username, request.password) for request in channel.login_requests
    ]
    assert credentials == [("user", "password")]
    assert [call.method for call in channel.calls] == [
        "/braiins.bos.v1.ActionsService/SetLocateDeviceStatus",
        "/braiins.bos.v1.ActionsService/SetLocateDeviceStatus",
        "/braiins.bos.v1.ActionsService/PauseMining",
        "/braiins.bos.v1.ActionsService/ResumeMining",
        "/braiins.bos.v1.ActionsService/Restart",
        "/braiins.bos.v1.ActionsService/Reboot",
    ]
    assert isinstance(
        channel.calls[0].request, actions_pb2.SetLocateDeviceStatusRequest
    )
    assert channel.calls[0].request.enable
    assert isinstance(
        channel.calls[1].request, actions_pb2.SetLocateDeviceStatusRequest
    )
    assert not channel.calls[1].request.enable
    assert isinstance(channel.calls[2].request, actions_pb2.PauseMiningRequest)
    assert isinstance(channel.calls[3].request, actions_pb2.ResumeMiningRequest)
    assert isinstance(channel.calls[4].request, actions_pb2.RestartRequest)
    assert isinstance(channel.calls[5].request, actions_pb2.RebootRequest)
    assert all(call.metadata == AUTH_METADATA for call in channel.calls)
    assert channel.closed


async def test_power_target_is_rounded_and_applied() -> None:
    """Power control rounds watts and requests save-and-apply behavior."""
    client, channel = create_client()

    try:
        await client.async_set_power_target(3_250.6)
    finally:
        await client.async_close()

    assert len(channel.login_requests) == 1
    assert len(channel.calls) == 1
    call = channel.calls[0]
    assert call.method == "/braiins.bos.v1.PerformanceService/SetPowerTarget"
    assert call.metadata == AUTH_METADATA
    assert isinstance(call.request, performance_pb2.SetPowerTargetRequest)
    assert call.request.save_action == common_pb2.SAVE_ACTION_SAVE_AND_APPLY
    assert call.request.power_target.watt == 3_251
    assert channel.closed
