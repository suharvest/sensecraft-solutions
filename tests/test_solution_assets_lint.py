"""Positive and negative test cases for scripts/ci/lint_solution_assets.py."""
from __future__ import annotations

import importlib.util
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lint_solution_assets", ROOT / "scripts" / "ci" / "lint_solution_assets.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def _write(base: pathlib.Path, rel: str, text: str = "x") -> pathlib.Path:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_clean_solution_passes(tmp_path: pathlib.Path) -> None:
    _write(tmp_path, "solutions/demo/solution.yaml", 'version: "1.0"\nid: demo\n')
    _write(tmp_path, "solutions/demo/assets/docker/docker-compose.yml", "services: {}\n")
    _write(tmp_path, "solutions/demo/gallery/cover.webp", "webp")
    assert MODULE.scan(tmp_path) == []


def test_non_solution_experiment_dir_skipped(tmp_path: pathlib.Path) -> None:
    # Directories without solution.yaml (like respeaker_audio_lab) are not solution packages.
    _write(tmp_path, "solutions/lab/README.md", "# Lab\n")
    _write(tmp_path, "solutions/lab/assets/web/tests/unit.test.mjs", "test();\n")
    assert MODULE.scan(tmp_path) == []


@pytest.mark.parametrize(
    "forbidden_rel",
    [
        "assets/image/app/tests/test_api.py",
        "assets/app/test/foo.py",
        "assets/web/__tests__/app.test.js",
        "assets/image/app/uv.lock",
        "assets/web/package-lock.json",
        "assets/web/yarn.lock",
        "assets/web/pnpm-lock.yaml",
        "assets/web/node_modules/pkg/index.js",
        "assets/app/.venv/bin/python",
        "assets/app/.pytest_cache/README.md",
    ],
)
def test_flags_forbidden_dev_artifacts(
    tmp_path: pathlib.Path, forbidden_rel: str
) -> None:
    _write(tmp_path, "solutions/demo/solution.yaml", 'version: "1.0"\nid: demo\n')
    _write(tmp_path, f"solutions/demo/{forbidden_rel}", "artifact")
    findings = MODULE.scan(tmp_path)
    assert len(findings) == 1
    assert findings[0].rule == "forbidden-dev-artifact"


def test_repository_is_clean() -> None:
    findings = MODULE.scan(ROOT)
    assert findings == [], f"Forbidden dev artifacts found: {findings}"
