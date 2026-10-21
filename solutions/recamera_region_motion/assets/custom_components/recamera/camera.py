"""Camera platform: live RTSP stream plus hardware JPEG stills."""

from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
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
    async_add_entities([RecameraCamera(coordinator, entry)])


class RecameraCamera(RecameraEntity, Camera):
    """The camera itself: RTSP for recordings, JPEG stills for the panel."""

    _attr_supported_features = CameraEntityFeature.STREAM
    _attr_name = None

    def __init__(self, coordinator: RecameraCoordinator, entry: ConfigEntry) -> None:
        RecameraEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._attr_unique_id = f"{entry.entry_id}_camera"

    @property
    def frame_interval(self) -> float:
        """Rate of the MJPEG proxy stream the panel uses for the live preview.

        Home Assistant caps the ?interval= query parameter at 2 fps, so the
        preview rate is driven from here instead.
        """

        return self.coordinator.frame_interval

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        return await self.coordinator.async_snapshot()

    async def stream_source(self) -> str | None:
        return self.coordinator.rtsp_url
