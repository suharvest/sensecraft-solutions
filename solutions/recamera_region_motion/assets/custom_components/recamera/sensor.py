"""Sensors for motion history and diagnostics."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RecameraCoordinator
from .entity import RecameraEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: RecameraCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            RecameraLastMotionSensor(coordinator, entry),
            RecameraMotionPixelsSensor(coordinator, entry),
            RecameraZoneCountSensor(coordinator, entry),
        ]
    )


class RecameraLastMotionSensor(RecameraEntity, SensorEntity):
    """Timestamp of the most recent motion alert."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_translation_key = "last_motion"

    def __init__(self, coordinator: RecameraCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_last_motion"

    @property
    def native_value(self) -> datetime | None:
        return self.coordinator.last_motion_at

    @property
    def extra_state_attributes(self) -> dict:
        event = self.coordinator.last_event or {}
        return {
            "event_id": event.get("event_id"),
            "image_url": event.get("image_url"),
            "bbox": event.get("bbox"),
        }


class RecameraMotionPixelsSensor(RecameraEntity, SensorEntity):
    """Live motion pixel count inside the active zones (diagnostic)."""

    _attr_translation_key = "motion_pixels"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "px"

    def __init__(self, coordinator: RecameraCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_motion_pixels"

    @property
    def native_value(self) -> int:
        return self.coordinator.motion_pixels


class RecameraZoneCountSensor(RecameraEntity, SensorEntity):
    """How many detection zones and whitelists are stored on the camera."""

    _attr_translation_key = "zone_count"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: RecameraCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_zone_count"

    @property
    def native_value(self) -> int:
        return len(self.coordinator.zones)
