> **DeepPCB is a bare-board (copper-layer) defect dataset, licensed MIT.**
> This demo **uses it to validate the missing-part and dimension chain** — to show
> that "detection → expected-item comparison → dimension measurement → rule merge
> → MQTT/Modbus output" runs end to end and the contracts line up. DeepPCB's six
> defect classes (open/short/mousebite/spur/copper/pin-hole) **are not assembly
> missing parts**, and the model trained on them is not a missing-part detector.
> A real assembly-inspection deployment needs your own data (real PCBA or
> assemblies plus caliper measurements).

## What it does

A camera watches one inspection station. Each frame goes through the detector,
then through two business modules and one rule merge:

- **Assembly comparison** — a template expected-item list ("class" + "ROI" +
  match distance) is matched against the detections; whatever the list expects
  and the frame does not contain becomes "missing", anything found outside the
  list can be reported as "extra".
- **Dimension measurement** — a calibration reference in the same plane gives
  "mm_per_pixel"; the minimum-area rectangle of the target inside a measurement
  ROI is converted to millimetres and compared against nominal ± tolerance.
- **Verdict merge** — "defect", "missing", "extra" and
  "dimension_out_of_tolerance" each make the frame NG, and each of the four can
  be switched off individually.

The verdict lands in two places at once: Modbus TCP holding registers and coils
for the PLC, and one MQTT JSON event per frame for the MES or the historian.
Registers are always written before the coil flips, so a consumer that reacts
to the coil reads register data from the same verdict.

## What you get

- **A missing-part check that carries its own evidence.** The event says
  "expected_count" / "matched_count" / "missing_count" and lists each missing
  item with its label and ROI, so the operator sees which slot is empty rather
  than only that the board failed.
- **A dimension check with a stated error budget.** The measurement is only as
  good as the calibration; the payload therefore carries "mm_per_pixel",
  "calibrated", and a per-measurement status ("ok" / "undersize" / "oversize" /
  "not_found" / "uncalibrated") instead of a bare number.
- **A PLC-compatible register map.** HR 0–7 are bit-identical to the
  surface-inspection contract v1, so an existing PLC program that reads HR 0–7
  keeps working; HR 8–11 are appended for missing count, extra count, measured
  millimetres ×100 and the tolerance code.
- **Per-source configuration.** ROIs are picture coordinates, so
  "assembly" and "dimension" are configured per camera
  ("sources[].assembly" / "sources[].dimension"), not globally.
- **Contract validation on the publish path.** Every MQTT payload is checked
  against the v2 schema before it is sent, not only in the test suite.

## Where it fits

- PCBA and small-assembly stations where a fixed camera can see every part slot.
- Incoming or outgoing inspection where a part's size has to be confirmed
  against a drawing tolerance.
- Lines whose PLC already consumes an OK/NG coil and wants the reason code
  without a new protocol.
- Sites that want the verdict on MQTT for traceability while the PLC keeps
  driving the reject actuator.

## How well it works

**This is a demo package, not a certified metrology or safety product.** The
dimension module measures pixels against a calibration reference; its accuracy
depends on your optics, lighting and fixture, and it is not a substitute for a
calibrated gauge in an acceptance test.

| What the line gets | Typical | Device |
|---|---|---|
| Frame captured to the verdict on the Modbus coil | **P50 10.92 ms / P99 11.18 ms** | reComputer J30 series (J3011, Orin Nano 8GB) |
| Defect detection accuracy (mAP50) | **0.9876** | reComputer J30 series |
| Streams one host carries at a 10 fps line rate | **8** (12 degrading, 24 failing) | reComputer J30 series |
| Missing-part closed loop | **6 / 6** matched, **6 / 6** flagged after swapping boards | reComputer J30 series |
| Dimension error against a calibration reference | **0.65%** worst case, budget 1% | reComputer J30 series |

Conditions: DeepPCB6 val, 205 images / 1158 boxes, 6 classes, YOLOX-Tiny 640²
TensorRT fp16 at a frozen 0.35 threshold; end-to-end sampled 3000 times at the
10 fps line rate with 0 frames dropped; the stream sweep ran with Modbus and
MQTT disabled, so a deployment carrying both reaches fewer. Measured 2026-09-05
on a reComputer J30 series unit (J3011, Orin Nano 8GB; JetPack 6.2 / TRT
10.3) — the device tree originally misread as an Orin NX engineering kit,
corrected 2026-09-08 via device-tree compatible (nvidia,p3767-0003).

