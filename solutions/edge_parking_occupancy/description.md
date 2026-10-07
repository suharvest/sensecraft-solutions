# Edge Multi-Camera Parking Occupancy

> **Draft / blocked artifact.** This package is disabled. The native SlotsApp,
> public or approved local image input, vehicle640 engine, and platform
> acceptance evidence are not available as a releasable artifact. Models,
> broker credentials, and host proprietary libraries are not bundled.

SlotsApp samples one or more RTSP streams, applies the native `slot_coverage`
analyzer to configured parking polygons, and publishes retained slot states to
an external MQTT broker. The HTTP editor and `/healthz` endpoints are part of
the intended app contract.

The current package records Jetson and RK3576/RK3588 staging contracts. These
remain drafts; multi-camera capacity, slot accuracy, disconnect recovery, and
real hardware acceptance remain unverified.

## RK3576 and RK3588 staging presets

Two disabled staging presets describe native RKNN SlotsApp deployment on reComputer RK3576 and RK3588. Copy the board-specific shipped `assets/config/slots-rk3576.json` or `slots-rk3588.json` to the host and edit it before deployment: use site/device IDs of at most 32 characters, unique MQTT client IDs and topic roots, matching broker maps, RTSP URLs/codecs, the pinned vehicle640 model path/SHA, slot polygons mapped to stream IDs, and an existing state path. Each preset also requires a locally built image, writable data directory, DRM device, and user-supplied RKNN/RGA/MPP host paths. The conversion artifacts are recorded by SHA but remain device-unverified and are not bundled or downloaded. H.264 is the default stream codec; H.265 is selected with per-stream `options.codec`. Slot messages use `<site>/parking/<camera>/slots`, where `<camera>` is the configured stream ID. The native health server binds `0.0.0.0:8099`; use the RK host's reachable address for a remote `/healthz` check.
