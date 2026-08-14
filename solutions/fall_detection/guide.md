## Preset: reCamera 2002 {#recamera}

One device does everything: the camera sees the room, decides on-device whether
someone fell, and publishes the event over MQTT.

| Device | Purpose |
|--------|---------|
| reCamera 2002 | Pose estimation, temporal fall logic, RTSP and MQTT, all local |

**Important:** this is an assistive alert, not a certified medical or
life-safety system. On the untouched 27-clip Subject 4 test it reached 74.1%
accuracy and 83.3% fall recall; on an independent external set recall was 58.8%.
Long shots, occlusion, low light and fall-like floor activities remain weak cases.

## Step 1: Update the reCamera Console {#update_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

Install console 0.5.5, which manages the camera apps. Already current? It's skipped.

### Prerequisites

1. Connect the reCamera over USB, or put it on the same network as this computer.
2. Over USB the address is `192.168.42.1`; over Wi-Fi use the IP your router shows.
3. The default password is `recamera` (older units use `recamera.2`).
4. Nothing is reinstalled if the console is already 0.5.5 — the version is checked before anything is touched, and the step reports itself as skipped.
5. The console is what turns fall detection on and off in the camera's app gallery, and what switches between vision apps, so it has to be current before the next step.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | Confirm SSH is enabled and the IP and password are correct |
| Console page does not load after install | Give it 30 seconds to restart, then reload `http://<camera-ip>/` |
| Password rejected | Try `recamera.2`; units shipped with older firmware use it |

---

## Step 2: Install Fall Detection {#deploy_recamera_fall type=recamera_cpp required=true config=devices/recamera_fall.yaml}

Install the pose model and the fall detector, then start it on the camera.

### Wiring

![Camera placement: a side or corner view at 2–3 m works; straight-down and long-shot or occluded views do not.](gallery/camera-placement.svg)

1. Mount the camera rigidly with a clear, wide view of the area you want covered.
2. Keep the whole person — especially shoulders and hips — visible along the path where a fall would happen.
3. Aim for a side or corner view of the floor area rather than looking straight down.
4. Point it at circulation space, not primarily at a bed or an exercise area — everyday floor activities there read as falls until you have validated them separately.
5. Expect it to detect the fall itself, not the aftermath: starting it while someone is already lying down reports the posture but raises no event.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Service exits immediately | Another camera app is still running; only one app can hold the camera, so reboot and retry |
| Node-RED stopped working after install | Expected — installing takes the camera from Node-RED and any other vision app |
| Falls are missed | Widen the view, improve lighting, keep shoulders and hips visible before and after impact |
| Push-ups trigger an alert | A known fall-like activity; change the view or add downstream human confirmation |
| No MQTT messages | Confirm port 1883 is reachable from your computer and the topic is `recamera/fall-detection/results` |

---

## Step 3: Watch Fall Status {#preview_recamera_fall type=preview required=false config=devices/preview_recamera_fall.yaml}

Click **Connect** to see the skeleton, the state and the event number live.

### Deployment Complete

The camera is ready for a supervised site trial. Alerts and diagnostics go to
`recamera/fall-detection/results`, and Home Assistant discovery exposes the fall
state, event ID and person presence.

#### Quick verification

1. Click **Connect** and wait for the video to appear.
2. Walk into view — the skeleton should follow you and the card should read
   `NORMAL`.
3. Lie down deliberately on the floor. Within roughly two seconds the card should
   turn red and show a new event number.

#### Next steps

- Add the camera to Home Assistant — the entities appear automatically once your
  broker is shared with it.
- Run a site acceptance test with representative falls and normal activity before
  enabling any notification workflow.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Overlay appears before video | MQTT connects faster than RTSP; wait a few seconds |
| Skeleton disappears near the floor | Reframe the camera; a short post-impact gap is tolerated, long occlusion cannot be classified |
| No overlay at all | Confirm MQTT port 1883 is reachable and the topic matches |

---

## Preset: IP Camera + reComputer J {#jetson}

Keep the cameras you already have. A Jetson Orin pulls their RTSP streams, runs a
larger pose model, and tracks several people per stream independently.

| Device | Purpose |
|--------|---------|
| reComputer J30 / J40 | Pose inference, tracking, fall logic and MQTT for every stream |
| IP camera | Supplies the RTSP video; any ONVIF or RTSP camera works |

**Important:** this is an assistive alert, not a certified medical or
life-safety system. On the untouched 27-clip Subject 4 test the YOLO11m
configuration reached 85.2% accuracy and 100% fall recall; on an independent
external set the deployed recall was 52.9%, limited by pose coverage in long shots
and occlusion.

