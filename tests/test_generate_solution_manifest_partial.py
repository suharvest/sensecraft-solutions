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


def test_republishing_identical_content_changes_nothing():
    merged = gsm.merge_partial_manifest(LIVE, {"alpha": _entry("a1", NOW)}, ["alpha"], NOW)
    assert gsm.changed_ids(LIVE, merged) == []


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

    def fetch(base_url):
        if fail_fetch:
            raise OSError("network down")
        return live

    uploads: list[str] = []
    monkeypatch.setattr(gsm, "fetch_live_manifest", fetch)
    monkeypatch.setattr(gsm, "upload_to_oss", lambda local, remote: uploads.append(remote.rsplit("/", 1)[-1]))
    monkeypatch.setattr(gsm, "_dirty_paths", lambda _dir: [])
    out = tmp_path / "dist"
    monkeypatch.setattr(sys, "argv", ["x", "--solutions-dir", str(sol), "--output-dir", str(out), *argv])
    return sol, out, uploads


def test_partial_publish_uploads_one_zip_and_keeps_the_rest(monkeypatch, tmp_path):
    live = {"version": 1, "generated_at": "t0", "base_url": "u", "deprecated": [],
            "solutions": {"alpha": _entry("live-a"), "beta": _entry("live-b"), "renamed_away": _entry("live-r")}}
    sol, out, uploads = _run(monkeypatch, tmp_path, ["--only", "alpha"], live=live)
    gsm.main()

    assert uploads == ["alpha.zip", "manifest.json", "bundled_hashes.json"]
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
