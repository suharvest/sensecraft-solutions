# Deployment Guide

> **Draft / disabled.** Do not deploy this package as a released artifact.

## Preset: IP Camera + Edge Compute Box (Draft) {#ip_camera_box}

This preset is a reviewable deployment contract for an existing RTSP gate
camera and an edge host. Pick the host in the deploy step: Jetson Orin
(TensorRT), RK3588 or RK3576 (RKNN). Every target requires a locally built
image, a target-device model, a JSON configuration, and an external MQTT
broker. Each target states its on-device acceptance status.

## Step 1: Deploy the native counting app {#deploy_counting type=docker_deploy required=true config=devices/jetson_counting.yaml}

The compose file mounts the host configuration and model directory. The image
must contain the native `vb-runtime` and the standard-library parking event
layer. On Jetson, CUDA, TensorRT, NVDEC, and other Jetson ABI libraries remain
host-owned.

On RK3576 the app uses BGR 0–255 input, top-left padding, YOLOX COCO-80
decoding, and two RKNN contexts; on RK3588 it uses three RKNN contexts with the
same input. The default stream codec is H.264; set `options.codec` to `h265` in
the config for an H.265 camera.

### Prerequisites

1. The RTSP URL has been tested independently.
2. **Jetson:** JetPack 6 and the NVIDIA container runtime are installed.
   Copy `assets/config/counting.json` to a host path and edit its RTSP stream,
   MQTT broker, site/device IDs, counting line, and target engine path.
   `PARKING_IMAGE`, `PARKING_CONFIG`, and `PARKING_MODELS_DIR` point to local,
   reviewed inputs. Optional `health_port` defaults to `8099`; set it to the
   port in the mounted JSON. Optional `memory_limit` defaults to `0` (no
   Compose cgroup limit); a bounded test may set `768m`. Optional `data_dir`
   defaults to `./data` and must be an existing writable directory so state
   survives container restart. Compose keeps a local JSON log cap of 8 MiB × 3. The Jetson precheck requires at least 0.5 GiB
   free on `/`; this path assumes the image, model, and TensorRT engine are
   already cached or staged and uses the space for runtime files, logs, and
   metadata. Prepare additional space separately when loading or building
   those artifacts; this threshold does not certify capacity or accuracy.
3. **RK3576 / RK3588:** a locally reviewed native RK image, the board-targeted
   vehicle416 RKNN artifact, a matching `vb.config/1` file, and host ABI paths.
   Copy the shipped `assets/config/counting-rk3576.json` or
   `assets/config/counting-rk3588.json` to the RK host and pass that host path
   as `PARKING_CONFIG`. Edit the copied JSON: keep `site_id` and `device_id` at 32 characters or fewer; make `mqtt.client_id` and `mqtt.topic_root` unique; set both the top-level `mqtt` map and `app.options.mqtt` to the real broker host, port, username, and password (leave username and password empty when the broker is anonymous); set every RTSP URL and each stream's `options.codec` to `h264` or `h265`; set `backend.model_path` and `backend.model_sha256` to the pinned vehicle416 artifact; set `app.options.counting.line`, direction, and capacity; and set an existing writable `app.options.state_dir`. Use the already-edited file as the `parking_config` input.
4. **RK3588:** the compose mounts the host RGA library as `librga.so.2` and the host GStreamer runtime plus `h264parse` (`gstreamer1.0-plugins-bad`) from `parking_host_lib_dir` (default `/lib/aarch64-linux-gnu`). The stock `app.options.http.port` is 8080 under host networking; change it when another service on the host already uses 8080.

### Target {#counting_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_counting.yaml default=true}

Connect to this Jetson host over SSH. Verified 2026-10-08 on a Jetson Orin
Nano with a locally built image and a synthetic 640x360 30 fps clip (one
vehicle crossing the line every 6 s): 29.98 fps processed, inference p50
3.58 ms / p95 3.64 ms, 41 of 41 expected crossings with alternating directions.
No counting-accuracy figure on real gate video.

### Target {#counting_local type=local device=jetson device_name="Jetson" config=devices/jetson_counting.yaml}

Run Docker on this Jetson host. Verified 2026-10-08 on a Jetson Orin Nano:
29.98 fps processed, inference p50 3.58 ms / p95 3.64 ms, 41 of 41 expected
crossings on a synthetic clip. No counting-accuracy figure on real gate video.

### Target {#rk3588_counting_remote type=remote device=rk3588_counting device_name="RK3588" config=devices/rk3588_counting.yaml}

Connect to the RK3588 host over SSH. Verified with conditions on 2026-10-08:
measured on a Radxa Rock 5T (RK3588) with a locally built image (6a5c781d) and
a looped 1280x720 H.264 5 fps parking-lot clip: 3.0 fps processed of the 5 fps
source (about 26 % of frames dropped, cause not diagnosed), inference p50
17.8 ms / p95 20.0 ms, 107 MQTT events with contiguous seq. The clip repeats
every 10 s, so no counting-accuracy figure is stated.

### Target {#rk3588_counting_local type=local device=rk3588_counting device_name="RK3588" config=devices/rk3588_counting.yaml}

Run Docker on the RK3588 host after the fail-closed host path precheck passes.
Verified with conditions on 2026-10-08 (Radxa Rock 5T): 3.0 fps processed of
the 5 fps source (about 26 % of frames dropped, cause not diagnosed), inference
p50 17.8 ms / p95 20.0 ms. No counting-accuracy figure.

### Target {#rk3576_counting_remote type=remote device=rk3576_counting device_name="RK3576" config=devices/rk3576_counting.yaml}

Connect to the RK3576 host over SSH. The same path and ABI checks run on the
remote host. Acceptance blocked: on the 2026-10-08 test board the package
image could not be loaded (root disk too small), so the package compose path
was not exercised; a run with a substitute image produced MQTT crossing events.

### Target {#rk3576_counting_local type=local device=rk3576_counting device_name="RK3576" config=devices/rk3576_counting.yaml}

Run Docker on the RK3576 host. The precheck requires every supplied path and
the exact vehicle416 model filename to exist. Acceptance blocked: the package
image could not be loaded on the RK3576 test board.

## Step 2: Verify native health {#verify_counting type=http_debug required=true config=devices/health_verify.yaml}

The HTTP verify step automatically checks only that `/healthz` returns HTTP
200. After it passes, inspect the response body manually for the runtime and
parking hook fields. For a local check use `127.0.0.1`; for a remote
deployment enter the host's reachable LAN or Fleet address — the verifier does
not inherit the engine SSH host automatically. On Jetson, the mounted JSON
`health.port`, the deploy `health_port` input, and the verify `port` input must
be the same value; the Docker healthcheck uses container-local `127.0.0.1` on
that port. `memory_limit=0` leaves the service uncapped; use `768m` only for a
bounded test. On RK3576 / RK3588 the app binds its health server to
`0.0.0.0:8099`, so keep the verify `port` at `8099`; the compose healthcheck
continues to probe container-local `127.0.0.1:8099`. HTTP 200 and the body
check do not prove accuracy, RKNN device compatibility, or platform
acceptance.
