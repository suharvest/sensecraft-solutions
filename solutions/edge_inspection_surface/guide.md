## Preset: IP Camera + reComputer J (Orin) {#orin}

The measured path. A Jetson Orin pulls the camera's RTSP stream, runs YOLOX-Tiny
on TensorRT FP16, and serves the verdict on Modbus TCP and MQTT. The engine is
built on the device during deployment because a TensorRT engine is bound to the
exact GPU architecture and TensorRT version and cannot be shipped prebuilt.

| Device | Purpose |
|--------|---------|
| reComputer J40 / J30 | Inference, OK/NG rule, Modbus TCP server, MQTT publisher, preview page |
| IP camera | Supplies the RTSP video; any RTSP camera framed on the strip or part |
| PLC or line controller | Optional Modbus TCP master that reads the verdict |

**Important:** internal validation only. The model is trained on a re-hosted copy
of NEU-DET whose licence is unconfirmed — do not use this for a public demo, a
customer-site demo or commercial material until that is cleared. The measured
accuracy is mAP50 0.7577 with recall 0.6969 at the deployed 0.35 threshold on
290 validation images, and every number is a single unreproduced measurement.
Known weaknesses: crazing is the weak class at AP50 0.3603 and no threshold
fixes it; frame-level false alarms could not be measured because every image in
the dataset carries a defect; all figures come from a synthetic video, not from
a real camera.

## Step 1: Deploy Surface Inspection {#deploy_jetson_inspection type=docker_deploy required=true config=devices/jetson_inspection.yaml}

Deploy the inspector and build its TensorRT engine on the Jetson. Allow about
10 minutes; the engine build alone measured 291 s on an Orin NX.

### Prerequisites

1. The Jetson runs JetPack 6.x with the NVIDIA container runtime available.
2. At least 10 GB free disk — the ONNX model, the built engine and the container
   image all live on the device.
3. Your camera's RTSP URL including credentials, for example
   `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`. Test it in
   VLC first.
4. **The container image has not been published.** The compose file names
   `sensecraft-missionpack.seeed.cn/solution/edge-inspection-jetson:0.1.1-dev`,
   but nothing has been pushed to that tag. Build it from the upstream repo's
   `platforms/jetson/Dockerfile.slim` on the device and retag it, or set
   `INSPECTION_IMAGE` to your local tag before deploying.
5. **The ONNX model has not been uploaded to the CDN either**, for the same
   licence reason. The deploy step will try to download
   `yolox_tiny_neu6.onnx` and verify sha256
   `4eb5e4ff6144810e919f2a63ad8f7dcd1c1ac5309d207b1d9ff832ba6cd63aba`. Until the
   licence is cleared, place that file at
   `~/edge-inspection-surface/jetson_inspection/models/yolox_tiny_neu6.onnx` on
   the device by hand; the checksum is verified either way.
6. Decide the verdict threshold before you deploy. 0.35 is the frozen value; the
   solution page prices 0.25 and 0.45 against it.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `Static model does not take explicit shapes` during the engine build | This model exports a static batch-1 ONNX, so trtexec must not be given `--minShapes/--optShapes/--maxShapes`. The deploy step already omits them; if you are building by hand with the upstream `build_engine.sh`, set `TRT_STATIC_SHAPE=true` |
| Engine build fails or stops part way | Confirm `/usr/src/tensorrt/bin/trtexec` exists and 10 GB is free. Delete any leftover `.part` file before retrying — a half-built engine is never moved into place, but a stale one blocks the rebuild |
| `numpy.core.multiarray failed to import`, or cv2 fails to import inside the container | Something is mounting the host's python packages over the image's own. Only `/usr/lib/python3.10/dist-packages/tensorrt` may be mounted — the host's numpy 2.x and its broken cv2 will shadow the image's pinned numpy 1.26.4 if the whole `dist-packages` goes in |
| `docker compose` fails reading `._docker-compose.yml`, or the config loader picks up `._config.json` | AppleDouble sidecars travelled with assets uploaded from a macOS machine. The deploy step deletes `._*` and `.DS_Store` from the upload directory; if you copied files by hand, run `find . -name '._*' -delete` in the compose directory |
| No video from the camera | Test the RTSP URL in VLC. A wrong path or wrong credentials is the most common failure |
| sha256 mismatch on the ONNX | The download was truncated or the file is a different build. Delete it and either retry or copy the correct file; do not edit the expected hash |
| Deploy cannot connect over SSH | Confirm SSH is reachable and the username is right — Seeed images use `recomputer`, `nvidia` or `ubuntu` |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_inspection.yaml default=true}