## Step 1: Deploy Fall Detection {#deploy_jetson_fall type=docker_deploy required=true config=devices/jetson_fall.yaml}

Deploy the detector and build its inference engine on the Jetson. Allow 10–20 min.

### Prerequisites

1. The Jetson runs JetPack 6.x with the NVIDIA container runtime available.
2. At least 10 GB free disk — the pose model and the built engine live on the device.
3. Your IP camera's RTSP URL, including credentials if it requires them, for
   example `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`.
4. Expect the first deploy to spend most of its time building the inference engine on the device. A TensorRT engine is tied to the exact GPU architecture and TensorRT version, so it cannot be shipped prebuilt. Measured on Orin Nano: 461 s for YOLO11s. Later deployments reuse it.
5. Match the pose model to the board — **YOLO11s** for Orin Nano, **YOLO11m** for Orin NX. YOLO11m is the more accurate row in the table on the solution page; YOLO11s leaves more headroom for additional camera streams.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Engine build fails | Confirm `/usr/src/tensorrt/bin/trtexec` exists and the disk has 10 GB free |
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |
| Container restarts repeatedly | Check the logs for the engine path; a half-built engine from an interrupted run must be deleted |
| Deploy cannot connect | Confirm SSH is reachable and the username is right — Seeed images use `recomputer` or `nvidia` |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_fall.yaml default=true}

Deploy to the Jetson over SSH from this computer.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_fall.yaml}

Run this directly on the Jetson if you are working on the device itself.

---

## Step 2: Watch Fall Status {#preview_jetson_fall type=preview required=false config=devices/preview_jetson_fall.yaml}

Click **Connect** to see each tracked person boxed, labelled and state-coloured.

### Deployment Complete

The Jetson is ready for a supervised site trial. Results go to
`recamera/fall-detection/results/<stream-id>`, one topic per camera, so several
cameras stay separable downstream.

#### Quick verification

1. Click **Connect** and wait for the camera's video to appear.
2. Walk into view — a box should follow you, labelled with a track number and
   `NORMAL`.
3. Lie down deliberately. The box should turn red and the card should show a new
   event number.

#### Adding more cameras

The detector handles several streams at once. Add them to the `streams` list in
the configuration on the device and restart the container; each stream keeps its
own tracking state and gets its own MQTT topic.

#### Next steps

- Point your alerting system at the MQTT topic, or add the broker to Home
  Assistant to pick up the discovery entities.
- Measure real throughput before adding streams — the published FPS figures are
  inference-core only and exclude decoding, tracking and MQTT.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the Jetson is reachable |
| Overlay but no video | The preview pulls RTSP straight from the camera; confirm this computer can reach it too |
| Boxes flicker between people | Raise the tracker IoU threshold, or reframe so people overlap less |

---

## Preset: IP Camera + reComputer RK {#rk}

Run the detector on a Rockchip NPU board. Same algorithm and same MQTT output as
the other presets, using the board's own NPU instead of a GPU.

| Device | Purpose |
|--------|---------|
| reComputer RK3576 / RK3588 | Pose inference on the NPU, tracking, fall logic and MQTT |
| IP camera | Supplies the RTSP video; any ONVIF or RTSP camera works |

**Important:** this is an assistive alert, not a certified medical or life-safety
system. Each board runs a temporal profile trained and frozen on its own pose traces.
Accuracy is reported for the solution as a whole on the introduction page — the
27-clip test set cannot separate the platforms, so per-board figures would read
as differences that were not measured.

## Step 1: Deploy Fall Detection {#deploy_rk_fall type=docker_deploy required=true config=devices/rk3588_fall.yaml}

Deploy the detector to your Rockchip board. Allow about 5 minutes.

### Prerequisites

1. The board runs a vendor image with the NPU driver and `librknnrt.so` present, plus Docker.
2. At least 6 GB free disk for the runtime image and the pose model.
3. Your IP camera's RTSP URL, with credentials if it needs them.
4. Choose the deployment target that matches your board. A model compiled for RK3588 does not run on RK3576 or the reverse, so the target selects which model is downloaded — it is not cosmetic.
5. Measured throughput, with other workloads left running on the boards: RK3588 reached 19.3 FPS single-context on blank frames and about 8.6 FPS end to end over RTSP; RK3576 reached 15.2 FPS on a real test image and about 4.9 FPS end to end. These are contention-affected figures, not board maxima.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `librknnrt.so not found` | Install the board's `rknpu2` runtime package; the container mounts the host copy on purpose |
| Model fails to load | The model must match the board — re-run the step with the correct board selected |
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |
| Low frame rate | Other NPU workloads compete for the accelerator; check what else is running before blaming the detector |

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_fall.yaml default=true}

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_fall.yaml}

