#!/usr/bin/env python3
"""Lint solutions to ensure no local .gif files exist or are referenced.

Local .gif files are excluded from the SenseCraft desktop installer package
(tauri.conf.json) to keep download size slim and prevent bloat.
Any GIF media must either be:
1. Uploaded to Seeed FTPS CDN (files.seeedstudio.com) and referenced via HTTPS URL.
2. Converted to animated WebP (.webp).
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SOLUTIONS_DIR = REPO_ROOT / "solutions"

_MARKDOWN_LOCAL_GIF_RE = re.compile(
    r"!\[.*?\]\((?!https?://)([^)]+\.gif)\)", re.IGNORECASE
)


def main() -> int:
    errors = []
    if not SOLUTIONS_DIR.is_dir():
        return 0

    for sol_dir in sorted(SOLUTIONS_DIR.iterdir()):
        if not sol_dir.is_dir() or sol_dir.name.startswith("."):
            continue

        # 1. On-disk check for *.gif
        for gif_path in sorted(sol_dir.rglob("*.gif")):
            if any(part.startswith(".") for part in gif_path.parts):
                continue
            rel = gif_path.relative_to(REPO_ROOT)
            errors.append(
                f"[ON-DISK] {rel}: local .gif file not allowed in solution packages. "
                "GIFs are excluded from desktop installer packaging. "
                "Upload to Seeed FTPS CDN (files.seeedstudio.com) or convert to animated WebP (.webp)."
            )

        # 2. Markdown reference check
        for md_file in sorted(sol_dir.glob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for match in _MARKDOWN_LOCAL_GIF_RE.findall(text):
                rel = md_file.relative_to(REPO_ROOT)
                errors.append(
                    f"[MARKDOWN] {rel}: image reference '{match}' points to a local .gif. "
                    "Use Seeed FTPS CDN URL or convert to .webp."
                )

    if errors:
        print("FAIL: Found local .gif files or references in solutions/:\n", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1

    print(f"✓ Verified 0 local .gif files across solutions in {SOLUTIONS_DIR.name}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
