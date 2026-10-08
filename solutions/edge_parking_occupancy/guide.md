# Deployment Guide

> **Draft / disabled.** Do not deploy this package as a released artifact.

## Preset: IP Cameras + Edge Compute Box (Draft) {#ip_camera_box}

This draft describes an existing RTSP camera set and an edge host. Pick the
host in the deploy step: Jetson Orin (TensorRT), RK3588 or RK3576 (RKNN). The
config must use `core_parking.slots.app:SlotsApp`; `SlotHooks` is not an app
entrypoint. Slot polygons, stream URLs, and the target-device model are mounted
from the host. Each target states its on-device acceptance status.

## Step 1: Deploy SlotsApp {#deploy_occupancy type=docker_deploy required=true config=devices/jetson_occupancy.yaml}

The compose file keeps the model and configuration outside the image. On
Jetson, CUDA, TensorRT, NVDEC, and other Jetson ABI libraries remain
host-owned. The broker is an external service.

On RK3576 the app uses BGR 0–255 input, top-left padding, YOLOX COCO-80
decoding, and two RKNN contexts; on RK3588 it uses three RKNN contexts. The
default stream codec is H.264; set each stream's `options.codec` to `h265` for
H.265 input.

Draw each slot polygon around one parking space so that a parked car the detector sees covers at least `occupied_ratio` (0.30) of it. A polygon spanning several small or distant cars stays below that ratio and never reports `occupied`: on the acceptance fixtures a wide ROI gave cover 0.0 (Orin Nano) and 0.11 (RK3588), a single-car ROI gave 0.40–0.45. The shipped `cam-b1-01` polygon (Jetson and RK3588 configs) matches the acceptance fixture; the shipped RK3576 polygons are placeholders. Redraw every polygon for your camera.

### Prerequisites

1. Each RTSP stream has been tested independently.
2. **Jetson:** JetPack 6 and the NVIDIA container runtime are installed. Copy
   `assets/config/slots.json` to a host path and edit its streams, MQTT
   broker, site/device IDs, slot polygons, and target engine path. The image
   and vehicle640 engine are the published 2026-10-08 artifacts, fetched at deploy time. Optional
   `health_port` defaults to `8099`; set it to the port in the mounted JSON.
   Optional `memory_limit` defaults to `0` (no Compose cgroup limit); a bounded
   test may set `768m`. Optional `data_dir` defaults to `./data` and must be an
   existing writable directory so state survives container restart. Compose
   keeps a local JSON log cap of 8 MiB × 3. The Jetson precheck requires at least 0.5 GiB
   free on `/`; this path assumes the image, model, and TensorRT engine are
   already cached or staged and uses the space for runtime files, logs, and
   metadata. Prepare additional space separately when loading or building
   those artifacts; this threshold does not certify capacity or accuracy.
3. **RK3576 / RK3588:** the published native RK image and the board-targeted
   vehicle640 RKNN bundle (both fetched at deploy time), slot configuration, and matching host ABI paths.
   Copy the shipped `assets/config/slots-rk3576.json` or
   `assets/config/slots-rk3588.json` to the RK host and pass that host path as
   `PARKING_CONFIG`. Edit the copied JSON: keep `site_id` and `device_id` at 32 characters or fewer; make `mqtt.client_id` and `mqtt.topic_root` unique; set both the top-level `mqtt` map and `app.options.mqtt` to the real broker host, port, username, and password (leave username and password empty when the broker is anonymous); set every RTSP URL and each stream's `options.codec` to `h264` or `h265`; set `backend.model_path` and `backend.model_sha256` to the pinned vehicle640 artifact; define slot polygons under `app.options.slots` and map each polygon set to its stream ID; and set an existing writable `app.options.state_dir`. Use the already-edited file as the `parking_config` input.
4. **RK3588:** the compose mounts the host RGA library as `librga.so.2` and the host GStreamer runtime plus `h264parse` (`gstreamer1.0-plugins-bad`) from `parking_host_lib_dir` (default `/lib/aarch64-linux-gnu`). The stock `app.options.http.port` is 8080 under host networking; change it when another service on the host already uses 8080.

