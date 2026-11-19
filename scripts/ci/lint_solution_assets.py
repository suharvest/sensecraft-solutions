#!/usr/bin/env python3
"""Lint solution packages for forbidden development, test, lock, and cache artifacts.

Solution packages under ``solutions/*/`` (directories containing ``solution.yaml``)
must ship only runtime/deployment assets and customer-facing documentation — not
unit test suites, dependency lockfiles, virtual environments, or tool caches.

Checks:
- Forbidden directories: ``tests/``, ``test/``, ``__tests__/``, ``node_modules/``,
  ``.venv/``, ``.pytest_cache/``
- Forbidden lockfiles: ``uv.lock``, ``package-lock.json``, ``yarn.lock``,
  ``pnpm-lock.yaml``
"""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_DIR_NAMES: frozenset[str] = frozenset(
    {
        "tests",
        "test",
        "__tests__",
        "node_modules",
        ".venv",
        ".pytest_cache",
    }
)

FORBIDDEN_FILE_NAMES: frozenset[str] = frozenset(
    {
        "uv.lock",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
    }
)


@dataclass
class Finding:
    path: str
    rule: str
    detail: str


def _iter_solution_dirs(root: Path) -> list[Path]:
    if (root / "solution.yaml").is_file():
        return [root]
    solutions_dir = root / "solutions"
    if not solutions_dir.is_dir():
        return []
    return [
        d
        for d in sorted(solutions_dir.iterdir())
        if d.is_dir() and not d.name.startswith(".") and (d / "solution.yaml").is_file()
    ]


def scan(root: str | Path) -> list[Finding]:
    """Scan ``root`` (repo root or single solution dir) for forbidden artifacts."""
    root_path = Path(root).resolve()
    findings: list[Finding] = []

    for sol_dir in _iter_solution_dirs(root_path):
        for dirpath, dirnames, filenames in os.walk(sol_dir):
            cur = Path(dirpath)
            kept_dirs: list[str] = []
            for dname in sorted(dirnames):
                if dname == ".git":
                    continue
                if dname in FORBIDDEN_DIR_NAMES:
                    rel = (cur / dname).relative_to(root_path).as_posix() + "/"
                    findings.append(
                        Finding(
                            path=rel,
                            rule="forbidden-dev-artifact",
                            detail=(
                                f"Forbidden development/test/cache directory '{dname}/' "
                                "must not be committed inside a solution package."
                            ),
                        )
                    )
                    continue
                kept_dirs.append(dname)
            dirnames[:] = kept_dirs

            for fname in sorted(filenames):
                if fname in FORBIDDEN_FILE_NAMES:
                    rel = (cur / fname).relative_to(root_path).as_posix()
                    findings.append(
                        Finding(
                            path=rel,
                            rule="forbidden-dev-artifact",
                            detail=(
                                f"Forbidden dependency lockfile '{fname}' "
                                "must not be committed inside a solution package."
                            ),
                        )
                    )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Repository root or single solution directory to scan (default: .)",
    )
    args = parser.parse_args()

    findings = scan(args.root)
    for f in findings:
        print(f"{f.path}: [{f.rule}] {f.detail}")

    print(f"\nsolution-assets lint: {len(findings)} issue(s) found.")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
