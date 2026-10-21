"""Coordinator that talks to one reCamera and fans motion events out to HA."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
from io import BytesIO
from collections import OrderedDict, deque
from datetime import datetime, timezone
import logging
import os
import re
import time
import zipfile
from typing import Any, Callable

import aiohttp

from homeassistant.components import webhook
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.network import NoURLAvailableError

from .const import (
    CONF_API_PORT,
    CONF_DEVICE_NAME,
    CONF_HA_NOTIFICATION,
    CONF_HOST,
    CONF_POLL_INTERVAL,
    CONF_PREVIEW_FPS,
    CONF_PUSH_ENABLED,
    CONF_PUSH_INCLUDE_IMAGE,
    CONF_RTSP_PORT,
    CONF_RTSP_STREAM,
    CONF_SNAPSHOT_KEEP,
    DEFAULT_API_PORT,
    DEFAULT_DEVICE_NAME,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_PREVIEW_FPS,
    DEFAULT_RTSP_PORT,
    DEFAULT_RTSP_STREAM,
    DEFAULT_SNAPSHOT_KEEP,
    DEVICE_SOURCE,
    DOMAIN,
    EVENT_MOTION,
    WWW_SUBDIR,
)
from .device_client import RecameraDeviceClient, RecameraDeviceError

_LOGGER = logging.getLogger(__name__)

MOTION_POLL_INTERVAL = 0.4
EVENT_HISTORY = 50
SEEN_EVENTS = 64
MAX_PACKAGE_BYTES = 8 * 1024 * 1024
APP_ID = re.compile(r"^[a-z][a-z0-9_]{1,47}$")
GITHUB_REPO = re.compile(r"^https://github\.com/([A-Za-z0-9-]{1,39})/([A-Za-z0-9_.-]{1,100})(?:\.git)?/?$")


class RecameraCoordinator:
    """Owns the connection to one camera and the state shared by all entities."""

    def __init__(self, hass: HomeAssistant, entry) -> None:
        self.hass = hass
        self.entry = entry

        conf = {**entry.data, **entry.options}
        self.name: str = conf.get(CONF_DEVICE_NAME) or DEFAULT_DEVICE_NAME
        self.host: str = conf[CONF_HOST]
        self.api_port: int = int(conf.get(CONF_API_PORT) or DEFAULT_API_PORT)
        self.rtsp_port: int = int(conf.get(CONF_RTSP_PORT) or DEFAULT_RTSP_PORT)
        self.rtsp_stream: str = conf.get(CONF_RTSP_STREAM) or DEFAULT_RTSP_STREAM
        self.poll_interval: float = float(conf.get(CONF_POLL_INTERVAL) or DEFAULT_POLL_INTERVAL)
        self.preview_fps: int = int(conf.get(CONF_PREVIEW_FPS) or DEFAULT_PREVIEW_FPS)
        self.snapshot_keep: int = int(conf.get(CONF_SNAPSHOT_KEEP) or DEFAULT_SNAPSHOT_KEEP)
        self.ha_notification: bool = bool(conf.get(CONF_HA_NOTIFICATION, True))
        self.push_enabled: bool = bool(conf.get(CONF_PUSH_ENABLED, True))
        self.push_include_image: bool = bool(conf.get(CONF_PUSH_INCLUDE_IMAGE, True))

        self.client = RecameraDeviceClient(self.host, self.api_port)
        self.device_identifier = f"{self.host}_{self.api_port}"

        self.available = False
        self.reachable = False
        self.app_version = ""
        self.custom_apps: dict[str, dict[str, Any]] = {}
        self.app_seen_at: dict[str, float] = {}
        self.legacy_device = False
        self.status: dict[str, Any] = {}
        self.config: dict[str, Any] = {}
        self.notify_state: dict[str, Any] = {}
        self.health: dict[str, Any] = {}

        self.motion = False
        self.warming_up = True
        self.configured = False
        self.motion_pixels = 0
        self.largest_blob_pixels = 0
        self.motion_ratio = 0.0
        self.bbox: list[float] | None = None
        self.last_error = ""
        self.last_motion_at: datetime | None = None
        self.last_event: dict[str, Any] | None = None
        self.events: deque[dict[str, Any]] = deque(maxlen=EVENT_HISTORY)

        self.last_image: bytes | None = None
        self.last_image_at: datetime | None = None
        self.last_image_url: str | None = None
        self.last_image_path: str | None = None

        self.push_url: str | None = None
        self.webhook_id = f"{DOMAIN}-{entry.entry_id}"
        self.push_error = ""
        self.push_received = 0
        self._ha_device_id: str | None = None

        self._listeners: set[Callable[[], None]] = set()
        self._poll_task: asyncio.Task | None = None
        self._watchdog_task: asyncio.Task | None = None
        self._seen: OrderedDict[tuple[int, str], bool] = OrderedDict()
        self._event_counter = 0
        self._last_event_id = 0
        self._image_counter = 0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ info
    @property
    def rtsp_url(self) -> str:
        return f"rtsp://{self.host}:{self.rtsp_port}/{self.rtsp_stream}"

    @property
    def api_base(self) -> str:
        return self.client.api_base

    @property
    def frame_interval(self) -> float:
        fps = max(1, min(25, self.preview_fps or DEFAULT_PREVIEW_FPS))
        return 1.0 / fps

    @property
    def zones(self) -> list[dict[str, Any]]:
        zones = self.config.get("zones")
        return zones if isinstance(zones, list) else []

    @property
    def ha_device_id(self) -> str | None:
        """Registry id of the HA device, so blueprints can filter by camera."""

        if self._ha_device_id is None:
            device = resolve_device(self.hass, self.device_identifier, self.entry.entry_id)
            self._ha_device_id = device.id if device else None
        return self._ha_device_id

    @property
    def apps(self) -> list[dict[str, Any]]:
        """Only show applications explicitly added to this camera in HA."""

        apps = []
        for manifest in self.custom_apps.values():
            motion = manifest["id"] == "region_motion"
            apps.append({
                **manifest,
                "running": bool(self.available) if motion else
                    time.monotonic() - self.app_seen_at.get(manifest["source"], 0) < 90,
                "installed": bool(self.available) if motion else None,
                "uploaded": manifest.get("origin") == "package",
            })
        return apps

    @property
    def has_motion_app(self) -> bool:
        return "region_motion" in self.custom_apps

    def as_dict(self) -> dict[str, Any]:
        """Serialisable view used by the sidebar panel."""

        return {
            "entry_id": self.entry.entry_id,
            "name": self.name,
            "host": self.host,
            "api_port": self.api_port,
            "api_base": self.api_base,
            "rtsp_url": self.rtsp_url,
            "available": self.available or any(app["running"] for app in self.apps),
            "reachable": self.reachable,
            "legacy_device": self.legacy_device,
            "motion": self.motion,
            "warming_up": self.warming_up,
            "configured": self.configured,
            "enabled": bool(self.config.get("enabled", False)),
            "motion_pixels": self.motion_pixels,
            "largest_blob_pixels": self.largest_blob_pixels,
            "motion_ratio": self.motion_ratio,
            "bbox": self.bbox,
            "last_error": self.last_error,
            "last_motion_at": self.last_motion_at.isoformat() if self.last_motion_at else None,
            "zone_count": len(self.zones),
            "config": self.config,
            "status": self.status,
            "events": list(self.events)[-25:],
            "push_url": self.push_url,
            "push_enabled": self.push_enabled,
            "push_error": self.push_error,
            "push_received": self.push_received,
            "notify_state": self.notify_state,
            "ha_notification": self.ha_notification,
            "preview_fps": self.preview_fps,
            "poll_interval": self.poll_interval,
            "snapshot_keep": self.snapshot_keep,
            "last_image_url": self.last_image_url,
            "analysis_width": self.status.get("analysis_width"),
            "analysis_height": self.status.get("analysis_height"),
            "apps": self.apps,
        }

    # ------------------------------------------------------------- lifecycle
    async def async_setup(self) -> None:
        await self.async_load_packages()
        webhook.async_register(
            self.hass,
            DOMAIN,
            f"{self.name} motion",
            self.webhook_id,
            _handle_webhook,
            allowed_methods=["POST"],
        )
        self._compute_push_url()
        await self.async_refresh_device()
        if self.available and self.has_motion_app:
            await self.async_apply_push_settings()
        self._poll_task = asyncio.create_task(self._poll_loop(), name=f"{DOMAIN}_poll_{self.entry.entry_id}")
        self._watchdog_task = asyncio.create_task(self._config_loop(), name=f"{DOMAIN}_cfg_{self.entry.entry_id}")

    @callback
    def async_apply_options(self) -> bool:
        """Pick up option changes without recreating entities.

        Returns True when the device push configuration has to be re-sent.
        """

        options = dict(self.entry.options)
        self.poll_interval = float(options.get(CONF_POLL_INTERVAL) or DEFAULT_POLL_INTERVAL)
        self.preview_fps = int(options.get(CONF_PREVIEW_FPS) or DEFAULT_PREVIEW_FPS)
        self.snapshot_keep = int(options.get(CONF_SNAPSHOT_KEEP) or DEFAULT_SNAPSHOT_KEEP)
        self.ha_notification = bool(options.get(CONF_HA_NOTIFICATION, True))

        push_changed = (
            bool(options.get(CONF_PUSH_ENABLED, True)) != self.push_enabled
            or bool(options.get(CONF_PUSH_INCLUDE_IMAGE, True)) != self.push_include_image
        )
        self.push_enabled = bool(options.get(CONF_PUSH_ENABLED, True))
        self.push_include_image = bool(options.get(CONF_PUSH_INCLUDE_IMAGE, True))
        self._notify_listeners()
        return push_changed

    async def async_shutdown(self) -> None:
        for task in (self._poll_task, self._watchdog_task):
            if task is not None:
                task.cancel()
        self._poll_task = None
        self._watchdog_task = None
        webhook.async_unregister(self.hass, self.webhook_id)
        await self.client.async_close()

    @callback
    def _compute_push_url(self) -> None:
        try:
            self.push_url = webhook.async_generate_url(
                self.hass,
                self.webhook_id,
                allow_internal=True,
                allow_external=True,
                allow_ip=True,
                prefer_external=False,
            )
        except NoURLAvailableError:
            self.push_url = None
            _LOGGER.warning(
                "reCamera %s: no internal/external URL configured, falling back to polling only",
                self.name,
            )

    async def async_refresh_device(self) -> None:
        """Fetch health, config and notify state once (used at setup/refresh)."""

        try:
            self.health = await self.client.async_health()
            try:
                version = await self.client.async_version()
                self.app_version = str(version.get("version") or "")[:64]
            except RecameraDeviceError:
                self.app_version = ""
            self.config = await self.client.async_get_config()
            try:
                self.notify_state = await self.client.async_get_notify()
            except RecameraDeviceError:
                self.legacy_device = True
                self.notify_state = {}
            self.available = True
            self.reachable = True
            self.configured = bool(self.status.get("configured", False)) or bool(self.zones)
        except RecameraDeviceError as err:
            self.available = False
            self.reachable = await self.async_probe_host()
            self.push_error = str(err)
            _LOGGER.warning("reCamera %s unreachable: %s", self.name, err)
        self._notify_listeners()

    async def async_probe_host(self) -> bool:
        """Check a management port when the application API is unavailable."""
        for port in (80, 22):
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(self.host, port), timeout=1.2
                )
                writer.close()
                await writer.wait_closed()
                return True
            except (OSError, asyncio.TimeoutError):
                continue
        return False

    @property
    def package_folder(self) -> str:
        return self.hass.config.path(".storage", "recamera_packages", self.entry.entry_id)

    async def async_load_packages(self) -> None:
        """Read manifests registered for this device without executing packages."""
        def _load() -> dict[str, dict[str, Any]]:
            found = {}
            if not os.path.isdir(self.package_folder):
                return found
            for filename in os.listdir(self.package_folder):
                if not filename.endswith((".zip", ".json")):
                    continue
                try:
                    with open(os.path.join(self.package_folder, filename), "rb") as handle:
                        manifest = (self._package_manifest(handle.read()) if filename.endswith(".zip")
                                    else self._repository_manifest(json.loads(handle.read())))
                    found[manifest["id"]] = manifest
                except (OSError, ValueError, UnicodeDecodeError, zipfile.BadZipFile):
                    _LOGGER.warning("Skipping invalid reCamera package %s", filename)
            return found
        self.custom_apps = await self.hass.async_add_executor_job(_load)

    @staticmethod
    def _package_manifest(data: bytes) -> dict[str, Any]:
        if not data or len(data) > MAX_PACKAGE_BYTES:
            raise ValueError("Package must be a ZIP smaller than 8 MiB")
        with zipfile.ZipFile(BytesIO(data)) as archive:
            if len(archive.infolist()) > 128:
                raise ValueError("Package has too many files")
            try:
                info = archive.getinfo("recamera-app.json")
            except KeyError as err:
                raise ValueError("ZIP must contain recamera-app.json at its root") from err
            if info.file_size > 32768:
                raise ValueError("App manifest is too large")
            try:
                raw = json.loads(archive.read(info))
            except (ValueError, UnicodeDecodeError) as err:
                raise ValueError("Invalid app manifest") from err
        if not isinstance(raw, dict):
            raise ValueError("App manifest must be a JSON object")
        app_id = raw.get("id")
        source = raw.get("source")
        if not isinstance(app_id, str) or not APP_ID.fullmatch(app_id) or app_id == "region_motion":
            raise ValueError("Invalid app id")
        if not isinstance(source, str) or not APP_ID.fullmatch(source) or source == DEVICE_SOURCE:
            raise ValueError("Invalid event source")
        name = raw.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise ValueError("App name is required (max 80 characters)")
        return {
            "id": app_id,
            "name": name.strip(),
            "description": str(raw.get("description") or "")[:240],
            "source": source,
            "version": str(raw.get("version") or "")[:64],
            "origin": "package",
        }

    @staticmethod
    def _repository_manifest(raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("App manifest must be a JSON object")
        app_id, source = raw.get("id"), raw.get("source")
        if not isinstance(app_id, str) or not APP_ID.fullmatch(app_id):
            raise ValueError("Invalid app id")
        if not isinstance(source, str) or not APP_ID.fullmatch(source):
            raise ValueError("Invalid event source")
        if (app_id == "region_motion") != (source == DEVICE_SOURCE):
            raise ValueError("Region motion app must use its matching event source")
        name = raw.get("name")
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80:
            raise ValueError("App name is required (max 80 characters)")
        repository = raw.get("repository")
        if not isinstance(repository, str) or not GITHUB_REPO.fullmatch(repository):
            raise ValueError("Invalid GitHub repository URL")
        return {
            "id": app_id, "name": name.strip(),
            "description": str(raw.get("description") or "")[:240],
            "source": source, "version": str(raw.get("version") or "")[:64],
            "origin": "github", "repository": repository,
        }

    async def async_add_repository(self, url: str) -> dict[str, Any]:
        """Fetch the root manifest from a public GitHub repo and save per device."""
        match = GITHUB_REPO.fullmatch(url.strip())
        if not match:
            raise ValueError("Enter a GitHub repository URL, such as https://github.com/owner/repo")
        owner, repo = match.groups()
        repo = repo.removesuffix(".git")
        repository = f"https://github.com/{owner}/{repo}"
        timeout = aiohttp.ClientTimeout(total=12, connect=5)
        try:
            # raw.githubusercontent.com avoids the shared GitHub API rate limit.
            # Unlike LAN device requests, this request should honor HA's HTTPS_PROXY.
            async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
                for branch in ("main", "master"):
                    raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/recamera-app.json"
                    async with session.get(raw_url, allow_redirects=False) as response:
                        if response.status == 404:
                            continue
                        if response.status != 200:
                            raise ValueError(f"Cannot read recamera-app.json from GitHub (HTTP {response.status})")
                        data = await response.content.read(32769)
                        if len(data) > 32768:
                            raise ValueError("App manifest is too large")
                        break
                else:
                    raise ValueError("No recamera-app.json found on the main or master branch")
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ValueError(f"Cannot reach GitHub: {err}") from err
        try:
            raw = json.loads(data)
        except (ValueError, UnicodeDecodeError) as err:
            raise ValueError("Invalid recamera-app.json") from err
        if not isinstance(raw, dict):
            raise ValueError("Invalid recamera-app.json")
        raw["repository"] = repository
        manifest = self._repository_manifest(raw)
        if manifest["id"] in self.custom_apps and self.custom_apps[manifest["id"]].get("origin") != "github":
            raise ValueError("An uploaded package already uses this app id")
        if any(app["source"] == manifest["source"] and app["id"] != manifest["id"]
               for app in self.custom_apps.values()):
            raise ValueError("Another app already uses this event source")
        def _write() -> None:
            os.makedirs(self.package_folder, exist_ok=True)
            target = os.path.join(self.package_folder, manifest["id"] + ".json")
            staged = target + ".tmp"
            with open(staged, "w", encoding="utf-8") as handle:
                json.dump(manifest, handle)
            os.replace(staged, target)
        await self.hass.async_add_executor_job(_write)
        self.custom_apps[manifest["id"]] = manifest
        self._notify_listeners()
        if manifest["id"] == "region_motion" and self.available:
            await self.async_apply_push_settings()
        return manifest

    async def async_upload_package(self, encoded: str) -> dict[str, Any]:
        if len(encoded) > MAX_PACKAGE_BYTES * 2:
            raise ValueError("Package is too large")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as err:
            raise ValueError("Invalid base64 package") from err
        try:
            manifest = await self.hass.async_add_executor_job(self._package_manifest, data)
        except zipfile.BadZipFile as err:
            raise ValueError("Invalid ZIP package") from err
        if manifest["id"] in self.custom_apps and self.custom_apps[manifest["id"]].get("origin") != "package":
            raise ValueError("A GitHub app already uses this app id")
        if any(
            app["source"] == manifest["source"] and app["id"] != manifest["id"]
            for app in self.custom_apps.values()
        ):
            raise ValueError("Another app already uses this event source")
        def _write() -> None:
            os.makedirs(self.package_folder, exist_ok=True)
            target = os.path.join(self.package_folder, manifest["id"] + ".zip")
            staged = target + ".tmp"
            with open(staged, "wb") as handle:
                handle.write(data)
            os.replace(staged, target)
        await self.hass.async_add_executor_job(_write)
        self.custom_apps[manifest["id"]] = manifest
        self._notify_listeners()
        return manifest

    async def async_remove_app(self, app_id: str) -> None:
        manifest = self.custom_apps.get(app_id)
        if manifest is None:
            raise ValueError("App is not registered on this device")
        extension = ".json" if manifest.get("origin") == "github" else ".zip"
        path = os.path.join(self.package_folder, app_id + extension)
        await self.hass.async_add_executor_job(os.remove, path)
        self.custom_apps.pop(app_id, None)
        self.app_seen_at.pop(manifest["source"], None)
        self._notify_listeners()
        if app_id == "region_motion" and self.available:
            await self.async_apply_push_settings()

    async def async_apply_push_settings(self) -> None:
        """Tell the camera where to push events (or disable pushing)."""

        if not self.has_motion_app or not self.push_enabled or not self.push_url:
            desired_enabled = False
            url = self.push_url or ""
        else:
            desired_enabled = True
            url = self.push_url

        notify = {
            "enabled": desired_enabled,
            "url": url,
            "device_name": self.name,
            "events": ["motion_start", "motion_end"],
            "include_image": self.push_include_image,
            "timeout_ms": 3000,
            "retries": 2,
        }
        try:
            self.notify_state = await self.client.async_set_notify(notify)
            self.legacy_device = False
            self.push_error = ""
        except RecameraDeviceError as err:
            self.push_error = str(err)
            if "404" in str(err):
                self.legacy_device = True
            _LOGGER.warning("reCamera %s: cannot configure device push: %s", self.name, err)
        self._notify_listeners()

    # --------------------------------------------------------------- polling
    async def _poll_loop(self) -> None:
        consecutive_failures = 0
        while True:
            interval = MOTION_POLL_INTERVAL if self.motion else self.poll_interval
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                return
            try:
                status = await self.client.async_status()
            except RecameraDeviceError as err:
                consecutive_failures += 1
                if self.available or consecutive_failures == 3:
                    _LOGGER.debug("reCamera %s poll failed: %s", self.name, err)
                if consecutive_failures >= 3 and self.available:
                    self.available = False
                    self.push_error = str(err)
                    self._notify_listeners()
                if consecutive_failures == 3 or consecutive_failures % 30 == 0:
                    self.reachable = await self.async_probe_host()
                    self._notify_listeners()
                continue

            consecutive_failures = 0
            if not self.available:
                self.available = True
                self.reachable = True
                self.push_error = ""
                async def _refresh_after_reconnect() -> None:
                    await self.async_refresh_device()
                    if self.available and self.has_motion_app:
                        await self.async_apply_push_settings()
                asyncio.create_task(_refresh_after_reconnect())
            self._process_status(status)

    async def _config_loop(self) -> None:
        """Refresh config/notify periodically so external edits show up."""

        while True:
            try:
                await asyncio.sleep(30.0)
            except asyncio.CancelledError:
                return
            try:
                self.config = await self.client.async_get_config()
                self.notify_state = await self.client.async_get_notify()
            except RecameraDeviceError:
                continue
            self._notify_listeners()

    def _process_status(self, status: dict[str, Any]) -> None:
        self.status = status
        self.warming_up = bool(status.get("warming_up", True))
        self.configured = bool(status.get("configured", False))
        self.motion_pixels = int(status.get("motion_pixels") or 0)
        self.largest_blob_pixels = int(status.get("largest_blob_pixels") or 0)
        self.motion_ratio = float(status.get("motion_ratio") or 0.0)
        bbox = status.get("bbox")
        self.bbox = bbox if isinstance(bbox, list) and len(bbox) == 4 else None
        self.last_error = str(status.get("last_error") or "")

        motion_now = bool(status.get("motion", False))
        try:
            event_id = int(float(status.get("event_id") or 0))
        except (TypeError, ValueError):
            event_id = 0

        if event_id < self._last_event_id:
            # The camera restarted and renumbered its events.
            self._seen.clear()
        self._last_event_id = max(self._last_event_id, event_id)

        capture_ms = status.get("capture_unix_ms") or status.get("timestamp_unix_ms")
        if motion_now and not self.motion:
            asyncio.create_task(
                self._emit(
                    "motion_start",
                    event_id=event_id,
                    capture_ms=capture_ms,
                    status=status,
                )
            )
        elif not motion_now and self.motion:
            asyncio.create_task(
                self._emit("motion_end", event_id=event_id, capture_ms=capture_ms, status=status)
            )

        self.motion = motion_now
        self._notify_listeners()

    # ------------------------------------------------------------- webhook
    @callback
    def async_handle_push(self, payload: dict[str, Any]) -> None:
        """Handle one webhook payload pushed by the camera."""

        if not isinstance(payload, dict):
            return
        source = payload.get("source")
        if source not in (DEVICE_SOURCE, None):
            if isinstance(source, str) and source in {app["source"] for app in self.custom_apps.values()}:
                asyncio.create_task(self._handle_custom_push(payload))
            else:
                _LOGGER.debug("reCamera %s: ignoring foreign webhook payload", self.name)
            return
        if not self.has_motion_app:
            return
        self.push_received += 1
        asyncio.create_task(self._handle_push_payload(payload))

    async def _handle_custom_push(self, payload: dict[str, Any]) -> None:
        """Publish a custom app's event with a stable, device scoped HA contract."""
        source = payload["source"]
        event_type = str(payload.get("event") or "")[:64]
        if not APP_ID.fullmatch(event_type):
            return
        self.app_seen_at[source] = time.monotonic()
        self.reachable = True
        self._notify_listeners()
        if event_type == "heartbeat":
            return
        data = payload.get("data")
        if not isinstance(data, dict):
            data = {}
        app = next(app for app in self.custom_apps.values() if app["source"] == source)
        event = {
            "device": self.name,
            "device_id": self.device_identifier,
            "ha_device_id": self.ha_device_id,
            "entry_id": self.entry.entry_id,
            "host": self.host,
            "app_id": app["id"],
            "source": source,
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        self.events.appendleft(event)
        self.hass.bus.async_fire(f"{DOMAIN}_event", event)
        if payload.get("alert") is True and self.ha_notification:
            await self.hass.services.async_call(
                "persistent_notification", "create",
                {"title": f"{self.name}: {app['name']}",
                 "message": str(payload.get("message") or event_type)[:500]},
                blocking=False,
            )

    async def _handle_push_payload(self, payload: dict[str, Any]) -> None:
        event_type = str(payload.get("event") or "")
        if event_type == "test":
            self.push_error = ""
            self._notify_listeners()
            return
        if event_type not in ("motion_start", "motion_end"):
            return

        try:
            event_id = int(payload.get("event_id") or 0)
        except (TypeError, ValueError):
            event_id = 0

        image_bytes: bytes | None = None
        image = payload.get("image")
        if isinstance(image, dict) and image.get("data"):
            try:
                image_bytes = base64.b64decode(image["data"])
            except Exception:  # noqa: BLE001 - a broken attachment is not fatal
                image_bytes = None

        await self._emit(
            event_type,
            event_id=event_id,
            capture_ms=payload.get("capture_unix_ms"),
            status=payload,
            image_bytes=image_bytes,
        )

    # -------------------------------------------------------------- events
    async def _emit(
        self,
        event_type: str,
        event_id: int,
        capture_ms: Any = None,
        status: dict[str, Any] | None = None,
        image_bytes: bytes | None = None,
    ) -> None:
        if not self.has_motion_app:
            return
        key = (event_id, event_type)
        async with self._lock:
            if event_id and self._seen.get(key):
                return
            if event_id:
                self._seen[key] = True
                while len(self._seen) > SEEN_EVENTS:
                    self._seen.popitem(last=False)

            if event_type == "motion_start":
                self.motion = True
                self.last_motion_at = datetime.now(timezone.utc)
            elif event_type == "motion_end":
                self.motion = False

            if image_bytes is None and event_type == "motion_start":
                image_bytes = await self._fetch_event_snapshot(event_id)

            event = self._build_event(event_type, event_id, capture_ms, status)
            if image_bytes and event_type == "motion_start":
                event["image_url"] = await self._store_snapshot(image_bytes, event_id)
                self.last_image = image_bytes
                self.last_image_at = datetime.now(timezone.utc)

            self.last_event = event
            self.events.appendleft(event)
            self._notify_listeners()

        self.hass.bus.async_fire(EVENT_MOTION, dict(event))
        if event_type == "motion_start" and self.ha_notification:
            await self._create_persistent_notification(event)

    def _build_event(
        self,
        event_type: str,
        event_id: int,
        capture_ms: Any,
        status: dict[str, Any] | None,
    ) -> dict[str, Any]:
        status = status or self.status
        bbox = status.get("bbox")
        captured_at = None
        try:
            if capture_ms:
                captured_at = datetime.fromtimestamp(float(capture_ms) / 1000.0, tz=timezone.utc)
        except (TypeError, ValueError):
            captured_at = None

        return {
            "device": self.name,
            "device_id": self.device_identifier,
            "entry_id": self.entry.entry_id,
            "ha_device_id": self.ha_device_id,
            "host": self.host,
            "event": event_type,
            "event_id": event_id,
            "motion": event_type == "motion_start",
            "captured_at": captured_at.isoformat() if captured_at else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "motion_pixels": int(status.get("motion_pixels") or 0),
            "largest_blob_pixels": int(status.get("largest_blob_pixels") or 0),
            "motion_ratio": float(status.get("motion_ratio") or 0.0),
            "bbox": bbox if isinstance(bbox, list) and len(bbox) == 4 else None,
            "analysis_width": status.get("analysis_width"),
            "analysis_height": status.get("analysis_height"),
            "image_url": None,
        }

    async def _fetch_event_snapshot(self, event_id: int) -> bytes | None:
        try:
            return await self.client.async_snapshot(event_id if event_id else None)
        except RecameraDeviceError as err:
            _LOGGER.debug("reCamera %s: snapshot failed: %s", self.name, err)
            return None

    async def async_snapshot(self, event_id: int | None = None) -> bytes | None:
        """Live still for the camera entity; never raises."""

        try:
            return await self.client.async_snapshot(event_id)
        except RecameraDeviceError:
            return None

    async def _store_snapshot(self, image_bytes: bytes, event_id: int) -> str | None:
        """Persist the frame under www/ so notifications can attach it."""

        folder = self.hass.config.path("www", WWW_SUBDIR, self.device_identifier)
        self._image_counter += 1
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"motion_{stamp}_e{event_id}_{self._image_counter:04d}.jpg"

        def _write() -> str | None:
            try:
                os.makedirs(folder, exist_ok=True)
                with open(os.path.join(folder, filename), "wb") as handle:
                    handle.write(image_bytes)
                self._prune(folder)
                return f"/local/{WWW_SUBDIR}/{self.device_identifier}/{filename}"
            except OSError:
                _LOGGER.exception("reCamera %s: cannot save snapshot", self.name)
                return None

        url = await self.hass.async_add_executor_job(_write)
        if url:
            self.last_image_url = url
            self.last_image_path = os.path.join(folder, filename)
        return url

    def _prune(self, folder: str) -> None:
        keep = max(1, self.snapshot_keep)
        try:
            entries = [
                os.path.join(folder, name)
                for name in os.listdir(folder)
                if name.startswith("motion_") and name.endswith(".jpg")
            ]
        except OSError:
            return
        if len(entries) <= keep:
            return
        entries.sort(key=lambda path: os.path.getmtime(path))
        for stale in entries[: len(entries) - keep]:
            try:
                os.remove(stale)
            except OSError:
                pass

    async def _create_persistent_notification(self, event: dict[str, Any]) -> None:
        chinese = str(self.hass.config.language or "").lower().startswith("zh")
        zone_count = len(self.zones)
        if chinese:
            title = f"{self.name} 选区运动告警"
            message = (
                f"检测区域 {zone_count} 个，运动像素 {event['motion_pixels']}，"
                f"占比 {event['motion_ratio'] * 100:.2f}%。"
            )
        else:
            title = f"{self.name} motion alert"
            message = (
                f"{zone_count} zone(s), {event['motion_pixels']} motion pixels "
                f"({event['motion_ratio'] * 100:.2f}%)."
            )
        if event.get("image_url"):
            message += f"\n\n![snapshot]({event['image_url']})"

        self._event_counter += 1
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": f"{DOMAIN}_{self.entry.entry_id}_{event.get('event_id') or self._event_counter}",
            },
            blocking=False,
        )

    # -------------------------------------------------------------- commands
    async def async_save_config(self, config: dict[str, Any]) -> dict[str, Any]:
        result = await self.client.async_set_config(config)
        if isinstance(result, dict):
            self.config = result
        else:
            self.config = await self.client.async_get_config()
        self.configured = bool(self.zones)
        self._notify_listeners()
        return self.config

    async def async_set_enabled(self, enabled: bool) -> None:
        config = dict(self.config or {})
        config["enabled"] = bool(enabled)
        await self.async_save_config(config)

    async def async_reset_background(self) -> None:
        await self.client.async_reset_background()
        self.warming_up = True
        self._notify_listeners()

    async def async_set_ha_notification(self, enabled: bool) -> None:
        self.ha_notification = bool(enabled)
        options = {**self.entry.options, CONF_HA_NOTIFICATION: self.ha_notification}
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self._notify_listeners()

    async def async_set_options(self, values: dict[str, Any]) -> dict[str, Any]:
        """Store panel edits in the config entry options and apply them live."""

        options = {**self.entry.options}
        for key, validator in (
            (CONF_PREVIEW_FPS, lambda raw: max(1, min(25, int(raw)))),
            (CONF_POLL_INTERVAL, lambda raw: max(0.5, min(30.0, float(raw)))),
            (CONF_SNAPSHOT_KEEP, lambda raw: max(1, min(1000, int(raw)))),
            (CONF_HA_NOTIFICATION, bool),
            (CONF_PUSH_ENABLED, bool),
            (CONF_PUSH_INCLUDE_IMAGE, bool),
        ):
            if key in values and values[key] is not None:
                options[key] = validator(values[key])
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        self.async_apply_options()
        if options.get(CONF_PUSH_ENABLED, True) and self.push_url:
            await self.async_apply_push_settings()
        return options

    async def async_test_push(self) -> dict[str, Any]:
        result = await self.client.async_test_notify()
        self.notify_state = await self.client.async_get_notify()
        self._notify_listeners()
        return result if isinstance(result, dict) else {}

    async def async_set_push(self, enabled: bool) -> None:
        self.push_enabled = bool(enabled)
        options = {**self.entry.options, CONF_PUSH_ENABLED: self.push_enabled}
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        await self.async_apply_push_settings()

    # ------------------------------------------------------------- listeners
    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        self._listeners.add(update_callback)

        @callback
        def _remove() -> None:
            self._listeners.discard(update_callback)

        return _remove

    @callback
    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:  # noqa: BLE001 - one bad entity must not stop others
                _LOGGER.exception("reCamera %s: listener failed", self.name)


def resolve_device(hass: HomeAssistant, identifier: str, entry_id: str) -> Any:
    """Device registry lookup that works with both the old and the new API.

    ``async_get_device`` is deprecated as of 2026.9 and ``async_get_device_by_identifier``
    does not exist in older releases, so pick whichever is available.
    """

    registry = dr.async_get(hass)
    key = (DOMAIN, identifier)
    getter = getattr(registry, "async_get_device_by_identifier", None)
    if getter is not None:
        return getter(key, entry_id)
    return registry.async_get_device(identifiers={key})


async def _handle_webhook(hass: HomeAssistant, webhook_id: str, request) -> None:
    """Webhook entry point: find the coordinator and hand over the payload."""

    for coordinator in hass.data.get(DOMAIN, {}).values():
        if not isinstance(coordinator, RecameraCoordinator):
            continue
        if coordinator.webhook_id != webhook_id:
            continue
        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001 - malformed bodies are ignored
            _LOGGER.debug("reCamera %s: invalid webhook body", coordinator.name)
            return
        coordinator.async_handle_push(payload)
        return
