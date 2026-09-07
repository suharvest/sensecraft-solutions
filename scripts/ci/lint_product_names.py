#!/usr/bin/env python3
"""Lint outward-facing product names in Solution content.

Rules live in ``scripts/ci/product-names.json`` (a copy of the same file is kept
in seeed-solutions-hub at ``scripts/lib/product-names.json``; the two must stay
in sync). The checks are:

1. blacklist        -- strings that are not product names at all
                       ("reComputer J", "reComputer R", "SenseCAP R1000", ...)
2. bench-only names -- lab boards and fleet host ids in outward text
                       (Raspberry Pi 4/5, Radxa, harvest-pi, ...)
3. model existence  -- every ``<brand> <model>`` token must be a model or a
                       series that exists in the product catalogue
4. cross-checks     -- J30xx paired with "Orin NX", J40xx with "Orin Nano", ...
5. prefer family    -- a bare SKU in prose warns; write the family name instead
6. preset coherence -- the product families a preset's text names must match the
                       families its ``device_ref`` entries point at

Usage:
    python scripts/ci/lint_product_names.py [PATH ...]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES = Path(__file__).resolve().parent / "product-names.json"
DEFAULT_MANIFEST = REPO_ROOT / "spec" / "product-family-manifest.json"
DEFAULT_ROOTS = [REPO_ROOT / "solutions"]

# Files whose whole text is outward-facing.
TEXT_GLOBS = (
    "description*.md",
    "guide*.md",
)
TEXT_NAMES = ("overlay.yaml",)
TEXT_DIRS = ("wiki",)
IR_NAME = "architecture.ir.yaml"

CODE_FENCE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE = re.compile(r"`[^`]*`")
URL = re.compile(r"https?://\S+|\S+\.(?:png|jpg|jpeg|svg|webp|gif|yaml|yml|json|md)\b")
TABLE_ROW = re.compile(r"^\s*\|")


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str
    severity: str
    message: str
    excerpt: str

    def render(self) -> str:
        return (
            f"{self.severity.upper()}: {self.path}:{self.line} [{self.rule}] "
            f"{self.message}\n    {self.excerpt.strip()[:200]}"
        )


@dataclass(frozen=True)
class Unit:
    """One scannable chunk of outward-facing text."""

    path: str
    line: int
    text: str
    prose: bool  # False for table rows / BOM fields, where a bare SKU is fine


def load_rules(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# collecting text units
# --------------------------------------------------------------------------


def _strip_noise(line: str) -> str:
    return URL.sub(" ", INLINE_CODE.sub(" ", line))


def units_from_text_file(path: Path, rel: str) -> list[Unit]:
    units: list[Unit] = []
    in_fence = False
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if CODE_FENCE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        text = _strip_noise(raw)
        if not text.strip():
            continue
        units.append(Unit(rel, number, text, prose=not TABLE_ROW.match(raw)))
    return units


def _find_line(haystack: list[str], needle: str) -> int:
    probe = needle.strip().splitlines()[0].strip() if needle.strip() else ""
    if probe:
        for number, line in enumerate(haystack, 1):
            if probe in line:
                return number
    return 1


def _i18n_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [v for v in value.values() if isinstance(v, str)]
    return []


def units_from_solution_yaml(path: Path, rel: str) -> list[Unit]:
    """Only the outward-facing fields: preset names, BOM names, catalog names."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    units: list[Unit] = []

    def add(value: Any, prose: bool) -> None:
        for text in _i18n_values(value):
            if text.strip():
                units.append(Unit(rel, _find_line(lines, text), text, prose))

    intro = data.get("intro") or {}
    for preset in intro.get("presets") or []:
        add(preset.get("name"), prose=True)
        add(preset.get("name_i18n"), prose=True)
        add(preset.get("description"), prose=True)
        add(preset.get("description_i18n"), prose=True)
    for key, entry in (intro.get("device_catalog") or {}).items():
        if not isinstance(entry, dict):
            continue
        add(entry.get("name"), prose=False)
        add(entry.get("name_i18n"), prose=False)
    for item in intro.get("bom") or []:
        if isinstance(item, dict):
            add(item.get("name"), prose=False)
            add(item.get("name_i18n"), prose=False)
    for shot in intro.get("gallery") or []:
        if isinstance(shot, dict):
            add(shot.get("caption"), prose=True)
            add(shot.get("caption_i18n"), prose=True)
    return units


