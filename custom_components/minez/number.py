"""Number platform for MineZ."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MinezDataUpdateCoordinator
from .entity import MinezEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MineZ numbers."""
    coordinator: MinezDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([MinezPowerTargetNumber(coordinator)])


class MinezPowerTargetNumber(MinezEntity, NumberEntity):
    """Writable power target."""

    _attr_translation_key = "power_target_number"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator: MinezDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.unique_base}_power_target"

    @property
    def available(self) -> bool:
        """Return availability."""
        return super().available and self.coordinator.data["controls"]["supports_power_target"]

    @property
    def native_value(self) -> float | None:
        """Return the configured power target."""
        return self.coordinator.data["performance"]["configured_power_target_w"]

    @property
    def native_min_value(self) -> float:
        """Return min value."""
        return float(self.coordinator.data["performance"]["power_target_min_w"] or 0)

    @property
    def native_max_value(self) -> float:
        """Return max value."""
        return float(self.coordinator.data["performance"]["power_target_max_w"] or 0)

    @property
    def native_step(self) -> float:
        """Return the step size."""
        return 1.0

    async def async_set_native_value(self, value: float) -> None:
        """Set a new power target."""
        await self.coordinator.client.async_set_power_target(value)
        await self.coordinator.async_request_refresh()
