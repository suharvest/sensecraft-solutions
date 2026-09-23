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
   * **Device-aware target grouping** — a ``docker_deploy`` step with more than
     one target in the same method (for example several remote hardware
     variants) must declare a unique ``device=`` value on every target. This
     is what lets the deploy UI render one Local card and one Remote card with
     a device dropdown instead of one card per hardware variant.
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

# A plugin-contributed step type is namespaced ``<plugin-id>/<type>`` (it
# contains a ``/``). Such types are NOT in the core contract: a solution that
# uses one is deployable only where the named plugin is installed, and is not
# eligible for the public catalog until the type is graduated into the core
# contract. ``validate`` treats these as WARNINGS (not ERRORS) so plugin-typed
# solutions can be self-checked offline. A non-namespaced unknown type (no
# ``/``) stays a hard ERROR — that's a real typo, not a plugin.
_PLUGIN_TYPE_RE = re.compile(r"\{#\w+[^}]*\btype=([\w.-]+/[\w.-]+)")

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


def _localized_text(loc, lang: str) -> str:
    """Plain-text value of a ``Localized`` for one language ('' when absent)."""
    if loc is None:
        return ""
    getter = getattr(loc, "get", None)
    val = getter(lang) if callable(getter) else None
    if isinstance(val, list):
        return "\n".join(str(v) for v in val)
    return str(val) if val is not None else ""


def _step_fingerprint(step, lang: str) -> tuple:
    """Content identity of a parsed step, for duplicate-id comparison."""
    sec = step.section
    wiring = ("", "")
    if sec.wiring is not None:
        wiring = (sec.wiring.image or "", _localized_text(sec.wiring.steps, lang))
    return (
        step.type,
        step.required,
        step.config_file or "",
        _localized_text(step.title, lang),
        _localized_text(sec.subtitle, lang),
        _localized_text(sec.description, lang),
        _localized_text(sec.troubleshoot, lang),
        _localized_text(sec.post_deploy, lang),
        wiring,
        tuple(t.id for t in (step.targets or [])),
    )


def _check_duplicate_step_ids(result, fname: str, lang: str) -> list[str]:
    """Duplicate step ids are allowed ONLY when the step content is identical.

    The engine app resolves step content by id with first-preset-wins
    semantics: a later preset reusing an id renders the earlier preset's
    step content. Reusing an id as a deliberate "shared step" (identical
    content in both presets) is therefore harmless and permitted. But if
    the two definitions diverge — even by one list item — the later preset
    silently shows the earlier preset's version, which is a wrong-content
    bug the author can't see. That divergence is what this check rejects.
    """
    errors: list[str] = []
    seen: dict[str, tuple[str, tuple]] = {}
    for preset in result.presets:
        for step in preset.steps:
            fp = _step_fingerprint(step, lang)
            if step.id in seen:
                first_preset, first_fp = seen[step.id]
                if fp != first_fp:
                    errors.append(
                        f"{fname}: step id '#{step.id}' in preset '{preset.id}' "
                        f"is already used in preset '{first_preset}' with "
                        f"DIFFERENT content — the app resolves steps by id "
                        f"(first preset wins), so this preset would silently "
                        f"render '{first_preset}''s version. Either make both "
                        f"definitions byte-identical (intentional shared step) "
                        f"or rename this one, e.g. '#{step.id}_{preset.id}'."
                    )
            else:
                seen[step.id] = (preset.id, fp)
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


def _check_device_aware_target_grouping(result, fname: str, lang: str) -> list[str]:
    """Reject ambiguous multi-target Docker selectors.

    The frontend switches to its two-card (Local / Remote) selector whenever a
    target declares ``device=``. Within each method, targets are then exposed
    through a device dropdown. A multi-variant step that omits ``device=``
    therefore silently falls back to a flat list of cards — the exact failure
    mode that previously rendered RK3576, RK3588, and Jetson as three cards.

    ``device`` is intentionally scoped per method: the same hardware can have
    both a local and a remote target, but two variants under one method must be
    distinguishable. This check is limited to ``docker_deploy`` because
    ``recamera_cpp`` uses a different flat model-variant selector by design.
    """
    errors: list[str] = []
    for preset in result.presets:
        for step in preset.steps:
            if step.type != "docker_deploy":
                continue

            groups: dict[str, list[object]] = {}
            for target in step.targets or []:
                method = (
                    getattr(target, "target_type", None)
                    or getattr(target, "method", None)
                    or "local"
                )
                method = str(method).strip().lower() or "local"
                groups.setdefault(method, []).append(target)

            for method, targets in groups.items():
                if len(targets) < 2:
                    continue

                target_ids = [f"#{getattr(t, 'id', '<unknown>')}" for t in targets]
                missing = [
                    target
                    for target in targets
                    if not str(getattr(target, "device", "") or "").strip()
                ]
                if missing:
                    missing_ids = ", ".join(
                        f"#{getattr(target, 'id', '<unknown>')}" for target in missing
                    )
                    errors.append(
                        f"{fname}: docker_deploy step '#{step.id}' has "
                        f"{len(targets)} {method} targets ({', '.join(target_ids)}) "
                        f"but {missing_ids} omit `device=`. Multi-target methods "
                        "must give every target a device id so the UI can group "
                        "them into one method card with a device dropdown."
                    )
                    # Do not report duplicate device ids for an already
                    # incomplete group; the missing-attribute error is the
                    # actionable root cause.
                    continue

                by_device: dict[str, list[object]] = {}
                for target in targets:
                    device = str(getattr(target, "device", "") or "").strip()
                    by_device.setdefault(device, []).append(target)
                duplicates = {
                    device: entries
                    for device, entries in by_device.items()
                    if len(entries) > 1
                }
                if duplicates:
                    duplicate_text = "; ".join(
                        f"{device!r}: "
                        + ", ".join(
                            f"#{getattr(target, 'id', '<unknown>')}"
                            for target in entries
                        )
                        for device, entries in sorted(duplicates.items())
                    )
                    errors.append(
                        f"{fname}: docker_deploy step '#{step.id}' has duplicate "
                        f"device groups within method '{method}' ({duplicate_text}). "
                        "Each dropdown option must map to a unique `device=` value."
                    )
    return errors


