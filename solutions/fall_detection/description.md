## What it does

Turn a camera into a sensor that reports "someone has fallen." The camera watches
a fixed indoor area, decides on the device whether a person went down, and pushes
an event to whatever you already use for alerting — Home Assistant, a nursing-call
system, an NVR, or your own service.

No video leaves the device unless you ask for it. Pose estimation, the fall
decision and the event history all run locally; what goes out on the network is a
small JSON message.

## What you get

**A fall event stream.** Each person is followed separately, with an ID that stays
with them as they move around the room, and a state that goes from normal, through
suspected, to fallen and then recovering. One "this is a new fall" flag fires on
the transition only, so an automation can trigger on it once instead of firing for
as long as someone is on the floor. Field names are in the interface table below.

**Ready-made Home Assistant entities.** Both presets publish MQTT discovery
configs, so a fall sensor, the current state, the event ID and a person-present
sensor appear in Home Assistant without any manual YAML.

**A live view for commissioning.** The deployment ends with a preview inside this
app: the video with the skeleton, the per-person state and the evidence count
drawn on top, so you can confirm the camera sees what it needs to before you wire
up any notifications.

## Where it fits

- **Assisted-living and home care** — an unattended bathroom, hallway or bedroom
  where a fall would otherwise go unnoticed until the next check.
- **Existing camera estates** — the reComputer preset consumes ordinary RTSP, so
  cameras you already own gain fall detection without being replaced.
- **Home Assistant automations** — a fall entity that turns on a light, sends a
  push notification, or starts a call.

## How well it works

These are engineering benchmarks on public datasets, **not a medical or
life-safety certification**. Subjects 1–2 trained the temporal model, Subject 3
froze the configuration, and Subject 4 was read once as an untouched test set.

**How it was tested**

- GMDCSA-24 v2.1, split by person: Subjects 1–2 train the temporal model,
  Subject 3 selects thresholds and freezes the configuration, and Subject 4 is a
  held-out test set **read exactly once**.
- Subject 4 drops the 10 clips previously used for pipeline smoke tests, leaving
  27 (12 falls / 15 everyday activities).
- Video is resampled to 15 FPS; tracking and temporal state reset before each clip.
- An alert more than 0.5 s before the annotated start of the fall counts as a false
  alarm, not a hit.
- Every platform re-extracts traces from its own real pose output and retrains and
  freezes its own temporal weights. Nothing is borrowed across platforms.

**Result**

Averaged over the six frozen configurations: **85.8% accuracy, 95.8% fall recall,
77.8% specificity, 85.7% F1, 1.4 s mean alert latency.** Individual configurations
fall between 77.8% and 88.9%.

**Why there is no per-platform comparison table**

27 clips resolve to 3.7 percentage points — one clip is one step — so every
configuration that reaches "all 12 falls caught, 3 of 15 everyday clips
false-alarmed" lands on the same 88.9%. All platforms false-alarm on the same two
clips, ADL/06 and ADL/07, which puts the limit in the fall-decision layer rather
than the pose model; the temporal state machine is one shared design. Model size
does not track the result either — the YOLO11s configuration scores below YOLO11n
ones. Separating the platforms would need a larger, harder test set.

### Performance

One model across every device: **YOLO11n-Pose at 640²**; per-frame is accelerator
inference only (excluding RTSP decode and postprocessing), aggregate is the highest total frame
rate measured across 1–6 concurrent contexts. Different precisions are not mixed into one
table.

**FP16**

| Runtime | Pose model | Per-frame | Aggregate | Inference-bound streams | Suggested streams |
|---|---|---:|---:|---:|---:|
| reComputer RK3576 | YOLO11n | 56.1 ms | 29.2 FPS | 1 | 1 |
| reComputer RK3588 | YOLO11n | 51.4 ms | 51.4 FPS | 3 | 1 |
| reComputer J (Orin Nano) | YOLO11n | 3.7 ms | 270.7 FPS | 18 | 7 |
| reComputer J (Orin NX) | YOLO11n | 3.3 ms | 306.2 FPS | 20 | 8 |

**INT8**

