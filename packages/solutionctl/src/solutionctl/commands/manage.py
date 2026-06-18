"""``solutionctl manage`` — drive the engine's headless REST server.

Starts ``<bin> serve --headless``, reads the JSON ready line from stdout to
discover the loopback ``base_url``, polls health, calls the appropriate REST
endpoint, then shuts the server down.

Networking uses the stdlib (``urllib``) so the thin client has no third-party
runtime dependency.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import Iterator, Optional

from ..engine_locator import locate_engine

_READY_TIMEOUT = 30.0
_HEALTH_TIMEOUT = 30.0


def _read_ready_line(proc: subprocess.Popen, timeout: float) -> Optional[dict]:
    """Read stdout lines until a JSON ready object appears (or timeout)."""
    deadline = time.monotonic() + timeout
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return None  # server exited before printing ready
        line = proc.stdout.readline()
        if not line:
            continue
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if isinstance(obj, dict) and obj.get("base_url"):
            return obj
    return None


def _http_get(url: str, timeout: float = 15.0) -> object:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body) if body else None


def _wait_healthy(base_url: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for path in ("/health", "/api/health", "/docs"):
            try:
                req = urllib.request.Request(base_url + path, method="GET")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status < 500:
                        return True
            except urllib.error.HTTPError as e:
                # Any HTTP response (even 404) means the server is up.
                if e.code < 500:
                    return True
            except (urllib.error.URLError, OSError):
                pass
        time.sleep(0.3)
    return False


@contextmanager
def _headless_engine() -> Iterator[str]:
    """Spawn ``serve --headless``, yield its base_url, then tear it down."""
    engine = locate_engine()
    print(f"Using engine: {engine}", file=sys.stderr)
    proc = subprocess.Popen(
        [str(engine), "serve", "--headless"],
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1,
    )
    try:
        ready = _read_ready_line(proc, _READY_TIMEOUT)
        if ready is None:
            raise RuntimeError("engine did not report a ready line (serve --headless)")
        base_url = ready["base_url"]
        print(f"Engine serving at {base_url} (pid={ready.get('pid')})", file=sys.stderr)
        if not _wait_healthy(base_url, _HEALTH_TIMEOUT):
            raise RuntimeError(f"engine never became healthy at {base_url}")
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def list_apps() -> int:
    """List active/deployed applications via the REST API."""
    with _headless_engine() as base_url:
        data = _http_get(base_url + "/api/device-management/active")
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


def run(subcommand: str) -> int:
    """Dispatch a manage subcommand."""
    if subcommand in ("list-apps", "list"):
        return list_apps()
    print(f"Unknown manage subcommand: {subcommand!r}", file=sys.stderr)
    print("Available: list-apps", file=sys.stderr)
    return 2
