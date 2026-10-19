"""Positive and negative test cases for the solution content and structure lint."""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "lint_solution_content", ROOT / "scripts" / "ci" / "lint_solution_content.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write(tmp_path: pathlib.Path, rel: str, text: str) -> pathlib.Path:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


STANDARD_ZH_DESC = """## 这个方案能帮你做什么
本方案提供边缘车辆检测。

## 核心价值
实时出入库计数。

## 适用场景
园区大门与地磅通道。

## 实测效果
在 RK3588 边缘主机实测推理延迟 18ms。
"""

STANDARD_EN_DESC = """## What the Solution Does
Provides edge vehicle detection.

## Core Value
Real-time vehicle counting.

## Suitable Scenarios
Industrial park entrances and weighbridges.

## Measured Performance
Benchmarked at 18ms latency on RK3588.
"""


@pytest.mark.parametrize(
    "banned_text",
    [
        "该配置目前处于草稿阶段。",
        "This is an unapproved Draft specification.",
        "image: seeed/app:0.1.0-draft",
        "由于驱动适配原因，硬件验收受阻。",
        "Feature rollout is acceptance blocked by bench test.",
        "要么改循环要么改门槛，目前未修。",
        "请注意发布顺序，必须先合入 SDK。",
        "执行 prune-stale 清理未发布镜像。",
        "等待 M7/M8 里程碑门禁通过。",
        "该接口属于暂存契约，不得在生产调用。",
        "已提交可审查契约等待安全审计。",
    ],
)
def test_flags_banned_wording(tmp_path: pathlib.Path, banned_text: str) -> None:
    write(tmp_path, "solutions/demo/guide.md", f"Overview\n{banned_text}\n")
    hits = MODULE.scan(str(tmp_path))
    assert any(h.rule == "banned-wording" for h in hits), hits


def test_code_fences_and_yaml_comments_exempt(tmp_path: pathlib.Path) -> None:
    write(
        tmp_path,
        "solutions/demo/guide.md",
        "```bash\n# internal note Draft 验收受阻\necho ok\n```\n",
    )
    write(
        tmp_path,
        "solutions/demo/solution.yaml",
        "# Draft status note\nname: demo\n",
    )
    hits = MODULE.scan(str(tmp_path))
    assert hits == []


def test_ui_draft_action_exempt(tmp_path: pathlib.Path) -> None:
    write(
        tmp_path,
        "solutions/demo/devices/tool.yaml",
        "description: Cancel discards the draft, Reset returns to initial view.\n"
        "help: 点击取消将丢弃草稿。\n",
    )
    hits = MODULE.scan(str(tmp_path))
    assert hits == []


def test_flags_broken_blockquote(tmp_path: pathlib.Path) -> None:
    broken = "每个车位画一个\n> 多边形，系统在边缘端检测。\n"
    write(tmp_path, "solutions/demo/guide.md", broken)
    hits = MODULE.scan(str(tmp_path))
    assert any(h.rule == "broken-blockquote" for h in hits), hits


def test_allows_valid_blockquote(tmp_path: pathlib.Path) -> None:
    valid = "每个车位画一个多边形。\n> **提示**：系统在边缘端实时检测。\n"
    write(tmp_path, "solutions/demo/guide.md", valid)
    hits = MODULE.scan(str(tmp_path))
    assert hits == []


def test_description_structure_pass(tmp_path: pathlib.Path) -> None:
    write(tmp_path, "solutions/demo/description_zh.md", STANDARD_ZH_DESC)
    write(tmp_path, "solutions/demo/description.md", STANDARD_EN_DESC)
    hits = MODULE.scan(str(tmp_path))
    assert hits == []


def test_flags_missing_description_section(tmp_path: pathlib.Path) -> None:
    incomplete = """## 这个方案能帮你做什么
本方案提供边缘检测。

## 适用场景
园区大门。

## 实测效果
延迟 18ms。
"""
    write(tmp_path, "solutions/demo/description_zh.md", incomplete)
    hits = MODULE.scan(str(tmp_path))
    assert any(h.rule == "missing-structure-section" for h in hits), hits


def test_repository_is_clean() -> None:
    hits = MODULE.scan(str(ROOT))
    assert hits == [], f"Lint found issues in repository: {hits}"
