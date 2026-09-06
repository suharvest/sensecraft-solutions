> **Internal validation only — not for public demonstration until the licence is
> confirmed.** The model is trained on a re-hosted copy of NEU-DET: the Roboflow
> page states CC BY 4.0, but no formal licence statement has been found for the
> original NEU-DET release. Until an explicit answer arrives or the dataset is
> replaced, nothing derived from it — weights, ONNX, HEF, evaluation
> screenshots, detection overlays — may be used for public demos, customer-site
> demos or commercial material. That is why this page carries a schematic rather
> than a sample of the detector's output: no dataset-derived image is committed
> to this package at all.

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

### Hailo-8 — on-device numbers from harvest-pi (2026-09-06)

The Raspberry Pi 5 + Hailo-8 path has an INT8 HEF (level-0, `optimization_level=0`)
built with Dataflow Compiler 3.31.0 / HailoRT 4.21.0. On-device measurement on
fleet `harvest-pi` (a 15-minute window with the board's sole Hailo-8 freed up
from a pre-existing container that otherwise holds it exclusively):

| Metric | Value | Conditions | Source |
|---|---:|---|---|
| Hardware inference FPS (`hailortcli run`) | 106.75 FPS | 854 frames / 8 s, HW latency 8.47 ms, no app-level pre/post-processing | `evaluation/runs/2026-09-06-rpi-hailo/results.md` §7.1 |
| mAP50 vs CPU golden (290-image val set) | 0.7091 vs 0.7574 (CPU), delta -0.0483 | `evaluate_accuracy.py detect --backend hailo` + `compare` | Same run §7.2 |
| Box match rate (IoU >= 0.5) | 86.66% (523 matched / 684 total boxes) | Same comparison | Same run §7.2 |
| Application-level inference FPS | 91.49 FPS (p50 10.93 ms, p95 13.19 ms) | `detector.detect()` only, bare-metal process reusing an existing Hailo Python venv | Same run §7.4 |
| Full-pipeline throughput | 46.14 FPS | Real `InspectionApp`: verdict + Modbus + MQTT + contract validation, source throttle removed | Same run §7.4 |
| End-to-end latency at 10 FPS line rate | p50 11.61 ms, p95 14.99 ms, p99 16.63 ms | `e2e_latency.py`, capture-to-Modbus-coil | Same run §7.5 |
| MQTT events | 20 captured, 3 sampled, all pass `contracts/validate_payload.py` (mqtt-event v1) | `mosquitto_sub` against the on-device broker | Same run §7.6 |
| Bare-metal process RSS | ~126 MB | Not measured through a container this round; the Dockerfile/ABI path was already verified separately | Same run §7.7 |

The two weakest classes (crazing AP50 0.3873, rolled-in_scale AP50 0.4483) lose
the most to INT8 quantisation — consistent with the emulator-stage finding
below, not a new problem introduced by the real board. Full detail, including
the known gap that the `compare` JSON's match-count fields were not re-saved
before device cleanup (the mAP50/score-delta numbers themselves are intact), is
in `evaluation/runs/2026-09-06-rpi-hailo/results.md` §7.2 and §7.9.

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
| Raspberry Pi added footprint | about 452 MB | Runtime image about 443 MB on disk + 8.9 MB HEF + config; natively built arm64 on harvest-pi on 2026-09-06 (444 MB); real inference now measured on that same board (see Hailo-8 section) | Cross-build measurement `2026-09-05-m3-hef` §3.1; native build `2026-09-06-rpi-hailo` |

## Detector Selection: Baseline vs Advanced

YOLOX-Tiny is the default and the only track measured on Jetson or shipped on
the Hailo preset. Two NMS-free DETR architectures — D-FINE-S and RT-DETRv2-S,
both Apache-2.0, both fine-tuned from their COCO-only checkpoint (no
Objects365-trained weights used or distributed) — were evaluated on the same
CPU golden run for a same-conditions comparison. `model.track` in
`config/config.json` selects which one runs; the Jetson deploy step exposes it
as a **Detector Track** choice.

