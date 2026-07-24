"""Sensor platform for MineZ."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import MinezDataUpdateCoordinator
from .entity import MinezEntity


@dataclass(frozen=True, kw_only=True)
class MinezSensorDescription(SensorEntityDescription):
    """Describes a MineZ sensor."""

    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any] | None] | None = None


def _format_duration(seconds: int | None) -> str | None:
    """Format seconds as a compact readable duration."""
    if seconds is None:
        return None

    remaining = int(seconds)
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, secs = divmod(remaining, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if minutes or hours or days:
        parts.append(f"{minutes}m")
    if not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


SENSORS: tuple[MinezSensorDescription, ...] = (
    MinezSensorDescription(
        key="hashboard_count",
        translation_key="hashboard_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["hashboards"]["count"],
    ),
    MinezSensorDescription(
        key="status",
        translation_key="status",
        value_fn=lambda data: data["miner"]["status"],
    ),
    MinezSensorDescription(
        key="api_version",
        translation_key="api_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data["api_version"],
    ),
    MinezSensorDescription(
        key="last_fetch_interval_s",
        translation_key="last_fetch_interval",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data["diagnostics"]["last_fetch_interval_s"],
    ),
    MinezSensorDescription(
        key="bos_version",
        translation_key="bos_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: data["miner"]["bos_version"],
    ),
    MinezSensorDescription(
        key="hashrate_5m_ths",
        translation_key="hashrate_5m",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data["stats"]["hashrate_5m_ths"],
    ),
    MinezSensorDescription(
        key="hashrate_15m_ths",
        translation_key="hashrate_15m",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data["stats"]["hashrate_15m_ths"],
    ),
    MinezSensorDescription(
        key="nominal_hashrate_ths",
        translation_key="nominal_hashrate",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data["stats"]["nominal_hashrate_ths"],
    ),
    MinezSensorDescription(
        key="power_w",
        translation_key="approximate_power_consumption",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["stats"]["power_w"],
    ),
    MinezSensorDescription(
        key="efficiency_jth",
        translation_key="efficiency",
        native_unit_of_measurement="J/TH",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data["stats"]["efficiency_jth"],
    ),
    MinezSensorDescription(
        key="highest_temp_c",
        translation_key="highest_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["cooling"]["highest_temp_c"],
    ),
    MinezSensorDescription(
        key="fan_rpm_avg",
        translation_key="fan_rpm_avg",
        native_unit_of_measurement="rpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["cooling"]["fan_rpm_avg"],
    ),
    MinezSensorDescription(
        key="accepted_shares",
        translation_key="accepted_shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data["stats"]["accepted_shares"],
    ),
    MinezSensorDescription(
        key="rejected_shares",
        translation_key="rejected_shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data["stats"]["rejected_shares"],
    ),
    MinezSensorDescription(
        key="stale_shares",
        translation_key="stale_shares",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data["stats"]["stale_shares"],
    ),
    MinezSensorDescription(
        key="best_share",
        translation_key="best_share",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["stats"]["best_share"],
    ),
    MinezSensorDescription(
        key="found_blocks",
        translation_key="found_blocks",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data["stats"]["found_blocks"],
    ),
    MinezSensorDescription(
        key="system_uptime_s",
        translation_key="system_uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["miner"]["system_uptime_s"],
    ),
    MinezSensorDescription(
        key="system_uptime_readable",
        translation_key="system_uptime_readable",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _format_duration(data["miner"]["system_uptime_s"]),
        attributes_fn=lambda data: {"seconds": data["miner"]["system_uptime_s"]},
    ),
    MinezSensorDescription(
        key="bosminer_uptime_s",
        translation_key="bosminer_uptime",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["miner"]["bosminer_uptime_s"],
    ),
    MinezSensorDescription(
        key="bosminer_uptime_readable",
        translation_key="bosminer_uptime_readable",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _format_duration(data["miner"]["bosminer_uptime_s"]),
        attributes_fn=lambda data: {"seconds": data["miner"]["bosminer_uptime_s"]},
    ),
    MinezSensorDescription(
        key="error_count",
        translation_key="error_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["errors"]["count"],
    ),
    MinezSensorDescription(
        key="tuner_state",
        translation_key="tuner_state",
        value_fn=lambda data: data["performance"]["tuner_state"],
    ),
    MinezSensorDescription(
        key="power_target_w",
        translation_key="current_power_target",
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data["performance"]["power_target_w"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MineZ sensors."""
    coordinator: MinezDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    entities: list[SensorEntity] = [
        *(MinezSensor(coordinator, description) for description in SENSORS),
        *(
            entity
            for hashboard in coordinator.data["hashboards"]["items"]
            for entity in _build_hashboard_sensors(coordinator, hashboard)
        ),
    ]
    async_add_entities(entities)


@dataclass(frozen=True, kw_only=True)
class MinezHashboardSensorDescription(SensorEntityDescription):
    """Describes a dynamic hashboard sensor."""

    name: str
    value_key: str


