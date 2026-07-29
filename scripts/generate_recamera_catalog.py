#!/usr/bin/env python3
"""Generate the reCamera console install catalog from the ecosystem solution.

The console (supervisor) runs in the user's browser, which has internet access
even when the camera itself does not -- over USB the device has no default
route out, which is why the console has never been able to fetch a package
itself. So the browser downloads on its behalf: it reads this catalog, pulls
the .deb and any model files from the CDN, and pushes them to the device over
the existing chunked-upload API.

The catalog is DERIVED, never hand-written. Its source of truth is
solutions/recamera_ecosystem/: the device YAMLs carry the package URLs and
checksums, guide.md says which device belongs to which preset, and solution.yaml
carries the display copy. Hand-maintaining a second list of URLs and hashes is
how the version numbers rotted (see sscma-example-sg200x@9187c33); do not start
a new one.

Usage:
    uv run python scripts/generate_recamera_catalog.py                  # write + upload
    uv run python scripts/generate_recamera_catalog.py --no-upload      # write only
    uv run python scripts/generate_recamera_catalog.py --no-sizes       # skip HEAD probes
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SOLUTION_DIR = REPO_ROOT / "solutions" / "recamera_ecosystem"
EXCLUDED = {"supervisor"}
OSS_TARGET = "oss://sensecraft-statics/solution-app/recamera_ecosystem/catalog.json"

# guide.md structure: "## Preset: Name {#preset_id}" then, under it,
# "## Step N: ... {#step_id type=recamera_cpp ... config=devices/<file>.yaml}".
_PRESET_RE = re.compile(r"^##\s+Preset:.*?\{#([a-z0-9_]+)\}", re.M)
_STEP_RE = re.compile(r"^##\s+Step\s+\d+:[^\{]*\{#[^}]*?type=recamera_cpp[^}]*?config=(devices/[^\s}]+)", re.M)


def preset_to_device() -> dict[str, str]:
    """preset id -> the device YAML of its recamera_cpp step (if it has one)."""
    guide = (SOLUTION_DIR / "guide.md").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    marks = [(m.start(), m.group(1)) for m in _PRESET_RE.finditer(guide)]
    for i, (start, preset_id) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(guide)
        step = _STEP_RE.search(guide, start, end)
        if step:
            out[preset_id] = step.group(1)
    return out


def content_length(url: str) -> int | None:
    """Byte size from a HEAD, so the console can show it before downloading."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=20) as r:
            n = r.headers.get("Content-Length")
            return int(n) if n else None
    except Exception as e:  # noqa: BLE001 - a missing size is not fatal
        print(f"  ! HEAD failed for {url}: {e}", file=sys.stderr)
        return None


def build(with_sizes: bool) -> dict:
    solution = yaml.safe_load((SOLUTION_DIR / "solution.yaml").read_text(encoding="utf-8"))
    presets = {p["id"]: p for p in solution["intro"]["presets"]}
    mapping = preset_to_device()

    apps = []
    for preset_id, device_rel in sorted(mapping.items()):
        preset = presets.get(preset_id)
        if preset is None:
            print(f"  ! guide.md has preset '{preset_id}' with no solution.yaml entry", file=sys.stderr)
            continue

        device = yaml.safe_load((SOLUTION_DIR / device_rel).read_text(encoding="utf-8"))
        binary = device.get("binary") or {}
        deb = binary.get("deb_package") or {}
        if not deb.get("path"):
            # console/restore-style steps have no package to install
            continue

        # `name` is the package/service name, which every reCamera app keeps
        # equal to its gallery manifest id. The console matches installed apps
        # against this to know what NOT to offer.
        app_id = deb.get("name") or binary.get("service_name")
        if not app_id:
            print(f"  ! {device_rel} has no package name", file=sys.stderr)
            continue
        if app_id in EXCLUDED:
            # The console is what serves this catalog; offering to install it
            # from inside itself would restart the very page doing the install.
            # Console updates go through the SenseCraft App or a manual upload.
            continue

        entry = {
            "id": app_id,
            "preset": preset_id,
            "name": preset.get("name", app_id),
            "name_zh": (preset.get("name_i18n") or {}).get("zh", ""),
            "description": preset.get("description", ""),
            "description_zh": (preset.get("description_i18n") or {}).get("zh", ""),
            "package": {
                "url": deb["path"],
                "filename": deb["path"].rsplit("/", 1)[-1],
                "sha256": ((deb.get("checksum") or {}).get("sha256") or ""),
            },
            "models": [],
        }
        if with_sizes:
            entry["package"]["size"] = content_length(deb["path"])

        for m in binary.get("models") or []:
            if not m.get("path"):
                continue
            model = {
                "url": m["path"],
                "filename": m.get("filename") or m["path"].rsplit("/", 1)[-1],
                # Models live under /userdata, which has gigabytes free — unlike
                # the root partition the .deb lands on (~47MB on a used device).
                "target_path": m.get("target_path", "/userdata/local/models"),
                "sha256": ((m.get("checksum") or {}).get("sha256") or ""),
            }
            if with_sizes:
                model["size"] = content_length(m["path"])
            entry["models"].append(model)

        apps.append(entry)
        print(f"  {app_id:22} {len(entry['models'])} model(s)")

    return {
        "schema": 1,
        "source": "sensecraft-solutions/solutions/recamera_ecosystem",
        "apps": apps,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=REPO_ROOT / "dist" / "catalog.json")
    ap.add_argument("--no-upload", dest="upload", action="store_false", default=True)
    ap.add_argument("--no-sizes", dest="sizes", action="store_false", default=True)
    args = ap.parse_args()

    print("Building reCamera install catalog from recamera_ecosystem ...")
    catalog = build(args.sizes)
    if not catalog["apps"]:
        print("Refusing to write an empty catalog", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {args.output}  ({len(catalog['apps'])} apps)")

    if args.upload:
        cmd = ["ossutil", "cp", str(args.output), OSS_TARGET, "--force"]
        print(f"  uploading -> {OSS_TARGET}")
        subprocess.run(cmd, check=True, capture_output=True)
        print("Upload complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