### Target {#rk_local type=local device=rk3588 device_name="reComputer RK" config=devices/rk_auto_fall.yaml}

---

## Step 2: Watch Fall Status {#preview_rk_fall type=preview required=false config=devices/preview_rk_fall.yaml}

Click **Connect** to see each tracked person boxed, labelled and state-coloured.

### Deployment Complete

The board is publishing to `recamera/fall-detection/results/<stream-id>`, one topic
per camera.

#### Quick verification

1. Click **Connect** and wait for the camera's video to appear.
2. Walk into view — a box should follow you, labelled with a track number.
3. Lie down deliberately. The box should turn red and the card should show a new
   event number.

#### Next steps

- Point your alerting system at the MQTT topic, or add the broker to Home Assistant.
- Before relying on it, run your own acceptance test — the frozen figure measures
  the temporal gate, not the alert your automation actually receives.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the board is reachable |
| Skeleton offset from the person | Report it — this runtime sends coordinates in the letterboxed model space and the preview corrects for it |
| Boxes flicker between people | Raise the tracker IoU threshold, or reframe so people overlap less |

---

## Preset: IP Camera + reComputer R (Hailo) {#hailo}

Run the detector on a Hailo-8 accelerator. The hot path is native C++ with no
Python, so the host CPU stays largely free.

| Device | Purpose |
|--------|---------|
| reComputer R with Hailo-8 | Pose inference on the Hailo-8, tracking, fall logic and MQTT |
| IP camera | Supplies the RTSP video; any ONVIF or RTSP camera works |

**Important:** this is an assistive alert, not a certified medical or life-safety
system. A Hailo-specific temporal profile is frozen, with 92.02% pose coverage on the
held-out test. Accuracy is reported for the solution as a whole on the
introduction page — the 27-clip test set cannot separate the platforms.

## Step 1: Deploy Fall Detection {#deploy_hailo_fall type=docker_deploy required=true config=devices/hailo_fall.yaml}

Deploy the detector to your Hailo-equipped device. Allow about 5 minutes.

### Prerequisites

1. A Hailo-8 accelerator present as `/dev/hailo0`, with **HailoRT 4.21** installed — the GStreamer plugin, the user library and the kernel driver must all be that version.
2. Docker, and at least 4 GB free disk.
3. Your IP camera's RTSP URL, with credentials if it needs them.
4. The pose model is downloaded from the official Hailo Model Zoo during deployment and checked against a pinned digest, so nothing needs to be staged by hand.
5. Nothing else may hold the accelerator — HailoRT contexts are exclusive, so stop any other Hailo application first.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `No /dev/hailo0` | The accelerator is not seated or its driver is not loaded; check `hailortcli fw-control identify` |
| `libhailort.so.4.21.0 not found` | This deployment is ABI-locked to HailoRT 4.21; upgrading means changing plugin, library and driver together |
| Container starts then exits | Another process owns the accelerator; HailoRT contexts are exclusive |
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |

### Target {#hailo_remote type=remote device=hailo device_name="reComputer R" config=devices/hailo_fall.yaml default=true}

Deploy to the device over SSH from this computer.

### Target {#hailo_local type=local device=hailo device_name="reComputer R" config=devices/hailo_fall.yaml}

Run this directly on the device if you are working on it.

---

## Step 2: Watch Fall Status {#preview_hailo_fall type=preview required=false config=devices/preview_hailo_fall.yaml}

Click **Connect** to see each tracked person boxed, labelled and state-coloured.

### Deployment Complete

The device is publishing to `recamera/fall-detection/results/<stream-id>`, one topic
per camera.

#### Quick verification

1. Click **Connect** and wait for the camera's video to appear.
2. Walk into view — a box should follow you, labelled with a track number.
3. Lie down deliberately. The box should turn red and the card should show a new
   event number.

#### Next steps

- Point your alerting system at the MQTT topic, or add the broker to Home Assistant.
- Before relying on it, run your own acceptance test — the frozen figure measures
  the temporal gate, not the alert your automation actually receives.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the device is reachable |
| Overlay but no video | The preview pulls RTSP straight from the camera; confirm this computer can reach it too |
| `inference_time_ms` reads 0 | Expected — the Hailo element does not expose the accelerator call duration at that probe point |
