"""Talk to the engine's headless REST server.

``serve --headless`` prints a JSON ready line with its loopback ``base_url``;
these helpers start it, wait for health, run HTTP calls against it and shut it
down. Shared by ``manage`` and ``stage``.

Networking uses the stdlib (``urllib``) so the thin client keeps no
third-party runtime dependency.
"""

from __future__ import annotations

import contextlib
import json
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from ._env import engine_env
from ._redact import redact
from .engine_locator import locate_engine

READY_TIMEOUT = 30.0
HEALTH_TIMEOUT = 30.0


class EngineHttpError(RuntimeError):
    """The engine answered with an error status."""

    def __init__(self, status: int, detail: str):
        super().__init__(f"engine returned {status}: {detail}")
        self.status = status
        self.detail = detail


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


def request(
    base_url: str,
    path: str,
    method: str = "GET",
    payload: Any = None,
    timeout: float = 60.0,
) -> Any:
    """One JSON call. Raises :class:`EngineHttpError` for 4xx/5xx."""
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        base_url + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        detail = raw
        try:
            parsed = json.loads(raw)
            detail = parsed.get("detail", raw) if isinstance(parsed, dict) else raw
        except ValueError:
            pass
        raise EngineHttpError(e.code, str(detail)) from None
    return json.loads(body) if body else None


def get(base_url: str, path: str, timeout: float = 60.0) -> Any:
    return request(base_url, path, "GET", timeout=timeout)


def post(base_url: str, path: str, payload: Any = None, timeout: float = 60.0) -> Any:
    return request(base_url, path, "POST", payload, timeout=timeout)


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


def _pump_stderr(proc: subprocess.Popen) -> None:
    """Forward the engine's log lines, redacted, to this process's stderr."""
    if proc.stderr is None:  # pragma: no cover - always piped above
        return
    for line in proc.stderr:
        sys.stderr.write(redact(line))
    with contextlib.suppress(Exception):
        proc.stderr.close()


@contextmanager
def headless_engine(solutions_dir: Optional[str] = None) -> Iterator[str]:
    """Spawn ``serve --headless``, yield its base_url, then tear it down."""
    engine = locate_engine()
    print(f"Using engine: {engine}", file=sys.stderr)
    proc = subprocess.Popen(
        [str(engine), "serve", "--headless"],
        stdout=subprocess.PIPE,
        # Piped, not inherited: the engine logs what it is doing, and a log
        # line can carry a credential. Everything it writes goes through the
        # same redaction as the rest of this CLI's output.
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=engine_env(solutions_dir),
    )
    pump = threading.Thread(target=_pump_stderr, args=(proc,), daemon=True)
    pump.start()
    try:
        ready = _read_ready_line(proc, READY_TIMEOUT)
        if ready is None:
            raise RuntimeError("engine did not report a ready line (serve --headless)")
        base_url = ready["base_url"]
        print(f"Engine serving at {base_url} (pid={ready.get('pid')})", file=sys.stderr)
        if not _wait_healthy(base_url, HEALTH_TIMEOUT):
            raise RuntimeError(f"engine never became healthy at {base_url}")
        yield base_url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
