> **Internal validation only — not for public demonstration until the licence is
> confirmed.** The model is trained on a re-hosted copy of NEU-DET: the Roboflow
> page states CC BY 4.0, but no formal licence statement has been found for the
> original NEU-DET release. Until an explicit answer arrives or the dataset is
> replaced, nothing derived from it — weights, ONNX, HEF, evaluation
> screenshots, the overlay images on this page — may be used for public demos,
> customer-site demos or commercial material.

## What it does

Point a fixed camera at a steel strip or part. The device decides, frame by
frame, whether the surface carries a defect, and hands the OK/NG verdict to the
line two ways at once: a Modbus TCP coil a PLC can latch on, and an MQTT message
carrying every box in that frame.

Six defect classes are recognised: crazing, inclusion, patches, pitted surface,
rolled-in scale and scratches. Detection, the OK/NG rule and both outputs run on
the device; no image leaves it.

## What you get

**A verdict a PLC can act on directly.** Coil 0 is NG and coil 1 is OK, always
mutually exclusive. The holding registers are updated atomically before the coil
is written, so the moment the PLC sees the coil flip, registers 0-7 already hold
that same frame's class, defect count, primary box and heartbeat.

**One MQTT message per frame, not per box.** The verdict, the reason, the defect
count and every detection in that frame arrive in one payload. Boxes are
normalised `[cx, cy, w, h]`, and `slot` is a within-frame index ordered by score
— this pipeline does no tracking, so nothing about `slot` is stable across
frames. Every message is validated against the contract schema on the publish
path; a malformed payload is counted and dropped rather than sent.

**A commissioning page on the device.** An MJPEG preview with the boxes drawn
on it, a health endpoint carrying inference time, capture-to-coil latency and
the MQTT/Modbus counters, and the most recent verdicts.

**One decode-and-postprocess implementation across accelerators.** The YOLOX
decode and per-class NMS are one shared numpy implementation; a backend only
preprocesses, calls the accelerator and hands back raw tensors. That is what
makes the cross-backend comparisons below meaningful rather than a comparison of
two different postprocessors.

## Where it fits

- **Strip and coil surface inspection** — a fixed overhead camera on the line,
  the verdict wired into an existing reject or marking station.
- **Retrofitting a PLC-driven line** — the Modbus register map is the whole
  integration surface; nothing on the line has to speak MQTT or HTTP.
- **Data collection before a real deployment** — the MQTT stream carries the
  boxes and scores per frame, so a line can be recorded and re-labelled before
  anyone commits to a threshold.

## How well it works

These are engineering benchmarks on one public dataset, **not a qualification
for any safety or quality-certification purpose**, and the dataset's licence is
unconfirmed. Every figure below is a single measurement by the original author,
never independently reproduced; the boundary files all carry `reproduced_by:
null`.

**How it was tested**

- NEU6, split 70/15/15 by source group — adjacent frame numbers within one
  defect class are treated as one strip and never cross a split boundary.
- Accuracy runs on the full 290-image validation split (706 annotated boxes).
  Inference runs once at a 0.01 score threshold; mAP50 and the frozen-threshold
  P/R/FP/FN all come out of that same pass, so the threshold sweep is post-hoc
  filtering rather than three separate tests.
- Throughput, latency and stream capacity were measured inside the deployment
  image itself, mounted the same way the compose file mounts it, so the numbers
  describe the ABI that actually ships.
- Input is a synthetic video assembled from 290 distinct validation images at
  640x640 / 10 FPS. Frames have no temporal continuity and the decode cost is
  not that of a real H.264 camera stream.
- Every validation image carries a defect, so a frame-level false alarm (a
  clean frame judged NG) cannot be measured on this dataset at all. Only misses
  can.

### Measured boundaries — Jetson Orin NX

