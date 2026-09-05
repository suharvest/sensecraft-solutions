# Gallery attribution

> **These images are internal validation assets. They must not be published, put
> on a public solution page, shown in a customer demo, or used in commercial
> material until the dataset licence question below is answered.**

## What these files are

| File | sha256 | Origin |
|---|---|---|
| `overlay-pitted-surface.jpg` | `b5871171ba0d2c8d50b421e258637039a7e28491f6d844248466f2ebbfd6f31a` | `evaluation/runs/2026-09-05-m1-smoke/overlay_pitted_surface_100_jpg.rf.50a2cc31fe13105a21b22f930e481d7f.jpg` in the upstream repo |
| `overlay-inclusion.jpg` | `f02a8d51f3999bf876b7aca3fb0b12b06ba0917c3ccc57e174280fb499b0be4b` | `evaluation/runs/2026-09-05-m1-smoke/overlay_inclusion_110_jpg.rf.14d4ab42696fedc3d48775e0cce5fd57.jpg` in the upstream repo |

Both are real output from this solution's own pipeline, not mock-ups: an image
from the held-out validation split with the detector's boxes, class names and
scores drawn on it by the CPU smoke script (ONNX
`4eb5e4ff6144810e919f2a63ad8f7dcd1c1ac5309d207b1d9ff832ba6cd63aba`, YOLOX-Tiny
640x640). The numerical output for the same run is
`evaluation/runs/2026-09-05-m1-smoke/smoke-report.json`.

## The licence problem

The underlying photographs come from **NEU-DET** (NEU surface defect database)
by way of a re-hosted copy on Roboflow. That Roboflow page states CC BY 4.0. **No
formal licence statement has been found for the original NEU-DET release**, so
the chain of permission from the original authors to that page is not
established, and CC BY 4.0 on a re-host is a claim by the re-hoster rather than
a grant traceable to the copyright holder.

Consequences, applied consistently across the whole project:

- The upstream repository excludes every dataset-derived image from version
  control (`evaluation/fixtures/`, `evaluation/runs/**/*.jpg`); only the
  numerical smoke report is committed. **The two files here are the one
  deliberate exception**, carried into this package so the solution has a cover
  image at all. They inherit the same restriction, not an exemption from it.
- The trained checkpoint, the ONNX, both HEFs and any TensorRT engine built from
  them are equally derived works and are equally restricted.
- The solution page, `solution.yaml`, both description files and both guides all
  carry the same notice.

## What has to happen before these can be published

One of:

1. An explicit licence answer for the original NEU-DET release that permits
   redistribution and derivative works, recorded in the upstream repo's
   `data/DATASET.md` alongside the Roboflow id, version, download date and URL.
2. Retraining on a dataset whose terms are clear — the upstream survey ranks
   AITEX (CC BY 4.0) above the NEU derivatives for exactly this reason — and
   regenerating these overlays from that model.

Until then these files stay in this package for internal review and go no
further.

## CDN

**Nothing has been uploaded.** The packaging convention is CDN-hosted images
under `https://files.seeedstudio.com/Solution/landpage_asset/<id>/<name>-<hash>.png`,
and `solution.yaml` deliberately does not use it: uploading these files to a
public CDN is itself the publication step that the licence question blocks. The
gallery entries therefore point at local paths.

When the licence is cleared or the images are replaced, upload them and switch
`intro.cover_image` and `intro.gallery[].src` to the CDN URLs in the same change.

## Model artefacts

`assets/models/` carries only manifests and checksums — `hef.manifest.json`,
`hef_o1.manifest.json` and `SHA256SUMS`. No weights, ONNX or HEF are in this
repository, and none have been uploaded to
`https://sensecraft-statics.seeed.cc/solution-app/edge_inspection_surface/models/`
either. The download steps in `devices/` name that path and verify the checksum,
and each carries a `TODO(CDN)` comment saying the file is not there yet and must
be placed on the device by hand in the meantime.
