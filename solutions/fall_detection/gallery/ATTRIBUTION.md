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