def units_from_ir_yaml(path: Path, rel: str) -> list[Unit]:
    """Architecture IR: only the human-visible labels."""
    units: list[Unit] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if "label" not in raw:
            continue
        units.append(Unit(rel, number, _strip_noise(raw), prose=False))
    return units


def collect_units(roots: Iterable[Path], repo_root: Path) -> list[Unit]:
    units: list[Unit] = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = str(path.relative_to(repo_root))
            name = path.name
            in_wiki = any(part in TEXT_DIRS for part in path.parts)
            if name == IR_NAME:
                units.extend(units_from_ir_yaml(path, rel))
            elif name == "solution.yaml":
                units.extend(units_from_solution_yaml(path, rel))
            elif name in TEXT_NAMES:
                units.extend(units_from_text_file(path, rel))
            elif path.suffix == ".md" and (
                in_wiki or any(path.match(g) for g in TEXT_GLOBS)
            ):
                units.extend(units_from_text_file(path, rel))
    return units


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------


def check_blacklist(unit: Unit, rules: dict[str, Any]) -> list[Finding]:
    out = []
    for rule in rules["blacklist"]:
        match = re.search(rule["pattern"], unit.text)
        if match:
            out.append(
                Finding(
                    unit.path,
                    unit.line,
                    rule["id"],
                    rule.get("severity", "error"),
                    rule["message"],
                    unit.text,
                )
            )
    return out


def bench_allowed(unit: Unit, rules: dict[str, Any]) -> bool:
    if any(token in unit.path for token in rules.get("bench_allow_paths", [])):
        return True
    return any(marker in unit.text for marker in rules.get("bench_allow_markers", []))


def check_bench_names(unit: Unit, rules: dict[str, Any]) -> list[Finding]:
    if bench_allowed(unit, rules):
        return []
    out = []
    for rule in rules.get("bench_only_names", []):
        if re.search(rule["pattern"], unit.text):
            out.append(
                Finding(
                    unit.path,
                    unit.line,
                    rule["id"],
                    rule.get("severity", "error"),
                    rule["message"],
                    unit.text,
                )
            )
    return out


def _model_regex(rules: dict[str, Any]) -> re.Pattern[str]:
    brands = "|".join(re.escape(b) for b in rules["brands"])
    quals = "|".join(re.escape(q) for q in rules["qualifiers"])
    return re.compile(
        rf"\b({brands})\b(?:[\s ]+(?:{quals})\b)*[\s ]+"
        r"([A-Za-z]{0,3}\d{1,4}[A-Za-z]{0,3}(?:-[A-Za-z0-9]{1,3})?)\b"
    )


def _token_matches(token: str, known: list[str]) -> bool:
    """``S21xx`` / ``R21xx-12`` are wildcards standing in for a whole series."""
    upper = token.upper()
    if upper in known:
        return True
    if "X" not in upper:
        return False
    probe = re.compile("^" + re.escape(upper).replace("X", "[0-9X]") + "$")
    return any(probe.match(candidate) for candidate in known)


def check_model_exists(unit: Unit, rules: dict[str, Any]) -> list[Finding]:
    out = []
    for match in _model_regex(rules).finditer(unit.text):
        brand, token = match.group(1), match.group(2)
        known = [m.upper() for m in rules["known_models"].get(brand, [])]
        known += [s.upper() for s in rules["known_series"].get(brand, [])]
        if _token_matches(token, known):
            continue
        digits = sum(c.isdigit() for c in token)
        if digits < 2:
            continue
        out.append(
            Finding(
                unit.path,
                unit.line,
                "unknown-model",
                "error",
                f"'{brand} {token}' 在产品库里查不到；核对型号或改写成产品族名",
                unit.text,
            )
        )
    return out


def _segments(unit: Unit) -> list[str]:
    """A table row pairs a device with its module cell by cell, not line by line."""
    if TABLE_ROW.match(unit.text):
        return [cell for cell in unit.text.split("|") if cell.strip()]
    return [unit.text]


def check_cross(unit: Unit, rules: dict[str, Any]) -> list[Finding]:
    out = []
    for rule in rules.get("cross_checks", []):
        for segment in _segments(unit):
            if not (
                re.search(rule["left"], segment) and re.search(rule["right"], segment)
            ):
                continue
            # A cell that lists both families ("J30 / J40 (Orin Nano / Orin NX)")
            # explains the module it is paired with; that is not a mismatch.
            if rule.get("unless") and re.search(rule["unless"], segment):
                continue
            out.append(
                Finding(
                    unit.path,
                    unit.line,
                    rule["id"],
                    rule.get("severity", "error"),
                    rule["message"],
                    segment,
                )
            )
            break
    return out