| Runtime | Pose model | Per-frame | Aggregate | Inference-bound streams | Suggested streams |
|---|---|---:|---:|---:|---:|
| reCamera 2002 | YOLO11n | 53.0 ms | 10.0 FPS | 1 | 1 |
| reCamera Pro | YOLO11n | 35.9 ms | 18.1 FPS | 1 | 1 |
| reComputer RK3576 | YOLO11n | 36.2 ms | 42.1 FPS | 2 | 1 |
| reComputer RK3588 | YOLO11n | 29.8 ms | 90.4 FPS | 6 | 2 |
| reComputer R (Hailo-8) | YOLOv8s ▲ | 6.9 ms | 393.9 FPS | 26 | 16 |
| reComputer J (Orin Nano) | YOLO11n ＊ | 2.7 ms | 363.9 FPS | 24 | 9 |
| reComputer J (Orin NX) | YOLO11n ＊ | 2.5 ms | 408.0 FPS | 27 | 10 |

▲ **This row uses the s size because n is slower on this accelerator.** The official
Model Zoo v2.15 hailo8 directory ships pose only as `yolov8s_pose` and `yolov8m_pose`,
with no n-size pose model at all. We compiled our own YOLO11n-Pose with the Hailo
Dataflow Compiler 3.31.0 (640², INT8, 64 GMDCSA calibration frames) and measured
**9.01 ms / 92.2 FPS** on the same board against the s build's 6.87 ms / 393.9 FPS:
**per-frame latency is the same order (+31%); the 4.3x gap is in throughput.** The
compiler split 11n across **3 contexts**, so weights are swapped once per frame, while
the Model Zoo s build is single-context and keeps its weights resident.

Measured against what this solution actually needs — one stream at 15 FPS — the n
build's 92.2 FPS still leaves roughly 6x headroom, so the gap constrains stream
density rather than single-stream deployment. The s size is kept because on this board
it is both faster and larger, leaving nothing to gain from the swap. The n figure
describes how that HEF was allocated, not the ceiling for 11n on Hailo-8.

＊ **Jetson INT8 is not deployable today and is listed for speed reference only.** The
engine is built with `trtexec --int8` and no calibrator or calibration set, so its
dynamic ranges are arbitrary: the kernel timing is real, the detections are not.
Upstream's `build_engine.sh` passes only `--fp16`; a real INT8 path needs a calibrator
and calibration set implemented in the project, then the temporal weights re-frozen on
INT8 pose output. RK INT8 is the opposite — calibrated on 240 GMDCSA frames and
identical to FP16 detection-for-detection on frames held out of that set, hence
deployable.

**Both tables use a synthetic blank 640 frame** (the same basis as the existing FP16
baselines) and time the accelerator only. Real footage is slower, because anything
detected has to go through raw-head decode, DFL, keypoints and NMS:

| Platform | Pose model | Accelerator inference | Real-footage pipeline | Pre/postprocess delta |
|---|---|---:|---:|---:|
| reCamera 2002 | YOLO11n INT8 | 52.74 ms ◇ | 53.23 ms | 0.012 ms |
| reCamera Pro | YOLO11n INT8 | 35.2 ms | 36.6 ms | 1.4 ms |
| reComputer RK3576 | YOLO11n FP16 | 69.6 ms | 70.8 ms | 1.2 ms |
| reComputer RK3588 | YOLO11n FP16 | 54.4 ms | 54.8 ms | 0.4 ms |
| reComputer R (Hailo-8) | YOLOv8s INT8 | 6.9 ms | 8.77 ms | 1.9 ms |
| reComputer J (Orin Nano) | YOLO11n FP16 | 3.7 ms ◆ | 5.57 ms | 1.9 ms |
| reComputer J (Orin NX) | YOLO11n FP16 | 3.3 ms ◆ | 5.18 ms | 1.9 ms |

"pipeline" is inference plus preprocess plus raw-head decode / DFL / keypoints / NMS. It
excludes RTSP decode, tracking, the temporal MLP and MQTT. The Orin NX figure is from 400
measured frames (264 of them containing people), p95 5.24 ms; the Orin Nano figure is from
1359 frames (1209 containing people), median 5.56 ms and p95 5.62 ms, with a single 88.9 ms
first-frame warm-up outlier removed (the next largest is 8.21 ms). Both Jetsons carry the
same 1.9 ms pre/postprocess delta. The reCamera Pro figure is from 382 frames, only 3
of which contained a person, so its 1.4 ms delta is a floor: it shares the RKNN path with the
RK boards, where postprocess grows with people (2.7 ms on a 4-person frame against 0.4 ms
blank on RK3576).

◇ **The reCamera 2002 figure is not accelerator-only, but it is now split as finely as this
platform allows.** The app carried a single detectAll-wide timer at integer-millisecond
resolution; it now reports microsecond-resolution stages (`model_run_ms`, `postprocess_ms`,
`pipeline_ms`, with `inference_metric` naming the span), verified on hardware.

