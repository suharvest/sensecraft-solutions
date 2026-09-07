# Gallery attribution

## Standing rule: exactly two dataset-derived frames, and only to show function

**Two detection frames are published here and no more** —
`defect-overlay-inclusion.jpg` and `defect-overlay-pitted.jpg`, described at the
bottom of this file. They exist so a reader can see what the solution does. No
further image derived from the training or validation data is committed in this
directory or anywhere else in the solution: no evaluation screenshot, no sample
frame, no dataset excerpt. The underlying photographs carry non-commercial
terms (see "The licence problem" below) and are not redistributed as data.

Until 2026-09-07 the rule here was zero such images. It was relaxed to two on
that date, deliberately and with the scope written down, because a page that
shows only a product photograph does not tell anyone what it is for.

The rest of the package is unchanged: `assets/models/` holds manifests and
checksums only, and nothing has been uploaded to a CDN.

## What is in this directory

| File | Origin | Contains dataset imagery |
|---|---|---|
| `defect-overlay-inclusion.jpg` | `evaluation/runs/2026-09-05-m1-smoke/overlay_inclusion_110_jpg.rf.14d4ab42696fedc3d48775e0cce5fd57.jpg` | Yes — one NEU-DET frame, published to show function |
| `defect-overlay-pitted.jpg` | `evaluation/runs/2026-09-05-m1-smoke/overlay_pitted_surface_100_jpg.rf.50a2cc31fe13105a21b22f930e481d7f.jpg` | Yes — one NEU-DET frame, published to show function |
| `recomputer-super-j4012.jpg` | Official Seeed Studio product photo, reComputer Super J4012 (SKU 114110314), fetched from `https://media-cdn.seeedstudio.com/media/catalog/product/cache/961a49e1875f8c1f40e5990d74e68365/s/u/suprt_j4012.jpg` (product page: https://www.seeedstudio.com/reComputer-Super-J4012-p-6443.html) | No |
| `architecture.svg` | Drawn for this solution | No |

`recomputer-super-j4012.jpg` is the third gallery entry. It is the official
product photo of the reComputer Super J4012 this solution's numbers were
measured on. It carries no dataset content. It was the cover until 2026-09-07,
when the two detection frames took over the front of the gallery.

`architecture.svg` is the data path only — camera, edge device, the OK/NG step,
and the three outputs with their ports. Boxes, arrows, product names, protocol
names and port numbers; no photograph, no detector output, nothing traceable to
the dataset. It is near-wordless on purpose so one asset serves both the English
and the Chinese page.

## The licence problem

The model is trained on **NEU-DET** (NEU surface defect database) by way of a
re-hosted copy on Roboflow. That Roboflow page states CC BY 4.0. **No formal
licence statement has been found for the original NEU-DET release**, so the
chain of permission from the original authors to that page is not established,
and CC BY 4.0 on a re-host is a claim by the re-hoster rather than a grant
traceable to the copyright holder.

Everything derived from that data is restricted the same way: the trained
checkpoint, the ONNX, both HEFs, any TensorRT engine built from them, and every
evaluation overlay. The same notice appears in `solution.yaml`, both description
files, both guides and both compose files.

## What has to happen before a sample image can be added

One of:

1. An explicit licence answer for the original NEU-DET release that permits
   redistribution and derivative works, recorded in the upstream repo's
   `data/DATASET.md` alongside the Roboflow id, version, download date and URL.
2. Retraining on a dataset whose terms are clear — the upstream survey ranks
   AITEX (CC BY 4.0) above the NEU derivatives for exactly this reason — and
   regenerating the overlays from that model.

Either way, the overlay to add would come from
`evaluation/runs/<date>-m1-smoke/` in the upstream repo, which produces the
detector's boxes, class names and scores drawn on a validation image. Add it in
the same change that records the licence answer, never before.

## CDN

**Nothing has been uploaded.** The packaging convention is CDN-hosted images
under `https://files.seeedstudio.com/Solution/landpage_asset/<id>/<name>-<hash>.png`,
and `solution.yaml` does not use it yet — `architecture.svg` is referenced by
its local path. Uploading is a separate step and is safe for this file, since it
carries no dataset content; it has simply not been done.

When the gallery is published, upload `architecture.svg` and switch
`intro.cover_image` and `intro.gallery[].src` to the CDN URLs in one change.

## Model artefacts

`assets/models/` carries only manifests and checksums — `hef.manifest.json`,
`hef_o1.manifest.json` and `SHA256SUMS`. No weights, ONNX or HEF are in this
repository, and none have been uploaded to
`https://sensecraft-statics.seeed.cc/solution-app/edge_inspection_surface/models/`
either. The download steps in `devices/` name that path and verify the checksum,
and each carries a `TODO(CDN)` comment saying the file is not there yet and must
be placed on the device by hand in the meantime.

## defect-overlay-inclusion.jpg / defect-overlay-pitted.jpg

Added 2026-09-07. Both are the detector's own output, taken from these two
files in the `edge-inspection-surface` working tree:

| Published file | Source file |
|---|---|
| `defect-overlay-inclusion.jpg` | `evaluation/runs/2026-09-05-m1-smoke/overlay_inclusion_110_jpg.rf.14d4ab42696fedc3d48775e0cce5fd57.jpg` |
| `defect-overlay-pitted.jpg` | `evaluation/runs/2026-09-05-m1-smoke/overlay_pitted_surface_100_jpg.rf.50a2cc31fe13105a21b22f930e481d7f.jpg` |

Each source frame is 640 × 640, copied unchanged apart from JPEG re-encoding.
`defect-overlay-pair.jpg` (1288 × 640) is the two of them placed side by side
at native resolution with an 8 px white gutter — inclusion on the left, pitted
on the right. Nothing was scaled and no pixel inside either frame was altered.
It is the cover; the two single frames stay in this directory but are not
listed in `intro.gallery`, so the page still shows two NEU-DET frames and no
more. The blue boxes and scores are the ONNX model's
predictions; the thin white boxes are the labels they were matched against.

**Detection-result screenshots. The underlying photographs come from NEU-DET
(Northeastern University) surface-defect dataset — publicly circulated academic
data — and are used here only to show what the solution does. They are not
redistributed for training or as a dataset, and no further NEU-DET image is
published on this page. Non-commercial terms apply to the underlying images.**
Two frames is the whole of it, by decision on 2026-09-07.
