## Preset: IP Camera + reComputer J30 / J40 (Orin) {#orin}

A Jetson Orin pulls the camera's RTSP stream, detects defects, and outputs the verdict on Modbus TCP and MQTT; a PLC is optional.

- **Camera:** Any RTSP camera framed on the strip or part. Have the RTSP URL with credentials ready and test it in VLC first.
- **Usage limits:** Internal validation only. The model is trained on a re-hosted copy of NEU-DET; clear its licence with the dataset owner, or retrain on your own images, before a public demo, a customer-site demo or commercial material. Crazing has the lowest accuracy of the six classes and changing the threshold does not improve it; frame-level false alarms have to be measured on your own line images.
- **Network:** The PLC or MES can reach ports 502 (Modbus) and 1883 (MQTT) on the device.

## Step 1: Deploy Surface Inspection {#deploy_jetson_inspection type=docker_deploy required=true config=devices/jetson_inspection.yaml}

Deploys the inspector and builds its TensorRT engine on the device. Allow about 10 minutes; the first start waits for the build to finish.

### Prerequisites

1. The model file is not on the CDN (licence not cleared): before deploying, place `yolox_tiny_neu6.onnx` at `~/edge-inspection-surface/jetson_inspection/models/yolox_tiny_neu6.onnx` on the device. The deploy verifies its sha256.
2. The verdict threshold defaults to 0.35.
3. **Detector Track**: `yolox` is the default; `dfine` and `rtdetrv2` are available, their engine build time on Orin varies, and the 0.35 threshold is calibrated for `yolox`, so tune it on your own line images after switching tracks.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `Static model does not take explicit shapes` during the engine build | When building by hand with the upstream `build_engine.sh`, set `TRT_STATIC_SHAPE=true` |
| Engine build fails or stops part way | Confirm `/usr/src/tensorrt/bin/trtexec` exists and 10 GB is free; delete any leftover `.part` file and retry |
| `numpy.core.multiarray failed to import`, or cv2 fails to import inside the container | Mount only the host's `/usr/lib/python3.10/dist-packages/tensorrt`, not the whole `dist-packages` |
| `docker compose` fails reading `._docker-compose.yml` | Run `find . -name '._*' -delete` in the compose directory |
| No video from the camera | Test the RTSP URL in VLC and check the path and credentials |
| sha256 mismatch on the ONNX | Delete the file and copy the correct model file again |
| Deploy cannot connect over SSH | Confirm SSH is reachable and the username is right (usually `recomputer`, `nvidia` or `ubuntu`) |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_inspection.yaml default=true}

Deploy to the Jetson over SSH. The device needs JetPack 6.x with the NVIDIA container runtime and at least 10 GB free disk.

### Target {#jetson_local type=local device=jetson device_name="Jetson Orin" config=devices/jetson_inspection.yaml}

Deploy to this machine, which must be a Jetson on JetPack 6.x with the NVIDIA container runtime and at least 10 GB free disk.

---

## Step 2: Watch the Live Inspection {#preview_orin_inspection type=web_dashboard required=false config=devices/preview_inspection.yaml}

Open the device's own page to see detection boxes on the live frames and the health counters.

### Deployment Complete

Results go to `<device-name>/inspection/<stream-id>/results` on MQTT port 1883, and the verdict is written to Modbus TCP port 502, unit 1, coils 0 and 1.

#### Quick verification

1. Open `http://<device-ip>:8080/`: the MJPEG preview is moving.
2. Open `http://<device-ip>:8080/healthz`: `inference_time_ms` is a few milliseconds, `frames_dropped` is 0 at 10 FPS, and `mqtt.rejected` is 0.
3. Put a defective sample in front of the camera: a box appears with its class name and score.
4. From another machine, run `mosquitto_sub -h <device-ip> -t '<device-name>/inspection/#' -v` and confirm messages arrive.

#### The MQTT message

One message per frame: `verdict` is OK / NG, `defect_count` is the number of defects, and `detections[]` lists every box in the frame (`class_name`, `score`, normalised centre/width/height `bbox`). With no defect, `primary_class_id` is `-1` while the matching Modbus register is `0`.

