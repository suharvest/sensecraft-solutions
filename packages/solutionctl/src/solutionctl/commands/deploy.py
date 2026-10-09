"""``solutionctl deploy`` — drive the engine's headless deploy subcommand.

Resolves the engine binary, runs ``<bin> deploy <id> --json ...``, and renders
the NDJSON event stream line-by-line as it arrives.
"""

from __future__ import annotations

import json
import subprocess
import sys
from typing import List, Optional

from .._env import engine_env
from ..engine_locator import locate_engine


# Key event types always rendered (the deploy skeleton: device/step lifecycle,
# pre-checks, final result). Everything else (notably ``log`` and ``progress``)
# is treated as noise unless ``--verbose`` is set or the line looks like an error.
_KEY_EVENT_TYPES = frozenset(
    {
        "deployment_completed",
        "device_started",
        "device_completed",
        "pre_check_started",
        "pre_check_passed",
        "pre_check_failed",
        "step_skipped",
        # Rust engine only: what to check after the deploy (url / endpoint /
        # instructions) and the final result line. The Python engine emits
        # neither, so nothing changes for it.
        "verify_required",
        "result",
    }
)

# Substrings that mark a log line as worth surfacing even in non-verbose mode.
_ERROR_HINTS = ("error", "fail", "exception", "traceback", "denied", "refused")


def _is_error_log(event: dict) -> bool:
    """True if a ``log`` event carries an error-ish message or level."""
    level = str(event.get("level") or "").lower()
    if level in ("error", "critical", "warning"):
        return True
    msg = str(event.get("message") or "").lower()
    return any(h in msg for h in _ERROR_HINTS)


def _should_render(event: dict, verbose: bool) -> bool:
    """Decide whether an event is worth printing in the current verbosity.

    Non-verbose: render the key lifecycle events plus any error-ish ``log``.
    Drop pure-noise ``log`` (docker layer pulls) and ``progress`` (httpx
    polling) events. Verbose: render everything.
    """
    if verbose:
        return True
    etype = event.get("type") or event.get("event") or ""
    if etype in _KEY_EVENT_TYPES:
        return True
    if etype == "log":
        return _is_error_log(event)
    return False


def _render_event(event: dict) -> str:
    """Render one NDJSON deploy event as a concise human line.

    Aligned to the event types the engine actually emits (see
    deployment_engine.py ``_broadcast_update`` / ``_broadcast_log``):
    ``device_started`` / ``device_completed`` / ``deployment_completed`` /
    ``progress`` / ``step_skipped`` / ``pre_check_*`` / ``log``.
    """
    etype = event.get("type") or event.get("event") or "event"
    device = event.get("device_id") or ""
    status = event.get("status") or ""
    step = event.get("step_id") or ""

    if etype == "deployment_completed":
        return f"[deployment_completed] {status}".rstrip()
    if etype in ("device_started", "device_completed"):
        return f"[{etype}] {device} {status}".rstrip()
    if etype in ("pre_check_started", "pre_check_passed", "pre_check_failed"):
        return f"  [{etype}] {device}".rstrip()
    if etype == "progress":
        pct = event.get("progress")
        msg = event.get("message") or ""
        prefix = f"  [progress] {device}"
        if step:
            prefix += f" {step}"
        if pct is not None:
            prefix += f" {pct}%"
        return f"{prefix} {msg}".rstrip()
    if etype == "verify_required":
        label = event.get("name") or event.get("step_id") or event.get("device_id") or ""
        kind = event.get("kind") or ""
        head = f"[verify_required] {label}"
        if kind:
            head += f" ({kind})"
        lines = [head]
        for key in ("url", "endpoint"):
            if event.get(key):
                lines.append(f"  {key}: {event[key]}")
        if event.get("sample_request"):
            sample = event["sample_request"]
            if not isinstance(sample, str):
                sample = json.dumps(sample, ensure_ascii=False)
            lines.append(f"  sample_request: {sample}")
        if event.get("instructions"):
            lines.append(f"  {event['instructions']}")
        return "\n".join(lines)
    if etype == "result":
        return f"[result] {event.get('deployment_id') or ''} {event.get('status') or ''}".rstrip()
    if etype == "step_skipped":
        reason = event.get("reason") or ""
        return f"  [step_skipped] {device} {step} {reason}".rstrip()
    if etype == "log":
        return f"    {event.get('message', '')}"
    return f"[{etype}] {json.dumps(event, ensure_ascii=False)}"


def run(
    solution_id: str,
    connection: Optional[str] = None,
    inputs: Optional[List[str]] = None,
    inputs_file: Optional[str] = None,
    preset: Optional[str] = None,
    device: Optional[str] = None,
    skip_verify: bool = False,
    solutions_dir: Optional[str] = None,
    replace_existing: bool = False,
    verbose: bool = False,
    extra: Optional[List[str]] = None,
) -> int:
    """Execute a deployment via the engine binary. Returns the exit code.

    The engine reads its solutions/devices dirs from the environment
    (``PS_SOLUTIONS_DIR`` / ``PS_DEVICES_DIR``) via :func:`engine_env`; we don't
    pass ``--solutions-dir`` on the command line. Output is converged by default:
    only the lifecycle skeleton + error logs are rendered (``--verbose`` shows
    the full docker-pull / httpx-polling firehose).
    """
    engine = locate_engine()
    print(f"Using engine: {engine}", file=sys.stderr)

    cmd = [str(engine), "deploy", solution_id, "--json", "--yes"]
    if connection:
        cmd += ["--connection", connection]
    if inputs:
        for item in inputs:
            cmd += ["--input", item]
    if inputs_file:
        cmd += ["--inputs-file", str(inputs_file)]
    if preset:
        cmd += ["--preset", preset]
    if device:
        cmd += ["--device", device]
    if skip_verify:
        cmd += ["--skip-verify"]
    if replace_existing:
        cmd += ["--replace-existing"]
    if extra:
        cmd += extra

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1,
        env=engine_env(solutions_dir),
    )
    assert proc.stdout is not None
    result_status: Optional[str] = None
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
            if event.get("type") == "result" and event.get("status"):
                result_status = str(event["status"])
            if _should_render(event, verbose):
                print(_render_event(event))
        else:
            print(line)
    rc = proc.wait()
    # The Rust engine ends with a ``{"type":"result","status":...}`` line; a
    # non-completed status is a failure even if the process exit code was 0.
    # The Python engine emits no such line, so its exit code is used as is.
    if rc == 0 and result_status is not None and result_status != "completed":
        return 1
    return rc
