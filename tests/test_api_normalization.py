"""Tests for normalization of Braiins API responses."""

from __future__ import annotations

from typing import Any

from google.protobuf.wrappers_pb2 import UInt32Value

from custom_components.minez.api import MinezApiClient, MinezConnectionInfo
from custom_components.minez.bos.v1 import (
    actions_pb2,
    configuration_pb2,
    constraints_pb2,
    cooling_pb2,
    miner_pb2,
    performance_pb2,
    pool_pb2,
    units_pb2,
    work_pb2,
)


def normalize_snapshot(**overrides: Any) -> dict[str, Any]:
    """Normalize real protobuf messages with sparse defaults."""
    inputs = {
        "api_version": "2.1.0",
        "details": miner_pb2.GetMinerDetailsResponse(),
        "stats": miner_pb2.GetMinerStatsResponse(),
        "cooling": cooling_pb2.GetCoolingStateResponse(),
        "tuner": performance_pb2.GetTunerStateResponse(),
        "locate": actions_pb2.LocateDeviceStatusResponse(),
        "errors": miner_pb2.GetErrorsResponse(),
        "configuration": configuration_pb2.GetMinerConfigurationResponse(),
        "constraints": configuration_pb2.GetConstraintsResponse(),
        "status": None,
        "hashboards": miner_pb2.GetHashboardsResponse(),
    }
    inputs.update(overrides)
    client = MinezApiClient(MinezConnectionInfo(host="unused"))
    return client._normalize_snapshot(**inputs)


