## Preset: Camera + reComputer J30 / J40 (Orin) {#jetson}

Detection, assembly comparison, dimension measurement, Modbus TCP and MQTT all run on one Jetson Orin. The camera can be any RTSP or ONVIF camera, a USB camera or a recorded file.

- **Model:** The shipped model is trained on DeepPCB, a bare-board copper-defect dataset, and only proves the chain end to end; a real station needs a model trained on your own images.
- **Known limits:** Expected-item ROIs are picture coordinates, so moving the camera invalidates the template; a tilted part or a calibration reference outside the measured plane biases measurements; all cameras share one Modbus register bank, so per-stream results come from MQTT only.
- **Network:** The camera is reachable from the Jetson, and the PLC can reach port 502 on the Jetson.

## Step 1: Deploy the Inspection Runtime {#deploy_jetson_assembly type=docker_deploy required=true config=devices/jetson_assembly.yaml}

Downloads the model, builds the TensorRT engine on the device (about five minutes on first deploy), then starts the runtime and its MQTT broker.

### Prerequisites

- Ports 1883, 502 and 8080 free on the device.
- The RTSP address tested in VLC.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `Image ... is not on this device` | Confirm the device can reach `sensecraft-missionpack.seeed.cn`, then deploy again |
| Engine build fails | Confirm `/usr/src/tensorrt/bin/trtexec` exists and 10 GB is free; delete a half-built `*.engine.part` before retrying |
| ONNX checksum mismatch | Delete the model file and deploy again so it is downloaded again |
| No video from the camera | Test the RTSP URL in VLC and check the path and credentials |
| Container restarts every ~30 s | A recorded file without looping exits at its end; this is expected |
| Deploy cannot connect | Confirm SSH is reachable and the username is right (usually `recomputer` or `nvidia`) |
| Modbus port 502 refused | Another Modbus server holds the port, or the container did not start; run `docker logs edge-inspection-assembly-app` |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_assembly.yaml default=true}

Deploy over SSH to a Jetson on the network. The device needs JetPack 6.x with the TensorRT dev packages, Docker with the NVIDIA runtime, and at least 10 GB free disk.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_assembly.yaml}

Deploy to this machine, which must be the Jetson. Same requirements as the remote target: JetPack 6.x with the TensorRT dev packages, Docker with the NVIDIA runtime, and at least 10 GB free disk.

## Step 2: Set Up the Dimension Calibration {#calibrate_dimension_jetson type=manual required=false config=devices/calibrate_dimension.yaml}

Optional, only needed for the dimension check. When skipped, the dimension section reports `uncalibrated` and Modbus HR 11 = 4; the assembly comparison is unaffected.

### Prerequisites

- A calibration reference in the **same plane** as the measured surface: an ArUco marker (the example uses `DICT_4X4_50`, id 7, 25 mm wide) or an object of known width. Measure a printed marker with a caliper.
- A known-good part to confirm the result against.
- Step 1 completed.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `check_aruco.py` exits non-zero | Rebuild the image with `opencv-contrib-python-headless` |
| `status: uncalibrated` | Check that `calibration.roi` bounds the reference and that `aruco_dict` and `aruco_id` match the printed marker |
| `status: not_found` | Raise the contrast, or draw the measurement ROI around the right feature |
| Measurement is consistently off by a few percent | Put the reference in the plane of the part and set `ref_object_width_mm` to the caliper width |
| Everything reads NG at nominal size | Measure several known-good parts and set `tolerance_mm` above their spread |

## Step 3: Watch the Verdicts {#preview_assembly_jetson type=web_dashboard required=false config=devices/preview_assembly.yaml}

Opens the panel on port 8080 with live counters, recent events and a preview with detection boxes and assembly ROIs.

### Deployment Complete

The station publishes one MQTT event per frame and keeps the Modbus registers and coils current.

#### Quick verification

1. Open `http://<jetson-ip>:8080/healthz`: `frames_processed` increases and `mqtt_rejected` stays at 0.
2. Run `mosquitto_sub -h <jetson-ip> -t '<station-name>/inspection/#' -C 5`: each event carries `assembly`, `dimension` and `verdict_reasons`.
3. Take one expected part off the fixture: `missing_count` rises and `verdict` becomes `NG`.
4. Connect a Modbus client to port 502, unit 1: Coil 0 (NG) and Coil 1 (OK) are mutually exclusive, and HR 8 equals the missing count.

#### Configuring the expected-item list

Configure `assembly` and `dimension` per camera under `sources[]` in `config/config.json`:

