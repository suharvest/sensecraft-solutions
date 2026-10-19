"""Talk to the engine's REST server.

Two ways to get one:

* :func:`engine_session` (``manage``, ``stage``): with the Rust engine (its ``meta --json``
  lists the ``daemon`` command), ``<bin> daemon ensure`` finds or starts the
  shared engine instance, this process takes a lease on it, heartbeats the
  lease while the command runs and releases it on exit. The instance itself
  keeps running (it exits on its own once idle). Every request carries the
  instance's runtime token. Older engines (the Python ``provisioning-station``
  has no ``daemon`` command) fall back to :func:`headless_engine`.
* :func:`headless_engine` (the fallback above): ``serve
  --headless`` prints a JSON ready line with its loopback ``base_url``; start
  it, wait for health, run HTTP calls against it and shut it down.

Networking uses the stdlib (``urllib``) so the thin client keeps no
third-party runtime dependency.
"""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from ._env import engine_env
from ._redact import redact
from .engine_locator import locate_engine

PUMP_TIMEOUT = 5.0
READY_TIMEOUT = 30.0
HEALTH_TIMEOUT = 30.0


class EngineHttpError(RuntimeError):
    """The engine answered with an error status."""

    def __init__(self, status: int, detail: str, error: str = ""):
        super().__init__(f"engine returned {status}: {detail}")
        self.status = status
        self.detail = detail
        # Machine-readable error id from the body (``"error"``), e.g.
        # ``requires_desktop_app`` for a route the Rust engine leaves to the
        # Python sidecar.
        self.error = error


class EngineConflictError(RuntimeError):
    """``daemon ensure`` refused: the running instance cannot be reused for
    this request (other devices directory, version / policy conflict) or is
    shutting down. The engine CLI's exit code 3."""


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
    token: Optional[str] = None,
) -> Any:
    """One JSON call. Raises :class:`EngineHttpError` for 4xx/5xx.

    ``token``: the Rust engine instance's runtime token (sent as
    ``X-SC-Engine-Token``).
    """
    data = None
    headers = {}
    if token:
        headers["X-SC-Engine-Token"] = token
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
        error = ""
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                detail = parsed.get("detail", raw)
                error = str(parsed.get("error") or "")
        except ValueError:
            pass
        raise EngineHttpError(e.code, str(detail), error) from None
    return json.loads(body) if body else None


def get(base_url: str, path: str, timeout: float = 60.0, token: Optional[str] = None) -> Any:
    return request(base_url, path, "GET", timeout=timeout, token=token)


def post(
    base_url: str, path: str, payload: Any = None, timeout: float = 60.0, token: Optional[str] = None
) -> Any:
    return request(base_url, path, "POST", payload, timeout=timeout, token=token)


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


def _close_quietly(stream) -> None:
    """Close a stream nobody is waiting on any more."""
    with contextlib.suppress(Exception):
        stream.close()


def _pump_stderr(proc: subprocess.Popen) -> None:
    """Forward the engine's log lines, redacted, to this process's stderr."""
    if proc.stderr is None:  # pragma: no cover - always piped above
        return
    # When the teardown gives up waiting and closes the pipe under this
    # thread, the pending read -- or the write of what it had already read --
    # raises. Neither is worth reporting: the CLI is on its way out.
    with contextlib.suppress(ValueError, OSError):
        for line in proc.stderr:
            sys.stderr.write(redact(line))
    _close_quietly(proc.stderr)


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
        try:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        finally:
            # Wait for the log pump: the engine's last lines (often the
            # reason it stopped) are written as it exits, and a daemon thread
            # would be cut off when the CLI returns. Bounded, because the
            # thread can block on a stderr nothing is draining.
            pump.join(timeout=PUMP_TIMEOUT)
            if pump.is_alive() and proc.stderr is not None:
                # Give the fd back rather than hold it for the rest of
                # this process's life -- but not on this thread: closing a
                # stream another thread is mid-read on waits for that read,
                # and a descendant of the engine can keep the write end open
                # long after the engine itself is gone.
                #
                # This bounds the teardown, not the cleanup: if that
                # descendant never lets go, the thread and the fd stay until
                # the process exits. Fine for a CLI that does this once per
                # run; something that spawned engines in a loop would need a
                # way to cancel it.
                threading.Thread(
                    target=_close_quietly, args=(proc.stderr,), daemon=True
                ).start()


# -- shared engine instance (Rust engine) -------------------------------------------

META_TIMEOUT = 30.0
ENSURE_TIMEOUT = 60.0
#: the engine CLI's "environment not ready / instance conflict" exit code
EXIT_CONFLICT = 3


@dataclass
class EngineConn:
    """A reachable engine REST server."""

    base_url: str
    #: runtime token of a shared instance (None for ``serve --headless``)
    token: Optional[str] = None
    #: ``"instance"`` (daemon ensure + lease) or ``"headless"``
    mode: str = "headless"
    lease_id: Optional[str] = None
    info: Dict[str, Any] = field(default_factory=dict)

    def get(self, path: str, timeout: float = 60.0) -> Any:
        return get(self.base_url, path, timeout=timeout, token=self.token)

    def post(self, path: str, payload: Any = None, timeout: float = 60.0) -> Any:
        return post(self.base_url, path, payload, timeout=timeout, token=self.token)


