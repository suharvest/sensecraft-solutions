import logging
from datetime import timedelta

import aiohttp
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

class ReCameraCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, host, port):
        super().__init__(
            hass,
            _LOGGER,
            name="ReCamera Sensor",
            update_interval=timedelta(seconds=2), # 每2秒更新一次
        )
        self.api_url = f"http://{host}:{port}/data" # Node-RED 设置的HTTP接口

    async def _async_update_data(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.api_url) as response:
                    return await response.json() # 返回 {"person": 1, ...}
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
