## What the Solution Does

Read license plates with the gate cameras you already have, and lift the barrier for whitelisted vehicles.

Use existing entrance and exit cameras plus one on-site edge host to read license plates, trigger automatic barrier gate opening for whitelisted vehicles, and record structured passage logs with snapshot links. Video never leaves the site.

- **Real-Time Detection and Recognition**: Surveillance cameras stream RTSP to an edge box, which automatically localizes plate bounding boxes and reads plate characters.
- **Whitelist Matching and Automatic Barrier Control**: Upload a CSV whitelist; matching plates trigger a pulse signal via relay to the barrier gate controller.
- **Structured Passage Logs**: Publishes one MQTT event per vehicle (including plate number, confidence, and timestamp) with a link to a local snapshot JPEG.

## Core Value

- **Leverage Existing Cameras**: No need to purchase dedicated all-in-one ANPR cameras—connect existing RTSP cameras to a compact edge host.
- **On-Premise Closed Loop**: Recognition, whitelist evaluation, and pulse triggers run locally; vehicles pass smoothly even during network outages, and vehicle images remain on site.
- **Fail-Safe Electrical Design**: Gate trigger pulses are isolated via an interposing relay with cooldown timing to prevent duplicate pulses; closing remains governed by ground loop safety.
- **Cross-Platform Accelerator Support**: Supported on reComputer J30 / J40 Series (Jetson Orin Nano / NX) and reComputer RK3588 / RK3576 Series.

## Suitable Scenarios

Gates where vehicles pass through fixed lanes and plates remain clearly legible in camera frames:

- **Residential Communities and Campus Gates**: Whitelist residents and faculty for automatic entry while visitors check in at the guard booth.
- **Corporate Staff Parking**: Import employee plate numbers with expiration dates; access permissions revoke automatically upon expiry.
- **Logging-Only Gates**: Deploy without connecting barrier relays to capture timestamped plate records and photos for reconciliation.

## Measured Performance

Evaluated using 1080p RTSP streams from the CCPD benchmark dataset:

| Metric | Typical | Device |
|---|---|---|
| 1080p processing speed | **30 fps** | reComputer J30 Series (J3011) |
| 1080p processing speed | **29–30 fps** | reComputer RK3576 Series |

## Usage Notes

- **Supported Plate Standards**: Supports mainland China 7-character blue plates and 8-character green new-energy plates; two-row, special-purpose, and foreign plates are not supported.
- **Camera Mounting**: Mount cameras 3–8 meters from the lane at an angle looking down toward plates, avoiding extreme angles or glare.
- **Integration Interfaces**: Publishes plates to `<site>/parking/<camera>/plate`, gate actions to `<site>/parking/<camera>/gate`, and manages whitelists via HTTP `/whitelist`.

> 📖 **Engineering Reference:** Full architecture internals, measured benchmarks, and failure modes are documented in the [Engineering Wiki · Edge License Plate Recognition](https://wiki.seeedstudio.com/solutions/edge-license-plate-recognition/).
