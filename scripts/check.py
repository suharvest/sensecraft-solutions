#!/usr/bin/env python3
"""Unified validation runner for sensecraft-solutions.

Runs offline and online linters, contracts, and solution validations without
short-circuiting, providing a clear summary of all passed and failed checks.

Scopes:
  fast    : Lightweight offline contract and lint checks (ideal for pre-commit)
  full    : All offline checks, linters, unit tests, and solution schema validation
  network : Network checks (URL validation, mirror drift)
  all     : Comprehensive validation combining full and network checks (used in CI)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CheckResult:
    name: str
    description: str
    passed: bool
    duration: float
    output: str


def run_command(cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str]:
    start = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout
    except Exception as exc:
        return 2, f"Failed to execute {cmd}: {exc}"


def check_compose_naming() -> tuple[int, str]:
    return run_command([sys.executable, "scripts/check_compose_naming.py"])


def check_product_names_test() -> tuple[int, str]:
    return run_command([sys.executable, "-m", "pytest", "tests/test_product_name_lint.py", "-q"])


def check_product_names_lint() -> tuple[int, str]:
    return run_command([sys.executable, "scripts/ci/lint_product_names.py"])


def check_untested_wording_test() -> tuple[int, str]:
    return run_command([sys.executable, "-m", "pytest", "tests/test_untested_wording_lint.py", "-q"])


def check_untested_wording_lint() -> tuple[int, str]:
    return run_command([sys.executable, "scripts/ci/lint_untested_wording.py"])


def check_solution_content_test() -> tuple[int, str]:
    return run_command([sys.executable, "-m", "pytest", "tests/test_solution_content_lint.py", "-q"])


def check_solution_content_lint() -> tuple[int, str]:
    return run_command([sys.executable, "scripts/ci/lint_solution_content.py"])


def check_target_mode_test() -> tuple[int, str]:
    return run_command([sys.executable, "-m", "pytest", "tests/test_target_mode_exclusivity.py", "-q"])


def check_validate_product_families() -> tuple[int, str]:
    return run_command([sys.executable, "scripts/ci/validate_product_families.py"])


def check_public_repo_guard() -> tuple[int, str]:
    return run_command(["sh", "scripts/public-repo-guard.sh"])


def check_mirror_backend() -> tuple[int, str]:
    return run_command(["bash", "scripts/sync_retail_vision_backend.sh"])


def check_solutionctl_offline(only_solutions: Optional[list[str]] = None) -> tuple[int, str]:
    solutions_dir = REPO_ROOT / "solutions"
    if only_solutions:
        dirs = [solutions_dir / s for s in only_solutions if (solutions_dir / s).is_dir()]
    else:
        dirs = sorted([d for d in solutions_dir.iterdir() if d.is_dir()])

    rc = 0
    logs = []
    for d in dirs:
        code, out = run_command([
            "uv", "run", "--package", "sensecraft-solutionctl",
            "solutionctl", "validate", str(d), "--spec-dir", "spec"
        ])
        if code != 0:
            rc = 1
            logs.append(f"FAIL: {d.name}\n{out}")
        else:
            first_line = out.strip().splitlines()[0] if out.strip() else f"✓ {d.name} valid"
            logs.append(first_line)
    return rc, "\n".join(logs)


def check_solutionctl_network(only_solutions: Optional[list[str]] = None) -> tuple[int, str]:
    solutions_dir = REPO_ROOT / "solutions"
    if only_solutions:
        dirs = [solutions_dir / s for s in only_solutions if (solutions_dir / s).is_dir()]
    else:
        dirs = sorted([d for d in solutions_dir.iterdir() if d.is_dir()])

    rc = 0
    logs = []
    for d in dirs:
        code, out = run_command([
            "uv", "run", "--package", "sensecraft-solutionctl",
            "solutionctl", "validate", str(d), "--spec-dir", "spec", "--check-urls"
        ])
        if code != 0:
            rc = 1
            logs.append(f"FAIL: {d.name}\n{out}")
        else:
            first_line = out.strip().splitlines()[0] if out.strip() else f"✓ {d.name} valid"
            logs.append(first_line)
    return rc, "\n".join(logs)


CHECKS = [
    # (id, description, func, is_fast, is_full, is_network, is_all)
    ("compose-naming", "Compose filename mirror rewrite coverage", check_compose_naming, True, True, False, True),
    ("product-families", "Product family catalog constraints and purchase profile alignment", check_validate_product_families, True, True, False, True),
    ("product-names-lint", "Lint customer-facing product family names", check_product_names_lint, True, True, False, True),
    ("untested-wording-lint", "Lint customer-facing untested disclaimer patterns", check_untested_wording_lint, True, True, False, True),
    ("solution-content-lint", "Lint 4-part structure, headers and forbidden terms", check_solution_content_lint, True, True, False, True),
    ("product-names-test", "Unit tests for product name linting rules", check_product_names_test, False, True, False, True),
    ("untested-wording-test", "Unit tests for untested wording rules", check_untested_wording_test, False, True, False, True),
    ("solution-content-test", "Unit tests for solution content rules", check_solution_content_test, False, True, False, True),
    ("target-mode-test", "Unit tests for target deployment mode exclusivity", check_target_mode_test, False, True, False, True),
    ("solutionctl-offline", "Schema validation for all solution directories (offline)", lambda: check_solutionctl_offline(), False, True, False, True),
    ("public-guard", "Enforce public/closed boundaries and secrets isolation", check_public_repo_guard, False, False, False, True),
    ("mirror-backend", "Sync check for retail vision mirrored backend config", check_mirror_backend, False, False, True, True),
    ("solutionctl-network", "Schema validation with dead URL detection (--check-urls)", lambda: check_solutionctl_network(), False, False, True, False),
]


def run_checks(scope: str, specific_check: Optional[str] = None) -> int:
    selected = []
    for item in CHECKS:
        cid, desc, fn, is_fast, is_full, is_network, is_all = item
        if specific_check and cid != specific_check:
            continue
        if specific_check:
            selected.append(item)
            continue
        if scope == "fast" and is_fast:
            selected.append(item)
        elif scope == "full" and is_full:
            selected.append(item)
        elif scope == "network" and is_network:
            selected.append(item)
        elif scope == "all" and is_all:
            selected.append(item)

    if not selected:
        print(f"No checks matched scope '{scope}' or check id '{specific_check}'.")
        return 1

    print(f"\n🚀 Running sensecraft-solutions checks (scope: {scope}, items: {len(selected)})...\n")

    results: list[CheckResult] = []
    for cid, desc, fn, *_ in selected:
        t0 = time.perf_counter()
        rc, out = fn()
        dur = time.perf_counter() - t0
        passed = (rc == 0)
        results.append(CheckResult(name=cid, description=desc, passed=passed, duration=dur, output=out))
        status_icon = "✓" if passed else "✗"
        print(f"  {status_icon} [{dur:5.2f}s] {cid:<24} {desc}")

    # Summary
    failed_results = [r for r in results if not r.passed]
    print("\n" + "=" * 70)
    print("📊 CHECK SUMMARY")
    print("=" * 70)
    for r in results:
        status_str = "PASS" if r.passed else "FAIL"
        print(f"[{status_str:4}] {r.name:<24} ({r.duration:.2f}s) - {r.description}")

    total_time = sum(r.duration for r in results)
    print("-" * 70)
    print(f"Total: {len(results)} | Passed: {len(results) - len(failed_results)} | Failed: {len(failed_results)} | Elapsed: {total_time:.2f}s")
    print("=" * 70)

    if failed_results:
        print("\n❌ DETAILS OF FAILURES:\n")
        for r in failed_results:
            print(f"--- [FAIL] {r.name} ---")
            print(r.output.strip())
            print()
        return 1

    print("\n✅ All selected checks passed successfully!\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Unified validator for sensecraft-solutions.")
    parser.add_argument(
        "--scope",
        choices=["fast", "full", "network", "all"],
        default="full",
        help="Validation scope (default: full). Use 'fast' for pre-commit, 'all' for CI.",
    )
    parser.add_argument("--check", help="Run a single specific check by ID.")
    args = parser.parse_args()
    return run_checks(scope=args.scope, specific_check=args.check)


if __name__ == "__main__":
    raise SystemExit(main())
