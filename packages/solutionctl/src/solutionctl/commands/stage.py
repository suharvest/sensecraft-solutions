"""``solutionctl stage`` — prepare a solution for an offline deploy.

The same flow the app offers, from a terminal: see what a preset's steps need
and whether they can be fully offline (``plan``), download it here
(``prepare``), check what is on this machine (``list`` / ``verify`` /
``changes``), free space (``delete``), and carry it to the machine that will
deploy (``export`` / ``import``).

Zero engine logic lives here: every subcommand is one call to the engine's
REST API, started headless for the duration (see ``_engine_http``).
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
from typing import Any, Dict, List, Optional

from .._engine_http import EngineHttpError, get, headless_engine, post

_POLL_SECONDS = 1.0

# Engine messages can quote the request that caused them, and a deploy
# request carries an SSH password. Never print one.
_SECRET_KEYS = r"password|passwd|secret|token|api[_-]?key|private[_-]?key"
_SECRET_KEY_RE = re.compile(rf"^(?:{_SECRET_KEYS})$", re.I)
# key, then : or =, then a quoted value (escapes included) or a bare one.
_SECRET_RE = re.compile(
    rf"""(?P<key>["']?\b(?:{_SECRET_KEYS})\b["']?\s*[:=]\s*)
         (?P<value>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\S+)""",
    re.I | re.X,
)


def _redact(text: object) -> str:
    """Mask credential-looking values in anything we print.

    Engine messages can quote the request that caused them, a deploy request
    carries an SSH password, and a download URL can carry a token; a CI log
    is forever.
    """
    return _SECRET_RE.sub(lambda m: f"{m.group('key')}<REDACTED>", str(text))


def _redacted_json(value: Any) -> str:
    """The payload as JSON, with credentials masked, structure intact.

    Both shapes are handled: a secret inside a string (an error message
    quoting a request) and a secret as a field of its own, where the key and
    the value are separate JSON nodes and no single string shows both.
    """

    def walk(node, key: Optional[str] = None):
        if isinstance(node, dict):
            return {k: walk(v, k) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v, key) for v in node]
        if key and _SECRET_KEY_RE.match(key) and node not in (None, ""):
            return "<REDACTED>"
        return _redact(node) if isinstance(node, str) else node

    return json.dumps(walk(value), ensure_ascii=False, indent=2)


def _human(n: int) -> str:
    """Bytes as the user reads them."""
    value = float(n or 0)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _parse_pairs(values: Optional[List[str]], what: str) -> Dict[str, List[str]]:
    """``--target step=value`` options into ``{step: [values]}``.

    Repeating a step is how several targets of one step are staged, so the
    values accumulate; repeating the exact same pair is rejected rather than
    silently collapsed.
    """
    out: Dict[str, List[str]] = {}
    for raw in values or []:
        key, sep, value = raw.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or not key or not value:
            raise ValueError(f"--{what} expects <step>=<value>, got {raw!r}")
        bucket = out.setdefault(key, [])
        if value in bucket:
            raise ValueError(f"--{what} {key}={value} given twice")
        bucket.append(value)
    return out


def _single(pairs: Dict[str, List[str]], what: str) -> Dict[str, str]:
    """One value per step (architectures, unlike targets, are not repeated)."""
    out = {}
    for step, values in pairs.items():
        if len(values) > 1:
            raise ValueError(f"--{what} for {step} given more than once")
        out[step] = values[0]
    return out


def _plan_payload(args) -> Dict[str, Any]:
    return {
        "solution_id": args.solution_id,
        "preset_id": args.preset,
        "targets": _parse_pairs(args.target, "target") or None,
        "arch": _single(_parse_pairs(args.arch, "arch"), "arch"),
        "params": json.loads(args.params) if args.params else {},
        "verify": True,
        "lang": args.lang or "en",
    }


def _print_entries(entries: List[dict], *, show_items: bool = True) -> None:
    for entry in entries:
        target = entry.get("target_id") or "-"
        arch = f" [{entry['arch']}]" if entry.get("arch") else ""
        print(f"{entry['step_id']} x {target}{arch}: {entry['verdict']}")
        for reason in entry.get("reasons") or []:
            print(f"    partial: {reason}")
        for error in entry.get("errors") or []:
            print(f"    error: {_redact(error)}")
        if not show_items:
            continue
        for item in entry.get("items") or []:
            status = item.get("status") or "unknown"
            detail = f" ({_redact(item['detail'])})" if item.get("detail") else ""
            # The source can be a URL with a token in its query string.
            print(f"    {status:<8} {item['kind']:<5} {_redact(item['source'])}{detail}")


def _exit_code(entries: List[dict], require_full: bool = False) -> int:
    """0 when everything the manifest lists is on this machine.

    2: the manifest could not be derived. 1: something it lists is not here.
    3: with ``--require-full``, everything is here but the solution does not
    declare that it needs nothing else on site (``partial`` / ``unknown``) --
    off by default, since no solution declares this yet and a CI job asking
    "did the download succeed" would otherwise always fail.
    """
    if any(e.get("errors") for e in entries):
        return 2
    if any(
        item.get("status") != "ready" for e in entries for item in e.get("items") or []
    ):
        return 1
    if require_full and any(e.get("verdict") != "full" for e in entries):
        return 3
    return 0


def plan(args) -> int:
    payload = _plan_payload(args)  # before the engine starts: fail fast on typos
    with headless_engine(args.solutions_dir) as base_url:
        data = post(base_url, "/api/staging/plan", payload)
    entries = data.get("entries") or []
    if args.json:
        print(_redacted_json(data))
    else:
        if not entries:
            print("Nothing to prepare for this preset.")
        _print_entries(entries)
    return _exit_code(entries, args.require_full)


def prepare(args) -> int:
    payload = dict(_plan_payload(args), refresh=bool(args.refresh))
    # Built first, so a malformed --target/--arch/--params never costs an
    # engine start.
    with headless_engine(args.solutions_dir) as base_url:
        job = post(base_url, "/api/staging/prepare", payload)
        job_id = job["id"]
        seen = None
        while job.get("status") == "running":
            time.sleep(_POLL_SECONDS)
            job = get(base_url, f"/api/staging/jobs/{job_id}")
            message = _redact(f"{job.get('progress', 0):>3}% {job.get('message', '')}")
            if message != seen and not args.json:
                print(message, file=sys.stderr)
                seen = message
    if args.json:
        print(_redacted_json(job))
    else:
        print(f"{job.get('status')}: {_redact(job.get('message', ''))}")
        _print_entries(job.get("entries") or [])
        for error in job.get("errors") or []:
            print(f"    error: {_redact(error)}")
    if job.get("status") != "completed":
        return 2
    return _exit_code(job.get("entries") or [], args.require_full)


def list_entries(args) -> int:
    with headless_engine(args.solutions_dir) as base_url:
        data = get(base_url, "/api/staging/entries")
        changes = (
            post(base_url, "/api/staging/entries/changes").get("changes") or []
            if args.check
            else []
        )
    entries = data.get("entries") or []
    if args.json:
        print(_redacted_json({**data, "changes": changes}))
        # A listing reports, it does not judge -- same exit code either way.
        return 0
    if not entries:
        print("Nothing prepared on this machine.")
        return 0
    by_key = {c["key"]: c for c in changes}
    for entry in entries:
        key = "/".join(
            [
                entry["solution_id"],
                entry["preset_id"],
                entry["step_id"],
                entry.get("target_id") or "-",
            ]
            + ([entry["arch"]] if entry.get("arch") else [])
        )
        note = ""
        change = by_key.get(key)
        if change:
            pending = len(change.get("added") or []) + len(change.get("changed") or [])
            if change.get("error"):
                note = f"  [{_redact(change['error'])}]"
            elif pending or change.get("stale"):
                note = f"  [update: {pending} item(s)"
                note += ", solution changed]" if change.get("stale") else "]"
        print(f"{key}: {entry['verdict']}{note}")
    print(f"\n{len(entries)} entr(ies), {_human(data.get('total_bytes', 0))} in "
          f"{data.get('files', 0)} file(s)")
    return 0


def _refs(args) -> List[dict]:
    """``--entry solution/preset/step[/target[/arch]]`` into API refs."""
    refs = []
    for raw in args.entry or []:
        parts = raw.split("/")
        if not 3 <= len(parts) <= 5 or any(not p.strip() for p in parts[:3]):
            raise ValueError(
                f"--entry expects solution/preset/step[/target[/arch]], got {raw!r}"
            )
        ref = {
            "solution_id": parts[0],
            "preset_id": parts[1],
            "step_id": parts[2],
        }
        if len(parts) > 3 and parts[3] != "-":
            ref["target_id"] = parts[3]
        if len(parts) > 4:
            ref["arch"] = parts[4]
        refs.append(ref)
    return refs


def delete(args) -> int:
    refs = _refs(args)  # before the engine starts
    if not refs:
        print("Nothing to delete: pass --entry solution/preset/step[/target[/arch]]",
              file=sys.stderr)
        return 2
    with headless_engine(args.solutions_dir) as base_url:
        data = post(base_url, "/api/staging/entries/delete", refs)
    if args.json:
        print(_redacted_json(data))
    else:
        for key in data.get("deleted") or []:
            print(f"deleted {key}")
        for key in data.get("not_found") or []:
            print(f"not prepared: {key}", file=sys.stderr)
        print(f"freed {_human(data.get('freed_bytes', 0))}")
    return 1 if data.get("not_found") else 0


def export(args) -> int:
    payload = {"path": args.file, "entries": _refs(args)}  # before the engine starts
    with headless_engine(args.solutions_dir) as base_url:
        data = post(base_url, "/api/staging/export", payload, timeout=3600.0)
    if args.json:
        print(_redacted_json(data))
    else:
        print(
            f"wrote {data['path']}: {data['entries']} entr(ies), "
            f"{data['files']} file(s), {_human(data['bytes'])}"
        )
    return 0


def import_(args) -> int:
    with headless_engine(args.solutions_dir) as base_url:
        data = post(
            base_url, "/api/staging/import", {"path": args.file}, timeout=3600.0
        )
    if args.json:
        print(_redacted_json(data))
        return 1 if (data.get("conflicts") or data.get("incomplete")) else 0
    print(
        f"imported {len(data.get('imported') or [])}, "
        f"skipped {len(data.get('skipped') or [])} (already here)"
    )
    for problem in (data.get("conflicts") or []) + (data.get("incomplete") or []):
        print(f"    {_redact(problem)}", file=sys.stderr)
    return 1 if (data.get("conflicts") or data.get("incomplete")) else 0


_SUBCOMMANDS = {
    "plan": plan,
    "prepare": prepare,
    "list": list_entries,
    "delete": delete,
    "export": export,
    "import": import_,
}


def run(args) -> int:
    handler = _SUBCOMMANDS.get(args.stage_command)
    if handler is None:  # pragma: no cover - argparse rejects these first
        print(f"Unknown stage subcommand: {args.stage_command!r}", file=sys.stderr)
        return 2
    try:
        return handler(args)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except EngineHttpError as e:
        print(f"error: {_redact(e.detail)}", file=sys.stderr)
        return 2
    except (RuntimeError, urllib.error.URLError, OSError, TimeoutError) as e:
        # The engine could not be started or stopped answering: say so
        # instead of a traceback.
        print(f"error: engine unavailable: {_redact(e)}", file=sys.stderr)
        return 2