A follow-up check on 2026-09-08, after that same engine had run continuously
for 67 hours on the same reComputer J30 series (J3011) unit, confirmed CPU vs
TensorRT box agreement of 0.9992 and a capture-to-coil P50 of 11.45 ms, with
zero frames dropped over the full 67-hour run.

Two other hosts run the same detector at the same accuracy: the reComputer R2000
series with the Hailo-8 option at P50 11.89 ms / P99 16.08 ms end to end and
0.9858 mAP50 (2026-09-06), and the all-in-one reCamera Pro at 0.9870 mAP50 with
a 30.9 ms P50 inference call (RKNN INT8, 2026-09-08). The reCamera Pro INT8
calibration images came from this same validation split, so that column reads
optimistic against a set the model has not seen.

The accuracy figures come from DeepPCB, which is easier than a real assembly
scene — synthetic PCB defects have clean boundaries — and it is not a
missing-part detector. Expect to retrain on your own boards. This is a reference
design, not a certified inspection product.

## Output Interfaces

| Interface | Where | Content |
|---|---|---|
| MQTT | port 1883, "<device-name>/inspection/<stream-id>/results" | One JSON event per frame, schema "2.0.0": "verdict", "verdict_reasons", "detections[]", and the "assembly" and "dimension" sections. Both sections are always present, "enabled: false" when the module is off for that source |
| Modbus TCP | port 502, unit 1 | Coil 0 = NG, Coil 1 = OK (mutually exclusive). HR 0–7 as in contract v1 (primary class, defect count, bbox ×10000, heartbeat). HR 8 = missing, HR 9 = extra, HR 10 = millimetres ×100, HR 11 = tolerance code (0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated) |
| HTTP | port 8080, "/healthz" "/events" "/preview.mjpg" | Health counters, recent events, and an MJPEG preview with detection boxes and the assembly ROIs drawn in |

"HR 10 = 0" does not mean "measured 0 mm" — read HR 11 first. And in v2,
"verdict = NG" no longer implies "defect_count > 0": a missing part or an
out-of-tolerance measurement is enough on its own.

## Semi-automatic Annotation Tool

"tools/annotation/" in the upstream repository turns hand-drawn boxes into
pixel masks with SAM2, and turns approved masks into an assembly ROI profile —
it never runs on the edge device or in the frame loop; it is an offline
offline workstation tool for building the "assembly.expected[]" template.

- **Model.** SAM 2.1 Hiera-Small ("facebookresearch/sam2", Apache-2.0 code and
  checkpoints), plus a pure-numpy Otsu-flood backend that needs no GPU and
  doubles as a baseline.
- **What it does not save.** The operator still draws the box — that click
  count is unchanged from manual annotation (2 clicks/box). What SAM2 adds is
  a pixel mask from that same box, which the ROI-profile step then expands
  into a normalised "assembly" ROI ("roi_profile.py", mask bbox × 1.6).
- **More prompt points make it worse, not better.** Box-only prompting beat
  box+points and box+points+negatives in calibration — DeepPCB's defects are
  small enough that extra points and negative points fall on or inside the
  defect itself and pull the mask the wrong way. The tool defaults to
  box-only for this reason.
- **The revision rate is a proxy, not a human count.** No human reviewed this
  evaluation round; the 9.33% figure is "gt_box_iou < 0.5" applied
  automatically ("review_by: auto:gt_box_iou>=0.5"), kept in a separate field
  from any real human decision so the two are never averaged together.
- **"roi_profile_sha256".** The generated "assembly" section carries a SHA-256
  over that section alone (not the run directory, timestamp or model name),
  so an event can assert which ROI profile is running in the field; the field
  is additive and optional — hand-written ROIs simply omit it or send "null".

Numbers, per-class breakdown and the point-count calibration are in the boundary
table above and the guide's optional annotation step; both come from the same
DeepPCB6 val run this demo already uses for detection accuracy.

## Deployment Comparison

