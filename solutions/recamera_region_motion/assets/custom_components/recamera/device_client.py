"""Async HTTP client for the reCamera motion detection API."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

from .const import DEFAULT_API_PORT

CONNECT_TIMEOUT = 5.0


class RecameraDeviceError(Exception):
    """Raised when the camera cannot be reached or answers with an error."""


class RecameraAuthError(RecameraDeviceError):
    """Raised when the device rejects the request."""


class RecameraDeviceClient:
    """Talks to one reCamera running the motion detection program."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_API_PORT,
        timeout: float = 5.0,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._host = host
        self._port = int(port or DEFAULT_API_PORT)
        self._timeout = aiohttp.ClientTimeout(total=timeout, connect=CONNECT_TIMEOUT)
        self._session = session
        self._owned_session = session is None

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def api_base(self) -> str:
        return f"http://{self._host}:{self._port}"

    async def async_connect(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            # trust_env=False keeps a host level http_proxy from hijacking
            # plain LAN traffic to the camera.
            self._session = aiohttp.ClientSession(timeout=self._timeout, trust_env=False)
            self._owned_session = True
        return self._session

    async def async_close(self) -> None:
        if self._session is not None and self._owned_session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        raw: bool = False,
        timeout: float | None = None,
    ) -> Any:
        session = await self.async_connect()
        url = f"{self.api_base}{path}"
        request_timeout = self._timeout if timeout is None else aiohttp.ClientTimeout(total=timeout)
        try:
            async with session.request(
                method,
                url,
                json=payload,
                timeout=request_timeout,
                allow_redirects=False,
            ) as response:
                if raw:
                    if response.status != 200:
                        raise RecameraDeviceError(f"HTTP {response.status} for {path}")
                    return await response.read()
                text = await response.text()
        except asyncio.TimeoutError as err:
            raise RecameraDeviceError(f"timeout calling {path}") from err
        except aiohttp.ClientError as err:
            raise RecameraDeviceError(f"cannot reach {self.api_base}: {err}") from err

        if response.status >= 500:
            raise RecameraDeviceError(f"device error HTTP {response.status}: {text[:200]}")
        if response.status >= 400:
            raise RecameraAuthError(f"device rejected {path} (HTTP {response.status}): {text[:200]}")

        try:
            return json.loads(text)
        except ValueError as err:
            raise RecameraDeviceError(f"{path} did not return JSON: {text[:200]}") from err

    async def async_health(self) -> dict[str, Any]:
        return await self._request("GET", "/api/health")

    async def async_version(self) -> dict[str, Any]:
        return await self._request("GET", "/api/version")

    async def async_status(self) -> dict[str, Any]:
        return await self._request("GET", "/api/status", timeout=4.0)

    async def async_get_config(self) -> dict[str, Any]:
        return await self._request("GET", "/api/config")

    async def async_set_config(self, config: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/api/config", payload=config)

    async def async_reset_background(self) -> dict[str, Any]:
        return await self._request("POST", "/api/background/reset", payload={})

    async def async_snapshot(self, event_id: int | None = None, timeout: float = 8.0) -> bytes:
        path = "/api/snapshot.jpg"
        if event_id is not None:
            path = f"{path}?event_id={event_id}"
        data = await self._request("GET", path, raw=True, timeout=timeout)
        return bytes(data)

    async def async_events(self, after_id: int = 0, limit: int = 25) -> dict[str, Any]:
        return await self._request("GET", f"/api/events?after_id={after_id}&limit={limit}")

    async def async_get_notify(self) -> dict[str, Any]:
        return await self._request("GET", "/api/notify")

    async def async_set_notify(self, notify: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/api/notify", payload={"notify": notify})

    async def async_test_notify(self) -> dict[str, Any]:
        return await self._request("POST", "/api/notify/test", payload={})



async def async_validate_device(host: str, port: int, timeout: float = 6.0) -> dict[str, Any]:
    """Return the device health payload, or raise RecameraDeviceError."""

    client = RecameraDeviceClient(host, port, timeout=timeout)
    try:
        health = await client.async_health()
    finally:
        await client.async_close()
    if not isinstance(health, dict) or not health.get("ok"):
        raise RecameraDeviceError("device answered but reported an error")
    return health
