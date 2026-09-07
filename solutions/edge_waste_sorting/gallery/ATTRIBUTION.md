# Gallery attribution

## What is in this directory

| File | Origin | Contains dataset imagery |
|---|---|---|
| `architecture.svg` | Drawn for this solution | No |
| `waste-recamera-sg2002-20260907.jpg` | Rendered from real on-device output | Yes (GC3, CC BY 4.0) |

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

## Standing rule: no dataset-derived image is committed (superseded 2026-09-07 for the four files below)

The licences permit it; this package previously did not do it, following the
upstream repository's own convention of keeping `data/raw/`, `data/cls/`,
`data/crops/` and evaluation overlays out of version control. This section
recorded that no sample photograph, classification overlay or evaluation
screenshot existed anywhere in the solution.

That changed on 2026-09-07: four TrashNet-sourced classification-overlay
images were added to this gallery (see next section), following the escape
hatch this document already specified — "If a sample image is added later, it
may come from either dataset with the attribution string above." Only
TrashNet (MIT) images were used, filtered by the `trashnet_` filename prefix
in `data/cls/waste8/val/<class>/`, to avoid the GC3 project-URL ambiguity
noted above even though GC3's CC BY 4.0 grant is also first-party.

`assets/models/` still holds checksum manifests only, and nothing has been
uploaded to a CDN.

## 2026-09-07 real local classification demo (4 categories)

Ran the repo's real ONNX model on real TrashNet validation images — CPU-only,
no synthetic/mock data. Environment: macOS host, Apple M4 (arm64), via
`uv run --extra smoke --extra data python <script>` using the repo's own
`backends.onnxruntime.classifier.OnnxRuntimeClassifier` and
`core_waste.taxonomy` modules (not a re-implementation) against
`models/mobilenetv3s_waste8.onnx` (sha256
`51c7c0ed7258aec62f653c9b05bafaed85c837be56c331d7f7812c3a2043a28e`, the same
artefact documented in `models/MODEL-CARD.json` and `evaluation/runs/2026-09-05-m1-cpu/`).
The overlay-drawing script itself is not part of the repo (it is a one-off
gallery-generation script, not committed to `edge-waste-sorting`); the
inference path and taxonomy mapping it calls are 100% the repo's own code.

One TrashNet validation image per requested category, first image
alphabetically in each class directory, real inference, real predicted label
+ china-category + top-3 confidences drawn onto the frame:

| File | Source image (repo-relative) | Predicted class | China category | Confidence | Inference (ms) |
|---|---|---|---|---:|---:|
| `waste-paper-local-20260907.jpg` | `data/cls/waste8/val/paper/trashnet_paper102.jpg` | paper | recyclable (可回收物) | 0.9011 | 2.14 |
| `waste-metal-local-20260907.jpg` (瓶罐/bottles-cans) | `data/cls/waste8/val/metal/trashnet_metal104.jpg` | metal | recyclable (可回收物) | 0.9379 | 1.80 |
| `waste-plastic-local-20260907.jpg` | `data/cls/waste8/val/plastic/trashnet_plastic103.jpg` | plastic | recyclable (可回收物) | 0.9777 | 1.92 |
| `waste-residual-local-20260907.jpg` (其它/other) | `data/cls/waste8/val/residual/trashnet_trash108.jpg` | **plastic** (misclassified) | recyclable (可回收物) | 0.4820 | 2.09 |

`waste-grid-4up-local-20260907.jpg` is a 2×2 tile of the four images above
(`np.hstack`/`np.vstack`, no re-encoding beyond the source JPEGs), generated by
the same script.

**The residual/trash image is genuinely misclassified as plastic, not cherry-picked
to look good.** This is consistent with the model's documented CPU baseline
(`evaluation/runs/2026-09-05-m1-cpu/results.md`: material top-1 0.9113,
china-category top-1 0.9866) — `residual` (TrashNet's original `trash` label)
had only 20 val images and the model confuses it with visually similar
recyclables at low confidence. Per README §9 item 8, this is a development-machine
CPU run, not a device-side (Jetson/Hailo/RK) measurement — do not present it as
verified edge-hardware inference.

`waste-demo-results-local-20260907.json` is the script's raw structured output
(source path, predicted class, full top-3, confidence, inference_ms per image)
— the source-of-truth the table above summarizes.

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

## reCamera (SG2002) on-device results grid

`waste-recamera-sg2002-20260907.jpg` is the only figure on this page produced
by an accelerator rather than a host CPU. The four frames were classified by
the BF16 cvimodel running on a reCamera's own SG2002 TPU on 2026-09-07; the
class, the Chinese four-way category and the per-frame inference time drawn on
each tile are the values the device returned, not re-rendered estimates.

| Tile | Source image | Device prediction | Confidence | Latency |
|---|---|---|---|---|
| top-left | `gc3_cardboard1013_jpg.rf.2c73fe8c…_0.jpg` | cardboard | 0.961 | 24.28 ms |
| top-right | `gc3_glass1025_jpg.rf.ea7059c7…_0.jpg` | glass | 0.898 | 24.28 ms |
| bottom-left | `gc3_paper1005_jpg.rf.31c04abaf…_0.jpg` | paper | 0.932 | 24.20 ms |
| bottom-right | `gc3_biodegradable1004_jpg.rf.645d3199…_0.jpg` | organic | 0.946 | 24.28 ms |

All four source images come from the Roboflow "Garbage Classification 3 —
Material Identification" dataset, CC BY 4.0, and are reproduced here under that
licence with the attribution string recorded above. All four were classified
correctly; none was swapped for a better-looking result.

## Multi-item table-top frames

`waste-multi-item-a-20260907.jpg` and `waste-multi-item-b-20260907.jpg` are the
detector's own output on two multi-item frames, cropped from the 640 × 640
annotated scene of `media/multi-item-still-1.jpg` and `multi-item-still-2.jpg`
in the `edge-waste-sorting-deb` working tree (rendered 2026-09-07 by
`tools/render_multi_demo.py`; the per-frame counts and classes are logged in
`media/multi-item-manifest.json`). The crop removes the blank canvas under the
scene; nothing inside the frame was altered.

| File | Source | Items detected | Crop |
|---|---|---|---|
| `waste-multi-item-a-20260907.jpg` | `multi-item-still-1.jpg` (`synth_test_00034`) | 7 | 960 × 1050 → 640 × 640 |
| `waste-multi-item-b-20260907.jpg` | `multi-item-still-2.jpg` (`synth_test_00053`) | 7 | 960 × 1050 → 640 × 640 |

The objects in both frames are **TrashNet** (MIT, `garythung/trashnet`) items
segmented out of their original photographs and composited onto a procedurally
generated empty-table background (`data/synth_multi.py`); the background
introduces no third-party asset. TrashNet's MIT licence covers redistribution.

## waste-multi-item-pair-20260907.jpg

`waste-multi-item-a-20260907.jpg` and `waste-multi-item-b-20260907.jpg` placed
side by side at native resolution with an 8 px white gutter, 1288 × 640, no
scaling. It is the cover. The source objects are TrashNet (MIT) items on a
procedurally generated background, as recorded above.

The device grid `waste-recamera-sg2002-20260907.jpg` is 768 px wide and stays in
the gallery as the second image rather than the cover. It cannot be re-rendered
any wider without upscaling: the tiles it is built from are GC3 instance crops
of 415 × 415 and smaller (the organic crop is 125 × 66), so the grid has no
larger native form.