def _scan_plugin_types(guide_texts: list[str]) -> set[str]:
    """Return the set of namespaced ``<plugin-id>/<type>`` step types used.

    Scans raw guide text (across languages) for ``type=`` values that contain a
    ``/`` — the plugin-contributed namespace form. These are seeded into the
    parser's valid step-type set so the parser accepts them instead of rejecting
    them as unknown; ``validate`` then surfaces them as WARNINGs separately.
    """
    found: set[str] = set()
    for text in guide_texts:
        stripped = _FENCE_RE.sub("", text)
        for m in _PLUGIN_TYPE_RE.finditer(stripped):
            found.add(m.group(1))
    return found


def _plugin_type_warnings(
    plugin_types: set[str],
    parsed: dict,
    required_plugin_ids: set[str],
) -> list[str]:
    """Build WARN strings for plugin-contributed step types.

    * Every plugin type → an advisory that it's outside the core contract and
      not catalog-eligible until graduated.
    * If the type's ``<plugin-id>`` is not in the solution's ``requires_plugins``
      → advise adding it (minimal lockfile).
    * If a preset's only steps are plugin-typed and none is marked
      ``verify=true`` → advise marking a plugin verify step ``verify=true`` so it
      satisfies the "≥1 verify step per preset" rule (validate is offline and
      can't know a plugin type's category).
    """
    warnings: list[str] = []
    for ptype in sorted(plugin_types):
        plugin_id = ptype.split("/", 1)[0]
        warnings.append(
            f"plugin-contributed type '{ptype}' — not in the core contract; "
            f"deployable only where plugin '{plugin_id}' is installed; not "
            f"eligible for the public catalog until graduated"
        )
        if plugin_id not in required_plugin_ids:
            warnings.append(
                f"plugin type '{ptype}' is used but plugin '{plugin_id}' is not "
                f"declared in requires_plugins — add "
                f"{{id: {plugin_id}, version: <ver>}} to solution.yaml's "
                f"requires_plugins so the dependency is locked"
            )

    # Per-preset: a preset whose verify coverage rests entirely on plugin-typed
    # steps must mark at least one of them verify=true (validate can't derive a
    # plugin type's category offline).
    seen_presets: set[str] = set()
    for result in parsed.values():
        for preset in result.presets:
            if preset.id in seen_presets:
                continue
            steps = list(preset.steps)
            if not steps:
                continue
            plugin_steps = [s for s in steps if "/" in (s.type or "")]
            non_plugin_steps = [s for s in steps if "/" not in (s.type or "")]
            if not plugin_steps or non_plugin_steps:
                # Either no plugin steps, or there are core-typed steps that can
                # carry verify coverage on their own — no plugin-specific advice.
                continue
            if any(getattr(s, "verify_override", False) for s in plugin_steps):
                continue
            seen_presets.add(preset.id)
            warnings.append(
                f"preset '{preset.id}' relies on plugin-typed steps for verify "
                f"coverage but none is marked verify=true — mark a plugin verify "
                f"step verify=true so it counts toward the ≥1 verify-step rule"
            )
    return warnings


def _required_field_present(dev_data: dict, spec_field: str) -> bool:
    """True when a capabilities.json required-field spec is satisfied.

    ``a.b.c`` walks nested mappings; ``key[]`` requires a non-empty list.
    """
    if spec_field.endswith("[]"):
        val = dev_data.get(spec_field[:-2])
        return isinstance(val, list) and len(val) > 0
    node = dev_data
    for part in spec_field.split("."):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return node is not None


