"""Positive and negative cases for the untested-wording lint."""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lint_untested_wording", ROOT / "scripts" / "ci" / "lint_untested_wording.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write(tmp_path: pathlib.Path, rel: str, text: str) -> pathlib.Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "line",
    [
        "False alarms are unmeasured on this dataset.",
        "The door path has not been measured on hardware.",
        "Capacity beyond two streams is untested end to end.",
        "Two inputs to that table are extrapolated rather than measured.",
        "Per-stream CPU at 1080p. **Needs verifying.**",
        "域偏移还没有实测过。",
        "这条路线的开门时间也还没有实测。",
        "该组合解析出的语音配置标记为待测。",
        "GroZi-120 的许可未核实。",
        "这一版固件能否两者并行，尚未实测。",
    ],
)
def test_flags_untested_wording(tmp_path: pathlib.Path, line: str) -> None:
    write(tmp_path, "solutions/demo/description.md", line + "\n")
    hits = MODULE.scan(str(tmp_path))
    assert len(hits) == 1, hits


@pytest.mark.parametrize(
    "line",
    [
        "Measure the pin voltage on your own unit before wiring the relay.",
        "Collect a field set and re-measure accuracy on it.",
        "Full activation measured p50 491.6 ms over 20 runs.",
        "Until you have measured, both read `unverified` in the start-up banner.",
        "The start-up banner names relay_contact=unverified fail_mode=unverified.",
        "误报率要用你自己的产线图像测。",
        "接线前请在自己的设备上用万用表确认。",
        "20 次实测 p50 491.6 ms、p95 507.8 ms。",
    ],
)
def test_allows_actionable_wording(tmp_path: pathlib.Path, line: str) -> None:
    write(tmp_path, "solutions/demo/description.md", line + "\n")
    assert MODULE.scan(str(tmp_path)) == []


def test_yaml_comments_are_exempt(tmp_path: pathlib.Path) -> None:
    write(
        tmp_path,
        "solutions/demo/devices/deploy.yaml",
        "# NOT VERIFIED ON HARDWARE. No unit was driven during packaging.\n"
        "description: Frames per second pulled from the source.\n",
    )
    assert MODULE.scan(str(tmp_path)) == []


def test_estimated_time_field_is_exempt(tmp_path: pathlib.Path) -> None:
    write(tmp_path, "solutions/demo/solution.yaml", "    estimated_time: 30min\n")
    assert MODULE.scan(str(tmp_path)) == []


def test_repository_is_clean() -> None:
    assert MODULE.scan(str(ROOT)) == []