Two samples of 300 frames each, one empty and one holding a person throughout:

| | empty | with a person |
|---|---:|---:|
| `model_run_ms` | 52.65 ms | 52.74 ms |
| `postprocess_ms` | 0.002 ms | 0.012 ms |
| `pipeline_ms` | 53.13 ms | 53.23 ms |

The original `inference_time_ms` averages 53.02 and 53.03, matching the frozen 52.96
baseline, so this measurement stays comparable with the history. Postprocess grows sixfold
with a person in frame yet is still only 0.012 ms — the same shape as Jetson and Hailo,
because decode walks a fixed anchor count regardless of how many people are present.

**Those 52.65 ms still include letterbox and raw-head decode** — all three run inside one
sscma-micro `model_->run()` call with no seam the app can see, so splitting further means
changing that upstream library. It is the narrowest inference span measurable here and is
**not** equivalent to Jetson's `trtexec` or RK's `rknnlite.inference()`.

This also corrects an earlier note. It said integer milliseconds were too coarse to resolve
a ~2 ms delta; measured, the app-side postprocess is **0.002 ms**, 0.004% of the frame, so
that delta does not exist.

Sampling: 300 frames each, captured with the scene empty and with one person present.

**reCamera Pro is the opposite case: its figure is accelerator-only and compares
directly.** Its runtime times `model.infer()` on its own (`kit/app.py:1258-1260`), with
letterbox before the start and raw-head decode after the end — exactly this table's
accelerator definition. The pipeline column comes from `pre+infer+post` in its own `metrics`
message (0.00 + 35.21 + 1.34), which matches this table's scope; the separate `pipeline_ms`
it publishes stops after tracking and the temporal decision and is therefore not used.

**That row is only comparable because the clocks were pinned.** Its NPU runs
`rknpu_ondemand` and sat at 800 MHz for 60 of 60 samples (ceiling 950), where inference
measures 43.1 ms. With `min_freq` raised to 950 MHz and the CPU governor set to
`performance` (1608 MHz) it measures 35.2 ms, matching the existing 35.89 frozen baseline.
**The same board differs by 23% on frequency bin alone.** The table uses the pinned figures;
the governors were restored afterwards. RK3576 and RK3588 held their top bin for 40 of 40
samples (950 / 1000 MHz) and are unaffected, Jetson is recorded at MAXN_SUPER, and Hailo has
no such layer.

**The reCamera 2002 row in the INT8 table above is still on a different basis** from the
RK, Jetson and Hailo entries: those are accelerator-only, while the 2002's 52.65 ms
includes letterbox and decode. The size of that gap is now known — app-side postprocess is
only 0.002 ms — so what separates them is letterbox and raw-head decode, not application
code. Closing it entirely would mean changing sscma-micro, which is outside this
solution.

**Whether postprocess scales with people differs by platform.** On RK3576 it is 2.7 ms for
a 4-person frame against 0.4 ms blank; on Jetson frames with and without people are
indistinguishable (NX 5.180 vs 5.187 ms; Nano 5.567 vs 5.556 ms), because YOLO11 decode walks a fixed 8400-anchor
head regardless of content and NMS over 0-2 boxes is free.

◆ The Jetson entry in that column is `trtexec` pure GPU compute with no host copies, while
the RK entries are `rknnlite.inference()` — different scopes by construction. The pipeline
column is the one that compares: on it, Jetson is roughly 11x faster than RK3588 and 14x
faster than RK3576.

Hailo's 8.77 ms is from 1951 measured frames (1849 containing people), p95 12.34 ms:
6.87 ms hardware inference, about 1.8 ms scheduling and output tensor transfer, and only
**0.052 ms** of raw-head decode + NMS (0.6% of the frame), plus 0.013 ms tracking. Its
decode barely moves with people (0.035 ms empty vs 0.053 ms with), behaving like Jetson
rather than RK, because the HEF emits low-cardinality output tensors.

▲ That platform's own `pipeline_ms` is a `pre_hailonet_to_hailonet_src` probe whose
timestamp is taken before `decodeYoloV8Pose()` and `tracker.update()`. To get a
like-for-like figure, `decode_ms` / `track_ms` / `pipeline_full_ms` were added upstream in
`platforms/rpi-hailo/src/main.cpp` as new fields, leaving the original field and its
`latency_metric` unchanged. The measurement then showed the original metric already covers
99.4% of the per-frame cost, so the two are interchangeable in practice.

