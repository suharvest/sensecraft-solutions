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

**Results**

| Frontend/profile | Accuracy | Recall | Specificity | F1 | Mean alert latency |
|---|---:|---:|---:|---:|---:|
| reCamera CVI baseline | 74.1% | 83.3% | 66.7% | 74.1% | 1.75 s |
| Jetson YOLO11s optimized | 81.5% | 83.3% | 80.0% | 80.0% | 1.47 s |
| Jetson YOLO11m optimized | 85.2% | 100% | 73.3% | 85.7% | 1.26 s |
| Jetson YOLOv8m mixed INT8/FP16 repaired | 88.9% | 83.3% | 93.3% | 87.0% | 1.43 s |
| RK3576 native temporal gate | 88.9% | 100% | 80.0% | 88.9% | 1.49 s |
| RK3588 native temporal gate | 88.9% | 100% | 80.0% | 88.9% | 1.53 s |
| reCamera Pro production fallback on Pro traces | 81.5% | 91.7% | 73.3% | 81.5% | 1.22 s |
| reCamera Pro native experiment | 70.4% | 75.0% | 66.7% | 69.2% | 1.47 s |
| Hailo-8 native temporal gate | 88.9% | 100% | 80.0% | 88.9% | 1.61 s |

The clean historical test has 27 clips, so one clip changes a metric by 3.7
percentage points. RK and Hailo rows measure the frozen temporal gate and are not
full deployed-state-machine accuracy. The repaired YOLOv8m result is regression
evidence on the same 27 clips, not a pristine one-shot holdout publication: its
calibration and fitting exclude Subject 4, but earlier failed-M investigations had
already observed that subject. The historical YOLO11m FP16 row remains the clean M
baseline. The temporal model itself remains FP32; INT8 names the pose frontend.

### Performance
Capacity now uses real RTSP input rather than synthetic blank tensors. Jetson and RK
passing routes had to publish at least 14.5 FPS from the same 640×640 H.264, 15 FPS
source. Hailo used the same source and threshold but disabled MQTT during its capacity
boundary run; reCamera Pro is one-camera coverage below that threshold. Other inference
applications were stopped before these runs.

| Device | Pose frontend | Highest tested live/RTSP load | Next boundary / coverage |
|---|---|---:|---:|
| reComputer J (Orin Nano Super) | YOLO11s-Pose TensorRT FP16 | 8 streams, 14.95 FPS each | 9 streams, 13.36 FPS each |
| reComputer J (Orin NX Super) | YOLO11s-Pose TensorRT FP16 | 9 streams, 14.93 FPS each | 10 streams, 13.05 FPS each |
| reComputer RK3576 | YOLOv8s-Pose RKNN INT8, MPP NV12 path | 1 stream, 14.83–15.01 FPS | 2 streams, 12.81–12.83 FPS |
| reComputer RK3588 | YOLOv8s-Pose RKNN INT8, MPP NV12 path | 5 streams, 14.97–15.01 FPS each | 6 streams, 14.43–14.49 FPS each |
| reComputer R (Hailo-8) | YOLOv8s-Pose quantized HEF, 1 context | 16 streams, 14.52–14.57 FPS each; MQTT disabled | 17 streams below 14.5 FPS |
| reComputer R (Hailo-8) | YOLOv8m-Pose quantized HEF, 3 contexts | 5 streams, 14.98–15.02 FPS each; MQTT disabled | 6 streams below 14.5 FPS |
| reCamera Pro | YOLO11n-Pose RKNN INT8 | 1 live camera, 13.05 FPS | Higher loads not tested; 14.5 FPS SLA not met |

The Hailo S-to-M drop is larger than the increase in model operations. The official S
HEF is single-context, so its weights stay resident; the M HEF is split across three
compiled contexts and pays context switching and memory traffic. This is a property of
that compiled graph, not a universal Hailo rule. Jetson also slows down with M, but its
aligned accelerator time rises by about 2.1–2.2× rather than Hailo's throughput cliff.