Deploy to the Jetson over SSH from this computer.

### Target {#jetson_local type=local device=jetson device_name="Jetson Orin" config=devices/jetson_inspection.yaml}

Run this directly on the Jetson if you are working on the device itself.

---

## Step 2: Watch the Live Inspection {#preview_orin_inspection type=web_dashboard required=false config=devices/preview_inspection.yaml}

Open the device's own page to see the boxes drawn on the live frames and the
health counters underneath.

### Deployment Complete

The device is running and publishing. Results go to
`<device-name>/inspection/<stream-id>/results` on MQTT port 1883, and the verdict
is on Modbus TCP port 502, unit 1, coils 0 and 1.

#### Quick verification

1. Open `http://<device-ip>:8080/` and confirm the MJPEG preview is moving.
2. Check `http://<device-ip>:8080/healthz` — `inference_time_ms` should be a few
   milliseconds, `frames_dropped` should be 0 at 10 FPS, and `mqtt.rejected`
   should be 0. A non-zero `rejected` means payloads are failing contract
   validation and are being dropped rather than published.
3. Put a defective sample in front of the camera and watch a box appear with its
   class name and score.
4. Subscribe to the topic from another machine:
   `mosquitto_sub -h <device-ip> -t '<device-name>/inspection/#' -v`.

#### The MQTT message

One message per frame, carrying every box in that frame:

```json
{
  "type": "surface_inspection_result",
  "version": "1.0.0",
  "device": "orin-nx",
  "stream_id": "line1-cam1",
  "frame_id": 10423,
  "verdict": "NG",
  "verdict_reason": "2 defect(s) >= min_defects=1",
  "defect_count": 2,
  "primary_class_id": 1,
  "coordinate_space": "normalized_center_wh",
  "inference_time_ms": 6.4,
  "pipeline_ms": 21.8,
  "detections": [
    {"slot": 0, "class_id": 1, "class_name": "inclusion", "score": 0.87,
     "bbox": [0.4125, 0.5312, 0.1094, 0.2031]}
  ]
}
```

`slot` is the within-frame index ordered by score. This pipeline does no
tracking, so `slot` means nothing across frames. `primary_class_id` is `-1` when
there is no defect — note that the Modbus register uses `0` for the same case,
because the holding registers are unsigned 16-bit and cannot carry `-1`.

#### Next steps

- Wire the Modbus coil into your reject or marking station, then run Step 3.
- Point your MES or historian at the MQTT topic. The device publishes only; it
  never writes to a time-series database itself.
- Load-test before adding cameras. Capacity was measured at 8 stable streams on
  an Orin NX with a synthetic 640x640 source, and that measurement ran without
  MQTT or Modbus writes.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The page does not load | Port 8080 is served on the host network. Confirm the container is up (`docker ps`) and that nothing else already holds 8080 |
| Preview moving but no boxes ever appear | Either nothing defective is in frame, or the threshold is too high. Check `/events` for recent verdicts before changing anything |
| `frames_dropped` climbing | The source is delivering faster than the pipeline consumes. An RTSP source drops the oldest frame by design; lower the configured FPS or reduce the stream count |
| `mqtt.rejected` non-zero | Payloads are failing contract validation on the publish path. Check the container logs — this normally means a backend change altered the payload shape |

---

## Step 3: Check the Modbus Output {#plc_check type=manual required=false verify=true config=devices/plc_check.yaml}

Confirm a Modbus master sees what the PLC will act on. Skip this on an
installation that consumes MQTT only.

### Prerequisites

1. A machine on the same network segment that can act as a Modbus TCP master.
2. The device IP, and the unit id you set during deployment (the register map
   below assumes unit 1).

### Deployment Complete

The register map, unit 1 on port 502:

| Address | Meaning |
|---|---|
| Coil 0 | NG, mutually exclusive with coil 1 |
| Coil 1 | OK, mutually exclusive with coil 0 |
| HR 0 | Primary defect class id — the highest-scoring box in the frame; 0 when OK |
| HR 1 | Defect count |
| HR 2 | Primary box cx, normalised x10000 |
| HR 3 | Primary box cy, normalised x10000 |
| HR 4 | Primary box w, normalised x10000 |
| HR 5 | Primary box h, normalised x10000 |
| HR 6 | Heartbeat Unix seconds, high word of a uint32 |
| HR 7 | Heartbeat Unix seconds, low word of a uint32 |

