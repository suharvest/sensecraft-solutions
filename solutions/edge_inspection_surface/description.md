> **The training dataset's licence is being confirmed.** The shipped weights are
> trained on a re-hosted copy of NEU-DET whose licence chain is unsettled.
> Retrain on your own images before any public demo or commercial use.
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
normalised "[cx, cy, w, h]", and "slot" is a within-frame index ordered by score
— this pipeline does no tracking, so nothing about "slot" is stable across
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

These are engineering benchmarks on one public dataset. This is a reference
design, not a qualification for any safety or quality-certification purpose.

| What the line gets | Typical | Device |
|---|---|---|
| Frame captured to the verdict on the Modbus coil | **P50 9.298 ms / P99 9.549 ms** | reComputer J40 series (J4012, Orin NX 16GB) |
| Frame captured to the verdict on the Modbus coil | **P50 10.56 ms** | reComputer J30 series (Orin Nano 8GB) |
| Defect detection accuracy (mAP50) | **0.7577** | reComputer J40 / J30 series |
| Precision and recall at the deployed 0.35 threshold | **P 0.7652 / R 0.6969** | reComputer J40 series |
| Streams one host carries at a 10 FPS line rate | **8** (12 degrading, 24 failing) | reComputer J40 series |

Conditions: NEU6 split 70/15/15 by source group; accuracy on the full 290-image
validation split (706 annotated boxes) in one pass at a 0.01 score threshold,
from which mAP50 and the frozen-threshold figures both derive. End-to-end
sampled 3000 times at 10 FPS. Board: Jetson Orin NX 16GB, L4T R36.4.3 /
JetPack 6.2, TensorRT 10.3.0.30, YOLOX-Tiny 640x640 FP16.

The reComputer R2000 series with the Hailo-8 option runs the same chain at
P50 11.61 ms / P99 16.63 ms and 0.7091 mAP50.

Accuracy differs a lot by defect class — scratches 0.9685, pitted surface
0.9301, patches 0.9065, inclusion 0.7658, rolled-in scale 0.6149, crazing
0.3603 — so check the classes you actually care about before you size a line
around the headline figure. Raising the threshold from 0.35 to 0.6 lifts
precision to 0.865 and drops recall to 0.5807.

**What these numbers cover.** Every validation image carries a defect, so a
frame-level false alarm (a clean frame judged NG) cannot be measured on this
dataset at all — that rate has to come from your own line images. The measured
input is a synthetic 640x640 / 10 FPS video assembled from validation images,
so add your camera's capture and encode time to the end-to-end figure.

## Detector Selection: Baseline vs Advanced

YOLOX-Tiny is the default and the only track measured on Jetson or shipped on
the Hailo preset. Two NMS-free DETR architectures — D-FINE-S and RT-DETRv2-S,
both Apache-2.0, both fine-tuned from their COCO-only checkpoint (no
Objects365-trained weights used or distributed) — were evaluated on the same
CPU golden run for a same-conditions comparison. "model.track" in
"config/config.json" selects which one runs; the Jetson deploy step exposes it
as a **Detector Track** choice.

| Detector | mAP50 | P / R at frozen 0.35 | Whole-frame misses | CPU "detect()" P50 / P95 / P99 (ms) |
|---|---:|---|---:|---|
| YOLOX-Tiny (default) | 0.7574 | 0.7632 / 0.6983 | 7/290 | 30.2 / 35.7 / 52.7 |
| D-FINE-S | 0.7499 | 0.4956 / 0.8017 | **0/290** | 54.0 / 68.1 / 95.8 |
| RT-DETRv2-S | 0.7317 | 0.4575 / 0.7847 | 1/290 | 83.1 / 93.8 / 126.1 |

All three: same 290-image NEU6 val split (706 boxes), same 640x640 static
batch-1 input, same development-machine CPU (onnxruntime, arm64) as an offline
baseline, frozen threshold 0.35. These are CPU comparison figures, not device
throughput.

