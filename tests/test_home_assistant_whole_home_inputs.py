"""Shell-injection regression tests for home_assistant_whole_home device actions.

The deploy engine renders ``{{placeholder}}`` values into ``run:`` scripts as
plain text (app_collaboration ``provisioning_station/utils/template.py``
``substitute``) and does not enforce an input's ``validation`` pattern on the
server, so every script must read inputs without shell expansion and
re-validate them. These tests render the scripts the same way the engine does
and run them with hostile values.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "solutions" / "home_assistant_whole_home"
DEVICE_FILES = sorted((PKG / "devices").glob("*_voice.yaml"))
ALL_DEVICE_FILES = sorted((PKG / "devices").glob("*.yaml"))
# Filled in by the engine from the SSH connection form, not a package input;
# its pattern has to be enforced by the engine (app_collaboration).
ENGINE_PROVIDED = {"username"}
SH = shutil.which("sh")


def substitute(template: str, context: dict) -> str:
    """Mirror of app_collaboration utils/template.py substitute()."""

    def replace_var(match):
        value = context.get(match.group(1))
        return "" if value is None else str(value)

    return re.sub(r"\{\{(\w+)\}\}", replace_var, template)


def all_runs(doc: dict):
    for section in (doc.get("actions") or {}, (doc.get("remote_overrides") or {}).get("actions") or {}):
        for hook, actions in section.items():
            for action in actions or []:
                if action.get("run"):
                    yield f"{hook}:{action['name']}", action["run"]


def payloads(marker: Path) -> list[str]:
    m = str(marker)
    return [
        f"https://example.invalid/$(touch${{IFS}}{m})",
        f"https://example.invalid/`touch {m}`",
        f"https://example.invalid/'; touch {m}; '",
        f'https://example.invalid/"; touch {m}; "',
        f"$(touch {m})",
        f"8000; touch {m}",
        f"192.168.1.20$(touch {m})",
        f"https://example.invalid\n$(touch {m})",
    ]


def terminator_payloads(marker: Path) -> list[str]:
    """Values that close the HAWH_INPUT_END heredoc early.

    In-script checks cannot stop these (the shell runs the injected line while
    parsing), so the input validation patterns, enforced by the engine before
    substitution, must reject them.
    """
    m = str(marker)
    return [
        f"8000\nHAWH_INPUT_END\ntouch {m}\n#",
        f"https://example.invalid\nHAWH_INPUT_END\ntouch {m}\n#",
        f"192.168.1.20\nHAWH_INPUT_END\ntouch {m}\n#",
        "\nHAWH_INPUT_END\n",
        "8000\r\nHAWH_INPUT_END",
        "\n",
    ]


VALID = {
    "voice_port": "8623",
    "wyoming_stt_port": "10300",
    "wyoming_tts_port": "10200",
    "llm_port": "18000",
    "ha_host": "192.168.1.20",
    "llm_base_url": "https://api.deepseek.com",
    "username": "recomputer",
}


@pytest.mark.parametrize("device_file", ALL_DEVICE_FILES, ids=lambda p: p.stem)
def test_every_interpolated_input_has_a_pattern_that_rejects_heredoc_terminators(device_file, tmp_path):
    text = device_file.read_text()
    doc = yaml.safe_load(text)
    patterns = {spec["id"]: (spec.get("validation") or {}).get("pattern") for spec in doc.get("user_inputs", [])}
    for name in sorted(set(re.findall(r"\{\{(\w+)\}\}", text)) - ENGINE_PROVIDED):
        pattern = patterns.get(name)
        assert pattern, f"{device_file.name}: {{{{{name}}}}} is interpolated but has no validation pattern"
        for value in terminator_payloads(tmp_path / "MARK") + payloads(tmp_path / "MARK"):
            # Whole-value match (JSON Schema / ECMAScript semantics) and
            # Python re.match with the pattern's own anchors must both reject.
            assert not re.fullmatch(pattern, value), (device_file.name, name, value)
            if "HAWH_INPUT_END" in value:
                assert re.match(pattern, value) is None, (device_file.name, name, value)


@pytest.mark.parametrize("device_file", DEVICE_FILES, ids=lambda p: p.stem)
def test_validation_patterns_reject_shell_metacharacters(device_file, tmp_path):
    doc = yaml.safe_load(device_file.read_text())
    for spec in doc.get("user_inputs", []):
        pattern = (spec.get("validation") or {}).get("pattern")
        if not pattern:
            continue
        for value in payloads(tmp_path / "MARK"):
            assert not re.fullmatch(pattern, value), (spec["id"], value)
        if spec["id"] in VALID:
            assert re.fullmatch(pattern, VALID[spec["id"]]), spec["id"]


@pytest.mark.skipif(SH is None, reason="needs a POSIX sh")
@pytest.mark.parametrize("device_file", DEVICE_FILES, ids=lambda p: p.stem)
def test_rendered_scripts_do_not_execute_injected_values(device_file, tmp_path):
    doc = yaml.safe_load(device_file.read_text())
    # Stub every external command the scripts might reach, so nothing touches
    # the host; a stub call is recorded but harmless.
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    calls = tmp_path / "stub-calls"
    for tool in ("curl", "python3", "iptables", "ip6tables", "systemctl", "docker", "ss", "netstat", "sudo", "id"):
        stub = stub_dir / tool
        stub.write_text(f"#!/bin/sh\necho {tool} \"$@\" >> {calls}\nexit 1\n")
        stub.chmod(0o755)
    env = {"PATH": f"{stub_dir}:/usr/bin:/bin", "HOME": str(tmp_path)}
    runs = list(all_runs(doc))
    assert runs
    for name, script in runs:
        placeholders = set(re.findall(r"\{\{(\w+)\}\}", script))
        for target in placeholders:
            for value in payloads(tmp_path / "MARK"):
                context = dict(VALID)
                context[target] = value
                rendered = substitute(script, context)
                marker = tmp_path / "MARK"
                subprocess.run([SH, "-c", rendered], cwd=tmp_path, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                assert not marker.exists(), f"{device_file.name} {name}: {target}={value!r} executed"


@pytest.mark.skipif(SH is None, reason="needs a POSIX sh")
def test_url_check_rejects_injection_before_any_network_call(tmp_path):
    doc = yaml.safe_load((PKG / "devices" / "rk3588_voice.yaml").read_text())
    script = next(r for n, r in all_runs(doc) if "LLM API address" in n)
    calls = tmp_path / "calls"
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    (stub_dir / "curl").write_text(f"#!/bin/sh\necho curl >> {calls}\necho 200\n")
    (stub_dir / "curl").chmod(0o755)
    env = {"PATH": f"{stub_dir}:/usr/bin:/bin"}
    bad = substitute(script, {"llm_base_url": f"https://example.invalid/$(printf${{IFS}}INJECTED > {tmp_path}/MARK)"})
    r = subprocess.run([SH, "-c", bad], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode != 0 and "LLM_URL_INVALID" in r.stderr
    assert not (tmp_path / "MARK").exists() and not calls.exists()
    good = substitute(script, {"llm_base_url": "https://api.deepseek.com"})
    r = subprocess.run([SH, "-c", good], env=env, capture_output=True, text=True, timeout=30)
    assert calls.exists(), r.stderr