#### Quick verification

1. Poll unit 1 on port 502 and read coils 0-1 and HR 0-7. The upstream repo's
   helper does it directly:
   `python evaluation/read_modbus.py --host <device-ip> --port 502 --unit 1`.
2. Sample continuously while a defective sample passes the camera and watch the
   coil pair flip. On the Orin NX check, 20 Hz sampling caught two transitions.
3. Confirm the coils are never both 1 in the same sample. If you ever read
   `(1,1)`, stop — a PLC latching on either coil would act on a verdict that
   does not exist.
4. On an NG frame, confirm HR 2-5 are within 0-10000 and decode to the same box
   the MQTT message carries. On an OK frame, confirm HR 0-5 are all zero.
5. Confirm HR 6-7 keep advancing on their own interval even when no new verdict
   arrives — the heartbeat is independent of the verdict path, which is what
   lets a PLC tell "no defect" apart from "the inspector died".

#### Next steps

- Latch on the coil, not on the registers: the registers are updated atomically
  first, so by the time the coil flips they already describe that frame.
- Alarm on a stale heartbeat. That is the only signal a Modbus-only integration
  gets when the inspector stops.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused on 502 | Modbus is disabled in the config, or the container is not up. Check `modbus.enabled` in `config/config.json` on the device |
| Registers all zero while MQTT shows detections | You are reading a different unit id than the one written during deployment, or reading during an OK frame |
| Values look plausible but the box is wrong | HR 2-5 are normalised x10000 centre/width/height, not pixels. Divide by 10000 and multiply by the frame size |
| Several cameras but only one set of registers | That is by design — the contract defines one register block, and with several streams the last verdict wins. Per-stream registers need a contract change |

---

## Preset: IP Camera + Raspberry Pi 5 (Hailo-8) {#pi_hailo}

The cheaper board and the unproven path. The INT8 HEF is compiled and its
quantisation loss measured against the compiler's emulator, and the runtime
image cross-builds for arm64 — but nothing here has ever run on a Pi. Three ABI
gates have to pass on the device before the container will start.

| Device | Purpose |
|--------|---------|
| Raspberry Pi 5 + Hailo-8 | Inference, OK/NG rule, Modbus TCP server, MQTT publisher, preview page |
| IP camera | Supplies the RTSP video; any RTSP camera framed on the strip or part |
| PLC or line controller | Optional Modbus TCP master that reads the verdict |

**Important:** internal validation only, same licence restriction as the other
preset. **In addition, nothing on this preset has been verified on hardware.**
No accuracy, throughput or latency figure exists for this board. What is known
comes from the compiler's emulator on 20 validation images: the deployed level-1
INT8 build scored mAP50 0.7266 against the CPU float reference's 0.7228, with 2
whole-frame misses against 0. That sample is 45 boxes and is not a conclusion.
The crazing weakness and the unmeasurable false-alarm rate apply here too.

## Step 1: Deploy Surface Inspection on Hailo {#deploy_hailo_inspection type=docker_deploy required=true config=devices/hailo_inspection.yaml}

Deploy the inspector and its precompiled HEF. There is no on-device compile, so
this is faster than the Jetson path — assuming the ABI gates pass.

### Prerequisites

1. **HailoRT 4.21.x, and both packages held.** The HEF was compiled with
   Dataflow Compiler 3.31.0 / HailoRT 4.21.0. Driver, user-space library and
   python bindings must all be that version:
   `hailortcli --version` should report 4.21.x, and `apt-mark showhold` must list
   both `hailort` and `hailort-pcie-driver`. Holding only the driver lets apt
   upgrade the user-space library out from under the HEF.
2. **`hailo_pci` loaded with `force_desc_page_size=4096`.** The Pi 5 kernel page
   size is 16 KB and the Hailo-8 maximum descriptor page size is 4 KB. Without
   it, `VDevice()` and `hailortcli fw-control identify` both succeed and the
   failure surfaces only at `configure(hef)`:
   `echo 'options hailo_pci force_desc_page_size=4096' | sudo tee /etc/modprobe.d/hailo.conf`
   then reboot.
