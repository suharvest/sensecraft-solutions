"""Binary sensors: live motion state and zone configuration health."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
            RecameraMotionSensor(coordinator, entry),
            RecameraZoneSensor(coordinator, entry),
        ]
    )


class RecameraMotionSensor(RecameraEntity, BinarySensorEntity):
    """On while the camera reports motion inside the configured zones."""

    _attr_device_class = BinarySensorDeviceClass.MOTION
    _attr_translation_key = "motion"

    def __init__(self, coordinator: RecameraCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_motion"

    @property
    def is_on(self) -> bool:
        return self.coordinator.motion

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "motion_pixels": self.coordinator.motion_pixels,
            "largest_blob_pixels": self.coordinator.largest_blob_pixels,
            "motion_ratio": round(self.coordinator.motion_ratio, 5),
            "bbox": self.coordinator.bbox,
            "warming_up": self.coordinator.warming_up,
            "zone_count": len(self.coordinator.zones),
            "last_motion_at": self.coordinator.last_motion_at.isoformat()
            if self.coordinator.last_motion_at
            else None,
        }


class RecameraZoneSensor(RecameraEntity, BinarySensorEntity):
    """Problem sensor: nothing is detected until at least one zone is drawn."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "zones_missing"

    def __init__(self, coordinator: RecameraCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_zones_missing"

    @property
    def is_on(self) -> bool:
        return self.coordinator.available and not self.coordinator.configured
