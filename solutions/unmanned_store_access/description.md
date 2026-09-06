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
consequences of a wrongly admitted person are severe. Nothing here is a
certified security product. Only the face-library distribution path has been
exercised on hardware — on a standard reCamera, sources below. Recognition,
liveness and the door path have not.

## How well it works

**This is not a certified security or life-safety system.** One link has been
exercised on hardware and the rest has not, so the two are stated separately.

**On hardware**: the face-library distribution path — poll, chunked download,
per-file SHA-256, manifest signature, atomic switch, gallery write and
`op:reload` ack, plus resume after an interrupted download and rejection of a
version whose manifest does not verify. Two probe runs on a standard reCamera
(SG2002 / CV181x riscv64, firmware 0.2.2).

**Not on hardware**: recognition, liveness and the door path. Nobody stood in
front of the lens in either probe run — each run sampled 220 frames, all
reading `face_count: 0` — no relay has been wired, and the thresholds are the
device's shipped values carrying `calibration = pending`. Everything outside
the library path runs as a pure software loop on a macOS development machine,
with a fake actuator, an in-memory MQTT broker and a fake recogniser.

Seven boundary metrics are defined. One carries numbers and six are empty, each
with the reason recorded rather than guessed at.

All sources below are paths in the upstream repository `unmanned-store-access`.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Face library activation, device side | p50 491.6 ms, p95 507.8 ms (n=20); `op:reload` round trip p50 100.0 ms (n=25) | Standard reCamera (SG2002 / CV181x riscv64, firmware 0.2.2) over USB-RNDIS, 2 people, 16.5 KB library. Scale points, one run each: 402 people / 2.86 MB in 9 801.7 ms, 1502 people / 10.66 MB in 22 278.7 ms | `evaluation/runs/2026-09-06-recamera-std-p3-r2/results.md` §2 and `boundary.facedb-activation.yaml` alongside it |
| Face library activation, software loop | 11.6 ms slowest of three activations (v1/v2/v3: 11.6 / 3.7 / 3.5 ms) | macOS development machine, loopback HTTP, no TLS, no authentication, zero loss, 4 people × 3 embeddings of 128 dimensions, single run | `evaluation/runs/2026-09-06-c1-software/results.md`. **Not a device-side figure**, and superseded by the row above |
| Recognition FAR / FRR | pending | — | `evaluation/runs/2026-09-06-c1-software/boundary.recognition.yaml`. No real face model and no positive/negative pairs in the software loop; both probe runs had nobody in front of the lens |
| Liveness spoof rejection / live false-reject | pending | — | `evaluation/runs/2026-09-06-c1-software/boundary.liveness.yaml`. Needs real spoof samples — photographs, screens, masks — and Silent-Face actually running |
| Direct-path unlock latency p95 | pending | — | `evaluation/runs/2026-09-06-c1-software/boundary.latency-direct.yaml`. Needs the full camera-to-relay chain on hardware |
| MQTT-relay unlock latency p95 | pending | — | `evaluation/runs/2026-09-06-c1-software/boundary.latency-p3.yaml`. Still pending after the second probe run — no relay has been wired at the gateway (`evaluation/runs/2026-09-06-recamera-std-p3-r2/results.md` §5) |
| Offline endurance | pending | — | `evaluation/runs/2026-09-06-c1-software/boundary.offline.yaml`. Needs a device running disconnected for a long period |
| 72-hour soak: wrong opens / crashes | pending | — | `evaluation/runs/2026-09-06-c1-software/boundary.soak72h.yaml`. Needs 72 hours of uninterrupted operation on hardware |

What the software loop did establish, on that machine and no other
(`evaluation/runs/2026-09-06-c1-software/results.md`): 52 of 52
checks passing across three library versions built, published, pulled,
SHA-verified and atomically switched; the policy denying a photograph
(`liveness_failed`), a null liveness result (`liveness_unknown`), a blocklisted
person, a below-threshold stranger, an empty frame and a repeat within the
debounce window; exactly two unlock pulses across ten frames, both at the
configured 1500 ms; a rollback to two different versions refused by the deletion
barrier with the current version unchanged; a remote unlock accepted and
executed, an expired one rejected with `TTL_EXPIRED`, a replay returning the
original receipt without a second pulse, and an anonymous identity refused; a
retained last-will delivered after a drop; a 13-record audit chain verifying, and
failing after one denial was edited into an approval; and the console's three
roles behaving — a viewer refused an unlock, an operator refused a library
change, an enrolment of fewer than three images refused.

