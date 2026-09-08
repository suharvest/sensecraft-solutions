#!/usr/bin/env python3
"""Fail on "we did not measure this" wording in customer-facing solution copy.

Customer-facing copy states what was measured and what the reader can use. A
sentence whose content is "this was not tested" tells the reader nothing they
can act on, so it is either deleted or rewritten as the action the reader
should take ("measure it on your own line").

Scope: solutions/*/description*.md, solutions/*/guide*.md,
solutions/*/solution.yaml and solutions/*/devices/*.yaml. YAML comment lines
(internal notes to packagers, not shown to the reader) are exempt, as are the
literal config values `unverified` and `pending` that the runtime writes.
"""
from __future__ import annotations

import glob
import os
import re
import sys

UNTESTED_BLACKLIST = [
    r"未实测",
    r"没有实测",
    r"没测过",
    r"未测(?!量出)",
    r"待测",
    r"需核实",
    r"未核实",
    r"尚未实测",
    r"还没有实测",
    r"未经[^，。]{0,4}验证",
    r"未在[^，。]{0,8}验证",
    r"没有.{0,8}在硬件上",
    r"没上过硬件",
    r"未验证",
    r"理论值",
    r"外推",
    r"\bnot\s+(yet\s+)?(measured|tested|verified|validated)\b",
    r"\bhas\s+not\s+been\s+(measured|tested|verified|run)\b",
    r"\bhave\s+not\s+been\s+(measured|tested|verified|characterised|characterized)\b",
    r"\buntested\b",
    r"\bunmeasured\b",
    r"\bunverified\b",
    r"\bextrapolated\b",
    r"\bneeds?\s+verifying\b",
]

# Literal runtime values and product-availability facts, not claims about
# whether something was measured.
EXEMPT = re.compile(
    r"relay_contact=unverified"
    r"|fail_mode=unverified"
    r"|`unverified`"
    r"|calibration=pending"
    r"|estimated_time"
)

PATTERN = re.compile("|".join(UNTESTED_BLACKLIST), re.IGNORECASE)

GLOBS = [
    "solutions/*/description*.md",
    "solutions/*/guide*.md",
    "solutions/*/solution.yaml",
    "solutions/*/devices/*.yaml",
]


def scan(root: str) -> list[tuple[str, int, str, str]]:
    hits: list[tuple[str, int, str, str]] = []
    for pattern in GLOBS:
        for path in sorted(glob.glob(os.path.join(root, pattern))):
            is_yaml = path.endswith((".yaml", ".yml"))
            with open(path, encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, 1):
                    if is_yaml and line.lstrip().startswith("#"):
                        continue
                    if EXEMPT.search(line):
                        continue
                    match = PATTERN.search(line)
                    if match:
                        hits.append(
                            (os.path.relpath(path, root), lineno, match.group(0), line.strip())
                        )
    return hits


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    hits = scan(root)
    for path, lineno, term, line in hits:
        print(f"{path}:{lineno}: untested-wording '{term}': {line[:160]}")
    print(f"untested-wording lint: {len(hits)} error(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    raise SystemExit(main())
