"""Unit tests for the three-level engine resolver."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from solutionctl import engine_locator as el
from solutionctl.engine_locator import EngineNotFoundError, locate_engine


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
