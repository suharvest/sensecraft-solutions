> **Dataset license pending.** The bundled weights are trained on a repost of
> NEU-DET whose license is not yet cleared; retrain on your own images before
> external demos or commercial use.

## What it does

Point a fixed camera at a steel strip or a workpiece. The device judges every
frame for surface defects and hands the OK/NG verdict to the line over two
paths at once: a Modbus TCP coil a PLC can latch onto, and an MQTT message
carrying every detection box of that frame.

Six defect classes are recognised: crazing, inclusion, patches,
pitted_surface, rolled-in_scale, scratches. Detection, the OK/NG rule and both
outputs run entirely on the device; images never leave it.

## What you get

**A verdict a PLC can act on directly.** Coil 0 is NG, coil 1 is OK, always
mutually exclusive. Every verdict atomically updates the holding registers
before the coil is written, so the moment the PLC sees the coil flip, registers
0-7 already hold that same frame's class, defect count, primary box and
heartbeat.

**One MQTT message per frame, not per box.** Verdict, verdict reasons, defect
count and all boxes of the frame ride in a single message. Boxes are normalised
"[cx, cy, w, h]". Every message is checked against the contract schema on the
publish path; failures are counted and dropped, never sent.

**A built-in debug page.** An MJPEG preview with the boxes drawn in, a health
endpoint with inference timing, capture→coil latency and MQTT/Modbus counters,
plus the most recent verdicts.

## Where it fits

- **Strip and coil surface inspection** — one fixed camera above the line, the
  verdict wired to an existing reject or marking station.
- **Retrofitting PLC-driven lines** — the Modbus register map is the whole
  integration surface; nothing on the line needs to speak MQTT or HTTP.
- **Data collection before a real deployment** — the MQTT stream carries boxes
  and scores per frame, so you can record the line, re-label, and only then
  decide where the threshold sits.

## How well it works

| What the line gets | Typical | Device |
|---|---|---|
| Frame captured to the verdict on the Modbus coil | **P50 9.298 ms / P99 9.549 ms** | reComputer J40 series (J4012, Orin NX 16GB) |
| Frame captured to the verdict on the Modbus coil | **P50 10.56 ms** | reComputer J30 series (Orin Nano 8GB) |
| Defect detection accuracy (mAP50) | **0.7577** | reComputer J40 / J30 series |
| Precision / recall at the 0.35 deploy threshold | **P 0.7652 / R 0.6969** | reComputer J40 series |
| Streams one host carries at a 10 FPS line rate | **8** (12 degrading, 24 failing) | reComputer J40 series |

Conditions: NEU6 validation set, 290 images (706 boxes), YOLOX-Tiny 640²
TensorRT fp16, end-to-end sampled 3000 times at 10 FPS. The reComputer R2000
series with the Hailo-8 option runs the same chain at P50 11.61 ms /
P99 16.63 ms and mAP50 0.7091.

Accuracy varies widely by defect class — scratches 0.9685, pitted surface
0.9301, but crazing only 0.3603 — so check the classes you actually care about
before sizing a line on the headline score. Raising the threshold from 0.35 to
0.6 moves precision to 0.865 and recall down to 0.5807.

**What these numbers cover.** Every validation image contains a defect, so the
frame-level false-alarm rate (clean frames judged NG) has to be measured on
your own line images. The measured input was a synthetic 640×640 / 10 FPS video
stitched from validation images; add the camera's own capture and encode time
to the end-to-end figures.

## Detector selection

YOLOX-Tiny is the default — the only track benchmarked on Jetson and the only
one shipped on the Hailo preset. Two NMS-free DETR tracks (D-FINE-S and
RT-DETRv2-S, both Apache-2.0) can be selected via "model.track" in
"config/config.json": they miss fewer frames entirely (0-1 vs YOLOX's 7) at
roughly 2-3× the CPU latency. Hailo-8 supports neither DETR track, so the
reComputer R2000 preset stays on YOLOX-Tiny.

## Unsupervised Anomaly Detection (Optional)

An optional second model (anomalib EfficientAD-S, Apache-2.0) trains on
defect-free (OK) reference images only and flags frames that look unlike the
reference set — including defect types the detector never learned to name. It
never replaces the detector's verdict: "anomaly_score" is an independent MQTT
field and is never merged into the top-level "verdict".

How to read it: treat it as a **pixel/region-level** signal (a heatmap of what
looks unusual), not as a frame-level normal/abnormal switch — the image-level
score has no discriminative power when the OK references and the inspected
images come from different sources. Before enabling "anomaly.enabled", collect
your own OK samples with the real inspection camera and recalibrate
"anomaly.threshold".

## Output Interfaces

| Output | Where | Content |
|---|---|---|
| Verdict | Modbus TCP port 502, unit 1, coils 0-1 | Coil 0 NG / coil 1 OK, mutually exclusive, written after the registers |
| Verdict detail | Modbus TCP port 502, unit 1, HR 0-7 | Class ID, defect count, primary box cx/cy/w/h normalised ×10000, heartbeat as two words of Unix seconds |
| Detections | MQTT port 1883, topic "<device-name>/inspection/<stream-id>/results" | One JSON per frame: verdict, reasons, defect count, and each box's class, score and normalised bbox |
| Live view | HTTP port 8080, "/preview.mjpg", "/healthz", "/events", "/snapshot.jpg" | MJPEG preview with boxes, health counters, recent verdicts |

"<device-name>" and "<stream-id>" are filled in by you during deployment, so
several lines can share one broker and one device can serve several cameras.
"stream_id" is also inside the payload, so downstream consumers know the source
without parsing the topic.

## Deployment Comparison

**IP camera + reComputer J30 / J40 (Orin)** is the benchmarked path; most
numbers come from a J40 (Orin NX 16GB), and the J30 (Orin Nano 8GB) is
separately benchmarked for accuracy and latency. The TensorRT engine is built
on the device during deployment and is tied to that GPU architecture and
TensorRT version.

**IP camera + reComputer R2000 (Hailo-8)** is the cheaper path: measured on the
same Hailo-8 platform at 46.14 FPS full pipeline and mAP50 0.7091. Three ABI
gates have to pass on the device first (Python minor version, the HailoRT
driver/user-space/firmware trio, and "force_desc_page_size=4096"); the
deployment steps check each one.

## Usage Notes

- **The threshold is a business decision.** 0.35 is the deploy value; at 0.6
  precision goes 0.765→0.865 while whole-frame misses grow from 7 to 39 of 290
  frames.
- **Measure the false-alarm rate on your own line images.** Every validation
  image contains a defect, so the dataset cannot say how often a clean strip
  gets judged NG.
- **One deployment configures one camera.** The runtime supports multiple
  streams (8 stable on Orin NX), but the deploy steps configure one; add the
  rest to the on-device "streams" list and restart the container.
- **Multiple streams share one Modbus register bank.** With several streams the
  latest verdict wins; per-stream results come from MQTT.
- **The stream ceiling is the single-threaded inference loop, not the GPU.**
  From 12 streams up, total throughput pins at ~110 FPS while the engine itself
  needs only 5.3-5.6 ms (~178 FPS).
- **The measured input is a synthetic video, not a camera.** Stress-test with
  your own video source before fixing a stream count.
- **The MQTT broker in this package is for debugging (anonymous).** A
  production line should point at a broker with credentials.

## Licensing note

The runtime code and every model track (YOLOX, D-FINE, RT-DETRv2,
EfficientAD-S) are Apache-2.0; no Ultralytics code or weights are used, so
there is no AGPL obligation. The license of the NEU-DET repost used as training
data is still being confirmed — see the note at the top of this page.
