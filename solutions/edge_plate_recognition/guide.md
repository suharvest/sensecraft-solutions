# Edge License Plate Recognition — Deployment Guide

> **Draft (staging).** Only the Jetson target of the IP camera preset has
> passed on-device acceptance (deployment and output path, 2026-10-08). Models,
> images and the app package for the other presets and targets are still being
> produced by the platform tasks. Steps below are the intended deployment flow
> and will be re-validated on hardware before this page loses its Draft badge.

## Preset: reCamera Pro (Recommended) {#recamera_pro}

One camera does detection, recognition and MQTT events on device. Add a
reComputer R1124-10 when you want whitelist-based barrier opening.

## Step 1: Install Plate Recognition {#deploy_pro type=recamera_pro_app required=true config=devices/recamera_pro_plate.yaml}

Configure the plate recognition app on the reCamera Pro and make it the active
app. The app itself ships through the device's App Center.

### Prerequisites

1. The reCamera Pro is on your network and you can sign in to its web console.
2. A mounting point 3–8 m from the lane where plates are legible. The camera
   needs a 12 V supply — it does not support PoE.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| App not found on the device | The app package is still in staging — install it from the App Center once published, then rerun this step |
| No plate events | Draw the lane ROI on the preview page; plates outside the ROI are not read |
| Plates misread at night | Add IR/white illumination at the gate; check the preview at night before trusting the whitelist |

## Step 2: Watch Recognition Results {#view_pro type=web_dashboard required=false config=devices/dashboard.yaml}

Open the live preview — plates boxed, latest reads listed. A plate event with a
snapshot URL on the MQTT topic means the pipeline works end to end.

## Step 3: Install the Gate Controller (optional) {#gate_pro type=script required=false config=devices/gate_controller.yaml}

Installs the MQTT broker and the gate service on the reComputer R1124-10. The
gate service subscribes to plate events, matches the whitelist and pulses the
digital output — cooldown-guarded, and it never replays old events into the
barrier.

## Step 4: Wire the Barrier Gate (optional) {#wire_pro type=manual required=false config=devices/gate_wiring.yaml}

Wire the R1124-10 digital output through an interposing relay to the barrier's
OPEN input, then upload the whitelist and fire a test pulse.

---

## Preset: reCamera 2002 HQ PoE (Minimum) {#recamera_2002}

The lowest-cost setup: one PoE camera on the gate. Whether it runs full
on-device recognition or detect-only plus host-side recognition on the R1124
is decided by the platform acceptance tests — the measured form will be stated
here.

## Step 1: Install Plate Recognition {#deploy_2002 type=recamera_cpp required=true config=devices/recamera_plate.yaml}

Install the plate recognition package (detector, recognizer, plugin) on the
reCamera 2002 and start it.

### Prerequisites

1. The reCamera 2002 is reachable over the network (USB default
   `192.168.42.1`) and you have its SSH password.
2. A mounting point 3–8 m from the lane; PoE switch or injector for power.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Service exits immediately | Another camera app is still running; only one app can hold the camera — reboot and retry |
| Node-RED stopped working after install | Expected — installing takes the camera from Node-RED and any other vision app |
| No plate events | Check the ROI covers the lane on the preview page, and that the camera can resolve plates at your mounting distance |

## Step 2: Watch Recognition Results {#view_2002 type=web_dashboard required=false config=devices/dashboard.yaml}

Open the live preview — plates boxed, latest reads listed.

## Step 3: Install the Gate Controller (optional) {#gate_2002 type=script required=false config=devices/gate_controller.yaml}

Installs the MQTT broker and the gate service on the reComputer R1124-10. In
detect-only fallback mode this host also runs the host-side recognizer
(plate-host), so for the 2002 the R1124 is effectively part of the pipeline,
not just the gate.

## Step 4: Wire the Barrier Gate (optional) {#wire_2002 type=manual required=false config=devices/gate_wiring.yaml}

Wire the R1124-10 digital output through an interposing relay to the barrier's
OPEN input, then upload the whitelist and fire a test pulse.

---

## Preset: IP Camera + Edge Compute Box {#ip_camera_box}

Keep your existing gate cameras — an edge compute box pulls the RTSP stream
and runs detection and recognition. Pick the box in the deploy step: Jetson
(TensorRT FP16), RK3588 or RK3576 (RKNN INT8 on the NPU), or R2035-12
(Hailo-8). Each target states its on-device acceptance status.

## Step 1: Deploy Plate Recognition {#deploy_host type=docker_deploy required=true config=devices/jetson_plate.yaml}

Deploy the recognition stack on the selected host. The Jetson target uses the
published parking image and the published detector and CN recognizer TensorRT
engine bundle (built on Orin Nano, JetPack 6.2.1); the RK3588 and RK3576
targets use the published RKNN bundles; the R2035 target uses the published HEF
bundle. Model bundles are downloaded and SHA-256 checked at deploy time.

### Prerequisites

1. Your gate camera's RTSP URL, credentials included if it requires them.
2. The camera mounted 3–8 m from the lane, 1080p or better.
3. **Jetson:** JetPack 6.x with the NVIDIA container runtime available. At
   least 0.5 GiB free disk beyond the image and engines. The published parking
   image and engine bundle are fetched at deploy time; you supply a rendered
   `vb.config/1` file. Optional `health_port` defaults
   to `8099` and must match `health.port` in the mounted JSON; change both when
   8099 is already taken on the host. Optional `memory_limit` (default `0`, no
   limit) and `data_dir` (default `./data`, existing writable directory for
   state and snapshots) match the counting package.
