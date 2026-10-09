"""``manage`` and ``stage`` through the shared engine instance (``daemon ensure`` + lease +
heartbeat + release) with the Rust engine, and the ``serve --headless``
fallback for engines without ``daemon`` (the Python provisioning-station).

The engines here are fake scripts plus an in-test HTTP server; the last test
runs the real binary named by ``SENSECRAFT_ENGINE_BIN`` with a temporary
``SC_HOME`` / data dir and an empty ``PATH`` (no Docker, SSH or devices).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from solutionctl import _engine_http
from solutionctl.commands import manage, stage

TOKEN = "t" * 64


class FakeInstance:
    """The engine instance's lease API plus ``/api/device-management/active``."""

    def __init__(self, active_status=200, active_delay=0.35, lease_status=201, routes=None, require_token=True):
        self.calls = []  # (method, path, token)
        # extra {(method, path): (status, body)} answered after the token check
        self.routes = routes or {}
        self.active_status = active_status
        self.active_delay = active_delay
        self.lease_status = lease_status
        outer = self

        class H(BaseHTTPRequestHandler):
            def _reply(self, status, body):
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _handle(self, method):
                n = int(self.headers.get("Content-Length") or 0)
                if n:
                    self.rfile.read(n)
                tok = self.headers.get("X-SC-Engine-Token")
                outer.calls.append((method, self.path, tok))
                if require_token and tok != TOKEN:
                    return self._reply(401, {"detail": "Invalid or missing engine token"})
                if method == "POST" and self.path == "/api/engine/lease":
                    if outer.lease_status != 201:
                        return self._reply(outer.lease_status, {"detail": "Engine instance is shutting down"})
                    return self._reply(201, {"lease_id": "L1", "heartbeat_interval_ms": 100, "ttl_ms": 1000})
                if method == "POST" and self.path == "/api/engine/lease/L1/heartbeat":
                    return self._reply(200, {"ok": True})
                if method == "DELETE" and self.path == "/api/engine/lease/L1":
                    return self._reply(200, {"released": True})
                if method == "GET" and self.path == "/api/device-management/active":
                    time.sleep(outer.active_delay)
                    if outer.active_status != 200:
                        return self._reply(outer.active_status, {"detail": "boom"})
                    return self._reply(200, [{"solution_id": "demo"}])
                if (method, self.path) in outer.routes:
                    return self._reply(*outer.routes[(method, self.path)])
                return self._reply(404, {"detail": "Not Found"})

            def do_GET(self):
                self._handle("GET")

            def do_POST(self):
                self._handle("POST")

            def do_DELETE(self):
                self._handle("DELETE")

            def log_message(self, *a):
                pass

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def paths(self, method=None):
        return [p for m, p, _ in self.calls if method in (None, m)]


def _engine_script(tmp_path: Path, url: str, rust: bool, ensure_rc: int = 0) -> Path:
    """A fake engine binary that logs its argv to ``argv.log``.

    rust=True: ``meta --json`` lists ``daemon``; ``daemon ensure`` prints the
    instance JSON (or exits ``ensure_rc``). rust=False: the Python engine:
    ``meta --json`` without ``cli.commands``; ``serve --headless`` prints a
    ready line and waits for SIGTERM.
    """
    log = tmp_path / "argv.log"
    meta = {"version": "0.0.1", "contract_version": 6}
    if rust:
        meta["cli"] = {"commands": ["meta", "deploy", "daemon", "serve"]}
    ensure = {"base_url": url, "token": TOKEN, "instance_id": "i1", "reused": False, "pid": 4242}
    script = tmp_path / "engine"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, signal, sys, time\n"
        f"open({str(log)!r}, 'a').write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "a = sys.argv[1:]\n"
        "if a[:2] == ['meta', '--json']:\n"
        f"    print(json.dumps({meta!r})); sys.exit(0)\n"
        "if a[:2] == ['daemon', 'ensure']:\n"
        f"    if {ensure_rc}:\n"
        "        sys.stderr.write('error: the running instance serves devices from /other\\n')\n"
        f"        sys.exit({ensure_rc})\n"
        f"    print(json.dumps({ensure!r})); sys.exit(0)\n"
        "if a[:2] == ['serve', '--headless']:\n"
        "    signal.signal(signal.SIGTERM, lambda *x: sys.exit(0))\n"
        f"    print(json.dumps({{'base_url': {url!r}, 'pid': 1}}), flush=True)\n"
        "    time.sleep(30); sys.exit(0)\n"
        "sys.exit(2)\n"
    )
    script.chmod(0o755)
    return script


def _argv(tmp_path: Path):
    p = tmp_path / "argv.log"
    return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []


@pytest.fixture
def setup(tmp_path, monkeypatch):
    def _make(rust=True, ensure_rc=0, **inst_kw):
        inst = FakeInstance(**inst_kw)
        eng = _engine_script(tmp_path, inst.url, rust, ensure_rc)
        monkeypatch.setattr(_engine_http, "locate_engine", lambda: eng)
        monkeypatch.setattr(_engine_http, "_wait_healthy", lambda *a, **k: True)
        monkeypatch.setenv("PS_DEVICES_DIR", str(tmp_path / "devices"))
        monkeypatch.setenv("PS_SOLUTIONS_DIR", str(tmp_path / "solutions"))
        return inst

    return _make


