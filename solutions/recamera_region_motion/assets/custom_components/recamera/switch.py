"""Switch that enables or pauses detection on the camera."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    async_add_entities([RecameraDetectionSwitch(coordinator, entry)])


class RecameraDetectionSwitch(RecameraEntity, SwitchEntity):
    """Turns the detector on or off without losing the drawn zones."""

    _attr_translation_key = "detection"

    def __init__(self, coordinator: RecameraCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_detection"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.config.get("enabled", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_enabled(False)