def test_normalize_miner_telemetry() -> None:
    """Normalize identity, aggregate telemetry, cooling and constraints."""
    details = miner_pb2.GetMinerDetailsResponse(
        uid="miner-uid",
        miner_identity=miner_pb2.MinerIdentity(
            brand=miner_pb2.MINER_BRAND_ANTMINER,
            model=miner_pb2.MINER_MODEL_ANTMINER_S19_PRO,
            name="Antminer S19 Pro",
            miner_model="S19 Pro",
        ),
        platform=miner_pb2.PLATFORM_CVITEK_BM1_AM2,
        bos_mode=miner_pb2.BOS_MODE_NAND,
        bos_version=miner_pb2.BosVersion(current="24.04.1"),
        hostname="miner-01",
        mac_address="00:11:22:33:44:55",
        sticker_hashrate=units_pb2.GigaHashrate(gigahash_per_second=110_000),
        bosminer_uptime_s=3_600,
        system_uptime_s=7_200,
        status=miner_pb2.MINER_STATUS_PAUSED,
        kernel_version="5.10.0",
        control_board_soc_family=miner_pb2.CONTROL_BOARD_SOC_FAMILY_CVITEK,
        serial_number="SN123",
    )
    stats = miner_pb2.GetMinerStatsResponse(
        pool_stats=pool_pb2.PoolStats(
            accepted_shares=100,
            rejected_shares=2,
            stale_shares=3,
            best_share=5_000,
        ),
        miner_stats=work_pb2.WorkSolverStats(
            real_hashrate=work_pb2.RealHashrate(
                last_5m=units_pb2.GigaHashrate(gigahash_per_second=101_250),
                last_15m=units_pb2.GigaHashrate(gigahash_per_second=100_500),
                last_24h=units_pb2.GigaHashrate(gigahash_per_second=99_000),
                since_restart=units_pb2.GigaHashrate(
                    gigahash_per_second=98_500
                ),
            ),
            nominal_hashrate=units_pb2.GigaHashrate(
                gigahash_per_second=110_000
            ),
            error_hashrate=units_pb2.MegaHashrate(megahash_per_second=12.5),
            found_blocks=1,
            best_share=6_000,
        ),
        power_stats=miner_pb2.MinerPowerStats(
            approximated_consumption=units_pb2.Power(watt=3_250),
            efficiency=units_pb2.PowerEfficiency(joule_per_terahash=29.55),
        ),
    )
    cooling = cooling_pb2.GetCoolingStateResponse(
        fans=[
            cooling_pb2.FanState(
                position=3,
                rpm=6_000,
                target_speed_ratio=0.8,
            ),
            cooling_pb2.FanState(rpm=5_500),
        ],
        highest_temperature=cooling_pb2.TemperatureSensor(
            location=cooling_pb2.SENSOR_LOCATION_CHIP,
            temperature=units_pb2.Temperature(degree_c=78.5),
        ),
    )
    tuner = performance_pb2.GetTunerStateResponse(
        overall_tuner_state=performance_pb2.TUNER_STATE_STABLE,
        power_target_mode_state=performance_pb2.PowerTargetModeState(
            current_target=units_pb2.Power(watt=3_200)
        ),
    )
    constraints = configuration_pb2.GetConstraintsResponse(
        tuner_constraints=performance_pb2.TunerConstraints(
            power_target=constraints_pb2.PowerConstraints(
                min=units_pb2.Power(watt=2_000),
                max=units_pb2.Power(watt=4_000),
            )
        )
    )
    configuration = configuration_pb2.GetMinerConfigurationResponse(
        tuner=performance_pb2.TunerConfiguration(
            power_target=units_pb2.Power(watt=3_500)
        )
    )

    result = normalize_snapshot(
        api_version="2.3.1-rc1+abc",
        details=details,
        stats=stats,
        cooling=cooling,
        tuner=tuner,
        locate=actions_pb2.LocateDeviceStatusResponse(enabled=True),
        errors=miner_pb2.GetErrorsResponse(
            errors=[
                miner_pb2.MinerError(message="Fan 2 is slow"),
                miner_pb2.MinerError(message="Board warning"),
            ]
        ),
        configuration=configuration,
        constraints=constraints,
        status=miner_pb2.MinerStatus.Name(miner_pb2.MINER_STATUS_NORMAL),
    )

    assert result["api_version"] == "2.3.1-rc1+abc"
    assert result["miner"] == {
        "uid": "miner-uid",
        "hostname": "miner-01",
        "mac_address": "00:11:22:33:44:55",
        "status": "Normal",
        "brand": "MINER_BRAND_ANTMINER",
        "model": "S19 Pro",
        "name": "Antminer S19 Pro",
        "platform": "PLATFORM_CVITEK_BM1_AM2",
        "control_board_soc_family": "CONTROL_BOARD_SOC_FAMILY_CVITEK",
        "bos_mode": "BOS_MODE_NAND",
        "bos_version": "24.04.1",
        "kernel_version": "5.10.0",
        "serial_number": "SN123",
        "system_uptime_s": 7_200,
        "bosminer_uptime_s": 3_600,
        "sticker_hashrate_ths": 110.0,
    }
    assert result["stats"] == {
        "hashrate_5m_ths": 101.25,
        "hashrate_15m_ths": 100.5,
        "hashrate_24h_ths": 99.0,
        "hashrate_since_restart_ths": 98.5,
        "nominal_hashrate_ths": 110.0,
        "error_hashrate_mhs": 12.5,
        "power_w": 3_250,
        "efficiency_jth": 29.55,
        "accepted_shares": 100,
        "rejected_shares": 2,
        "stale_shares": 3,
        "best_share": 6_000,
        "found_blocks": 1,
    }
    assert result["cooling"] == {
        "highest_temp_c": 78.5,
        "fan_count": 2,
        "fan_rpm_avg": 5_750.0,
        "fans": [
            {"position": 3, "rpm": 6_000, "target_speed_ratio": 0.8},
            {"position": 2, "rpm": 5_500, "target_speed_ratio": None},
        ],
    }
    assert result["performance"] == {
        "tuner_state": "Stable",
        "mode_state": "power_target_mode_state",
        "power_target_w": 3_200,
        "configured_power_target_w": 3_500,
        "hashrate_target_ths": None,
        "power_target_min_w": 2_000,
        "power_target_max_w": 4_000,
    }
    assert result["controls"] == {
        "locate_device_enabled": True,
        "supports_power_target": True,
        "mining_active": True,
        "supports_mining_toggle": True,
    }
    assert result["errors"] == {
        "count": 2,
        "messages": ["Fan 2 is slow", "Board warning"],
    }
    assert result["diagnostics"]["details"]["uid"] == "miner-uid"