#### Next steps

- Wire the Modbus coil into your reject or marking station, then run Step 3.
- Point your MES or historian at the MQTT topic.
- Load-test before adding cameras: an Orin NX ran 8 streams stably with MQTT and Modbus writes turned off.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| The page does not load | Run `docker ps` to confirm the container is up, and check nothing else holds port 8080 |
| Preview moving but no boxes ever appear | Check `/events` for recent verdicts first, then confirm a defect is in frame or lower the threshold |
| `frames_dropped` climbing | Lower the configured FPS or reduce the stream count |
| `mqtt.rejected` non-zero | Check the container logs for contract validation errors |

---

## Step 3: Check the Modbus Output {#plc_check type=manual required=false verify=true config=devices/plc_check.yaml}

Confirm a Modbus master reads the correct verdict. Skip this on an installation that consumes MQTT only.

### Prerequisites

1. A machine on the same network segment that can act as a Modbus TCP master.
2. The device IP and the unit id set during deployment (the table below assumes unit 1).

### Deployment Complete

The register map, unit 1 on port 502:

| Address | Meaning |
|---|---|
| Coil 0 | NG, mutually exclusive with coil 1 |
| Coil 1 | OK, mutually exclusive with coil 0 |
| HR 0 | Primary defect class id (the highest-scoring box in the frame); 0 when OK |
| HR 1 | Defect count |
| HR 2 | Primary box cx, normalised x10000 |
| HR 3 | Primary box cy, normalised x10000 |
| HR 4 | Primary box w, normalised x10000 |
| HR 5 | Primary box h, normalised x10000 |
| HR 6 | Heartbeat Unix seconds, high word of a uint32 |
| HR 7 | Heartbeat Unix seconds, low word of a uint32 |

#### Quick verification

1. Read coils 0-1 and HR 0-7 on unit 1, port 502, for example with the upstream repo's `python evaluation/read_modbus.py --host <device-ip> --port 502 --unit 1`.
2. Sample continuously while a defective sample passes the camera: the coil pair flips.
3. The coils are never both 1 in the same sample; if you read `(1,1)`, stop and investigate.
4. On an NG frame, HR 2-5 are within 0-10000 and match the box in the MQTT message; on an OK frame, HR 0-5 are all zero.
5. HR 6-7 keep advancing even when no new verdict arrives.

#### Next steps

- Have the PLC trigger on the coil; when the coil flips, the registers already hold that frame's data.
- Alarm on a stale heartbeat to tell "no defect" apart from "the inspector stopped".

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Connection refused on 502 | Check `modbus.enabled` in `config/config.json` on the device and confirm the container is up |
| Registers all zero while MQTT shows detections | Check the unit id, or read again on an NG frame |
| The box position is wrong | HR 2-5 are normalised x10000 centre/width/height; divide by 10000 and multiply by the frame size |
| Several cameras but only one set of registers | There is one register block and the last verdict wins; take per-stream results from MQTT |

---

## Step 4: Enable Unsupervised Anomaly Detection (Optional) {#enable_anomaly_jetson type=manual required=false verify=true config=devices/enable_anomaly.yaml}

Optional. Runs EfficientAD-S (trained only on defect-free images) alongside the detector to flag frames unlike the OK reference set, including defect types the detector was never trained on. It does not affect the verdict.

### Prerequisites

- Step 1 completed; a config edit and container restart are enough.
- The EfficientAD-S ONNX copied onto the device by hand (not on the CDN).
- Before relying on `anomaly_score`, calibrate `anomaly.threshold` with your own OK samples from the actual inspection camera.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `anomaly_score` never appears in the MQTT event | Confirm `anomaly.enabled: true` was saved and the container restarted; check the container logs for a model-load error at `anomaly.path` |
| `anomaly_score` stays near one value for every sample | Recalibrate `anomaly.threshold` on your own camera's OK set |
| Judging a frame abnormal from a single `anomaly_score` gives inconsistent results | The single-frame score is near random; use the pixel/region signal (`heatmap_ref` plus the score) |

