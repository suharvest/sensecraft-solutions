# Gallery attribution

## cover.png

A real frame from this solution's own detection pipeline, not a mock-up. The
skeleton, bounding box and status card are rendered from the actual MQTT message
the detector published for that frame (`frame_id` 1147, `state: fallen`,
`evidence_features: 2/3`), captured on a reComputer J30 (Orin Nano, JetPack 6.2,
TensorRT 10.3) running the YOLO11s-Pose engine.

The underlying video frame comes from the **GMDCSA-24** fall-detection dataset,
v2.1:

> GMDCSA24 — A Dataset for Human Fall Detection in Videos
> https://github.com/ekramalam/GMDCSA24-A-Dataset-for-Human-Fall-Detection-in-Videos
> Licensed under the MIT License.

MIT License terms require the copyright notice to travel with copies and
derivatives, which is the purpose of this file.

The subject's face is obscured (pixelated and Gaussian-blurred) in the published
image. The dataset licence covers the authors' copyright; it does not purport to
grant the subjects' likeness rights, so the face is removed rather than relied
on. Replace this image with first-party footage if the solution page moves to a
context where that distinction matters more.

## live-fall-demo.gif

The reCamera Pro App Center `Live Preview` page, showing a track move from
`NORMAL` through `fall detected 84%` to `FALLEN`.

Source video is again **GMDCSA-24** v2.1 (`subject-4/Fall/01.mp4`, MIT — see the
citation above); the pose overlay is a matching RV1126B / YOLO11n-pose trace.
File SHA-256 `005893ab60a7085734827c1cc05b4f87a07e911c65593231707720f734d0bbd9`,
verified against the value upstream records for it.

Two things to keep straight when using this asset:

- **The state labels are replayed** to demonstrate the panel transition. Upstream
  states plainly that this is not evaluation evidence; the frozen accuracy figures
  live in the evaluation ledger, not here.
- **It depicts reCamera Pro**, which is not one of this solution's four presets.
  It is included because it shows the shared detection behaviour and state machine
  that every preset implements. Caption it as the Pro preview rather than implying
  it is one of the presets on offer.

No face is identifiable in any frame (the subject is turned away, then face-down),
so unlike `cover.png` there was nothing to obscure.

## camera-placement.svg

Drawn for this solution. Deliberately wordless — marks and measurements only — so
one asset serves both the English and Chinese guides.
