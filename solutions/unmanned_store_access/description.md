## What it does

A camera at the door recognises a face. Only when the liveness check passes, the person is inside their allowed schedule and not on the blocklist does it send a relay pulse to open the door. Recognition and the decision run locally, so the door still opens when the network is down.

## What you get

- **Opens the door offline**: library updates, event reports and remote unlock use the network; opening the door does not.
- **Rejects photos and screen replays**: liveness is always on (except on the RKNN backend), and the service refuses to start if the liveness model is not loaded.
- **Face library managed in the cloud**: add or remove people once and it reaches every door device; a removed person cannot come back through a rollback.
- **Remote unlock**: the console or MQTT sends unlock, hold-open and close commands; a repeated command does not open the door twice.
- **Verifiable access records**: every allow and deny is recorded, and the verification endpoint reports any record that was tampered with.

## Where it fits

- Staff entrances, stock rooms and back doors of unmanned or lightly staffed stores
- Shared offices where the roster changes often
- Equipment rooms and cabinets that need an access trail
- Sites that already have RTSP cameras at the door and do not want to replace them

Not for doors where admitting the wrong person causes a safety incident. This is not a certified security product.

## Measured results

| Metric | Result |
|---|---|
| Face to door-open signal | **about 0.6 s**, nearly unchanged from 10 to 1 000 people in the library |
| Registered person | **door opened in 24 of 24 runs** |
| Stranger | **0 false opens in 40 runs** |
| Phone screen replay, still screen image | **0 false opens in 60 runs** |

Tested on reCamera Pro; the open time excludes the mechanical action of the relay and lock.

## Output Interfaces

| Interface | Content |
|---|---|
| MQTT "access/v1/events" | Allow/deny decision for every attempt |
| MQTT "access/v1/status/{device_id}" | Device online status and heartbeat |
| MQTT "access/v1/commands/{door_id}" | Remote unlock / hold-open / close commands |
| HTTP "/api/…" | Console API: people, devices, events, record verification |

## Two routes

| | A. AI camera at the door | B. AI host + existing cameras |
|---|---|---|
| Device | reCamera Pro, or standard reCamera | reComputer J20 / J30 / J40 / R1000 |
| Camera | Built into the device | RTSP cameras already at the door |
| Does the unlock path go over the network | Not on Pro; over MQTT on standard | Not when the relay is wired to the host |

**Choose A**: there is no camera at the door yet and you want one device to do it all.
**Choose B**: the door already has a camera, or one host needs to manage several doors.

## Usage Notes

- **This solution only outputs a relay dry contact** to the door controller's input. The lock and its power supply belong to the door-control installer; do not drive a lock from a device pin.
- **Wiring order: first an LED to confirm the signal, then the relay, then the lock.**
- Active level, pulse width, NO/NC contact and power-loss state have no defaults and must be configured on site.
- Tune the recognition threshold after testing on site.
- The bundled MQTT broker is anonymous and plaintext, for testing only; enable TLS and access control for production.
- The RKNN backend has no liveness check; choose another backend where anti-spoofing matters.
- Cloud face enrolment for reCamera Pro does not yet produce a usable face library.

## Licensing note

Code is Apache-2.0. **The face recognition model InsightFace buffalo_l is for non-commercial research only**, and this package does not ship its weights. Commercial deployment requires a commercially licensed model and rebuilding every face library. The liveness model Silent-Face-Anti-Spoofing is Apache-2.0 and may be used commercially.