def _iter_step_config_refs(result):
    """Yield (step, config_path, origin) for every config= pointer in a parsed
    guide: the step's own config plus per-target / per-mode overrides."""
    for preset in result.presets:
        for step in preset.steps:
            if step.config_file:
                yield step, step.config_file, f"step '#{step.id}'"
            for target in step.targets or []:
                if target.config_file:
                    yield step, target.config_file, (
                        f"target '#{target.id}' in step '#{step.id}'"
                    )
            for mode in step.modes or []:
                if mode.config_file:
                    yield step, mode.config_file, (
                        f"mode '#{mode.id}' in step '#{step.id}'"
                    )


def _check_step_config_pointers(
    result, fname: str, sol_path: Path, deployers_info: dict
) -> tuple[list[str], set[str]]:
    """Every ``config=`` pointer must resolve to an existing YAML whose content
    satisfies the required fields of the step's deployer type.

    The guide heading defines the step's existence and prose; the device YAML
    is the executable payload. A dangling pointer (or a payload missing the
    deployer's required fields, e.g. ``firmware.flash_config`` for
    ``esp32_usb``) means the step renders fine but cannot actually deploy.

    Returns (errors, referenced_relative_paths) — the latter feeds the orphan
    device-YAML warning.
    """
    import yaml

    errors: list[str] = []
    referenced: set[str] = set()
    for step, cfg_rel, origin in _iter_step_config_refs(result):
        referenced.add(cfg_rel)
        cfg_path = sol_path / cfg_rel
        if not cfg_path.is_file():
            errors.append(
                f"{fname}: {origin} points at config='{cfg_rel}' which does "
                f"not exist — the step will render but has no executable "
                f"payload. Fix the path or add the device YAML."
            )
            continue
        # Required-field check only for the step's own config: target/mode
        # configs are partial overrides merged by the engine.
        if cfg_rel != step.config_file:
            continue
        required = (deployers_info.get(step.type) or {}).get("required") or []
        if not required:
            continue
        try:
            dev_data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue  # parse error already reported by the schema pass
        if not isinstance(dev_data, dict):
            continue
        missing = [f for f in required if not _required_field_present(dev_data, f)]
        if missing:
            errors.append(
                f"{fname}: {origin} (type={step.type}) config '{cfg_rel}' is "
                f"missing required field(s) {missing} — capabilities.json "
                f"requires them for this deployer, so deployment would fail "
                f"at runtime."
            )
    return errors, referenced


# --- Cross-step placeholder lint ------------------------------------------- #
#
# Verify / preview steps resolve ``{{...}}`` placeholders in a fixed set of
# fields against the steps that precede them in the same preset. An
# unresolvable placeholder is left in the URL verbatim by the frontend, so the
# step renders but connects to nothing (e.g. an RTSP preview that stays black).
# Only the fields below are checked; templates in compose files, actions,
# request bodies, post_deployment links etc. follow other rules.

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([\w-]+)(?:\.([\w-]+))?\s*\}\}")

# Connection fields a deploy step contributes (SSH / target connection form).
_CONNECTION_FIELDS: frozenset[str] = frozenset({"host", "port", "username", "password"})

# Without ``inherit_host_from`` the frontend only falls back to the nearest
# preceding step of these types (step-context.js resolveUpstreamHostStep).
_IMPLICIT_UPSTREAM_TYPES: frozenset[str] = frozenset(
    {"docker_deploy", "docker_local", "docker_remote"}
)

# Preview-type steps resolve their user_inputs[].default_template against
# earlier steps' inputs only (no own inputs, no ``{{step_id.field}}``).
_PREVIEW_STEP_TYPES: frozenset[str] = frozenset({"preview", "video_stream"})

# ``{{deploy.observation_port}}`` in robot_inspect endpoints is filled by the
# backend proxy (routers/robot_inspect.py DEFAULT_OBSERVATION_PORT).
_ROBOT_INSPECT_DEPLOY_FIELDS: frozenset[str] = frozenset({"observation_port"})

_MQTT_TEMPLATE_KEYS = (
    "broker_template",
    "port_template",
    "topic_template",
    "username_template",
    "password_template",
)


