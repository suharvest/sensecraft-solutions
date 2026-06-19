"""Offline ``validate`` command — engine-free solution checker.

Unlike ``deploy`` / ``manage`` / ``meta`` (which subprocess the engine binary),
``validate`` runs fully offline with zero engine dependency. It only uses:

* the contract files under ``spec/`` (``solution.schema.json``,
  ``device.schema.json``, ``capabilities.json``), and
* the ``sensecraft_solution_spec`` parser subpackage (guide.md parsing).

It never imports ``provisioning_station`` and never shells out to the engine.

Checks performed against ``<solution_path>``:

1. ``solution.yaml`` validated against ``spec/solution.schema.json``.
2. ``devices/*.yaml`` (if present) validated against ``spec/device.schema.json``.
3. ``guide.md`` (+ ``guide_zh.md`` if present) parsed with the valid step-type
   set seeded from ``capabilities.json`` deployer keys, surfacing parse errors
   and illegal ``type=`` values.
4. Parser-based structure/format rules (engine-free), mirroring the private
   ``tests/unit/test_solution_format.py`` so contributors can self-check
   offline with the same verdict the maintainer CI applies:

   * **EN/ZH structure parity** — ``validate_structure_consistency`` on the
     two parsed guides (preset/step/target IDs must match).
   * **Verify step per preset** — every preset must contain at least one
     verify-category step (``web_dashboard`` / ``image_predict`` / ``text_chat``
     / etc.) or a ``verify=true`` override. A small legacy allowlist matches
     the private compliance test.
   * **Orphan H2** — every ``##`` heading must be a canonical
     ``## Preset:`` / ``## Step N:`` (EN) or ``## 套餐:`` / ``## 步骤 N:`` (ZH)
     heading; any other top-level H2 is an error.
   * **Target naming** — a markdown ``### Target`` name must not be a bare
     direction word (Local / Remote / 本地 / 远程 / 本机 / 远端); the live UI
     label is resolved from i18n, so a direction word is misleading.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# NOTE: jsonschema / yaml / sensecraft_solution_spec are declared deps. Engine
# packages (provisioning_station) are intentionally NOT imported anywhere here.

# --- Parser-based check constants (mirror tests/unit/test_solution_format.py
#     and tests/unit/test_solution_spec_compliance.py from the private repo) ---

# Verify step types are derived at runtime from ``capabilities.json`` —
# the deployers whose ``category == "verify"`` (see run()). No static list to
# drift out of sync with the engine registry.

# Presets exempt from the "≥1 verify step" rule (hardware-only / cloud-only
# with no local dashboard to point a verify step at) are flagged
# ``verify_exempt: true`` in their own solution.yaml — read in run() and passed
# down. The flag lives with the solution, so this validator and the private
# compliance test read the same source instead of mirroring an allowlist.

# A markdown Target name must not be a bare direction word — the live UI label
# is resolved from i18n.deploy.methodLabels based on ``type=`` + ``device_name=``,
# so a direction word in the source is misleading. Mirrors
# ``_FORBIDDEN_GENERIC_NAMES`` in the private compliance test.
_FORBIDDEN_TARGET_NAMES: frozenset[str] = frozenset(
    {"Local", "Remote", "local", "remote", "本地", "远程", "本机", "远端"}
)

# Strip fenced code blocks before scanning for orphan H2 so a literal
# ``## ...`` inside a code example doesn't trip the lint.
_FENCE_RE = re.compile(r"```[^\n]*\n.*?\n```", re.DOTALL)
# Strict H2 (exactly two ``#``), capturing the heading text.
_H2_RE = re.compile(r"(?m)^##(?!#)\s+(.+?)\s*$")
# Canonical H2 forms: ``Preset:`` / ``套餐:`` / ``预设:`` (with {#id}) and
# ``Step N:`` / ``步骤 N:`` (with {#id ...}). Matches test_solution_format.py.
_CANONICAL_H2_RE = re.compile(
    r"^(?:"
    r"Preset:\s*.+\{#\w+\}|"
    r"(?:套餐|预设)[：:]?\s*.+\{#\w+\}|"
    r"Step\s+\d+[：:]\s*.+\{#\w+[^}]*\}|"
    r"步骤\s*\d+[：:]\s*.+\{#\w+[^}]*\}"
    r")\s*$",
    re.IGNORECASE,
)


def _check_orphan_h2(content: str, fname: str) -> list[str]:
    """Return error strings for any non-canonical top-level H2 heading."""
    errors: list[str] = []
    stripped = _FENCE_RE.sub("", content)
    for m in _H2_RE.finditer(stripped):
        header = m.group(1).strip()
        if not _CANONICAL_H2_RE.match(header):
            errors.append(
                f"{fname}: orphan H2 '## {header}' — every H2 must be "
                f"'## Preset: <name> {{#id}}' / '## 套餐: <name> {{#id}}' or "
                f"'## Step N: <title> {{#id ...}}' / '## 步骤 N: <title> {{#id ...}}'. "
                f"Move appendix/intro content into a step subsection or description.md."
            )
    return errors


def _target_name_text(raw_name, lang: str) -> str:
    """Extract a plain target-name string from a str or ``Localized`` value."""
    if isinstance(raw_name, str):
        return raw_name.strip()
    getter = getattr(raw_name, "get", None)
    if callable(getter):
        val = getter(lang)
        if isinstance(val, str):
            return val.strip()
    return ""


def _check_verify_and_target_naming(
    result,
    sol_id: str,
    fname: str,
    lang: str,
    verify_types: frozenset[str],
    verify_exempt: frozenset[str],
) -> list[str]:
    """Verify-step presence per preset + non-direction-word target names.

    ``result`` is a single-language ``ParseResult``. ``verify_types`` is the
    set of deployer types whose ``category == "verify"`` (from capabilities.json).
    ``verify_exempt`` is the set of preset ids flagged ``verify_exempt: true``
    in solution.yaml.
    """
    errors: list[str] = []
    for preset in result.presets:
        # Verify step presence.
        verify_count = sum(
            1
            for s in preset.steps
            if s.type in verify_types or getattr(s, "verify_override", False)
        )
        if verify_count == 0 and preset.id not in verify_exempt:
            errors.append(
                f"{fname}: preset '{preset.id}' has no verify step — every preset "
                f"needs ≥1 verify-category step (e.g. type=web_dashboard / "
                f"image_predict / text_chat / voice_chat) or a step marked "
                f"verify=true, so the user can confirm the deployment worked."
            )
        # Target naming.
        for step in preset.steps:
            for target in step.targets or []:
                text = _target_name_text(getattr(target, "name", None), lang)
                if text and text in _FORBIDDEN_TARGET_NAMES:
                    errors.append(
                        f"{fname}: target '{target.id}' in step '{step.id}' uses a "
                        f"bare direction word as its name ({text!r}). The live UI "
                        f"label comes from i18n, so this is misleading — omit the "
                        f"name or use a descriptive fallback like 'Deploy on Pi'."
                    )
    return errors


def _find_spec_dir(solution_path: Path, explicit: str | None) -> Path | None:
    """Locate the ``spec/`` directory holding ``solution.schema.json``.

    Resolution order:
    1. ``--spec-dir`` if given (must directly contain ``solution.schema.json``).
    2. Walk up from the solution path, then from cwd, looking for a ``spec/``
       subdirectory that contains ``solution.schema.json``.
    """
    marker = "solution.schema.json"

    if explicit:
        d = Path(explicit).expanduser().resolve()
        if (d / marker).is_file():
            return d
        return None

    seen: set[Path] = set()
    for start in (solution_path.resolve(), Path.cwd().resolve()):
        cur = start
        while cur not in seen:
            seen.add(cur)
            candidate = cur / "spec"
            if (candidate / marker).is_file():
                return candidate
            if cur.parent == cur:
                break
            cur = cur.parent
    return None


def _format_jsonschema_errors(validator_cls, instance, schema, label: str) -> list[str]:
    """Run a jsonschema validator and return human-readable error strings."""
    errors: list[str] = []
    for err in sorted(
        validator_cls(schema).iter_errors(instance), key=lambda e: list(e.absolute_path)
    ):
        path = "/".join(str(p) for p in err.absolute_path) or "(root)"
        errors.append(f"{label}: at '{path}': {err.message}")
    return errors


def run(solution_path: str, spec_dir: str | None = None) -> int:
    """Validate a single solution offline. Returns 0 on success, 1 on errors."""
    import jsonschema
    import yaml

    sol_path = Path(solution_path).expanduser()
    if not sol_path.is_dir():
        print(f"Error: solution path not found: {sol_path}", file=sys.stderr)
        return 1
    sol_id = sol_path.name

    spec = _find_spec_dir(sol_path, spec_dir)
    if spec is None:
        hint = (
            f"--spec-dir '{spec_dir}' does not contain solution.schema.json"
            if spec_dir
            else "no spec/ directory with solution.schema.json found near the "
            "solution path or current directory"
        )
        print(f"Error: cannot locate contract files: {hint}", file=sys.stderr)
        print("Hint: pass --spec-dir pointing at the repo's spec/ directory.", file=sys.stderr)
        return 1

    errors: list[str] = []
    validator_cls = jsonschema.Draft202012Validator

    # --- 1. solution.yaml against solution.schema.json -----------------------
    sol_yaml = sol_path / "solution.yaml"
    if not sol_yaml.is_file():
        # Not a solution directory (e.g. shared assets like ``_shared/``, or a
        # container dir holding nested solutions). Skip rather than fail so
        # iterating ``solutions/*`` stays clean.
        print(f"⊘ {sol_path.name} skipped (no solution.yaml — not a solution directory)")
        return 0
    sol_data = None
    try:
        sol_data = yaml.safe_load(sol_yaml.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        errors.append(f"solution.yaml: YAML parse error: {exc}")
    if sol_data is not None:
        sol_schema = json.loads((spec / "solution.schema.json").read_text(encoding="utf-8"))
        errors.extend(
            _format_jsonschema_errors(validator_cls, sol_data, sol_schema, "solution.yaml")
        )

    # --- 2. devices/*.yaml against device.schema.json ------------------------
    devices_dir = sol_path / "devices"
    if devices_dir.is_dir():
        dev_schema_path = spec / "device.schema.json"
        dev_schema = (
            json.loads(dev_schema_path.read_text(encoding="utf-8"))
            if dev_schema_path.is_file()
            else None
        )
        if dev_schema is None:
            errors.append("device.schema.json not found in spec/ — cannot validate devices/")
        else:
            for dev_file in sorted(devices_dir.glob("*.yaml")):
                label = f"devices/{dev_file.name}"
                try:
                    dev_data = yaml.safe_load(dev_file.read_text(encoding="utf-8"))
                except yaml.YAMLError as exc:
                    errors.append(f"{label}: YAML parse error: {exc}")
                    continue
                errors.extend(
                    _format_jsonschema_errors(validator_cls, dev_data, dev_schema, label)
                )

    # --- 3. guide step-type validation via the parser subpackage -------------
    caps_path = spec / "capabilities.json"
    if not caps_path.is_file():
        errors.append("capabilities.json not found in spec/ — cannot validate step types")
    else:
        from sensecraft_solution_spec import markdown_parser as mp

        caps = json.loads(caps_path.read_text(encoding="utf-8"))
        deployers_info = caps.get("deployers", {})
        deployer_keys = set(deployers_info.keys())
        # Verify step types = deployers with category == "verify" (no drift).
        verify_types = frozenset(
            t for t, info in deployers_info.items() if info.get("category") == "verify"
        )
        # Seed the parser's valid step-type set from the contract (engine-free).
        mp.register_step_type_provider(lambda: deployer_keys)

        # Resolve the guide path from solution.yaml's deployment.guide_file so
        # legacy solutions (e.g. guide under deploy/) validate correctly; fall
        # back to the flat-layout default guide.md.
        guide_rel = "guide.md"
        if isinstance(sol_data, dict):
            guide_rel = (sol_data.get("deployment") or {}).get("guide_file") or "guide.md"
        zh_rel = guide_rel[:-3] + "_zh.md" if guide_rel.endswith(".md") else guide_rel + "_zh.md"
        guide_files = [(guide_rel, "en"), (zh_rel, "zh")]
        # Presets that opt out of the verify-step rule via solution.yaml.
        verify_exempt = frozenset(
            p["id"]
            for p in ((sol_data or {}).get("intro") or {}).get("presets") or []
            if isinstance(p, dict) and p.get("verify_exempt") is True and p.get("id")
        )
        any_guide = False
        parsed: dict[str, object] = {}
        for fname, lang in guide_files:
            gpath = sol_path / fname
            if not gpath.is_file():
                continue
            any_guide = True
            content = gpath.read_text(encoding="utf-8")
            result = mp.parse_single_language_guide(content, lang)
            parsed[lang] = result
            for perr in result.errors:
                errors.append(f"{fname}: {perr}")
            # --- 4. parser-based structure/format rules (engine-free) --------
            errors.extend(_check_orphan_h2(content, fname))
            errors.extend(
                _check_verify_and_target_naming(
                    result, sol_id, fname, lang, verify_types, verify_exempt
                )
            )
        if not any_guide:
            errors.append("no guide.md (or guide_zh.md) found — cannot validate steps")

        # --- 4b. EN/ZH structure parity (only when both guides exist) --------
        if "en" in parsed and "zh" in parsed:
            consistency = mp.validate_structure_consistency(parsed["en"], parsed["zh"])
            if not consistency.valid:
                for cerr in consistency.errors:
                    errors.append(f"EN/ZH structure mismatch: {cerr}")

    # --- report --------------------------------------------------------------
    if errors:
        print(f"✗ {sol_id} invalid ({len(errors)} error(s)):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"✓ {sol_id} valid")
    return 0
