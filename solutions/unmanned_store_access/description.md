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
events and remote commands — not the unlock itself, except in the MQTT-relay
preset where that trade is made explicitly.

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

**Five ways to wire the same system**, from a camera that drives its own GPIO to
a 20-dollar controller with no liveness at all, sharing one library, one event
contract and one console: P1 on-device (reCamera Pro), P2 industrial box
(reComputer Industrial J20), P3 MQTT relay, P5 standard reCamera running its own
recognition with the relay at the gateway, and P4 XIAO + Grove Vision AI V2.

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

| What the door does | Typical | Device |
|---|---|---|
| A newly published face library live on the door | **0.49 s** p50 (0.51 s p95) | reCamera |
| Power-on to the access app answering | **8.8 s** median, 6 power-on runs | reCamera |

Activation time grows with the size of the library — about 9.8 s at 402 people
and about 22 s at 1502 people on the same chain — so allow for the first sync of
a large library. A tampered library or a wrongly signed update is refused on the
device and the door keeps running on the version it already holds.

The P4 preset's WE2 models — SCRFD detection and a distilled MobileFaceNet
embedding — inherit InsightFace's non-commercial terms. A commercial P4
deployment has to retrain through the QAT pipeline rather than ship these.

Every face library version carries five licence fields — licence id, use scope,
redistributable, source revision and content hash — so the terms travel with the
artefact rather than living only in a document.

**The RKNN backend has no liveness implementation.** A preset running on RKNN
cannot enforce liveness; use one of the other backends where liveness matters.
