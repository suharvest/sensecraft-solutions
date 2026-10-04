# Edge License Plate Recognition — Deployment Guide

> **Draft (staging).** No preset here has passed on-device acceptance yet —
> models, images and the app package are still being produced by the platform
> tasks. Steps below are the intended deployment flow and will be re-validated
> on hardware before this page loses its Draft badge.

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

## Preset: IP Camera + reComputer J30 (Jetson) {#jetson}

Keep your existing gate cameras — the Jetson Orin pulls the RTSP stream and
runs detection and recognition with TensorRT FP16.

## Step 1: Deploy Plate Recognition {#deploy_jetson type=docker_deploy required=true config=devices/jetson_plate.yaml}

Deploy the recognition stack on the Jetson. The first deployment builds the
TensorRT engines on the device — allow extra time.

### Prerequisites

1. The Jetson runs JetPack 6.x with the NVIDIA container runtime available.
2. At least 10 GB free disk.
3. Your gate camera's RTSP URL, credentials included if it requires them.
4. The camera mounted 3–8 m from the lane, 1080p or better.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Engine build fails | Confirm the NVIDIA runtime is visible to Docker and the disk has 10 GB free |
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |
| Container restarts repeatedly | Check the logs for the engine path; delete a half-built engine from an interrupted run |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_plate.yaml default=true}

Deploy to the Jetson over SSH from this computer.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_plate.yaml}

Run this directly on the Jetson if you are working on the device itself.

## Step 2: Watch Recognition Results {#view_jetson type=web_dashboard required=false config=devices/dashboard.yaml}

Open the live preview — plates boxed, latest reads listed.

## Step 3: Install the Gate Controller (optional) {#gate_jetson type=script required=false config=devices/gate_controller.yaml}

Installs the MQTT broker and the gate service on the reComputer R1124-10. Point
the Jetson's MQTT broker host at the R1124 when you use this.

## Step 4: Wire the Barrier Gate (optional) {#wire_jetson type=manual required=false config=devices/gate_wiring.yaml}

Wire the R1124-10 digital output through an interposing relay to the barrier's
OPEN input, then upload the whitelist and fire a test pulse.

---

## Preset: IP Camera + reComputer RK3588-30 {#rk3588}

Recommended host form — RKNN INT8 on the RK3588 NPU, with headroom for more
than one lane camera.

## Step 1: Deploy Plate Recognition {#deploy_rk3588 type=docker_deploy required=true config=devices/rk3588_plate.yaml}

Deploy the recognition stack on the RK3588 with its converted RKNN models.

### Prerequisites

1. The RKNN runtime (librknnrt) is installed on the board.
2. At least 6 GB free disk.
3. Your gate camera's RTSP URL, credentials included if it requires them.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| librknnrt not found | Install the RKNN runtime (rknpu2) for this board first |
| No video from the camera | Test the RTSP URL in VLC first |
| NPU idle in the logs | Confirm the RKNN model files downloaded completely — a truncated model falls back or fails loudly |

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml default=true}

Deploy to the RK3588 over SSH from this computer.

### Target {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml}

Run this directly on the RK3588 if you are working on the device itself.

## Step 2: Watch Recognition Results {#view_rk3588 type=web_dashboard required=false config=devices/dashboard.yaml}

Open the live preview — plates boxed, latest reads listed.

## Step 3: Install the Gate Controller (optional) {#gate_rk3588 type=script required=false config=devices/gate_controller.yaml}

Installs the MQTT broker and the gate service on the reComputer R1124-10.

## Step 4: Wire the Barrier Gate (optional) {#wire_rk3588 type=manual required=false config=devices/gate_wiring.yaml}

Wire the R1124-10 digital output through an interposing relay to the barrier's
OPEN input, then upload the whitelist and fire a test pulse.

---

## Preset: IP Camera + reComputer RK3576-30 {#rk3576}

RKNN INT8 on the RK3576 NPU for your existing gate cameras.

## Step 1: Deploy Plate Recognition {#deploy_rk3576 type=docker_deploy required=true config=devices/rk3576_plate.yaml}

Deploy the recognition stack on the RK3576 with its converted RKNN models.

### Prerequisites

1. The RKNN runtime (librknnrt) is installed on the board.
2. At least 6 GB free disk.
3. Your gate camera's RTSP URL, credentials included if it requires them.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| librknnrt not found | Install the RKNN runtime (rknpu2) for this board first |
| No video from the camera | Test the RTSP URL in VLC first |

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml default=true}

Deploy to the RK3576 over SSH from this computer.

### Target {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml}

Run this directly on the RK3576 if you are working on the device itself.

## Step 2: Watch Recognition Results {#view_rk3576 type=web_dashboard required=false config=devices/dashboard.yaml}

Open the live preview — plates boxed, latest reads listed.

## Step 3: Install the Gate Controller (optional) {#gate_rk3576 type=script required=false config=devices/gate_controller.yaml}

Installs the MQTT broker and the gate service on the reComputer R1124-10.

## Step 4: Wire the Barrier Gate (optional) {#wire_rk3576 type=manual required=false config=devices/gate_wiring.yaml}

Wire the R1124-10 digital output through an interposing relay to the barrier's
OPEN input, then upload the whitelist and fire a test pulse.

---

## Preset: IP Camera + reComputer R2035-12 (Hailo-8) {#hailo}

Detection and recognition on a Hailo-8 accelerator for your existing gate
cameras.

## Step 1: Deploy Plate Recognition {#deploy_hailo type=docker_deploy required=true config=devices/hailo_plate.yaml}

Deploy the recognition stack on the R2035 with its compiled HEF models.

### Prerequisites

1. The Hailo-8 driver and HailoRT are installed, and `/dev/hailo0` exists.
   HailoRT must match the driver version — you fetch it yourself from the
   Hailo Developer Zone.
2. At least 6 GB free disk.
3. Your gate camera's RTSP URL, credentials included if it requires them.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| /dev/hailo0 not found | Load the Hailo-8 driver before deploying |
| HailoRT version mismatch | Install the HailoRT package matching your driver — the pre-check prints the versions it found |
| Recognition on CPU | Expected when two network groups cannot share the device; accuracy is unaffected, throughput is lower |

### Target {#hailo_remote type=remote device=hailo device_name="R2035" config=devices/hailo_plate.yaml default=true}

Deploy to the R2035 over SSH from this computer.

### Target {#hailo_local type=local device=hailo device_name="R2035" config=devices/hailo_plate.yaml}

Run this directly on the R2035 if you are working on the device itself.

## Step 2: Watch Recognition Results {#view_hailo type=web_dashboard required=false config=devices/dashboard.yaml}

Open the live preview — plates boxed, latest reads listed.

## Step 3: Install the Gate Controller (optional) {#gate_hailo type=script required=false config=devices/gate_controller.yaml}

Installs the MQTT broker and the gate service on the reComputer R1124-10.

## Step 4: Wire the Barrier Gate (optional) {#wire_hailo type=manual required=false config=devices/gate_wiring.yaml}

Wire the R1124-10 digital output through an interposing relay to the barrier's
OPEN input, then upload the whitelist and fire a test pulse.
