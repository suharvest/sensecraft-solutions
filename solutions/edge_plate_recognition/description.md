# Edge License Plate Recognition

> **Draft (staging).** This reference design has not passed on-device
> acceptance yet. No accuracy, latency or FPS figures are published here — they
> will be filled in from the acceptance runs, per platform, before release.

Recognize license plates where the camera is, not in the cloud. A vehicle
arrives at the gate; the plate is detected, read character by character, and
voted on across several frames; one event per vehicle goes out over MQTT with a
link to the snapshot. If the plate is on your whitelist, the barrier gets an
open pulse — and a second event records who triggered it and how long the pulse
took.

## One pipeline on the edge host

- **Host-side**: keep your existing gate IP cameras. A reComputer (Jetson Orin,
  RK3588, RK3576 or Hailo-8) pulls the RTSP streams and runs the models — one
  host can cover several lanes.
- **Camera-side** (reCamera Pro / reCamera 2002 HQ PoE): not offered in this
  release; the on-camera app is not published yet.

Every host publishes the same event contract, so your parking system subscribes
once regardless of which hardware sits at the gate.

## Barrier control that fails safe

All gate opening goes through a reComputer R1124-10: it hosts the MQTT broker
and a gate service that matches plates against a local whitelist (CSV upload
over HTTP, exact match after normalization — no fuzzy matching) and pulses a
digital output through an interposing relay to the barrier's OPEN input. The
pulse is cooldown-guarded, replayed or stale events never open the barrier, and
the output is forced back to open-circuit on any fault. Closing the barrier
stays the barrier controller's own job.

## Private by construction

Events carry the plate string, confidence and a snapshot *reference* — images
never travel inside the event. Snapshots stay on the device, kept for 7 days by
default with a size cap, and fetched over HTTP only when you follow the link.
There is no cloud plate database and no video uplink; adding one is your
integration to make, not a default.

Supported plate formats at launch: mainland China single-row plates (blue
7-character and new-energy green 8-character). Two-row, special-purpose and
overseas formats are out of scope for this release.
