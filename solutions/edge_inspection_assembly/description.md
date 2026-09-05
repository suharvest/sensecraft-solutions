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

- **Assembly comparison** — a template expected-item list (`class` + `ROI` +
  match distance) is matched against the detections; whatever the list expects
  and the frame does not contain becomes `missing`, anything found outside the
  list can be reported as `extra`.
- **Dimension measurement** — a calibration reference in the same plane gives
  `mm_per_pixel`; the minimum-area rectangle of the target inside a measurement
  ROI is converted to millimetres and compared against nominal ± tolerance.
- **Verdict merge** — `defect`, `missing`, `extra` and
  `dimension_out_of_tolerance` each make the frame NG, and each of the four can
  be switched off individually.

The verdict lands in two places at once: Modbus TCP holding registers and coils
for the PLC, and one MQTT JSON event per frame for the MES or the historian.
Registers are always written before the coil flips, so a consumer that reacts
to the coil reads register data from the same verdict.

## What you get

- **A missing-part check that carries its own evidence.** The event says
  `expected_count` / `matched_count` / `missing_count` and lists each missing
  item with its label and ROI, so the operator sees which slot is empty rather
  than only that the board failed.
- **A dimension check with a stated error budget.** The measurement is only as
  good as the calibration; the payload therefore carries `mm_per_pixel`,
  `calibrated`, and a per-measurement status (`ok` / `undersize` / `oversize` /
  `not_found` / `uncalibrated`) instead of a bare number.
- **A PLC-compatible register map.** HR 0–7 are bit-identical to the
  surface-inspection contract v1, so an existing PLC program that reads HR 0–7
  keeps working; HR 8–11 are appended for missing count, extra count, measured
  millimetres ×100 and the tolerance code.
- **Per-source configuration.** ROIs are picture coordinates, so
  `assembly` and `dimension` are configured per camera
  (`sources[].assembly` / `sources[].dimension`), not globally.
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
calibrated gauge in an acceptance test. The detection numbers below come from
the DeepPCB dataset described in the box at the top of this page, which is a
bare-board defect dataset — they say the chain works, not that this model finds
missing parts on your assemblies.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Detection mAP50 | **0.9876** | DeepPCB6 val, 205 images / 1158 boxes, 6 classes; YOLOX-Tiny 640², TensorRT fp16; frozen threshold 0.35 gives P 0.9284 / R 0.9741, FP 87 / FN 30, 0 frames fully missed | This project's own M4 run, 2026-09-05, on `orin-nano` (Orin NX 16GB engineering kit, JetPack 6.2 / TRT 10.3). Single run, not independently reproduced |
| Inference throughput | **95.06 FPS** (`detect()` P50 10.52 ms) | Same device and engine, single stream, 500 timed calls over 60 pre-decoded frames; engine execute alone is ~6.3 ms, the rest is letterbox + CPU NMS | Same M4 run |
| End-to-end latency, capture → Modbus coil | **P50 10.92 ms / P99 11.18 ms** | Single stream at the 10 fps line rate, 3000 samples, 0 frames dropped, 3000 Modbus writes. Unthrottled (89 FPS) the same path is P50 42.9 ms | Same M4 run |
| Multi-stream capacity | **stable 8 / degrading 12 / failure 24 streams** | 640² at 10 fps per stream, 5 min per level, whole sweep run twice; MQTT and Modbus were disabled during this test, so a real deployment with I/O reaches fewer streams | Same M4 run |
| Missing-part closed loop | **6 / 6 matched on the template frame, 6 / 6 missing after swapping boards** | Expected list generated from the ground-truth boxes of one val image (ROI = GT box ×1.6, 6 items); on that frame `missing_count` = 0, on a different board all 6 go missing and `verdict_reasons` gains `missing` alongside `defect` | This project's M2 run, 2026-09-05, same device |
| Dimension error (ArUco calibration) | **worst relative error 0.65%** (budget 1%) | Synthetic ArUco scene, mm/px +0.40%, long edge 60 → 60.241 mm (+0.40%), short edge 40 → 40.261 mm (+0.65%); tolerance ±1.0 mm, verdict `ok`. Identical on the uncompressed PNG and after mp4v encoding | Same M2 run |
| Hailo INT8 (HEF) accuracy | **mAP50 0.9924, identical on all three paths** | 20 val images / 118 boxes; CPU onnxruntime, Hailo emulator `SDK_NATIVE`, and emulator `SDK_QUANTIZED` (optimization level 1 + Bias Correction) return the same mAP50 / P / R / FP / FN. Per-box: CPU ↔ native 120/120 matched; CPU ↔ quantized 119/120 | This project's M3a run, 2026-09-05, in the Hailo Dataflow Compiler emulator on x86 — **not on a device** |
| Raspberry Pi 5 + Hailo-8 on-device throughput and latency | **not measured** | The runtime image cross-builds for arm64 and the HEF loads in the emulator, but nothing has run on the board yet | To be measured — do not quote a number here until it is |
| 72 h soak | **in progress at packaging time** | Single stream, looped 300 s video, 10 fps; baseline over the first samples: RSS 256–259 MiB, 0 dropped frames, tj 61–62 °C, 0 restarts | Same M4 run; the three tiers in `boundary.soak.yaml` are null until it finishes |

