"""Event platform: motion events surface in the logbook and the HA app."""

from __future__ import annotations

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RecameraCoordinator
from .entity import RecameraEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: RecameraCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RecameraMotionEvent(coordinator, entry)])


class RecameraMotionEvent(RecameraEntity, EventEntity):
    """Fires `motion` with the frame details and the saved snapshot URL."""

    _attr_device_class = EventDeviceClass.MOTION
    _attr_event_types = ["motion", "motion_end"]
    _attr_translation_key = "motion"

    def __init__(self, coordinator: RecameraCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_event"
        self._last_handled: tuple[int, str] | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_event))

    @callback
    def _handle_event(self) -> None:
        event = self.coordinator.last_event
        if not event:
            return
        key = (int(event.get("event_id") or 0), str(event.get("event")))
        if key == self._last_handled:
            return
        self._last_handled = key

        event_type = "motion" if event.get("event") == "motion_start" else "motion_end"
        self._trigger_event(
            event_type,
            {
                "event_id": event.get("event_id"),
                "motion_pixels": event.get("motion_pixels"),
                "largest_blob_pixels": event.get("largest_blob_pixels"),
                "motion_ratio": event.get("motion_ratio"),
                "bbox": event.get("bbox"),
                "captured_at": event.get("captured_at"),
                "image_url": event.get("image_url"),
            },
        )
        self.async_write_ha_state()