def _iter_placeholder_fields(dev_data: dict):
    """Yield ``(field_path, template_string)`` for the contract-scoped fields."""
    video = dev_data.get("video")
    if isinstance(video, dict):
        for key in ("rtsp_url_template", "mjpeg_url_template"):
            if isinstance(video.get(key), str):
                yield f"video.{key}", video[key]
    mqtt = dev_data.get("mqtt")
    if isinstance(mqtt, dict):
        for key in _MQTT_TEMPLATE_KEYS:
            if isinstance(mqtt.get(key), str):
                yield f"mqtt.{key}", mqtt[key]
    data = dev_data.get("data")
    if isinstance(data, dict) and isinstance(data.get("http_url_template"), str):
        yield "data.http_url_template", data["http_url_template"]
    for prefix, inputs in _iter_user_input_lists(dev_data):
        for i, inp in enumerate(inputs):
            if not isinstance(inp, dict):
                continue
            ident = inp.get("id", i)
            if isinstance(inp.get("default_template"), str):
                yield f"{prefix}[{ident}].default_template", inp["default_template"]
            if isinstance(inp.get("default"), str) and "{{" in inp["default"]:
                yield f"{prefix}[{ident}].default", inp["default"]
    dash = dev_data.get("web_dashboard")
    if isinstance(dash, dict) and isinstance(dash.get("url"), str):
        yield "web_dashboard.url", dash["url"]
    robot = dev_data.get("robot_inspect")
    if isinstance(robot, dict):
        for key in ("endpoint", "schema_endpoint"):
            if isinstance(robot.get(key), str):
                yield f"robot_inspect.{key}", robot[key]


def _iter_user_input_lists(dev_data: dict):
    """Yield ``(path, list)`` for top-level user_inputs and the remote-target
    variant under ``<x>_overrides.user_inputs`` (e.g. ``remote_overrides``)."""
    if isinstance(dev_data.get("user_inputs"), list):
        yield "user_inputs", dev_data["user_inputs"]
    for key, val in dev_data.items():
        if (
            isinstance(key, str)
            and key.endswith("_overrides")
            and isinstance(val, dict)
            and isinstance(val.get("user_inputs"), list)
        ):
            yield f"{key}.user_inputs", val["user_inputs"]


def _user_input_ids(dev_data: dict) -> set[str]:
    return {
        str(inp["id"])
        for _, inputs in _iter_user_input_lists(dev_data)
        for inp in inputs
        if isinstance(inp, dict) and inp.get("id")
    }


def _inherit_host_from(dev_data: dict, step_type: str | None) -> str | None:
    """``inherit_host_from`` at top level, under ``config``, or ``config.<type>``
    / ``<type>`` — the same lookup order the frontend uses."""
    candidates = [dev_data.get("inherit_host_from")]
    cfg = dev_data.get("config")
    if isinstance(cfg, dict):
        candidates.append(cfg.get("inherit_host_from"))
        if step_type and isinstance(cfg.get(step_type), dict):
            candidates.append(cfg[step_type].get("inherit_host_from"))
    if step_type and isinstance(dev_data.get(step_type), dict):
        candidates.append(dev_data[step_type].get("inherit_host_from"))
    for c in candidates:
        if isinstance(c, str) and c:
            return c
    return None


def _resolve_inherit_host_from(inherit, order, prior, where, report):
    """Resolve ``inherit_host_from`` to an earlier step id in the same preset.

    1. Exact match on a guide step id wins.
    2. Otherwise match the top-level ``id`` of earlier steps' device YAMLs
       (lets several presets share one verify YAML). Exactly one hit resolves;
       two or more is ambiguous and reported.
    3. No hit is reported with the earlier step ids and their device ids.
    """
    if inherit in prior:
        return inherit
    hits = [sid for sid in order if inherit in prior[sid]["device_ids"]]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        report(
            f"{where}: inherit_host_from '{inherit}' is ambiguous — it matches the "
            f"device id of several earlier steps in this preset {hits}. Use the "
            f"guide step id instead."
        )
        return None
    listing = {sid: sorted(prior[sid]["device_ids"]) for sid in order}
    report(
        f"{where}: inherit_host_from '{inherit}' matches neither a guide step id "
        f"nor a device YAML id of an earlier step in the same preset, so host "
        f"inheritance is dropped. Earlier steps (step id: device ids): "
        f"{listing or 'none'}."
    )
    return None


