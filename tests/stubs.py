"""Stateful API stubs shared by Home Assistant entity tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

ACTIVE_POWER_TARGET = 2_300
CONFIGURED_POWER_TARGET = 3_500


class MinerApiStub:
    """Expose a complete miner snapshot and record control operations."""

    def __init__(self) -> None:
        self.configured_power_target = CONFIGURED_POWER_TARGET
        self.status = "Normal"
        self.set_power_targets: list[float] = []
        self.pause_requests = 0
        self.resume_requests = 0
        self.closed = False

    async def async_fetch_data(self) -> dict[str, Any]:
        """Return a complete snapshot for entity platform setup."""
        snapshot = {
            "api_version": "1.0.0",
            "miner": {
                "uid": "miner-uid",
                "hostname": "Miner",
                "mac_address": "00:11:22:33:44:55",
                "status": self.status,
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
                "mining_active": self.status == "Normal",
                "supports_mining_toggle": self.status in {"Normal", "Paused"},
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

    async def async_pause_mining(self) -> None:
        """Pause mining and update the next snapshot."""
        self.pause_requests += 1
        self.status = "Paused"

    async def async_resume_mining(self) -> None:
        """Resume mining and update the next snapshot."""
        self.resume_requests += 1
        self.status = "Normal"

    async def async_close(self) -> None:
        """Close the API stub."""
        self.closed = True
