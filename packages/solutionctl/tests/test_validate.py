"""Tests for the offline ``validate`` command (zero engine dependency)."""

from __future__ import annotations

from pathlib import Path

from solutionctl.commands import validate

# Repo root: packages/solutionctl/tests/test_validate.py -> up 3 levels.
REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_DIR = REPO_ROOT / "spec"
REAL_SOLUTION = REPO_ROOT / "solutions" / "recamera_heatmap_grafana"


def test_validate_real_solution_passes(capsys):
    """A real, valid solution validates with exit code 0."""
    rc = validate.run(str(REAL_SOLUTION), spec_dir=str(SPEC_DIR))
    assert rc == 0
    out = capsys.readouterr().out
    assert "valid" in out
    assert "recamera_heatmap_grafana" in out


def _write_min_solution(base: Path) -> None:
    """Write a minimal but valid-ish solution skeleton under ``base``."""
    base.mkdir(parents=True, exist_ok=True)
    (base / "solution.yaml").write_text(
        "version: 1\n"
        "id: broken_solution\n"
        "name: Broken Solution\n"
        "intro:\n"
        "  description_file: description.md\n"
        "deployment:\n"
        "  guide_file: guide.md\n",
        encoding="utf-8",
    )
    (base / "guide.md").write_text(
        "## Step 1: Do thing {#dothing type=web_dashboard required=true "
        "config=devices/d.yaml}\n\nHello\n",
        encoding="utf-8",
    )


def test_validate_missing_required_field_fails(tmp_path, capsys):
    """A solution.yaml missing required schema fields fails with exit 1."""
    base = tmp_path / "broken_required"
    base.mkdir()
    # Missing required 'id', 'intro', 'deployment'.
    (base / "solution.yaml").write_text("name: No Id Here\n", encoding="utf-8")
    (base / "guide.md").write_text(
        "## Step 1: X {#x type=web_dashboard required=true config=devices/x.yaml}\n\nhi\n",
        encoding="utf-8",
    )

    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "invalid" in err
    assert "solution.yaml" in err


def test_validate_illegal_step_type_fails(tmp_path, capsys):
    """A guide.md with an unknown step type= fails with exit 1."""
    base = tmp_path / "broken_steptype"
    _write_min_solution(base)
    # Overwrite guide with an illegal step type.
    (base / "guide.md").write_text(
        "## Step 1: Bad {#bad type=totally_bogus required=true config=devices/x.yaml}\n\nhi\n",
        encoding="utf-8",
    )

    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "guide.md" in err
    assert "totally_bogus" in err


def test_validate_bad_device_yaml_fails(tmp_path, capsys):
    """An invalid devices/*.yaml fails schema validation with exit 1."""
    base = tmp_path / "broken_device"
    _write_min_solution(base)
    devices = base / "devices"
    devices.mkdir()
    # Device YAML that is the wrong shape entirely (a list, not an object).
    (devices / "d.yaml").write_text("- not\n- a\n- device\n", encoding="utf-8")

    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "devices/d.yaml" in err


def test_validate_bad_spec_dir(tmp_path, capsys):
    """An explicit --spec-dir without the schema reports a friendly error."""
    base = tmp_path / "sol"
    _write_min_solution(base)
    rc = validate.run(str(base), spec_dir=str(tmp_path))
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot locate contract files" in err