None of that is a measurement of how well the system recognises faces or rejects
spoofs. It is a measurement of whether the protocol and the state machine do what
they claim.

## Output Interfaces

| Interface | Where | What it carries |
|---|---|---|
| `access/v1/events` | MQTT, QoS 1 | One message per decision: person or anonymous id, score, threshold in force, liveness block, decision and reason, door action, actuator id, library version, model sha, corrected timestamp |
| `access/v1/status/{device_id}` | MQTT, retained last-will | 30-second heartbeat: actuator health, library version and model tag, whether liveness is loaded. The last-will is retained so a late subscriber still sees a dropped device as offline |
| `access/v1/commands/{door_id}` | MQTT, never retained | `unlock`, `hold_open`, `lock`, with a UUIDv4 id, a timezone-bearing `issued_at` and a TTL |
| `access/v1/receipts/{command_id}` | MQTT | The terminal state of one command. A replayed command returns this same receipt |
| `access/v1/relay/{relay_id}/set` and `/state` | MQTT | The MQTT-relay preset only. `set` is never retained; `state` is retained and reports the physical contact, not whether the door is open |
| `GET /v1/facedb/current`, `GET /v1/facedb/{version}` | HTTP | The entire library distribution surface. `Range` for chunked and resumable downloads |
| `/api/events`, `/api/devices`, `/api/persons`, `/api/audit/verify` | HTTP | The console's API behind a three-role shared-token gate. No anonymous read |

## Deployment Comparison

| | P1 on-device | P2 industrial box | P3 MQTT relay | P5 standard reCamera | P4 XIAO + Grove Vision |
|---|---|---|---|---|---|
| Compute | reCamera Pro / PoE / HQ PoE | reComputer Industrial J20 | J30 / J40 / R2000 / reCamera | Standard reCamera (SG2002), on-camera native process | XIAO ESP32-S3 |
| Camera | The device's own sensor | Existing RTSP camera | Existing RTSP camera | The device's own sensor | Grove Vision AI V2 (Himax WE2) |
| Unlock path | Local sysfs GPIO → relay | Opto-isolated DO → relay | MQTT → R1000 Modbus point or XIAO relay | MQTT → relay at the gateway | Local GPIO D0 → relay |
| Liveness | Enforced (Silent-Face) | Enforced (Silent-Face) | Enforced (Silent-Face) | On-camera two-head texture liveness with blink fusion, **thresholds uncalibrated** | **None. No model exists for this chip** |
| Policy | Person + schedule + blocklist + liveness + debounce | Same | Same | Same, evaluated in the cloud from the event stream | **Weakened: allowlist within a schedule, single-shot** |
| Network on the unlock path | No | No | **Yes — broker availability is door availability** | **Yes — broker availability is door availability** | No |
| Install form | Root appmgr kit app, manual steps | Containers over SSH | Containers over SSH | Manual copy of a standard-library daemon, no container | Two-segment USB flash |
| State | Untested on hardware | Untested on hardware | Untested on hardware | Library path exercised on hardware; door path untested | **Firmware not built** |

**Choose P1** when the door has no camera yet and you want the shortest possible
chain: recognition, decision and contact all in one device, nothing on the
network between a face and the lock. The cost is that reCamera Pro is a
Buildroot device with no package manager, so installation is a manual procedure
rather than an automated step.

**Choose P2** when the door already has a camera you are keeping, and you want
galvanic isolation between the compute and the lock circuit. This is the
conventional industrial answer and the one with the fewest surprises — provided
the DO pin numbers turn out to be what the design spec says, which has not been
confirmed.

**Choose P3** when the box that can run recognition is nowhere near the door, or
when one box serves several doors. You are explicitly buying a network hop on the
unlock path in exchange for that flexibility, which is why it carries its own
latency boundary.

**Choose P5** when the door has a standard reCamera and you want no recognition
container anywhere: the camera already detects, embeds, judges liveness and
matches in one native process, so the only thing added is a standard-library
daemon that pulls the versioned library and maps the camera's native result
stream onto the event contract. The relay sits at the gateway, so the unlock
path crosses the network the same way P3's does. It is the preset whose library
path has actually run on hardware, and the one whose thresholds are the device's
shipped values rather than calibrated ones.