- `assembly.expected[]`: one entry per part slot with `class` (one of the model classes), `roi` (`[x1, y1, x2, y2]` normalised to this camera's picture), `min_count` and `label` (the name shown when the part is missing).
- `dimension`: on the source that sees the calibration reference; `calibration` bounds the reference, and each `measurements[]` entry has an ROI, nominal size and `tolerance_mm`.
- `rules.ng_on_defect`, `ng_on_missing`, `ng_on_extra` and `ng_on_dimension` decide which reasons fail a board.

#### Reading the outputs

Modbus TCP, unit 1, port 502:

| Register | Meaning |
|---|---|
| Coil 0 / Coil 1 | NG / OK, mutually exclusive |
| HR 0 / HR 1 | Primary defect class id / defect count |
| HR 2–5 | Primary bbox cx, cy, w, h, normalised x10000 |
| HR 6–7 | Heartbeat, Unix seconds as a uint32 high/low word |
| HR 8 / HR 9 | Missing count / extra count |
| HR 10 | Primary measurement in millimetres x100 (long edge) |
| HR 11 | Tolerance code: 0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated |

When `HR 10 = 0`, read HR 11 first. MQTT publishes on `<station-name>/inspection/<stream-id>/results`; `verdict = NG` does not imply `defect_count > 0`.

#### Next steps

- Replace the example expected list with your own slots and retrain the model on your own images.
- Point `mqtt.host` at a broker with credentials; the bundled mosquitto allows anonymous local access.
- Add cameras by appending to `sources[]`. A reComputer J30 series unit (Orin Nano 8GB) ran 8 streams at 10 fps stably with MQTT and Modbus disabled; plan for fewer with the full I/O path.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| The panel does not open | Check that the host firewall allows port 8080 |
| Panel loads but the preview is black | Check `/healthz` for a rising `frames_processed`, then the camera URI in the container logs |
| The coil and the registers disagree | Read the registers first and treat the coil as the trigger |
| Everything is NG the moment the line starts | The expected list is still the shipped example; rebuild it for your station |
| `dimension.enabled` is false in every event | That source has no `dimension` block; check the events from the calibration camera's source |

## Step 4: Generate Expected List and ROIs with SAM2 (Optional) {#annotate_sam2_jetson type=manual required=false config=devices/annotate_with_sam2.yaml}

Optional. Runs the upstream semi-automatic annotation tool (`tools/annotation/`) on a GPU workstation to generate the `assembly.expected[]` template and ROI profile from your own images instead of hand-writing ROIs. Nothing in this step runs on the inspection device.

### Prerequisites

- A GPU workstation with the upstream `edge-inspection-assembly` repository (`--backend otsu` needs no GPU but gives weaker results).
- Your own station images and a COCO-style category list.

### Troubleshooting

| Symptom | Fix |
|------|------|
| The SAM2 backend fails to start or is slow | Confirm the workstation has a GPU, or re-run with `--backend otsu` |
| The runtime on the device rejects the generated template | Copy the `assembly.expected[]` template and ROI profile from this step over together and reload |
| SAM2 proposes no useful boxes | Add your parts to the category list, label a few classes by hand, then re-run |

## Preset: Camera + reComputer R2000 (Hailo-8) {#hailo}

Detection runs on the Hailo-8 accelerator; assembly comparison, dimension measurement, Modbus TCP and MQTT run on the reComputer R2000. The camera can be any RTSP or ONVIF camera, a USB camera or a recorded file. The model is precompiled, so there is no build step on the board.

- **Model:** The shipped model is trained on the DeepPCB bare-board defect dataset; a real station needs a model trained on your own images.
- **Known limits:** Expected-item ROIs are picture coordinates, so moving the camera invalidates the template; the calibration reference must be in the measured plane; all cameras share one Modbus register bank. Measure one stream on this board before adding more.
- **Network:** The camera is reachable from the device, and the PLC can reach port 502 on the device.

## Step 1: Deploy the Inspection Runtime {#deploy_hailo_assembly type=docker_deploy required=true config=devices/hailo_assembly.yaml}

Checks the Hailo runtime, downloads the model, then starts the runtime and its MQTT broker.

### Prerequisites

- Ports 1883, 502 and 8080 free on the device.
- The RTSP address tested in VLC.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `No /dev/hailo0` | Check the accelerator is seated; look at `lspci` and `dmesg` for the PCIe link |
| `libhailort.so.4.21.0 not found` | Install HailoRT 4.21.x for the driver, library and Python bindings, and run `apt-mark hold hailort hailort-pcie-driver` |
| Import of `hailo_platform` fails in the container | The host Python version must match the image (3.11, Pi OS bookworm) |
| `configure(hef)` crashes after a clean identify | Add `force_desc_page_size=4096` for `hailo_pci` in `/etc/modprobe.d/` and reboot |
| `Image ... is not on this device` | Confirm the device can reach `sensecraft-missionpack.seeed.cn`, then deploy again |
| HEF checksum mismatch | Delete the HEF file and deploy again so it is downloaded again |
| No video from the camera | Test the RTSP URL in VLC |

### Target {#hailo_remote type=remote device=hailo device_name="reComputer R2000" config=devices/hailo_assembly.yaml default=true}

Deploy over SSH to a reComputer R2000 on the network. The device needs HailoRT 4.21.x, `/dev/hailo0` present, and at least 4 GB free disk.

### Target {#hailo_local type=local device=hailo device_name="reComputer R2000" config=devices/hailo_assembly.yaml}

Deploy to this machine, which must be the reComputer R2000. Same requirements as the remote target: HailoRT 4.21.x, `/dev/hailo0` present, and at least 4 GB free disk.

## Step 2: Set Up the Dimension Calibration {#calibrate_dimension_hailo type=manual required=false config=devices/calibrate_dimension.yaml}

Optional, only needed for the dimension check. When skipped, the dimension section reports `uncalibrated` and Modbus HR 11 = 4; the assembly comparison is unaffected.

### Prerequisites

- A calibration reference in the **same plane** as the measured surface: an ArUco marker (the example uses `DICT_4X4_50`, id 7, 25 mm wide) or an object of known width. Measure a printed marker with a caliper.
- A known-good part to confirm the result against.
- Step 1 completed.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `check_aruco.py` exits non-zero | Rebuild the image with `opencv-contrib-python-headless` |
| `status: uncalibrated` | Check `calibration.roi`, `aruco_dict` and `aruco_id` |
| `status: not_found` | Raise the contrast, or draw the measurement ROI around the right feature |
| Measurement is consistently off by a few percent | Put the reference in the plane of the part and set `ref_object_width_mm` to the caliper width |
| Everything reads NG at nominal size | Measure several known-good parts and set `tolerance_mm` above their spread |

## Step 3: Watch the Verdicts {#preview_assembly_hailo type=web_dashboard required=false config=devices/preview_assembly.yaml}

Opens the panel on port 8080 with live counters, recent events and a preview with detection boxes and assembly ROIs.

### Deployment Complete

The station publishes one MQTT event per frame and keeps the Modbus registers and coils current.

#### Quick verification

1. Open `http://<device-ip>:8080/healthz`: `frames_processed` increases and `mqtt_rejected` stays at 0.
2. Run `mosquitto_sub -h <device-ip> -t '<station-name>/inspection/#' -C 5`: each event carries `assembly`, `dimension` and `verdict_reasons`.
3. Take one expected part off the fixture: `missing_count` rises and `verdict` becomes `NG`.
4. Connect a Modbus client to port 502, unit 1: Coil 0 (NG) and Coil 1 (OK) are mutually exclusive, and HR 8 equals the missing count.
5. Record the frame rate and `inference_ms_avg` from the panel as this board's actual performance.

#### Configuring the expected-item list

Configure `assembly` and `dimension` per camera under `sources[]` in `config/config.json`:

- `assembly.expected[]`: one entry per part slot with `class` (one of the model classes), `roi` (`[x1, y1, x2, y2]` normalised to this camera's picture), `min_count` and `label` (the name shown when the part is missing).
- `dimension`: on the source that sees the calibration reference; `calibration` bounds the reference, and each `measurements[]` entry has an ROI, nominal size and `tolerance_mm`.
- `rules.ng_on_defect`, `ng_on_missing`, `ng_on_extra` and `ng_on_dimension` decide which reasons fail a board.

#### Reading the outputs

Modbus TCP, unit 1, port 502:

| Register | Meaning |
|---|---|
| Coil 0 / Coil 1 | NG / OK, mutually exclusive |
| HR 0 / HR 1 | Primary defect class id / defect count |
| HR 2–5 | Primary bbox cx, cy, w, h, normalised x10000 |
| HR 6–7 | Heartbeat, Unix seconds as a uint32 high/low word |
| HR 8 / HR 9 | Missing count / extra count |
| HR 10 | Primary measurement in millimetres x100 (long edge) |
| HR 11 | Tolerance code: 0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated |

When `HR 10 = 0`, read HR 11 first. MQTT publishes on `<station-name>/inspection/<stream-id>/results`; `verdict = NG` does not imply `defect_count > 0`.

#### Next steps

- Replace the example expected list with your own slots and retrain the model on your own images.
- Point `mqtt.host` at a broker with credentials; the bundled mosquitto allows anonymous local access.
- Measure one stream before adding more.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| The panel does not open | Check that the host firewall allows port 8080 |
| Panel loads but the preview is black | Check `/healthz` for a rising `frames_processed`, then the container logs |
| The coil and the registers disagree | Read the registers first and treat the coil as the trigger |
| Everything is NG the moment the line starts | The expected list is still the shipped example; rebuild it for your station |

## Step 4: Generate Expected List and ROIs with SAM2 (Optional) {#annotate_sam2_hailo type=manual required=false config=devices/annotate_with_sam2.yaml}

Optional. Runs the upstream semi-automatic annotation tool (`tools/annotation/`) on a GPU workstation to generate the `assembly.expected[]` template and ROI profile from your own images instead of hand-writing ROIs. Nothing in this step runs on the reComputer R2000.

### Prerequisites

- A GPU workstation with the upstream `edge-inspection-assembly` repository (`--backend otsu` needs no GPU but gives weaker results).
- Your own station images and a COCO-style category list.

### Troubleshooting

| Symptom | Fix |
|------|------|
| The SAM2 backend fails to start or is slow | Confirm the workstation has a GPU, or re-run with `--backend otsu` |
| The runtime on the device rejects the generated template | Copy the `assembly.expected[]` template and ROI profile from this step over together and reload |
| SAM2 proposes no useful boxes | Add your parts to the category list, label a few classes by hand, then re-run |

## Preset: reCamera Pro {#recamera_pro}

Detection, the OK/NG verdict, Modbus TCP and MQTT all run on the reCamera Pro; no host is needed.

- **Known limits:** This preset only detects defects; it does not compare assemblies or measure dimensions (choose the Orin or Hailo preset for those). The camera runs one App Center application at a time, so activating this one stops the running app.
- **Account:** Admin credentials for the camera's web console.
- **Network:** The PLC can reach port 502 on the camera; prepare a broker address if you want MQTT.

## Step 1: Deploy the Inspection Node on reCamera Pro {#deploy_recamera_pro_assembly type=recamera_pro_app required=true config=devices/recamera_pro_assembly.yaml}

Install `inspection-assembly` from the App Center on the camera's web console first; this step applies your settings and makes it the active app. About 20 MB free on `/userdata` is needed.

Fill in a device name, and a broker address if you want verdicts on a broker. With the broker empty, verdicts still leave the device over Modbus TCP.

### Wiring

With a broker configured, every processed frame publishes one JSON record to `inspection/<device name>/results` (QoS 0) carrying the verdict, defect count, boxes and inference time.

#### What the PLC reads

Modbus TCP on port 502, unit 1: coil 0 is NG, coil 1 is OK, and holding registers 0-11 carry the class, defect count, primary box, heartbeat and the assembly and dimension counters.

### Troubleshooting

| Symptom | Fix |
|------|------|
| The app is not in the App Center list | Install `inspection-assembly` from the App Center first |
| Activation stops another app | Expected; the App Center runs one application at a time |
| No events on the broker, but the panel shows frames processed | Check the broker address and credentials, and `mqtt.last_error` on the status panel |
| Nothing on Modbus 502 | Confirm the app is the active one and nothing else on the camera holds port 502 |

## Step 2: Confirm One Verdict Leaves the Camera {#verify_recamera_pro_assembly type=manual required=true verify=true config=devices/verify_recamera_pro_assembly.yaml}

Read Modbus TCP from the network to confirm verdicts are leaving the camera.

1. Point the camera at the station so a board is in frame
2. From any machine on the network, read coil 0/1 and holding registers 0-11 on port 502, unit 1
3. Read them again a second later

The check passes when the heartbeat in HR 6/7 has advanced between the two reads and exactly one of coil 0 and coil 1 is set. With a defective board in frame, coil 0 is set and HR 1 is the defect count; with a clean board, coil 1 is set and HR 1 is 0.

### Troubleshooting

| Symptom | Fix |
|------|------|
| Connection refused on 502 | Confirm the app is the active one and no other process holds the port |
| The heartbeat does not advance | The app reads the RTSP substream from the camera's built-in `rkipc`; confirm `rkipc` is running |
| Both coils read 0 | The first frame has not completed yet; read again |
