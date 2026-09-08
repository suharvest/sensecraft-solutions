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

**An optional alarm panel.** The event stream on its own is a feed. The panel
turns it into an alarm someone is accountable for: a site overview of rooms,
cameras and zones with a 24-hour alarm trend; zones drawn on the live picture of
each camera; a no-person and a no-motion timeout per zone; an evidence window; an
operator who confirms, dismisses or marks handled; an SQLite audit trail; and a
webhook whose payload carries no video. It is a service inside the same compose
stack on the reComputer J30 / J40, RK and R2000 presets, and an optional extra box on the two
reCamera presets. The section "Alarm panel" below covers what it does.

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
| Fall recall, frozen temporal gate | **100%** | Same host, 27-clip held-out set |
| Everyday activity not raising an alert | **80%** | Same host and set |
| Streams one host carries at 15 FPS, MQTT disabled | **16** | reComputer R2000 (Hailo-8) |
| Fall to alert received with the alarm panel in the loop | **P50 2.83 s** | reComputer R2000 (Hailo-8), shortened confirmation windows |

Accuracy lands between 74.1% and 88.9% across the frozen platform profiles and
mean alert latency between 1.22 s and 1.75 s, so **choose hardware by stream
count, not by accuracy**. Stream count follows the host: 1 on reCamera Pro and
reComputer RK3576, 5 on reComputer RK3588, 8 on reComputer J30, 9 on reComputer
J40, 16 on reComputer R2000 with Hailo-8. Those are the highest loads tested
from a real 640x640 H.264 15 FPS source and are a starting point for your own
load test, not a rated capacity.

The panel row is the whole chain — camera to detector to panel to webhook — with
the confirmation windows shortened to 1 s of evidence plus 1 s of auto-confirm.
With the shipped defaults (5 s plus 60 s) the same path takes just over a minute,
which is the confirmation design rather than overhead. The panel's notifier also
stops after 5 sends per 10 minutes, by design.

The RK and Hailo rows measure the frozen temporal gate, not full deployed
state-machine accuracy, and the Hailo capacity run had MQTT disabled. The
held-out set has 27 clips, so one clip moves a metric by 3.7 percentage points.
Results were frozen on 2026-09-05.

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
| Alarm list and actions | HTTP port 8080, "/api/alarms" and the page at "/" — alarm panel only | Alarm records with state, zone, stream, timestamps and operator; confirm, dismiss and mark handled |
| Notification | HTTP POST to your webhook URL — alarm panel only | Alarm id, kind, zone, stream, timestamp, operator, plus an idempotency header — no snapshot, no video |
| Alarm bus (optional, off) | MQTT port 1883, topic "eldercare/alarm/<zone-id>" — alarm panel only | Same payload as the webhook |

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
is frozen.

**Where the alarm panel runs** differs by preset. On reComputer J30 / J40, RK and R2000 it is
a service in the same compose file as the detector, brought up by the same deploy
step and reachable on port 8080 of that device. On reCamera 2002 and reCamera Pro
the camera cannot host it — the detector there is a native process or an App
Center application, and the camera offers no filesystem, SQLite or web server for
it — so the panel is an optional extra step onto a separate box that needs no AI
accelerator: a reComputer R1000 Series, or a machine you already run. Skip that
step and the cameras behave as before, publishing MQTT events and nothing else.

## Alarm panel

**A site overview, not just a list.** The first page counts rooms, cameras and
zones, draws a 24-hour alarm trend split by type, and gives each room a card with
its own live thumbnail and its open-alarm count. A room whose camera is
unreachable reads unknown and stream-lost with the time of the last frame,
instead of reading normal.

**Zones drawn on the live picture.** Zone rectangles are drawn over the camera's
own WebRTC stream in the browser, not typed as coordinates. Coordinates map to
the picture rather than to the container, so a 4:3 stream in a 16:9 box keeps its
letterbox bars outside the rectangles. Saving bumps a configuration version and
adds a row to the change log; if another administrator saved first, the page gets
a 409 and a reload prompt rather than silently overwriting their work.

**Three alarm kinds, per zone.** A fall arrives as an event from the detector. An
empty zone and a motionless person are decided in the panel, from "person_count"
and from the displacement of each tracked person's bounding-box centre. Every zone
gets its own "no_person_timeout" and "no_motion_timeout", because a bathroom and a
bedroom are not the same problem.

