#!/usr/bin/env python3
"""Offline validation for family-keyed Solution device catalogs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import yaml


LOCAL_PREFIXES = ("generic_", "external_")
PRODUCT_DUPLICATE_FIELDS = {"family_id", "sku", "name", "name_i18n", "image", "product_url"}
RANGE_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)?\.\.(-?\d+(?:\.\d+)?)?\s*$")


def _value_matches(actual: Any, requirement: Any) -> bool:
    if isinstance(requirement, list):
        return any(str(actual) == str(item) for item in requirement)
    if isinstance(requirement, str):
        match = RANGE_RE.fullmatch(requirement)
        if match:
            try:
                number = float(actual)
            except (TypeError, ValueError):
                return False
            low = float(match.group(1)) if match.group(1) is not None else None
            high = float(match.group(2)) if match.group(2) is not None else None
            return (low is None or number >= low) and (high is None or number <= high)
    return str(actual) == str(requirement)


def _validate_require(
    label: str, family: dict, require: dict[str, Any], errors: list[str]
) -> None:
    axes = family.get("axes", {})
    for axis_id, requirement in require.items():
        axis = axes.get(axis_id)
        if axis is None:
            errors.append(f"{label}: purchase.require references unknown axis {axis_id!r}")
            continue
        declared = axis.get("values", [])
        requested = requirement if isinstance(requirement, list) else [requirement]
        if axis.get("type") != "number" and not (
            isinstance(requirement, str) and RANGE_RE.fullmatch(requirement)
        ):
            unknown = [v for v in requested if all(str(v) != str(d) for d in declared)]
            if unknown:
                errors.append(
                    f"{label}: purchase.require {axis_id!r} has unknown values {unknown!r}"
                )

    if require and not any(
        all(_value_matches(attrs.get(axis_id), spec) for axis_id, spec in require.items())
        for attrs in family.get("sku_attrs", [])
    ):
        errors.append(f"{label}: purchase.require matches no SKU in this family")


def validate_solution(path: Path, families: dict[str, dict]) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return [f"{path}: cannot parse YAML: {exc}"]
    intro = data.get("intro") or {}
    catalog = intro.get("device_catalog") or {}

    for key, raw_entry in catalog.items():
        entry = raw_entry or {}
        label = f"{path}: device_catalog.{key}"
        if key.startswith(LOCAL_PREFIXES):
            if entry.get("purchase"):
                errors.append(f"{label}: local-only devices cannot declare purchase constraints")
            continue
        family = families.get(key)
        if family is None:
            errors.append(f"{label}: key is not present in product-family manifest")
            continue
        duplicate = sorted(PRODUCT_DUPLICATE_FIELDS.intersection(entry))
        if duplicate:
            errors.append(f"{label}: product data must come from purchase_profile: {duplicate}")
        purchase = entry.get("purchase") or {}
        if not isinstance(purchase, dict):
            errors.append(f"{label}: purchase must be an object")
            continue
        require = purchase.get("require") or {}
        if not isinstance(require, dict):
            errors.append(f"{label}: purchase.require must be an object")
            continue
        _validate_require(label, family, require, errors)

    for preset in intro.get("presets") or []:
        for group in preset.get("device_groups") or []:
            refs = [
                option.get("device_ref")
                for option in group.get("options") or []
                if option.get("device_ref")
            ]
            if group.get("device_ref"):
                refs.append(group["device_ref"])
            if len(refs) != len(set(refs)):
                errors.append(
                    f"{path}: preset {preset.get('id')!r} group {group.get('id')!r} has duplicate device_ref"
                )
            for ref in refs:
                if ref not in catalog:
                    errors.append(f"{path}: device_ref {ref!r} is missing from device_catalog")
            default = group.get("default")
            if default and default not in catalog:
                errors.append(f"{path}: default {default!r} is missing from device_catalog")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("spec/product-family-manifest.json"))
    parser.add_argument("--solutions-dir", type=Path, default=Path("solutions"))
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    families = manifest.get("families", {})
    paths = sorted(args.solutions_dir.glob("*/solution.yaml"))
    errors = [error for path in paths for error in validate_solution(path, families)]
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print(
        f"product-family validation passed: {len(paths)} solutions, "
        f"{len(families)} known families"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
