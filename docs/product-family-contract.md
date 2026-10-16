# Product family contract

Solution content selects a stable product **family**, not a concrete SKU.
Contributors do not need Typesense access: the reviewable snapshot at
[`spec/product-family-manifest.json`](../spec/product-family-manifest.json)
contains every known `family_id`, its localized family title, selectable axes,
and the SKU attribute combinations needed for offline validation.

## Authoring quickstart

Search the snapshot by family id, English title, or Chinese title:

```bash
jq --arg q 'J40' '
  ($q | ascii_downcase) as $needle
  | .families | to_entries[]
  | select(
      ([.key, .value.title.en // "", .value.title["zh-hans"] // ""]
       | join(" ") | ascii_downcase | contains($needle))
    )
  | {family_id: .key, title: .value.title}
' spec/product-family-manifest.json
```

Inspect one family's selectable axes and allowed values:

```bash
jq --arg id 'recomputer_j40' \
  '.families[$id] | {title, axes}' \
  spec/product-family-manifest.json
```

Use the selected `family_id` directly as all three identifiers. There is no
second mapping key:

- the `intro.device_catalog` key;
- every matching `device_ref`;
- the device group's `default` value.

Put capability requirements in `purchase.require`, using axis ids and values
from the snapshot. For a product-backed catalog entry, `purchase` may contain
only `require`; SKU, URL, image, name, or any other product metadata comes from
`purchase_profile`. For example, this means “any J40-family product with at
least 16 GB”, not one particular J4012 product:

```yaml
intro:
  device_catalog:
    recomputer_j40:
      description: Runs the local AI service
      purchase:
        require:
          module: [orin_nx_16]
  presets:
    - id: local_ai
      device_groups:
        - id: server
          type: single
          required: true
          options:
            - device_ref: recomputer_j40
          default: recomputer_j40
```

Enum axes accept one value or a list. Number axes also accept ranges such as
`"8.."`, `"..16"`, or `"8..16"`.

Use a `generic_` or `external_` key only for hardware that genuinely has no
`purchase_profile` family in the snapshot. Do not invent a key from a product
name just because the contributor cannot access Typesense.

## Validate before submitting

Run the offline product-family validator from the repository root:

```bash
uv run python scripts/ci/validate_product_families.py
```

CI rejects:

- unknown family ids;
- duplicated product data in Solution YAML (`family_id`, SKU, product name,
  image, or purchase URL), including any `purchase` key other than `require`;
- `purchase.require` axes or values that the family does not declare;
- a complete requirement that matches no SKU attribute combination;
- broken `device_ref` / default references.

Concrete SKU names, product images, and purchase URLs never belong in the
Solution repository. The App resolves them at runtime from the Typesense
`purchase_profile` collection. The snapshot is used only for authoring and
offline CI; it is not a runtime product database.

## Refreshing the snapshot

The purchase-profile owner refreshes the snapshot after `solution_bot`
regenerates `data/purchase_profiles`. From this repository run:

```bash
uv run python scripts/update_product_family_manifest.py \
  --profiles-dir /path/to/solution_bot/data/purchase_profiles \
  --output spec/product-family-manifest.json
uv run python scripts/ci/validate_product_families.py
git diff -- spec/product-family-manifest.json
```

The generated file has no timestamp and must be deterministic. Review the diff,
confirm the family count and titles, then submit the snapshot change together
with any Solution content that needs the new family. Contributors should not
hand-edit the generated manifest or copy concrete SKU/image/URL data into it.
