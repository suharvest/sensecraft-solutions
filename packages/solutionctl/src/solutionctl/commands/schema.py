"""``solutionctl schema`` — export standard JSON Schema for solution deployment parameters.

Delegates directly to the engine's native ``schema`` subcommand for single-source-of-truth
parameter introspection and data output interface discovery.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Optional

from .._env import engine_env
from ..engine_locator import locate_engine


def run(
    solution_id: str,
    preset: Optional[str] = None,
    connection: Optional[str] = None,
    json_mode: bool = False,
    show_outputs: bool = False,
    lang: Optional[str] = None,
    solutions_dir: Optional[str] = None,
) -> int:
    """Execute schema inspection via the engine binary."""
    engine = locate_engine()

    cmd = [str(engine), "schema", solution_id]
    if preset:
        cmd += ["--preset", preset]
    if json_mode:
        cmd += ["--json"]
    if show_outputs:
        cmd += ["--outputs"]
    if connection:
        cmd += ["--connection", connection]
    if lang:
        cmd += ["--lang", lang]
    if solutions_dir:
        cmd += ["--solutions-dir", str(solutions_dir)]

    proc = subprocess.run(
        cmd,
        env=engine_env(solutions_dir),
    )
    return proc.returncode
