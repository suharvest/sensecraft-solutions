#!/usr/bin/env python3
"""Build the offline product-family contract used by solution CI.

The source is solution_bot's generated ``data/purchase_profiles/*.json``.
Only stable fields needed for authoring and validation are copied: family ids,
localized family titles, axes, and SKU attribute combinations. Concrete product
names, images, URLs, and SKUs are not authored in Solution files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _axis_values(axis: dict) -> list[str | int | float]:
    values: list[str | int | float] = []
    for item in axis.get("values", []):
        value = item.get("value") if isinstance(item, dict) else item
        if isinstance(value, (str, int, float)) and not isinstance(value, bool):
            values.append(value)
    return values


def _localized_title(value: object) -> dict[str, str]:
    """Return only non-empty string locale/value pairs.

    A missing or malformed title deliberately falls back to an empty object.
    Consumers should continue to identify the family by its stable id.
    """

    if not isinstance(value, dict):
        return {}
    return {
        locale.strip(): title.strip()
        for locale, title in value.items()
        if isinstance(locale, str)
        and locale.strip()
        and isinstance(title, str)
        and title.strip()
    }


def build_manifest(profiles_dir: Path) -> dict:
    families: dict[str, dict] = {}
    family_sources: dict[str, Path] = {}
    for path in sorted(profiles_dir.glob("*.json")):
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        family_id = profile.get("id") if isinstance(profile, dict) else None
        if not isinstance(family_id, str) or not family_id:
            continue
        if family_id in families:
            raise ValueError(
                f"duplicate product family id {family_id!r}: "
                f"{family_sources[family_id]} and {path}"
            )
        axes = {
            axis["id"]: {
                "type": axis.get("type", "enum"),
                "values": _axis_values(axis),
            }
            for axis in profile.get("axes", [])
            if isinstance(axis, dict) and isinstance(axis.get("id"), str)
        }
        sku_attrs = [
            sku.get("attrs", {})
            for sku in profile.get("skus", [])
            if isinstance(sku, dict) and isinstance(sku.get("attrs"), dict)
        ]
        families[family_id] = {
            "title": _localized_title(profile.get("title")),
            "axes": axes,
            "sku_attrs": sku_attrs,
        }
        family_sources[family_id] = path

    return {
        "schema_version": 1,
        "family_count": len(families),
        "families": dict(sorted(families.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profiles-dir",
        type=Path,
        required=True,
        help="solution_bot/data/purchase_profiles directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("spec/product-family-manifest.json"),
    )
    args = parser.parse_args()
    manifest = build_manifest(args.profiles_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.output} ({manifest['family_count']} families)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
