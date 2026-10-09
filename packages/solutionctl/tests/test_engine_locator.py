"""Unit tests for the three-level engine resolver."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest
from solutionctl import engine_locator as el
from solutionctl.engine_locator import EngineNotFoundError, locate_engine


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Keep Rust-engine discovery (~/.sensecraft, PATH) away from the real host."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("PATH", str(tmp_path / "emptybin"))


def _make_engine(dir_path: Path, with_internal: bool = True) -> Path:
    """Create a fake executable engine binary (+ optional _internal dir)."""
    binp = dir_path / "provisioning-station"
    binp.write_text("#!/bin/sh\necho fake\n")
    binp.chmod(binp.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    if with_internal:
        (dir_path / "_internal").mkdir()
    return binp


# --------------------------------------------------------------------------- #
# Level 1: env var
# --------------------------------------------------------------------------- #
def test_level1_env(tmp_path, monkeypatch):
    binp = _make_engine(tmp_path)
    monkeypatch.setenv("SENSECRAFT_ENGINE_BIN", str(binp))
    # Point handshake/native away so only level-1 can succeed.
    assert locate_engine(handshake_path=tmp_path / "nope.json") == binp


def test_level1_env_invalid_falls_through(tmp_path, monkeypatch):
    # Env points at a non-executable file -> invalid -> fall through to error.
    bad = tmp_path / "notexec"
    bad.write_text("x")
    bad.chmod(0o644)
    monkeypatch.setenv("SENSECRAFT_ENGINE_BIN", str(bad))
    monkeypatch.setattr(el, "_from_native", lambda: None)
    with pytest.raises(EngineNotFoundError):
        locate_engine(handshake_path=tmp_path / "nope.json")


# --------------------------------------------------------------------------- #
# Level 2: handshake file
# --------------------------------------------------------------------------- #
def test_level2_handshake(tmp_path, monkeypatch):
    monkeypatch.delenv("SENSECRAFT_ENGINE_BIN", raising=False)
    monkeypatch.setattr(el, "_from_native", lambda: None)
    binp = _make_engine(tmp_path)
    hs = tmp_path / "engine.json"
    hs.write_text(json.dumps({"schema_version": 1, "bin": str(binp)}))
    assert locate_engine(handshake_path=hs) == binp


def test_level2_handshake_missing_bin_field(tmp_path, monkeypatch):
    monkeypatch.delenv("SENSECRAFT_ENGINE_BIN", raising=False)
    monkeypatch.setattr(el, "_from_native", lambda: None)
    hs = tmp_path / "engine.json"
    hs.write_text(json.dumps({"schema_version": 1}))
    with pytest.raises(EngineNotFoundError):
        locate_engine(handshake_path=hs)


def test_level2_handshake_corrupt(tmp_path, monkeypatch):
    monkeypatch.delenv("SENSECRAFT_ENGINE_BIN", raising=False)
    monkeypatch.setattr(el, "_from_native", lambda: None)
    hs = tmp_path / "engine.json"
    hs.write_text("not json {{{")
    with pytest.raises(EngineNotFoundError):
        locate_engine(handshake_path=hs)


def test_level1_precedes_level2(tmp_path, monkeypatch):
    env_bin = _make_engine(tmp_path / "env_dir" if False else tmp_path)
    d2 = tmp_path / "hs"
    d2.mkdir()
    hs_bin = _make_engine(d2)
    monkeypatch.setenv("SENSECRAFT_ENGINE_BIN", str(env_bin))
    hs = tmp_path / "engine.json"
    hs.write_text(json.dumps({"bin": str(hs_bin)}))
    # Env wins.
    assert locate_engine(handshake_path=hs) == env_bin


# --------------------------------------------------------------------------- #
# Level 3: native discovery (mocked)
# --------------------------------------------------------------------------- #
def test_level3_native(tmp_path, monkeypatch):
    monkeypatch.delenv("SENSECRAFT_ENGINE_BIN", raising=False)
    binp = _make_engine(tmp_path)
    monkeypatch.setattr(el, "_from_native", lambda: binp)
    assert locate_engine(handshake_path=tmp_path / "nope.json") == binp


def test_nothing_found(tmp_path, monkeypatch):
    monkeypatch.delenv("SENSECRAFT_ENGINE_BIN", raising=False)
    monkeypatch.setattr(el, "_from_native", lambda: None)
    with pytest.raises(EngineNotFoundError) as exc:
        locate_engine(handshake_path=tmp_path / "nope.json")
    msg = str(exc.value)
    assert "SENSECRAFT_ENGINE_BIN" in msg
    assert "handshake" in msg


# --------------------------------------------------------------------------- #
# onedir validation: both shapes
# --------------------------------------------------------------------------- #
def test_valid_without_internal_dev_shape(tmp_path):
    # No _internal sibling at all -> still valid (dev/shim layout).
    binp = _make_engine(tmp_path, with_internal=False)
    assert el._is_valid_engine(binp) is True


def test_valid_with_internal_dir(tmp_path):
    binp = _make_engine(tmp_path, with_internal=True)
    assert el._is_valid_engine(binp) is True


def test_valid_with_internal_junction_symlink(tmp_path):
    # Simulate a Tauri junction: _internal is a symlink to a real dir.
    target = tmp_path / "real_internal"
    target.mkdir()
    binp = _make_engine(tmp_path, with_internal=False)
    link = tmp_path / "_internal"
    os.symlink(target, link, target_is_directory=True)
    assert el._is_valid_engine(binp) is True


def test_invalid_dangling_internal_junction(tmp_path):
    # Dangling symlink named _internal -> candidate rejected.
    binp = _make_engine(tmp_path, with_internal=False)
    link = tmp_path / "_internal"
    os.symlink(tmp_path / "missing_target", link, target_is_directory=True)
    assert el._is_valid_engine(binp) is False


def test_invalid_internal_is_file(tmp_path):
    # _internal is a regular file, not a dir -> invalid.
    binp = _make_engine(tmp_path, with_internal=False)
    (tmp_path / "_internal").write_text("oops")
    assert el._is_valid_engine(binp) is False


def test_invalid_not_executable(tmp_path):
    binp = tmp_path / "provisioning-station"
    binp.write_text("x")
    binp.chmod(0o644)
    assert el._is_valid_engine(binp) is False


def test_invalid_missing_file(tmp_path):
    assert el._is_valid_engine(tmp_path / "does-not-exist") is False
    assert el._is_valid_engine(None) is False


def test_unstattable_internal_soft_passes(tmp_path, monkeypatch):
    """A sibling _internal that raises on stat (e.g. Windows WinError 448
    "untrusted mount point" on a junction) must not hard-fail an
    already-validated binary — treat it as an unreadable soft signal."""
    binp = _make_engine(tmp_path, with_internal=False)
    real_exists = Path.exists

    def fake_exists(self):
        if self.name == "_internal":
            raise OSError(448, "untrusted mount point")
        return real_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    assert el._is_valid_engine(binp) is True


# --------------------------------------------------------------------------- #
# Level 3: Linux dpkg discovery tries every known package name
# --------------------------------------------------------------------------- #
class _FakeProc:
    def __init__(self, returncode: int, stdout: str):
        self.returncode = returncode
        self.stdout = stdout


def test_linux_tries_both_deb_names(tmp_path, monkeypatch):
    """Tauri ships the deb as ``sense-craft-solution``; if the first name isn't
    installed, discovery must fall through to the next candidate name."""
    binp = _make_engine(tmp_path)
    calls = []

    def fake_run(cmd, **kw):
        pkg = cmd[2]
        calls.append(pkg)
        if pkg == "sense-craft-solution":
            return _FakeProc(1, "")  # not installed under this name
        return _FakeProc(0, f"/usr/share/doc/x\n{binp}\n")

    monkeypatch.setattr(el.subprocess, "run", fake_run)
    cands = el._native_candidates_linux()
    assert binp in cands
    assert calls == ["sense-craft-solution", "sensecraft-solution"]


def test_linux_first_deb_name_wins(tmp_path, monkeypatch):
    """A match under the first package name stops the search (no extra dpkg)."""
    binp = _make_engine(tmp_path)
    calls = []

    def fake_run(cmd, **kw):
        calls.append(cmd[2])
        return _FakeProc(0, f"{binp}\n")

    monkeypatch.setattr(el.subprocess, "run", fake_run)
    cands = el._native_candidates_linux()
    assert cands == [binp]
    assert calls == ["sense-craft-solution"]


# --------------------------------------------------------------------------- #
# Level 3: Rust engine installer layout
# --------------------------------------------------------------------------- #
def _make_rust_engine(path: Path, contract) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = json.dumps({"version": "0.0.1", "contract_version": contract})
    path.write_text(f"#!/bin/sh\necho '{meta}'\n")
    path.chmod(0o755)
    return path


def _no_env(monkeypatch):
    monkeypatch.delenv("SENSECRAFT_ENGINE_BIN", raising=False)
    monkeypatch.setattr(el, "_from_native", lambda: None)


def test_rust_engine_in_sensecraft_bin(tmp_path, monkeypatch):
    _no_env(monkeypatch)
    binp = _make_rust_engine(Path.home() / ".sensecraft" / "bin" / "sensecraft-engine", 6)
    assert locate_engine(handshake_path=tmp_path / "nope.json") == binp


def test_rust_engine_in_engine_current(tmp_path, monkeypatch):
    _no_env(monkeypatch)
    binp = _make_rust_engine(
        Path.home() / ".sensecraft" / "engine" / "current" / "sensecraft-engine", 6
    )
    assert locate_engine(handshake_path=tmp_path / "nope.json") == binp


def test_rust_engine_on_path(tmp_path, monkeypatch):
    _no_env(monkeypatch)
    binp = _make_rust_engine(tmp_path / "pathbin" / "sensecraft-engine", "6.2")
    monkeypatch.setenv("PATH", str(binp.parent))
    assert locate_engine(handshake_path=tmp_path / "nope.json") == binp


def test_rust_engine_wrong_contract_major_is_rejected(tmp_path, monkeypatch):
    _no_env(monkeypatch)
    _make_rust_engine(Path.home() / ".sensecraft" / "bin" / "sensecraft-engine", 7)
    with pytest.raises(EngineNotFoundError):
        locate_engine(handshake_path=tmp_path / "nope.json")


def test_rust_engine_bad_meta_is_rejected(tmp_path, monkeypatch):
    _no_env(monkeypatch)
    binp = Path.home() / ".sensecraft" / "bin" / "sensecraft-engine"
    binp.parent.mkdir(parents=True)
    binp.write_text("#!/bin/sh\necho not-json\n")
    binp.chmod(0o755)
    with pytest.raises(EngineNotFoundError):
        locate_engine(handshake_path=tmp_path / "nope.json")


def test_handshake_precedes_rust_install(tmp_path, monkeypatch):
    _no_env(monkeypatch)
    _make_rust_engine(Path.home() / ".sensecraft" / "bin" / "sensecraft-engine", 6)
    hsbin = _make_engine(tmp_path)
    hs = tmp_path / "engine.json"
    hs.write_text(json.dumps({"bin": str(hsbin)}))
    assert locate_engine(handshake_path=hs) == hsbin


def test_rust_install_precedes_native(tmp_path, monkeypatch):
    monkeypatch.delenv("SENSECRAFT_ENGINE_BIN", raising=False)
    native = _make_engine(tmp_path)
    monkeypatch.setattr(el, "_from_native", lambda: native)
    binp = _make_rust_engine(Path.home() / ".sensecraft" / "bin" / "sensecraft-engine", 6)
    assert locate_engine(handshake_path=tmp_path / "nope.json") == binp


def test_windows_candidates(monkeypatch):
    monkeypatch.setattr(el.platform, "system", lambda: "Windows")
    names = [c.name for c in el._rust_install_candidates()]
    assert names == [
        "sensecraft-engine.cmd",
        "sensecraft-engine.exe",
        "sensecraft-engine.cmd",
        "sensecraft-engine.exe",
    ]
