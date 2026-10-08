# Deployment Guide

> **Draft / disabled.** Do not deploy this package as a released artifact.

## Preset: Multi-Camera Jetson Occupancy (Draft) {#jetson}

This draft describes an existing RTSP camera set and a Jetson Orin host. The
config must use `core_parking.slots.app:SlotsApp`; `SlotHooks` is not an app
entrypoint. Slot polygons, stream URLs, and the target-device engine are
mounted from the host.

Measured on a Jetson Orin Nano with a locally built image and a synthetic
640x360 clip (parking-lot still 20 s / black 20 s, 1 stream at 1 fps): 0.988 fps
processed, inference p50 6.48 ms / p95 6.69 ms, 0 dropped frames, 15
occupied/free transitions per slot over 300 s. No slot-accuracy figure on real
parking video; multi-stream capacity was not re-measured in this run.

## Step 1: Deploy SlotsApp {#deploy_occupancy type=docker_deploy required=true config=devices/jetson_occupancy.yaml}

The compose file keeps the model and configuration outside the image. CUDA,
TensorRT, NVDEC, and other Jetson ABI libraries remain host-owned. The broker
is an external service.

### Prerequisites

1. JetPack 6 and the NVIDIA container runtime are installed.
2. Each RTSP stream has been tested independently.
3. Copy `assets/config/slots.json` to a host path and edit its streams, MQTT
   broker, site/device IDs, slot polygons, and target engine path.
   Draw each slot polygon around one parking space so that a parked car the detector sees covers at least `occupied_ratio` (0.30) of it. A polygon spanning several small or distant cars stays below that ratio and never reports `occupied`: on the acceptance fixtures a wide ROI gave cover 0.0 (Orin Nano) and 0.11 (RK3588), a single-car ROI gave 0.40–0.45. The shipped `cam-b1-01` polygon matches the acceptance fixture; redraw every polygon for your camera.
4. The image and vehicle640 engine come from an approved local build. Optional
   `health_port` defaults to `8099`; set it to the port in the mounted JSON.
   Optional `memory_limit` defaults to `0` (no Compose cgroup limit); a bounded
   test may set `768m`. Optional `data_dir` defaults to `./data` and must be an
   existing writable directory so state survives container restart. Compose
   keeps a local JSON log cap of 8 MiB × 3. The Jetson precheck requires at least 0.5 GiB
   free on `/`; this path assumes the image, model, and TensorRT engine are
   already cached or staged and uses the space for runtime files, logs, and
   metadata. Prepare additional space separately when loading or building
   those artifacts; this threshold does not certify capacity or accuracy.

### Target {#occupancy_local type=local device=jetson device_name="Jetson" config=devices/jetson_occupancy.yaml}

Run Docker on this Jetson host.

### Target {#occupancy_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_occupancy.yaml default=true}

Connect to this Jetson host over SSH.

## Step 2: Verify SlotsApp health {#verify_occupancy type=http_debug required=true config=devices/health_verify.yaml}

The HTTP verify step automatically checks only that `/healthz` returns HTTP
200. After it passes, manually inspect the response body and open
`http://<host>:<app.options.http.port>/slots/editor` (the stock port is 8080)
to inspect the configured polygons. For a local check use `127.0.0.1`; for a
remote Jetson deployment enter the Jetson host's reachable LAN or Fleet
address. The mounted JSON `health.port`, the deploy `health_port` input, and
the verify `port` input must be the same value; the Docker healthcheck uses
container-local `127.0.0.1` on that port. `memory_limit=0` leaves the service
uncapped; use `768m` only for a bounded test. HTTP 200, body inspection, and
the editor view do not prove slot accuracy, capacity, or multi-camera
acceptance.

## Preset: Multi-Camera RK3576 Occupancy (Draft) {#rk3576}

This disabled preset requires a locally reviewed native RK image, the RK3576-targeted vehicle640 RKNN artifact, slot configuration, and matching host ABI paths. The conversion remains device-unverified.

## Step 1: Deploy RK3576 SlotsApp {#deploy_rk3576_occupancy type=docker_deploy required=true config=devices/rk3576_occupancy.yaml}

The app uses BGR 0–255 input, top-left padding, YOLOX COCO-80 decoding, two RKNN contexts, and default H.264 streams. Set each stream's `options.codec` to `h265` for H.265 input.

Before deployment, copy the shipped `assets/config/slots-rk3576.json` to the RK3576 host and pass that host path as `PARKING_CONFIG`. Edit the copied JSON: keep `site_id` and `device_id` at 32 characters or fewer; make `mqtt.client_id` and `mqtt.topic_root` unique; set both the top-level `mqtt` map and `app.options.mqtt` to the real broker host, port, username, and password (leave username and password empty when the broker is anonymous); set every RTSP URL and each stream's `options.codec` to `h264` or `h265`; set `backend.model_path` and `backend.model_sha256` to the pinned vehicle640 artifact; define slot polygons under `app.options.slots` and map each polygon set to its stream ID; and set an existing writable `app.options.state_dir`. Use the already-edited file as the `parking_config` input. Draw each slot polygon around one parking space so that a parked car the detector sees covers at least `occupied_ratio` (0.30) of it. A polygon spanning several small or distant cars stays below that ratio and never reports `occupied`: on the acceptance fixtures a wide ROI gave cover 0.0 (Orin Nano) and 0.11 (RK3588), a single-car ROI gave 0.40–0.45. The shipped RK3576 polygons are placeholders; redraw every polygon for your camera.

