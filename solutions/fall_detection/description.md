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
life-safety certification**. GMDCSA-24 v2.1 is split by person: Subjects 1-2
train the temporal model, Subject 3 selects thresholds and freezes the
configuration, and Subject 4 is a held-out test set read exactly once — 27 clips
(12 falls / 15 everyday activities) at 15 FPS.

| What the site gets | Typical | Device |
|---|---|---|
| Fall to alert | **1.61 s** mean | reComputer R2000 (Hailo-8) |
| Fall recall | **100%** | Same host, 27-clip held-out set |
| Everyday activity not raising an alert | **80%** | Same host and set |
| Streams one host carries at 15 FPS | **16** | reComputer R2000 (Hailo-8) |

Accuracy lands between 74.1% and 88.9% across the frozen platform profiles and
mean alert latency between 1.22 s and 1.75 s, so **choose hardware by stream
count, not by accuracy**. Stream count follows the host: 1 on reCamera Pro and
reComputer RK3576, 5 on reComputer RK3588, 8 on reComputer J30, 9 on reComputer
J40, 16 on reComputer R2000 with Hailo-8. Those are the highest loads tested
from a real 640x640 H.264 15 FPS source and are a starting point for your own
load test, not a rated capacity.

The held-out set has 27 clips, so one clip moves a metric by 3.7 percentage
points. Results were frozen on 2026-09-05.

On an independent external set (RealBiomFall, 34 fall-only clips) recall drops
to 52.9%-58.8%. The limiting factor is pose coverage: in long shots and heavy
occlusion the person is barely detected at all. The table above covers a framed
indoor view at close-to-medium range.

## Output Interfaces

| Output | Where | Content |
|---|---|---|
| Fall results | MQTT port 1883, topic "<device-name>/fall-detection/results" (multi-stream presets use ".../results/<stream-id>") | Per-frame JSON: aggregate state plus one entry per tracked person |
| Availability | MQTT port 1883, topic "<device-name>/fall-detection/status" | "online" / "offline", retained |
| Home Assistant | MQTT discovery under "homeassistant/" | Fall sensor, state, event ID, person count |
| Video | RTSP port 8554 "/live0" on reCamera, or your own IP camera | The scene the detector is watching |

**"<device-name>" is yours to choose.** It is the Device Name field in the deploy step,
defaulting to "recamera" on the reCamera preset and "recomputer" on the reComputer ones. It
is only the first topic segment, there to keep several installations apart on one broker, so
a room, floor or site name works just as well. "stream_id" is also carried in the payload, so
nothing downstream has to parse the topic to know where a message came from.

The reComputer runtime appends the stream ID to the topic
("<device-name>/fall-detection/results/cam-01"), so routes stay separable downstream.
The deploy form configures one stream. Separate 15 FPS tests measured 8 streams on
Orin Nano Super, 9 on Orin NX Super, 1 on RK3576, 5 on RK3588, and 16/5 on Hailo
with YOLOv8s/YOLOv8m respectively (see Performance). Those runs
used one looped clip per stream, so measure your own cameras, codec and scene
density before committing to a count.

## Deployment Comparison

**reCamera 2002** is the whole thing in one device — camera, inference and MQTT in
a unit you mount and power. Pick it for a single room and the shortest path to a
working alert.

**IP camera + reComputer J30 / J40** keeps the cameras you already have and puts the
detector on a Jetson Orin, taking more than one stream at once with a larger pose
model and higher measured accuracy. Pick it when the cameras exist, when you need
more than one view, or when the accuracy difference in the table above matters.

**reComputer RK3576 / RK3588** puts the detector on a Rockchip NPU board with a board-native
temporal profile and hardware video decode. On the optimized YOLOv8s INT8 benchmark
profile, RK3576 reached 1×15 FPS and RK3588 5×15 FPS. The current deployment
keeps its existing single-camera YOLO11n FP16 profile.

**reComputer R2000 (Hailo)** runs a native C++ hot path on a Hailo-8. The default S
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