**Camera + reComputer J30 / J40 (Orin)** is the Jetson path. Every Jetson
measurement on this page — accuracy, throughput, latency and the 67-hour soak —
was taken on the reComputer J30 series (J3011, Orin Nano 8GB); J40 is not
separately benchmarked for this solution. A TensorRT engine is built on the
device during the first deploy (measured about 5 minutes on the J3011 unit),
which ties it to that device and that TensorRT version. Choose J3011 when you
want the numbers above to apply, or J40 for more headroom on extra camera
streams (not separately benchmarked on this solution).

**Camera + reComputer R2000 with Hailo-8** trades power and cost for a smaller
board footprint. The INT8 HEF is compiled off-device and downloaded at deploy
time, so there is no build step on the board. Measured on the same Hailo-8 platform: 106.75 FPS
hardware inference, 43.92 FPS full pipeline, mAP50 0.9858 against a CPU golden
(delta -0.0018) — reference values, to be updated after a re-test on the
reComputer unit. The multi-stream sweep above is Orin-only. This board also
has three hard prerequisites — matching Python minor version, HailoRT 4.21.x
held across driver, library and Python bindings, and
"hailo_pci force_desc_page_size=4096" — that the guide walks through.

**reCamera Pro** puts the whole node inside the camera: capture, detection on
the RV1126B NPU in INT8, the OK/NG verdict, the Modbus TCP server and the MQTT
publisher, with no host and no network hop in the decision path. Measured on
the device over the same 205-image val set: mAP50 0.9870 against 0.9876 for the
fp32 CPU reference, inference P50 30.9 ms. mAP50-95 is 0.8000 against 0.8213 —
that gap is box tightness at high IoU, and at the frozen 0.35 score this build
and the CPU reference report the same aggregate precision and recall on those
images, on a slightly different set of 30 missed boxes. Two limits: the 64 INT8
calibration images came from that same validation split, so the INT8 column
reads optimistic against unseen data, and the figures come from replaying
validation images on the device rather than from a camera pointed at a board. An
fp16 build is published alongside it (mAP50-95 0.8221, P50 110.3 ms) for a
station that needs the tighter boxes more than the frame rate. Assembly
comparison and dimension measurement stay off on this path: both need ROIs
marked per station, and this preset has no place to carry them.

## Usage Notes

- **The expected-item ROIs are picture coordinates.** Move or refocus the
  camera and the whole expected list has to be rebuilt. Fix the camera before
  building the template, not after.
- **The shipped expected list is an example, not your product.** It was
  generated from one DeepPCB image as a worked example. Replace
  "assembly.expected[]" with your own slots before the station means anything.
- **The dimension module is CPU-only and single-plane.** It measures a
  minimum-area rectangle inside a ROI against a calibration reference in the
  same plane; a tilted part, a reference at a different working distance, or a
  low-contrast edge will show up as error, "not_found", or "uncalibrated".
- **Read the coil and the registers as one sample only on the write side.** The
  runtime writes all registers, then the coil, under one lock. A reader that
  issues a coil read and a register read as two Modbus requests can land between
  two verdicts at high verdict rates — this was observed at ~20 verdicts/s in
  testing. At a real line takt this window does not open, but poll the registers
  first and treat the coil as the trigger if you care.
- **Multiple streams share one register bank.** Modbus carries the latest
  verdict, whichever source produced it; per-stream results come from MQTT.
- **The MQTT broker in this package is anonymous and local.** It is there so
  the deployment works out of the box; a production install should point at a
  broker with credentials.

## Scope of the Numbers

- **Orin figures** — detection accuracy, throughput, end-to-end latency and multi-stream capacity: run M4, 2026-09-05, host `orin-nano`.
- **Missing-part closed loop and dimension error** — run M2, 2026-09-05, same host, on a validation frame and a synthetic scene.
- **Hailo INT8 accuracy** — run M3a, 2026-09-05, in the x86 Hailo Dataflow Compiler emulator, not on a device.
- **Hailo-8 on-device throughput, latency and accuracy** — run M3b-pi-2, 2026-09-06, fleet host `harvest-pi`.

## Licensing note

The runtime code is Apache-2.0. The detector backbone is **YOLOX**
(Megvii-BaseDetection, Apache-2.0) — no Ultralytics code or weights are used,
so there is no AGPL obligation. The training data is **DeepPCB, MIT licensed**,
which allows redistribution and commercial use; the attribution travels with
the images in "gallery/ATTRIBUTION.md". The model shipped here is trained on
that bare-board defect dataset — see the box at the top of this page for what
that does and does not make it.