Board: Jetson Orin NX 16GB (Seeed reComputer Super J4012), L4T R36.4.3 /
JetPack 6.2, TensorRT 10.3.0.30, power mode MAXN_SUPER (read, not changed),
image `edge-inspection-jetson:0.1.0-dev`, repo commit `670e433`. YOLOX-Tiny
640x640 FP16.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| mAP50 | 0.7577 | 290 val images / 706 boxes, TensorRT FP16, single pass at score 0.01 | This measurement, `boundary.accuracy.yaml` stable tier |
| Precision / recall at the frozen 0.35 threshold | P 0.7652 / R 0.6969 | Same pass, post-hoc filter; TP 492 / FP 151 / FN 214; 7 of 290 frames produce nothing at all | This measurement, `boundary.accuracy.yaml` stable tier |
| Recall at threshold 0.6 | R 0.5807 | Same pass; FN 214 to 296, whole-frame misses 7 to 39 (13.4%); precision rises to 0.865 | This measurement, `boundary.accuracy.yaml` degrading tier |
| Recall at threshold 0.9 | R 0.0241 | Same pass; 273 of 290 frames produce nothing (94%); crazing and rolled-in scale recall zero | This measurement, `boundary.accuracy.yaml` failure tier |
| Inference call, P50 | 8.797 ms (113.7 FPS) | 500 `detect()` calls over 60 pre-decoded frames; includes letterbox, execute and CPU NMS. P95 9.097 / P99 9.223 ms | This measurement, `boundary.throughput.yaml` |
| Engine execute alone | about 5.6 ms (about 178 FPS) | The runtime's own `inference_time_ms` field, execute only — the remaining ~3.2 ms is letterbox plus CPU NMS | This measurement, `boundary.throughput.yaml` |
| Full pipeline at line rate | 9.999 FPS, 0 frames dropped | Single stream throttled to the configured 10 FPS; capture, inference, verdict, Modbus, MQTT and contract validation all included | This measurement, `boundary.throughput.yaml` stable tier |
| Full pipeline unthrottled | 76.5-104.3 FPS | Source throttle removed; the two figures differ by sample length (300 frames by wall clock vs 3000 frames counted in-app) | This measurement, `boundary.throughput.yaml` degrading tier |
| capture to Modbus coil, P50 / P95 / P99 | 9.298 / 9.441 / 9.549 ms | Single stream at 10 FPS, 3000 samples, max 9.926 ms, no sample over 20 ms; both timestamps taken by the runtime itself | This measurement, `boundary.e2e_latency.yaml` stable tier |
| capture to Modbus coil unthrottled, P50 / P95 / P99 | 35.90 / 39.75 / 40.36 ms | Same 3000 samples at 104 FPS; the extra ~26 ms is queueing in a depth-2 queue, not slower inference (5.35 ms mean) | This measurement, `boundary.e2e_latency.yaml` degrading tier |
| Concurrent streams — stable | 8 streams x 10 FPS | 5 min per level; 9.989 FPS per stream, 0.02% frames dropped, P95 72.3 ms. Criteria are in the script, not applied afterwards | This measurement, `boundary.multistream.yaml` stable tier |
| Concurrent streams — degrading | 12 streams x 10 FPS | 9.306 FPS per stream, 6.83% dropped, P95 104.0 ms. Aggregate pins at 110-112 FPS from here up: single-threaded inference is the ceiling | This measurement, `boundary.multistream.yaml` degrading tier |
| Concurrent streams — failure | 24 streams x 10 FPS | 4.593 FPS per stream, 53.95% dropped. Nothing crashes — over half the input is silently discarded, which on a line means missed parts | This measurement, `boundary.multistream.yaml` failure tier |
| 72 h soak | Not available | Started 2026-09-05T06:22:47Z, due 2026-09-08T06:22Z. Baseline at start: RSS 250.5 MiB, 10.9% CPU, 9.96 FPS, 0 dropped, Tj 62.1-62.7 C | In progress, `boundary.soak.yaml` all tiers null |

Per-class AP50 on the same pass, which is where the accuracy figure actually
comes from:

