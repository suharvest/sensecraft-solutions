# Internal status — Unmanned Store Access

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rule "results / KPI only carry measured numbers".

## What has run on hardware

The face-library distribution path — poll, chunked download, per-file SHA-256,
manifest signature, atomic switch, gallery write and `op:reload` ack, plus
resume after an interrupted download and rejection of a version whose manifest
does not verify — on:

- a standard reCamera (SG2002 / CV181x riscv64, firmware 0.2.2), two probe runs
- a reCamera Pro (RV1126B, Buildroot 2023.02.6), one probe run

The Pro run also exercised recognition-to-GPIO pulse readback, using injected
synthetic recognition events rather than a live face.

## What has not run on hardware

Recognition, liveness and the door path end to end. No relay or lock has been
wired on either device, and nobody stood in front of either lens — each
standard-reCamera probe run sampled 220 frames, all reading `face_count: 0`.

On the Pro, the registration path cannot yet produce a face library usable in
production (see the licensing note on the page).

Thresholds on both devices are shipped defaults carrying `calibration =
pending`. `gpio130`'s physical identity is confirmed (device tree pinmux: the
expansion port's UART4 M0 pins, reconfigured as GPIO — the 3.3 V family,
not one of the board's two native 12–21 V outputs); its level and drive
current are still unmeasured. reCamera PoE: pending hardware, no figure.

Everything outside the library-distribution and GPIO-readback paths runs as a
pure software loop on a macOS development machine, with a fake actuator, an
in-memory MQTT broker and a fake recogniser.

## Boundary metrics still empty

Seven boundary metrics are defined, covered by nine rows (face-library
activation has a row per platform). Three carried numbers; six were empty and
have been removed from the page:

| Metric | Why it is empty | Boundary file |
|---|---|---|
| Recognition FAR / FRR | No real face model, no positive/negative pairs; both probe runs had nobody in front of the lens | `boundary.recognition.yaml` |
| Liveness spoof rejection / live false-reject | Needs real spoof samples (photographs, screens, masks) and Silent-Face actually running | `boundary.liveness.yaml` |
| Direct-path unlock latency p95 | Needs the full camera-to-relay chain on hardware | `boundary.latency-direct.yaml` |
| MQTT-relay unlock latency p95 | No relay has been wired at the gateway (`evaluation/runs/2026-09-06-recamera-std-p3-r2/results.md` §5) | `boundary.latency-p3.yaml` |
| Offline endurance | Needs a device running disconnected for a long period | `boundary.offline.yaml` |
| 72-hour soak: wrong opens / crashes | Needs 72 hours of uninterrupted operation on hardware | `boundary.soak72h.yaml` |

All under `evaluation/runs/2026-09-06-c1-software/` in the upstream repository
`unmanned-store-access`.

## Software-loop-only row removed

**Face library activation, software loop** — 11.6 ms slowest of three
activations (v1/v2/v3: 11.6 / 3.7 / 3.5 ms). macOS development machine, loopback
HTTP, no TLS, no authentication, zero loss, 4 people x 3 embeddings of 128
dimensions, single run. Superseded on the page by the device-side row.

## Per-preset hardware status (removed from the zh comparison table)

| Preset | Status |
|---|---|
| P1 direct GPIO | Library pull and GPIO readback verified on board; door path and registration not verified |
| P2 industrial box | Not verified on board |
| P3 MQTT relay | Not verified on board |
| P5 standard reCamera | Library pull verified on board; door path not verified |
| P4 XIAO + Grove Vision | Firmware not built |

## Licence field convention

An unverified licence is recorded in a face-library manifest as
`license_id: unverified` with `use_scope: internal-only`. It is never written as
permissive and corrected later.
