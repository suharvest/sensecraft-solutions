from .const import DOMAIN
from .coordinator import ReCameraCoordinator

PLATFORMS = ["sensor", "camera"]

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})

    # 初始化数据协调器
    coordinator = ReCameraCoordinator(
        hass,
        entry.data["host"],
        entry.data.get("port", 1880)
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # 加载 Sensor 和 Camera
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True