3. **Host and container Python minor versions must match.** The host's
   `hailo_platform` bindings are mounted into the container, and
   `_pyhailort.cpython-3XX-*.so` only imports under the same minor. Pi OS
   bookworm is 3.11 and the default image base matches it; trixie is 3.13 and
   needs the image rebuilt on a trixie base.
4. At least 4 GB free disk. The measured footprint added is about 452 MB — the
   runtime image at about 443 MB, the 8.9 MB HEF, and the config.
5. **The container image has not been published.** The compose file names
   `sensecraft-missionpack.seeed.cn/solution/edge-inspection-rpi-hailo:0.1.0-dev`,
   but nothing has been pushed to it. Build it from the upstream repo's
   `platforms/rpi-hailo/Dockerfile` and set `INSPECTION_IMAGE`, or retag your
   local build.
6. **The HEF has not been uploaded to the CDN**, for the same licence reason. The
   deploy step will try to download it and verify sha256
   `02201b733a3009a5e72cebf49b9b314bd09d63dafa9cf4b9f359251ff49c0565` for the
   default level-1 build (level-0 is
   `9638f2b210b49b10b44658d2e970b2822e0fac7d36ec8831f08ad4d0a10dac8f`). Until
   then, place the file at
   `~/edge-inspection-surface/hailo_inspection/models/yolox_tiny_neu6_o1.hef` by
   hand; the checksum is verified either way.
7. Your camera's RTSP URL, tested in VLC first.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deploy stops at "libhailort.so.4.21.0 not found" | The device is on a different HailoRT. This deployment is ABI-locked; either install 4.21.x or recompile the HEF against the version you have. Changing the mount alone will not work |
| Deploy stops at the `force_desc_page_size` check | Add the modprobe option and reboot. It is not optional on a Pi 5 — without it the container starts and then dies inside `configure(hef)` |
| Container exits on a python import error mentioning `_pyhailort` | Host and container Python minors differ. Rebuild the image on a base matching the host (`--build-arg RUNTIME_IMAGE=...trixie-slim` for a 3.13 host) |
| `AssembleError` in the logs | The HEF's nine output tensors did not match the expected layout. Outputs are matched by feature-map size and channel count, not by name, so this means a different HEF than the one this solution expects. Check the sha256 against `assets/models/hef_o1.manifest.json` |
| `docker compose` fails reading `._docker-compose.yml` | AppleDouble sidecars from a macOS upload. The deploy step deletes `._*` and `.DS_Store` from the upload directory; if you copied by hand, run `find . -name '._*' -delete` |
| Detections look plausible but recall is worse than the solution page | Expected on this path — the level-0 build lost 0.03 mAP50 against the CPU reference on the emulator subset. Confirm you are running the level-1 HEF, which is the default |
| No video from the camera | Test the RTSP URL in VLC. A wrong path or wrong credentials is the most common failure |

### Target {#hailo_remote type=remote device=hailo device_name="Raspberry Pi 5" config=devices/hailo_inspection.yaml default=true}

Deploy to the Raspberry Pi over SSH from this computer.

### Target {#hailo_local type=local device=hailo device_name="Raspberry Pi 5" config=devices/hailo_inspection.yaml}

Run this directly on the Pi if you are working on the device itself.

---

## Step 2: Watch the Live Inspection {#preview_hailo_inspection type=web_dashboard required=false config=devices/preview_inspection.yaml}

Open the device's own page to see the boxes drawn on the live frames and the
health counters underneath.

### Deployment Complete

The device is running and publishing. Results go to
`<device-name>/inspection/<stream-id>/results` on MQTT port 1883, and the verdict
is on Modbus TCP port 502, unit 1, coils 0 and 1.

#### Quick verification

1. Open `http://<device-ip>:8080/` and confirm the MJPEG preview is moving.
2. Check `http://<device-ip>:8080/healthz` — `inference_time_ms` should be a few
   milliseconds, `frames_dropped` should be 0 at 10 FPS, and `mqtt.rejected`
   should be 0. A non-zero `rejected` means payloads are failing contract
   validation and are being dropped rather than published.
3. Put a defective sample in front of the camera and watch a box appear with its
   class name and score.
4. Subscribe to the topic from another machine:
   `mosquitto_sub -h <device-ip> -t '<device-name>/inspection/#' -v`.

#### The MQTT message

One message per frame, carrying every box in that frame:

