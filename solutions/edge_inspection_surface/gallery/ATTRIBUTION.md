# Gallery attribution

## Standing rule: no dataset-derived image is committed

**Until the dataset licence question below is answered, this package commits no
image derived from the training or validation data** — no detection overlay, no
evaluation screenshot, no sample frame, in this directory or anywhere else in
the solution. This matches the upstream repository, which excludes
`evaluation/fixtures/` and `evaluation/runs/**/*.jpg` from version control and
commits only the numerical smoke report.

The rule covers the whole package, not just this directory: `assets/models/`
holds manifests and checksums only, and nothing has been uploaded to a CDN.

## What is in this directory

| File | Origin | Contains dataset imagery |
|---|---|---|
| `architecture.svg` | Drawn for this solution | No |

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
