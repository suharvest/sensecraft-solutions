"""``solutionctl stage`` — argument shapes, exit codes and output.

The engine is stubbed: what matters here is that the CLI sends what the API
expects and reports back honestly.
"""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from unittest.mock import patch

import pytest

from solutionctl.commands import stage


def _args(**kw):
    defaults = dict(
        solution_id="sol",
        preset="p",
        target=None,
        arch=None,
        params=None,
        lang="en",
        solutions_dir=None,
        json=False,
        require_full=False,
        refresh=False,
        check=False,
        entry=None,
        file=None,
        stage_command="plan",
    )
    defaults.update(kw)
    return argparse.Namespace(**defaults)


def _entry(statuses=("ready",), verdict="unknown", errors=(), **kw):
    return {
        "solution_id": "sol",
        "preset_id": "p",
        "step_id": "step1",
        "target_id": kw.get("target_id", "rk"),
        "arch": kw.get("arch", "aarch64"),
        "verdict": verdict,
        "errors": list(errors),
        "reasons": kw.get("reasons", []),
        "items": [
            {"kind": "image", "source": f"reg/app:{n}", "status": s}
            for n, s in enumerate(statuses)
        ],
    }


@contextmanager
def _engine(responses):
    """Stub the headless engine: {(method, path): payload}."""
    calls = []

    @contextmanager
    def fake_engine(solutions_dir=None):
        yield "http://engine"

    def fake_get(base_url, path, timeout=60.0):
        calls.append(("GET", path, None))
        return responses[("GET", path)]

    def fake_post(base_url, path, payload=None, timeout=60.0):
        calls.append(("POST", path, payload))
        return responses[("POST", path)]

    with patch.object(stage, "headless_engine", fake_engine), patch.object(
        stage, "get", fake_get
    ), patch.object(stage, "post", fake_post):
        yield calls


# --------------------------------------------------------------------------- #
# What the CLI sends
# --------------------------------------------------------------------------- #


def test_plan_sends_targets_arch_and_params():
    args = _args(
        target=["step1=rk", "step2=j40"],
        arch=["step1=both"],
        params='{"board": "rk3588"}',
    )
    with _engine({("POST", "/api/staging/plan"): {"entries": []}}) as calls:
        stage.plan(args)

    (_, _, payload) = calls[0]
    assert payload["targets"] == {"step1": ["rk"], "step2": ["j40"]}
    assert payload["arch"] == {"step1": "both"}
    assert payload["params"] == {"board": "rk3588"}
    assert payload["verify"] is True


def test_malformed_option_is_a_clear_error(capsys):
    assert stage.run(_args(target=["oops"])) == 2
    assert "expects <step>=<value>" in capsys.readouterr().err


def test_entry_refs_accept_optional_target_and_arch():
    refs = stage._refs(_args(entry=["s/p/step", "s/p/step/rk", "s/p/step/rk/aarch64",
                                    "s/p/step/-"]))
    assert refs == [
        {"solution_id": "s", "preset_id": "p", "step_id": "step"},
        {"solution_id": "s", "preset_id": "p", "step_id": "step", "target_id": "rk"},
        {
            "solution_id": "s",
            "preset_id": "p",
            "step_id": "step",
            "target_id": "rk",
            "arch": "aarch64",
        },
        {"solution_id": "s", "preset_id": "p", "step_id": "step"},
    ]


def test_entry_ref_without_a_step_is_refused(capsys):
    assert stage.run(_args(stage_command="delete", entry=["s/p"])) == 2
    assert "solution/preset/step" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Exit codes
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "entries,require_full,expected",
    [
        ([_entry(("ready", "ready"))], False, 0),
        ([_entry(("ready", "missing"))], False, 1),
        ([_entry(("ready",), errors=["arch cannot be inferred"])], False, 2),
        # Everything is here, but the solution does not declare it needs
        # nothing else: only --require-full treats that as failure.
        ([_entry(("ready",), verdict="partial")], False, 0),
        ([_entry(("ready",), verdict="partial")], True, 3),
        ([_entry(("ready",), verdict="full")], True, 0),
        ([], False, 0),
    ],
)
def test_exit_codes(entries, require_full, expected):
    assert stage._exit_code(entries, require_full) == expected