Timing fields are kept separate because their boundaries differ:

| Device / model | Output cadence | Application inference | Named pipeline interval |
|---|---:|---:|---:|
| Orin Nano / YOLOv8s INT8 | 14.79 FPS | 5.35 / 5.40 ms mean/P95 | Not instrumented |
| Orin Nano / YOLOv8m mixed INT8/FP16 | 14.35 FPS | 9.92 / 9.98 ms mean/P95 | Not instrumented |
| Orin NX / YOLOv8s INT8 | 14.80 FPS | 4.82 / 4.86 ms mean/P95 | Not instrumented |
| Orin NX / YOLOv8m mixed INT8/FP16 | 14.35 FPS | 8.86 / 8.90 ms mean/P95 | Not instrumented |
| Hailo-8 / YOLOv8s | 15.00–15.06 FPS | Not exposed | 7.47–7.51 ms mean; 7.99–8.10 ms P95 |
| Hailo-8 / YOLOv8m | 14.12–14.16 FPS | Not exposed | 28.52–28.89 ms mean; 32.30–37.86 ms P95 |
| reCamera Pro / YOLO11n | 13.05 FPS | 35.89 / 39.36 ms mean/P95 | 77.80 / 85.99 ms mean/P95 |

Jetson's application interval includes preprocessing, copies, TensorRT, output copy and
pose parsing. Hailo S and M use different named probe boundaries. RK `inference_ms`
excludes video preprocessing, while RK `pipeline_ms` starts only after the source returns
a model-input frame and includes inference, pose decoding, tracking, temporal logic and
payload construction. None of those fields is relabelled as another platform's metric.

The RK capacity rows are the optimized benchmark profile, not the current one-camera
solution default. The deploy preset intentionally remains on its existing board-specific
YOLO11n FP16 model and temporal profile until the INT8 profiles complete the same frozen
accuracy release process. A separate RK3588 prototype moved DMA-BUF→RGA→RKNN into a native
hot stage; at five 15 FPS sources it reduced CPU from 144.6% to 43.7–44.5% and RSS from
495,488 KiB to about 157,000 KiB. That prototype omits pose decoding, tracking, temporal
logic and MQTT, so it is not a production capacity or accuracy claim.

These results were frozen on 2026-09-05. Synthetic blank-frame and accelerator-only
history remains available in the
[EdgeFallKit results ledger](https://github.com/suharvest/edgefallkit/blob/main/evaluation/RESULTS.md),
but is no longer presented here as route capacity.

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

**`<device-name>` is yours to choose.** It is the Device Name field in the deploy step,
defaulting to `recamera` on the reCamera preset and `recomputer` on the reComputer ones. It
is only the first topic segment, there to keep several installations apart on one broker, so
a room, floor or site name works just as well. `stream_id` is also carried in the payload, so
nothing downstream has to parse the topic to know where a message came from.

The reComputer runtime appends the stream ID to the topic
(`<device-name>/fall-detection/results/cam-01`), so routes stay separable downstream.
The deploy form configures one stream. Separate 15 FPS tests verified 8 streams on
Orin Nano Super, 9 on Orin NX Super, 1 on RK3576, 5 on RK3588, and 16/5 on Hailo
with YOLOv8s/YOLOv8m respectively (see Performance). Those runs
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

**reComputer RK** puts the detector on a Rockchip NPU board with a board-native
temporal profile and hardware video decode. On the optimized YOLOv8s INT8 benchmark
profile, RK3576 verified 1×15 FPS and RK3588 verified 5×15 FPS. The current deployment
keeps its existing single-camera YOLO11n FP16 profile.

**reComputer R (Hailo)** runs a native C++ hot path on a Hailo-8. The default S
model carried 16 measured 15 FPS streams; the official M model carried 5 after
the runtime switched it to shared batching. The current deployment form still configures
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
