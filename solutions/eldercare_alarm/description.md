## What it does

Take the MQTT event stream a fall detector already publishes and turn it into an
alarm someone is accountable for. The service watches three things per zone: a
fall event, a zone that has been empty too long, and a person who has stayed in
the zone without moving for too long. Each one opens an alarm, an operator
confirms or dismisses it on a one-page console, and the confirmed ones go out as
a webhook or an MQTT message.

Nothing about the detection changes. This solution contains no inference code —
it consumes the "fall_result_v1" payload from the
[EdgeFallKit](https://github.com/suharvest/edgefallkit) detector and reuses its
published images. What it adds is the part between "the camera saw something"
and "a person dealt with it": zones, timeouts, a state machine with an evidence
window, an SQLite audit trail, idempotent delivery, and a queue that survives the
notification endpoint being down.

## What you get

**Three alarm kinds, per zone.** A fall arrives as an event from the detector. An
empty zone and a motionless person are decided here, from "person_count" and from
the displacement of each tracked person's bounding-box centre. Every zone gets its
own "no_person_timeout" and "no_motion_timeout", because a bathroom and a bedroom
are not the same problem.

**A confirmation step, not just a push.** An alarm sits in an evidence window
(5 s), then waits for an operator (60 s). Confirm and dismiss are both recorded
against the operator who pressed them. If nobody answers within the window the
default is to treat it as real and notify — configurable to the opposite through
"statemachine.confirm_timeout_action".

**Delivery you can audit.** Confirmed alarms must be notified within 5 s or the
alarm moves to "escalated" and stays there, retrying every 30 s. "escalated"
never reverts to "notified" even when a retry succeeds, so the audit trail shows
that the deadline was missed. Every notification carries an idempotency key
("zone:kind:event_timestamp:global_event_id"), and both the alarm table and the
notification table have unique indexes on it — replays and retries cannot create
a duplicate alarm or a duplicate delivery.

**Notifications with no video in them.** The payload is the alarm id, kind, zone,
stream id, timestamp and operator. No snapshot, no clip. Snapshot capture exists
as a configuration switch ("web.snapshot_enabled") and is off, with nothing
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

| What the carer gets | Typical | Device |
|---|---|---|
| Fall to alert received, real inference in the loop | **2.8 s** P50 (3.1 s P95) | reComputer R2000 series with the Hailo-8 option |
| Fall detection rate | **74.1%-88.9%** | Across the four detector platforms |
| Alerts recovered after the notification endpoint came back | **3 of 3**, no duplicates, first one 96 ms after recovery | reComputer R2000 series |

The 2.8 s figure was taken with the confirmation windows shortened to 1 s of
evidence plus 1 s of auto-confirm. With the shipped defaults (5 s plus 60 s) the
same path takes just over a minute, which is the confirmation design rather than
overhead. Set those two windows to what your site can answer.

The notifier rate-limits itself to 5 sends per 10 minutes. Past that it stops
sending, by design — size your webhook expectations accordingly.

**Detection accuracy is the base project's, not this one's.** This solution does
not detect anything itself, so its accuracy is whatever the EdgeFallKit detector
underneath it achieves. Those figures — GMDCSA-24 v2.1, split by subject, held-out
Subject 4 read once, 27 clips — are published in the Fall Detection solution's own
description, where the frozen per-platform accuracy runs from 74.1% to 88.9% and
mean alert latency from 1.22 s to 1.75 s. Quote those as base data with their
conditions attached. The alarm layer adds its own confirmation windows on top.

**Commission every site.** Watch a real alarm complete end to end on your own
cameras and your own webhook before the system carries anyone's safety.

## Output Interfaces

| Output | Where | Content |
|---|---|---|
| Alarm list and actions | HTTP port 8080, "/api/alarms" and the page at "/" | Alarm records with state, zone, stream, timestamps and operator; confirm and dismiss |
| Notification | HTTP POST to your webhook URL | Alarm id, kind, zone, stream, timestamp, operator, plus an idempotency header — no snapshot, no video |
| Alarm bus (optional, off) | MQTT port 1883, topic "eldercare/alarm/<zone-id>" | Same payload as the webhook |
| Detector results (input) | MQTT port 1883, topic "<device-name>/fall-detection/results/<stream-id>" | The "fall_result_v1" stream this service consumes |

"<device-name>" is the first topic segment and is yours to choose in the deploy
form. "stream_id" is read from the message payload, never parsed out of the topic
— a broker rewrite or a bridge prefix cannot silently reroute a zone.

## Deployment Comparison

**IP Camera + reComputer J30 / J40 (Orin)** puts everything on one box: the detector, the
alarm service, the broker and the confirmation page. It takes the most streams of
the three and builds its TensorRT engine on the device during the first deploy,
which is why that deploy takes the longest — measured 455 s for the YOLO11s-pose
engine on a reComputer J40 series (Orin NX). Pick it when the cameras exist and the
site has no gateway yet.

**IP Camera + reComputer R2000 (Hailo)** is the same stack on a Hailo-8, with the
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
- **"no_motion" will fire during sleep** unless the zone excludes the bed or the
  timeout is longer than a normal nap. Motion is the displacement of a tracked
  person's bbox centre above "motion_threshold" (0.02 normalised, default), not
  optical flow or keypoint velocity — small movements under a blanket do not
  count.
- **The Jetson detector must publish empty frames.** Its default is not to send
  anything when nobody is in view, which starves the "no_person" timeout of
  input. The Orin preset sets "publish_empty_frames: true" for you; if you
  replace the shipped detector config with the device's own, set it again. The
  Hailo runtime has no such switch and needs none.
- **A single point of failure by construction.** One camera, one detector, one
  service. If the camera drops off the network there is no alarm about the
  absence of alarms; the retained MQTT availability topic from the detector is
  what to monitor for that.
- **Occlusion can raise a false "no_person".** A zone only re-arms after the
  person is seen again, so one occlusion produces one alarm rather than a
  repeating series — but it still produces one.
- **The broker's origin differs by preset.** Orin and Hailo bring up their own
  alongside the detector; the reCamera gateway can either host one or point at
  the one the cameras already publish to. The bundled broker allows anonymous
  connections for commissioning on a trusted LAN — put credentials and TLS on it
  before the device is reachable from anywhere else.
- **The alarm service image is published on Harbor** for both `arm64`
  (`eldercare-alarm-arm64:0.1.0`) and `amd64` (`eldercare-alarm-amd64:0.1.0`);
  the Orin and Hailo deploy steps pull it directly rather than building it on
  the device.
- **Telegram and email are interface stubs.** Selecting them raises an error that
  lands in the retry queue rather than silently dropping the notification, which
  is the intended behaviour but is not a working channel.

## Voice Check-in (optional)

Off by default, and off changes nothing about the rest of the solution. When
enabled, a raised fall alarm makes the service speak a prompt into the room —
"are you all right? please answer" — and listen for a few seconds, in parallel
with the five-second evidence window rather than after it.

A call for help, no answer at all, or an answer nobody can read confirms the
alarm immediately and skips the remaining operator window. "I'm fine" does
*not* close the alarm by default: it flags the alarm for review and lets the
normal timing continue. Set "on_ok: dismiss" to close it instead. The asymmetry
is the whole point — a mis-heard "I'm fine" would suppress a real fall, while a
confirmed alarm nobody needed costs an operator a few seconds. For the same
reason a distress word beats a safe word in the same sentence, and a phrase the
keyword lists do not recognise confirms rather than waits.

Audio hardware is a USB microphone and speaker on the LAN compute box, plus an
OpenVoiceStream instance for TTS and streaming ASR. The cameras are not the
audio path: neither reCamera model has a confirmed usable microphone, and the
SG2002 cannot host local ASR at all. TTS and ASR compete with the detector for
CPU, accelerator and memory on a shared box — one session at a time, a
pre-generated prompt, and a fail-safe confirm on any OVS timeout are what keep
that contention from costing an alarm.

**Privacy.** Audio is never written to disk. Raw PCM lives in memory for one
listening window and is released when the verdict is produced. Persisted are the
verdict, the confidence, the latency and the transcribed text; setting
"store_transcript: false" drops the text as well, leaving only the verdict in
the audit trail. Notifications gain the same fields and still carry no snapshot
and no video.

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