def test_normalize_hashboard_telemetry() -> None:
    """Normalize per-board telemetry and hashrate-target tuning."""
    board = miner_pb2.Hashboard(
        id="board-a",
        enabled=True,
        chips_count=UInt32Value(value=76),
        current_voltage=units_pb2.Voltage(volt=14.25),
        current_frequency=units_pb2.Frequency(hertz=650_000_000),
        highest_chip_temp=cooling_pb2.TemperatureSensor(
            temperature=units_pb2.Temperature(degree_c=82.5)
        ),
        board_temp=units_pb2.Temperature(degree_c=65.0),
        lowest_inlet_temp=units_pb2.Temperature(degree_c=24.5),
        highest_outlet_temp=units_pb2.Temperature(degree_c=48.25),
        stats=work_pb2.WorkSolverStats(
            real_hashrate=work_pb2.RealHashrate(
                last_5m=units_pb2.GigaHashrate(gigahash_per_second=35_250),
                last_15m=units_pb2.GigaHashrate(gigahash_per_second=35_000),
                last_24h=units_pb2.GigaHashrate(gigahash_per_second=34_500),
            ),
            nominal_hashrate=units_pb2.GigaHashrate(
                gigahash_per_second=36_000
            ),
            error_hashrate=units_pb2.MegaHashrate(megahash_per_second=4.5),
            best_share=777,
            found_blocks=2,
        ),
        model="HB-S19",
        serial_number="HB123",
        board_name="Chain 0",
        chip_type="BM1398",
    )
    tuner = performance_pb2.GetTunerStateResponse(
        overall_tuner_state=performance_pb2.TUNER_STATE_TUNING,
        hashrate_target_mode_state=performance_pb2.HashrateTargetModeState(
            current_target=units_pb2.TeraHashrate(terahash_per_second=105.5)
        ),
    )

    result = normalize_snapshot(
        tuner=tuner,
        hashboards=miner_pb2.GetHashboardsResponse(hashboards=[board]),
    )

    assert result["performance"] == {
        "tuner_state": "Tuning",
        "mode_state": "hashrate_target_mode_state",
        "power_target_w": None,
        "configured_power_target_w": None,
        "hashrate_target_ths": 105.5,
        "power_target_min_w": None,
        "power_target_max_w": None,
    }
    assert result["hashboards"] == {
        "count": 1,
        "items": [
            {
                "id": "board-a",
                "index": 1,
                "enabled": True,
                "chips_count": 76,
                "voltage_v": 14.25,
                "frequency_mhz": 650.0,
                "highest_chip_temp_c": 82.5,
                "board_temp_c": 65.0,
                "inlet_temp_c": 24.5,
                "outlet_temp_c": 48.25,
                "hashrate_5m_ths": 35.25,
                "hashrate_15m_ths": 35.0,
                "hashrate_24h_ths": 34.5,
                "nominal_hashrate_ths": 36.0,
                "error_hashrate_mhs": 4.5,
                "best_share": 777,
                "found_blocks": 2,
                "model": "HB-S19",
                "serial_number": "HB123",
                "board_name": "Chain 0",
                "chip_type": "BM1398",
            }
        ],
    }


def test_normalize_unknown_enum_values() -> None:
    """Unknown firmware enum values do not prevent snapshot normalization."""
    details = miner_pb2.GetMinerDetailsResponse(
        uid="future-miner",
        status=999,
        platform=998,
        bos_mode=997,
        control_board_soc_family=996,
        miner_identity=miner_pb2.MinerIdentity(
            brand=995,
            model=994,
            miner_model="FutureMiner X1",
        ),
    )
    tuner = performance_pb2.GetTunerStateResponse(overall_tuner_state=993)

    result = normalize_snapshot(details=details, tuner=tuner)

    assert result["miner"]["uid"] == "future-miner"
    assert result["miner"]["model"] == "FutureMiner X1"
    assert result["miner"]["status"] is None
    assert result["miner"]["brand"] is None
    assert result["miner"]["platform"] is None
    assert result["miner"]["bos_mode"] is None
    assert result["miner"]["control_board_soc_family"] is None
    assert result["performance"]["tuner_state"] is None
    assert not result["controls"]["mining_active"]
    assert not result["controls"]["supports_mining_toggle"]


def test_normalize_paused_miner_supports_mining_toggle() -> None:
    """A paused miner can be represented as an off mining switch."""
    result = normalize_snapshot(status="MINER_STATUS_PAUSED")

    assert not result["controls"]["mining_active"]
    assert result["controls"]["supports_mining_toggle"]