**How to read the stream counts.** "Inference-bound" is aggregate ÷ 15 FPS — the
accelerator's theoretical ceiling. "Suggested" discounts it: measured end-to-end
throughput on RK reached only 28–44% of the inference bound, because RTSP decode,
tracking, the state machine and MQTT also consume CPU and memory bandwidth. Start
from the suggested figure and load-test with your own cameras, codec and scene
density.

The two RK boards appear in both tables, which gives the exchange rate between the
precisions: INT8 is 1.5–1.7× faster and matches FP16 detection-for-detection on
held-out frames.

**Measurement conditions**: both Jetson rows were taken with co-resident workloads
stopped. That step is necessary — when a co-resident workload uses the accelerator the
ranking inverts: Orin NX measured 264.9 FPS while running its own inference workload,
*below* Orin Nano and the opposite of their relative capability; stopped, it is
306.2 FPS. Orin Nano measured identically either way (270.5 vs 270.7), because its
co-resident services never touch the GPU.

reCamera 2002 and Pro are INT8 only. reComputer R (Hailo) runs the official Model Zoo YOLOv8s-Pose INT8.

**What the presets deploy today:** Jetson FP16, RK FP16, reCamera 2002 and Pro INT8.
The RK INT8 weights were converted for this comparison and are not shipped yet —
the temporal weights need re-checking before that switch.

Both Jetson boards hold essentially flat aggregate throughput from 1 to 6 concurrent
contexts, so concurrency shares one GPU budget rather than multiplying it.

**Measured multi-stream capacity (YOLO11s-Pose FP16, runtime 0.1.0-rc2).** The
figures above are accelerator-only on YOLO11n. End-to-end stream density was
measured separately with the deployed YOLO11s configuration: 640x640 H264
15 FPS RTSP sources, 60 s windows, a stream counting as carried only when it
sustained at least 14.5 published FPS.

| Module | Max streams at 15 FPS | Aggregate FPS | GPU |
|---|---:|---:|---:|
| reComputer J (Orin Nano Super) | 8 | 119.6 | 91% |
| reComputer J (Orin NX Super) | 9 | 134.4 | 95% |
| Jetson AGX Orin 32G | 16 | 239.8 | 89% |

These supersede the earlier suggestion of 4 streams on Orin Nano and 3 on
Orin NX. Two changes in the `0.1.0-rc2` runtime account for the difference. The TensorRT
runner used to read its output back with a synchronous copy on the CUDA legacy
default stream, which acted as a device-wide barrier and held GPU utilisation
at 59–77% no matter how many streams were added; it now copies asynchronously
on each runner's own non-blocking stream. Above 7 streams the control plane
also shards itself across OS processes, because per-frame payload building,
JSON encoding and MQTT publishing contend for a single GIL. Both boards are
accelerator-bound at the counts above — adding streams past them lowers
per-stream FPS without raising the total.

Orin NX Super leads Orin Nano Super by 12% here, matching their 12% gap in
pure accelerator throughput (173.8 against 155.3 qps for this engine). Both
modules carry 1024 CUDA cores, and an FP16 GPU path uses neither the DLA nor
INT8, so the ratio their TOPS ratings suggest does not appear.

**Measured Hailo-8 multi-stream capacity (runtime `0.1.0-rc3`).** The same
640x640 H264, 15 FPS source and 14.5 FPS pass threshold were used. The default
YOLOv8s-Pose HEF is single-context and stays on the existing `hailonet` path.
The official Model Zoo v2.19 YOLOv8m-Pose HEF has three contexts; rc3 detects
that layout and switches to a shared direct-HailoRT batcher automatically.

| Pose model | Runtime path | Max streams at 15 FPS | Aggregate FPS |
|---|---|---:|---:|
| YOLOv8s-Pose | Single-context `hailonet` | 16 | 233.6 |
| YOLOv8m-Pose | Shared auto-batch | 5 | 75.0 |

At five M-model streams the device used 72.5% CPU, 234,368 KiB RSS and reached
63.9 C. The M-model gain came from full-batch padding and disabling scheduler
wait in the single shared runner; the official HEF was not recompiled. MQTT was
disabled during both capacity-boundary runs, so these figures describe the
video-to-tracker runtime rather than broker throughput. The deploy preset remains
single-stream and downloads the S model; rc3 can run the M HEF when `HEF_PATH`
points to it. A model selector and multi-camera form are deferred.