**A confirmation step, not just a push.** An alarm sits in an evidence window
(5 s), then waits for an operator (60 s). Confirm and dismiss are both recorded
against the operator who pressed them. If nobody answers within the window the
default is to treat it as real and notify — configurable to the opposite through
"statemachine.confirm_timeout_action".

**Delivery you can audit.** Confirmed alarms must be notified within 5 s or the
alarm moves to "escalated" and stays there, retrying every 30 s. "escalated" never
reverts to "notified" even when a retry succeeds, so the audit trail shows that
the deadline was missed. Every notification carries an idempotency key
("zone:kind:event_timestamp:global_event_id"), and both the alarm table and the
notification table have unique indexes on it — replays and retries cannot create a
duplicate alarm or a duplicate delivery. One measured outage run recovered 3 of 3
queued alarms with no duplicates, the first 96 ms after the endpoint came back.

**Notifications with no video in them.** The payload is the alarm id, kind, zone,
stream id, timestamp and operator. No snapshot, no clip. Snapshot capture exists as
a configuration switch ("web.snapshot_enabled") and is off, with nothing
implemented behind it yet.

**Local by default.** No cloud dependency anywhere in the path. Events, state
transitions, operators and delivery receipts are kept 90 days; media, if it is ever
enabled, 7 days with a daily purge.

**The panel is not a medical device and not a certified emergency-response
product.** It does not diagnose, treat, or replace a carer's judgement. An alarm is
a prompt; the decision and the response stay with a person.

### Voice check-in (optional)

Off by default, and off changes nothing about the rest of the solution. When
enabled, a raised fall alarm makes the panel speak a prompt into the room — "are
you all right? please answer" — and listen for a few seconds, in parallel with the
five-second evidence window rather than after it.

A call for help, no answer at all, or an answer nobody can read confirms the alarm
immediately and skips the remaining operator window. "I'm fine" does *not* close
the alarm by default: it flags the alarm for review and lets the normal timing
continue. Set "on_ok: dismiss" to close it instead. The asymmetry is deliberate — a
mis-heard "I'm fine" would suppress a real fall, while a confirmed alarm nobody
needed costs an operator a few seconds. For the same reason a distress word beats a
safe word in the same sentence, and a phrase the keyword lists do not recognise
confirms rather than waits.

Audio hardware is a USB microphone and speaker on the box running the panel, plus
an OpenVoiceStream instance for TTS and streaming ASR. The cameras are not the
audio path: neither reCamera model has a confirmed usable microphone, and the
SG2002 cannot host local ASR at all. TTS and ASR compete with the detector for CPU,
accelerator and memory on a shared box — one session at a time, a pre-generated
prompt, and a fail-safe confirm on any OVS timeout are what keep that contention
from costing an alarm.

**Privacy.** Audio is never written to disk. Raw PCM lives in memory for one
listening window and is released when the verdict is produced. Persisted are the
verdict, the confidence, the latency and the transcribed text; setting
"store_transcript: false" drops the text as well, leaving only the verdict in the
audit trail. Notifications gain the same fields and still carry no snapshot and no
video.

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
- **Zones are normalised rectangles over the camera frame.** Moving or re-aiming a
  camera invalidates the zone layout without any error being raised — the rectangle
  still exists, it just covers a different part of the room. Re-check the zones
  after any physical change.
- **"no_motion" will fire during sleep** unless the zone excludes the bed or the
  timeout is longer than a normal nap. Motion is the displacement of a tracked
  person's bbox centre above "motion_threshold" (0.02 normalised, default), not
  optical flow or keypoint velocity — small movements under a blanket do not count.
- **The no-person timeout needs the detector to publish empty frames.** A detector
  that sends nothing when nobody is in view starves that timeout of input. The
  Jetson config ships "publish_empty_frames: true" and the Hailo runtime has no
  such switch and needs none. On an RK board, if falls raise alarms but no-person
  alarms never do, confirm the detector still publishes with nobody in view.
- **Occlusion can raise a false "no_person".** A zone only re-arms after the person
  is seen again, so one occlusion produces one alarm rather than a repeating series
  — but it still produces one.
- **Telegram and email are interface stubs** in the panel. Selecting them raises an
  error that lands in the retry queue rather than silently dropping the
  notification, which is the intended behaviour but is not a working channel.
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