**Choose P4** when cost dominates and the threat model does not include someone
holding up a photograph — a stock-room door inside an already-controlled
building, for instance. Do not choose it for a street-facing entrance. The
firmware exists as source on a branch and has not been built.

## Usage Notes

**The lock is always behind a relay, always on its own supply.** A lock draws
300 mA to 1 A; a GPIO pin and an opto-isolated DO carry milliamps. Four settings
— active level, pulse width, relay contact and fail mode — are configured per
installation and deliberately have no defaults, because a fail-safe magnetic lock
wired through the normally-open contact stands open permanently and looks like a
working installation until somebody tests it.

**Wire in order: LED, then relay, then lock.** Confirm polarity and pulse width
on an LED, confirm the contact clicks on the relay, and only then put a lock on
it.

**Do not assume a GPIO pin is free.** The surveyed reCamera Pro had `gpio131`
already exported and driven by another application. The actuator refuses to
start on a pin whose current state disagrees with the configured idle state, and
will not take a pin over unless told to explicitly.

**Device clocks are not trustworthy, and the design assumes it.** The surveyed
unit's clock was about seven months out with no NTP client, so HTTPS failed with
"certificate is not yet valid". Devices therefore take a time offset from the
library server's HTTP `Date` header and correct their own event timestamps —
they never set the system clock. A plaintext `http://` library URL is permitted
on a LAN, but only with an HMAC-SHA256 signature over the manifest; without a
key, the device refuses to start. That signature stops tampering on the wire; it
does not stop someone who has opened a device, since any leaked device key can
forge a library.

**The threshold shipped as a default is a starting point, not a result.** No
FAR/FRR figure exists for this project on any hardware. Sweep positive and
negative pairs on the installed camera and set it from that.

**The bundled broker configuration is anonymous plaintext and is for a bench.**
An unlock topic that accepts anonymous publishes is not access control. The
design calls for TLS, per-device identities and topic ACLs; none of the three is
in the bundled configuration.

**Neither container image has been pushed and the P4 firmware has not been
built.** The compose files name the tags they will have and say so at the top;
the firmware step points at labelled stubs rather than at a plausible binary.

## Licensing note

The code in this package and in the upstream repository is Apache-2.0. **The
model weights are not**, and the difference matters before anybody deploys this
commercially.

Face detection and embedding use InsightFace's `buffalo_l`, through
`face_rec_api`. InsightFace's own statement, quoted verbatim:

> The code of InsightFace is released under the MIT License. There is no
> limitation for both academic and commercial usage.
>
> The training data containing the annotation (and models trained with these
> data) are available for non-commercial research purposes only.

`buffalo_l` is a model trained with that data. It is therefore usable for
**non-commercial research purposes only**: `license_id: non-commercial`,
`use_scope: non-commercial`, `redistributable: false`. The weights are not
shipped with this package.

Two consequences worth stating before they are discovered late. A commercial
deployment must replace the face backbone with a commercially licensed one. And
replacing it means **rebuilding every face library version**, because embeddings
are not comparable across models — a library built with one backbone scores
approximately zero against another, so the old versions are dead rather than
merely stale, and the `model_tag` guard in the manifest is what stops a device
loading one by mistake.

The passive liveness model, MiniVision's Silent-Face-Anti-Spoofing, is
Apache-2.0: `use_scope: commercial`, redistributable, used unmodified. Apache-2.0
permits commercial use provided the copyright and licence notices are retained
and changes are marked.

The P4 preset's WE2 models — SCRFD detection and a distilled MobileFaceNet
embedding — inherit InsightFace's non-commercial terms. A commercial P4
deployment has to retrain through the QAT pipeline rather than ship these.

Every face library version's manifest carries five licence fields — `license_id`,
`use_scope`, `redistributable`, `source_revision`, `sha256` — so the terms travel
with the artefact rather than living only in a document. An unverified licence is
recorded as `license_id: unverified` with `use_scope: internal-only`; it is never
written as permissive and corrected later.

One coverage gap on the record: the RKNN backend's liveness is not implemented
upstream. A preset running on RKNN cannot satisfy "liveness enforced" and must
not be accepted, and its liveness boundary must not be filled from that path.