4. **RK3588 / RK3576:** the RKNN runtime (librknnrt), Rockchip MPP/RGA and the
   GStreamer `h264parse` plugin (`gstreamer1.0-plugins-bad`) are installed on the
   board — the container uses these host libraries, and the deploy step checks
   they exist. At least 6 GB free disk. The container uses host networking:
   ports 8099 (health) and 8080 (app HTTP, `app.options.http.port` in
   `config/plate.json`) must be free.
5. **R2035 (Hailo-8):** the Hailo-8 driver and HailoRT are installed, and
   `/dev/hailo0` exists. HailoRT must match the driver version — you fetch it
   yourself from the Hailo Developer Zone. At least 6 GB free disk.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |
| Jetson: engine or runtime validation fails | Confirm the supplied image, config, target-device engine directory, NVIDIA runtime, and at least 0.5 GiB free disk |
| Jetson: container restarts repeatedly | Check the logs for the engine path; delete a half-built engine from an interrupted run |
| RK3588 / RK3576: librknnrt not found | Install the RKNN runtime (rknpu2) for this board first |
| RK3588: NPU idle in the logs | Confirm the RKNN model files downloaded completely — a truncated model falls back or fails loudly |
| R2035: /dev/hailo0 not found | Load the Hailo-8 driver before deploying |
| R2035: HailoRT version mismatch | Install the HailoRT package matching your driver — the pre-check prints the versions it found |
| R2035: recognition on CPU | Expected when two network groups cannot share the device; accuracy is unaffected, throughput is lower |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_plate.yaml default=true}

Deploy to the Jetson over SSH from this computer. Verified 2026-10-08 on a
Jetson Orin Nano (deployment and output path) with a locally built image and a
1080p 30 fps RTSP slideshow of 40 labelled CCPD stills: 29.86 fps processed at
1080p, detector inference p50 5.61 ms / p95 5.75 ms, 56 `parking.plate/1` MQTT
events with JPEG snapshots. Recognition accuracy is not accepted yet: the
formal Chinese plate corpus (day and night) has not been run, so no accuracy
figure is stated.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_plate.yaml}

Run this directly on the Jetson if you are working on the device itself.
Verified 2026-10-08 on a Jetson Orin Nano (deployment and output path): 29.86
fps at 1080p, detector p50 5.61 ms / p95 5.75 ms, 56 `parking.plate/1` events
with snapshots. Recognition accuracy is not accepted yet.

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml}

Deploy to the RK3588 over SSH from this computer. Verified 2026-10-08 on an
RK3588 board (deployment and output path): this target's check, bundle and
config steps, its compose file, the published `nrd-parking-rk:20261008` image and
the published RK3588 model bundle, fed a 1080p 30 fps RTSP slideshow of 40
labelled CCPD stills, produced 36 `parking.plate/1` MQTT events with JPEG
snapshots in about 160 s. Recognition accuracy is not accepted yet.

### Target {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml}

Run this directly on the RK3588 if you are working on the device itself. Uses
the same compose file, config and model bundle as the SSH target, which was
verified 2026-10-08 (36 `parking.plate/1` events with snapshots); the local
deploy path itself was not run. Recognition accuracy is not accepted yet.

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml}

Deploy to the RK3576 over SSH from this computer. Verified 2026-10-08 on an
RK3576 board (deployment and output path): this target's check, bundle and
config steps, its compose file, the published `nrd-parking-rk:20261008` image and
the published RK3576 model bundle, fed the same 1080p 30 fps slideshow, produced
44 `parking.plate/1` MQTT events with JPEG snapshots in about 170 s. Recognition
accuracy is not accepted yet.

### Target {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml}

Run this directly on the RK3576 if you are working on the device itself. Uses
the same compose file, config and model bundle as the SSH target, which was
verified 2026-10-08 (44 `parking.plate/1` events with snapshots); the local
deploy path itself was not run. Recognition accuracy is not accepted yet.

### Target {#hailo_remote type=remote device=hailo device_name="R2035 (Hailo-8)" config=devices/hailo_plate.yaml}

Deploy to the R2035 over SSH from this computer. Acceptance blocked: the runtime
image `sensecraft/edge-parking-hailo:0.1.0-draft` has not been built, and the
vision runtime's Hailo backend does not yet accept the plate detector's
per-level outputs without a patch.

### Target {#hailo_local type=local device=hailo device_name="R2035 (Hailo-8)" config=devices/hailo_plate.yaml}

Run this directly on the R2035 if you are working on the device itself.
Acceptance blocked: the runtime image is not built and the Hailo backend needs
a patch for the plate detector.

## Step 2: Watch Recognition Results {#view_host type=web_dashboard required=false config=devices/dashboard.yaml}

Open the live preview — plates boxed, latest reads listed.

## Step 3: Install the Gate Controller (optional) {#gate_host type=script required=false config=devices/gate_controller.yaml}

Installs the MQTT broker and the gate service on the reComputer R1124-10. Point
the recognition host's MQTT broker host at the R1124 when you use this.

## Step 4: Wire the Barrier Gate (optional) {#wire_host type=manual required=false config=devices/gate_wiring.yaml}

Wire the R1124-10 digital output through an interposing relay to the barrier's
OPEN input, then upload the whitelist and fire a test pulse.