On an independent external set (RealBiomFall, 34 fall-only clips) recall drops on
both configurations measured there — 58.8% on reCamera and 52.9% for the deployed
YOLO11m on reComputer J. YOLO11s was not measured on that set. The limiting factor
is pose coverage: in long shots and heavy occlusion the person is barely detected
at all. The table above covers a framed indoor view at close-to-medium range; the
external figures cover long shots and occlusion.

## Output Interfaces

| Output | Where | Content |
|---|---|---|
| Fall results | MQTT port 1883, topic `<device-name>/fall-detection/results` (multi-stream presets use `.../results/<stream-id>`) | Per-frame JSON: aggregate state plus one entry per tracked person |
| Availability | MQTT port 1883, topic `<device-name>/fall-detection/status` | `online` / `offline`, retained |
| Home Assistant | MQTT discovery under `homeassistant/` | Fall sensor, state, event ID, person count |
| Video | RTSP port 8554 `/live0` on reCamera, or your own IP camera | The scene the detector is watching |

The reComputer preset takes more than one camera from a single box and appends the
**`<device-name>` is yours to choose.** It is the Device Name field in the deploy step,
defaulting to `recamera` on the reCamera preset and `recomputer` on the reComputer ones. It
is only the first topic segment, there to keep several installations apart on one broker, so
a room, floor or site name works just as well. `stream_id` is also carried in the payload, so
nothing downstream has to parse the topic to know where a message came from.

stream id to the topic (`<device-name>/fall-detection/results/cam-01`), so each camera
stays separable downstream. The deploy preset configures one stream; multi-stream
capacity was measured separately at 8 streams on Orin Nano Super, 9 on Orin NX
Super and 16 on AGX Orin with YOLO11s, plus 16 with Hailo YOLOv8s and 5 with
Hailo YOLOv8m, at 15 FPS (see Performance). Those runs
used one looped clip per stream, so measure your own cameras, codec and scene
density before committing to a count.

## Deployment Comparison

**reCamera 2002** is the whole thing in one device — camera, inference and MQTT in
a unit you mount and power. Pick it for a single room and the shortest path to a
working alert.

**IP camera + reComputer J** keeps the cameras you already have and puts the
detector on a Jetson Orin, taking more than one stream at once with a larger pose
model and higher measured accuracy. Pick it when the cameras exist, when you need
more than one view, or when the accuracy difference in the table above matters.

**reComputer RK** puts the detector on a Rockchip NPU board, now with a
board-native temporal profile and a hardware-accelerated video path. Measured
throughput with other workloads still running was about 8.6 FPS on RK3588 and
4.9 FPS on RK3576 end to end.

**reComputer R (Hailo)** runs a native C++ hot path on a Hailo-8. The default S
model carried 16 measured 15 FPS streams; the official M model carried 5 after
rc3 switched it to shared batching. The current deployment form still configures
one camera. Pick it when this hardware is already installed; its temporal profile
is frozen, but the deployed state machine has not been measured separately.

## Usage Notes

- **Framing decides accuracy.** The figures above come from a fixed indoor view at
  close-to-medium range with shoulders and hips visible. A ceiling-down view, a
  long corridor shot or heavy furniture occlusion will perform worse.

  ![Camera placement: a side or corner view at 2–3 m works; straight-down and long-shot or occluded views do not.](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/camera-placement-be3fb598.svg)
- **The fall has to happen on camera.** Starting the detector on someone already
  lying down reports the posture but raises no event.
- **Where the MQTT broker comes from depends on the preset.** reCamera 2002 runs
  its own; the reComputer presets bring one up alongside the detector; reCamera
  Pro ships none, so MQTT there is optional — point it at an existing broker to
  forward events, or leave it empty and read results on the camera's own page.
- **One vision app at a time on reCamera.** Installing takes the camera away from
  Node-RED and any other vision application.
- **Latency in the table is detection latency** — from the annotated start of the
  fall to the alert being published — measured in the offline evaluation harness.
  The separate FPS figures quoted for the pose engines are inference-core only.

## Licensing note

Upstream ships the runtime code under Apache-2.0, but that covers the code and
documentation only — the pose models keep their own terms, and the projects
require explicit licence acceptance before a model is downloaded.

The reference pose weights are distributed by Ultralytics under AGPL-3.0. Confirm
that licence suits your product, obtain a commercial licence, or substitute a
compatibly-licensed pose model before shipping a closed commercial deployment. The
runtime itself is model-agnostic within the documented output contract.
