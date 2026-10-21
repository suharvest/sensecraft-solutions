"""Image platform: the frame captured when motion was detected."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.image import Image, ImageEntity
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
    async_add_entities([RecameraLastMotionImage(coordinator, entry, hass)])


class RecameraLastMotionImage(RecameraEntity, ImageEntity):
    """Serves the last motion frame stored inside Home Assistant."""

    _attr_content_type = "image/jpeg"
    _attr_translation_key = "last_motion"

    def __init__(
        self, coordinator: RecameraCoordinator, entry: ConfigEntry, hass: HomeAssistant
    ) -> None:
        RecameraEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)
        self._attr_unique_id = f"{entry.entry_id}_image"

    @property
    def image_last_updated(self) -> datetime | None:
        return self.coordinator.last_image_at

    async def async_image(self) -> bytes | None:
        return self.coordinator.last_image

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "image_url": self.coordinator.last_image_url,
            "event_id": (self.coordinator.last_event or {}).get("event_id"),
        }