## Preset: IP Camera + reComputer R2000 (Hailo-8) {#pi_hailo}

A reComputer R2000 pulls the camera's RTSP stream, detects defects on the Hailo-8, and outputs the verdict on Modbus TCP and MQTT; a PLC is optional. The model is precompiled, so nothing is built on the device.

- **Camera:** Any RTSP camera framed on the strip or part. Have the RTSP URL with credentials ready and test it in VLC first.
- **Usage limits:** Internal validation only. The model is trained on a re-hosted copy of NEU-DET; clear its licence or retrain on your own images before public or commercial use. Crazing has the lowest accuracy; frame-level false alarms have to be measured on your own line images. Only the `yolox` detector is supported.
- **Network:** The PLC or MES can reach ports 502 (Modbus) and 1883 (MQTT) on the device.

## Step 1: Deploy Surface Inspection on Hailo {#deploy_hailo_inspection type=docker_deploy required=true config=devices/hailo_inspection.yaml}

Deploys the inspector and its precompiled HEF model. The deploy first checks the HailoRT version, the driver option and the Python version.

### Prerequisites

1. The model file is not on the CDN (licence not cleared): before deploying, place the HEF at `~/edge-inspection-surface/hailo_inspection/models/yolox_tiny_neu6_o1.hef` on the device. The deploy verifies its sha256.
2. Driver load option: `echo 'options hailo_pci force_desc_page_size=4096' | sudo tee /etc/modprobe.d/hailo.conf`, then reboot.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Deploy stops at "libhailort.so.4.21.0 not found" | Install HailoRT 4.21.x for the driver, library and Python bindings |
| Deploy stops at the `force_desc_page_size` check | Add the modprobe option from prerequisite 2 and reboot |
| Container exits on a python import error mentioning `_pyhailort` | The host must run Pi OS bookworm (Python 3.11); on a 3.13 host, rebuild the image with `--build-arg RUNTIME_IMAGE=...trixie-slim` |
| `AssembleError` in the logs | The HEF is not the one this solution expects; check its sha256 against `assets/models/hef_o1.manifest.json` |
| `docker compose` fails reading `._docker-compose.yml` | Run `find . -name '._*' -delete` in the compose directory |
| Recall is noticeably low | Confirm you are running the default level-1 HEF (`yolox_tiny_neu6_o1.hef`) |
| No video from the camera | Test the RTSP URL in VLC and check the path and credentials |

### Target {#hailo_remote type=remote device=hailo device_name="reComputer R2000" config=devices/hailo_inspection.yaml default=true}

Deploy to the reComputer R2000 over SSH. The device needs HailoRT 4.21.x (run `apt-mark hold hailort hailort-pcie-driver` to lock the version) and at least 4 GB free disk.

### Target {#hailo_local type=local device=hailo device_name="reComputer R2000" config=devices/hailo_inspection.yaml}

Deploy to this machine, which must be the reComputer R2000 with HailoRT 4.21.x (both packages held) and at least 4 GB free disk.

---

## Step 2: Watch the Live Inspection {#preview_hailo_inspection type=web_dashboard required=false config=devices/preview_inspection.yaml}

Open the device's own page to see detection boxes on the live frames and the health counters.

### Deployment Complete

Results go to `<device-name>/inspection/<stream-id>/results` on MQTT port 1883, and the verdict is written to Modbus TCP port 502, unit 1, coils 0 and 1.

#### Quick verification

1. Open `http://<device-ip>:8080/`: the MJPEG preview is moving.
2. Open `http://<device-ip>:8080/healthz`: `inference_time_ms` is a few milliseconds, `frames_dropped` is 0 at 10 FPS, and `mqtt.rejected` is 0.
3. Put a defective sample in front of the camera: a box appears with its class name and score.
4. From another machine, run `mosquitto_sub -h <device-ip> -t '<device-name>/inspection/#' -v` and confirm messages arrive.

#### The MQTT message

One message per frame: `verdict` is OK / NG, `defect_count` is the number of defects, and `detections[]` lists every box in the frame (`class_name`, `score`, normalised centre/width/height `bbox`). With no defect, `primary_class_id` is `-1` while the matching Modbus register is `0`.

