"""
Validate all solutions follow the expected guide.md format conventions.

These tests scan real solution files to catch structural issues
that would cause rendering problems in the frontend.
"""

import re
from pathlib import Path

import pytest
import yaml

from sensecraft_solution_spec.markdown_parser import (
    parse_single_language_guide,
    validate_structure_consistency,
)

SOLUTIONS_DIR = Path(__file__).parent.parent.parent / "solutions"

# Patterns that indicate rich markdown content in target descriptions
RICH_CONTENT_PATTERNS = [
    (r"^\|.+\|", "table row"),
    (r"^\*\*[^*]+\*\*[:：]", "bold heading"),
    (r"^```", "code block"),
    (r"^[-*] ", "unordered list"),
    (r"^\d+\.\s+\*\*", "numbered list with bold"),
]

# Target header pattern (matches both EN and ZH)
TARGET_HEADER_RE = re.compile(
    r"^###\s+(?:Target|部署目标):\s+.+\{#(\w+)", re.MULTILINE
)

# Any H3 subsection header (### Wiring, ### Troubleshooting, etc.)
H3_HEADER_RE = re.compile(r"^###\s+", re.MULTILINE)


def get_solution_ids():
    """Get all complete solution IDs (have both solution.yaml and guide.md).

    Incomplete solutions (missing solution.yaml) are not loaded by the backend
    and should be skipped by tests.
    """
    if not SOLUTIONS_DIR.exists():
        return []
    return sorted(
        d.name
        for d in SOLUTIONS_DIR.iterdir()
        if d.is_dir()
        and (d / "solution.yaml").exists()
        and (d / "guide.md").exists()
    )


def get_guide_files():
    """Get all guide.md and guide_zh.md files as test parameters."""
    params = []
    for sol_id in get_solution_ids():
        sol_dir = SOLUTIONS_DIR / sol_id
        for guide_file in ["guide.md", "guide_zh.md"]:
            path = sol_dir / guide_file
            if path.exists():
                params.append(
                    pytest.param(sol_id, guide_file, id=f"{sol_id}/{guide_file}")
                )
    return params


def get_all_solution_ids():
    """Get all solution IDs that have solution.yaml files."""
    if not SOLUTIONS_DIR.exists():
        return []
    return sorted(
        d.name
        for d in SOLUTIONS_DIR.iterdir()
        if d.is_dir() and (d / "solution.yaml").exists()
    )