| Class | Annotated boxes | AP50 | Recall at 0.35 |
|---|---:|---:|---:|
| scratches | 95 | 0.9685 | 0.9263 |
| pitted_surface | 70 | 0.9301 | 0.8857 |
| patches | 122 | 0.9065 | 0.8689 |
| inclusion | 184 | 0.7658 | 0.6902 |
| rolled-in_scale | 104 | 0.6149 | 0.5481 |
| crazing | 131 | 0.3603 | 0.3969 |

Crazing is the weak class by a wide margin and no threshold fixes it — it is a
model-capability limit, visible since training. Any line whose dominant defect
is crazing needs a retrained model, not a retuned threshold.

The FP16 engine was also compared box-for-box against the same ONNX on CPU
(onnxruntime): 643 matched pairs, 3 boxes on the CPU side only and none on the
TensorRT side, mean IoU 0.9972 (minimum 0.8311), mean score difference 0.0011,
mAP50 difference 0.0003. FP16 changed no frame's OK/NG verdict.

### Hailo-8 — compiled and emulated, not yet run on hardware

The Raspberry Pi 5 + Hailo-8 path has an INT8 HEF built with Dataflow Compiler
3.31.0 / HailoRT 4.21.0, and its quantisation loss has been measured against the
compiler's own emulator. **No figure in this section comes from Hailo hardware**,
and no accuracy, throughput or latency number for that board exists yet.

Two HEF builds were compiled from the same ONNX and compared on the same 20
validation images (45 boxes), chosen to be disjoint from the calibration set and
spread evenly across the six classes:

| Path | mAP50 | P at 0.35 | R at 0.35 | Whole-frame misses | Conditions | Source |
|---|---:|---:|---:|---:|---|---|
| CPU onnxruntime (reference) | 0.7228 | 0.6429 | 0.6000 | 0 | Same ONNX, same 20 images | Emulator run, `2026-09-05-m3-hef` |
| Emulator, INT8 level-0 | 0.6927 | 0.7353 | 0.5556 | 3 | `optimization_level=0`, 128 calibration images from the val split | Emulator run, `2026-09-05-m3-hef` §2 |
| Emulator, INT8 level-1 | 0.7266 | 0.7179 | 0.6222 | 2 | `optimization_level=1`, 1024 calibration images from the train split, Bias Correction applied | Emulator run, `2026-09-05-m3-hef` §6.5 |

Level-1 is the default this solution deploys. It recovers the two classes
level-0 damaged most — inclusion 0.5415 to 0.6552, rolled-in scale 0.4048 to
0.5108 — at the cost of a longer compile (773 s to 1180 s, all of it in the
optimize step). Its mAP50 lands 0.0038 above the CPU float baseline, which on 20
images and 45 boxes is sampling noise, not evidence that INT8 beats float.

What the emulator can and cannot show: it uses the fixed-point parameters from
the compiled model, so it demonstrates that the nine-tensor output assembly is
numerically equivalent to the CPU path (42 of 42 boxes matched, minimum IoU
0.9992) and it quantifies the INT8 loss on this subset. It is not bit-exact with
the hardware, and its own timing figures are x86 GPU timings with no relation to
a Hailo-8. Full-validation accuracy on the board is still outstanding.

### Deployment footprint

| Item | Value | Conditions | Source |
|---|---|---|---|
| TensorRT engine build on device | 291 s | Orin NX 16GB, JetPack 6.2, TRT 10.3, YOLOX-Tiny 640x640 FP16, static shapes | This measurement, `2026-09-05-m2-orin` §1 |
| Jetson image | 375 MB | `edge-inspection-jetson:0.1.0-dev`; host TensorRT and CUDA mounted rather than baked in | This measurement, `2026-09-05-m2-orin` |
| Raspberry Pi added footprint | about 452 MB | Runtime image about 443 MB on disk + 8.9 MB HEF + config; cross-built for arm64 on macOS, never run on a Pi | Cross-build measurement, `2026-09-05-m3-hef` §3.1 |

## Output Interfaces