HASHBOARD_SENSORS: tuple[MinezHashboardSensorDescription, ...] = (
    MinezHashboardSensorDescription(
        key="enabled",
        translation_key="hashboard_enabled",
        name="Enabled",
        value_key="enabled",
    ),
    MinezHashboardSensorDescription(
        key="hashrate_5m_ths",
        translation_key="hashboard_hashrate_5m",
        name="Hashrate 5m",
        value_key="hashrate_5m_ths",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    MinezHashboardSensorDescription(
        key="hashrate_15m_ths",
        translation_key="hashboard_hashrate_15m",
        name="Hashrate 15m",
        value_key="hashrate_15m_ths",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    MinezHashboardSensorDescription(
        key="nominal_hashrate_ths",
        translation_key="hashboard_nominal_hashrate",
        name="Nominal hashrate",
        value_key="nominal_hashrate_ths",
        native_unit_of_measurement="TH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    MinezHashboardSensorDescription(
        key="highest_chip_temp_c",
        translation_key="hashboard_highest_chip_temp",
        name="Highest chip temperature",
        value_key="highest_chip_temp_c",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MinezHashboardSensorDescription(
        key="board_temp_c",
        translation_key="hashboard_board_temp",
        name="Board temperature",
        value_key="board_temp_c",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MinezHashboardSensorDescription(
        key="inlet_temp_c",
        translation_key="hashboard_inlet_temp",
        name="Inlet temperature",
        value_key="inlet_temp_c",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MinezHashboardSensorDescription(
        key="outlet_temp_c",
        translation_key="hashboard_outlet_temp",
        name="Outlet temperature",
        value_key="outlet_temp_c",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MinezHashboardSensorDescription(
        key="voltage_v",
        translation_key="hashboard_voltage",
        name="Voltage",
        value_key="voltage_v",
        native_unit_of_measurement="V",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
    ),
    MinezHashboardSensorDescription(
        key="frequency_mhz",
        translation_key="hashboard_frequency",
        name="Frequency",
        value_key="frequency_mhz",
        native_unit_of_measurement="MHz",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    MinezHashboardSensorDescription(
        key="chips_count",
        translation_key="hashboard_chips_count",
        name="Chips count",
        value_key="chips_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


def _build_hashboard_sensors(
    coordinator: MinezDataUpdateCoordinator,
    hashboard: dict[str, Any],
) -> list["MinezHashboardSensor"]:
    """Create sensors for a discovered hashboard."""
    return [
        MinezHashboardSensor(coordinator, hashboard["id"], description)
        for description in HASHBOARD_SENSORS
    ]


class MinezSensor(MinezEntity, SensorEntity):
    """Representation of a MineZ sensor."""

    entity_description: MinezSensorDescription

    def __init__(
        self,
        coordinator: MinezDataUpdateCoordinator,
        description: MinezSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self.unique_base}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the current value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return optional extra attributes."""
        attributes: dict[str, Any] = {}
        if self.entity_description.key == "error_count":
            attributes["messages"] = self.coordinator.data["errors"]["messages"][:10]
        if self.entity_description.attributes_fn:
            extra = self.entity_description.attributes_fn(self.coordinator.data)
            if extra:
                attributes.update(extra)
        return attributes or None


class MinezHashboardSensor(MinezEntity, SensorEntity):
    """Representation of a dynamic hashboard sensor."""

    entity_description: MinezHashboardSensorDescription

    def __init__(
        self,
        coordinator: MinezDataUpdateCoordinator,
        hashboard_id: str,
        description: MinezHashboardSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._hashboard_id = hashboard_id
        hashboard = self._hashboard()
        label = f"Hashboard {hashboard['index']}" if hashboard else hashboard_id
        self._attr_unique_id = f"{self.unique_base}_{hashboard_id}_{description.key}"
        self._attr_name = f"{label} {description.name}"
        self._attr_translation_key = description.translation_key
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_device_class = description.device_class
        self._attr_state_class = description.state_class
        self._attr_entity_category = description.entity_category

    def _hashboard(self) -> dict[str, Any] | None:
        for hashboard in self.coordinator.data["hashboards"]["items"]:
            if hashboard["id"] == self._hashboard_id:
                return hashboard
        return None

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return super().available and self._hashboard() is not None

    @property
    def native_value(self) -> Any:
        """Return current state."""
        hashboard = self._hashboard()
        if hashboard is None:
            return None
        value = hashboard[self.entity_description.value_key]
        if self.entity_description.key == "enabled":
            return "Enabled" if value else "Disabled"
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return hashboard metadata."""
        hashboard = self._hashboard()
        if hashboard is None:
            return None
        return {
            "hashboard_id": hashboard["id"],
            "index": hashboard["index"],
            "model": hashboard["model"],
            "board_name": hashboard["board_name"],
            "chip_type": hashboard["chip_type"],
            "serial_number": hashboard["serial_number"],
        }
