"""``solutionctl deploy`` — drive the engine's headless deploy subcommand.

Resolves the engine binary, runs ``<bin> deploy <id> --json ...``, and renders
the NDJSON event stream line-by-line as it arrives.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import List, Optional

from ..engine_locator import locate_engine


def _render_event(event: dict) -> str:
    """Render one NDJSON deploy event as a concise human line."""
    etype = event.get("type") or event.get("event") or "event"
    if etype in ("deployment_started", "deployment_finished"):
        status = event.get("status", "")
        return f"[{etype}] {event.get('solution_id', '')} {status}".rstrip()
    if etype in ("step_started", "step_finished", "step_skipped"):
        step = event.get("step_id") or event.get("name") or ""
        status = event.get("status") or event.get("reason") or ""
        return f"  [{etype}] {step} {status}".rstrip()
    if etype == "log":
        return f"    {event.get('message', '')}"
    return f"[{etype}] {json.dumps(event, ensure_ascii=False)}"


def run(
    solution_id: str,
    connection: Optional[str] = None,
    preset: Optional[str] = None,
    device: Optional[str] = None,
    skip_verify: bool = False,
    solutions_dir: Optional[str] = None,
    extra: Optional[List[str]] = None,
) -> int:
    """Execute a deployment via the engine binary. Returns the exit code."""
    engine = locate_engine()
    print(f"Using engine: {engine}", file=sys.stderr)

    cmd = [str(engine), "deploy", solution_id, "--json", "--yes"]
    if connection:
        cmd += ["--connection", connection]
    if preset:
        cmd += ["--preset", preset]
    if device:
        cmd += ["--device", device]
    if skip_verify:
        cmd += ["--skip-verify"]
    if solutions_dir:
        cmd += ["--solutions-dir", solutions_dir]
    if extra:
        cmd += extra

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip("\n")
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            # Non-JSON trailing output (e.g. the final indented result block).
            print(line)
            continue
        if isinstance(event, dict):
            print(_render_event(event))
        else:
            print(line)
    return proc.wait()