**mAP is close; the frozen threshold is not a fair comparison across
architectures.** 0.35 was calibrated on YOLOX's "obj x cls" score
distribution, not re-calibrated per architecture — that is why P/R above looks
lopsided (DETR's sigmoid decoder scores are distributed differently). At
matched precision instead of matched threshold (P approx. 0.81-0.87), D-FINE's
recall is 2-7 points higher than YOLOX's and whole-frame misses drop to 20
against YOLOX's 38.

**Crazing AP50 across the three detector tracks:** YOLOX 0.360, D-FINE 0.302,
RT-DETRv2 0.310 (same validation set, same evaluation protocol). The YOLOX
figure matches the Jetson boundary table.

**Hailo-8 does not support either DETR track — the reComputer R2000 preset stays
on YOLOX-Tiny.** The Hailo Dataflow Compiler 3.31.0 parser rejects
RT-DETRv2-S outright ("GridSample" x9, "GatherElements" x3, "TopK" x2 all
reported unsupported — deformable-attention operators with no Hailo-8
lowering) and crashes before it can even produce that list for D-FINE-S (a
"MatMul"-shape assumption in the parser itself, not a supported/unsupported
verdict). "dfine" and "rtdetrv2" are not offered as "detector_track" options
on the Hailo deploy step for this reason.

Source: "tracks/detector/PROVENANCE.md" (licence and commit lock for both
upstreams).

## Unsupervised Anomaly Detection (Optional)

An optional second model (anomalib EfficientAD-S, Apache-2.0) can run
alongside the detector, trained only on defect-free ("OK") reference images,
to flag frames that look unlike that reference set — including defect
*types* the detector was never trained to name. It never replaces the
detector's verdict: "anomaly_score" is an additive, independent MQTT field
("contracts/MQTT.md"), and "anomaly_verdict" is never merged into the
top-level "verdict".

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Pixel-level AUROC | **0.8752** | DeepPCB "pcb" OK/anomaly split: 205 OK val + 213 OK test + 213 defect test images | "evaluation/runs/2026-09-05-a2-cpu/results.md" |
| Pixel-level AUPRO (FPR <= 0.30) | **0.6494** | Same run, 1177 connected defect regions | Same run |
| Image-level AUROC | **0.5201** (0.5 = random) | Same run — see caveat below | Same run |
| Same-source OK-set cross-check: image-level AUROC (NEU patch) | **0.7055** | A separate EfficientAD-S training/evaluation run; OK and defect patches are cropped from the same batch of NEU photographs, same shoot, only crop position differs; 256x256 patches; dataset licence UNRESOLVED, internal method-validation only | "evaluation/runs/2026-09-06-a2-neu-cpu/results.md" |
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
"anomaly.enabled", collect your own OK-sample images from the actual
inspection camera and recalibrate "anomaly.threshold" on them** — do not
treat the pixel AUROC above as a promise for your line's images; it
demonstrates the mechanism, not your dataset's number.

Config: "anomaly.enabled" (default "false") and "anomaly.threshold" in
"config/config.json", additive to the schema — leaving it off reproduces
every other measurement on this page exactly. When enabled, read
"anomaly_score" as a pixel/region-level signal alongside "heatmap_ref", not a
frame-level normal/abnormal switch; the number above is why.

Source: "tracks/anomaly/README.md", "tracks/anomaly/PROVENANCE.md" (anomalib
"lib/v2.6.0", Apache-2.0), "evaluation/runs/2026-09-05-a2-cpu/results.md",
"evaluation/runs/2026-09-05-a2-aggregation/results.md".

## Output Interfaces

| Output | Where | Content |
|---|---|---|
| Verdict | Modbus TCP port 502, unit 1, coils 0-1 | Coil 0 NG / coil 1 OK, mutually exclusive, written after the registers |
| Verdict detail | Modbus TCP port 502, unit 1, HR 0-7 | Class id, defect count, primary box as cx/cy/w/h normalised x10000, heartbeat Unix seconds as two words |
| Detections | MQTT port 1883, topic "<device-name>/inspection/<stream-id>/results" | One JSON per frame: verdict, reason, defect count, every box with class, score and normalised bbox |
| Live view | HTTP port 8080 "/preview.mjpg", "/healthz", "/events", "/snapshot.jpg" | MJPEG preview with boxes, health counters, recent verdicts |

"<device-name>" and "<stream-id>" are both yours to choose in the deploy step.
They exist so several lines can share one broker and one box can carry several
cameras. The "stream_id" is also inside the payload, so nothing downstream has
to parse the topic.

## Deployment Comparison

**IP camera + reComputer J30 / J40 (Orin)** is the measured path. Most numbers
in the tables above were taken on an Orin NX 16GB (J40); the smaller Orin
Nano 8GB (J30) has also been measured directly for accuracy and capture-to-coil
latency (mAP50 0.7577, P50 10.56 ms) — the streaming-capacity figures are still
J40-only. The TensorRT engine is built on the
device during deployment — it is bound to that exact GPU architecture and
TensorRT version and is never redistributed. Pick this when you need figures you
can hold someone to.

**IP camera + reComputer R2000 (Hailo-8)** is the cheaper board. Measured on
the same Hailo-8 platform: 106.75 FPS hardware inference, 46.14 FPS full
pipeline, mAP50 0.7091 against a CPU golden of 0.7574 (86.66% box match rate at
IoU >= 0.5) — reference values, to be updated after a re-test on the reComputer
unit. Three ABI
gates have to pass on the device before it starts (Python minor version,
HailoRT driver/userspace/firmware triple, "force_desc_page_size=4096"), and the
deploy step checks each one.

## Usage Notes

- **The threshold is a business decision.** 0.35
  is the deployed value. At 0.6, precision goes from 0.765 to 0.865 and
  whole-frame misses go from 7 to 39 out of 290.
- **False alarms have to come from your own line.** Every image in the
  validation split carries a defect, so this dataset cannot show how often a
  clean strip is called NG.
- **One camera per deployment as configured.** The runtime handles several
  streams and the capacity was measured at 8 stable on Orin NX, but the deploy
  step configures one. Add the rest to the "streams" list on the device and
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
  "allow_anonymous true". A production line should point at a broker with
  credentials instead.

## Scope of the Numbers

- **Orin figures** — 2026-09-05, Jetson Orin NX 16GB, JetPack 6.2 / TensorRT 10.3.0.30, image `edge-inspection-jetson:0.1.0-dev`, commit `670e433`.
- **reComputer R2000 series host** — 2026-09-06, fleet host `harvest-pi`, in a 15-minute exclusive window on the board's sole Hailo-8.
- **INT8 quantisation loss** — 2026-09-05, x86 Hailo Dataflow Compiler 3.31.0, emulator stage, not on a device.
- **D-FINE-S and RT-DETRv2-S tracks** — 2026-09-06, arm64 Mac, onnxruntime CPUExecutionProvider, CPU only, single seed each.
- **Throughput and end-to-end latency come from a synthetic 640×640 / 10 FPS video assembled from validation images**, so add your camera's own capture and encode time on top. The detector-track comparison ran on static 640×640 batch-1 images instead.
- **Frame-level false alarms** — every validation image carries a defect, so this dataset can only expose misses; the false-alarm rate comes from your own line.

## Licensing note

The runtime code is Apache-2.0. The default detection backbone is YOLOX
(Megvii-BaseDetection), also Apache-2.0 — deliberately, to avoid the AGPL terms
that come with Ultralytics weights. No Ultralytics code or weights are used
anywhere in this solution. The two optional advanced detector tracks are
likewise Apache-2.0 upstream (D-FINE, Peterande/D-FINE; RT-DETRv2,
lyuwenyu/RT-DETR), fine-tuned only from their COCO-licensed checkpoint — no
Objects365-trained weights are downloaded or distributed, since upstream
itself states that licence is unconfirmed for those ("tracks/detector/PROVENANCE.md").
The optional unsupervised-anomaly model (anomalib EfficientAD-S) is also
Apache-2.0, including its pretrained teacher weights
("tracks/anomaly/PROVENANCE.md"); its OK/anomaly training data (DeepPCB) is
MIT-licensed and distinct from NEU-DET.

**The training dataset's licence is being confirmed.** Until it is settled,
replace the shipped weights with a model trained on your own images before any
public or commercial use.
