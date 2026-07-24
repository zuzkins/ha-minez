"""Tests for MineZ API authentication."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from custom_components.minez.api import (
    MinezApiAuthError,
    MinezApiClient,
    MinezConnectionInfo,
)
from custom_components.minez.bos.v1 import (
    actions_pb2,
    authentication_pb2,
)

OLD_TOKEN = "old-token"
FRESH_TOKEN = "fresh-token"


class MinerChannelStub:
    """Stateful gRPC channel stub for the miner services used by the test."""

    def __init__(self) -> None:
        self.current_token = OLD_TOKEN
        self.expired_token: str | None = None
        self.login_requests: list[tuple[str, str]] = []
        self.action_tokens: list[str | None] = []
        self.stale_call_count = 0
        self.two_stale_calls_arrived = asyncio.Event()
        self.fresh_retry_arrived = asyncio.Event()
        self.closed = False

    def unary_unary(
        self,
        method: str,
        **_kwargs: Any,
    ) -> Callable[..., Awaitable[Any]]:
        """Return a stub call for a generated unary RPC."""
        if method == "/braiins.bos.v1.AuthenticationService/Login":
            return self._login
        if method == "/braiins.bos.v1.ActionsService/GetLocateDeviceStatus":
            return self._get_locate_device_status
        return self._unexpected_call

    async def _login(
        self,
        request: authentication_pb2.LoginRequest,
        **_kwargs: Any,
    ) -> authentication_pb2.LoginResponse:
        """Return the currently valid session token."""
        self.login_requests.append((request.username, request.password))
        return authentication_pb2.LoginResponse(token=self.current_token)

    async def _get_locate_device_status(
        self,
        _request: actions_pb2.GetLocateDeviceStatusRequest,
        metadata: tuple[tuple[str, str], ...] | None = None,
    ) -> actions_pb2.LocateDeviceStatusResponse:
        """Reject stale sessions and accept the refreshed session."""
        token = dict(metadata or ()).get("authorization")
        self.action_tokens.append(token)

        if token == self.expired_token:
            self.stale_call_count += 1
            if self.stale_call_count == 1:
                await self.two_stale_calls_arrived.wait()
            else:
                self.two_stale_calls_arrived.set()
                await self.fresh_retry_arrived.wait()
            raise MinezApiAuthError("session expired")

        if token == self.current_token:
            if self.expired_token is not None:
                self.fresh_retry_arrived.set()
            return actions_pb2.LocateDeviceStatusResponse(enabled=True)

        raise MinezApiAuthError("missing or invalid session")

    async def _unexpected_call(self, _request: Any, **_kwargs: Any) -> Any:
        """Fail if the client invokes an RPC outside this test's scope."""
        raise AssertionError("Unexpected RPC call")

    def expire_token(self) -> None:
        """Expire the current token and rotate to a new token."""
        self.expired_token = self.current_token
        self.current_token = FRESH_TOKEN

    async def close(self) -> None:
        """Close the channel stub."""
        self.closed = True


async def test_concurrent_stale_calls_refresh_session_once() -> None:
    """Concurrent stale calls share one refreshed session token."""
    channel_stub = MinerChannelStub()
    client = MinezApiClient(
        MinezConnectionInfo(
            host="miner.local",
            username="user",
            password="password",
            timeout=5,
        )
    )
    client._channel = channel_stub  # type: ignore[assignment]

    try:
        initial_response = await client._get_locate_device_status()
        assert initial_response.enabled
        assert channel_stub.login_requests == [("user", "password")]

        channel_stub.login_requests.clear()
        channel_stub.expire_token()
        channel_stub.action_tokens.clear()

        async with asyncio.timeout(10):
            responses = await asyncio.gather(
                client._get_locate_device_status(),
                client._get_locate_device_status(),
            )

        assert all(response.enabled for response in responses)
        assert channel_stub.login_requests == [("user", "password")]
        assert channel_stub.stale_call_count == 2
        assert channel_stub.action_tokens.count(OLD_TOKEN) == 2
        assert channel_stub.action_tokens.count(FRESH_TOKEN) == 2
    finally:
        await client.async_close()

    assert channel_stub.closed
