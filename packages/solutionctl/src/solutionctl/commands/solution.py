"""``solutionctl solution`` — discover solutions via the engine binary.

Resolves the engine binary and drives its headless ``solution`` subcommands:

* ``solution list``         → ``<bin> solution list``
* ``solution show <id>``    → ``<bin> solution show <id> [--lang ...]``

The engine already emits JSON on stdout, so we pass it through verbatim and
forward the engine's exit code. Zero engine code lives here — this module only
locates the binary and runs it as a subprocess (same pattern as ``deploy.py``).
"""

from __future__ import annotations

import subprocess
import sys
from typing import List, Optional

from ..engine_locator import locate_engine


def _run_engine(args: List[str]) -> int:
    """Run ``<engine> <args...>``, stream stdout through, forward exit code."""
    engine = locate_engine()
    print(f"Using engine: {engine}", file=sys.stderr)

    cmd = [str(engine), *args]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=sys.stderr, text=True)
    # Engine already prints JSON; pass it through unchanged.
    sys.stdout.write(proc.stdout)
    if proc.stdout and not proc.stdout.endswith("\n"):
        sys.stdout.write("\n")
    return proc.returncode


def run_list(solutions_dir: Optional[str] = None) -> int:
    """List available solutions (``<bin> solution list``)."""
    args = ["solution", "list"]
    if solutions_dir:
        args += ["--solutions-dir", solutions_dir]
    return _run_engine(args)


def run_show(
    solution_id: str,
    lang: Optional[str] = None,
    solutions_dir: Optional[str] = None,
) -> int:
    """Show one solution's detail incl. presets (``<bin> solution show <id>``)."""
    args = ["solution", "show", solution_id]
    if lang:
        args += ["--lang", lang]
    if solutions_dir:
        args += ["--solutions-dir", solutions_dir]
    return _run_engine(args)