def test_validate_missing_solution_path(tmp_path, capsys):
    rc = validate.run(str(tmp_path / "does_not_exist"), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err


def test_find_spec_dir_autodiscovery():
    """Auto-discovery walks up from the solution path to find spec/."""
    found = validate._find_spec_dir(REAL_SOLUTION, None)
    assert found is not None
    assert (found / "solution.schema.json").is_file()


def test_no_provisioning_station_import():
    """Sanity: the validate module source must not import the engine."""
    src = Path(validate.__file__).read_text(encoding="utf-8")
    assert "import provisioning_station" not in src
    assert "from provisioning_station" not in src


# ---------------------------------------------------------------------------
# Parser-based structure/format checks (mirror tests/unit/test_solution_format.py)
# ---------------------------------------------------------------------------


def _write_solution(base: Path, guide_en: str, guide_zh: str | None = None) -> None:
    """Write a schema-valid solution skeleton with the given guide content(s)."""
    base.mkdir(parents=True, exist_ok=True)
    (base / "solution.yaml").write_text(
        'version: "1.0"\n'
        f"id: {base.name}\n"
        "name: Test Solution\n"
        "intro:\n"
        "  summary: A test solution.\n"
        "  description_file: description.md\n"
        "deployment:\n"
        "  guide_file: guide.md\n",
        encoding="utf-8",
    )
    (base / "guide.md").write_text(guide_en, encoding="utf-8")
    if guide_zh is not None:
        (base / "guide_zh.md").write_text(guide_zh, encoding="utf-8")


def test_validate_missing_verify_step_fails(tmp_path, capsys):
    """A preset with no verify-category step fails with exit 1."""
    base = tmp_path / "no_verify"
    # Single docker_deploy step, no verify step in the preset.
    _write_solution(
        base,
        "## Preset: Demo {#default}\n\n"
        "## Step 1: Deploy {#deploy type=docker_deploy required=true}\n\n"
        "Deploy the stack.\n\n"
        "### Target {#local type=local config=devices/x.yaml default=true}\n\n"
        "Run here.\n",
    )
    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "no verify step" in err
    assert "default" in err


def test_validate_orphan_h2_fails(tmp_path, capsys):
    """A non-canonical top-level H2 fails with exit 1."""
    base = tmp_path / "orphan_h2"
    _write_solution(
        base,
        "## Preset: Demo {#default}\n\n"
        "## Step 1: Verify {#check type=web_dashboard required=true config=devices/x.yaml}\n\n"
        "Open the dashboard.\n\n"
        "## Quick Verification\n\n"
        "This appendix H2 is an orphan.\n",
    )
    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "orphan H2" in err
    assert "Quick Verification" in err


def test_validate_direction_word_target_name_fails(tmp_path, capsys):
    """A Target named with a bare direction word fails with exit 1."""
    base = tmp_path / "dir_target"
    _write_solution(
        base,
        "## Preset: Demo {#default}\n\n"
        "## Step 1: Verify {#check type=web_dashboard required=true}\n\n"
        "Open it.\n\n"
        "## Step 2: Deploy {#deploy type=docker_deploy required=true}\n\n"
        "Deploy.\n\n"
        "### Target: Local {#local type=local config=devices/x.yaml default=true}\n\n"
        "Run here.\n",
    )
    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "bare direction word" in err
    assert "'Local'" in err


def test_validate_en_zh_mismatch_fails(tmp_path, capsys):
    """EN and ZH guides with mismatched structure fail with exit 1."""
    base = tmp_path / "en_zh_mismatch"
    en = (
        "## Preset: Demo {#default}\n\n"
        "## Step 1: Verify {#check type=web_dashboard required=true config=devices/x.yaml}\n\n"
        "Open the dashboard.\n"
    )
    # ZH guide has a different step id (#different vs #check) → structure mismatch.
    zh = (
        "## 套餐: 演示 {#default}\n\n"
        "## 步骤 1: 验证 {#different type=web_dashboard required=true config=devices/x.yaml}\n\n"
        "打开仪表盘。\n"
    )
    _write_solution(base, en, zh)
    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "EN/ZH structure mismatch" in err


# ---------------------------------------------------------------------------
# Plugin-contributed step types (P3b): WARN, never ERROR
# ---------------------------------------------------------------------------


def _write_solution_with_yaml(base: Path, sol_yaml: str, guide_en: str) -> None:
    """Write a solution with a custom solution.yaml + guide.

    Also drops the referenced ``description.md`` and ``devices/x.yaml`` so the
    shared static checks (referenced-file existence, device-ref integrity) don't
    fail on missing fixtures — keeping each test focused on the behaviour under
    test rather than incidental scaffolding.
    """
    base.mkdir(parents=True, exist_ok=True)
    (base / "solution.yaml").write_text(sol_yaml, encoding="utf-8")
    (base / "guide.md").write_text(guide_en, encoding="utf-8")
    (base / "description.md").write_text("# Desc\n", encoding="utf-8")
    devices = base / "devices"
    devices.mkdir(exist_ok=True)
    (devices / "x.yaml").write_text(
        "id: x\nname: X\ntype: docker_local\n", encoding="utf-8"
    )


_PLUGIN_GUIDE = (
    "## Preset: Demo {#default}\n\n"
    "## Step 1: Teleop {#teleop type=myplugin/robot_arm required=true verify=true "
    "config=devices/x.yaml}\n\n"
    "Drive the arm to confirm it deployed.\n"
)


def test_validate_plugin_type_warns_not_errors(tmp_path, capsys):
    """A namespaced plugin type with verify=true validates (exit 0) with a WARN."""
    base = tmp_path / "plugin_ok"
    _write_solution_with_yaml(
        base,
        'version: "1.0"\n'
        "id: plugin_ok\n"
        "name: Plugin Solution\n"
        "intro:\n"
        "  summary: Uses a plugin type.\n"
        "  description_file: description.md\n"
        "requires_plugins:\n"
        "  - id: myplugin\n"
        "    version: 1.0.0\n"
        "deployment:\n"
        "  guide_file: guide.md\n",
        _PLUGIN_GUIDE,
    )
    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    err = capsys.readouterr().err
    # Not an error: the plugin type must not be rejected as unknown.
    assert rc == 0
    assert "Invalid step type" not in err
    assert "error(s)" not in err
    # It IS surfaced as a warning.
    assert "warning(s)" in err
    assert "plugin-contributed type 'myplugin/robot_arm'" in err
    assert "not eligible for the public catalog until graduated" in err


def test_validate_plugin_type_missing_requires_plugins_warns(tmp_path, capsys):
    """Plugin type used but not declared in requires_plugins → WARN, still exit 0."""
    base = tmp_path / "plugin_no_req"
    _write_solution_with_yaml(
        base,
        'version: "1.0"\n'
        "id: plugin_no_req\n"
        "name: Plugin Solution\n"
        "intro:\n"
        "  summary: Uses a plugin type.\n"
        "  description_file: description.md\n"
        "deployment:\n"
        "  guide_file: guide.md\n",
        _PLUGIN_GUIDE,
    )
    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    err = capsys.readouterr().err
    assert rc == 0
    assert "warning(s)" in err
    assert "not declared in requires_plugins" in err
    assert "myplugin" in err


def test_validate_plugin_verify_not_marked_warns(tmp_path, capsys):
    """A preset relying on a plugin step that isn't verify=true → verify WARN.

    The preset has no core-typed verify step, so it also fails the ≥1-verify
    rule (ERROR); the plugin advisory tells the author to mark verify=true.
    """
    base = tmp_path / "plugin_no_verify"
    _write_solution_with_yaml(
        base,
        'version: "1.0"\n'
        "id: plugin_no_verify\n"
        "name: Plugin Solution\n"
        "intro:\n"
        "  summary: Uses a plugin type.\n"
        "  description_file: description.md\n"
        "requires_plugins:\n"
        "  - id: myplugin\n"
        "    version: 1.0.0\n"
        "deployment:\n"
        "  guide_file: guide.md\n",
        "## Preset: Demo {#default}\n\n"
        "## Step 1: Teleop {#teleop type=myplugin/robot_arm required=true "
        "config=devices/x.yaml}\n\n"
        "Drive the arm.\n",
    )
    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    err = capsys.readouterr().err
    # No core-typed verify step → the ≥1-verify rule still ERRORs (exit 1)…
    assert rc == 1
    assert "no verify step" in err
    # …and the plugin advisory tells the author how to satisfy it.
    assert "warning(s)" in err
    assert "mark a plugin verify step verify=true" in err


def test_validate_non_namespaced_unknown_type_still_errors(tmp_path, capsys):
    """A non-namespaced unknown type (no '/') is still a hard ERROR."""
    base = tmp_path / "bogus_type"
    _write_solution_with_yaml(
        base,
        'version: "1.0"\n'
        "id: bogus_type\n"
        "name: Bogus\n"
        "intro:\n"
        "  summary: x\n"
        "  description_file: description.md\n"
        "deployment:\n"
        "  guide_file: guide.md\n",
        "## Preset: Demo {#default}\n\n"
        "## Step 1: Bad {#bad type=totally_bogus required=true config=devices/x.yaml}\n\n"
        "hi\n",
    )
    rc = validate.run(str(base), spec_dir=str(SPEC_DIR))
    assert rc == 1
    err = capsys.readouterr().err
    assert "totally_bogus" in err
    assert "Invalid step type" in err


# --- action image-reference lint ------------------------------------------ #

# The exact shape that shipped broken: the image sits on a `docker run` line
# that ends in `sh -c '`, with the quoted body spanning many lines. Any
# tokenizer that splits on newlines before tracking quotes drops this one.
_OPENCLAW_ACTION = """\
set -e
VOL="openclaw_openclaw-config"
docker volume create "$VOL" 2>/dev/null || true
WS_VOL="openclaw_openclaw-workspace"
docker run --rm --network none -v "$VOL":/data -v "$WS_VOL":/ws alpine sh -c '
  chown 1000:1000 /data /ws
  if [ ! -f /data/openclaw.json ]; then
    cat > /data/openclaw.json <<VOLCFG
{"gateway":{"controlUi":{"dangerouslyAllowHostHeaderOriginFallback":true}}}
VOLCFG
    echo "Initial config written"
  fi
'
"""


def _device_with_action(script: str) -> dict:
    return {"actions": {"before": [{"name": "step", "run": script}]}}


def test_action_image_without_mirror_prefix_errors():
    errors = validate._check_action_image_refs(
        _device_with_action(_OPENCLAW_ACTION), "devices/d.yaml"
    )
    assert len(errors) == 1
    assert "'alpine'" in errors[0]
    assert "DOCKER_REGISTRY_PREFIX" in errors[0]


def test_action_image_with_mirror_prefix_passes():
    fixed = _OPENCLAW_ACTION.replace(" alpine ", " ${DOCKER_REGISTRY_PREFIX}alpine ")
    assert validate._check_action_image_refs(_device_with_action(fixed), "d") == []


def test_private_registry_image_is_not_flagged():
    # The mirror only fronts Docker Hub; prefixing a self-hosted registry
    # would break the pull.
    script = (
        "docker run --rm --privileged \\\n"
        "  -v /dev/bus/usb:/dev/bus/usb \\\n"
        "  sensecraft-missionpack.seeed.cn/solution/voice-client:v0.4 \\\n"
        "  python3 -c 'print(1)'\n"
    )
    assert validate._check_action_image_refs(_device_with_action(script), "d") == []
    assert validate._extract_docker_images(script) == [
        "sensecraft-missionpack.seeed.cn/solution/voice-client:v0.4"
    ]


def test_variable_image_reference_is_not_flagged():
    script = "docker pull $IMAGE\ndocker run --rm ${IMG}:${TAG} sh\n"
    assert validate._check_action_image_refs(_device_with_action(script), "d") == []


def test_flag_values_are_not_mistaken_for_images():
    # `none` (value of --network) and `mlc:/data` (value of -v) must not be
    # reported as the image.
    script = "docker run --rm --network none -v mlc:/data -e A=B alpine sh\n"
    assert validate._extract_docker_images(script) == ["alpine"]


def test_docker_pull_form_is_checked():
    errors = validate._check_action_image_refs(
        _device_with_action("docker pull redis:7-alpine\n"), "devices/d.yaml"
    )
    assert len(errors) == 1
    assert "'redis:7-alpine'" in errors[0]


def test_non_docker_commands_are_ignored():
    script = "echo 'docker run something' > /tmp/doc.txt\ndockerize --rm foo\n"
    assert validate._extract_docker_images(script) == []


def test_shipped_solutions_have_no_unprefixed_hub_images():
    """Corpus guard: every device YAML in the repo must already comply."""
    import yaml

    findings = []
    for dev in sorted((REPO_ROOT / "solutions").glob("*/devices/*.yaml")):
        data = yaml.safe_load(dev.read_text(encoding="utf-8"))
        findings += validate._check_action_image_refs(
            data, f"{dev.parent.parent.name}/{dev.name}"
        )
    assert findings == []
