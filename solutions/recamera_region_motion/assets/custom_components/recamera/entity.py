"""Shared entity base for the reCamera integration."""

from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import RecameraCoordinator


class RecameraEntity(Entity):
    """Base class that follows the coordinator instead of polling on its own."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, coordinator: RecameraCoordinator) -> None:
        self.coordinator = coordinator
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_identifier)},
            name=coordinator.name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=coordinator.api_base,
        )

    @property
    def available(self) -> bool:
        return self.coordinator.available and self.coordinator.has_motion_app

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.coordinator.async_add_listener(self._handle_coordinator_update))

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()
