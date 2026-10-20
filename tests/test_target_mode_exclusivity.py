"""Tests for architectural exclusivity between Targets and Modes.

Rule contract:
1. docker_deploy natively carries targets (e.g. local vs remote); it must NOT define modes.
2. A single step must NEVER define both targets and modes.
3. Steps without targets (e.g. recamera_console_app, web_dashboard, verify) can use modes
   to select hardware models or configurations via the dropdown.
4. All real solutions in solutions/ must strictly adhere to this rule.
"""
from __future__ import annotations

import pathlib
import sys
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Import markdown parser from sensecraft_solution_spec
from sensecraft_solution_spec import markdown_parser as mp
from sensecraft_solution_spec.markdown_parser import parse_single_language_guide

# Register known step types for testing
mp.register_step_type_provider(
    lambda: {
        "docker_deploy",
        "recamera_cpp",
        "recamera_console_app",
        "recamera_pro_app",
        "web_dashboard",
        "verify",
        "manual",
    }
)

# Import the exclusivity checker from solutionctl validate
sys.path.insert(0, str(ROOT / "packages" / "solutionctl" / "src"))
from solutionctl.commands.validate import _check_target_and_mode_exclusivity


def test_docker_deploy_with_modes_is_rejected():
    """docker_deploy steps must use targets, not modes."""
    guide_text = """## Preset: Demo {#demo}

## Step 1: Deploy Service {#deploy type=docker_deploy required=true config=devices/app.yaml}

Deploy container.

### Mode: Variant A {#mode_a config=devices/app_a.yaml}

Variant A description.

### Mode: Variant B {#mode_b config=devices/app_b.yaml}

Variant B description.
"""
    result = parse_single_language_guide(guide_text, lang="en")
    errors = _check_target_and_mode_exclusivity(result, "guide.md")
    assert any("defines modes, but docker_deploy must use targets instead" in err for err in errors)


def test_step_with_both_targets_and_modes_is_rejected():
    """A single step must never define both targets and modes."""
    guide_text = """## Preset: Demo {#demo}

## Step 1: Deploy Service {#deploy type=recamera_cpp required=true config=devices/app.yaml}

Deploy.

### Mode: Mode 1 {#m1 config=devices/app1.yaml}

Mode 1.

### Target: Target 1 {#t1 type=local config=devices/app1.yaml}

Target 1.
"""
    result = parse_single_language_guide(guide_text, lang="en")
    errors = _check_target_and_mode_exclusivity(result, "guide.md")
    assert any("defines both targets and modes" in err for err in errors)


def test_valid_docker_deploy_with_targets_passes():
    """docker_deploy with targets only is completely valid."""
    guide_text = """## Preset: Demo {#demo}

## Step 1: Deploy Service {#deploy type=docker_deploy required=true config=devices/app.yaml}

Deploy container.

### Target {#local type=local config=devices/app.yaml default=true}

Local deploy.

### Target {#remote type=remote config=devices/app.yaml}

Remote deploy.
"""
    result = parse_single_language_guide(guide_text, lang="en")
    errors = _check_target_and_mode_exclusivity(result, "guide.md")
    assert errors == []


def test_valid_non_docker_with_modes_passes():
    """Non-docker steps (recamera_console_app, web_dashboard, etc.) with modes only pass."""
    guide_text = """## Preset: Demo {#demo}

## Step 1: Install App {#install type=recamera_console_app required=false config=devices/app.yaml}

Select app and deploy.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/app_sg.yaml default=true}

SG2002 install.

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/app_pro.yaml}

Pro install.
"""
    result = parse_single_language_guide(guide_text, lang="en")
    errors = _check_target_and_mode_exclusivity(result, "guide.md")
    assert errors == []


def test_all_repository_solutions_comply():
    """Scan all solutions in solutions/ and ensure zero target/mode exclusivity violations."""
    solutions_dir = ROOT / "solutions"
    assert solutions_dir.is_dir(), "solutions/ directory not found"

    violations: list[str] = []
    for sol in sorted(solutions_dir.iterdir()):
        if not sol.is_dir() or not (sol / "solution.yaml").exists():
            continue

        for guide_name, lang in [("guide.md", "en"), ("guide_zh.md", "zh")]:
            guide_path = sol / guide_name
            if not guide_path.is_file():
                continue
            content = guide_path.read_text(encoding="utf-8")
            result = parse_single_language_guide(content, lang=lang)
            errs = _check_target_and_mode_exclusivity(result, f"{sol.name}/{guide_name}")
            violations.extend(errs)

    assert violations == [], f"Found target/mode exclusivity violations:\n" + "\n".join(violations)
