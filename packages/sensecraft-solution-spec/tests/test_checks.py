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


def test_referenced_device_assets_nested_manifest(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/apps/app.yaml": (
                "id: app\n"
                "docker:\n"
                "  compose_file: assets/missing.yml\n"
            ),
        },
    )
    errs = checks.check_referenced_device_assets(sol, {})
    assert len(errs) == 1
    assert "devices/apps/app.yaml:docker.compose_file" in errs[0]
    assert "assets/missing.yml" in errs[0]


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


def test_urls_gated_4xx_tolerated(tmp_path, monkeypatch):
    """401/403/408/429 = exists-but-gated (CF bot-block, auth, rate-limit) — not dead.

    e.g. files.seeedstudio.com images render fine but 403 a stdlib client;
    flagging them would be a false positive on a good CDN.
    """
    for code in (401, 403, 408, 429):
        sol = _make_solution(tmp_path / f"s{code}")
        data = {"intro": {"cover_image": "https://files.seeedstudio.com/x.png"}}
        monkeypatch.setattr(checks, "_url_status", lambda url, timeout, c=code: c)
        assert checks.check_urls_reachable(sol, data) == [], f"{code} should be tolerated"


# ---------------------------------------------------------------------------
# check_no_local_gifs
# ---------------------------------------------------------------------------


def test_no_local_gifs_good(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "gallery/cover.webp": "fake webp",
            "guide.md": "![demo](https://files.seeedstudio.com/demo.gif)",
        },
    )
    data = {
        "intro": {
            "cover_image": "gallery/cover.webp",
            "gallery": [
                {"src": "https://files.seeedstudio.com/live-demo.gif"},
                {"src": "gallery/demo.webp"},
            ],
        }
    }
    assert checks.check_no_local_gifs(sol, data) == []


def test_no_local_gifs_bad_disk(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={"gallery/animation.gif": "fake gif"},
    )
    data = {"intro": {"cover_image": "gallery/cover.png"}}
    errs = checks.check_no_local_gifs(sol, data)
    assert len(errs) == 1
    assert "local .gif file found: gallery/animation.gif" in errs[0]


def test_no_local_gifs_bad_yaml(tmp_path):
    sol = _make_solution(tmp_path / "s")
    data = {
        "intro": {
            "cover_image": "gallery/cover.gif",
            "gallery": [{"src": "gallery/demo.gif"}],
            "presets": [{"architecture_image": "arch.gif"}],
            "device_catalog": {"d1": {"image": "device.gif"}},
        }
    }
    errs = checks.check_no_local_gifs(sol, data)
    assert any("cover_image references local .gif" in e for e in errs)
    assert any("gallery[0].src references local .gif" in e for e in errs)
    assert any("presets[0].architecture_image references local .gif" in e for e in errs)
    assert any("device_catalog.d1.image references local .gif" in e for e in errs)


def test_no_local_gifs_bad_markdown(tmp_path):
    sol = _make_solution(
        tmp_path / "s",
        files={"guide.md": "See demo:\n\n![Demo](gallery/local-preview.gif)\n"},
    )
    data = {"intro": {}}
    errs = checks.check_no_local_gifs(sol, data)
    assert any("markdown image references local .gif: guide.md -> gallery/local-preview.gif" in e for e in errs)


# ---------------------------------------------------------------------------
# check_recamera_deb_packages
# ---------------------------------------------------------------------------


def _make_ar_entry(name: str, content: bytes) -> bytes:
    # 60-byte ar member header:
    # name (16), mtime (12), uid (6), gid (6), mode (8), size (10), trailer (2)
    header = (
        name.ljust(16).encode("ascii")
        + b"0".ljust(12)
        + b"0".ljust(6)
        + b"0".ljust(6)
        + b"100644".ljust(8)
        + str(len(content)).encode("ascii").ljust(10)
        + b"`\n"
    )
    padding = b"\n" if len(content) % 2 == 1 else b""
    return header + content + padding


def _craft_deb(*, compression: str = "gz") -> bytes:
    """Craft a minimal in-memory deb archive with ar header."""
    archive = b"!<arch>\n"
    archive += _make_ar_entry("debian-binary", b"2.0\n")
    archive += _make_ar_entry(f"control.tar.{compression}", b"dummy control")
    archive += _make_ar_entry(f"data.tar.{compression}", b"dummy data")
    return archive


def test_recamera_deb_format_good(tmp_path):
    deb_bytes = _craft_deb(compression="gz")
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/recamera.yaml": (
                "id: recamera\n"
                "type: recamera_cpp\n"
                "binary:\n"
                "  deb_package:\n"
                "    path: packages/app.deb\n"
            ),
            "packages/app.deb": "placeholder",
        },
    )
    (sol / "packages/app.deb").write_bytes(deb_bytes)
    assert checks.check_recamera_deb_packages(sol, {}) == []

    static_errs = checks.run_static_checks(sol, {})
    assert not any("[recamera_deb_format]" in e for e in static_errs)


def test_recamera_deb_format_zst_rejected(tmp_path):
    deb_bytes = _craft_deb(compression="zst")
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/recamera.yaml": (
                "id: recamera\n"
                "type: recamera_cpp\n"
                "binary:\n"
                "  deb_package:\n"
                "    path: packages/app.deb\n"
            ),
            "packages/app.deb": "placeholder",
        },
    )
    (sol / "packages/app.deb").write_bytes(deb_bytes)
    errs = checks.check_recamera_deb_packages(sol, {})
    assert len(errs) == 1
    assert (
        "incompatible deb package: reCamera does not support zstd compression: "
        "devices/recamera.yaml:binary.deb_package -> control.tar.zst. "
        "Use 'dpkg-deb -Zgzip -b' to package with gzip."
    ) in errs[0]

    static_errs = checks.run_static_checks(sol, {})
    assert any(
        "[recamera_deb_format] incompatible deb package: reCamera does not support zstd compression:"
        in e
        for e in static_errs
    )


