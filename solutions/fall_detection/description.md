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

Final deployed comparison on GMDCSA-24 Subject 4 (27 clips, 12 falls / 15
everyday activities):

| Runtime | Pose model | Accuracy | Fall recall | Specificity | F1 | Mean latency |
|---|---|---:|---:|---:|---:|---:|
| reCamera 2002 | YOLO11n INT8 | 74.1% | 83.3% | 66.7% | 74.1% | 1.75 s |
| reComputer J | YOLO11s FP16 | 81.5% | 83.3% | 80.0% | 80.0% | 1.47 s |
| reComputer J | YOLO11m FP16 | 85.2% | 100% | 73.3% | 85.7% | 1.26 s |


A second, separately frozen result now exists for the NPU platforms. It is **not
directly comparable to the table above**: those rows measure the deployed state
machine — the alert you actually receive over MQTT — while these measure the
temporal gate, the moment the model first sustains its probability threshold.
The gate fires earlier and is the more flattering of the two, so the deployed
figure for these boards is still unmeasured.

| Runtime | Pose model | Measured at | Accuracy | Fall recall | Specificity | F1 | Mean latency |
|---|---|---|---:|---:|---:|---:|---:|
| reComputer RK3576 | YOLO11n FP16 | temporal gate | 88.9% | 100% | 80.0% | 88.9% | 1.49 s |
| reComputer RK3588 | YOLO11n FP16 | temporal gate | 88.9% | 100% | 80.0% | 88.9% | 1.53 s |
| reComputer R (Hailo) | YOLOv8s | temporal gate | 88.9% | 100% | 80.0% | 88.9% | 1.61 s |

Each of these runs on a profile trained and frozen on that platform's own pose
traces, so unlike earlier builds the figures describe the board rather than a
model borrowed from another one.

On an independent external set (RealBiomFall, 34 fall-only clips) recall drops on
both configurations measured there — 58.8% on reCamera and 52.9% for the deployed
YOLO11m on reComputer J. YOLO11s was not measured on that set. The limiting factor
is pose coverage: in long shots and heavy occlusion the person is barely detected
at all. The table above covers a framed indoor view at close-to-medium range; the
external figures cover long shots and occlusion.

Known weak cases in every runtime: long shots, occlusion, low light, and
floor-level activities that look like falls (push-ups, lying down to play with a
pet). The detector must also observe the *transition* — starting it while someone
is already on the floor reports the posture but raises no event.

**Run a site acceptance test with representative falls and normal activity before
you enable any notification workflow, and keep another means of summoning help.**

## Output Interfaces

| Output | Where | Content |
|---|---|---|
| Fall results | MQTT port 1883, topic `recamera/fall-detection/results` | Per-frame JSON: aggregate state plus one entry per tracked person |
| Availability | MQTT port 1883, topic `recamera/fall-detection/status` | `online` / `offline`, retained |
| Home Assistant | MQTT discovery under `homeassistant/` | Fall sensor, state, event ID, person count |
| Video | RTSP port 8554 `/live0` on reCamera, or your own IP camera | The scene the detector is watching |

The reComputer preset takes more than one camera from a single box and appends the
stream id to the topic (`recamera/fall-detection/results/cam-01`), so each camera
stays separable downstream. This solution was verified end to end on one stream;
the upstream project suggests starting at 4 streams with YOLO11s on Orin Nano, or
3 with YOLO11m on Orin NX, at 15 FPS, then measuring your own cameras, codec and
scene density before committing to a count.

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

**reComputer R (Hailo)** runs a native C++ hot path on a Hailo-8, holding a steady
15 FPS per stream with low host CPU. Pick either when you already run that
hardware; both now have a frozen temporal-gate result, though neither has had its
deployed state machine measured separately.

## Usage Notes

- **Framing decides accuracy.** The figures above come from a fixed indoor view at
  close-to-medium range with shoulders and hips visible. A ceiling-down view, a
  long corridor shot or heavy furniture occlusion will perform worse.

  ![Camera placement: a side or corner view at 2–3 m works; straight-down and long-shot or occluded views do not.](gallery/camera-placement.svg)
- **The fall has to happen on camera.** Starting the detector on someone already
  lying down reports the posture but raises no event.
- **An MQTT broker must be reachable on port 1883.** reCamera uses its own local
  broker; the reComputer preset brings one up alongside the detector.
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
