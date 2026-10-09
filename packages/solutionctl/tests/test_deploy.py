"""``solutionctl deploy`` event rendering and exit handling (engine mocked)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from solutionctl.commands import deploy


def _fake_engine(tmp_path: Path, lines: list, rc: int = 0) -> Path:
    body = "\n".join(
        l if isinstance(l, str) else json.dumps(l) for l in lines
    )
    script = tmp_path / "fake-engine"
    script.write_text(f"#!/bin/sh\ncat <<'EOF'\n{body}\nEOF\nexit {rc}\n")
    script.chmod(0o755)
    return script


@pytest.fixture
def run_deploy(tmp_path, monkeypatch, capfd):
    monkeypatch.setattr(deploy, "engine_env", lambda *_a, **_k: dict(os.environ))

    def _run(lines, rc=0, **kw):
        eng = _fake_engine(tmp_path, lines, rc)
        monkeypatch.setattr(deploy, "locate_engine", lambda: eng)
        code = deploy.run("demo", **kw)
        return code, capfd.readouterr().out

    return _run


VERIFY = {
    "type": "verify_required",
    "step_id": "dash",
    "kind": "web_dashboard",
    "name": "Dashboard",
    "url": "http://10.0.0.5:3000",
    "endpoint": None,
    "instructions": "Open the page and check it loads.",
}
RESULT = {"type": "result", "deployment_id": "d1", "status": "completed", "devices": []}


def test_verify_required_shown_without_verbose(run_deploy):
    code, out = run_deploy([{"type": "log", "message": "pulling"}, VERIFY, RESULT])
    assert code == 0
    assert "[verify_required] Dashboard (web_dashboard)" in out
    assert "url: http://10.0.0.5:3000" in out
    assert "Open the page and check it loads." in out
    assert "pulling" not in out
    assert "[result] d1 completed" in out


def test_non_completed_result_fails_even_with_exit_0(run_deploy):
    code, out = run_deploy([{**RESULT, "status": "failed"}], rc=0)
    assert code == 1
    assert "[result] d1 failed" in out


def test_engine_exit_code_wins_when_nonzero(run_deploy):
    code, _ = run_deploy([RESULT], rc=3)
    assert code == 3


def test_python_engine_without_result_line_keeps_exit_code(run_deploy):
    ok, out = run_deploy([{"type": "deployment_completed", "status": "completed"}])
    assert ok == 0 and "[deployment_completed] completed" in out
    bad, _ = run_deploy([{"type": "deployment_completed", "status": "failed"}], rc=1)
    assert bad == 1


@pytest.mark.skipif(
    not os.environ.get("SENSECRAFT_ENGINE_BIN") or sys.platform == "win32",
    reason="needs SENSECRAFT_ENGINE_BIN (Rust engine)",
)
def test_real_rust_engine_smoke(tmp_path):
    """meta / solution list through the real binary (no devices, no instance)."""
    env = {**os.environ, "SC_HOME": str(tmp_path / "sc-home"),
           "HOME": str(tmp_path / "home")}
    cmd = [sys.executable, "-m", "solutionctl.cli"]
    meta = subprocess.run(cmd + ["meta"], capture_output=True, text=True, env=env)
    assert meta.returncode == 0, meta.stderr
    assert json.loads(meta.stdout)["contract_version"] == 6