Two things the numbers above deliberately do not claim. First, the accuracy
figures are DeepPCB's, and DeepPCB is easier than a real assembly scene —
synthetic PCB defects have clean boundaries. Second, all five boundary files
record `reproduced_by: null`: single measurements by the author, on one device
each.

## Output Interfaces

| Interface | Where | Content |
|---|---|---|
| MQTT | port 1883, `<device-name>/inspection/<stream-id>/results` | One JSON event per frame, schema `2.0.0`: `verdict`, `verdict_reasons`, `detections[]`, and the `assembly` and `dimension` sections. Both sections are always present, `enabled: false` when the module is off for that source |
| Modbus TCP | port 502, unit 1 | Coil 0 = NG, Coil 1 = OK (mutually exclusive). HR 0–7 as in contract v1 (primary class, defect count, bbox ×10000, heartbeat). HR 8 = missing, HR 9 = extra, HR 10 = millimetres ×100, HR 11 = tolerance code (0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated) |
| HTTP | port 8080, `/healthz` `/events` `/preview.mjpg` | Health counters, recent events, and an MJPEG preview with detection boxes and the assembly ROIs drawn in |

`HR 10 = 0` does not mean "measured 0 mm" — read HR 11 first. And in v2,
`verdict = NG` no longer implies `defect_count > 0`: a missing part or an
out-of-tolerance measurement is enough on its own.

## Deployment Comparison

**Camera + reComputer J (Orin)** is the path every measurement on this page was
taken on. A TensorRT engine is built on the device during the first deploy
(about 5 minutes), which ties it to that device and that TensorRT version. Choose
it when you want the numbers above to apply, or when you need more than one or
two camera streams on one box.

**Camera + Raspberry Pi 5 with Hailo-8** trades measured evidence for power and
cost. The INT8 HEF is compiled off-device and downloaded at deploy time, so
there is no build step on the board; accuracy has been checked in the Hailo
emulator against the CPU baseline, but throughput, latency and stream capacity
on the board itself have not been measured. The board also has three hard
prerequisites — matching Python minor version, HailoRT 4.21.x held across
driver, library and Python bindings, and `hailo_pci force_desc_page_size=4096` —
that the guide walks through.

## Usage Notes

- **The expected-item ROIs are picture coordinates.** Move or refocus the
  camera and the whole expected list has to be rebuilt. Fix the camera before
  building the template, not after.
- **The shipped expected list is an example, not your product.** It was
  generated from one DeepPCB image so the chain could be verified. Replace
  `assembly.expected[]` with your own slots before the station means anything.
- **The dimension module is CPU-only and single-plane.** It measures a
  minimum-area rectangle inside a ROI against a calibration reference in the
  same plane; a tilted part, a reference at a different working distance, or a
  low-contrast edge will show up as error, `not_found`, or `uncalibrated`.
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

## Licensing note

The runtime code is Apache-2.0. The detector backbone is **YOLOX**
(Megvii-BaseDetection, Apache-2.0) — no Ultralytics code or weights are used,
so there is no AGPL obligation. The training data is **DeepPCB, MIT licensed**,
which allows redistribution and commercial use; the attribution travels with
the images in `gallery/ATTRIBUTION.md`. The model shipped here is trained on
that bare-board defect dataset — see the box at the top of this page for what
that does and does not make it.
