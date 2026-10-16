from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
MANIFEST_SCRIPT = REPO_ROOT / "scripts" / "update_product_family_manifest.py"
MANIFEST_SPEC = importlib.util.spec_from_file_location(
    "update_product_family_manifest", MANIFEST_SCRIPT
)
assert MANIFEST_SPEC and MANIFEST_SPEC.loader
MANIFEST_MODULE = importlib.util.module_from_spec(MANIFEST_SPEC)
MANIFEST_SPEC.loader.exec_module(MANIFEST_MODULE)
build_manifest = MANIFEST_MODULE.build_manifest

VALIDATOR_SCRIPT = REPO_ROOT / "scripts" / "ci" / "validate_product_families.py"
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_product_families", VALIDATOR_SCRIPT
)
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
VALIDATOR_MODULE = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(VALIDATOR_MODULE)
validate_solution = VALIDATOR_MODULE.validate_solution


def _write_profile(directory: Path, filename: str, data: object) -> None:
    (directory / filename).write_text(
        json.dumps(data, ensure_ascii=False), encoding="utf-8"
    )


def _profile(family_id: str, *, title: object) -> dict:
    return {
        "id": family_id,
        "title": title,
        "axes": [
            {
                "id": "memory",
                "type": "number",
                "values": [{"value": 8}, {"value": 16}],
            }
        ],
        "skus": [
            {"sku": "not-copied", "attrs": {"memory": 16}},
            {"sku": "also-not-copied", "attrs": {"memory": 8}},
        ],
    }


def test_copies_localized_family_title_without_product_fields(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "family.json",
        _profile(
            "recomputer_example",
            title={"en": "Example Family", "zh-hans": "示例产品族"},
        ),
    )

    family = build_manifest(tmp_path)["families"]["recomputer_example"]

    assert family["title"] == {
        "en": "Example Family",
        "zh-hans": "示例产品族",
    }
    assert family["axes"]["memory"]["values"] == [8, 16]
    assert family["sku_attrs"] == [{"memory": 16}, {"memory": 8}]
    assert not {"sku", "name", "image", "url"}.intersection(family)


@pytest.mark.parametrize("invalid_title", [None, "Example Family", [], 42])
def test_malformed_title_explicitly_falls_back_to_empty_object(
    tmp_path: Path, invalid_title: object
) -> None:
    _write_profile(
        tmp_path,
        "family.json",
        _profile("recomputer_example", title=invalid_title),
    )

    assert build_manifest(tmp_path)["families"]["recomputer_example"]["title"] == {}


def test_title_drops_non_string_and_empty_locale_value_pairs(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "family.json",
        _profile(
            "recomputer_example",
            title={
                " en ": " Example Family ",
                "zh-hans": "   ",
                "": "No locale",
                "ja": 123,
            },
        ),
    )

    assert build_manifest(tmp_path)["families"]["recomputer_example"]["title"] == {
        "en": "Example Family"
    }
    assert MANIFEST_MODULE._localized_title({7: "No string locale"}) == {}


def test_bad_json_and_profiles_without_ids_are_skipped(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    _write_profile(tmp_path, "report.json", {"title": {"en": "Report"}})
    _write_profile(
        tmp_path,
        "valid.json",
        _profile("valid_family", title={"en": "Valid family"}),
    )

    manifest = build_manifest(tmp_path)

    assert manifest["family_count"] == 1
    assert list(manifest["families"]) == ["valid_family"]


def test_duplicate_family_id_is_an_explicit_error(tmp_path: Path) -> None:
    _write_profile(tmp_path, "a.json", _profile("same_id", title={"en": "First"}))
    _write_profile(tmp_path, "b.json", _profile("same_id", title={"en": "Second"}))

    with pytest.raises(
        ValueError, match=r"duplicate product family id 'same_id'.*a.json.*b.json"
    ):
        build_manifest(tmp_path)


def test_family_output_is_sorted_and_deterministic(tmp_path: Path) -> None:
    _write_profile(tmp_path, "first-file.json", _profile("z_family", title={"en": "Z"}))
    _write_profile(tmp_path, "second-file.json", _profile("a_family", title={"en": "A"}))

    first = build_manifest(tmp_path)
    second = build_manifest(tmp_path)

    assert list(first["families"]) == ["a_family", "z_family"]
    assert json.dumps(first, ensure_ascii=False, sort_keys=True) == json.dumps(
        second, ensure_ascii=False, sort_keys=True
    )


def _families_for_validator() -> dict:
    return {
        "recomputer_example": {
            "axes": {
                "module": {
                    "type": "enum",
                    "values": ["orin_nx_8", "orin_nx_16"],
                }
            },
            "sku_attrs": [
                {"module": "orin_nx_8"},
                {"module": "orin_nx_16"},
            ],
        }
    }


def _write_solution_with_purchase(tmp_path: Path, purchase: dict) -> Path:
    path = tmp_path / "solution.yaml"
    path.write_text(
        json.dumps(
            {
                "intro": {
                    "device_catalog": {
                        "recomputer_example": {"purchase": purchase}
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_product_family_validator_accepts_only_legal_require(tmp_path: Path) -> None:
    path = _write_solution_with_purchase(
        tmp_path, {"require": {"module": ["orin_nx_16"]}}
    )

    assert validate_solution(path, _families_for_validator()) == []


@pytest.mark.parametrize("field", ["product_url", "unexpected_metadata"])
def test_product_family_validator_rejects_unknown_purchase_fields(
    tmp_path: Path, field: str
) -> None:
    path = _write_solution_with_purchase(
        tmp_path,
        {
            "require": {"module": ["orin_nx_16"]},
            field: "must-come-from-purchase-profile",
        },
    )

    errors = validate_solution(path, _families_for_validator())

    assert len(errors) == 1
    assert "purchase only supports 'require'" in errors[0]
    assert field in errors[0]
