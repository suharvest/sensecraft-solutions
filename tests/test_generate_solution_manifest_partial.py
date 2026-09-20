"""--only: a partial publish may move the named entries and nothing else."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "generate_solution_manifest.py"
_spec = importlib.util.spec_from_file_location("generate_solution_manifest", _SCRIPT)
gsm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gsm)


def _entry(h: str, at: str = "2026-01-01T00:00:00Z") -> dict:
    return {"hash": f"sha256:{h}", "size": 1, "updated_at": at, "min_app_version": "0.2.0"}


LIVE = {
    "version": 1,
    "generated_at": "2026-01-01T00:00:00Z",
    "base_url": "https://example.invalid/solutions",
    "deprecated": ["retired_one"],
    "solutions": {"alpha": _entry("a1"), "old_name": _entry("b1"), "gamma": _entry("c1")},
}
NOW = "2026-02-02T00:00:00Z"


def test_only_the_named_entry_moves():
    built = {"alpha": _entry("a2", NOW)}
    merged = gsm.merge_partial_manifest(LIVE, built, ["alpha"], NOW)

    assert merged["solutions"]["alpha"] == built["alpha"]
    # Everything this run did not build is exactly what clients already see --
    # including an id the checkout has since renamed, and the deprecated list.
    assert merged["solutions"]["old_name"] == LIVE["solutions"]["old_name"]
    assert merged["solutions"]["gamma"] == LIVE["solutions"]["gamma"]
    assert list(merged["solutions"]) == list(LIVE["solutions"])
    assert merged["deprecated"] == ["retired_one"]
    assert merged["generated_at"] == NOW
    assert gsm.changed_ids(LIVE, merged) == ["alpha"]


def test_live_manifest_is_not_mutated():
    snapshot = json.dumps(LIVE, sort_keys=True)
    gsm.merge_partial_manifest(LIVE, {"alpha": _entry("a2", NOW)}, ["alpha"], NOW)
    assert json.dumps(LIVE, sort_keys=True) == snapshot


def test_a_new_solution_is_added_and_reported():
    merged = gsm.merge_partial_manifest(LIVE, {"delta": _entry("d1", NOW)}, ["delta"], NOW)
    assert "delta" in merged["solutions"]
    assert gsm.changed_ids(LIVE, merged) == ["delta"]


def test_republishing_identical_content_moves_only_its_own_timestamp():
    merged = gsm.merge_partial_manifest(LIVE, {"alpha": _entry("a1", NOW)}, ["alpha"], NOW)
    assert gsm.changed_ids(LIVE, merged) == ["alpha"]          # updated_at, same hash
    same = gsm.merge_partial_manifest(LIVE, {"alpha": LIVE["solutions"]["alpha"]}, ["alpha"], NOW)
    assert gsm.changed_ids(LIVE, same) == []


def test_changed_ids_compares_whole_entries():
    other = json.loads(json.dumps(LIVE))
    other["solutions"]["gamma"]["size"] = 2               # same hash, different size
    assert gsm.changed_ids(LIVE, other) == ["gamma"]


def test_asking_for_something_that_was_not_built_fails():
    with pytest.raises(KeyError):
        gsm.merge_partial_manifest(LIVE, {"alpha": _entry("a2")}, ["alpha", "gamma"], NOW)


def test_changed_ids_sees_additions_removals_and_rehashes():
    other = {"solutions": {"alpha": _entry("a1"), "gamma": _entry("c9"), "delta": _entry("d1")}}
    assert gsm.changed_ids(LIVE, other) == ["delta", "gamma", "old_name"]


def _run(monkeypatch, tmp_path, argv, live=None, fail_fetch=False):
    sol = tmp_path / "solutions"
    for name in ("alpha", "beta"):
        (sol / name).mkdir(parents=True)
        (sol / name / "solution.yaml").write_text(f"id: {name}\n", encoding="utf-8")
    (sol / "bundled_hashes.json").write_text(
        json.dumps({"alpha": "sha256:old-a", "beta": "sha256:old-b"}) + "\n", encoding="utf-8")

    fetches: list[bool] = []

    def fetch(base_url, from_origin=False):
        fetches.append(from_origin)
        _run.events.append("read-baseline")
        if fail_fetch:
            raise OSError("network down")
        if callable(live):
            return live(len(fetches))
        return live

    uploads: list[str] = []
    events: list[str] = []
    monkeypatch.setattr(gsm, "acquire_publish_lock", lambda note: events.append(f"lock:{note.split()[1]}"))
    monkeypatch.setattr(gsm, "release_publish_lock", lambda: events.append("unlock"))
    _run.events = events
    monkeypatch.setattr(gsm, "fetch_live_manifest", fetch)
    monkeypatch.setattr(gsm, "upload_to_oss", lambda local, remote: uploads.append(remote.rsplit("/", 1)[-1]))
    monkeypatch.setattr(gsm, "_dirty_paths", lambda _dir: [])
    out = tmp_path / "dist"
    monkeypatch.setattr(sys, "argv", ["x", "--solutions-dir", str(sol), "--output-dir", str(out), *argv])
    _run.fetches = fetches
    return sol, out, uploads


def test_partial_publish_uploads_one_zip_and_keeps_the_rest(monkeypatch, tmp_path):
    live = {"version": 1, "generated_at": "t0", "base_url": "u", "deprecated": [],
            "solutions": {"alpha": _entry("live-a"), "beta": _entry("live-b"), "renamed_away": _entry("live-r")}}
    sol, out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha"], live=live)
    gsm.main()

    assert uploads == ["alpha.zip", "manifest.json", "bundled_hashes.json"]
    # A real publish reads the OSS object, never the CDN -- and reads it again
    # right before uploading.
    assert _run.fetches == [True, True]
    assert not (out / "beta.zip").exists()
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["solutions"]["beta"] == live["solutions"]["beta"]
    assert manifest["solutions"]["renamed_away"] == live["solutions"]["renamed_away"]
    assert manifest["solutions"]["alpha"]["hash"] != "sha256:live-a"
    # The committed file moves in that one key only.
    repo = json.loads((sol / "bundled_hashes.json").read_text())
    assert repo["beta"] == "sha256:old-b"
    assert repo["alpha"] == manifest["solutions"]["alpha"]["hash"]


def test_partial_publish_refuses_without_a_live_manifest(monkeypatch, tmp_path):
    _sol, out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha"], fail_fetch=True)
    with pytest.raises(SystemExit) as exc:
        gsm.main()
    assert exc.value.code == 1
    assert uploads == [] and not (out / "manifest.json").exists()


def test_partial_publish_refuses_an_unknown_id(monkeypatch, tmp_path):
    _sol, _out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha,nope"], live=LIVE)
    with pytest.raises(SystemExit) as exc:
        gsm.main()
    assert exc.value.code == 1 and uploads == []


def test_empty_only_is_the_full_publish(monkeypatch, tmp_path):
    _sol, out, uploads = _run(monkeypatch, tmp_path, ["--only", ""])
    gsm.main()
    assert uploads == ["alpha.zip", "beta.zip", "manifest.json", "bundled_hashes.json"]
    assert set(json.loads((out / "manifest.json").read_text())["solutions"]) == {"alpha", "beta"}


def test_dry_run_reads_through_the_cdn_and_uploads_nothing(monkeypatch, tmp_path):
    live = {"version": 1, "generated_at": "t0", "base_url": "u", "deprecated": [],
            "solutions": {"alpha": _entry("live-a"), "beta": _entry("live-b")}}
    sol, _out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha", "--no-upload"], live=live)
    gsm.main()
    assert uploads == [] and _run.fetches == [False]
    assert json.loads((sol / "bundled_hashes.json").read_text())["alpha"] == "sha256:old-a"


def test_publish_aborts_when_the_baseline_moved_underneath_it(monkeypatch, tmp_path):
    first = {"version": 1, "generated_at": "t0", "base_url": "u", "deprecated": [],
             "solutions": {"alpha": _entry("live-a"), "beta": _entry("live-b")}}
    second = json.loads(json.dumps(first)); second["generated_at"] = "t1"
    second["solutions"]["beta"] = _entry("someone-elses-publish")
    sol, _out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha"],
                              live=lambda n: first if n == 1 else second)
    with pytest.raises(SystemExit) as exc:
        gsm.main()
    assert exc.value.code == 1 and uploads == []
    # ...and the committed hashes were not touched either.
    assert json.loads((sol / "bundled_hashes.json").read_text())["alpha"] == "sha256:old-a"


@pytest.mark.parametrize("value", [",", " , ", ",,", " ", "\t"])
def test_only_that_names_nothing_is_an_error_not_a_full_publish(monkeypatch, tmp_path, value):
    _sol, _out, uploads = _run(monkeypatch, tmp_path, ["--only", value], live=LIVE)
    with pytest.raises(SystemExit) as exc:
        gsm.main()
    assert exc.value.code == 1 and uploads == []


def test_partial_publish_refuses_a_solution_the_live_manifest_retires(monkeypatch, tmp_path):
    live = {"version": 1, "generated_at": "t0", "base_url": "u", "deprecated": ["alpha"],
            "solutions": {"beta": _entry("live-b")}}
    _sol, _out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha"], live=live)
    with pytest.raises(SystemExit) as exc:
        gsm.main()
    assert exc.value.code == 1 and uploads == []


def test_partial_publish_refuses_to_write_into_the_solutions_dir(monkeypatch, tmp_path):
    sol, _out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha"], live=LIVE)
    monkeypatch.setattr(sys, "argv", ["x", "--solutions-dir", str(sol), "--output-dir", str(sol), "--only", "alpha"])
    with pytest.raises(SystemExit) as exc:
        gsm.main()
    assert exc.value.code == 1 and uploads == []
    assert json.loads((sol / "bundled_hashes.json").read_text()) == {"alpha": "sha256:old-a", "beta": "sha256:old-b"}


def test_publish_takes_the_lock_before_reading_and_releases_it_after(monkeypatch, tmp_path):
    live = {"version": 1, "generated_at": "t0", "base_url": "u", "deprecated": [],
            "solutions": {"alpha": _entry("live-a"), "beta": _entry("live-b")}}
    _run(monkeypatch, tmp_path, ["--only", "alpha"], live=live)
    gsm.main()
    assert _run.events == ["lock:only=alpha", "read-baseline", "read-baseline", "unlock"]


def test_a_full_publish_is_locked_too(monkeypatch, tmp_path):
    _run(monkeypatch, tmp_path, [])
    gsm.main()
    assert _run.events == ["lock:only=ALL", "unlock"]


def test_the_lock_is_released_when_the_run_aborts(monkeypatch, tmp_path):
    _run(monkeypatch, tmp_path, ["--only", "alpha"], fail_fetch=True)
    with pytest.raises(SystemExit):
        gsm.main()
    assert _run.events[0] == "lock:only=alpha" and _run.events[-1] == "unlock"


def test_a_dry_run_takes_no_lock(monkeypatch, tmp_path):
    live = {"version": 1, "generated_at": "t0", "base_url": "u", "deprecated": [],
            "solutions": {"alpha": _entry("live-a")}}
    _run(monkeypatch, tmp_path, ["--only", "alpha", "--no-upload"], live=live)
    gsm.main()
    assert [e for e in _run.events if "lock" in e] == []


def test_a_held_lock_stops_the_run_before_anything_is_read_or_written(monkeypatch, tmp_path):
    sol, out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha"], live=LIVE)

    class _Done:
        def __init__(self, rc, out=""): self.returncode, self.stdout, self.stderr = rc, out, "FileAlreadyExists"
    calls: list[list[str]] = []

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return _Done(2) if cmd[:3] == ["ossutil", "api", "put-object"] else _Done(0, "2026-01-01T00:00:00Z only=ALL run=1")
    monkeypatch.undo()                       # real acquire_publish_lock, fake ossutil
    monkeypatch.setattr(gsm.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", ["x", "--solutions-dir", str(sol), "--output-dir", str(out), "--only", "alpha"])
    with pytest.raises(SystemExit) as exc:
        gsm.main()
    assert exc.value.code == 1
    assert calls[0][:3] == ["ossutil", "api", "put-object"] and "--forbid-overwrite" in calls[0]
    assert not any(c[:2] == ["ossutil", "cp"] for c in calls)      # no baseline read, no upload
    assert not any(c[:2] == ["ossutil", "rm"] for c in calls)      # never releases a lock it does not hold
    assert not out.exists() or not any(out.iterdir())
