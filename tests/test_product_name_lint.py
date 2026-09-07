"""Positive/negative cases for every rule in scripts/ci/lint_product_names.py."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "ci" / "lint_product_names.py"
RULES_PATH = REPO_ROOT / "scripts" / "ci" / "product-names.json"

_spec = importlib.util.spec_from_file_location("lint_product_names", SCRIPT)
lint_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
sys.modules["lint_product_names"] = lint_mod  # dataclasses needs the module entry
_spec.loader.exec_module(lint_mod)


@pytest.fixture(scope="module")
def rules() -> dict:
    return lint_mod.load_rules(RULES_PATH)


def scan(tmp_path: Path, rules: dict, relative: str, body: str) -> list:
    target = tmp_path / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return lint_mod.lint([tmp_path / "solutions"], rules, tmp_path)


def rule_ids(findings) -> set[str]:
    return {f.rule for f in findings}


def severities(findings, rule: str) -> set[str]:
    return {f.severity for f in findings if f.rule == rule}


# --------------------------------------------------------------------------
# rule 1: blacklist
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("The hub runs on a reComputer J today.", "bare-recomputer-j"),
        ("The hub runs on a reComputer R today.", "bare-recomputer-r"),
        ("Ships as reComputer R20 for the line.", "recomputer-r20-r21-bare"),
        ("Ships as reComputer R21 for the line.", "recomputer-r20-r21-bare"),
        ("A SenseCAP R1000 writes the Modbus point.", "sensecap-r1000"),
        ("Use the reComputer R (Hailo) build.", "recomputer-r-hailo"),
        ("用 reComputer R（Hailo）这一档。", "recomputer-r-hailo"),
    ],
)
def test_blacklist_hits(tmp_path, rules, body, expected):
    findings = scan(tmp_path, rules, "solutions/demo/description.md", body)
    assert expected in rule_ids(findings)
    assert severities(findings, expected) == {"error"}


@pytest.mark.parametrize(
    "body",
    [
        "The hub runs on a reComputer J40 Series box.",
        "The hub runs on a reComputer R2000 Series box.",
        "算力设备是 reComputer J30 系列。",
        "Ships as reComputer R2035-12 for the line.",
        "A reComputer R1000 Series node writes the Modbus point.",
    ],
)
def test_blacklist_clean(tmp_path, rules, body):
    findings = scan(tmp_path, rules, "solutions/demo/description.md", body)
    assert not [f for f in findings if f.severity == "error"], [
        f.render() for f in findings
    ]


# --------------------------------------------------------------------------
# rule 2: bench-only names
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("Runs on a Raspberry Pi 5 at the door.", "bench-pi5-delivery"),
        ("门口那台是树莓派 5。", "bench-pi5-delivery"),
        ("Runs on a Raspberry Pi 4 at the door.", "bench-pi4-delivery"),
        ("A Radxa board drives the display.", "bench-radxa"),
        ("A ROCK 5T board drives the display.", "bench-rock5t"),
        ("A LubanCat board drives the display.", "bench-lubancat"),
        ("Deployed to harvest-pi in the shop.", "bench-fleet-id"),
        ("Deployed to cat-remote in the shop.", "bench-fleet-id"),
    ],
)
def test_bench_names_are_errors_in_outward_text(tmp_path, rules, body, expected):
    findings = scan(tmp_path, rules, "solutions/demo/description.md", body)
    assert expected in rule_ids(findings)
    assert severities(findings, expected) == {"error"}


def test_bench_names_allowed_in_run_records(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/wiki/evaluation.md",
        "Measured on harvest-pi, a Raspberry Pi 5, 2026-09-05.",
    )
    assert not [f for f in findings if f.rule.startswith("bench-")]


def test_bench_names_allowed_behind_inline_marker(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "Radxa ROCK 5T bench board <!-- lint:bench-ok -->",
    )
    assert not [f for f in findings if f.rule.startswith("bench-")]


def test_measured_on_no_longer_whitelists_outward_text(tmp_path, rules):
    """The old "出处注释" escape is gone: same-SoC text writes the family name."""
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "| Throughput | Measured on hardware | Raspberry Pi 5, 2026-09-05 |",
    )
    assert "bench-pi5-delivery" in rule_ids(findings)


# --------------------------------------------------------------------------
# rule 3: model existence
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        "Deploy to a reComputer J4012 node.",
        "Deploy to a reComputer Industrial R2135-12 node.",
        "Deploy to a reTerminal E1003 panel.",
        "Sensors are SenseCAP S21xx nodes.",
        "Gateway is a reComputer R21xx-12 unit.",
        "Tracker is a SenseCAP T1000-E card.",
    ],
)
def test_known_models_pass(tmp_path, rules, body):
    findings = scan(tmp_path, rules, "solutions/demo/description.md", body)
    assert "unknown-model" not in rule_ids(findings)


@pytest.mark.parametrize(
    "body",
    [
        "Deploy to a reComputer J9012 node.",
        "Deploy to a reComputer R2999-12 node.",
        "Deploy to a reTerminal E1099 panel.",
    ],
)
def test_unknown_models_fail(tmp_path, rules, body):
    findings = scan(tmp_path, rules, "solutions/demo/description.md", body)
    assert "unknown-model" in rule_ids(findings)
    assert severities(findings, "unknown-model") == {"error"}


# --------------------------------------------------------------------------
# rule 4: cross-checks
# --------------------------------------------------------------------------


def test_j30_with_orin_nx_is_an_error(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "The J3011 carries a Jetson Orin NX 16GB module.",
    )
    assert "j30-orin-nx" in rule_ids(findings)
    assert severities(findings, "j30-orin-nx") == {"error"}


def test_j40_with_orin_nano_is_an_error(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "The J4012 carries a Jetson Orin Nano 8GB module.",
    )
    assert "j40-orin-nano" in rule_ids(findings)


def test_a_cell_listing_both_families_is_not_a_mismatch(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "| reComputer J30 / J40 (Orin Nano 8GB / Orin NX 16GB) | TensorRT FP16 |",
    )
    assert not {"j30-orin-nx", "j40-orin-nano"} & rule_ids(findings)


def test_cross_check_is_per_cell_not_per_row(tmp_path, rules):
    """A neighbouring cell's module name must not implicate this cell's device."""
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "| reComputer J3011 (Orin Nano 8GB) | figures taken on Orin NX 16GB |",
    )
    assert "j30-orin-nx" not in rule_ids(findings)


def test_correct_module_pairing_passes(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "| reComputer J3011 (Jetson Orin Nano 8GB) | 14 FPS |\n"
        "| reComputer J4012 (Jetson Orin NX 16GB) | 15 FPS |\n",
    )
    assert not {"j30-orin-nx", "j40-orin-nano"} & rule_ids(findings)


def test_hailo_with_non_hailo_sku_warns(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "Pose runs on the Hailo-8 in an R2135-10.",
    )
    assert "hailo-non-hailo-sku" in rule_ids(findings)
    assert severities(findings, "hailo-non-hailo-sku") == {"warn"}


# --------------------------------------------------------------------------
# rule 5: prefer the family name in prose
# --------------------------------------------------------------------------


def test_sku_in_prose_warns(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "Recognition runs on the R2135-12 at the door.",
    )
    assert "prefer-family-name" in rule_ids(findings)
    assert severities(findings, "prefer-family-name") == {"warn"}


def test_sku_in_a_table_row_is_fine(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "| Compute | reComputer R2135-12 | 1 |",
    )
    assert "prefer-family-name" not in rule_ids(findings)


def test_family_name_in_prose_is_fine(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "Recognition runs on the reComputer R2000 Series at the door.",
    )
    assert not findings, [f.render() for f in findings]


def test_sku_in_a_bom_entry_is_fine(tmp_path, rules):
    solution = {
        "intro": {
            "bom": [{"name": "reComputer R2135-12 (Hailo-8)", "qty": 1}],
            "device_catalog": {},
            "presets": [],
        }
    }
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/solution.yaml",
        yaml.safe_dump(solution, allow_unicode=True),
    )
    assert "prefer-family-name" not in rule_ids(findings)


# --------------------------------------------------------------------------
# rule 6: preset text vs device_ref family
# --------------------------------------------------------------------------


def _solution(preset_name: str, ref: str) -> str:
    return yaml.safe_dump(
        {
            "intro": {
                "device_catalog": {ref: {"purchase": {}}},
                "presets": [
                    {
                        "id": "p1",
                        "name": preset_name,
                        "device_groups": [{"id": "g1", "device_ref": ref}],
                    }
                ],
            }
        },
        allow_unicode=True,
    )


def test_preset_text_naming_another_family_fails(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/solution.yaml",
        _solution("IP Camera + reComputer J30 Series", "recomputer_j40"),
    )
    assert "preset-family-mismatch" in rule_ids(findings)
    assert severities(findings, "preset-family-mismatch") == {"error"}


def test_preset_text_matching_its_device_ref_passes(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/solution.yaml",
        _solution("IP Camera + reComputer J40 Series", "recomputer_j40"),
    )
    assert "preset-family-mismatch" not in rule_ids(findings)


def test_preset_naming_a_sku_of_its_own_family_passes(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/solution.yaml",
        _solution("IP Camera + reComputer J4012", "recomputer_j40"),
    )
    assert "preset-family-mismatch" not in rule_ids(findings)


# --------------------------------------------------------------------------
# rule data
# --------------------------------------------------------------------------


def test_every_family_in_family_models_exists_in_the_manifest(rules):
    manifest = json.loads(
        (REPO_ROOT / "spec" / "product-family-manifest.json").read_text("utf-8")
    )
    known = set(manifest["families"])
    for family in rules["family_models"]:
        assert family in known, family
    for family in rules["family_aliases"]:
        assert family in known, family


def test_rule_patterns_compile(rules):
    import re

    for group in ("blacklist", "bench_only_names"):
        for rule in rules[group]:
            re.compile(rule["pattern"])
    for rule in rules["cross_checks"]:
        re.compile(rule["left"])
        re.compile(rule["right"])


def test_sync_note_points_at_the_hub_copy(rules):
    assert "seeed-solutions-hub" in " ".join(rules["sync"]["copies"])
    assert rules["prefer_family"] is True
    assert rules["soc_family_map"]["Raspberry Pi 5"].startswith("reComputer R2000")


# --------------------------------------------------------------------------
# scanner robustness
# --------------------------------------------------------------------------


def test_fenced_code_is_skipped(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "intro\n```bash\necho reComputer R\n```\noutro\n",
    )
    assert not findings


def test_an_unclosed_fence_does_not_swallow_the_rest_of_the_file(tmp_path, rules):
    """An odd fence count is malformed markdown; over-report rather than skip."""
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "```bash\necho hi\nand then: reComputer R\n",
    )
    assert "bare-recomputer-r" in rule_ids(findings)


def test_a_null_device_catalog_entry_does_not_crash(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/solution.yaml",
        "intro:\n"
        "  device_catalog:\n"
        "    recomputer_j40:\n"
        "  presets:\n"
        "    - id: p1\n"
        "      name: reComputer J30 Series\n"
        "      device_groups:\n"
        "        - {id: g1, device_ref: recomputer_j40}\n",
    )
    assert "preset-family-mismatch" in rule_ids(findings)


def test_unparseable_yaml_is_skipped_rather_than_raised(tmp_path, rules):
    assert (
        scan(tmp_path, rules, "solutions/demo/solution.yaml", "intro: [unclosed\n")
        == []
    )


# --------------------------------------------------------------------------
# boundaries: CJK neighbours, link targets, over-long suffixes
# --------------------------------------------------------------------------


def test_a_markdown_link_keeps_its_visible_product_name(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/description.md",
        "See [reComputer J](https://example.com/doc.md) for the host.",
    )
    assert "bare-recomputer-j" in rule_ids(findings)


def test_a_brand_pressed_against_chinese_text_is_still_found(tmp_path, rules):
    """`re` counts CJK as word characters, so \\b never fires between 用 and r."""
    findings = scan(
        tmp_path, rules, "solutions/demo/description.md", "采用reComputer J9012 做主机"
    )
    assert "unknown-model" in rule_ids(findings)


def test_a_module_name_after_the_brand_is_not_read_as_a_model(tmp_path, rules):
    findings = scan(
        tmp_path, rules, "solutions/demo/description.md", "reComputer Orin NX 16GB"
    )
    assert "unknown-model" not in rule_ids(findings)


def test_an_over_long_suffix_is_not_truncated_to_a_legal_prefix(tmp_path, rules):
    findings = scan(
        tmp_path, rules, "solutions/demo/description.md", "reComputer RK3576-9999"
    )
    assert "unknown-model" in rule_ids(findings)


def test_hailo_warns_on_every_no_accelerator_suffix(tmp_path, rules):
    findings = scan(
        tmp_path, rules, "solutions/demo/description.md", "Hailo-8 搭 R2045-10"
    )
    assert "hailo-non-hailo-sku" in rule_ids(findings)


def test_a_bare_series_number_still_triggers_the_cross_check(tmp_path, rules):
    findings = scan(
        tmp_path, rules, "solutions/demo/description.md", "J3011 装的是 Orin NX 16GB"
    )
    assert "j30-orin-nx" in rule_ids(findings)


def test_the_solution_name_and_summary_are_scanned(tmp_path, rules):
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/solution.yaml",
        "name: Fall detection on reComputer J\n"
        "intro:\n"
        "  summary: Runs on a Raspberry Pi 5 at the bedside.\n"
        "  device_catalog: {}\n"
        "  presets: []\n",
    )
    assert {"bare-recomputer-j", "bench-pi5-delivery"} <= rule_ids(findings)


def test_a_device_refs_family_id_wins_over_its_catalog_key(tmp_path, rules):
    """A key named after one family pointing at another must not launder it."""
    findings = scan(
        tmp_path,
        rules,
        "solutions/demo/solution.yaml",
        "intro:\n"
        "  device_catalog:\n"
        "    recomputer_j30:\n"
        "      family_id: recomputer_j40\n"
        "  presets:\n"
        "    - id: p1\n"
        "      name: IP Camera + reComputer J30 Series\n"
        "      device_groups:\n"
        "        - {id: g1, device_ref: recomputer_j30}\n",
    )
    assert "preset-family-mismatch" in rule_ids(findings)
