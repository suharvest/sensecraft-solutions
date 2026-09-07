# Internal status — Eldercare Fall & Inactivity Alarm

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rule "results / KPI only carry measured numbers".

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| MacBook, macOS 15 (Darwin 25.5.0), arm64, loopback network, no container | development-machine baseline (alarm path only) |
| reCamera One, standard (non-PoE), over USB-RNDIS | reCamera One |

## Test-run conditions

Date 2026-09-05, run directory `evaluation/runs/2026-09-05-smoke/` in the
eldercare-alarm project. Raw outputs under `raw/`, conditions in
`conditions.yaml`, one `boundary.<metric>.yaml` per row.

Every `boundary.*.yaml` has values in the `stable` tier only. `degrading` and
`failure` are `null`: nothing was loaded to the point of degradation, so no
boundary was found. `reproduced_by: null` — one person, one run, not
independently reproduced.

## Rows removed from the page

**False alarms — 0 over 0.02 camera-hours** (72 s of quiet replay). 0.02
camera-hours proves nothing about a false-alarm rate. The intended run is 24 h.

**Robustness under darkening and occlusion — not measured.** Needs GMDCSA clips
and on-device inference. The script exists and was not run.

## What has not been shown on hardware

The Jetson `publish_empty_frames` override, the Hailo per-frame publishing
behaviour and the exact reCamera topic and payload shapes are all still
unverified on hardware. The detector image digests are recorded as pending in
`eldercare-alarm/release/PINNING.md`.

## The one on-device run

2026-09-06, standard (non-PoE) reCamera One over USB-RNDIS. Real
`fall-detection` MQTT frames, an injected fall alarm and a real 60 s no-activity
alarm both reached a webhook over the device's mosquitto broker (proxied through
an SSH tunnel because a local network tool intercepted the direct route — not a
device issue).

Alert latency across 10 injected trials was P50 2487 ms / P95 2751 ms for the
first 5, after which the notifier's own 5-per-10-minute rate limit silently
stopped further sends — by design, not a fault. USB-disconnect recovery was not
attempted (out of that session's authorized scope). See
`eldercare-alarm/evaluation/runs/2026-09-06-recamera-one/results.md`.

## Detection accuracy is the base project's

This solution does not detect anything itself. Its accuracy is whatever the
EdgeFallKit detector underneath it achieves — GMDCSA-24 v2.1, split by subject,
held-out Subject 4 read once, 27 clips. Those figures live in
`solutions/fall_detection/description.md`. They are not re-measured here, and
the alarm layer adds its own confirmation windows on top of detection latency.
