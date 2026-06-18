from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ReCameraMainSensor(coordinator, entry)], True)

class ReCameraMainSensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._entry = entry
        self._attr_name = "reCamera Detection"
        self._attr_unique_id = f"{entry.data['host']}_detection_sensor"
        # ★关键：绑定设备信息，让它和摄像头归为一类
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.data['host'])},
            "name": f"reCamera ({entry.data['host']})",
            "manufacturer": "Seeed Studio",
            "model": "reCamera AI (YOLO11n)",
            "sw_version": "1.0.0",
        }

    @property
    def state(self):
        # 主状态显示总数
        return self.coordinator.data.get("total", 0) if self.coordinator.data else 0

    @property
    def extra_state_attributes(self):
        # 详细数据（person, car等）藏在这里
        return self.coordinator.data if self.coordinator.data else {}

    @property
    def icon(self):
        return "mdi:account-group"
