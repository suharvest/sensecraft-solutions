## What it does

Take the MQTT event stream a fall detector already publishes and turn it into an
alarm someone is accountable for. The service watches three things per zone: a
fall event, a zone that has been empty too long, and a person who has stayed in
the zone without moving for too long. Each one opens an alarm, an operator
confirms or dismisses it on a one-page console, and the confirmed ones go out as
a webhook or an MQTT message.

Nothing about the detection changes. This solution contains no inference code —
it consumes the `fall_result_v1` payload from the
[EdgeFallKit](https://github.com/suharvest/edgefallkit) detector and reuses its
published images. What it adds is the part between "the camera saw something"
and "a person dealt with it": zones, timeouts, a state machine with an evidence
window, an SQLite audit trail, idempotent delivery, and a queue that survives the
notification endpoint being down.

## What you get

**Three alarm kinds, per zone.** A fall arrives as an event from the detector. An
empty zone and a motionless person are decided here, from `person_count` and from
the displacement of each tracked person's bounding-box centre. Every zone gets its
own `no_person_timeout` and `no_motion_timeout`, because a bathroom and a bedroom
are not the same problem.

**A confirmation step, not just a push.** An alarm sits in an evidence window
(5 s), then waits for an operator (60 s). Confirm and dismiss are both recorded
against the operator who pressed them. If nobody answers within the window the
default is to treat it as real and notify — configurable to the opposite through
`statemachine.confirm_timeout_action`.

**Delivery you can audit.** Confirmed alarms must be notified within 5 s or the
alarm moves to `escalated` and stays there, retrying every 30 s. `escalated`
never reverts to `notified` even when a retry succeeds, so the audit trail shows
that the deadline was missed. Every notification carries an idempotency key
(`zone:kind:event_timestamp:global_event_id`), and both the alarm table and the
notification table have unique indexes on it — replays and retries cannot create
a duplicate alarm or a duplicate delivery.

**Notifications with no video in them.** The payload is the alarm id, kind, zone,
stream id, timestamp and operator. No snapshot, no clip. Snapshot capture exists
as a configuration switch (`web.snapshot_enabled`) and is off, with nothing
implemented behind it yet.

**Local by default.** No cloud dependency anywhere in the path. Events, state
transitions, operators and delivery receipts are kept 90 days; media, if it is
ever enabled, 7 days with a daily purge.

## Where it fits

- **Assisted living and home care** — a bathroom or bedroom where a fall would
  otherwise go unnoticed, and where "nobody has been in the kitchen since
  yesterday evening" is as much a signal as the fall itself.
- **A site that already has fall detection** — the reCamera preset adds the
  alarm layer to cameras that are already running the detector, without touching
  them.
- **Anywhere an alarm needs a name against it** — the confirmation step and the
  audit store exist for handover between shifts and for after-the-fact review.

## How well it works

**This is not a medical device and not a certified emergency-response product.**
It does not diagnose, treat, or replace a carer's judgement. An alarm is a
prompt; the decision and the response stay with a person.

Everything in the first table below was measured on a laptop with a replayer
standing in for the cameras — **local replay, not a device**. The three target
devices were offline on the measurement date, so this package contains no
on-device numbers at all.

**How it was tested**

- Date 2026-09-05, run directory `evaluation/runs/2026-09-05-smoke/` in the
  eldercare-alarm project. Raw outputs under `raw/`, conditions in
  `conditions.yaml`, one `boundary.<metric>.yaml` per row.
- Host: MacBook, macOS 15 (Darwin 25.5.0), arm64. Loopback network. No
  container — the service ran directly.
- The evaluation scripts drive the real `AlarmService` — real state machine,
  real SQLite, real HTTP webhook — with only the camera replaced by a replayer.
  The numbers therefore describe the alarm path and **exclude inference time and
  any cross-machine network**.
- The state-machine windows were shortened for the run (1 s evidence + 1 s
  auto-confirm instead of the 5 s + 60 s defaults), so the absolute latency is a
  property of the run's configuration, not of a site.
- Every `boundary.*.yaml` has values in the `stable` tier only. `degrading` and
  `failure` are `null`: nothing was loaded to the point of degradation, so no
  boundary was found.
- `reproduced_by: null` — one person, one run, not independently reproduced.

**Results**

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Alert latency, event timestamp to notification sent | P50 2061 ms / P95 2093 ms | 5 fall replays, 15 FPS × 12 s each, 1 s evidence + 1 s auto-confirm window, single zone, single stream, loopback webhook | Local replay, not a device — `boundary.alert_latency.yaml` |
| No-person detection lateness, relative to the configured timeout | P50 65 ms / P95 77 ms late | 3 replays, 10 FPS × 11 s, 5 s timeout, 0.1 s tick, single zone, in-process (no broker) | Local replay, not a device — `boundary.inactivity.yaml` |
| Outage recovery, unique successful deliveries over queued | 3 of 3, 0 duplicates, first delivery 96 ms after recovery | Webhook endpoint returning 503 for 4 s, 3 alarms queued, 2 s retry interval | Local replay, not a device — `boundary.offline_recovery.yaml` |
| False alarms | 0 over 0.02 camera-hours | 72 s of quiet replay | Local replay, not a device — **0.02 camera-hours proves nothing about a false-alarm rate**; the intended run is 24 h |
| Robustness under darkening and occlusion | Not measured | Needs GMDCSA clips and on-device inference | Script exists, was not run |

Two of those rows deserve reading twice. The alert latency is essentially the sum
of the two configured windows plus about 60 ms of dispatch — with the shipped
defaults (5 s + 60 s) the same path would take just over a minute, and that is by
design, not overhead. The false-alarm row is 72 seconds of quiet; it is in the
table so it cannot be quoted as a rate.

**Detection accuracy is the base project's, not this one's.** This solution does
not detect anything itself, so its accuracy is whatever the EdgeFallKit detector
underneath it achieves. Those figures — GMDCSA-24 v2.1, split by subject, held-out
Subject 4 read once, 27 clips — are published in the Fall Detection solution's own
description (`solutions/fall_detection/description.md`, "How well it works"), where
the frozen per-platform accuracy runs from 74.1% to 88.9% and mean alert latency
from 1.22 s to 1.75 s. Quote those as base data with their conditions attached.
They are not re-measured here, and the alarm layer adds its own confirmation
windows on top of that detection latency.

**What has not been shown at all.** No on-device run. The Jetson
`publish_empty_frames` override, the Hailo per-frame publishing behaviour and the
exact reCamera topic and payload shapes are all still unverified on hardware, and
the detector image digests are recorded as pending in
`eldercare-alarm/release/PINNING.md`. Treat every deployment as a commissioning
exercise until you have watched a real alarm complete on your own site.
On 2026-09-06, an attempt on a standard (non-PoE) reCamera One over USB-RNDIS
could not complete the on-device loop: the SSH account has no passwordless
sudo, and every remaining step (releasing the camera from the running
`depth-estimation` App Center app, starting `fall-detection`, opening the
local mosquitto listener) requires root — see
`eldercare-alarm/evaluation/runs/2026-09-06-recamera-one/results.md`.

## Output Interfaces

| Output | Where | Content |
|---|---|---|
| Alarm list and actions | HTTP port 8080, `/api/alarms` and the page at `/` | Alarm records with state, zone, stream, timestamps and operator; confirm and dismiss |
| Notification | HTTP POST to your webhook URL | Alarm id, kind, zone, stream, timestamp, operator, plus an idempotency header — no snapshot, no video |
| Alarm bus (optional, off) | MQTT port 1883, topic `eldercare/alarm/<zone-id>` | Same payload as the webhook |
| Detector results (input) | MQTT port 1883, topic `<device-name>/fall-detection/results/<stream-id>` | The `fall_result_v1` stream this service consumes |

`<device-name>` is the first topic segment and is yours to choose in the deploy
form. `stream_id` is read from the message payload, never parsed out of the topic
— a broker rewrite or a bridge prefix cannot silently reroute a zone.

## Deployment Comparison

**IP Camera + reComputer J (Orin)** puts everything on one box: the detector, the
alarm service, the broker and the confirmation page. It takes the most streams of
the three and builds its TensorRT engine on the device during the first deploy,
which is why that deploy takes the longest. Pick it when the cameras exist and the
site has no gateway yet.

**IP Camera + reComputer R (Hailo)** is the same stack on a Hailo-8, with the
detector's hot path in native C++ and the pose model downloaded as a compiled HEF
instead of built on device. It is ABI-locked to HailoRT 4.21 — plugin, user
library and driver all move together — so pick it when that hardware and that
runtime version are already installed.

**reCamera + Alarm Gateway** is the only preset where this solution installs
nothing new for detection. The cameras already run it; the alarm service goes on a
gateway beside them. That step is manual: the gateway is whatever machine the site
already has, and the deploy form has no device class to address it with. Pick it
when the cameras are in place and adding a compute box is not.

## Usage Notes

- **Zones are normalised rectangles over the camera frame.** Moving or re-aiming
  a camera invalidates the zone layout without any error being raised — the
  rectangle still exists, it just covers a different part of the room. Re-check
  the zones after any physical change.
- **`no_motion` will fire during sleep** unless the zone excludes the bed or the
  timeout is longer than a normal nap. Motion is the displacement of a tracked
  person's bbox centre above `motion_threshold` (0.02 normalised, default), not
  optical flow or keypoint velocity — small movements under a blanket do not
  count.
- **The Jetson detector must publish empty frames.** Its default is not to send
  anything when nobody is in view, which starves the `no_person` timeout of
  input. The Orin preset sets `publish_empty_frames: true` for you; if you
  replace the shipped detector config with the device's own, set it again. The
  Hailo runtime has no such switch and needs none.
- **A single point of failure by construction.** One camera, one detector, one
  service. If the camera drops off the network there is no alarm about the
  absence of alarms; the retained MQTT availability topic from the detector is
  what to monitor for that.
- **Occlusion can raise a false `no_person`.** A zone only re-arms after the
  person is seen again, so one occlusion produces one alarm rather than a
  repeating series — but it still produces one.
- **The broker's origin differs by preset.** Orin and Hailo bring up their own
  alongside the detector; the reCamera gateway can either host one or point at
  the one the cameras already publish to. The bundled broker allows anonymous
  connections for commissioning on a trusted LAN — put credentials and TLS on it
  before the device is reachable from anywhere else.
- **The alarm service image is not published yet.** As of packaging it exists only
  as a local build from the upstream project's `docker/Dockerfile`. Build and
  retag it, or push it, before a deploy of the Orin or Hailo preset can succeed.
- **Telegram and email are interface stubs.** Selecting them raises an error that
  lands in the retry queue rather than silently dropping the notification, which
  is the intended behaviour but is not a working channel.

## Licensing note

The alarm service and this package are the upstream project's own code. The
detector underneath comes from EdgeFallKit, whose runtime code and documentation
are Apache-2.0 while the pose models keep their own terms — the reference weights
are distributed by Ultralytics under AGPL-3.0, and both projects require explicit
licence acceptance before a model is downloaded.

If you are shipping a closed commercial deployment, confirm that AGPL-3.0 suits
your product, obtain a commercial licence, or substitute a compatibly-licensed
pose model. The detector is model-agnostic within its documented output contract,
and this alarm service only ever sees that contract, so a model substitution does
not reach it.
