"""Unit tests for engine subprocess environment derivation."""

from __future__ import annotations

from pathlib import Path

from solutionctl import _env
from solutionctl._env import engine_env


def _isolate(monkeypatch, tmp_home: Path) -> None:
    """Neutralise external discovery so only the writable-dir logic is exercised."""
    monkeypatch.setattr(_env, "locate_app_devices", lambda: None)
    monkeypatch.setattr(_env, "_find_repo_solutions_dir", lambda start=None: None)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_home))
    for var in ("PS_DATA_DIR", "PS_LOGS_DIR", "PS_CACHE_DIR"):
        monkeypatch.delenv(var, raising=False)


def test_engine_env_injects_writable_dirs(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    env = engine_env()
    base = tmp_path / ".sensecraft" / "engine-runtime"
    assert env["PS_DATA_DIR"] == str(base)
    assert env["PS_LOGS_DIR"] == str(base / "logs")
    assert env["PS_CACHE_DIR"] == str(base / "cache")


def test_engine_env_respects_existing_writable_dirs(tmp_path, monkeypatch):
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("PS_DATA_DIR", "/custom/data")
    monkeypatch.setenv("PS_LOGS_DIR", "/custom/logs")
    env = engine_env()
    # Pre-set values are never overwritten...
    assert env["PS_DATA_DIR"] == "/custom/data"
    assert env["PS_LOGS_DIR"] == "/custom/logs"
    # ...while an unset one still gets the per-user default.
    assert env["PS_CACHE_DIR"] == str(tmp_path / ".sensecraft" / "engine-runtime" / "cache")


def test_engine_env_injects_logs_cache_when_only_data_preset(tmp_path, monkeypatch):
    # PS_DATA_DIR is preset but logs/cache are not — they are independent fields
    # in the engine, so both must still be injected (not derived from PS_DATA_DIR).
    _isolate(monkeypatch, tmp_path)
    monkeypatch.setenv("PS_DATA_DIR", "/custom/data")
    env = engine_env()
    base = tmp_path / ".sensecraft" / "engine-runtime"
    assert env["PS_DATA_DIR"] == "/custom/data"
    assert env["PS_LOGS_DIR"] == str(base / "logs")
    assert env["PS_CACHE_DIR"] == str(base / "cache")
