# Gallery attribution

## What is in this directory

| File | Origin | Contains dataset imagery |
|---|---|---|
| `architecture.svg` | Drawn for this solution | No |

`architecture.svg` is the data path only — trigger, camera, the debounce,
classify and four-way lookup stages, and the outputs with their ports. Boxes,
arrows, product names, protocol names and port numbers; no photograph, no
classifier output, nothing traceable to either dataset. It is near-wordless on
purpose so one asset serves both the English and the Chinese page.

## Dataset licences — cleared, with one correction

Unlike the sibling surface-inspection package, this solution's training data
carries licences that permit redistribution and derivative works. Figures and
models derived from it may be used externally, with attribution.

**TrashNet — MIT License, Copyright (c) 2017 Gary Thung.** Verified against two
first-party sources: the repository's own `LICENSE` file at commit `6fa2b87`,
and the `license` field of the official HuggingFace dataset card
(`garythung/trashnet`), which returns `{"license": "mit"}`. Full text is kept
upstream at `data/licenses/MIT-trashnet.txt`.

**Correction on record:** the upstream project's own `docs/SPEC.md` §2 and its
survey report both record TrashNet as CC BY 4.0. That is wrong. No first-party
source states CC BY 4.0. MIT is more permissive — it requires the copyright and
licence notice to be retained but imposes no share-alike term — so attribution
practices written for CC BY 4.0 remain compliant. What is not permissible is
describing TrashNet as CC BY 4.0 in outward-facing material.

**Garbage Classification 3 — Material Identification (Roboflow Universe) —
CC BY 4.0**, stated verbatim in the export package's own `README.dataset.txt`:

```
# GARBAGE CLASSIFICATION 3 > GC1
https://universe.roboflow.com/object-detection/garbage-classification-3

Provided by Roboflow
License: CC BY 4.0
```

Full text is kept upstream at `data/licenses/CC-BY-4.0.txt` (the Creative
Commons official legalcode). The project URL printed inside that README points
at a different Roboflow workspace from the one actually downloaded
(`material-identification/garbage-classification-3`) — a copied or migrated
project whose README metadata was not updated. It does not affect the licence
determination: the CC BY 4.0 grant is first-party, inside the export package.

## Attribution string

Use this verbatim in outward-facing material:

```
TrashNet — Gary Thung and Mindy Yang, https://github.com/garythung/trashnet,
MIT License, Copyright (c) 2017 Gary Thung.
Garbage Classification 3 — Material Identification / Roboflow Universe,
https://universe.roboflow.com/material-identification/garbage-classification-3,
licensed CC BY 4.0.
```

## Standing rule: no dataset-derived image is committed

The licences permit it; this package does not do it. The upstream repository
keeps every dataset-derived image out of version control — `data/raw/`,
`data/cls/`, `data/crops/` and the evaluation overlays are all gitignored, and
only the numerical reports and the split statistics are committed — and this
package follows the same rule. No sample photograph, no classification overlay
and no evaluation screenshot is in this directory or anywhere else in the
solution.

The rule covers the whole package: `assets/models/` holds checksum manifests
only, and nothing has been uploaded to a CDN.

If a sample image is added later, it may come from either dataset with the
attribution string above. Add it in the same change that records where it came
from.

## Third-party model licences

| Artefact | Licence |
|---|---|
| Upstream project code | Apache-2.0 |
| `google/siglip2-base-patch16-224`, revision `75de2d55ec2d0b4efc50b3e9ad70dba96a7b2fa2` | Apache-2.0 (recorded upstream in `tracks/open_vocab/PROVENANCE.md`) |
| MobileNetV3-Small ImageNet starting weights (torchvision) | BSD-3-Clause, per torchvision |

## CDN

**Nothing has been uploaded.** The packaging convention is CDN-hosted images
under `https://files.seeedstudio.com/Solution/landpage_asset/<id>/<name>-<hash>.png`,
and `solution.yaml` does not use it yet — `architecture.svg` is referenced by
its local path. Uploading is a separate step and is safe for this file, since it
carries no dataset content; it has simply not been done.

When the gallery is published, upload `architecture.svg` and switch
`intro.cover_image` and `intro.gallery[].src` to the CDN URLs in one change.

## Model artefacts

`assets/models/` carries checksums only — `SHA256SUMS` (baseline),
`SHA256SUMS.open_vocab`, and `SHA256SUMS.hef` which is deliberately empty
because no HEF exists. No weights, ONNX, engine or HEF is in this repository,
and none has been uploaded to
`https://sensecraft-statics.seeed.cc/solution-app/edge_waste_sorting/models/`
either. The download steps in `devices/` name that path and verify the
checksums, and each carries a `TODO(CDN)` comment saying the file is not there
yet and must be placed on the device by hand in the meantime.

Neither container image has been pushed to
`sensecraft-missionpack.seeed.cn/solution/edge-waste-sorting-{jetson,hailo}`;
both compose files say so at the top and name the local-build fallback.
