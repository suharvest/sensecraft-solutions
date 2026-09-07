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
`/health` at startup and refuses to run unless liveness reports as loaded. A
`live` value of `null` is treated as a failure, not a pass: it means the check
did not run.

**A face library with a delete that stays deleted.** Removing a person mints a
new version without them and writes a deletion barrier. Rolling back to any
version that still contains them is refused by name. Without the barrier, one
rollback quietly re-admits everyone who has ever been removed.

**Remote commands that cannot be replayed into a second unlock.** Exact field
set, UUIDv4 command id, RFC3339 `issued_at` with a timezone, a TTL bound, and a
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
before the design carries a door. The numbers below cover the face-library
distribution path and the GPIO pulse, measured on hardware.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Face library activation, reCamera Pro (P1) | Full activation 62.2 ms (v1) and 45.4 ms (v2); up-to-date no-op round 6.2 ms; recognition event to GPIO pin readback n=22, p50 1.448 ms / p95 2.709 ms | reCamera Pro (RV1126B, Buildroot 2023.02.6) on Ethernet, 1-2 people / under 20 KB library. Consistency gate `problems: []`; a tampered gallery and a wrongly signed manifest were both rejected on the device. The 22 events were injected synthetic recognition results, the readback is sysfs so the values are an upper bound, and no external circuit was connected | `evaluation/runs/2026-09-07-recamera-pro-p1/results.md` and the two `boundary.*.yaml` alongside it |
| Face library activation, device side | p50 491.6 ms, p95 507.8 ms (n=20); `op:reload` round trip p50 100.0 ms (n=25) | Standard reCamera (SG2002 / CV181x riscv64, firmware 0.2.2) over USB-RNDIS, 2 people, 16.5 KB library. Scale points, one run each: 402 people / 2.86 MB in 9 801.7 ms, 1502 people / 10.66 MB in 22 278.7 ms | `evaluation/runs/2026-09-06-recamera-std-p3-r2/results.md` §2 and `boundary.facedb-activation.yaml` alongside it |

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

The P4 preset's WE2 models — SCRFD detection and a distilled MobileFaceNet
embedding — inherit InsightFace's non-commercial terms. A commercial P4
deployment has to retrain through the QAT pipeline rather than ship these.

Every face library version's manifest carries five licence fields — `license_id`,
`use_scope`, `redistributable`, `source_revision`, `sha256` — so the terms travel
with the artefact rather than living only in a document.

**The RKNN backend has no liveness implementation.** A preset running on RKNN
cannot enforce liveness; use one of the other backends where liveness matters.
