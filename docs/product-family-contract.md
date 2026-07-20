# Product family contract

Product-backed entries in `intro.device_catalog` use the Typesense
`purchase_profile.family_id` directly as their key. `device_ref` and preset
defaults use the same value; there is no second mapping key.

```yaml
device_catalog:
  recomputer_j40:
    description: Runs the local AI service
    purchase:
      require:
        module: [orin_nx_16]
```

Product names, images, purchase URLs, and concrete SKUs belong to
`purchase_profile`, not Solution YAML. Hardware without a purchase profile uses
an explicit `generic_` or `external_` key.

`purchase.require` uses purchase-profile axis ids. Enum axes accept one value or
a list; number axes also accept ranges such as `"8.."`, `"..16"`, or
`"8..16"`. CI verifies that each axis/value exists and that at least one SKU in
the family satisfies the complete requirement.

## Offline manifest

[`spec/product-family-manifest.json`](../spec/product-family-manifest.json) is a
generated, reviewable snapshot of family ids, axes, and SKU attribute
combinations. It lets contributors and CI validate content without Typesense
credentials.

Refresh it after `solution_bot` regenerates purchase profiles:

```bash
python3 scripts/update_product_family_manifest.py \
  --profiles-dir /path/to/solution_bot/data/purchase_profiles
```

Run the same validation used by CI:

```bash
uv run python scripts/ci/validate_product_families.py
```