### Target {#rk3576_occupancy_local type=local device=rk3576_occupancy device_name="RK3576" config=devices/rk3576_occupancy.yaml}

Run Docker on the RK3576 host after the required-path precheck passes.

### Target {#rk3576_occupancy_remote type=remote device=rk3576_occupancy device_name="RK3576" config=devices/rk3576_occupancy.yaml default=true}

Connect to the RK3576 host over SSH.

## Step 2: Verify RK3576 SlotsApp health {#verify_rk3576_occupancy type=http_debug required=true config=devices/health_verify_rk.yaml}

Require HTTP 200 from `/healthz`. For a local check, use `127.0.0.1`; for a remote RK deployment, enter the RK board's reachable LAN or Fleet address. The verifier does not inherit the engine SSH host automatically. The app binds its health server to `0.0.0.0:8099`, while the compose healthcheck continues to probe container-local `127.0.0.1:8099`. This does not prove slot accuracy or device verification.

## Preset: Multi-Camera RK3588 Occupancy (Draft) {#rk3588}

This disabled preset requires a locally reviewed native RK image, the RK3588-targeted vehicle640 RKNN artifact, slot configuration, and matching host ABI paths. Measured on a Radxa Rock 5T (RK3588) with a locally built image (6a5c781d) and a synthetic occupied/empty fixture (1 stream at 1 fps, single-car ROI): 17 occupied/free state changes, inference p50 36.6 ms / p95 40.5 ms, 0 dropped frames. No slot-accuracy figure; multi-stream capacity was not measured. The compose mounts the host RGA library as `librga.so.2` and the host GStreamer runtime plus `h264parse` (`gstreamer1.0-plugins-bad`) from `parking_host_lib_dir` (default `/lib/aarch64-linux-gnu`). The stock `app.options.http.port` is 8080 under host networking; change it when another service on the host already uses 8080.

## Step 1: Deploy RK3588 SlotsApp {#deploy_rk3588_occupancy type=docker_deploy required=true config=devices/rk3588_occupancy.yaml}

The app uses three RKNN contexts on RK3588. The default stream codec is H.264; set `options.codec` to `h265` when the camera input is H.265.

Before deployment, copy the shipped `assets/config/slots-rk3588.json` to the RK3588 host and pass that host path as `PARKING_CONFIG`. Edit the copied JSON: keep `site_id` and `device_id` at 32 characters or fewer; make `mqtt.client_id` and `mqtt.topic_root` unique; set both the top-level `mqtt` map and `app.options.mqtt` to the real broker host, port, username, and password (leave username and password empty when the broker is anonymous); set every RTSP URL and each stream's `options.codec` to `h264` or `h265`; set `backend.model_path` and `backend.model_sha256` to the pinned vehicle640 artifact; define slot polygons under `app.options.slots` and map each polygon set to its stream ID; and set an existing writable `app.options.state_dir`. Use the already-edited file as the `parking_config` input. Draw each slot polygon around one parking space so that a parked car the detector sees covers at least `occupied_ratio` (0.30) of it. A polygon spanning several small or distant cars stays below that ratio and never reports `occupied`: on the acceptance fixtures a wide ROI gave cover 0.0 (Orin Nano) and 0.11 (RK3588), a single-car ROI gave 0.40–0.45. The shipped `cam-b1-01` polygon matches the acceptance fixture; redraw every polygon for your camera.

### Target {#rk3588_occupancy_local type=local device=rk3588_occupancy device_name="RK3588" config=devices/rk3588_occupancy.yaml}

Run Docker on the RK3588 host after the required-path precheck passes.

### Target {#rk3588_occupancy_remote type=remote device=rk3588_occupancy device_name="RK3588" config=devices/rk3588_occupancy.yaml default=true}

Connect to the RK3588 host over SSH.

## Step 2: Verify RK3588 SlotsApp health {#verify_rk3588_occupancy type=http_debug required=true config=devices/health_verify_rk.yaml}

Require HTTP 200 from `/healthz`. For a local check, use `127.0.0.1`; for a remote RK deployment, enter the RK board's reachable LAN or Fleet address. The verifier does not inherit the engine SSH host automatically. The app binds its health server to `0.0.0.0:8099`, while the compose healthcheck continues to probe container-local `127.0.0.1:8099`. This does not prove slot accuracy, device verification, or formal multi-camera acceptance.
