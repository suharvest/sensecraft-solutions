import logging

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.components.ffmpeg import async_get_image
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the camera from a config entry."""
    host = entry.data['host']

    # ★关键修改：加入了账号密码 admin:admin
    # 格式：rtsp://用户名:密码@IP:端口/路径
    rtsp_url = f"rtsp://admin:admin@{host}:554/live"

    async_add_entities([ReCameraCam(hass, entry, rtsp_url)], True)

class ReCameraCam(Camera):
    """Implementation of the ReCamera."""

    def __init__(self, hass, entry, stream_url):
        """Initialize the camera."""
        super().__init__()
        self.hass = hass
        self._entry = entry
        self._stream_source = stream_url

        self._attr_name = "reCamera Stream"
        self._attr_unique_id = f"{entry.data['host']}_stream_camera"

        # 声明支持流媒体 (让HA显示预加载选项)
        self._attr_supported_features = CameraEntityFeature.STREAM

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data['host'])},
            name=f"reCamera ({entry.data['host']})",
            manufacturer="Seeed Studio",
            model="reCamera AI",
        )

    async def stream_source(self):
        """返回视频流地址 (给 stream 组件使用)"""
        return self._stream_source

    async def async_camera_image(self, width=None, height=None):
        """
        从流中截取静态图片。
        这个方法依赖于系统安装了 ffmpeg (sudo apt install ffmpeg)。
        """
        return await async_get_image(
            self.hass, self._stream_source, width=width, height=height
        )

    @property
    def is_recording(self):
        return False

    @property
    def is_streaming(self):
        return True