def test_rust_engine_uses_daemon_ensure_lease_heartbeat_release(setup, tmp_path, capsys):
    inst = setup()
    assert manage.run("list-apps") == 0
    assert json.loads(capsys.readouterr().out) == [{"solution_id": "demo"}]
    argv = _argv(tmp_path)
    assert argv[0] == ["meta", "--json"]
    ensure = argv[1]
    assert ensure[:4] == ["daemon", "ensure", "--client-kind", "cli"]
    assert ensure[ensure.index("--devices-dir") + 1] == str(tmp_path / "devices")
    assert ensure[ensure.index("--solutions-dir") + 1] == str(tmp_path / "solutions")
    assert not any(a[:1] == ["serve"] for a in argv), "no temporary serve"
    paths = inst.paths()
    assert paths[0] == "/api/engine/lease"
    assert "/api/engine/lease/L1/heartbeat" in paths, "heartbeat while the command runs"
    assert paths[-1] == "/api/engine/lease/L1" and inst.calls[-1][0] == "DELETE"
    assert paths.index("/api/device-management/active") < paths.index("/api/engine/lease/L1")
    assert all(t == TOKEN for _, _, t in inst.calls), "runtime token on every request"


def test_lease_released_when_the_call_fails(setup):
    inst = setup(active_status=500, active_delay=0)
    assert manage.run("list-apps") == 1
    assert inst.paths("DELETE") == ["/api/engine/lease/L1"]


def test_ensure_conflict_is_exit_3(setup, tmp_path, capsys):
    inst = setup(ensure_rc=3)
    assert manage.run("list-apps") == 3
    err = capsys.readouterr().err
    assert "serves devices from /other" in err
    assert inst.calls == []


def test_instance_shutting_down_is_exit_3(setup):
    inst = setup(lease_status=503)
    assert manage.run("list-apps") == 3
    assert inst.paths("GET") == []


def test_python_engine_falls_back_to_serve_headless(setup, tmp_path, capsys):
    inst = setup(rust=False, active_delay=0)
    # the old engine's server has no runtime token
    inst.calls.clear()
    with _engine_http.engine_session() as conn:
        assert conn.mode == "headless" and conn.token is None
    argv = _argv(tmp_path)
    assert argv[0] == ["meta", "--json"]
    assert argv[1][:2] == ["serve", "--headless"]
    assert not any(a[:2] == ["daemon", "ensure"] for a in argv)
    assert inst.calls == []


def test_engine_without_meta_falls_back(tmp_path, monkeypatch):
    script = tmp_path / "engine"
    script.write_text("#!/bin/sh\nexit 2\n")
    script.chmod(0o755)
    assert _engine_http.engine_meta(script) is None
    assert not _engine_http.supports_daemon(None)
    assert not _engine_http.supports_daemon({"contract_version": 6})
    assert _engine_http.supports_daemon({"cli": {"commands": ["daemon"]}})


def _stage_args(**kw):
    import argparse

    base = dict(stage_command="list", solutions_dir=None, json=True, check=False)
    base.update(kw)
    return argparse.Namespace(**base)


ENTRIES = {"entries": [], "total_bytes": 0, "files": 0}


def test_stage_uses_the_instance_not_a_temporary_serve(setup, tmp_path, capsys):
    inst = setup(routes={("GET", "/api/staging/entries"): (200, ENTRIES)})
    assert stage.run(_stage_args()) == 0
    assert json.loads(capsys.readouterr().out)["entries"] == []
    argv = _argv(tmp_path)
    assert argv[0] == ["meta", "--json"]
    assert argv[1][:4] == ["daemon", "ensure", "--client-kind", "cli"]
    assert not any(a[:1] == ["serve"] for a in argv), "no temporary serve"
    paths = inst.paths()
    assert paths[0] == "/api/engine/lease"
    assert paths.index("/api/staging/entries") < paths.index("/api/engine/lease/L1")
    assert paths[-1] == "/api/engine/lease/L1" and inst.calls[-1][0] == "DELETE"
    assert all(t == TOKEN for _, _, t in inst.calls), "runtime token on every request"


def test_stage_lease_released_when_the_call_fails(setup, capsys):
    inst = setup(routes={("GET", "/api/staging/entries"): (500, {"detail": "boom"})})
    assert stage.run(_stage_args()) == 2
    assert inst.paths("DELETE") == ["/api/engine/lease/L1"]


def test_stage_ensure_conflict_is_exit_3(setup, capsys):
    inst = setup(ensure_rc=3)
    assert stage.run(_stage_args()) == 3
    assert "serves devices from /other" in capsys.readouterr().err
    assert inst.calls == []


def test_stage_instance_shutting_down_is_exit_3(setup):
    inst = setup(lease_status=503)
    assert stage.run(_stage_args()) == 3
    assert inst.paths("GET") == []


