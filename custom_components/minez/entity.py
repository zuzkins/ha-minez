"""Shared entity helpers for MineZ."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import MinezDataUpdateCoordinator


class MinezEntity(CoordinatorEntity[MinezDataUpdateCoordinator]):
    """Base entity for Braiins."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MinezDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.data["miner"]["uid"])},
            manufacturer=MANUFACTURER,
            name=coordinator.data["miner"]["hostname"] or coordinator.data["miner"]["model"],
            model=coordinator.data["miner"]["model"],
            sw_version=coordinator.data["miner"]["bos_version"],
            hw_version=coordinator.data["miner"]["platform"],
            serial_number=coordinator.data["miner"]["serial_number"],
        )

    @property
    def unique_base(self) -> str:
        """Return the base unique ID for the device."""
        return self.coordinator.data["miner"]["uid"]
