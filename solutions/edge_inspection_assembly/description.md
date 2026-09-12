> ⚠️ **The bundled model is trained on DeepPCB (MIT license) — a bare-board copper-defect dataset, not assembly missing-part data.**
> It exists to prove the "detection → expected-item comparison → dimension measurement → rule merge → MQTT/Modbus output" chain and its contracts.
> For a real assembly station, retrain on your own data (real PCBA plus caliper measurements).

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
- **A dimension check with a stated error budget.** The payload carries
  "mm_per_pixel", "calibrated", and a per-measurement status ("ok" /
  "undersize" / "oversize" / "not_found" / "uncalibrated") instead of a bare
  number.
- **A PLC-compatible register map.** HR 0–7 are bit-identical to the
  surface-inspection contract v1, so an existing PLC program that reads HR 0–7
  keeps working; HR 8–11 are appended for missing count, extra count, measured
  millimetres ×100 and the tolerance code.
- **Per-source configuration.** ROIs are picture coordinates, so
  "assembly" and "dimension" are configured per camera
  ("sources[].assembly" / "sources[].dimension"), not globally.
- **Contract validation on the publish path.** Every MQTT payload is checked
  against the v2 schema before it is sent.

## Where it fits

- PCBA and small-assembly stations where a fixed camera can see every part slot.
- Incoming or outgoing inspection where a part's size has to be confirmed
  against a drawing tolerance.
- Lines whose PLC already consumes an OK/NG coil and wants the reason code
  without a new protocol.
- Sites that want the verdict on MQTT for traceability while the PLC keeps
  driving the reject actuator.

## How well it works

| What the line gets | Typical | Device |
|---|---|---|
| Frame captured to the verdict on the Modbus coil | **P50 10.92 ms / P99 11.18 ms** | reComputer J30 series (J3011, Orin Nano 8GB) |
| Defect detection accuracy (mAP50) | **0.9876** | reComputer J30 series |
| Streams one host carries at a 10 fps line rate | **8** (12 degrading, 24 failing) | reComputer J30 series |
| Missing-part closed loop | **6 / 6** matched, **6 / 6** flagged after swapping boards | reComputer J30 series |
| Dimension error against a calibration reference | **0.65%** worst case, budget 1% | reComputer J30 series |

Conditions: DeepPCB6 val, 205 images / 1158 boxes / 6 classes, YOLOX-Tiny 640²
TensorRT fp16 at a frozen 0.35 threshold; end-to-end sampled 3000 times at
10 fps with 0 frames dropped. A follow-up check after the same J3011 unit had
run continuously for 67 hours confirmed 0.9992 CPU-vs-TensorRT box agreement
with zero frames dropped.

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

"tools/annotation/" in the upstream repository is an offline workstation tool
for building the "assembly.expected[]" template (it never runs on the edge
device): the operator draws boxes, SAM 2.1 (Apache-2.0) turns each box into a
pixel mask, and the masks are expanded into normalised ROIs. The generated
"assembly" section carries a "roi_profile_sha256" so an event can assert which
ROI profile is running in the field. See the optional annotation step in the
deployment guide.

## Deployment Comparison

**Camera + reComputer J30 / J40 (Orin)** is the fully benchmarked path; the
numbers on this page come from a J3011 (Orin Nano 8GB). J40 is not separately
benchmarked — choose it when you want headroom for more camera streams. A
TensorRT engine is built on the device during the first deploy (~5 minutes),
tying it to that device and TensorRT version.

**Camera + reComputer R2000 with Hailo-8** trades power and cost for a smaller
board: measured on the same Hailo-8 platform at mAP50 0.9858 and P50 11.89 ms
end to end. The INT8 HEF is compiled off-device and
downloaded at deploy time. Three hard prerequisites (matching Python minor
version, HailoRT 4.21.x across driver/library/bindings, and
"force_desc_page_size=4096") are walked through in the guide.

**reCamera Pro** puts the whole node inside the camera: capture, INT8 detection
on the RV1126B NPU, the OK/NG verdict, Modbus TCP and MQTT — no host in the
decision path. mAP50 0.9870, inference P50 30.9 ms. An fp16 build (higher
mAP50-95, P50 110.3 ms) is published alongside for stations that need tighter
boxes. Assembly comparison and dimension measurement are not available on this
path.

## Usage Notes

- **The expected-item ROIs are picture coordinates.** Move or refocus the
  camera and the whole expected list has to be rebuilt. Fix the camera before
  building the template, not after.
- **The shipped expected list is an example, not your product.** Replace
  "assembly.expected[]" with your own slots before the station means anything.
- **The dimension module is CPU-only and single-plane.** A tilted part, a
  reference at a different working distance, or a low-contrast edge shows up as
  error, "not_found", or "uncalibrated".
- **Coil and registers belong to one verdict only on the write side.** The
  runtime writes all registers, then the coil, under one lock. A reader issuing
  two separate Modbus requests can land between verdicts at high verdict rates;
  poll the registers first and treat the coil as the trigger if you care.
- **Multiple streams share one register bank.** Modbus carries the latest
  verdict, whichever source produced it; per-stream results come from MQTT.
- **The MQTT broker in this package is anonymous and local.** A production
  install should point at a broker with credentials.

## Licensing note

Runtime code is Apache-2.0; the detector backbone is YOLOX (Apache-2.0), with
no Ultralytics code or weights, so there is no AGPL obligation. The training
data is DeepPCB (MIT); attribution travels with the images in
"gallery/ATTRIBUTION.md".