| Output | Where | Content |
|---|---|---|
| Verdict | Modbus TCP port 502, unit 1, coils 0-1 | Coil 0 NG / coil 1 OK, mutually exclusive, written after the registers |
| Verdict detail | Modbus TCP port 502, unit 1, HR 0-7 | Class id, defect count, primary box as cx/cy/w/h normalised x10000, heartbeat Unix seconds as two words |
| Detections | MQTT port 1883, topic `<device-name>/inspection/<stream-id>/results` | One JSON per frame: verdict, reason, defect count, every box with class, score and normalised bbox |
| Live view | HTTP port 8080 `/preview.mjpg`, `/healthz`, `/events`, `/snapshot.jpg` | MJPEG preview with boxes, health counters, recent verdicts |

`<device-name>` and `<stream-id>` are both yours to choose in the deploy step.
They exist so several lines can share one broker and one box can carry several
cameras. The `stream_id` is also inside the payload, so nothing downstream has
to parse the topic.

## Deployment Comparison

**IP camera + reComputer J (Orin)** is the measured path. Every number in the
tables above was taken on an Orin NX 16GB. The TensorRT engine is built on the
device during deployment — it is bound to that exact GPU architecture and
TensorRT version and is never redistributed. Pick this when you need figures you
can hold someone to.

**IP camera + Raspberry Pi 5 (Hailo-8)** is the cheaper board and the unproven
one. The HEF is compiled, its quantisation loss is measured against the
compiler's emulator, and the runtime image cross-builds for arm64 — but nothing
has run on the hardware. Three ABI gates have to pass on the device before it
will start at all, and the deploy step checks each one. Pick this only if you are
prepared to be the first to run it.

## Usage Notes

- **The threshold is a business decision, and the sweep above prices it.** 0.35
  is the deployed value. Going to 0.6 buys precision 0.765 to 0.865 and costs
  whole-frame misses 7 to 39 out of 290. Decide which error your line can absorb
  before changing it.
- **False alarms are unmeasured.** Every image in the validation split carries a
  defect, so nothing here says how often a clean strip is called NG. That number
  has to come from your own line.
- **One camera per deployment as configured.** The runtime handles several
  streams and the capacity was measured at 8 stable on Orin NX, but the deploy
  step configures one. Add the rest to the `streams` list on the device and
  restart the container.
- **Multi-stream shares one Modbus register block.** The contract defines one set
  of coils and registers, so with several streams the last verdict wins. A line
  that needs per-stream registers needs a contract change first.
- **The stream ceiling is the single-threaded inference loop, not the GPU.**
  Aggregate throughput pins at about 110 FPS from 12 streams up, while the engine
  itself executes in 5.3-5.6 ms (about 178 FPS). Accelerator contexts are not
  thread-safe, so inference is serialised by design.
- **The measured input is a synthetic video, not a camera.** 290 validation
  images assembled at 640x640 / 10 FPS. Real H.264 from a real camera decodes
  differently and at other resolutions the decode share rises. Load-test with
  your own source before committing to a stream count.
- **The MQTT broker in this package is for commissioning.** It runs with
  `allow_anonymous true`. A production line should point at a broker with
  credentials instead.

## Licensing note

The runtime code is Apache-2.0. The detection backbone is YOLOX
(Megvii-BaseDetection), also Apache-2.0 — deliberately, to avoid the AGPL terms
that come with Ultralytics weights. No Ultralytics code or weights are used
anywhere in this solution.

**The training data is the unresolved part.** The model is trained on a
re-hosted copy of NEU-DET. The Roboflow page for that copy states CC BY 4.0, but
no formal licence statement has been found for the original NEU-DET release, so
the chain from the original authors to that page is not established. Everything
derived from it — the checkpoint, the ONNX, both HEFs, the TensorRT engine, the
evaluation overlays and the two images on this page — is restricted to internal
validation until an explicit answer arrives or the dataset is replaced with one
whose terms are clear. Do not use this solution for a public demo, a
customer-site demo or commercial material before that.