def engine_meta(engine, env: Optional[Dict[str, str]] = None) -> Optional[dict]:
    """``<bin> meta --json`` as a dict; None when the engine has no such
    command or prints something else."""
    try:
        out = subprocess.run(
            [str(engine), "meta", "--json"],
            capture_output=True,
            text=True,
            timeout=META_TIMEOUT,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    try:
        obj = json.loads(out.stdout)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def supports_daemon(meta: Optional[dict]) -> bool:
    """The engine can run a shared instance (``daemon ensure``)."""
    if not meta:
        return False
    commands = (meta.get("cli") or {}).get("commands") or []
    return isinstance(commands, list) and "daemon" in commands


def _client_id() -> str:
    return f"solutionctl-{os.getpid()}"


def ensure_args(engine, env: Dict[str, str], client_id: str) -> List[str]:
    """``daemon ensure`` command line. The directories ``engine_env`` derived
    are passed as flags: ``PS_DEVICES_DIR`` -> ``--devices-dir`` (a running
    instance serving another catalog is then a conflict, exit 3, never reused
    silently), ``PS_SOLUTIONS_DIR`` -> ``--solutions-dir`` (used when a new
    instance is started)."""
    cmd = [str(engine), "daemon", "ensure", "--client-kind", "cli", "--client-id", client_id]
    if env.get("PS_SOLUTIONS_DIR"):
        cmd += ["--solutions-dir", env["PS_SOLUTIONS_DIR"]]
    if env.get("PS_DEVICES_DIR"):
        cmd += ["--devices-dir", env["PS_DEVICES_DIR"]]
    return cmd


def _heartbeat(conn: EngineConn, interval: float, stop: threading.Event) -> None:
    while not stop.wait(interval):
        with contextlib.suppress(Exception):
            request(conn.base_url, f"/api/engine/lease/{conn.lease_id}/heartbeat", "POST",
                    timeout=5.0, token=conn.token)


@contextmanager
def instance_engine(engine, env: Dict[str, str]) -> Iterator[EngineConn]:
    """``daemon ensure`` + lease (heartbeated) for the duration of the block."""
    client_id = _client_id()
    try:
        out = subprocess.run(
            ensure_args(engine, env, client_id),
            capture_output=True,
            text=True,
            timeout=ENSURE_TIMEOUT,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        if exc.stderr:
            sys.stderr.write(redact(exc.stderr))
        raise RuntimeError(f"`daemon ensure` timed out after {ENSURE_TIMEOUT}s") from None
    if out.stderr:
        sys.stderr.write(redact(out.stderr))
    if out.returncode == EXIT_CONFLICT:
        raise EngineConflictError(
            "the running engine instance cannot be used for this request (see the message above); "
            f"`{engine} daemon stop` ends it when it is idle"
        )
    if out.returncode != 0:
        raise RuntimeError(f"`daemon ensure` failed (exit {out.returncode})")
    try:
        info = json.loads(out.stdout)
        base_url, token = info["base_url"].rstrip("/"), info["token"]
    except (ValueError, KeyError, TypeError, AttributeError):
        raise RuntimeError("`daemon ensure` printed no base_url / token") from None
    conn = EngineConn(base_url=base_url, token=token, mode="instance", info=info)
    try:
        lease = request(base_url, "/api/engine/lease", "POST",
                        {"kind": "cli", "client_id": client_id}, timeout=15.0, token=token)
    except EngineHttpError as exc:
        if exc.status == 503:
            raise EngineConflictError("the engine instance is shutting down; retry in a moment") from None
        raise
    conn.lease_id = (lease or {}).get("lease_id")
    interval = max(float((lease or {}).get("heartbeat_interval_ms") or 15000), 50.0) / 1000.0
    reused = "reused" if info.get("reused") else "started"
    print(f"Engine instance at {base_url} ({reused}, pid={info.get('pid', '?')})", file=sys.stderr)
    stop = threading.Event()
    beat = None
    if conn.lease_id:
        beat = threading.Thread(target=_heartbeat, args=(conn, interval, stop), daemon=True)
        beat.start()
    try:
        yield conn
    finally:
        stop.set()
        if beat is not None:
            beat.join(timeout=6)
        if conn.lease_id:
            with contextlib.suppress(Exception):
                request(base_url, f"/api/engine/lease/{conn.lease_id}", "DELETE", timeout=5.0, token=token)


@contextmanager
def engine_session(solutions_dir: Optional[str] = None) -> Iterator[EngineConn]:
    """A REST server for one command: the shared Rust engine instance when
    the engine supports it (``meta --json`` lists ``daemon``), else a
    temporary ``serve --headless`` (older / Python engines)."""
    engine = locate_engine()
    print(f"Using engine: {engine}", file=sys.stderr)
    env = engine_env(solutions_dir)
    if supports_daemon(engine_meta(engine, env)):
        with instance_engine(engine, env) as conn:
            yield conn
        return
    with headless_engine(solutions_dir) as base_url:
        yield EngineConn(base_url=base_url, mode="headless")
