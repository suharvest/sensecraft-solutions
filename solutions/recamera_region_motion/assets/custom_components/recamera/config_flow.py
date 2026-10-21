"""Config and options flow for the reCamera integration."""

from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback

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
    DOMAIN,
)
from .device_client import RecameraDeviceError, async_validate_device

_LOGGER = logging.getLogger(__name__)
_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.-]*$")

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): str,
        vol.Optional(CONF_API_PORT, default=DEFAULT_API_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_RTSP_PORT, default=DEFAULT_RTSP_PORT): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=65535)
        ),
        vol.Optional(CONF_RTSP_STREAM, default=DEFAULT_RTSP_STREAM): str,
    }
)


class RecameraConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add one SG2002 reCamera, including devices awaiting an app flash."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> RecameraOptionsFlow:
        return RecameraOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            if not _HOST_RE.fullmatch(host):
                return self.async_show_form(
                    step_id="user", data_schema=USER_SCHEMA,
                    errors={CONF_HOST: "invalid_host"},
                )
            port = int(user_input.get(CONF_API_PORT) or DEFAULT_API_PORT)
            name = str(user_input.get(CONF_DEVICE_NAME) or "").strip() or DEFAULT_DEVICE_NAME

            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            try:
                health = await async_validate_device(host, port)
            except RecameraDeviceError as err:
                # A camera can be added before Solution flashes an application,
                # or while it is temporarily offline. Its card reports both
                # host reachability and motion API availability after setup.
                _LOGGER.info("reCamera %s:%s has no motion API yet: %s", host, port, err)
                health = {}
            except Exception:  # noqa: BLE001 - unexpected transport errors
                _LOGGER.exception("Unexpected error while validating %s:%s", host, port)
                health = {}
            snapshot = health.get("snapshot") or {}
            if health and not snapshot.get("enabled"):
                _LOGGER.info(
                    "reCamera %s reports no snapshot channel; alerts will not carry a frame",
                    host,
                )
            return self.async_create_entry(
                title=name,
                data={
                    CONF_HOST: host,
                    CONF_API_PORT: port,
                    CONF_DEVICE_NAME: name,
                    CONF_RTSP_PORT: int(user_input.get(CONF_RTSP_PORT) or DEFAULT_RTSP_PORT),
                    CONF_RTSP_STREAM: str(
                        user_input.get(CONF_RTSP_STREAM) or DEFAULT_RTSP_STREAM
                    ),
                },
                options={
                    CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
                    CONF_PREVIEW_FPS: DEFAULT_PREVIEW_FPS,
                    CONF_SNAPSHOT_KEEP: DEFAULT_SNAPSHOT_KEEP,
                    CONF_HA_NOTIFICATION: True,
                    CONF_PUSH_ENABLED: True,
                    CONF_PUSH_INCLUDE_IMAGE: True,
                },
            )

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)


class RecameraOptionsFlow(OptionsFlow):
    """Tune polling, preview bandwidth, snapshots and notifications."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_POLL_INTERVAL,
                    default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=30.0)),
                vol.Optional(
                    CONF_PREVIEW_FPS,
                    default=options.get(CONF_PREVIEW_FPS, DEFAULT_PREVIEW_FPS),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=25)),
                vol.Optional(
                    CONF_SNAPSHOT_KEEP,
                    default=options.get(CONF_SNAPSHOT_KEEP, DEFAULT_SNAPSHOT_KEEP),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1000)),
                vol.Optional(
                    CONF_HA_NOTIFICATION,
                    default=options.get(CONF_HA_NOTIFICATION, True),
                ): bool,
                vol.Optional(
                    CONF_PUSH_ENABLED,
                    default=options.get(CONF_PUSH_ENABLED, True),
                ): bool,
                vol.Optional(
                    CONF_PUSH_INCLUDE_IMAGE,
                    default=options.get(CONF_PUSH_INCLUDE_IMAGE, True),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
