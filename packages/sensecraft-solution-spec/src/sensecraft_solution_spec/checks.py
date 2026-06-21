"""Shared, engine-free static checks for solution packages.

Pure functions: every check takes ``(sol_dir, sol_data)`` (a solution directory
``Path`` and the parsed ``solution.yaml`` dict) and returns a ``list[str]`` of
human-readable error strings — empty list means "passed".

These are a faithful port of the high-value rules previously enforced only by
the private pytest suite (``tests/unit/test_solution_spec_compliance.py``).
They are reused by:

* the public ``solutionctl validate`` command (author / PR CI self-check), and
* the private compliance tests (which now delegate here — single source of
  truth, no drift).

STRICT CONSTRAINT: this module MUST NOT import ``provisioning_station`` (the
closed engine) or any third-party HTTP client. Only the standard library and
this package's own parser are allowed.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import yaml

from . import markdown_parser as mp

# Field is a remote reference (URL) rather than an on-disk path when it starts
# with one of these schemes — such references are skipped by local-existence
# checks (and validated separately by ``check_urls_reachable``).
_URL_PREFIXES = ("http://", "https://")


def _is_url(value: str) -> bool:
    return isinstance(value, str) and value.startswith(_URL_PREFIXES)


# ---------------------------------------------------------------------------
# Referenced files exist on disk (intro-level references)
# ---------------------------------------------------------------------------


def check_referenced_files(sol_dir: Path, sol_data: dict) -> list[str]:
    """intro description files, cover image, gallery media, preset architecture
    images, and device_catalog images referenced in solution.yaml must exist on
    disk.  ``http(s)://`` references are skipped (those are URLs, not local
    files).

    Faithful port of ``TestReferencedFilesExist``.
    """
    intro = (sol_data.get("intro") or {})
    missing: list[str] = []

    # --- description files (+ i18n) -----------------------------------------
    desc_file = intro.get("description_file")
    if desc_file and not _is_url(desc_file) and not (sol_dir / desc_file).exists():
        missing.append(f"description_file: {desc_file}")
    for lang, path in (intro.get("description_file_i18n") or {}).items():
        if path and not _is_url(path) and not (sol_dir / path).exists():
            missing.append(f"description_file_i18n[{lang}]: {path}")

    # --- cover image --------------------------------------------------------
    cover = intro.get("cover_image") or ""
    if cover and not _is_url(cover) and not (sol_dir / cover).exists():
        missing.append(f"cover_image: {cover}")

    # --- gallery (+ src_i18n) -----------------------------------------------
    for i, item in enumerate(intro.get("gallery") or []):
        if not isinstance(item, dict):
            continue
        src = item.get("src") or ""
        if src and not _is_url(src) and not (sol_dir / src).exists():
            missing.append(f"gallery[{i}].src: {src}")
        for lang, path in (item.get("src_i18n") or {}).items():
            if path and not _is_url(path) and not (sol_dir / path).exists():
                missing.append(f"gallery[{i}].src_i18n[{lang}]: {path}")

    # --- preset architecture images (+ i18n) --------------------------------
    for i, preset in enumerate(intro.get("presets") or []):
        arch = preset.get("architecture_image") or ""
        if arch and not _is_url(arch) and not (sol_dir / arch).exists():
            missing.append(f"presets[{i}].architecture_image: {arch}")
        for lang, path in (preset.get("architecture_image_i18n") or {}).items():
            if path and not _is_url(path) and not (sol_dir / path).exists():
                missing.append(f"presets[{i}].architecture_image_i18n[{lang}]: {path}")

    # --- device_catalog images ----------------------------------------------
    catalog = intro.get("device_catalog") or {}
    for dev_id, dev in catalog.items():
        if not isinstance(dev, dict):
            continue
        img = dev.get("image") or ""
        if img and not _is_url(img) and not (sol_dir / img).exists():
            missing.append(f"device_catalog.{dev_id}.image: {img}")

    return [f"referenced file not found: {m}" for m in missing]


# ---------------------------------------------------------------------------
# Referenced device assets exist on disk (device-YAML-level references)
# ---------------------------------------------------------------------------

# Device-YAML fields that may carry a local file reference. Nested fields
# (e.g. ``source.path``) are handled separately below.
_DEVICE_FLAT_REF_KEYS = ("path", "file", "compose_file", "flow_file")


def _iter_device_refs(node, prefix: str):
    """Yield ``(label, value)`` for every string-valued reference field found
    recursively under ``node``.

    Captures the flat reference keys at any nesting depth (covers
    ``docker.compose_file``, ``nodered.flow_file``, ``firmware.partitions[].path``,
    ``source.path``, ``files[].file``, etc.) without needing to hard-code the
    full device schema.
    """
    if isinstance(node, dict):
        for key, val in node.items():
            label = f"{prefix}.{key}" if prefix else key
            if key in _DEVICE_FLAT_REF_KEYS and isinstance(val, str):
                yield label, val
            else:
                yield from _iter_device_refs(val, label)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _iter_device_refs(item, f"{prefix}[{i}]")


def check_referenced_device_assets(sol_dir: Path, sol_data: dict) -> list[str]:
    """Local file references inside ``devices/*.yaml`` (compose_file, flow_file,
    firmware path, source.path, etc.) must point to files that exist on disk.

    Resolution mirrors the engine: device asset paths are resolved relative to
    the solution base_path (``sol_dir``). As a conservative fallback we also
    accept a path that exists relative to the device YAML's own parent
    directory (covers ``../`` style references) so this never false-positives
    on a valid solution.  ``http(s)://`` references are skipped.
    """
    devices_dir = sol_dir / "devices"
    if not devices_dir.is_dir():
        return []

    errors: list[str] = []
    for dev_file in sorted(devices_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(dev_file.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            # YAML parse errors are surfaced by the schema/semantics checks;
            # don't double-report here.
            continue
        if not isinstance(data, dict):
            continue
        for label, ref in _iter_device_refs(data, ""):
            if not ref or _is_url(ref):
                continue
            # Resolve relative to solution dir (engine base_path) OR relative
            # to the device YAML's parent (handles ../ style references).
            if (sol_dir / ref).exists() or (dev_file.parent / ref).exists():
                continue
            errors.append(
                f"device asset not found: devices/{dev_file.name}:{label} -> {ref!r}"
            )
    return errors


# ---------------------------------------------------------------------------
# i18n completeness
# ---------------------------------------------------------------------------


def check_i18n_completeness(sol_dir: Path, sol_data: dict) -> list[str]:
    """Solutions shipping bilingual content must populate every ``_i18n`` field
    for each active (non-EN) language; partial i18n silently falls back to EN
    and hides missing translations.

    Faithful port of ``TestI18nCompleteness``.
    """
    data = sol_data

    # Determine which extra languages (beyond EN) are active. A language is
    # "active" if its guide file or description file exists on disk.
    active_langs: set[str] = set()
    deployment = data.get("deployment") or {}
    guide_i18n = deployment.get("guide_file_i18n") or {}
    for lang, rel_path in guide_i18n.items():
        if rel_path and (sol_dir / rel_path).exists():
            active_langs.add(lang)
    intro = data.get("intro") or {}
    desc_i18n = intro.get("description_file_i18n") or {}
    for lang, rel_path in desc_i18n.items():
        if rel_path and (sol_dir / rel_path).exists():
            active_langs.add(lang)

    if not active_langs:
        return []  # Single-language solution, nothing to check

    missing: list[str] = []
    for lang in sorted(active_langs):
        name_i18n = (data.get("name_i18n") or {})
        if not name_i18n.get(lang):
            missing.append(f"name_i18n.{lang}")

        if not intro.get("summary_i18n", {}).get(lang):
            missing.append(f"intro.summary_i18n.{lang}")
        if not intro.get("description_file_i18n", {}).get(lang):
            missing.append(f"intro.description_file_i18n.{lang}")

        if not deployment.get("guide_file_i18n", {}).get(lang):
            missing.append(f"deployment.guide_file_i18n.{lang}")

        for i, preset in enumerate(intro.get("presets") or []):
            if not preset.get("name_i18n", {}).get(lang):
                missing.append(f"intro.presets[{i}].name_i18n.{lang}")
            if preset.get("description") and not preset.get("description_i18n", {}).get(lang):
                missing.append(f"intro.presets[{i}].description_i18n.{lang}")
            for j, grp in enumerate(preset.get("device_groups") or []):
                if not grp.get("name_i18n", {}).get(lang):
                    missing.append(
                        f"intro.presets[{i}].device_groups[{j}].name_i18n.{lang}"
                    )
                if grp.get("description") and not grp.get("description_i18n", {}).get(lang):
                    missing.append(
                        f"intro.presets[{i}].device_groups[{j}].description_i18n.{lang}"
                    )

    return [
        f"missing i18n field ({', '.join(sorted(active_langs))} active): {m}"
        for m in missing
    ]


# ---------------------------------------------------------------------------
# Duplicate IDs within a single solution
# ---------------------------------------------------------------------------


def check_duplicate_ids(sol_data: dict) -> list[str]:
    """No duplicate preset IDs, device_catalog keys, or device_group IDs within
    one solution.  Duplicates cause non-deterministic runtime behavior.

    Faithful port of ``TestNoDuplicateIds``. (Note: yaml.safe_load collapses
    duplicate mapping keys, so duplicate device_catalog keys in raw YAML are
    not detectable here — kept for parity with the source.)
    """
    intro = sol_data.get("intro") or {}
    violations: list[str] = []

    # Duplicate preset IDs
    seen_presets: dict[str, int] = {}
    for i, preset in enumerate(intro.get("presets") or []):
        pid = preset.get("id")
        if not pid:
            continue
        if pid in seen_presets:
            violations.append(
                f"preset id={pid!r} at presets[{i}] duplicates "
                f"presets[{seen_presets[pid]}]"
            )
        else:
            seen_presets[pid] = i

    # Duplicate device_catalog keys
    seen_devices: dict[str, int] = {}
    catalog = intro.get("device_catalog") or {}
    for i, did in enumerate(catalog.keys()):
        if did in seen_devices:
            violations.append(
                f"device_catalog key={did!r} at position {i} duplicates "
                f"position {seen_devices[did]}"
            )
        else:
            seen_devices[did] = i

    # Duplicate device_group IDs within presets
    for pi, preset in enumerate(intro.get("presets") or []):
        seen_groups: dict[str, int] = {}
        for gi, grp in enumerate(preset.get("device_groups") or []):
            gid = grp.get("id")
            if not gid:
                continue
            if gid in seen_groups:
                violations.append(
                    f"presets[{pi}] device_group id={gid!r} at position {gi} "
                    f"duplicates position {seen_groups[gid]}"
                )
            else:
                seen_groups[gid] = gi

    return [f"duplicate id: {v}" for v in violations]


# ---------------------------------------------------------------------------
# device_ref integrity
# ---------------------------------------------------------------------------


def check_device_ref_integrity(sol_data: dict) -> list[str]:
    """Every preset ``device_ref`` must resolve to a key in
    ``intro.device_catalog``.

    Faithful port of ``TestDeviceRefIntegrity``.
    """
    intro = sol_data.get("intro") or {}
    catalog_keys = set((intro.get("device_catalog") or {}).keys())

    broken: list[str] = []
    for preset in intro.get("presets") or []:
        for grp in preset.get("device_groups") or []:
            for opt in grp.get("options") or []:
                ref = opt.get("device_ref")
                if ref and ref not in catalog_keys:
                    broken.append(
                        f"preset={preset.get('id')} group={grp.get('id')} "
                        f"device_ref={ref!r}"
                    )
    return [f"device_ref not in device_catalog: {b}" for b in broken]


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


_ALLOWED_VERIFIED = {"deploy-smoke", "hardware"}


def check_verification_claims(sol_dir: Path, sol_data: dict) -> list[str]:
    """Guard against fake verification badges.

    A preset may declare attained verification levels in ``verified`` (a list of
    strings). Only ``deploy-smoke`` and ``hardware`` are legal. When a preset
    claims ``deploy-smoke`` it MUST be backed by at least one ``docker_deploy``
    device YAML carrying ``docker.ci_smoke: true`` (the CI compose smoke gate),
    otherwise the badge would be unearned. ``hardware`` is a maintainer
    attestation and is not machine-checkable here.
    """
    errors: list[str] = []
    presets = (sol_data.get("intro") or {}).get("presets") or []

    # Pass 1: flag illegal verified values
    for preset in presets:
        if not isinstance(preset, dict):
            continue
        preset_id = preset.get("id")
        verified = preset.get("verified") or []
        if not isinstance(verified, list):
            errors.append(
                f"preset={preset_id} verified must be a list of strings, got {type(verified).__name__}"
            )
            continue
        for i, claim in enumerate(verified):
            if claim not in _ALLOWED_VERIFIED:
                errors.append(
                    f"illegal verified claim: preset={preset_id} verified[{i}]={claim!r} "
                    f"(allowed: deploy-smoke, hardware)"
                )

    # Pass 2: deploy-smoke claims must be backed by a ci_smoke device
    deploy_smoke_ids = {
        p.get("id")
        for p in presets
        if isinstance(p, dict)
        and isinstance(p.get("verified"), list)
        and "deploy-smoke" in p.get("verified")
        and p.get("id")
    }
    if not deploy_smoke_ids:
        return errors

    guide_rel = (sol_data.get("deployment") or {}).get("guide_file") or "guide.md"
    guide_path = sol_dir / guide_rel
    if not guide_path.is_file():
        for preset_id in sorted(deploy_smoke_ids):
            errors.append(
                f"verification claim not backed by ci_smoke: preset={preset_id} "
                f"verified='deploy-smoke' (guide not found: {guide_rel})"
            )
        return errors

    result = mp.parse_single_language_guide(
        guide_path.read_text(encoding="utf-8"), "en"
    )
    presets_by_id = {p.id: p for p in result.presets}

    for preset_id in sorted(deploy_smoke_ids):
        guide_preset = presets_by_id.get(preset_id)
        has_ci_smoke = False
        if guide_preset:
            config_paths = []
            for step in guide_preset.steps:
                if step.type != "docker_deploy":
                    continue
                if step.config_file:
                    config_paths.append(step.config_file)
                for target in (step.targets or []):
                    if target.config_file:
                        config_paths.append(target.config_file)
            for rel in dict.fromkeys(config_paths):
                dev_path = sol_dir / rel
                if not dev_path.is_file():
                    continue
                data = yaml.safe_load(dev_path.read_text(encoding="utf-8")) or {}
                if (
                    isinstance(data, dict)
                    and data.get("type") == "docker_deploy"
                    and (data.get("docker") or {}).get("ci_smoke") is True
                ):
                    has_ci_smoke = True
                    break
        if not has_ci_smoke:
            errors.append(
                f"verification claim not backed by ci_smoke: preset={preset_id} "
                f"verified='deploy-smoke'"
            )
    return errors


def run_static_checks(sol_dir: Path, sol_data: dict) -> list[str]:
    """Run all engine-free static checks and return a flat list of errors,
    each prefixed with the originating check name.
    """
    errors: list[str] = []
    errors.extend(
        f"[referenced_files] {e}" for e in check_referenced_files(sol_dir, sol_data)
    )
    errors.extend(
        f"[referenced_device_assets] {e}"
        for e in check_referenced_device_assets(sol_dir, sol_data)
    )
    errors.extend(
        f"[i18n_completeness] {e}" for e in check_i18n_completeness(sol_dir, sol_data)
    )
    errors.extend(f"[duplicate_ids] {e}" for e in check_duplicate_ids(sol_data))
    errors.extend(
        f"[verification_claims] {e}"
        for e in check_verification_claims(sol_dir, sol_data)
    )
    errors.extend(
        f"[device_ref_integrity] {e}" for e in check_device_ref_integrity(sol_data)
    )
    return errors


# ---------------------------------------------------------------------------
# Tier 2 — semantic checks (parseability of referenced compose / flow files)
# ---------------------------------------------------------------------------


def check_semantics(sol_dir: Path, sol_data: dict) -> list[str]:
    """For every device YAML, any ``compose_file`` that exists on disk must
    parse as YAML, and any ``flow_file`` that exists on disk must parse as JSON.

    Missing files are NOT reported here (that's ``check_referenced_device_assets``)
    and URL references are skipped.
    """
    devices_dir = sol_dir / "devices"
    if not devices_dir.is_dir():
        return []

    errors: list[str] = []
    for dev_file in sorted(devices_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(dev_file.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if not isinstance(data, dict):
            continue

        for label, ref in _iter_device_refs(data, ""):
            if not ref or _is_url(ref):
                continue
            # Resolve like check_referenced_device_assets.
            candidate = None
            if (sol_dir / ref).exists():
                candidate = sol_dir / ref
            elif (dev_file.parent / ref).exists():
                candidate = dev_file.parent / ref
            if candidate is None:
                continue  # missing — reported elsewhere

            if label.endswith("compose_file"):
                try:
                    yaml.safe_load(candidate.read_text(encoding="utf-8"))
                except yaml.YAMLError as exc:
                    errors.append(
                        f"compose_file does not parse as YAML: "
                        f"devices/{dev_file.name}:{label} -> {ref!r}: {exc}"
                    )
            elif label.endswith("flow_file"):
                try:
                    json.loads(candidate.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, ValueError) as exc:
                    errors.append(
                        f"flow_file does not parse as JSON: "
                        f"devices/{dev_file.name}:{label} -> {ref!r}: {exc}"
                    )
    return errors


# ---------------------------------------------------------------------------
# Tier 2 — URL reachability (stdlib only, no third-party HTTP)
# ---------------------------------------------------------------------------


def _collect_urls(sol_dir: Path, sol_data: dict) -> list[tuple[str, str]]:
    """Collect ``(label, url)`` for every ``http(s)://`` reference in
    solution.yaml (cover/gallery/architecture/device_catalog images) and in
    every ``devices/*.yaml`` reference field.
    """
    urls: list[tuple[str, str]] = []
    intro = (sol_data.get("intro") or {})

    def add(label: str, value) -> None:
        if _is_url(value):
            urls.append((label, value))

    add("intro.cover_image", intro.get("cover_image"))
    for i, item in enumerate(intro.get("gallery") or []):
        if isinstance(item, dict):
            add(f"intro.gallery[{i}].src", item.get("src"))
            for lang, path in (item.get("src_i18n") or {}).items():
                add(f"intro.gallery[{i}].src_i18n[{lang}]", path)
    for i, preset in enumerate(intro.get("presets") or []):
        add(f"intro.presets[{i}].architecture_image", preset.get("architecture_image"))
        for lang, path in (preset.get("architecture_image_i18n") or {}).items():
            add(f"intro.presets[{i}].architecture_image_i18n[{lang}]", path)
    for dev_id, dev in (intro.get("device_catalog") or {}).items():
        if isinstance(dev, dict):
            add(f"intro.device_catalog.{dev_id}.image", dev.get("image"))

    devices_dir = sol_dir / "devices"
    if devices_dir.is_dir():
        for dev_file in sorted(devices_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(dev_file.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            if not isinstance(data, dict):
                continue
            for label, ref in _iter_device_refs(data, ""):
                add(f"devices/{dev_file.name}:{label}", ref)

    return urls


def _url_status(url: str, timeout: float) -> int | None:
    """Return the HTTP status code for ``url`` (HEAD, falling back to GET), or
    ``None`` if the request could not be completed (network/timeout/DNS).

    Uses only ``urllib`` from the standard library — no third-party deps.
    """
    headers = {"User-Agent": "sensecraft-solution-spec-validator/1.0"}
    for method in ("HEAD", "GET"):
        req = urllib.request.Request(url, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except urllib.error.HTTPError as exc:
            # Some servers reject HEAD with 405/501 — retry as GET. For any
            # other HTTP status (incl. 4xx) return the code so the caller can
            # decide whether it's a dead link.
            if method == "HEAD" and exc.code in (405, 501):
                continue
            return exc.code
        except (urllib.error.URLError, TimeoutError, OSError):
            # Network error / timeout / DNS failure — fall through to retry as
            # GET; if GET also fails we return None (treated as a warning, not
            # a hard failure, to avoid CI flakiness).
            continue
    return None


def check_urls_reachable(sol_dir: Path, sol_data: dict, timeout: float = 10) -> list[str]:
    """Check that every ``http(s)://`` reference is reachable.

    Policy (designed to avoid CI flakiness):
      * **4xx → error** (dead link / typo — the author's fault, deterministic).
      * network error / timeout / 5xx → NOT a failure (transient / server-side);
        returns nothing for those cases.

    Stdlib only.
    """
    errors: list[str] = []
    for label, url in _collect_urls(sol_dir, sol_data):
        status = _url_status(url, timeout)
        if status is not None and 400 <= status < 500:
            errors.append(f"dead URL ({status}): {label} -> {url}")
    return errors