def test_plan_exit_code_reaches_the_shell():
    args = _args()
    with _engine({("POST", "/api/staging/plan"): {"entries": [_entry(("missing",))]}}):
        assert stage.plan(args) == 1


def test_prepare_reports_a_failed_job():
    job = {
        "id": "j1",
        "status": "failed",
        "progress": 100,
        "message": "Some items could not be prepared",
        "entries": [_entry(("missing",))],
        "errors": ["step1: 404 while downloading"],
    }
    with _engine({("POST", "/api/staging/prepare"): job}):
        assert stage.prepare(_args()) == 2


def test_prepare_polls_until_the_job_finishes():
    started = {"id": "j1", "status": "running", "progress": 0, "message": "..."}
    done = {
        "id": "j1",
        "status": "completed",
        "progress": 100,
        "message": "Offline package ready",
        "entries": [_entry(("ready",))],
        "errors": [],
    }
    with _engine(
        {("POST", "/api/staging/prepare"): started, ("GET", "/api/staging/jobs/j1"): done}
    ) as calls, patch.object(stage, "_POLL_SECONDS", 0):
        assert stage.prepare(_args()) == 0
    assert calls[-1][1] == "/api/staging/jobs/j1"


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #


def test_list_shows_size_and_pending_updates(capsys):
    responses = {
        ("GET", "/api/staging/entries"): {
            "entries": [_entry(("ready",))],
            "total_bytes": 3 * 1024 * 1024 * 1024,
            "files": 7,
        },
        ("POST", "/api/staging/entries/changes"): {
            "changes": [
                {
                    "key": "sol/p/step1/rk/aarch64",
                    "added": ["reg/new:1"],
                    "changed": [],
                    "removed": [],
                    "stale": True,
                    "error": None,
                }
            ]
        },
    }
    with _engine(responses):
        assert stage.list_entries(_args(check=True)) == 0

    out = capsys.readouterr().out
    assert "sol/p/step1/rk/aarch64: unknown" in out
    assert "update: 1 item(s), solution changed" in out
    assert "3.0 GB in 7 file(s)" in out


def test_list_without_check_does_not_ask_for_changes():
    responses = {
        ("GET", "/api/staging/entries"): {"entries": [], "total_bytes": 0, "files": 0}
    }
    with _engine(responses) as calls:
        stage.list_entries(_args(check=False))
    assert [c[1] for c in calls] == ["/api/staging/entries"]


def test_import_reports_conflicts_and_fails(capsys):
    result = {
        "entries": ["sol/p/step1/rk"],
        "imported": ["reg/a:1"],
        "skipped": [],
        "conflicts": ["reg/b:1: a different file is already cached at b.tar"],
        "incomplete": [],
    }
    with _engine({("POST", "/api/staging/import"): result}):
        assert stage.import_(_args(file="kit.tar")) == 1
    captured = capsys.readouterr()
    assert "imported 1" in captured.out
    assert "already cached" in captured.err


def test_delete_while_a_deployment_runs_is_reported(capsys):
    def boom(*a, **kw):
        raise stage.EngineHttpError(409, "A deployment is running; try again later")

    with patch.object(stage, "headless_engine") as engine, patch.object(
        stage, "post", boom
    ):
        engine.return_value.__enter__ = lambda _s: "http://engine"
        engine.return_value.__exit__ = lambda *_a: False
        assert stage.run(_args(stage_command="delete", entry=["s/p/step"])) == 2
    assert "A deployment is running" in capsys.readouterr().err


@pytest.mark.parametrize(
    "size,text",
    [(0, "0 B"), (512, "512 B"), (1536, "1.5 KB"), (5 * 1024**2, "5.0 MB"),
     (2 * 1024**3, "2.0 GB")],
)
def test_human_sizes(size, text):
    assert stage._human(size) == text


def test_json_mode_prints_the_payload_unchanged(capsys):
    data = {"entries": [_entry(("ready",))]}
    with _engine({("POST", "/api/staging/plan"): data}):
        stage.plan(_args(json=True))
    assert json.loads(capsys.readouterr().out) == data
