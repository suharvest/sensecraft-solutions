"""Unit tests for the shared engine-free static checks.

Each check gets a "good" fixture (no errors) and a "bad" fixture (the specific
violation it guards against). Fixtures are built on tmp_path so the tests are
hermetic and don't depend on the real solutions/ tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sensecraft_solution_spec import checks


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _make_solution(base: Path, *, files: dict[str, str] | None = None) -> Path:
    """Create a solution dir at ``base`` and write ``files`` (relative paths)."""
    base.mkdir(parents=True, exist_ok=True)
    for rel, content in (files or {}).items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# check_referenced_files
# ---------------------------------------------------------------------------


def test_referenced_files_good(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={"description.md": "x", "gallery/cover.png": "x", "g/a.png": "x"},
    )
    data = {
        "intro": {
            "description_file": "description.md",
            "cover_image": "gallery/cover.png",
            "gallery": [{"src": "g/a.png"}],
            "device_catalog": {"d": {"image": "https://example.com/x.png"}},
        }
    }
    assert checks.check_referenced_files(sol, data) == []


def test_referenced_files_bad_missing(tmp_path):
    sol = _make_solution(tmp_path / "s")
    data = {
        "intro": {
            "description_file": "nope.md",
            "cover_image": "gallery/missing.png",
            "gallery": [{"src": "g/missing.png"}],
        }
    }
    errs = checks.check_referenced_files(sol, data)
    assert len(errs) == 3
    assert any("nope.md" in e for e in errs)
    assert any("missing.png" in e for e in errs)


def test_referenced_files_url_is_skipped(tmp_path):
    sol = _make_solution(tmp_path / "s")
    data = {"intro": {"cover_image": "https://cdn.example.com/cover.png"}}
    assert checks.check_referenced_files(sol, data) == []


# ---------------------------------------------------------------------------
# check_referenced_device_assets
# ---------------------------------------------------------------------------


def test_referenced_device_assets_good(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/d.yaml": (
                "id: d\n"
                "docker:\n"
                "  compose_file: assets/docker/docker-compose.yml\n"
            ),
            "assets/docker/docker-compose.yml": "services: {}\n",
        },
    )
    assert checks.check_referenced_device_assets(sol, {}) == []


def test_referenced_device_assets_bad_missing(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/d.yaml": (
                "id: d\n"
                "docker:\n"
                "  compose_file: assets/docker/ghost.yml\n"
            ),
        },
    )
    errs = checks.check_referenced_device_assets(sol, {})
    assert len(errs) == 1
    assert "ghost.yml" in errs[0]


def test_referenced_device_assets_url_skipped(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/d.yaml": (
                "id: d\n"
                "firmware:\n"
                "  path: https://cdn.example.com/fw.bin\n"
            ),
        },
    )
    assert checks.check_referenced_device_assets(sol, {}) == []


# ---------------------------------------------------------------------------
# check_i18n_completeness
# ---------------------------------------------------------------------------


def test_i18n_completeness_single_lang_noop(tmp_path):
    """No active extra languages → nothing to check."""
    sol = _make_solution(tmp_path / "s")
    data = {"intro": {"presets": [{"id": "p", "name": "P"}]}}
    assert checks.check_i18n_completeness(sol, data) == []


def test_i18n_completeness_good(tmp_path):
    sol = _make_solution(tmp_path / "s", files={"description_zh.md": "x", "guide_zh.md": "x"})
    data = {
        "name_i18n": {"zh": "名称"},
        "deployment": {"guide_file_i18n": {"zh": "guide_zh.md"}},
        "intro": {
            "summary_i18n": {"zh": "摘要"},
            "description_file_i18n": {"zh": "description_zh.md"},
            "presets": [{"id": "p", "name": "P", "name_i18n": {"zh": "套餐"}}],
        },
    }
    assert checks.check_i18n_completeness(sol, data) == []


def test_i18n_completeness_bad_missing(tmp_path):
    sol = _make_solution(tmp_path / "s", files={"description_zh.md": "x"})
    data = {
        # zh active (description_zh.md exists) but name_i18n.zh / summary missing
        "intro": {
            "description_file_i18n": {"zh": "description_zh.md"},
            "presets": [{"id": "p", "name": "P"}],
        },
    }
    errs = checks.check_i18n_completeness(sol, data)
    assert errs  # several missing fields
    assert any("name_i18n.zh" in e for e in errs)
    assert any("summary_i18n.zh" in e for e in errs)


# ---------------------------------------------------------------------------
# check_duplicate_ids
# ---------------------------------------------------------------------------


def test_duplicate_ids_good():
    data = {
        "intro": {
            "presets": [
                {"id": "a", "device_groups": [{"id": "g1"}, {"id": "g2"}]},
                {"id": "b"},
            ]
        }
    }
    assert checks.check_duplicate_ids(data) == []


def test_duplicate_ids_bad_preset():
    data = {"intro": {"presets": [{"id": "dup"}, {"id": "dup"}]}}
    errs = checks.check_duplicate_ids(data)
    assert len(errs) == 1
    assert "dup" in errs[0]


def test_duplicate_ids_bad_group():
    data = {"intro": {"presets": [{"id": "p", "device_groups": [{"id": "g"}, {"id": "g"}]}]}}
    errs = checks.check_duplicate_ids(data)
    assert len(errs) == 1
    assert "g" in errs[0]


# ---------------------------------------------------------------------------
# check_device_ref_integrity
# ---------------------------------------------------------------------------


def test_device_ref_integrity_good():
    data = {
        "intro": {
            "device_catalog": {"cam": {}},
            "presets": [
                {
                    "id": "p",
                    "device_groups": [
                        {"id": "g", "options": [{"device_ref": "cam"}]}
                    ],
                }
            ],
        }
    }
    assert checks.check_device_ref_integrity(data) == []


def test_device_ref_integrity_bad():
    data = {
        "intro": {
            "device_catalog": {"cam": {}},
            "presets": [
                {
                    "id": "p",
                    "device_groups": [
                        {"id": "g", "options": [{"device_ref": "ghost"}]}
                    ],
                }
            ],
        }
    }
    errs = checks.check_device_ref_integrity(data)
    assert len(errs) == 1
    assert "ghost" in errs[0]


# ---------------------------------------------------------------------------
# run_static_checks aggregator
# ---------------------------------------------------------------------------


def test_run_static_checks_prefixes_and_aggregates(tmp_path):
    sol = _make_solution(tmp_path / "s")
    data = {
        "intro": {
            "cover_image": "missing.png",
            "device_catalog": {"cam": {}},
            "presets": [
                {"id": "dup"},
                {
                    "id": "dup",
                    "device_groups": [
                        {"id": "g", "options": [{"device_ref": "ghost"}]}
                    ],
                },
            ],
        }
    }
    errs = checks.run_static_checks(sol, data)
    joined = "\n".join(errs)
    assert "[referenced_files]" in joined
    assert "[duplicate_ids]" in joined
    assert "[device_ref_integrity]" in joined


# ---------------------------------------------------------------------------
# check_semantics
# ---------------------------------------------------------------------------


def test_semantics_good(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/d.yaml": (
                "id: d\n"
                "docker:\n"
                "  compose_file: assets/c.yml\n"
                "nodered:\n"
                "  flow_file: assets/flow.json\n"
            ),
            "assets/c.yml": "services:\n  a: {}\n",
            "assets/flow.json": '[{"id": "n1"}]',
        },
    )
    assert checks.check_semantics(sol, {}) == []


def test_semantics_bad_compose(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/d.yaml": "id: d\ndocker:\n  compose_file: assets/c.yml\n",
            "assets/c.yml": "services: [unbalanced: {{{\n",
        },
    )
    errs = checks.check_semantics(sol, {})
    assert len(errs) == 1
    assert "compose_file" in errs[0]


def test_semantics_bad_flow_json(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/d.yaml": "id: d\nnodered:\n  flow_file: assets/flow.json\n",
            "assets/flow.json": "{not valid json,,}",
        },
    )
    errs = checks.check_semantics(sol, {})
    assert len(errs) == 1
    assert "flow_file" in errs[0]


# ---------------------------------------------------------------------------
# check_verification_claims
# ---------------------------------------------------------------------------


def _verified_solution(base: Path, *, ci_smoke: bool) -> Path:
    """Build a solution where preset ``p`` has a docker_deploy step pointing at
    ``devices/dep.yaml``. ``ci_smoke`` controls whether that device backs the
    deploy-smoke badge.
    """
    docker_block = (
        "type: docker_deploy\n"
        "id: dep\n"
        "docker:\n"
        "  compose_file: assets/c.yml\n"
    )
    if ci_smoke:
        docker_block += "  ci_smoke: true\n"
    guide = (
        "## Preset: P {#p}\n\n"
        "Intro.\n\n"
        "## Step 1: Deploy {#dep type=docker_deploy required=true "
        "config=devices/dep.yaml}\n\n"
        "Deploy it.\n"
    )
    return _make_solution(
        base,
        files={
            "guide.md": guide,
            "devices/dep.yaml": docker_block,
            "assets/c.yml": "services:\n  a: {}\n",
        },
    )


def test_verification_claims_good(tmp_path):
    """deploy-smoke claim backed by a ci_smoke device → no errors."""
    sol = _verified_solution(tmp_path / "s", ci_smoke=True)
    data = {
        "deployment": {"guide_file": "guide.md"},
        "intro": {"presets": [{"id": "p", "verified": ["deploy-smoke"]}]},
    }
    assert checks.check_verification_claims(sol, data) == []


def test_verification_claims_bad_not_backed(tmp_path):
    """deploy-smoke claimed but device has no ci_smoke → not-backed error."""
    sol = _verified_solution(tmp_path / "s", ci_smoke=False)
    data = {
        "deployment": {"guide_file": "guide.md"},
        "intro": {"presets": [{"id": "p", "verified": ["deploy-smoke"]}]},
    }
    errs = checks.check_verification_claims(sol, data)
    assert len(errs) == 1
    assert "not backed by ci_smoke" in errs[0]
    assert "preset=p" in errs[0]


def test_verification_claims_illegal_value(tmp_path):
    """A verified value outside the allowed enum → illegal-claim error."""
    sol = _make_solution(tmp_path / "s")
    data = {"intro": {"presets": [{"id": "p", "verified": ["bogus"]}]}}
    errs = checks.check_verification_claims(sol, data)
    assert len(errs) == 1
    assert "illegal verified claim" in errs[0]
    assert "bogus" in errs[0]


def test_verification_claims_hardware_not_checked(tmp_path):
    """hardware is an attestation — not machine-checkable, never errors."""
    sol = _make_solution(tmp_path / "s")
    data = {"intro": {"presets": [{"id": "p", "verified": ["hardware"]}]}}
    assert checks.check_verification_claims(sol, data) == []


# ---------------------------------------------------------------------------
# check_urls_reachable (status policy — no network: test _url_status logic via
# the public function with a monkeypatched probe)
# ---------------------------------------------------------------------------


def test_urls_4xx_is_error(tmp_path, monkeypatch):
    sol = _make_solution(tmp_path / "s")
    data = {"intro": {"cover_image": "https://example.com/dead.png"}}
    monkeypatch.setattr(checks, "_url_status", lambda url, timeout: 404)
    errs = checks.check_urls_reachable(sol, data)
    assert len(errs) == 1
    assert "404" in errs[0]


def test_urls_5xx_and_network_tolerated(tmp_path, monkeypatch):
    sol = _make_solution(tmp_path / "s")
    data = {
        "intro": {
            "cover_image": "https://example.com/server-err.png",
            "gallery": [{"src": "https://example.com/network-err.png"}],
        }
    }

    def fake_status(url, timeout):
        return 503 if "server-err" in url else None  # 5xx / network failure

    monkeypatch.setattr(checks, "_url_status", fake_status)
    assert checks.check_urls_reachable(sol, data) == []


def test_urls_2xx_ok(tmp_path, monkeypatch):
    sol = _make_solution(tmp_path / "s")
    data = {"intro": {"cover_image": "https://example.com/ok.png"}}
    monkeypatch.setattr(checks, "_url_status", lambda url, timeout: 200)
    assert checks.check_urls_reachable(sol, data) == []


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