def _check_placeholders(
    result, fname: str, sol_path: Path, deployers_info: dict
) -> list[str]:
    """Every placeholder in a scoped template field must resolve.

    Contract (per preset, steps in guide order):

    * ``{{deploy.<field>}}`` — needs an upstream step: the one named by
      ``inherit_host_from`` (must be earlier in the same preset), else the
      nearest earlier docker_deploy / docker_local / docker_remote step. Other
      upstream types must be named explicitly. ``<field>`` is a connection
      field (host/port/username/password) or an upstream user_inputs id.
    * ``{{<field>}}`` — a user_inputs id of this step or of an earlier step, or
      a connection field when an earlier deploy step exists. A preview step's
      user_inputs[].default_template sees earlier steps only.
    * ``{{<step_id>.<field>}}`` — ``<step_id>`` is an earlier step in the
      preset; ``<field>`` is its user_inputs id or a connection field.
    """
    import yaml

    cache: dict[str, dict | None] = {}

    def load(rel: str) -> dict | None:
        if rel not in cache:
            data = None
            p = sol_path / rel
            if p.is_file():
                try:
                    data = yaml.safe_load(p.read_text(encoding="utf-8"))
                except yaml.YAMLError:
                    data = None
            cache[rel] = data if isinstance(data, dict) else None
        return cache[rel]

    def is_deploy(step_type: str | None) -> bool:
        if not step_type:
            return False
        if "/" in step_type:  # plugin type: category unknown offline
            return True
        return (deployers_info.get(step_type) or {}).get("category") == "deploy"

    errors: list[str] = []
    seen: set[str] = set()

    def report(msg: str) -> None:
        if msg not in seen:
            seen.add(msg)
            errors.append(msg)

    for preset in result.presets:
        # step_id -> {"type": str, "deploy": bool, "fields": set[str]}
        prior: dict[str, dict] = {}
        order: list[str] = []
        for step in preset.steps:
            cfgs: list[tuple[str, dict]] = []
            rels = [step.config_file]
            rels += [t.config_file for t in (step.targets or [])]
            rels += [m.config_file for m in (step.modes or [])]
            for rel in rels:
                if rel and all(rel != r for r, _ in cfgs):
                    data = load(rel)
                    if data is not None:
                        cfgs.append((rel, data))
            own_inputs: set[str] = set()
            for _, data in cfgs:
                own_inputs |= _user_input_ids(data)

            earlier_inputs: set[str] = set()
            for sid in order:
                earlier_inputs |= prior[sid]["fields"]
            if any(prior[sid]["deploy"] for sid in order):
                earlier_inputs |= _CONNECTION_FIELDS
            implicit = [
                sid for sid in order if prior[sid]["type"] in _IMPLICIT_UPSTREAM_TYPES
            ]

            for rel, data in cfgs:
                where = f"{fname}: {rel} (step '#{step.id}', preset '{preset.id}')"
                inherit = _inherit_host_from(data, step.type)
                upstream: str | None = None
                if inherit:
                    upstream = _resolve_inherit_host_from(
                        inherit, order, prior, where, report
                    )
                elif implicit:
                    upstream = implicit[-1]

                for field_path, tmpl in _iter_placeholder_fields(data):
                    preview_default = step.type in _PREVIEW_STEP_TYPES and (
                        ".user_inputs[" in f".{field_path}"
                    )
                    flat = earlier_inputs if preview_default else earlier_inputs | own_inputs
                    for m in _PLACEHOLDER_RE.finditer(tmpl):
                        head, tail, var = m.group(1), m.group(2), m.group(0)
                        if tail is None:
                            ok = head in flat
                            hint = f"{sorted(flat)}"
                        elif head == "deploy":
                            if (
                                field_path.startswith("robot_inspect.")
                                and tail in _ROBOT_INSPECT_DEPLOY_FIELDS
                            ):
                                continue
                            if upstream is None:
                                ok = False
                                if inherit:
                                    hint = f"inherit_host_from '{inherit}' does not resolve"
                                else:
                                    hint = (
                                        "no docker_deploy/docker_local/docker_remote step "
                                        "precedes this step; add `inherit_host_from: "
                                        "<step_id>` naming the earlier deploy step"
                                    )
                                    if any(prior[s]["deploy"] for s in order):
                                        cands = [s for s in order if prior[s]["deploy"]]
                                        hint += f" (candidates: {cands})"
                            else:
                                avail = _CONNECTION_FIELDS | prior[upstream]["fields"]
                                ok = tail in avail
                                hint = f"{sorted('deploy.' + f for f in avail)}"
                        elif head in prior and not preview_default:
                            avail = prior[head]["fields"] | _CONNECTION_FIELDS
                            ok = tail in avail
                            hint = f"{sorted(head + '.' + f for f in avail)}"
                        elif head in prior:
                            ok = False
                            hint = (
                                "preview-step default_template does not support "
                                f"{{{{step_id.field}}}}; use one of {sorted(earlier_inputs)}"
                            )
                        else:
                            ok = False
                            hint = f"'{head}' is not an earlier step; earlier steps: {order or 'none'}"
                        if not ok:
                            report(
                                f"{where}: field '{field_path}' uses placeholder "
                                f"'{var}' which cannot be resolved (the frontend "
                                f"leaves it verbatim). Available: {hint}."
                            )

            prior[step.id] = {
                "device_ids": {
                    str(d["id"]) for _, d in cfgs if isinstance(d.get("id"), str) and d["id"]
                },
                "type": step.type,
                "deploy": is_deploy(step.type),
                "fields": own_inputs,
            }
            order.append(step.id)
    return errors


def _check_orphan_device_yamls(
    sol_path: Path, referenced: set[str], sol_yaml_text: str
) -> list[str]:
    """Warn about devices/*.yaml not referenced by any guide step or by
    solution.yaml — usually a stale file, or an author editing a config that
    nothing actually points at."""
    devices_dir = sol_path / "devices"
    if not devices_dir.is_dir():
        return []
    warnings: list[str] = []
    for dev_file in sorted(devices_dir.glob("*.yaml")):
        rel = f"devices/{dev_file.name}"
        if rel in referenced or rel in sol_yaml_text:
            continue
        warnings.append(
            f"{rel}: not referenced by any guide step (config=) nor by "
            f"solution.yaml — editing it has no effect; delete it or wire "
            f"it to a step."
        )
    return warnings