```json
{
  "type": "surface_inspection_result",
  "version": "1.0.0",
  "device": "rpi-hailo",
  "stream_id": "line1-cam1",
  "frame_id": 10423,
  "verdict": "NG",
  "verdict_reason": "2 defect(s) >= min_defects=1",
  "defect_count": 2,
  "primary_class_id": 1,
  "coordinate_space": "normalized_center_wh",
  "inference_time_ms": 6.4,
  "pipeline_ms": 21.8,
  "detections": [
    {"slot": 0, "class_id": 1, "class_name": "inclusion", "score": 0.87,
     "bbox": [0.4125, 0.5312, 0.1094, 0.2031]}
  ]
}
```

`slot` is the within-frame index ordered by score. This pipeline does no
tracking, so `slot` means nothing across frames. `primary_class_id` is `-1` when
there is no defect — note that the Modbus register uses `0` for the same case,
because the holding registers are unsigned 16-bit and cannot carry `-1`.

#### Next steps

- Wire the Modbus coil into your reject or marking station, then run Step 3.
- Point your MES or historian at the MQTT topic. The device publishes only; it
  never writes to a time-series database itself.
- Measure this board before trusting it. No throughput, latency or on-device
  accuracy figure exists for the Hailo path; the `/healthz` counters are the
  first real data anyone will have.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The page does not load | Port 8080 is served on the host network. Confirm the container is up (`docker ps`) and that nothing else already holds 8080 |
| Preview moving but no boxes ever appear | Either nothing defective is in frame, or the threshold is too high. Check `/events` for recent verdicts before changing anything |
| `frames_dropped` climbing | The source is delivering faster than the pipeline consumes. An RTSP source drops the oldest frame by design; lower the configured FPS |
| `mqtt.rejected` non-zero | Payloads are failing contract validation on the publish path. Check the container logs — this normally means a backend change altered the payload shape |

---

## Step 3: Check the Modbus Output {#plc_check_hailo type=manual required=false verify=true config=devices/plc_check.yaml}

Confirm a Modbus master sees what the PLC will act on. Skip this on an
installation that consumes MQTT only.

### Prerequisites

1. A machine on the same network segment that can act as a Modbus TCP master.
2. The device IP, and the unit id you set during deployment (the register map
   below assumes unit 1).

### Deployment Complete

The register map, unit 1 on port 502:

| Address | Meaning |
|---|---|
| Coil 0 | NG, mutually exclusive with coil 1 |
| Coil 1 | OK, mutually exclusive with coil 0 |
| HR 0 | Primary defect class id — the highest-scoring box in the frame; 0 when OK |
| HR 1 | Defect count |
| HR 2 | Primary box cx, normalised x10000 |
| HR 3 | Primary box cy, normalised x10000 |
| HR 4 | Primary box w, normalised x10000 |
| HR 5 | Primary box h, normalised x10000 |
| HR 6 | Heartbeat Unix seconds, high word of a uint32 |
| HR 7 | Heartbeat Unix seconds, low word of a uint32 |

#### Quick verification

1. Poll unit 1 on port 502 and read coils 0-1 and HR 0-7. The upstream repo's
   helper does it directly:
   `python evaluation/read_modbus.py --host <device-ip> --port 502 --unit 1`.
2. Sample continuously while a defective sample passes the camera and watch the
   coil pair flip.
3. Confirm the coils are never both 1 in the same sample. If you ever read
   `(1,1)`, stop — a PLC latching on either coil would act on a verdict that
   does not exist.
4. On an NG frame, confirm HR 2-5 are within 0-10000 and decode to the same box
   the MQTT message carries. On an OK frame, confirm HR 0-5 are all zero.
5. Confirm HR 6-7 keep advancing on their own interval even when no new verdict
   arrives — the heartbeat is independent of the verdict path.

#### Next steps

- Latch on the coil, not on the registers: the registers are updated atomically
  first, so by the time the coil flips they already describe that frame.
- Alarm on a stale heartbeat. That is the only signal a Modbus-only integration
  gets when the inspector stops.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused on 502 | Modbus is disabled in the config, or the container is not up. Check `modbus.enabled` in `config/config.json` on the device |
| Registers all zero while MQTT shows detections | You are reading a different unit id than the one written during deployment, or reading during an OK frame |
| Values look plausible but the box is wrong | HR 2-5 are normalised x10000 centre/width/height, not pixels. Divide by 10000 and multiply by the frame size |
| Several cameras but only one set of registers | That is by design — the contract defines one register block, and with several streams the last verdict wins. Per-stream registers need a contract change |
