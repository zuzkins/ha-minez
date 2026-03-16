"""Button platform for MineZ."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Awaitable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MinezDataUpdateCoordinator
from .entity import MinezEntity


@dataclass(frozen=True, kw_only=True)
class MinezButtonDescription(ButtonEntityDescription):
    """Describes a MineZ button."""

    press_fn: Callable[[MinezDataUpdateCoordinator], Awaitable[None]]


BUTTONS: tuple[MinezButtonDescription, ...] = (
    MinezButtonDescription(
        key="pause_mining",
        translation_key="pause_mining",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.async_pause_mining(),
    ),
    MinezButtonDescription(
        key="resume_mining",
        translation_key="resume_mining",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.async_resume_mining(),
    ),
    MinezButtonDescription(
        key="restart_bosminer",
        translation_key="restart_bosminer",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.async_restart_bosminer(),
    ),
    MinezButtonDescription(
        key="reboot_miner",
        translation_key="reboot_miner",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda coordinator: coordinator.client.async_reboot_miner(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MineZ buttons."""
    coordinator: MinezDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(MinezButton(coordinator, description) for description in BUTTONS)


class MinezButton(MinezEntity, ButtonEntity):
    """Representation of a MineZ button."""

    entity_description: MinezButtonDescription

    def __init__(
        self,
        coordinator: MinezDataUpdateCoordinator,
        description: MinezButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self.unique_base}_{description.key}"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self.entity_description.press_fn(self.coordinator)
        await self.coordinator.async_request_refresh()
