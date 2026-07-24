"""Async client for the MineZ gRPC API."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any

# Reduce noisy gRPC C-core logging in the Home Assistant process.
os.environ.setdefault("GRPC_ENABLE_FORK_SUPPORT", "false")
os.environ.setdefault("GRPC_VERBOSITY", "ERROR")

import grpc
from google.protobuf.json_format import MessageToDict
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME

from custom_components.minez.bos import version_pb2, version_pb2_grpc
from custom_components.minez.bos.v1 import (
    actions_pb2,
    actions_pb2_grpc,
    authentication_pb2,
    authentication_pb2_grpc,
    common_pb2,
    configuration_pb2,
    configuration_pb2_grpc,
    cooling_pb2,
    cooling_pb2_grpc,
    miner_pb2,
    miner_pb2_grpc,
    performance_pb2,
    performance_pb2_grpc,
    units_pb2,
)

from .const import DEFAULT_PORT, DEFAULT_TIMEOUT


class MinezApiError(Exception):
    """Base Braiins API error."""


class MinezApiConnectionError(MinezApiError):
    """Connection error talking to the miner."""


class MinezApiAuthError(MinezApiError):
    """Authentication error talking to the miner."""


def _enum_name(message: Any, field_name: str) -> str | None:
    value = getattr(message, field_name, None)
    if value is None:
        return None

    try:
        enum_descriptor = message.DESCRIPTOR.fields_by_name[field_name].enum_type
    except KeyError:
        return None

    enum_value = enum_descriptor.values_by_number.get(value)
    return enum_value.name if enum_value else None


def _humanize_enum_name(value: str | None, *, prefixes: tuple[str, ...] = ()) -> str | None:
    """Convert protobuf enum names into readable labels."""
    if value is None:
        return None

    normalized = value
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized.removeprefix(prefix)
            break

    return normalized.replace("_", " ").title()


def _message_to_dict(message: Any) -> dict[str, Any]:
    return MessageToDict(
        message,
        preserving_proto_field_name=True,
        always_print_fields_with_no_presence=False,
    )


def _ghs(message: Any | None) -> float | None:
    if message is None:
        return None
    return getattr(message, "gigahash_per_second", None)


def _mhs(message: Any | None) -> float | None:
    if message is None:
        return None
    return getattr(message, "megahash_per_second", None)


def _ths(message: Any | None) -> float | None:
    if message is None:
        return None
    return getattr(message, "terahash_per_second", None)


def _temperature(message: Any | None) -> float | None:
    if message is None:
        return None
    return getattr(message, "degree_c", None)


def _watt(message: Any | None) -> int | None:
    if message is None:
        return None
    return getattr(message, "watt", None)


def _efficiency(message: Any | None) -> float | None:
    if message is None:
        return None
    return getattr(message, "joule_per_terahash", None)


@dataclass(slots=True)
class MinezConnectionInfo:
    """Connection parameters for the miner."""

    host: str
    port: int = DEFAULT_PORT
    username: str = ""
    password: str = ""
    timeout: int = DEFAULT_TIMEOUT

    @property
    def endpoint(self) -> str:
        """Return the gRPC endpoint."""
        return f"{self.host}:{self.port}"


class MinezApiClient:
    """Async MineZ gRPC API client."""

    def __init__(self, info: MinezConnectionInfo) -> None:
        self._info = info
        self._channel: grpc.aio.Channel | None = None
        self._token: str | None = None
        self._token_lock = asyncio.Lock()

    @classmethod
    def from_config_entry(cls, entry: ConfigEntry) -> "MinezApiClient":
        """Create a client from a config entry."""
        return cls(
            MinezConnectionInfo(
                host=entry.data[CONF_HOST],
                port=entry.data.get(CONF_PORT, DEFAULT_PORT),
                username=entry.data.get(CONF_USERNAME, ""),
                password=entry.data.get(CONF_PASSWORD, ""),
            )
        )

    async def async_close(self) -> None:
        """Close the gRPC channel."""
        if self._channel is not None:
            await self._channel.close()
            self._channel = None

    async def async_validate(self) -> dict[str, Any]:
        """Validate connectivity and credentials."""
        api_version = await self._get_api_version()
        if self._info.username:
            await self._ensure_token()
        details = await self._get_miner_details()

        return {
            "api_version": api_version,
            "uid": details.uid,
            "hostname": details.hostname,
            "model": details.miner_identity.miner_model or details.miner_identity.name,
        }

    async def async_fetch_data(self) -> dict[str, Any]:
        """Fetch a normalized snapshot for Home Assistant."""
        if self._info.username:
            await self._ensure_token()

        (
            api_version,
            details,
            stats,
            cooling,
            tuner,
            locate,
            errors,
            configuration,
            constraints,
            status,
            hashboards,
        ) = await asyncio.gather(
            self._get_api_version(),
            self._get_miner_details(),
            self._get_miner_stats(),
            self._get_cooling_state(),
            self._get_tuner_state(),
            self._get_locate_device_status(),
            self._get_errors(),
            self._get_miner_configuration(),
            self._get_constraints(),
            self._get_miner_status(),
            self._get_hashboards(),
        )

        return self._normalize_snapshot(
            api_version=api_version,
            details=details,
            stats=stats,
            cooling=cooling,
            tuner=tuner,
            locate=locate,
            errors=errors,
            configuration=configuration,
            constraints=constraints,
            status=status,
            hashboards=hashboards,
        )

    async def async_set_locate_device(self, enabled: bool) -> None:
        """Enable or disable locate mode."""
        await self._call_with_auth(
            actions_pb2_grpc.ActionsServiceStub,
            "SetLocateDeviceStatus",
            actions_pb2.SetLocateDeviceStatusRequest(enable=enabled),
        )

    async def async_pause_mining(self) -> None:
        """Pause mining."""
        await self._call_with_auth(
            actions_pb2_grpc.ActionsServiceStub,
            "PauseMining",
            actions_pb2.PauseMiningRequest(),
        )

    async def async_resume_mining(self) -> None:
        """Resume mining."""
        await self._call_with_auth(
            actions_pb2_grpc.ActionsServiceStub,
            "ResumeMining",
            actions_pb2.ResumeMiningRequest(),
        )

    async def async_restart_bosminer(self) -> None:
        """Restart bosminer."""
        await self._call_with_auth(
            actions_pb2_grpc.ActionsServiceStub,
            "Restart",
            actions_pb2.RestartRequest(),
        )

    async def async_reboot_miner(self) -> None:
        """Reboot the miner."""
        await self._call_with_auth(
            actions_pb2_grpc.ActionsServiceStub,
            "Reboot",
            actions_pb2.RebootRequest(),
        )

    async def async_set_power_target(self, watts: float) -> None:
        """Set the miner power target."""
        await self._call_with_auth(
            performance_pb2_grpc.PerformanceServiceStub,
            "SetPowerTarget",
            performance_pb2.SetPowerTargetRequest(
                save_action=common_pb2.SAVE_ACTION_SAVE_AND_APPLY,
                power_target=units_pb2.Power(watt=round(watts)),
            ),
        )

    async def _ensure_channel(self) -> grpc.aio.Channel:
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(self._info.endpoint)
        return self._channel

    async def _ensure_token(self) -> str:
        if self._token:
            return self._token

        async with self._token_lock:
            if self._token:
                return self._token

            channel = await self._ensure_channel()
            stub = authentication_pb2_grpc.AuthenticationServiceStub(channel)

            try:
                response = await asyncio.wait_for(
                    stub.Login(
                        authentication_pb2.LoginRequest(
                            username=self._info.username,
                            password=self._info.password,
                        )
                    ),
                    timeout=self._info.timeout,
                )
            except grpc.aio.AioRpcError as err:
                raise self._translate_error(err) from err
            except asyncio.TimeoutError as err:
                raise MinezApiConnectionError("Login timed out") from err

            self._token = response.token
            return self._token

    async def _call(
        self,
        stub_factory: Any,
        method_name: str,
        request: Any,
        *,
        metadata: tuple[tuple[str, str], ...] | None = None,
    ) -> Any:
        channel = await self._ensure_channel()
        stub = stub_factory(channel)
        method = getattr(stub, method_name)

        try:
            return await asyncio.wait_for(
                method(request, metadata=metadata),
                timeout=self._info.timeout,
            )
        except grpc.aio.AioRpcError as err:
            raise self._translate_error(err) from err
        except asyncio.TimeoutError as err:
            raise MinezApiConnectionError(f"{method_name} timed out") from err

    async def _call_with_auth(
        self, stub_factory: Any, method_name: str, request: Any
    ) -> Any:
        token = await self._ensure_token()
        metadata = (("authorization", token),)

        try:
            return await self._call(
                stub_factory, method_name, request, metadata=metadata
            )
        except MinezApiAuthError:
            if self._token == token:
                self._token = None
            token = await self._ensure_token()
            return await self._call(
                stub_factory,
                method_name,
                request,
                metadata=(("authorization", token),),
            )

    async def _get_api_version(self) -> str:
        response = await self._call(
            version_pb2_grpc.ApiVersionServiceStub,
            "GetApiVersion",
            version_pb2.ApiVersionRequest(),
        )
        parts = [str(response.major), str(response.minor), str(response.patch)]
        version = ".".join(parts)
        if response.pre:
            version = f"{version}-{response.pre}"
        if response.build:
            version = f"{version}+{response.build}"
        return version

    async def _get_miner_status(self) -> str | None:
        token = await self._ensure_token()

        try:
            response = await self._read_miner_status(token)
        except MinezApiAuthError:
            if self._token == token:
                self._token = None
            token = await self._ensure_token()
            response = await self._read_miner_status(token)

        return _enum_name(response, "status") if response else None

    async def _read_miner_status(self, token: str) -> Any:
        """Read one status update using the provided session token."""
        channel = await self._ensure_channel()
        stub = miner_pb2_grpc.MinerServiceStub(channel)
        call = stub.GetMinerStatus(
            miner_pb2.GetMinerStatusRequest(),
            metadata=(("authorization", token),),
        )

        try:
            return await asyncio.wait_for(call.read(), timeout=self._info.timeout)
        except grpc.aio.AioRpcError as err:
            raise self._translate_error(err) from err
        except asyncio.TimeoutError as err:
            raise MinezApiConnectionError("GetMinerStatus timed out") from err
        finally:
            call.cancel()

    async def _get_miner_details(self) -> Any:
        return await self._call_with_auth(
            miner_pb2_grpc.MinerServiceStub,
            "GetMinerDetails",
            miner_pb2.GetMinerDetailsRequest(),
        )

    async def _get_miner_stats(self) -> Any:
        return await self._call_with_auth(
            miner_pb2_grpc.MinerServiceStub,
            "GetMinerStats",
            miner_pb2.GetMinerStatsRequest(),
        )

    async def _get_errors(self) -> Any:
        return await self._call_with_auth(
            miner_pb2_grpc.MinerServiceStub,
            "GetErrors",
            miner_pb2.GetErrorsRequest(),
        )

    async def _get_hashboards(self) -> Any:
        return await self._call_with_auth(
            miner_pb2_grpc.MinerServiceStub,
            "GetHashboards",
            miner_pb2.GetHashboardsRequest(),
        )

    async def _get_cooling_state(self) -> Any:
        return await self._call_with_auth(
            cooling_pb2_grpc.CoolingServiceStub,
            "GetCoolingState",
            cooling_pb2.GetCoolingStateRequest(),
        )

    async def _get_tuner_state(self) -> Any:
        return await self._call_with_auth(
            performance_pb2_grpc.PerformanceServiceStub,
            "GetTunerState",
            performance_pb2.GetTunerStateRequest(),
        )

    async def _get_locate_device_status(self) -> Any:
        return await self._call_with_auth(
            actions_pb2_grpc.ActionsServiceStub,
            "GetLocateDeviceStatus",
            actions_pb2.GetLocateDeviceStatusRequest(),
        )

    async def _get_miner_configuration(self) -> Any:
        return await self._call_with_auth(
            configuration_pb2_grpc.ConfigurationServiceStub,
            "GetMinerConfiguration",
            configuration_pb2.GetMinerConfigurationRequest(),
        )

    async def _get_constraints(self) -> Any:
        return await self._call_with_auth(
            configuration_pb2_grpc.ConfigurationServiceStub,
            "GetConstraints",
            configuration_pb2.GetConstraintsRequest(),
        )

    def _normalize_snapshot(
        self,
        *,
        api_version: str,
        details: Any,
        stats: Any,
        cooling: Any,
        tuner: Any,
        locate: Any,
        errors: Any,
        configuration: Any,
        constraints: Any,
        status: str | None,
        hashboards: Any,
    ) -> dict[str, Any]:
        miner_status = _humanize_enum_name(
            status or _enum_name(details, "status"),
            prefixes=("MINER_STATUS_",),
        )
        tuner_state = _humanize_enum_name(
            _enum_name(tuner, "overall_tuner_state"),
            prefixes=("TUNER_STATE_",),
        )
        mode_state_name = tuner.WhichOneof("mode_state")
        power_target = None
        hashrate_target = None

        if mode_state_name == "power_target_mode_state":
            power_target = _watt(tuner.power_target_mode_state.current_target)
        if mode_state_name == "hashrate_target_mode_state":
            hashrate_target = _ths(tuner.hashrate_target_mode_state.current_target)

        configured_power_target = None
        if configuration.HasField("tuner") and configuration.tuner.HasField(
            "power_target"
        ):
            configured_power_target = _watt(configuration.tuner.power_target)

        min_power_target = None
        max_power_target = None
        if constraints.HasField("tuner_constraints"):
            power_constraints = constraints.tuner_constraints.power_target
            min_power_target = _watt(power_constraints.min)
            max_power_target = _watt(power_constraints.max)

        fan_rpms = [fan.rpm for fan in cooling.fans]
        error_messages = [error.message for error in errors.errors]
        hashboard_items: list[dict[str, Any]] = []

        for index, hashboard in enumerate(hashboards.hashboards, start=1):
            hashboard_items.append(
                {
                    "id": hashboard.id,
                    "index": index,
                    "enabled": hashboard.enabled,
                    "chips_count": hashboard.chips_count.value
                    if hashboard.HasField("chips_count")
                    else None,
                    "voltage_v": getattr(hashboard.current_voltage, "volt", None),
                    "frequency_mhz": (
                        getattr(hashboard.current_frequency, "hertz", None) / 1_000_000
                        if getattr(hashboard.current_frequency, "hertz", None) is not None
                        else None
                    ),
                    "highest_chip_temp_c": _temperature(hashboard.highest_chip_temp.temperature),
                    "board_temp_c": _temperature(hashboard.board_temp),
                    "inlet_temp_c": _temperature(hashboard.lowest_inlet_temp),
                    "outlet_temp_c": _temperature(hashboard.highest_outlet_temp),
                    "hashrate_5m_ths": _ghs(hashboard.stats.real_hashrate.last_5m) / 1000
                    if _ghs(hashboard.stats.real_hashrate.last_5m) is not None
                    else None,
                    "hashrate_15m_ths": _ghs(hashboard.stats.real_hashrate.last_15m) / 1000
                    if _ghs(hashboard.stats.real_hashrate.last_15m) is not None
                    else None,
                    "hashrate_24h_ths": _ghs(hashboard.stats.real_hashrate.last_24h) / 1000
                    if _ghs(hashboard.stats.real_hashrate.last_24h) is not None
                    else None,
                    "nominal_hashrate_ths": _ghs(hashboard.stats.nominal_hashrate) / 1000
                    if _ghs(hashboard.stats.nominal_hashrate) is not None
                    else None,
                    "error_hashrate_mhs": _mhs(hashboard.stats.error_hashrate),
                    "best_share": hashboard.stats.best_share,
                    "found_blocks": hashboard.stats.found_blocks,
                    "model": hashboard.model if hashboard.HasField("model") else None,
                    "serial_number": hashboard.serial_number if hashboard.HasField("serial_number") else None,
                    "board_name": hashboard.board_name if hashboard.HasField("board_name") else None,
                    "chip_type": hashboard.chip_type if hashboard.HasField("chip_type") else None,
                }
            )

        return {
            "api_version": api_version,
            "miner": {
                "uid": details.uid,
                "hostname": details.hostname,
                "mac_address": details.mac_address,
                "status": miner_status,
                "brand": _enum_name(details.miner_identity, "brand"),
                "model": details.miner_identity.miner_model or details.miner_identity.name,
                "name": details.miner_identity.name,
                "platform": _enum_name(details, "platform"),
                "control_board_soc_family": _enum_name(details, "control_board_soc_family"),
                "bos_mode": _enum_name(details, "bos_mode"),
                "bos_version": details.bos_version.current,
                "kernel_version": details.kernel_version,
                "serial_number": details.serial_number if details.HasField("serial_number") else None,
                "system_uptime_s": details.system_uptime_s,
                "bosminer_uptime_s": details.bosminer_uptime_s,
                "sticker_hashrate_ths": _ghs(details.sticker_hashrate) / 1000
                if _ghs(details.sticker_hashrate) is not None
                else None,
            },
            "stats": {
                "hashrate_5m_ths": _ghs(stats.miner_stats.real_hashrate.last_5m) / 1000
                if _ghs(stats.miner_stats.real_hashrate.last_5m) is not None
                else None,
                "hashrate_15m_ths": _ghs(stats.miner_stats.real_hashrate.last_15m) / 1000
                if _ghs(stats.miner_stats.real_hashrate.last_15m) is not None
                else None,
                "hashrate_24h_ths": _ghs(stats.miner_stats.real_hashrate.last_24h) / 1000
                if _ghs(stats.miner_stats.real_hashrate.last_24h) is not None
                else None,
                "hashrate_since_restart_ths": _ghs(stats.miner_stats.real_hashrate.since_restart) / 1000
                if _ghs(stats.miner_stats.real_hashrate.since_restart) is not None
                else None,
                "nominal_hashrate_ths": _ghs(stats.miner_stats.nominal_hashrate) / 1000
                if _ghs(stats.miner_stats.nominal_hashrate) is not None
                else None,
                "error_hashrate_mhs": _mhs(stats.miner_stats.error_hashrate),
                "power_w": _watt(stats.power_stats.approximated_consumption),
                "efficiency_jth": _efficiency(stats.power_stats.efficiency),
                "accepted_shares": stats.pool_stats.accepted_shares,
                "rejected_shares": stats.pool_stats.rejected_shares,
                "stale_shares": stats.pool_stats.stale_shares,
                "best_share": max(stats.pool_stats.best_share, stats.miner_stats.best_share),
                "found_blocks": stats.miner_stats.found_blocks,
            },
            "cooling": {
                "highest_temp_c": _temperature(cooling.highest_temperature.temperature),
                "fan_count": len(cooling.fans),
                "fan_rpm_avg": round(sum(fan_rpms) / len(fan_rpms), 2) if fan_rpms else None,
                "fans": [
                    {
                        "position": fan.position if fan.HasField("position") else index,
                        "rpm": fan.rpm,
                        "target_speed_ratio": fan.target_speed_ratio
                        if fan.HasField("target_speed_ratio")
                        else None,
                    }
                    for index, fan in enumerate(cooling.fans, start=1)
                ],
            },
            "performance": {
                "tuner_state": tuner_state,
                "mode_state": mode_state_name,
                "power_target_w": power_target,
                "configured_power_target_w": configured_power_target,
                "hashrate_target_ths": hashrate_target,
                "power_target_min_w": min_power_target,
                "power_target_max_w": max_power_target,
            },
            "controls": {
                "locate_device_enabled": locate.enabled,
                "supports_power_target": min_power_target is not None and max_power_target is not None,
            },
            "errors": {
                "count": len(errors.errors),
                "messages": error_messages,
            },
            "hashboards": {
                "count": len(hashboard_items),
                "items": hashboard_items,
            },
            "diagnostics": {
                "details": _message_to_dict(details),
                "stats": _message_to_dict(stats),
                "cooling": _message_to_dict(cooling),
                "tuner": _message_to_dict(tuner),
                "configuration": _message_to_dict(configuration),
                "constraints": _message_to_dict(constraints),
                "hashboards": _message_to_dict(hashboards),
            },
        }

    def _translate_error(self, err: grpc.aio.AioRpcError) -> MinezApiError:
        code = err.code()
        if code in (grpc.StatusCode.UNAUTHENTICATED, grpc.StatusCode.PERMISSION_DENIED):
            return MinezApiAuthError(err.details() or "Authentication failed")
        if code in (
            grpc.StatusCode.UNAVAILABLE,
            grpc.StatusCode.DEADLINE_EXCEEDED,
            grpc.StatusCode.UNKNOWN,
        ):
            return MinezApiConnectionError(err.details() or code.name)
        return MinezApiError(err.details() or code.name)
