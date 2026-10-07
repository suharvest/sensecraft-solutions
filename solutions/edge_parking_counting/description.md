# Edge Parking Vehicle Counting

> **Draft / blocked artifact.** This package is disabled until the native
> `SlotsApp`/counting application, public image or approved local build input,
> model artifact, and Jetson acceptance evidence are available. No image,
> model, broker, or host proprietary library is bundled here.

This design counts cars, motorcycles, buses, and trucks crossing a configured
entrance line. The native TensorRT runtime performs capture, decode, inference,
tracking, and line analysis. The parking event layer publishes crossing and
occupancy messages through an external MQTT broker.

The current draft documents the Jetson deployment contract only. CPU execution
is a reference path and does not constitute platform validation. Accuracy,
throughput, and end-to-end MQTT acceptance remain open.

## RK3576 and RK3588 staging presets

Two disabled staging presets describe the native RKNN path for reComputer RK3576 and RK3588. Copy the board-specific shipped `assets/config/counting-rk3576.json` or `counting-rk3588.json` to the host and edit it before deployment: use site/device IDs of at most 32 characters, unique MQTT client IDs and topic roots, matching broker maps, RTSP URLs/codecs, the pinned vehicle416 model path/SHA, counting line/direction/capacity, and an existing state path. They also require a locally built image, writable data directory, DRM device, and host RKNN/RGA/MPP paths. The recorded conversion SHA is checked in deployment input documentation, but the artifacts remain device-unverified and are not bundled or downloaded by this package. H.264 is the default stream codec; H.265 is selected per stream through `options.codec`. The native health server binds `0.0.0.0:8099`; use the RK host's reachable address for a remote `/healthz` check.