def test_stage_requires_desktop_app_is_exit_4(setup, capsys):
    body = {"success": False, "error": "requires_desktop_app", "detail": "needs the desktop App", "group": "staging"}
    setup(routes={("GET", "/api/staging/entries"): (501, body)})
    assert stage.run(_stage_args()) == 4
    assert "desktop App" in capsys.readouterr().err


def test_stage_python_engine_falls_back_to_serve_headless(setup, tmp_path, capsys):
    inst = setup(rust=False, require_token=False, routes={("GET", "/api/staging/entries"): (200, ENTRIES)})
    assert stage.run(_stage_args()) == 0
    argv = _argv(tmp_path)
    assert argv[1][:2] == ["serve", "--headless"]
    assert not any(a[:2] == ["daemon", "ensure"] for a in argv)
    assert inst.calls == [("GET", "/api/staging/entries", None)]


@pytest.mark.skipif(
    not os.environ.get("SENSECRAFT_ENGINE_BIN") or sys.platform == "win32",
    reason="needs SENSECRAFT_ENGINE_BIN (Rust engine)",
)
def test_real_rust_engine_manage_through_instance(tmp_path):
    """manage list-apps against the real binary: instance started by ensure,
    devices dir passed, lease released afterwards."""
    bin_ = os.environ["SENSECRAFT_ENGINE_BIN"]
    devices = tmp_path / "devices"
    devices.mkdir()
    env = {
        "SENSECRAFT_ENGINE_BIN": bin_,
        "SC_HOME": str(tmp_path / "sc-home"),
        "HOME": str(tmp_path / "home"),
        "PS_DATA_DIR": str(tmp_path / "data"),
        "PS_LOGS_DIR": str(tmp_path / "data/logs"),
        "PS_CACHE_DIR": str(tmp_path / "data/cache"),
        "PS_DEVICES_DIR": str(devices),
        "PS_SOLUTIONS_DIR": str(Path(__file__).resolve().parents[3] / "solutions"),
        "SC_ENGINE_IDLE_EXIT_MS": "60000",
        # nothing on PATH: no docker / ssh can be reached
        "PATH": str(tmp_path / "empty-path"),
        "PYTHONPATH": os.pathsep.join(sys.path),
    }
    try:
        r = subprocess.run([sys.executable, "-m", "solutionctl.cli", "manage", "list-apps"],
                           capture_output=True, text=True, env=env, timeout=120)
        assert r.returncode == 0, r.stderr
        assert isinstance(json.loads(r.stdout), list)
        assert "Engine instance at" in r.stderr
        st = subprocess.run([bin_, "daemon", "status"], capture_output=True, text=True, env=env, timeout=30)
        assert st.returncode == 0, st.stderr
        ping = json.loads(st.stdout)
        assert ping["devices_dir"] == str(devices)
        assert ping["leases"] == 0, "lease released on exit"
    finally:
        subprocess.run([bin_, "daemon", "stop"], capture_output=True, env=env, timeout=30)


@pytest.mark.skipif(
    not os.environ.get("SENSECRAFT_ENGINE_BIN") or sys.platform == "win32",
    reason="needs SENSECRAFT_ENGINE_BIN (Rust engine)",
)
def test_real_rust_engine_stage_through_instance(tmp_path):
    """stage list against the real binary: the instance is used (staging is a
    Python route group, so without the App's backend the answer is 501 ->
    exit 4) and the lease is released afterwards."""
    bin_ = os.environ["SENSECRAFT_ENGINE_BIN"]
    devices = tmp_path / "devices"
    devices.mkdir()
    env = {
        "SENSECRAFT_ENGINE_BIN": bin_,
        "SC_HOME": str(tmp_path / "sc-home"),
        "HOME": str(tmp_path / "home"),
        "PS_DATA_DIR": str(tmp_path / "data"),
        "PS_LOGS_DIR": str(tmp_path / "data/logs"),
        "PS_CACHE_DIR": str(tmp_path / "data/cache"),
        "PS_DEVICES_DIR": str(devices),
        "PS_SOLUTIONS_DIR": str(Path(__file__).resolve().parents[3] / "solutions"),
        "SC_ENGINE_IDLE_EXIT_MS": "60000",
        "PATH": str(tmp_path / "empty-path"),
        "PYTHONPATH": os.pathsep.join(sys.path),
    }
    try:
        r = subprocess.run([sys.executable, "-m", "solutionctl.cli", "stage", "list"],
                           capture_output=True, text=True, env=env, timeout=120)
        assert r.returncode == 4, (r.returncode, r.stderr)
        assert "Engine instance at" in r.stderr
        assert "serve --headless" not in r.stderr
        st = subprocess.run([bin_, "daemon", "status"], capture_output=True, text=True, env=env, timeout=30)
        assert st.returncode == 0, st.stderr
        assert json.loads(st.stdout)["leases"] == 0, "lease released on exit"
    finally:
        subprocess.run([bin_, "daemon", "stop"], capture_output=True, env=env, timeout=30)