# --- Action image-reference lint ------------------------------------------ #
#
# The engine exports ``DOCKER_REGISTRY_PREFIX`` into every action step's
# environment (SSHActionExecutor / LocalActionExecutor apply
# ``MirrorContext.as_env()``), but only compose ``image:`` fields are rewritten
# automatically. A ``docker run``/``docker pull`` inside an action ``run:``
# script has to opt in by writing ``${DOCKER_REGISTRY_PREFIX}<image>`` itself.
# Forgetting it deploys fine abroad and fails on CN-restricted networks with an
# opaque ``dial tcp ...: i/o timeout`` against registry-1.docker.io, so it is
# caught here instead of at deploy time.

# Boolean ``docker run`` flags — every *other* ``-``-prefixed token is assumed
# to consume the following value. Erring that way can only make us miss an
# image (false negative); the opposite default would mistake a flag value for
# an image name and fire spuriously.
_DOCKER_BOOLEAN_FLAGS: frozenset[str] = frozenset(
    {
        "-d", "--detach", "-i", "--interactive", "-t", "--tty", "-it", "-ti",
        "--rm", "--privileged", "--init", "--read-only", "--no-healthcheck",
        "--sig-proxy", "--oom-kill-disable", "--publish-all", "-P",
        "--disable-content-trust", "--quiet", "-q",
    }
)

def _quoted_spans(text: str) -> list[tuple[int, int]]:
    """Return ``(start, end)`` character spans of quoted regions in ``text``.

    Used to ignore ``docker run`` occurrences that are merely quoted prose
    (``echo "try: docker run foo"``). Unterminated quotes are treated as
    running to end-of-string, which is the conservative choice: it suppresses
    a finding rather than inventing one.
    """
    spans: list[tuple[int, int]] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch in "'\"":
            start = i
            i += 1
            while i < n:
                if ch == '"' and text[i] == "\\":
                    i += 2
                    continue
                if text[i] == ch:
                    break
                i += 1
            spans.append((start, min(i + 1, n)))
            i += 1
            continue
        i += 1
    return spans


def _shell_tokens(text: str):
    """Yield shell words from ``text``, stopping at the first unquoted command
    separator (``;`` ``|`` ``&`` newline).

    Written by hand rather than with ``shlex`` because an action's ``docker
    run`` frequently ends in ``sh -c '`` with the quoted body spanning many
    lines. Splitting on newlines first (or handing the truncated line to
    ``shlex.split``) breaks on the unbalanced quote and silently drops exactly
    the invocations this lint exists to catch. Quotes are tracked here, so a
    newline *inside* them is not a separator.
    """
    token: list[str] = []
    have_token = False
    i, n = 0, len(text)

    while i < n:
        ch = text[i]
        if ch == "'":
            end = text.find("'", i + 1)
            if end == -1:  # unterminated — stop, emit what we have
                break
            token.append(text[i + 1 : end])
            have_token = True
            i = end + 1
        elif ch == '"':
            i += 1
            buf: list[str] = []
            closed = False
            while i < n:
                if text[i] == "\\" and i + 1 < n:
                    buf.append(text[i + 1])
                    i += 2
                    continue
                if text[i] == '"':
                    closed = True
                    i += 1
                    break
                buf.append(text[i])
                i += 1
            if not closed:
                break
            token.append("".join(buf))
            have_token = True
        elif ch == "\\" and i + 1 < n:
            # Line continuation joins words; any other escape is literal.
            if text[i + 1] == "\n":
                i += 2
                continue
            token.append(text[i + 1])
            have_token = True
            i += 2
        elif ch in ";|&\n":
            break
        elif ch.isspace():
            if have_token:
                yield "".join(token)
                token, have_token = [], False
            i += 1
        else:
            token.append(ch)
            have_token = True
            i += 1

    if have_token:
        yield "".join(token)


def _is_registry_qualified(image: str) -> bool:
    """True when ``image`` already names an explicit registry host.

    ``sensecraft-missionpack.seeed.cn/solution/foo`` or ``localhost:5000/bar``
    must NOT be prefixed — the mirror only fronts Docker Hub.

    Docker's own rule: a name with no ``/`` is *always* ``docker.io/library/*``
    — so ``alpine:latest`` is Hub, and the ``:`` there is a tag, not a registry
    port. Only when a ``/`` is present is the first segment a registry, and
    only if it contains a ``.`` or ``:`` or is exactly ``localhost``.
    """
    head, sep, _ = image.partition("/")
    if not sep:
        return False
    return "." in head or ":" in head or head == "localhost"


