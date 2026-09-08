## What it does

A camera at the door recognises a face, requires a passive liveness check to
pass, checks the person against the current library, the schedule and the
blocklist, and — only if all of that holds — pulses a relay that switches a lock
running on its own 12/24 V supply. Every decision, allowed or denied, is
published on MQTT and appended to a hash-chained audit log.

The face library lives in the cloud, versioned. Devices poll two HTTP endpoints,
compare the version, download in chunks, verify SHA-256 and a manifest
signature, load the new matcher, and only then switch atomically. A failure at
any step leaves the previous version in place, and a device that is offline keeps
opening the door with the last library it successfully loaded.

## What you get

**A door that keeps working when the network does not.** Recognition, liveness
and the decision all happen at the door. The network carries library updates,
events and remote commands — not the unlock itself, except when route B's
relay node sits on the far side of MQTT, where that trade is made explicitly.

**Liveness that cannot be silently switched off.** The upstream recognition
service degrades to "keep recognising, skip liveness" when the model file is
missing. For a door that degradation is an open door, so the adapter probes
"/health" at startup and refuses to run unless liveness reports as loaded. A
"live" value of "null" is treated as a failure, not a pass: it means the check
did not run.

**A face library with a delete that stays deleted.** Removing a person mints a
new version without them and writes a deletion barrier. Rolling back to any
version that still contains them is refused by name. Without the barrier, one
rollback quietly re-admits everyone who has ever been removed.

**Remote commands that cannot be replayed into a second unlock.** Exact field
set, UUIDv4 command id, RFC3339 "issued_at" with a timezone, a TTL bound, and a
per-identity replay table. A redelivered command returns the original receipt
and does not open the door again. The command topic is never retained — a
retained unlock replays on every reconnect, so the door would open by itself
after a power cut.

**An audit log you can check.** Append-only NDJSON, each record carrying the
previous record's hash. Changing one past decision from denied to allowed breaks
the chain, and the console's verification endpoint reports it.

**Two ways to wire the same system**, sharing one library, one event contract
and one console. **A. AI camera at the door** - a reCamera Pro or a standard
reCamera recognises, checks liveness and decides on the camera itself. **B. AI
host with your existing cameras** - a reComputer J20 / J30 / J40 / R1000 pulls
the RTSP streams already at the doors and drives the relay from its own digital
output, a Grove Relay, or an MQTT relay node when the host is not at the door.

## Where it fits

- Unmanned or partially staffed retail — staff entrance, stock room, back door.
- Shared office and co-working doors where the roster changes weekly.
- Equipment rooms and cabinets where an audit trail matters more than throughput.
- Any site that already has RTSP cameras at the door and wants recognition
  without replacing them.

Not for: doors where a failure to open is a safety event, and doors where the
consequences of a wrongly admitted person are severe. This is a reference
design, not a certified security product. Commission recognition, liveness and
the door path on your own site before it carries a door.

## How well it works

**This is not a certified security or life-safety system.** Calibrate the
thresholds and measure recognition, liveness and the door path on your own site
before the design carries a door.

**Door-open time: from the face entering the frame to the relay contact
closing.** Measured on the device, running the deployed app itself, over the
complete pipeline — capture, detection, liveness, matching, policy, GPIO pulse.
p50, with p95 in brackets, 12 approaches per point.

| Camera / host | 10 people | 100 people | 500 people | 1 000 people | 1 500 people |
|---|---|---|---|---|---|
| reCamera Pro (RV1126B) | **3.74 s** (3.78) | **3.72 s** (3.75) | **3.75 s** (3.78) | **3.75 s** (3.80) | **3.78 s** (3.81) |
| Standard reCamera (SG2002) | — | — | — | — | — |
| AI host + RTSP camera (Jetson) | — | — | — | — | — |

60 of 60 approaches opened the door. Conditions: reCamera Pro, 1280x720 frames
replayed at 12.5 fps, liveness on, `min_face_px` 40, `match_threshold` 0.40; the
probe is a stock video clip replayed through the device's own pipeline, not a
live person, and the endpoint is a sysfs readback of the GPIO pin with no relay
or lock connected. Library size costs 43 ms between 10 and 1 500 people: the
cosine scan is 0.215 ms at 10 people and 13.1 ms at 1 500. The time is the
recognition pipeline itself — the device runs 7.0-7.2 fps and liveness needs
motion evidence across frames. Source:
"evaluation/runs/2026-09-08-open-door-latency/results.md" in the
unmanned-store-access repository.

The standard reCamera row is empty because its recogniser is a closed native
process with no way to feed it a frame: measuring it needs a person in front of
the lens. The AI-host row is empty because that route has not been run on
hardware yet.

A software-loop test suite covers the protocol and the state machine: 52 of 52
checks across three library versions built, published, pulled, hash-checked and
atomically switched; the policy denying a photograph, a null liveness result, a
blocklisted person, a below-threshold stranger, an empty frame and a repeat
inside the debounce window; exactly two unlock pulses across ten frames, both at
the configured 1500 ms; a rollback to a removed-person version refused; a remote
unlock accepted, an expired one rejected, a replay returning the original
receipt without a second pulse; a 13-record audit chain that fails once a denial
is edited into an approval; and the console's three roles behaving.

That measures whether the protocol and the state machine do what they claim, not
how well the system recognises faces or rejects spoofs.

Every face library version's manifest carries five licence fields — "license_id",
"use_scope", "redistributable", "source_revision", "sha256" — so the terms travel
with the artefact rather than living only in a document.

**The RKNN backend has no liveness implementation.** A preset running on RKNN
cannot enforce liveness; use one of the other backends where liveness matters.