#### Next steps

- Wire the Modbus coil into your reject or marking station, then run Step 3.
- Point your MES or historian at the MQTT topic.
- Take this board's throughput and latency from the `/healthz` counters.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| The page does not load | Run `docker ps` to confirm the container is up, and check nothing else holds port 8080 |
| Preview moving but no boxes ever appear | Check `/events` for recent verdicts first, then confirm a defect is in frame or lower the threshold |
| `frames_dropped` climbing | Lower the configured FPS |
| `mqtt.rejected` non-zero | Check the container logs for contract validation errors |

---

## Step 3: Check the Modbus Output {#plc_check_hailo type=manual required=false verify=true config=devices/plc_check.yaml}

Confirm a Modbus master reads the correct verdict. Skip this on an installation that consumes MQTT only.

### Prerequisites

1. A machine on the same network segment that can act as a Modbus TCP master.
2. The device IP and the unit id set during deployment (the table below assumes unit 1).

### Deployment Complete

The register map, unit 1 on port 502:

| Address | Meaning |
|---|---|
| Coil 0 | NG, mutually exclusive with coil 1 |
| Coil 1 | OK, mutually exclusive with coil 0 |
| HR 0 | Primary defect class id (the highest-scoring box in the frame); 0 when OK |
| HR 1 | Defect count |
| HR 2 | Primary box cx, normalised x10000 |
| HR 3 | Primary box cy, normalised x10000 |
| HR 4 | Primary box w, normalised x10000 |
| HR 5 | Primary box h, normalised x10000 |
| HR 6 | Heartbeat Unix seconds, high word of a uint32 |
| HR 7 | Heartbeat Unix seconds, low word of a uint32 |

#### Quick verification

1. Read coils 0-1 and HR 0-7 on unit 1, port 502, for example with the upstream repo's `python evaluation/read_modbus.py --host <device-ip> --port 502 --unit 1`.
2. Sample continuously while a defective sample passes the camera: the coil pair flips.
3. The coils are never both 1 in the same sample; if you read `(1,1)`, stop and investigate.
4. On an NG frame, HR 2-5 are within 0-10000 and match the box in the MQTT message; on an OK frame, HR 0-5 are all zero.
5. HR 6-7 keep advancing even when no new verdict arrives.

#### Next steps

- Have the PLC trigger on the coil; when the coil flips, the registers already hold that frame's data.
- Alarm on a stale heartbeat to tell "no defect" apart from "the inspector stopped".

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Connection refused on 502 | Check `modbus.enabled` in `config/config.json` on the device and confirm the container is up |
| Registers all zero while MQTT shows detections | Check the unit id, or read again on an NG frame |
| The box position is wrong | HR 2-5 are normalised x10000 centre/width/height; divide by 10000 and multiply by the frame size |
| Several cameras but only one set of registers | There is one register block and the last verdict wins; take per-stream results from MQTT |

---

## Step 4: Enable Unsupervised Anomaly Detection (Optional) {#enable_anomaly_hailo type=manual required=false verify=true config=devices/enable_anomaly.yaml}

Optional. Runs EfficientAD-S on the CPU (`accelerator: "cpu"`; this model has no Hailo build) to flag frames unlike the OK reference set. It does not affect the verdict.

### Prerequisites

- Step 1 completed; a config edit and container restart are enough.
- The EfficientAD-S ONNX copied onto the device by hand (not on the CDN).
- Before relying on `anomaly_score`, calibrate `anomaly.threshold` with your own OK samples from the actual inspection camera.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `anomaly_score` never appears in the MQTT event | Confirm `anomaly.enabled: true` was saved and the container restarted; check the container logs for a model-load error at `anomaly.path` |
| `anomaly_score` stays near one value for every sample | Recalibrate `anomaly.threshold` on your own camera's OK set |
| Judging a frame abnormal from a single `anomaly_score` gives inconsistent results | The single-frame score is near random; use the pixel/region signal (`heatmap_ref` plus the score) |