def _extract_docker_images(script: str) -> list[str]:
    """Return image references pulled by ``docker run``/``docker pull`` in ``script``."""
    images: list[str] = []
    quoted = _quoted_spans(script)

    for match in re.finditer(r"(?<![\w./-])docker\s+(?:run|pull)(?![\w-])", script):
        # ``echo "Run: docker run foo"`` in a help message is documentation,
        # not a pull. Only an occurrence outside quotes is a real command.
        if any(start <= match.start() < end for start, end in quoted):
            continue
        tokens = list(_shell_tokens(script[match.end():]))
        idx = 0
        while idx < len(tokens):
            tok = tokens[idx]
            if not tok.startswith("-"):
                images.append(tok)
                break
            if tok in _DOCKER_BOOLEAN_FLAGS or "=" in tok:
                idx += 1
                continue
            # Value-taking flag: consume its argument too, unless the next
            # token is itself a flag (then this one was boolean after all).
            if idx + 1 < len(tokens) and not tokens[idx + 1].startswith("-"):
                idx += 2
            else:
                idx += 1
    return images


def _iter_action_scripts(node, path: str = ""):
    """Yield ``(json_path, script)`` for every ``run:`` string in a device YAML."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else str(key)
            if key == "run" and isinstance(value, str):
                yield child, value
            else:
                yield from _iter_action_scripts(value, child)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _iter_action_scripts(value, f"{path}[{i}]")


def _check_device_class(dev_data, label: str, known: list) -> list[str]:
    """Error on a ``device_class`` the engine has no profile for.

    The engine raises when loading such a device YAML (no
    ``devices/profiles/<class>.yaml``), so the step fails at deploy time.
    ``known`` comes from ``capabilities.json``; an older spec without the
    list skips the check rather than guessing.
    """
    if not isinstance(dev_data, dict) or not known:
        return []
    declared = dev_data.get("device_class")
    if not declared or declared in known:
        return []
    return [
        f"{label}: unknown device_class {declared!r} — the engine has no "
        f"profile for it and the deploy fails when loading this file. "
        f"Use one of {sorted(known)}, or drop the key if this solution "
        f"needs no device-class behavior."
    ]


def _check_action_image_refs(dev_data, label: str) -> list[str]:
    """Error on Docker Hub images pulled by an action without the mirror prefix."""
    errors: list[str] = []
    for json_path, script in _iter_action_scripts(dev_data):
        for image in _extract_docker_images(script):
            if "DOCKER_REGISTRY_PREFIX" in image:
                continue
            # A fully variable-driven reference (``$IMAGE``, ``${IMG}:$TAG``)
            # is resolved at runtime — the author may already be prefixing it
            # where the variable is set, so we cannot judge it here.
            if image.startswith("$"):
                continue
            if _is_registry_qualified(image):
                continue
            errors.append(
                f"{label}: at '{json_path}': action pulls Docker Hub image "
                f"'{image}' without the mirror prefix — write "
                f"'${{DOCKER_REGISTRY_PREFIX}}{image}' instead. The engine "
                f"exports DOCKER_REGISTRY_PREFIX into every action step; "
                f"without it this pull fails on CN-restricted networks."
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


def run(
    solution_path: str, spec_dir: str | None = None, check_urls: bool = False
) -> int:
    """Validate a single solution offline. Returns 0 on success, 1 on errors.

    When ``check_urls`` is True, also verifies every ``http(s)://`` reference is
    reachable (4xx → error; transient/5xx/network failures are tolerated).
    """
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
    warnings: list[str] = []
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
    caps_path = spec / "capabilities.json"
    caps = (
        json.loads(caps_path.read_text(encoding="utf-8"))
        if caps_path.is_file()
        else {}
    )
    known_device_classes = caps.get("device_classes") or []
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
                errors.extend(_check_action_image_refs(dev_data, label))
                errors.extend(
                    _check_device_class(dev_data, label, known_device_classes)
                )

    # --- 3. guide step-type validation via the parser subpackage -------------
    if not caps_path.is_file():
        errors.append("capabilities.json not found in spec/ — cannot validate step types")
    else:
        from sensecraft_solution_spec import markdown_parser as mp

        deployers_info = caps.get("deployers", {})
        deployer_keys = set(deployers_info.keys())
        # Verify step types = deployers with category == "verify" (no drift).
        verify_types = frozenset(
            t for t, info in deployers_info.items() if info.get("category") == "verify"
        )

        # Resolve the guide path from solution.yaml's deployment.guide_file so
        # legacy solutions (e.g. guide under deploy/) validate correctly; fall
        # back to the flat-layout default guide.md.
        guide_rel = "guide.md"
        if isinstance(sol_data, dict):
            guide_rel = (sol_data.get("deployment") or {}).get("guide_file") or "guide.md"
        zh_rel = guide_rel[:-3] + "_zh.md" if guide_rel.endswith(".md") else guide_rel + "_zh.md"
        guide_files = [(guide_rel, "en"), (zh_rel, "zh")]

        # Pre-read guide contents so we can scan for plugin-contributed
        # ``<plugin-id>/<type>`` step types BEFORE parsing. Those namespaced
        # types aren't in the core contract; seed them into the parser's valid
        # set so the parser accepts them (no INVALID_STEP_TYPE error) and we
        # surface them as WARNINGs instead. Non-namespaced unknown types still
        # ERROR via the parser.
        guide_contents: dict[str, str] = {}
        for fname, lang in guide_files:
            gpath = sol_path / fname
            if gpath.is_file():
                guide_contents[lang] = gpath.read_text(encoding="utf-8")
        plugin_types = _scan_plugin_types(list(guide_contents.values()))

        # Seed the parser's valid step-type set from the contract (engine-free)
        # plus any plugin-namespaced types found in the guide.
        mp.register_step_type_provider(lambda: deployer_keys | plugin_types)

        # Presets that opt out of the verify-step rule via solution.yaml.
        verify_exempt = frozenset(
            p["id"]
            for p in ((sol_data or {}).get("intro") or {}).get("presets") or []
            if isinstance(p, dict) and p.get("verify_exempt") is True and p.get("id")
        )
        # Plugin ids declared in the solution's minimal lockfile.
        required_plugin_ids = {
            r["id"]
            for r in ((sol_data or {}).get("requires_plugins") or [])
            if isinstance(r, dict) and r.get("id")
        }
        any_guide = False
        parsed: dict[str, object] = {}
        referenced_configs: set[str] = set()
        for fname, lang in guide_files:
            content = guide_contents.get(lang)
            if content is None:
                continue
            any_guide = True
            result = mp.parse_single_language_guide(content, lang)
            parsed[lang] = result
            for perr in result.errors:
                errors.append(f"{fname}: {perr}")
            # --- 4. parser-based structure/format rules (engine-free) --------
            errors.extend(_check_orphan_h2(content, fname))
            errors.extend(_check_duplicate_step_ids(result, fname, lang))
            cfg_errors, cfg_refs = _check_step_config_pointers(
                result, fname, sol_path, deployers_info
            )
            errors.extend(cfg_errors)
            referenced_configs |= cfg_refs
            errors.extend(
                _check_verify_and_target_naming(
                    result, sol_id, fname, lang, verify_types, verify_exempt
                )
            )
            errors.extend(_check_device_aware_target_grouping(result, fname, lang))
        if not any_guide:
            errors.append("no guide.md (or guide_zh.md) found — cannot validate steps")

        # --- 4b. EN/ZH structure parity (only when both guides exist) --------
        if "en" in parsed and "zh" in parsed:
            consistency = mp.validate_structure_consistency(parsed["en"], parsed["zh"])
            if not consistency.valid:
                for cerr in consistency.errors:
                    errors.append(f"EN/ZH structure mismatch: {cerr}")

        # --- 4b'. cross-step placeholders (one guide is enough: EN/ZH
        #          structure parity is enforced above) ---------------------
        placeholder_lang = "en" if "en" in parsed else ("zh" if "zh" in parsed else None)
        if placeholder_lang is not None:
            placeholder_fname = guide_rel if placeholder_lang == "en" else zh_rel
            errors.extend(
                _check_placeholders(
                    parsed[placeholder_lang], placeholder_fname, sol_path, deployers_info
                )
            )

        # --- 4c. plugin-contributed type advisories (WARN, never ERROR) ------
        if plugin_types:
            warnings.extend(
                _plugin_type_warnings(plugin_types, parsed, required_plugin_ids)
            )

        # --- 4d. orphan device YAMLs (WARN) ----------------------------------
        if any_guide:
            warnings.extend(
                _check_orphan_device_yamls(
                    sol_path,
                    referenced_configs,
                    sol_yaml.read_text(encoding="utf-8") if sol_yaml.is_file() else "",
                )
            )

    # --- 5. shared engine-free static checks (referenced files, i18n, dup ids,
    #        device-ref integrity) + semantics (compose/flow parseability) -----
    #        These are the single source of truth shared with the private
    #        compliance pytest suite (sensecraft_solution_spec.checks).
    if isinstance(sol_data, dict):
        from sensecraft_solution_spec import checks

        errors.extend(checks.run_static_checks(sol_path, sol_data))
        errors.extend(checks.check_semantics(sol_path, sol_data))
        if check_urls:
            errors.extend(checks.check_urls_reachable(sol_path, sol_data))

    # --- report --------------------------------------------------------------
    if warnings:
        print(f"⚠ {sol_id} ({len(warnings)} warning(s)):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    if errors:
        print(f"✗ {sol_id} invalid ({len(errors)} error(s)):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"✓ {sol_id} valid")
    return 0
