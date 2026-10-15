#!/usr/bin/env python3
"""Materialize a disabled E1003 flash-review package; never access a device.

Maintainer authoring tool. No downloads, provisioning records, credentials,
serial access or publishing. End users do not run this script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "solutions/reterminal_e1003_ha"
FILES = (
    "solution.yaml",
    "description.md",
    "description_zh.md",
    "guide.md",
    "guide_zh.md",
    "gallery/e1003-product-official.jpg",
    "gallery/e1003-keyless-cover.png",
    "gallery/README.md",
    "assets/firmware/README.md",
    "assets/firmware/manifest.json",
)
OLD_STEP = "type=manual required=true verify=true config=devices/review_setup.yaml"
NEW_STEP = "type=esp32_usb required=true verify=true config=devices/e1003_usb.yaml"


def stage(firmware: Path, output: Path, *, source: Path = SOURCE) -> Path:
    """Check the artifact, then atomically create a new review directory."""
    # Reject private locations before even stat/read. Check both the supplied
    # path and its resolved target so symlinks cannot bypass this boundary.
    for path in (firmware, firmware.resolve()):
        if any(part in {"provisioning", "verification"} for part in path.parts):
            raise ValueError("Private provisioning/verification paths are forbidden")
    output = output.resolve()
    if output.is_relative_to(REPO) or REPO.is_relative_to(output):
        raise ValueError("Output must be outside the Git checkout")
    if output.exists():
        raise ValueError("Output already exists; choose a new review directory")
    if output.name != "reterminal_e1003_ha":
        raise ValueError("Output directory name must be reterminal_e1003_ha")

    manifest = json.loads((source / "assets/firmware/manifest.json").read_text())
    if firmware.stat().st_size != manifest["size_bytes"]:
        raise ValueError("Factory image size mismatch; no package created")
    payload = firmware.read_bytes()
    if hashlib.sha256(payload).hexdigest() != manifest["sha256"]:
        raise ValueError("Factory image SHA-256 mismatch; no package created")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".e1003-stage-", dir=output.parent) as tmp:
        candidate = Path(tmp) / output.name
        candidate.mkdir()
        for relative in FILES:
            origin = source / relative
            if origin.is_symlink():
                raise ValueError("Symlinks are not allowed in candidate content")
            target = candidate / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, target)
        (candidate / "assets/firmware/firmware.factory.bin").write_bytes(payload)
        template = source / "assets/firmware/esp32_usb.yaml.in"
        (candidate / "devices").mkdir()
        (candidate / "devices/e1003_usb.yaml").write_text(template.read_text())
        for lang in ("guide.md", "guide_zh.md"):
            guide = candidate / lang
            text = guide.read_text()
            if text.count(OLD_STEP) != 1:
                raise ValueError("Guide flash marker changed; update the staging tool")
            guide.write_text(text.replace(OLD_STEP, NEW_STEP))
        # Directory rename publishes only a fully built local package.
        candidate.rename(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firmware", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = stage(args.firmware, args.output)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Cannot stage candidate: {exc}\n")
    print(f"Local flash-review copy: {output}")
    print("enabled=false; provisioning/HA acceptance blocked; no device accessed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