### Target {#occupancy_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_occupancy.yaml default=true}

The prebuilt TensorRT engines are for Jetson Orin Nano (P3767-0003 / P3767-0004) on L4T R36.4 (JetPack 6.2) with TensorRT 10.3; the deploy step stops on any other module or JetPack version.

Connect to this Jetson host over SSH. Verified 2026-10-08 on a Jetson Orin
Nano with a locally built image and a synthetic 640x360 clip (parking-lot still
20 s / black 20 s, 1 stream at 1 fps): 0.988 fps processed, inference p50
6.48 ms / p95 6.69 ms, 0 dropped frames, 15 occupied/free transitions per slot
over 300 s. No slot-accuracy figure on real parking video; multi-stream
capacity was not re-measured in this run.

### Target {#occupancy_local type=local device=jetson device_name="Jetson" config=devices/jetson_occupancy.yaml}

The prebuilt TensorRT engines are for Jetson Orin Nano (P3767-0003 / P3767-0004) on L4T R36.4 (JetPack 6.2) with TensorRT 10.3; the deploy step stops on any other module or JetPack version.

Run Docker on this Jetson host. Verified 2026-10-08 on a Jetson Orin Nano:
0.988 fps processed (1 stream at 1 fps), inference p50 6.48 ms / p95 6.69 ms,
0 dropped frames. No slot-accuracy figure on real parking video.

### Target {#rk3588_occupancy_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_occupancy.yaml}

Connect to the RK3588 host over SSH. Verified with conditions on 2026-10-08:
measured on a Radxa Rock 5T (RK3588) with a locally built image (6a5c781d) and
a synthetic occupied/empty fixture (1 stream at 1 fps, single-car ROI): 17
occupied/free state changes, inference p50 36.6 ms / p95 40.5 ms, 0 dropped
frames. No slot-accuracy figure; multi-stream capacity was not measured.

### Target {#rk3588_occupancy_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_occupancy.yaml}

Run Docker on the RK3588 host after the required-path precheck passes.
Verified with conditions on 2026-10-08 (Radxa Rock 5T, 1 stream at 1 fps): 17
occupied/free state changes, inference p50 36.6 ms / p95 40.5 ms. No
slot-accuracy figure.

### Target {#rk3576_occupancy_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_occupancy.yaml}

Connect to the RK3576 host over SSH. Acceptance blocked: on the 2026-10-08
test board the package image could not be loaded (root disk too small), so the
package compose path was not exercised; a run with a substitute image produced
slot events but no occupied transition.

### Target {#rk3576_occupancy_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_occupancy.yaml}

Run Docker on the RK3576 host after the required-path precheck passes.
Acceptance blocked: the package image could not be loaded on the RK3576 test
board.

## Step 2: Verify SlotsApp health {#verify_occupancy type=http_debug required=true config=devices/health_verify.yaml}

The HTTP verify step automatically checks only that `/healthz` returns HTTP
200. After it passes, manually inspect the response body and open
`http://<host>:<app.options.http.port>/slots/editor` (the stock port is 8080)
to inspect the configured polygons. For a local check use `127.0.0.1`; for a
remote deployment enter the host's reachable LAN or Fleet address — the
verifier does not inherit the engine SSH host automatically. On Jetson, the
mounted JSON `health.port`, the deploy `health_port` input, and the verify
`port` input must be the same value; the Docker healthcheck uses
container-local `127.0.0.1` on that port. `memory_limit=0` leaves the service
uncapped; use `768m` only for a bounded test. On RK3576 / RK3588 the app binds
its health server to `0.0.0.0:8099`, so keep the verify `port` at `8099`; the
compose healthcheck continues to probe container-local `127.0.0.1:8099`. HTTP
200, body inspection, and the editor view do not prove slot accuracy,
capacity, device verification, or multi-camera acceptance.