def test_recamera_deb_format_non_recamera_ignored(tmp_path):
    zst_deb = _craft_deb(compression="zst")
    # 1. Non-recamera device referencing a zstd deb (e.g. docker_deploy / jetson)
    sol = _make_solution(
        tmp_path / "s1",
        files={
            "devices/jetson.yaml": (
                "id: jetson\n"
                "type: docker_deploy\n"
                "target_platform: jetson_orin\n"
                "files:\n"
                "  - path: packages/app.deb\n"
            ),
            "packages/app.deb": "placeholder",
        },
    )
    (sol / "packages/app.deb").write_bytes(zst_deb)
    assert checks.check_recamera_deb_packages(sol, {}) == []

    # 2. Recamera device referencing a non-deb file
    sol2 = _make_solution(
        tmp_path / "s2",
        files={
            "devices/recamera.yaml": (
                "id: recamera\n"
                "type: recamera_cpp\n"
                "binary:\n"
                "  deb_package:\n"
                "    path: packages/model.bin\n"
            ),
            "packages/model.bin": "binary content",
        },
    )
    assert checks.check_recamera_deb_packages(sol2, {}) == []


def test_urls_remote_recamera_deb_zst_rejected(tmp_path, monkeypatch):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/recamera.yaml": (
                "id: recamera\n"
                "type: recamera_cpp\n"
                "binary:\n"
                "  deb_package:\n"
                "    path: https://example.com/app.deb\n"
            ),
        },
    )
    monkeypatch.setattr(checks, "_url_status", lambda url, timeout: 200)
    monkeypatch.setattr(checks, "_check_remote_deb_zstd", lambda url, timeout: True)
    errs = checks.check_urls_reachable(sol, {})
    assert len(errs) == 1
    assert (
        "incompatible remote deb package: reCamera does not support zstd compression: "
        "devices/recamera.yaml:binary.deb_package.path -> https://example.com/app.deb. "
        "Use 'dpkg-deb -Zgzip -b' to package with gzip."
    ) in errs[0]


def test_urls_remote_recamera_deb_gz_ok(tmp_path, monkeypatch):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/recamera.yaml": (
                "id: recamera\n"
                "type: recamera_cpp\n"
                "binary:\n"
                "  deb_package:\n"
                "    path: https://example.com/app.deb\n"
            ),
        },
    )
    monkeypatch.setattr(checks, "_url_status", lambda url, timeout: 200)
    monkeypatch.setattr(checks, "_check_remote_deb_zstd", lambda url, timeout: False)
    assert checks.check_urls_reachable(sol, {}) == []


def test_urls_remote_non_recamera_deb_ignored(tmp_path, monkeypatch):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/jetson.yaml": (
                "id: jetson\n"
                "type: docker_deploy\n"
                "files:\n"
                "  - file: https://example.com/app.deb\n"
            ),
        },
    )
    monkeypatch.setattr(checks, "_url_status", lambda url, timeout: 200)
    monkeypatch.setattr(checks, "_check_remote_deb_zstd", lambda url, timeout: True)
    assert checks.check_urls_reachable(sol, {}) == []


def test_recamera_deb_format_nested_manifest_zst_rejected(tmp_path):
    deb_bytes = _craft_deb(compression="zst")
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/apps/recamera_app.yaml": (
                "id: recamera_app\n"
                "type: recamera_cpp\n"
                "binary:\n"
                "  deb_package:\n"
                "    path: packages/app.deb\n"
            ),
            "packages/app.deb": "placeholder",
        },
    )
    (sol / "packages/app.deb").write_bytes(deb_bytes)
    errs = checks.check_recamera_deb_packages(sol, {})
    assert len(errs) == 1
    assert (
        "incompatible deb package: reCamera does not support zstd compression: "
        "devices/apps/recamera_app.yaml:binary.deb_package -> control.tar.zst. "
        "Use 'dpkg-deb -Zgzip -b' to package with gzip."
    ) in errs[0]


def test_urls_remote_recamera_deb_nested_manifest_zst_rejected(tmp_path, monkeypatch):
    sol = _make_solution(
        tmp_path / "s",
        files={
            "devices/apps/recamera_app.yaml": (
                "id: recamera_app\n"
                "type: recamera_cpp\n"
                "binary:\n"
                "  deb_package:\n"
                "    path: https://example.com/app.deb\n"
            ),
        },
    )
    collected = checks._collect_urls(sol, {})
    assert (
        "devices/apps/recamera_app.yaml:binary.deb_package.path",
        "https://example.com/app.deb",
    ) in collected

    monkeypatch.setattr(checks, "_url_status", lambda url, timeout: 200)
    monkeypatch.setattr(checks, "_check_remote_deb_zstd", lambda url, timeout: True)
    errs = checks.check_urls_reachable(sol, {})
    assert len(errs) == 1
    assert (
        "incompatible remote deb package: reCamera does not support zstd compression: "
        "devices/apps/recamera_app.yaml:binary.deb_package.path -> https://example.com/app.deb. "
        "Use 'dpkg-deb -Zgzip -b' to package with gzip."
    ) in errs[0]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
