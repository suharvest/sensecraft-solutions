"""The reCamera integration: region motion detection with a sidebar panel."""

from __future__ import annotations

import base64
import json
import logging
import os
import shutil
from typing import Any

import voluptuous as vol

from homeassistant.components import frontend, panel_custom, websocket_api
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)

from .const import (
    CONF_HOST,
    DOMAIN,
    PANEL_TITLE,
    PANEL_URL_PATH,
    PLATFORMS,
    STATIC_PATH,
)
from .coordinator import RecameraCoordinator, resolve_device
from .device_client import RecameraDeviceError

_LOGGER = logging.getLogger(__name__)

def _panel_version() -> str:
    """Manifest version, appended to the panel URL to bust the browser cache.

    Static paths are registered with cache headers, so a stale `recamera-panel.js`
    would otherwise survive an upgrade.
    """

    try:
        with open(
            os.path.join(os.path.dirname(__file__), "manifest.json"), encoding="utf-8"
        ) as handle:
            return str(json.load(handle).get("version") or "0")
    except (OSError, ValueError):  # noqa: PERF203 - one small file, once per start
        return "0"


_VERSION = _panel_version()

DEVICE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("device_id"): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Register the sidebar panel, websocket API, HTTP views and services."""

    hass.data.setdefault(DOMAIN, {})

    if not hass.data.get(f"{DOMAIN}_panel_registered"):
        frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_PATH, frontend_dir, cache_headers=True)]
        )
        frontend.add_extra_js_url(hass, f"{STATIC_PATH}/recamera-icon.js")
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL_PATH,
            webcomponent_name="recamera-motion-panel",
            sidebar_title=PANEL_TITLE,
            sidebar_icon="recamera_motion:detect",
            module_url=f"{STATIC_PATH}/recamera-panel.js?v={_VERSION}",
            require_admin=True,
        )
        hass.data[f"{DOMAIN}_panel_registered"] = True

    if not hass.data.get(f"{DOMAIN}_api_registered"):
        hass.data[f"{DOMAIN}_api_registered"] = True
        _register_websocket_commands(hass)

    if not hass.data.get(f"{DOMAIN}_services_registered"):
        hass.data[f"{DOMAIN}_services_registered"] = True
        _register_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one camera."""

    coordinator = RecameraCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await coordinator.async_setup()

    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload one camera."""

    if not await hass.config_entries.async_unload_platforms(
        entry, [Platform(platform) for platform in PLATFORMS]
    ):
        return False
    coordinator: RecameraCoordinator | None = hass.data[DOMAIN].pop(entry.entry_id, None)
    if coordinator is not None:
        await coordinator.async_shutdown()
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop the stored snapshots of a removed camera."""

    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    identifier = coordinator.device_identifier if coordinator else f"{entry.data.get(CONF_HOST)}_8080"
    folder = hass.config.path("www", "recamera", identifier)

    def _remove() -> None:
        if not os.path.isdir(folder):
            return
        for name in os.listdir(folder):
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                pass
        try:
            os.rmdir(folder)
        except OSError:
            pass

    await hass.async_add_executor_job(_remove)
    await hass.async_add_executor_job(
        shutil.rmtree,
        hass.config.path(".storage", "recamera_packages", entry.entry_id),
        True,
    )


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply option changes in place; recreating would orphan the entities."""

    coordinator: RecameraCoordinator | None = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator is None:
        return
    if coordinator.async_apply_options():
        await coordinator.async_apply_push_settings()


# ------------------------------------------------------------------ services
def _register_services(hass: HomeAssistant) -> None:
    async def _reset_background(call: ServiceCall) -> None:
        coordinator = _coordinator_for_service(hass, call)
        if coordinator is None:
            return
        await coordinator.async_reset_background()

    async def _test_push(call: ServiceCall) -> None:
        coordinator = _coordinator_for_service(hass, call)
        if coordinator is None:
            return
        try:
            await coordinator.async_test_push()
        except RecameraDeviceError as err:
            _LOGGER.warning("reCamera test push failed: %s", err)

    hass.services.async_register(
        DOMAIN, "reset_background", _reset_background, schema=DEVICE_SERVICE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, "test_push", _test_push, schema=DEVICE_SERVICE_SCHEMA
    )


def _coordinator_for_service(hass: HomeAssistant, call: ServiceCall) -> RecameraCoordinator | None:
    device_id = call.data.get("device_id")
    registry = dr.async_get(hass)
    device = registry.async_get(device_id) if device_id else None
    if device is None:
        return None
    for identifier in device.identifiers:
        if identifier[0] != DOMAIN:
            continue
        for coordinator in hass.data.get(DOMAIN, {}).values():
            if isinstance(coordinator, RecameraCoordinator) and coordinator.device_identifier == identifier[1]:
                return coordinator
    return None


# --------------------------------------------------------------- websocket
def _register_websocket_commands(hass: HomeAssistant) -> None:
    @websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/devices"})
    @websocket_api.async_response
    async def ws_devices(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        connection.send_result(msg["id"], {"devices": _device_summaries(hass)})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/add_repository",
            vol.Required("entry_id"): cv.string,
            vol.Required("url"): cv.string,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_add_repository(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        try:
            manifest = await coordinator.async_add_repository(msg["url"])
        except (ValueError, OSError) as err:
            connection.send_error(msg["id"], "invalid_repository", str(err))
            return
        connection.send_result(msg["id"], {"app": manifest})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/remove_app",
            vol.Required("entry_id"): cv.string,
            vol.Required("app_id"): cv.string,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_remove_app(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        try:
            await coordinator.async_remove_app(msg["app_id"])
        except (ValueError, OSError) as err:
            connection.send_error(msg["id"], "remove_failed", str(err))
            return
        connection.send_result(msg["id"], {})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/upload_package",
            vol.Required("entry_id"): cv.string,
            vol.Required("package"): cv.string,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_upload_package(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        try:
            manifest = await coordinator.async_upload_package(msg["package"])
        except (ValueError, OSError) as err:
            connection.send_error(msg["id"], "invalid_package", str(err))
            return
        connection.send_result(msg["id"], {"app": manifest})

    @websocket_api.websocket_command(
        {vol.Required("type"): f"{DOMAIN}/state", vol.Required("entry_id"): cv.string}
    )
    @websocket_api.async_response
    async def ws_state(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        connection.send_result(msg["id"], _state_payload(hass, coordinator))

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/refresh",
            vol.Required("entry_id"): cv.string,
        }
    )
    @websocket_api.async_response
    async def ws_refresh(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        await coordinator.async_refresh_device()
        payload = _state_payload(hass, coordinator)
        connection.send_result(msg["id"], payload)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/save_config",
            vol.Required("entry_id"): cv.string,
            vol.Required("config"): dict,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_save_config(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        try:
            config = await coordinator.async_save_config(msg["config"])
        except RecameraDeviceError as err:
            connection.send_error(msg["id"], "device_error", str(err))
            return
        connection.send_result(msg["id"], {"ok": True, "config": config})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_enabled",
            vol.Required("entry_id"): cv.string,
            vol.Required("enabled"): cv.boolean,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_enabled(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        try:
            await coordinator.async_set_enabled(msg["enabled"])
        except RecameraDeviceError as err:
            connection.send_error(msg["id"], "device_error", str(err))
            return
        connection.send_result(msg["id"], {"ok": True, "config": coordinator.config})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/reset_background",
            vol.Required("entry_id"): cv.string,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_reset_background(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        try:
            await coordinator.async_reset_background()
        except RecameraDeviceError as err:
            connection.send_error(msg["id"], "device_error", str(err))
            return
        connection.send_result(msg["id"], {"ok": True})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/notify",
            vol.Required("entry_id"): cv.string,
            vol.Optional("push_enabled"): cv.boolean,
            vol.Optional("ha_notification"): cv.boolean,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_notify(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        try:
            if "ha_notification" in msg:
                await coordinator.async_set_ha_notification(msg["ha_notification"])
            if "push_enabled" in msg:
                await coordinator.async_set_push(msg["push_enabled"])
        except RecameraDeviceError as err:
            connection.send_error(msg["id"], "device_error", str(err))
            return
        payload = _state_payload(hass, coordinator)
        connection.send_result(msg["id"], payload)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/set_options",
            vol.Required("entry_id"): cv.string,
            vol.Optional("preview_fps"): vol.Coerce(int),
            vol.Optional("poll_interval"): vol.Coerce(float),
            vol.Optional("snapshot_keep"): vol.Coerce(int),
            vol.Optional("ha_notification"): cv.boolean,
            vol.Optional("push_enabled"): cv.boolean,
            vol.Optional("push_include_image"): cv.boolean,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_set_options(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        values = {
            key: msg[key]
            for key in (
                "preview_fps",
                "poll_interval",
                "snapshot_keep",
                "ha_notification",
                "push_enabled",
                "push_include_image",
            )
            if key in msg
        }
        try:
            options = await coordinator.async_set_options(values)
        except (TypeError, ValueError) as err:
            connection.send_error(msg["id"], "invalid_option", str(err))
            return
        payload = _state_payload(hass, coordinator)
        payload["options"] = options
        connection.send_result(msg["id"], payload)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/test_push",
            vol.Required("entry_id"): cv.string,
        }
    )
    @websocket_api.require_admin
    @websocket_api.async_response
    async def ws_test_push(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        try:
            result = await coordinator.async_test_push()
        except RecameraDeviceError as err:
            connection.send_error(msg["id"], "device_error", str(err))
            return
        connection.send_result(msg["id"], {"ok": bool(result.get("ok", True)), "result": result})

    @websocket_api.websocket_command(
        {
            vol.Required("type"): f"{DOMAIN}/snapshot",
            vol.Required("entry_id"): cv.string,
        }
    )
    @websocket_api.async_response
    async def ws_snapshot(
        hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
    ) -> None:
        coordinator = _coordinator(hass, msg["entry_id"])
        if coordinator is None:
            connection.send_error(msg["id"], "not_found", "unknown reCamera")
            return
        image = await coordinator.async_snapshot()
        if not image:
            connection.send_error(msg["id"], "no_snapshot", "camera returned no frame")
            return
        connection.send_result(
            msg["id"],
            {"content_type": "image/jpeg", "data": base64.b64encode(image).decode("ascii")},
        )

    for command in (
        ws_devices,
        ws_add_repository,
        ws_remove_app,
        ws_upload_package,
        ws_state,
        ws_refresh,
        ws_save_config,
        ws_set_enabled,
        ws_reset_background,
        ws_notify,
        ws_set_options,
        ws_test_push,
        ws_snapshot,
    ):
        websocket_api.async_register_command(hass, command)


def _coordinator(hass: HomeAssistant, entry_id: str) -> RecameraCoordinator | None:
    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    return coordinator if isinstance(coordinator, RecameraCoordinator) else None


def _entity_map(hass: HomeAssistant, entry_id: str) -> dict[str, str]:
    """Map our internal keys (camera, motion, image...) to entity ids."""

    registry = er.async_get(hass)
    prefix = f"{entry_id}_"
    mapping: dict[str, str] = {}
    for entity in registry.entities.values():
        if entity.config_entry_id != entry_id or not entity.unique_id:
            continue
        if not entity.unique_id.startswith(prefix):
            continue
        key = entity.unique_id[len(prefix) :]
        mapping[key] = entity.entity_id
    return mapping


def _state_payload(hass: HomeAssistant, coordinator: RecameraCoordinator) -> dict[str, Any]:
    """Coordinator state plus the entity ids the panel needs for proxying.

    Every websocket reply must carry `entities`; the panel builds the camera
    stream and snapshot URLs from it.
    """

    payload = coordinator.as_dict()
    payload["entities"] = _entity_map(hass, coordinator.entry.entry_id)
    return payload


def _device_summaries(hass: HomeAssistant) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for coordinator in hass.data.get(DOMAIN, {}).values():
        if not isinstance(coordinator, RecameraCoordinator):
            continue
        device = resolve_device(
            hass, coordinator.device_identifier, coordinator.entry.entry_id
        )
        summary = coordinator.as_dict()
        summary["entities"] = _entity_map(hass, coordinator.entry.entry_id)
        summary.pop("config", None)
        summary.pop("events", None)
        summary.pop("status", None)
        summary["device_id"] = device.id if device else None
        summaries.append(summary)
    return summaries