| Detector | mAP50 | P / R at frozen 0.35 | Whole-frame misses | CPU `detect()` P50 / P95 / P99 (ms) |
|---|---:|---|---:|---|
| YOLOX-Tiny (default) | 0.7574 | 0.7632 / 0.6983 | 7/290 | 30.2 / 35.7 / 52.7 |
| D-FINE-S | 0.7499 | 0.4956 / 0.8017 | **0/290** | 54.0 / 68.1 / 95.8 |
| RT-DETRv2-S | 0.7317 | 0.4575 / 0.7847 | 1/290 | 83.1 / 93.8 / 126.1 |

All three: same 290-image NEU6 val split (706 boxes), same 640x640 static
batch-1 input, same machine (arm64 Mac, onnxruntime CPUExecutionProvider),
single seed per track, frozen threshold 0.35. Source:
`evaluation/runs/2026-09-06-a1-cpu/results.md`.

**mAP is close; the frozen threshold is not a fair comparison across
architectures.** 0.35 was calibrated on YOLOX's `obj x cls` score
distribution, not re-calibrated per architecture — that is why P/R above looks
lopsided (DETR's sigmoid decoder scores are distributed differently). At
matched precision instead of matched threshold (P approx. 0.81-0.87), D-FINE's
recall is 2-7 points higher than YOLOX's and whole-frame misses drop to 20
against YOLOX's 38. **This is a single-seed observation, not a confirmed
result** — each track has run one seed so far, and three are needed to call it
settled.

**crazing does not improve with a different architecture.** AP50 stays
0.30-0.36 across all three (YOLOX 0.360, D-FINE 0.302, RT-DETRv2 0.310) — the
same conclusion the Jetson boundary caveats already state for YOLOX alone: a
model-capability limit, not something a different detector head fixes.

**Hailo-8 does not support either DETR track — the Raspberry Pi preset stays
on YOLOX-Tiny.** The Hailo Dataflow Compiler 3.31.0 parser rejects
RT-DETRv2-S outright (`GridSample` x9, `GatherElements` x3, `TopK` x2 all
reported unsupported — deformable-attention operators with no Hailo-8
lowering) and crashes before it can even produce that list for D-FINE-S (a
`MatMul`-shape assumption in the parser itself, not a supported/unsupported
verdict). `dfine` and `rtdetrv2` are not offered as `detector_track` options
on the Hailo deploy step for this reason.

**RKNN converts without error but is unverified on hardware.** Both ONNX
files convert to `.rknn` for RK3576 (FP16, no quantization) successfully, but
18 `GridSample` nodes (9 per model) fall back to a custom-operator lowering
with no NPU implementation of their own — a successful conversion does not
mean that part of the graph runs on the NPU. No RK3576 device was reachable
to confirm output parity against CPU, so this is unverified, not a negative
result.

Source: `tracks/detector/PROVENANCE.md` (licence and commit lock for both
upstreams), `evaluation/runs/2026-09-06-a1-probe/results.md` (Hailo/RKNN
probe).

## Unsupervised Anomaly Detection (Optional)

An optional second model (anomalib EfficientAD-S, Apache-2.0) can run
alongside the detector, trained only on defect-free ("OK") reference images,
to flag frames that look unlike that reference set — including defect
*types* the detector was never trained to name. It never replaces the
detector's verdict: `anomaly_score` is an additive, independent MQTT field
(`contracts/MQTT.md`), and `anomaly_verdict` is never merged into the
top-level `verdict`.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Pixel-level AUROC | **0.8752** | DeepPCB `pcb` OK/anomaly split: 205 OK val + 213 OK test + 213 defect test images | `evaluation/runs/2026-09-05-a2-cpu/results.md` |
| Pixel-level AUPRO (FPR <= 0.30) | **0.6494** | Same run, 1177 connected defect regions | Same run |
| Image-level AUROC | **0.5201** (0.5 = random) | Same run — see caveat below | Same run |
| Same-source OK-set cross-check: image-level AUROC (NEU patch) | **0.7055** | A separate EfficientAD-S training/evaluation run; OK and defect patches are cropped from the same batch of NEU photographs, same shoot, only crop position differs; 256x256 patches; dataset licence UNRESOLVED, internal method-validation only | `evaluation/runs/2026-09-06-a2-neu-cpu/results.md` |
| Unseen-defect recall, leave-one-class-out (pixel/region level) | **0.225 - 0.955**, uneven by class (open 0.955, spur 0.225) | Held-out class never enters calibration; the model has never seen its label | Same run §2 |
| Dual-path latency overhead (detector + EfficientAD, CPU reference) | **+139 ms P95/frame** | queue=2, 500 ms timeout (the shipped default); 120/120 frames joined, 0 dropped | Same run §3 |

**Pixel/region-level scoring is usable; image-level is not, and 12 aggregation
methods were tried and none fixed it.** Turning the pixel-level heatmap into a
single per-image score (max, top-k mean, Otsu-foreground-mask max,
Gaussian-smoothed max, connected-area / connected-region fraction) leaves
image AUROC at 0.495-0.530 across all twelve — inside the noise band around
random. The cause is not a sparse noise spike at the image border (cropping
the border made no measurable difference); it is a diffuse, whole-image score
offset between the OK set (scanned templates) and the defect set (real
photographs) that pollutes every single-scalar summary of the pixel map in
the same way. Pixel/region metrics stay valid because they only compare
inside one anomaly image (in-box vs. out-of-box), where that offset cancels
out; image-level metrics compare two different images from two different
sources, where it does not.

**The OK reference set must be sourced the same way as the frames being
tested — the set behind the numbers above is not. This is not an inference;
it is the result of two paired experiments: OK/defect not same-sourced (this
model, DeepPCB template scans vs. photographs) gives image-level AUROC
0.5201 (random); OK/defect same-sourced (a separate EfficientAD-S
training/evaluation run, NEU patch, OK and defect patches cropped from the
same batch of photographs) brings image-level AUROC back up to 0.7055 — see
the "same-source OK-set cross-check" row in the table above.** NEU6, this
package's own detector training data, has no defect-free images at all:
every one of its 1799 images carries at least one annotated defect. The
anomaly model above is therefore trained and evaluated on a different,
MIT-licensed dataset (DeepPCB) whose OK images are scanned board templates
while its defect images are photographs of a different, physical board —
that template-vs-photograph gap is exactly the diffuse offset described
above, and it does not represent what a real line's OK/defect pair looks
like when both are captured by the same camera. **The 0.7055 same-source
number is itself not a product metric** — it comes from patch-level
evaluation (256x256 crops, not full frames), the dataset's licence is
UNRESOLVED (internal method-validation only, not for external demos), and it
is a single, unreproduced run; it does not license a claim that "same-source
data gets you to 0.7 AUROC" in production. **Before enabling
`anomaly.enabled`, collect your own OK-sample images from the actual
inspection camera and recalibrate `anomaly.threshold` on them** — do not
treat the pixel AUROC above as a promise for your line's images; it
demonstrates the mechanism, not your dataset's number.

Config: `anomaly.enabled` (default `false`) and `anomaly.threshold` in
`config/config.json`, additive to the schema — leaving it off reproduces
every other measurement on this page exactly. When enabled, read
`anomaly_score` as a pixel/region-level signal alongside `heatmap_ref`, not a
frame-level normal/abnormal switch; the number above is why.

Source: `tracks/anomaly/README.md`, `tracks/anomaly/PROVENANCE.md` (anomalib
`lib/v2.6.0`, Apache-2.0), `evaluation/runs/2026-09-05-a2-cpu/results.md`,
`evaluation/runs/2026-09-05-a2-aggregation/results.md`.

## Optional: VLM Explanations

The runtime can hand a frame to a shared external VLM service
(`edge-vision-vlm`) for a plain-language explanation. This is a side channel,
not a second judge: it never enters the frame loop, never changes `verdict`,
and a disabled, slow or unreachable service produces exactly the same OK/NG
stream as without it.

- **Trigger** (either condition, a box always wins). `low_confidence` — the
  primary defect's score is below `vlm.trigger.min_confidence`. `anomaly` —
  `anomaly_score` crosses `anomaly.threshold` **and the detector produced
  zero boxes**, so there is nothing machine-readable to hand the operator
  otherwise. Rate-limited by `vlm.trigger.min_interval_s` per stream; never a
  per-frame call.
- **Side channel.** A bounded, drop-oldest queue plus an independent worker
  thread submit the call; the main event on `inspection/<stream-id>/results`
  publishes on its usual schedule regardless of whether the VLM answers. If
  it does, a second event follows on `inspection/<stream-id>/explanations`,
  keyed to the same `frame_id`.
- **Does not block the main chain.** A hard client timeout abandons the
  call; repeated failures open a circuit breaker for a cool-off period,
  probed by `GET /healthz`.
- **Latency is not a per-frame number to plan around.** Measured on the
  shared service's own evaluation hardware — an NVIDIA Spark GB10
  workstation, **not this device** — generation alone with Qwen3-VL-2B bf16
  is P50 approx. 3.2 s / P95 approx. 7.2 s at `max_tokens=320`. That is why
  the call sits off the hot path in the first place; no Orin-specific
  latency has been measured for this integration.

Enable it by setting `vlm.enabled: true` and pointing `vlm.base_url` at a
reachable `edge-vision-vlm` instance; see the guide for the walk-through,
including the `no_proxy` requirement on the device.

Source: upstream `README.md` "VLM 解释" section,
`contracts/explanation-event.schema.json`,
`evaluation/runs/2026-09-06-mvlma-stub-localhost/results.md` (Mac stub-backend
integration test, not a real-model latency measurement).

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

**IP camera + Raspberry Pi 5 (Hailo-8)** is the cheaper board. It has now run
on real hardware (harvest-pi, 2026-09-06): 106.75 FPS hardware inference,
46.14 FPS full pipeline, mAP50 0.7091 against a CPU golden of 0.7574 (86.66%
box match rate at IoU >= 0.5). Three ABI gates still have to pass on the device
before it starts (Python minor version, HailoRT driver/userspace/firmware
triple, `force_desc_page_size=4096`), and the deploy step checks each one.

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

The runtime code is Apache-2.0. The default detection backbone is YOLOX
(Megvii-BaseDetection), also Apache-2.0 — deliberately, to avoid the AGPL terms
that come with Ultralytics weights. No Ultralytics code or weights are used
anywhere in this solution. The two optional advanced detector tracks are
likewise Apache-2.0 upstream (D-FINE, Peterande/D-FINE; RT-DETRv2,
lyuwenyu/RT-DETR), fine-tuned only from their COCO-licensed checkpoint — no
Objects365-trained weights are downloaded or distributed, since upstream
itself states that licence is unconfirmed for those (`tracks/detector/PROVENANCE.md`).
The optional unsupervised-anomaly model (anomalib EfficientAD-S) is also
Apache-2.0, including its pretrained teacher weights
(`tracks/anomaly/PROVENANCE.md`); its OK/anomaly training data (DeepPCB) is
MIT-licensed and distinct from NEU-DET.

**The training data is the unresolved part.** The model is trained on a
re-hosted copy of NEU-DET. The Roboflow page for that copy states CC BY 4.0, but
no formal licence statement has been found for the original NEU-DET release, so
the chain from the original authors to that page is not established. Everything
derived from it — the checkpoint, the ONNX, both HEFs, the TensorRT engine, the
evaluation overlays — is restricted to internal validation until an explicit
answer arrives or the dataset is replaced with one whose terms are clear. No
image derived from that dataset is committed to this package, which is why the
only illustration here is a schematic drawn for this solution. Do not use this
solution for a public demo, a customer-site demo or commercial material before
that.
