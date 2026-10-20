"""Constants for the reCamera integration."""

DOMAIN = "recamera"

MANUFACTURER = "Seeed Studio"
MODEL = "reCamera"

PLATFORMS = ["binary_sensor", "camera", "event", "image", "sensor", "switch"]

CONF_DEVICE_NAME = "device_name"
CONF_HOST = "host"
CONF_API_PORT = "api_port"
CONF_RTSP_PORT = "rtsp_port"
CONF_RTSP_STREAM = "rtsp_stream"
CONF_POLL_INTERVAL = "poll_interval"
CONF_PREVIEW_FPS = "preview_fps"
CONF_SNAPSHOT_KEEP = "snapshot_keep"
CONF_HA_NOTIFICATION = "ha_notification"
CONF_PUSH_ENABLED = "push_enabled"
CONF_PUSH_INCLUDE_IMAGE = "push_include_image"

DEFAULT_API_PORT = 8080
DEFAULT_RTSP_PORT = 8554
DEFAULT_RTSP_STREAM = "live0"
DEFAULT_POLL_INTERVAL = 1.0
DEFAULT_PREVIEW_FPS = 8
DEFAULT_SNAPSHOT_KEEP = 100
DEFAULT_DEVICE_NAME = "reCamera"

MIN_POLL_INTERVAL = 0.5
MAX_POLL_INTERVAL = 30.0

# Bus event fired for every motion transition. Automations and the bundled
# blueprint listen on this; it carries the saved snapshot URL.
EVENT_MOTION = f"{DOMAIN}_motion"

PANEL_URL_PATH = "recamera"
PANEL_TITLE = "reCamera"
STATIC_PATH = "/recamera_static"

WWW_SUBDIR = "recamera"

DEVICE_SOURCE = "recamera_motion_detection"