def check_prefer_family(unit: Unit, rules: dict[str, Any]) -> list[Finding]:
    """A bare SKU reads as an order code; outward prose wants the family name."""
    if not rules.get("prefer_family") or not unit.prose:
        return []
    out = []
    for family, skus in rules.get("preferred_family_names", {}).items():
        for sku in skus:
            if not re.search(r"\d", sku):
                continue
            if re.search(rf"\b{re.escape(sku)}\b", unit.text):
                out.append(
                    Finding(
                        unit.path,
                        unit.line,
                        "prefer-family-name",
                        "warn",
                        f"正文里出现具体 SKU '{sku}'；对外文本优先写 '{family}'，"
                        f"SKU 留给 BOM 与型号表",
                        unit.text,
                    )
                )
                break
    return out


def check_preset_families(
    path: Path, rel: str, rules: dict[str, Any]
) -> list[Finding]:
    """A preset's text must name the same product families as its device_refs."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    intro = data.get("intro") or {}
    catalog = intro.get("device_catalog") or {}
    family_models: dict[str, list[str]] = rules["family_models"]
    family_aliases: dict[str, list[str]] = rules.get("family_aliases", {})

    # model token -> families it can belong to
    token_families: dict[str, set[str]] = {}
    for family, tokens in family_models.items():
        for token in tokens:
            token_families.setdefault(token.upper(), set()).add(family)
    for family, tokens in family_aliases.items():
        for token in tokens:
            token_families.setdefault(token.upper(), set()).add(family)

    out: list[Finding] = []
    for preset in intro.get("presets") or []:
        refs: set[str] = set()
        for group in preset.get("device_groups") or []:
            if group.get("device_ref"):
                refs.add(group["device_ref"])
            for option in group.get("options") or []:
                if option.get("device_ref"):
                    refs.add(option["device_ref"])
        families = {catalog.get(ref, {}).get("family_id", ref) for ref in refs}
        families |= refs
        if not families & set(family_models):
            continue  # preset has no catalogued compute device; nothing to compare

        texts = []
        for key in ("name", "name_i18n", "description", "description_i18n"):
            texts.extend(_i18n_values(preset.get(key)))
        blob = " ".join(texts)
        if not blob:
            continue
        for token, owners in token_families.items():
            if not owners & set(family_models):
                continue
            if not re.search(rf"\b{re.escape(token)}\b", blob, re.IGNORECASE):
                continue
            if owners & families:
                continue
            out.append(
                Finding(
                    rel,
                    _find_line(lines, texts[0]),
                    "preset-family-mismatch",
                    "error",
                    f"套餐 {preset.get('id')!r} 文本里写了 {token}"
                    f"（属于 {sorted(owners)}），但它的 device_ref 指向 "
                    f"{sorted(families & set(family_models))}",
                    blob,
                )
            )
    return out


# --------------------------------------------------------------------------


def lint(roots: Iterable[Path], rules: dict[str, Any], repo_root: Path) -> list[Finding]:
    roots = list(roots)
    findings: list[Finding] = []
    for unit in collect_units(roots, repo_root):
        findings.extend(check_blacklist(unit, rules))
        findings.extend(check_bench_names(unit, rules))
        findings.extend(check_model_exists(unit, rules))
        findings.extend(check_cross(unit, rules))
        findings.extend(check_prefer_family(unit, rules))
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("solution.yaml")):
            findings.extend(
                check_preset_families(path, str(path.relative_to(repo_root)), rules)
            )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, default=None)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument(
        "--warn-as-error", action="store_true", help="treat warnings as failures"
    )
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    roots = args.paths or DEFAULT_ROOTS
    rules = load_rules(args.rules)
    findings = lint(roots, rules, REPO_ROOT)

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity != "error"]
    ordered = sorted(findings, key=lambda f: (f.path, f.line, f.rule))
    if args.format == "json":
        print(json.dumps([f.__dict__ for f in ordered], ensure_ascii=False, indent=2))
        return 1 if errors or (warnings and args.warn_as_error) else 0
    for finding in ordered:
        print(finding.render())
    print(f"\nproduct-name lint: {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors or (warnings and args.warn_as_error):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
