"""Switch platform for MineZ."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
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
    """Set up MineZ switches."""
    coordinator: MinezDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        [MinezLocateSwitch(coordinator), MinezMiningSwitch(coordinator)]
    )


class MinezLocateSwitch(MinezEntity, SwitchEntity):
    """Switch for locate-device mode."""

    _attr_translation_key = "locate_device"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: MinezDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.unique_base}_locate_device"

    @property
    def is_on(self) -> bool:
        """Return whether locate mode is enabled."""
        return self.coordinator.data["controls"]["locate_device_enabled"]

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the entity on."""
        await self.coordinator.client.async_set_locate_device(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the entity off."""
        await self.coordinator.client.async_set_locate_device(False)
        await self.coordinator.async_request_refresh()


class MinezMiningSwitch(MinezEntity, SwitchEntity):
    """Switch for pausing and resuming mining."""

    _attr_translation_key = "mining"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: MinezDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.unique_base}_mining"

    @property
    def available(self) -> bool:
        """Return whether the miner supports a pause or resume action."""
        return (
            super().available
            and self.coordinator.data["controls"]["supports_mining_toggle"]
        )

    @property
    def is_on(self) -> bool:
        """Return whether mining is active."""
        return self.coordinator.data["controls"]["mining_active"]

    async def async_turn_on(self, **kwargs) -> None:
        """Resume mining."""
        await self.coordinator.client.async_resume_mining()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Pause mining."""
        await self.coordinator.client.async_pause_mining()
        await self.coordinator.async_request_refresh()