def load_solution_yaml(sol_id: str) -> dict:
    """Load and parse a solution.yaml file."""
    yaml_path = SOLUTIONS_DIR / sol_id / "solution.yaml"
    if not yaml_path.exists():
        return {}
    with open(yaml_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def extract_target_descriptions(content: str) -> list[dict]:
    """Extract raw text between target headers and next H3 subsection.

    Returns list of {target_id, description_lines, line_number}.
    """
    lines = content.split("\n")
    targets = []
    current_target = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check for target header
        target_match = TARGET_HEADER_RE.match(stripped)
        if target_match:
            # Save previous target
            if current_target:
                targets.append(current_target)
            current_target = {
                "target_id": target_match.group(1),
                "description_lines": [],
                "line_number": i,
            }
            continue

        # Check for any H3 header (ends current target description)
        if current_target and H3_HEADER_RE.match(stripped):
            targets.append(current_target)
            current_target = None
            continue

        # Check for H2 header or separator (ends current target)
        if current_target and (stripped.startswith("## ") or stripped == "---"):
            targets.append(current_target)
            current_target = None
            continue

        # Accumulate description lines
        if current_target and stripped:
            current_target["description_lines"].append(stripped)

    # Save last target
    if current_target:
        targets.append(current_target)

    return targets


# ============================================
# Test: Target descriptions should be brief
# ============================================


class TestTargetDescriptionFormat:
    """Target selector cards only show raw text, so descriptions must be brief.

    Rich markdown content (tables, lists, bold headings, code blocks) must
    go inside ### Wiring / ### 接线 subsections, not directly under the
    target header.
    """

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_target_description_no_rich_content(self, sol_id, guide_file):
        """Target description should not contain tables, lists, or other rich markdown."""
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        targets = extract_target_descriptions(content)

        violations = []
        for target in targets:
            for line in target["description_lines"]:
                for pattern, desc in RICH_CONTENT_PATTERNS:
                    if re.match(pattern, line):
                        violations.append(
                            f"  Target #{target['target_id']} (line {target['line_number']}): "
                            f"found {desc} in description: {line[:80]}"
                        )
                        break  # one violation per line is enough

        if violations:
            msg = (
                f"{sol_id}/{guide_file}: Target description contains rich markdown "
                f"that should be in ### Wiring / ### 接线 subsection:\n"
                + "\n".join(violations)
            )
            pytest.fail(msg)

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_target_description_not_too_long(self, sol_id, guide_file):
        """Target description should be brief (≤3 non-empty lines)."""
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        targets = extract_target_descriptions(content)

        MAX_LINES = 3
        violations = []
        for target in targets:
            n = len(target["description_lines"])
            if n > MAX_LINES:
                preview = " | ".join(target["description_lines"][:3])
                violations.append(
                    f"  Target #{target['target_id']} (line {target['line_number']}): "
                    f"{n} lines (max {MAX_LINES}): {preview[:100]}..."
                )

        if violations:
            msg = (
                f"{sol_id}/{guide_file}: Target description too long. "
                f"Move detailed content to ### Wiring / ### 接线 subsection:\n"
                + "\n".join(violations)
            )
            pytest.fail(msg)


# ============================================
# Test: Bilingual structure consistency
# ============================================


class TestBilingualConsistency:
    """EN and ZH guide files must have matching structure."""

    @pytest.mark.parametrize(
        "sol_id",
        [
            pytest.param(sid, id=sid)
            for sid in get_solution_ids()
            if (SOLUTIONS_DIR / sid / "guide_zh.md").exists()
        ],
    )
    def test_en_zh_structure_matches(self, sol_id):
        """guide.md and guide_zh.md should have matching preset/step/target IDs."""
        en_content = (SOLUTIONS_DIR / sol_id / "guide.md").read_text(encoding="utf-8")
        zh_content = (SOLUTIONS_DIR / sol_id / "guide_zh.md").read_text(
            encoding="utf-8"
        )

        en_result = parse_single_language_guide(en_content, "en")
        zh_result = parse_single_language_guide(zh_content, "zh")

        validation = validate_structure_consistency(en_result, zh_result)
        if not validation.valid:
            errors = "\n".join(f"  - {e}" for e in validation.errors)
            pytest.fail(f"{sol_id}: EN/ZH structure mismatch:\n{errors}")


# ============================================
# Test: Parse errors
# ============================================


class TestNoParseErrors:
    """All solution guide files should parse without errors."""

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_no_parse_errors(self, sol_id, guide_file):
        """Guide file should parse without errors."""
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        lang = "zh" if guide_file.endswith("_zh.md") else "en"
        result = parse_single_language_guide(content, lang)

        if result.has_errors:
            errors = "\n".join(f"  - {e}" for e in result.errors)
            pytest.fail(f"{sol_id}/{guide_file}: Parse errors:\n{errors}")


# ============================================
# Test: Required subsections
# ============================================


class TestRequiredSubsections:
    """Every deployable step should have a troubleshooting subsection."""

    # Types that don't need troubleshooting
    EXEMPT_TYPES = {
        "preview", "serial_camera",
        "video_stream", "voice_chat", "image_predict",
        "text_chat", "image_text_chat", "image_text_to_image", "verify",
    }

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_steps_have_troubleshooting(self, sol_id, guide_file):
        """Each non-manual step should have a troubleshooting section."""
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        lang = "zh" if guide_file.endswith("_zh.md") else "en"
        result = parse_single_language_guide(content, lang)

        missing = []
        all_steps = list(result.steps)
        for preset in result.presets:
            all_steps.extend(preset.steps)

        for step in all_steps:
            if step.type in self.EXEMPT_TYPES:
                continue

            # Check step-level troubleshoot
            has_troubleshoot = bool(
                step.section.troubleshoot.get("en")
                or step.section.troubleshoot.get("zh")
            )

            # For steps with targets, check target-level troubleshoot
            if step.targets:
                for target in step.targets:
                    if target.troubleshoot.get("en") or target.troubleshoot.get("zh"):
                        has_troubleshoot = True
                        break

            if not has_troubleshoot:
                missing.append(f"  Step #{step.id} (type={step.type})")

        if missing:
            pytest.fail(
                f"{sol_id}/{guide_file}: Steps missing troubleshooting section:\n"
                + "\n".join(missing)
            )


# ============================================
# Test: Output interfaces and input requirements validation
# ============================================


class TestOutputInterfacesAndInputRequirements:
    """Validate new schema fields for solution composition and integration."""

    VALID_OUTPUT_TYPES = {"rtsp", "mqtt", "http", "websocket", "http_stream", "influxdb", "opc_ua"}
    VALID_INPUT_TYPES = {"rtsp", "mqtt", "http", "usb", "serial", "websocket", "audio", "lorawan", "modbus", "network"}

    @pytest.mark.parametrize(
        "sol_id",
        [pytest.param(sid, id=sid) for sid in get_all_solution_ids()],
    )
    def test_technical_solutions_have_output_interfaces(self, sol_id):
        """Technical solutions must have non-empty output_interfaces with required fields."""
        data = load_solution_yaml(sol_id)
        intro = data.get("intro", {})
        solution_type = intro.get("solution_type", "solution")

        if solution_type != "technical":
            pytest.skip(f"{sol_id} is not a technical solution")

        output_interfaces = intro.get("output_interfaces", [])
        if not output_interfaces:
            pytest.fail(
                f"{sol_id} is marked as technical but has no output_interfaces"
            )

        for i, interface in enumerate(output_interfaces):
            errors = []
            if "type" not in interface:
                errors.append(f"output_interfaces[{i}]: missing 'type' key")
            if "description" not in interface:
                errors.append(f"output_interfaces[{i}]: missing 'description' key")

            if errors:
                pytest.fail(
                    f"{sol_id}: {', '.join(errors)}"
                )

    @pytest.mark.parametrize(
        "sol_id",
        [pytest.param(sid, id=sid) for sid in get_all_solution_ids()],
    )
    def test_output_interface_types_are_valid(self, sol_id):
        """All output_interfaces must have valid type values."""
        data = load_solution_yaml(sol_id)
        intro = data.get("intro", {})
        output_interfaces = intro.get("output_interfaces", [])

        if not output_interfaces:
            pytest.skip(f"{sol_id} has no output_interfaces")

        invalid_types = []
        for i, interface in enumerate(output_interfaces):
            iface_type = interface.get("type", "")
            if iface_type not in self.VALID_OUTPUT_TYPES:
                invalid_types.append(
                    f"output_interfaces[{i}]: type '{iface_type}' not in {self.VALID_OUTPUT_TYPES}"
                )

        if invalid_types:
            pytest.fail(f"{sol_id}: {'; '.join(invalid_types)}")

    @pytest.mark.parametrize(
        "sol_id",
        [pytest.param(sid, id=sid) for sid in get_all_solution_ids()],
    )
    def test_input_requirement_types_are_valid(self, sol_id):
        """All input_requirements must have valid type values and required fields."""
        data = load_solution_yaml(sol_id)
        intro = data.get("intro", {})
        input_requirements = intro.get("input_requirements", [])

        if not input_requirements:
            pytest.skip(f"{sol_id} has no input_requirements")

        errors = []
        for i, requirement in enumerate(input_requirements):
            req_type = requirement.get("type", "")
            if req_type not in self.VALID_INPUT_TYPES:
                errors.append(
                    f"input_requirements[{i}]: type '{req_type}' not in {self.VALID_INPUT_TYPES}"
                )
            if "description" not in requirement:
                errors.append(f"input_requirements[{i}]: missing 'description' key")

        if errors:
            pytest.fail(f"{sol_id}: {'; '.join(errors)}")

    @pytest.mark.parametrize(
        "sol_id",
        [pytest.param(sid, id=sid) for sid in get_all_solution_ids()],
    )
    def test_includes_demos_reference_existing_solutions(self, sol_id):
        """All includes_demos IDs must reference existing solutions."""
        all_solution_ids = set(get_all_solution_ids())
        data = load_solution_yaml(sol_id)
        intro = data.get("intro", {})
        includes_demos = intro.get("includes_demos", [])

        if not includes_demos:
            pytest.skip(f"{sol_id} has no includes_demos")

        missing_ids = []
        for demo_id in includes_demos:
            if demo_id not in all_solution_ids:
                missing_ids.append(demo_id)

        if missing_ids:
            pytest.fail(
                f"{sol_id}: includes_demos references non-existent solutions: {missing_ids}"
            )


# ============================================
# Test: Wiring section content discipline
# ============================================


# Tokens that should NEVER appear inside a `### Wiring` / `### 接线`
# subsection — they indicate non-wiring content (software install,
# device discovery, API key acquisition, container commands).
# Wiring is strictly limited to physical connection / cabling instructions.
#
# `ssh ` is intentionally NOT in this list — it commonly appears as
# "ensure SSH is enabled" which is legitimate connection setup info.
_WIRING_FORBIDDEN_TOKENS = [
    ("curl ", "shell install command"),
    ("wget ", "shell download command"),
    ("apt install", "package install command"),
    ("apt-get", "package install command"),
    ("pip install", "python package install"),
    ("docker run", "docker runtime command"),
    ("docker pull", "docker image fetch"),
    ("docker compose", "docker compose command"),
    ("docker-compose", "docker compose command"),
    ("api key", "API key acquisition (belongs in user_inputs)"),
    ("api 密钥", "API key acquisition (belongs in user_inputs)"),
    ("list_mics", "device discovery command (belongs in user_inputs.description)"),
]


def _extract_wiring_blocks(content: str) -> list[tuple[int, str]]:
    """Return list of (line_number, body_text) for each ### Wiring / ### 接线 block."""
    lines = content.split("\n")
    blocks = []
    in_wiring = False
    start_line = 0
    body: list[str] = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        is_wiring_header = bool(re.match(r"^###\s+(Wiring|接线)\s*$", stripped, re.IGNORECASE))
        is_end = bool(re.match(r"^(###|##|---)", stripped)) and not is_wiring_header
        if is_wiring_header:
            if in_wiring:
                blocks.append((start_line, "\n".join(body)))
            in_wiring = True
            start_line = i
            body = []
            continue
        if in_wiring and is_end:
            blocks.append((start_line, "\n".join(body)))
            in_wiring = False
            body = []
            continue
        if in_wiring:
            body.append(line)
    if in_wiring:
        blocks.append((start_line, "\n".join(body)))
    return blocks


class TestWiringIsActualWiring:
    """`### Wiring` / `### 接线` is for physical connection instructions only.

    Install commands, device discovery, API key signup, and docker invocations
    belong elsewhere:
    - Software install → step description or a separate prerequisites step
    - Device discovery (`ls /dev/`, `list_mics.py`) → user_inputs.description
      in the device YAML (the form auto-renders it next to the field)
    - API key acquisition → user_inputs.description with the signup URL
    - Container commands → docker-compose.yml / device YAML

    Putting these in Wiring confuses users (they're not wiring) and creates
    duplication with the auto-rendered form fields.
    """

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_wiring_content_is_wiring_only(self, sol_id, guide_file):
        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        blocks = _extract_wiring_blocks(content)

        violations = []
        for line_no, body in blocks:
            body_lower = body.lower()
            for token, label in _WIRING_FORBIDDEN_TOKENS:
                if token in body_lower:
                    violations.append(
                        f"  Wiring block at line {line_no}: "
                        f"contains {label} (matched '{token}')"
                    )

        if violations:
            pytest.fail(
                f"{sol_id}/{guide_file}: `### Wiring` section contains non-wiring content. "
                f"Move install commands to step description, device discovery to "
                f"`user_inputs.description` in the device YAML, API key signup to "
                f"`user_inputs.description`, and docker commands to docker-compose.yml.\n"
                + "\n".join(violations)
            )


# ============================================
# Test: Step description verbosity cap
# ============================================


# Step description = text between the `## Step N:` header and the first
# `###` subsection. Long descriptions almost always mean the author stuffed
# Wiring/Troubleshooting/Verify content into the description block, which
# then gets rendered both in the collapsed step header AND the expanded
# body — producing the duplication users notice.
#
# The cap is generous (500 chars ≈ 2-3 sentences). Steps that genuinely
# need long onboarding prose (OS flashing, complex initial setup) can be
# added to the allowlist with a reason.
_STEP_DESCRIPTION_MAX_CHARS = 500
_LEGACY_LONG_STEP_DESCRIPTIONS: set[str] = {
    # OS flashing onboarding with multi-paragraph instructions covering
    # initial-vs-pre-flashed reRouter paths — legitimately long prose.
    "smart_retail_voice_ai/default/firmware",
    "smart_retail_voice_ai/default/user_guide",
    # Watcher pairing flow — multi-step setup written as continuous prose
    # rather than `### Wiring` because it's not physical wiring.
    "smart_warehouse/trial/sensecraft",
    "smart_warehouse/sensecraft_cloud/sensecraft",
    "smart_warehouse/private_cloud/watcher_config",
    "smart_warehouse/private_cloud_multi/watcher_config",
    "smart_warehouse/edge_computing/watcher_config",
    # IP camera + RTSP discovery setup with multiple alternative paths.
    "industrial_security_jetson/default/init_camera",
    # Heatmap calibration walkthrough.
    "recamera_heatmap_grafana/recamera/heatmap",
    # Default voice-command reference table — a lookup users want visible on
    # the verify step itself, not buried in a subsection.
    "respeaker_flex_soarm/default/verify_arm",
}


class TestStepDescriptionLength:
    """Step descriptions should be ≤ 500 chars to avoid stuffing.

    Long step descriptions usually indicate misplaced Wiring / Troubleshooting
    / Verify content that should be in proper subsections or device YAML.
    """

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_step_description_under_cap(self, sol_id, guide_file):
        if guide_file != "guide.md":
            pytest.skip("EN-only check (ZH is checked via structure parity)")

        content = (SOLUTIONS_DIR / sol_id / guide_file).read_text(encoding="utf-8")
        result = parse_single_language_guide(content, "en")

        violations = []
        for preset in result.presets:
            for step in preset.steps:
                desc_html = step.section.description.get("en") or ""
                text = re.sub(r"<[^>]+>", "", desc_html).strip()
                if len(text) <= _STEP_DESCRIPTION_MAX_CHARS:
                    continue
                key = f"{sol_id}/{preset.id}/{step.id}"
                if key in _LEGACY_LONG_STEP_DESCRIPTIONS:
                    continue
                violations.append(
                    f"  Step {key}: description is {len(text)} chars "
                    f"(max {_STEP_DESCRIPTION_MAX_CHARS}). First 120 chars: "
                    f"{text[:120]}..."
                )

        if violations:
            pytest.fail(
                f"{sol_id}: step description too long — move details to "
                f"### Wiring / ### Troubleshooting / device YAML user_inputs:\n"
                + "\n".join(violations)
            )


# ---------------------------------------------------------------------------
# Lint: forbid top-level `# Deployment Complete` H1 in guide files
# ---------------------------------------------------------------------------

class TestGuideCompletionMarker:
    """Preset completion content must live in `### Deployment Complete`
    inside a preset (parsed as step.section.post_deploy), never as a
    top-level `# Deployment Complete` H1.

    Why: the old H1 form populated `parsed_result.success` — a single
    global slot — which leaked into every preset's exported manual for
    multi-preset solutions, and silently went missing when the export
    fallback was removed. The H3 form attaches to a specific preset
    via `parse_subsections`, so it can't leak.
    """

    H1_PATTERN = re.compile(
        r"(?m)^#\s+(?:Deployment\s+Complete|部署完成)\s*$"
    )
    # Strip fenced code blocks (```…```) before scanning so a literal
    # `# Deployment Complete` written inside a code example doesn't
    # trip the lint. The regex is non-greedy and tolerates any info
    # string (language tag) on the opening fence.
    _FENCE_PATTERN = re.compile(r"```[^\n]*\n.*?\n```", re.DOTALL)

    def test_no_top_level_deployment_complete_h1(self):
        root = Path(__file__).resolve().parents[2] / "solutions"
        guide_globs = ["*/guide.md", "*/guide_zh.md",
                       "*/deploy/guide.md", "*/deploy/guide_zh.md"]
        offenders = []
        for pattern in guide_globs:
            for guide in root.glob(pattern):
                content = guide.read_text(encoding="utf-8")
                # Remove fenced code blocks so literal markdown inside
                # code examples doesn't false-positive.
                stripped = self._FENCE_PATTERN.sub("", content)
                if self.H1_PATTERN.search(stripped):
                    offenders.append(str(guide.relative_to(root)))
        assert not offenders, (
            "Top-level `# Deployment Complete` / `# 部署完成` is no longer "
            "supported (was a leak source for multi-preset solutions). "
            "Move the content into the preset's last step as "
            "`### Deployment Complete` (becomes step.section.post_deploy). "
            f"Offenders: {offenders}"
        )

    def test_lint_ignores_h1_inside_fenced_code_block(self):
        """A literal `# Deployment Complete` inside a ```code``` block
        is not a real heading and must not trip the lint.
        """
        sample = (
            "Some intro.\n\n"
            "```markdown\n"
            "# Deployment Complete\n"
            "do not match me — I am a code example\n"
            "```\n"
        )
        stripped = self._FENCE_PATTERN.sub("", sample)
        assert not self.H1_PATTERN.search(stripped)

    def test_lint_catches_real_h1_outside_fenced_code(self):
        sample = (
            "Some intro.\n\n"
            "```bash\n"
            "echo hi\n"
            "```\n"
            "\n"
            "# Deployment Complete\n"
            "real offender\n"
        )
        stripped = self._FENCE_PATTERN.sub("", sample)
        assert self.H1_PATTERN.search(stripped) is not None


# ---------------------------------------------------------------------------
# Lint: forbid orphan H2 outside the canonical `## Preset:` / `## Step N:`
# structure. Examples that previously slipped in:
#   ## Quick Verification / ## API Reference / ## Next Steps / ## Prerequisites
# These render inconsistently (sometimes as part of overview, sometimes as
# step content, sometimes silently dropped) and visually conflict with the
# real Step H2 headings.
# ---------------------------------------------------------------------------

class TestNoOrphanH2:
    """Every H2 in a guide must be either a Preset header or a Step header.

    Canonical forms:
      - `## Preset: <name> {#id}`         (EN)
      - `## 套餐: <name> {#id}`           (ZH)
      - `## 预设: <name> {#id}`           (ZH legacy)
      - `## Step N: <title> {#id ...}`    (EN)
      - `## 步骤 N: <title> {#id ...}`    (ZH)

    Anything else at H2 is a structural mistake — content belongs inside
    a step (as `### Deployment Complete`, `### Troubleshooting`, etc.) or
    in `description.md` / `description_zh.md` for intro material.
    """

    _FENCE_PATTERN = re.compile(r"```[^\n]*\n.*?\n```", re.DOTALL)
    # Strict H2 (exactly two `#`, not three+); allow optional trailing
    # `{#id ...}` block.
    _H2_LINE = re.compile(r"(?m)^##(?!#)\s+(.+?)\s*$")
    _CANONICAL_H2 = re.compile(
        r"^(?:"
        r"Preset:\s*.+\{#\w+\}|"
        r"(?:套餐|预设)[：:]?\s*.+\{#\w+\}|"
        r"Step\s+\d+[：:]\s*.+\{#\w+[^}]*\}|"
        r"步骤\s*\d+[：:]\s*.+\{#\w+[^}]*\}"
        r")\s*$",
        re.IGNORECASE,
    )

    def test_no_orphan_h2_in_guides(self):
        root = Path(__file__).resolve().parents[2] / "solutions"
        guide_globs = [
            "*/guide.md", "*/guide_zh.md",
            "*/deploy/guide.md", "*/deploy/guide_zh.md",
        ]
        offenders = []
        for pattern in guide_globs:
            for guide in root.glob(pattern):
                content = guide.read_text(encoding="utf-8")
                stripped = self._FENCE_PATTERN.sub("", content)
                for m in self._H2_LINE.finditer(stripped):
                    header = m.group(1).strip()
                    if not self._CANONICAL_H2.match(header):
                        rel = guide.relative_to(root)
                        offenders.append(f"{rel}: ## {header}")
        assert not offenders, (
            "Orphan H2 found. Every `## ...` must be either:\n"
            "  - `## Preset: <name> {#id}` / `## 套餐: <name> {#id}`\n"
            "  - `## Step N: <title> {#id ...}` / `## 步骤 N: <title> {#id ...}`\n"
            "Move appendix sections (Quick Verification, API Reference, "
            "Next Steps, etc.) under `### Deployment Complete` inside the "
            "preset's last step, demoted to `####`. Move intro/prereq "
            "material into description.md. Offenders:\n  "
            + "\n  ".join(offenders)
        )

    def test_orphan_h2_lint_catches_appendix(self):
        sample = (
            "## Preset: Demo {#default}\n"
            "## Step 1: Deploy {#deploy type=docker_deploy}\n"
            "## Quick Verification\n"
            "should be caught\n"
        )
        stripped = self._FENCE_PATTERN.sub("", sample)
        bad = [
            m.group(1) for m in self._H2_LINE.finditer(stripped)
            if not self._CANONICAL_H2.match(m.group(1).strip())
        ]
        assert bad == ["Quick Verification"]

    def test_orphan_h2_lint_ignores_h3_and_canonical(self):
        sample = (
            "## Preset: X {#a}\n"
            "## Step 1: Y {#b type=docker_deploy}\n"
            "### Deployment Complete\n"
            "#### Quick Verification\n"
        )
        stripped = self._FENCE_PATTERN.sub("", sample)
        bad = [
            m.group(1) for m in self._H2_LINE.finditer(stripped)
            if not self._CANONICAL_H2.match(m.group(1).strip())
        ]
        assert bad == []


# ---------------------------------------------------------------------------
# Lint: H2 preset/step headings match the file's locale.
#
# Background: the wp_next deploy-modal renderer detects preset and step
# headings by regex (`Preset:` / `Step N:`, `套餐:` / `步骤 N:`,
# `プリセット:` / `ステップ N:`). When a guide_zh.md uses the English
# `## Step 1:` form, the regex used to only match EN — the heading fell
# through to the intro fallback, which dropped tab/step-box styling and
# leaked the raw `{#anchor}` annotation into rendered prose.
#
# The renderer is now i18n-aware, so locale-mismatched headings render OK,
# but the content is still wrong: `_zh.md` should read like Chinese end-to-end.
# This test enforces the file-name → heading-language convention so we don't
# drift back.
# ---------------------------------------------------------------------------


class TestGuideHeadingLanguageMatchesFile:
    """`guide.md` uses EN headings, `guide_zh.md` uses ZH, `guide_ja.md` uses JA."""

    _FENCE_PATTERN = re.compile(r"```[^\n]*\n.*?\n```", re.DOTALL)
    _H2_LINE = re.compile(r"(?m)^##(?!#)\s+(.+?)\s*$")

    # Tokens that must NOT appear at the start of an H2 heading for each
    # locale variant. Keyed by file suffix.
    _FORBIDDEN_TOKENS = {
        "guide.md": re.compile(r"^(?:套餐|预设|步骤|プリセット|ステップ)\b"),
        "guide_zh.md": re.compile(r"^(?:Preset|Step\b|プリセット|ステップ)", re.IGNORECASE),
        "guide_ja.md": re.compile(r"^(?:Preset|Step\b|套餐|预设|步骤)", re.IGNORECASE),
    }

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_heading_language_matches_file(self, sol_id, guide_file):
        forbidden = self._FORBIDDEN_TOKENS.get(guide_file)
        if forbidden is None:
            return  # unknown variant — nothing to check
        path = SOLUTIONS_DIR / sol_id / guide_file
        content = path.read_text(encoding="utf-8")
        stripped = self._FENCE_PATTERN.sub("", content)
        offenders = []
        for m in self._H2_LINE.finditer(stripped):
            header = m.group(1).strip()
            if forbidden.match(header):
                offenders.append(f"  ## {header}")
        if offenders:
            pytest.fail(
                f"{sol_id}/{guide_file}: H2 heading uses wrong-language prefix.\n"
                f"  EN file (guide.md) must use `Preset:` / `Step N:`.\n"
                f"  ZH file (guide_zh.md) must use `套餐:` / `步骤 N:`.\n"
                f"  JA file (guide_ja.md) must use `プリセット:` / `ステップ N:`.\n"
                f"Without this, the wp_next deploy-modal renderer mismatches\n"
                f"file locale vs heading locale and historically fell through\n"
                f"to the intro fallback (no preset tabs, no step-box styling,\n"
                f"raw `{{#anchor}}` leaked into prose).\n"
                f"Offending headings:\n" + "\n".join(offenders)
            )

    def test_lint_catches_en_step_in_zh_file(self):
        # Smoke test: confirm the regex catches the historical regression.
        forbidden = self._FORBIDDEN_TOKENS["guide_zh.md"]
        assert forbidden.match("Step 1: 准备摄像头")
        assert forbidden.match("Preset: Jetson 一体化部署")
        assert not forbidden.match("步骤 1: 准备摄像头")
        assert not forbidden.match("套餐: 部署到 Jetson")
        # Negative: a heading that just contains "step" mid-sentence (rare)
        # shouldn't trip — only leading match counts.
        assert not forbidden.match("Two-step deploy 部署")


class TestTargetHeadingDeclaresType:
    """Every `### Target {...}` / `### 部署目标 {...}` heading must declare
    `type=local` or `type=remote` in its attribute block.

    The deploy API resolves local-vs-remote routing from this field; an
    unset `type=` previously fell through a target_id substring heuristic
    that quietly mis-routed remote deploys (e.g. `target=jetson` → wrong
    docker_local route) — see docs/bug-deploy-api-hang-pull-images.md.

    This lint catches the omission at test time so new solutions can't
    re-introduce the same silent failure mode.
    """

    _HEADING_RE = re.compile(
        r"^###\s+(?:Target|部署目标)(?:[：:]?\s*[^{]*?)?\{#(\w+)([^}]*)\}\s*$",
        re.MULTILINE,
    )
    _TYPE_ATTR_RE = re.compile(r"\btype=(local|remote)\b")

    @pytest.mark.parametrize("sol_id,guide_file", get_guide_files())
    def test_every_target_heading_has_type(self, sol_id, guide_file):
        path = SOLUTIONS_DIR / sol_id / guide_file
        content = path.read_text(encoding="utf-8")

        offenders: list[str] = []
        for m in self._HEADING_RE.finditer(content):
            target_id, attrs = m.group(1), m.group(2)
            if not self._TYPE_ATTR_RE.search(attrs):
                line = content[: m.start()].count("\n") + 1
                offenders.append(f"  L{line}: #{target_id} (attrs: {attrs.strip()})")

        if offenders:
            pytest.fail(
                f"{sol_id}/{guide_file}: Target heading missing `type=local|remote`. "
                "Add it to the attribute block (e.g. "
                "`### Target {#jetson type=remote config=...}`) so the deploy "
                "API can route to the correct local/remote deployer without "
                "guessing from the id string.\n" + "\n".join(offenders)
            )

    def test_lint_self_check(self):
        # Positive: with type= → no offenders.
        good = "### Target {#jetson type=remote config=devices/x.yaml default=true}\n"
        m = self._HEADING_RE.search(good)
        assert m and self._TYPE_ATTR_RE.search(m.group(2))

        # Negative: missing type= → caught.
        bad = "### Target {#jetson config=devices/x.yaml default=true}\n"
        m = self._HEADING_RE.search(bad)
        assert m and not self._TYPE_ATTR_RE.search(m.group(2))

        # Chinese variant.
        zh_good = (
            "### 部署目标 {#r_remote type=remote config=devices/recomputer_r.yaml}\n"
        )
        m = self._HEADING_RE.search(zh_good)
        assert m and self._TYPE_ATTR_RE.search(m.group(2))
