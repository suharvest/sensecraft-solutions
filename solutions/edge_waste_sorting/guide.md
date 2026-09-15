## Preset: Camera + reComputer J30 / J40 (Orin) {#orin}

The Jetson Orin runs the classifier on TensorRT and serves the web page, the trigger endpoint and MQTT output. The first deployment builds the TensorRT engine on the device. Open-vocabulary classification (Step 4) is optional; switch to it after the baseline works.

- **Camera:** a USB or IP camera looking down into the drop area, one item per shot.
- **Optional peripherals:** a physical button as a trigger source; a flap, relay or indicator driven by the actuator callback. Wiring and the GPIO read are your own integration work.

**Limitations:**

- The Chinese four-way mapping is maintained by this project and municipal definitions differ between cities. Do not use the output as the sole basis for a charging, penalty or compliance decision.
- One item per frame. Two items in one frame produce one result.
- `textile` has no training data and is not recognized; `hazardous` (有害垃圾) is never emitted.
- The training data is photos of single clean items. Accuracy drops on wet, crushed, stacked or bagged waste; verify with data from your own site.

## Step 1: Deploy Waste Sorting {#deploy_jetson_waste type=docker_deploy required=true config=devices/jetson_waste.yaml}

Fill in the device, camera and classifier options. The step downloads the model, builds the engine, and starts the classifier with a local MQTT broker. The first start waits for the engine build to finish.

### Prerequisites

- A Jetson Orin on JetPack 6.x with the NVIDIA container runtime configured.
- At least 10 GB of free disk.
- For a USB camera, uncomment the matching `/dev/videoN` line in `assets/jetson/docker-compose.yml`. Do not mount all of `/dev`.
- The container image is built on the device from the upstream repository; retag it to the name in the compose file or set `WASTE_IMAGE` to your local tag.
- Classifier option: `baseline` by default; for `open_vocab` see Step 4.

### Troubleshooting

| Symptom | Action |
|---|---|
| `This target is not a NVIDIA Jetson` | The target is not a Jetson. Use a Jetson Orin. |
| `trtexec not found` | Run `sudo apt install tensorrt`. |
| `WARNING: nvidia runtime missing` | Run `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`, then redeploy. |
| Engine build fails with `Static model does not take explicit shapes` | Remove the `--minShapes`/`--optShapes`/`--maxShapes` flags. |
| sha256 mismatch on the ONNX | The file is not the released one; do not proceed. Delete the ONNX on the device and redeploy to download it again. |
| `docker compose` not found | Install `docker-compose-plugin` by hand. |
| Compose fails parsing `._docker-compose.yml` | Run `find … -name '._*' -delete` on the device to remove the files copied from a Mac. |
| Container starts, no camera | Uncomment the `/dev/videoN` line in the compose file. |
| `edge-waste-mosquitto` restart-loops with `Address in use` | Another broker holds 1883. Change `config/mosquitto.conf` and `config/config.json`'s `mqtt.port` to a free port (e.g. 18831) and run `docker compose up -d --force-recreate mosquitto`. |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_waste.yaml default=true}

Deploy over SSH from this machine to the Orin. Enter the device IP, SSH credentials, camera address and classifier option.

### Target {#jetson_local type=local device=jetson device_name="Jetson Orin" config=devices/jetson_waste.yaml}

Run the deployment on the Orin itself.

## Step 2: Watch the Live Classification {#preview_orin_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

Opens the device's own page with the live view, a trigger button and recent classifications. Use it to aim the camera before verification.

### Troubleshooting

| Symptom | Action |
|---|---|
| Page does not load | Run `docker ps` on the device to confirm the `waste` container is up; check `docker logs edge-waste-app`. |
| Preview is black | For a USB camera check that `/dev/videoN` is mounted into the container; for RTSP test the URL in VLC first. |
| Preview works, `/events` stays empty | Nothing has triggered yet. By default the runtime classifies only on a trigger. |
| Item is tiny in the frame | Re-aim so the item fills most of the frame. |

## Step 3: Wire the Trigger and Confirm One Classification {#trigger_setup_orin type=manual required=true verify=true config=devices/trigger_setup.yaml}

Put an item under the camera, fire one trigger, and confirm one classification result arrives on MQTT.

### Prerequisites

- Step 1 finished and the container running.
- `mosquitto_sub` on a machine on the same network, or use the broker container: `docker exec edge-waste-mosquitto mosquitto_sub …`.
- One item to classify that is not textile.

### Deployment Complete

The classifier is running and one classification has completed end to end.

#### Quick verification

1. Open `http://<device-ip>:8080/` and confirm the view covers the drop area with the item filling most of the frame.
2. Subscribe: `mosquitto_sub -h <device-ip> -t '<device-name>/waste/+/results' -v`.
3. Fire one trigger: `curl -X POST http://<device-ip>:8080/trigger`.
4. Confirm one message arrives and `category` matches `top3[0]`.
5. Fire two triggers within 800 ms and confirm you still get one message.

#### The MQTT message

Each classification publishes one JSON record. Main fields below; read `stream_id` from the payload rather than parsing the topic:

```json
{
  "type": "waste_sorting_result",
  "stream_id": "bin1-cam1",
  "timestamp": 1757030400123,
  "trigger": "button",
  "category": {
    "class_name": "plastic",
    "china_category": "recyclable",
    "china_category_zh": "可回收物"
  },
  "confidence": 0.913,
  "top3": [
    {"rank": 0, "class_name": "plastic", "confidence": 0.913, "china_category": "recyclable"},
    {"rank": 1, "class_name": "glass", "confidence": 0.052, "china_category": "recyclable"},
    {"rank": 2, "class_name": "residual", "confidence": 0.021, "china_category": "residual"}
  ],
  "image_ref": {
    "kind": "local",
    "uri": "/var/lib/edge-waste-sorting/captures/2026-09-05/bin1-cam1-4207.jpg"
  },
  "model": {"name": "efficientnet_lite0_waste8", "accelerator": "tensorrt"}
}
```

#### Next steps

- For a flap or indicator, set `"actuator": {"enabled": true, "min_confidence": 0.5}` and write the integration code.
- Before production use, point MQTT at a broker with credentials. The bundled broker allows anonymous connections and is for commissioning only.
- To reject out-of-vocabulary items or add classes without retraining, see Step 4.
- Collect data from your site to verify accuracy.

### Troubleshooting

| Symptom | Action |
|---|---|
| No message at all | Check the trigger counter in `/healthz`; if it does not move, check `trigger.sources` in `config/config.json`. |
| Two messages per button press | Raise `trigger.debounce_ms` to at least about 300 ms. |
| Category is always `residual` | Confidence is below `rules.min_confidence`. Check the lighting, the framing, and whether the item belongs to one of the eight classes. |
| Glass and plastic confused | Both map to 可回收物, so the four-way result is unaffected. |
| Most items come back `organic` | Improve framing and lighting; a full fix needs a rebalanced retrain. |
| Textile item classified as something else | Known limitation: textile has no training data. |
| Item is not household waste | The baseline cannot reject out-of-vocabulary items; switch to Step 4 if you need that. |

## Step 4: Switch to Open-Vocabulary Classification (Optional) {#enable_open_vocab_orin type=manual required=false verify=true config=devices/enable_open_vocab.yaml}

Switches to the SigLIP 2 open-vocabulary classifier: it can reject out-of-vocabulary items, answer in Chinese or English, and add classes without retraining, at the cost of lower top-1 accuracy and higher latency.

### Prerequisites

- Step 1 working with `model_track: baseline`.
- About 372 MB extra for the vision model, plus space for its engine.
- The prototype bank and its meta file copied onto the device by hand and verified with `sha256sum -c` against `assets/models/SHA256SUMS.open_vocab`.
- Orin preset only.

### Troubleshooting

| Symptom | Action |
|---|---|
| Engine build takes far longer than the baseline's | Expected. Do not stop it early. |
| Engine build fails with `Static model does not take explicit shapes` | Remove the `--minShapes`/`--optShapes`/`--maxShapes` flags. |
| Latency is much higher | Expected. If it is not acceptable, switch back to `baseline`. |
| Confidences all look different | After changing `temperature`, retune `min_confidence`; the calibrated value is 0.0075. |
| Four-way accuracy dropped after switching to a Chinese four-way bank | Use the hierarchical path: classify eight classes, then map to four. |
| Unknown objects still get a confident material label | Rejection is weak on the `residual` class; known limitation. |

## Preset: Camera + reComputer R2000 (Hailo-8) {#recomputer_r20}

The reComputer R2000 series (Hailo-8) runs the EfficientNet-Lite0 classifier on the NPU and serves the web page, the trigger endpoint and MQTT output.

- **Camera:** a USB or IP camera looking down into the drop area, one item per shot.
- **Optional peripherals:** a physical button as a trigger source; a flap, relay or indicator driven by the actuator callback. Wiring and the GPIO read are your own integration work.

**Limitations:**

- The Chinese four-way mapping is maintained by this project and municipal definitions differ between cities. Do not use the output as the sole basis for a charging, penalty or compliance decision.
- One item per frame.
- `textile` is not recognized, and `hazardous` is never emitted.
- Verify accuracy with data from your site; verify long-running full-load thermals on the chassis you ship.
- Open-vocabulary classification is not supported.

## Step 1: Deploy Waste Sorting on Hailo {#deploy_hailo_waste type=docker_deploy required=true config=devices/hailo_waste.yaml}

Fill in the device and camera details. The step checks the Hailo environment, downloads and verifies the model, and starts the classifier.

### Prerequisites

- Raspberry Pi OS with Docker, a Hailo-8 installed, and `/dev/hailo0` present.
- HailoRT 4.21.x installed, with `sudo apt-mark hold hailort hailort-pcie-driver` applied.
- `options hailo_pci force_desc_page_size=4096` in `/etc/modprobe.d/`, followed by a reboot.
- At least 4 GB of free disk.
- Outbound HTTPS to `sensecraft-statics.seeed.cc` for the model download.
- The container image is built on the device from the upstream repository; retag it to the name in the compose file or set `WASTE_IMAGE` to your local tag.

### Troubleshooting

| Symptom | Action |
|---|---|
| `No /dev/hailo0` | Check the module is seated: `lspci \| grep -i hailo` and `dmesg \| grep -i hailo`. |
| `libhailort.so.4.21.0 not found` | Install HailoRT 4.21 and keep the driver, library and Python bindings on the same version. |
| `expected both hailort and hailort-pcie-driver on hold` | Run `sudo apt-mark hold hailort hailort-pcie-driver`. |
| `hailo_pci is missing force_desc_page_size=4096` | Run `echo 'options hailo_pci force_desc_page_size=4096' \| sudo tee /etc/modprobe.d/hailo.conf && sudo reboot`. |
| `No HEF for this solution` | The model download or check failed. Re-run Step 1; if the device cannot reach `sensecraft-statics.seeed.cc`, download the file elsewhere and place it at the path the step names. |
| Python import error on `_pyhailort` | The bindings import only under the same Python minor version (Bookworm is 3.11, trixie is 3.13). Match the OS to the bindings. |
| Your own trained MobileNetV3-Small performs badly on Hailo | Its INT8 quantisation breaks accuracy. Use the supplied EfficientNet-Lite0. |

### Target {#hailo_remote type=remote device=hailo device_name="reComputer R2000 series" config=devices/hailo_waste.yaml default=true}

Deploy over SSH from this machine to the device.

### Target {#hailo_local type=local device=hailo device_name="reComputer R2000 series" config=devices/hailo_waste.yaml}

Run the deployment on the device itself.

## Step 2: Watch the Live Classification {#preview_hailo_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

Opens the device's own page with the live view, a trigger button and classification results. Use it to aim the camera before verification.

### Troubleshooting

| Symptom | Action |
|---|---|
| Page does not load | Run `docker ps` on the device to confirm the `waste` container is up; check `docker logs edge-waste-app`. |
| Preview is black | For a USB camera check that `/dev/videoN` is mounted into the container; for RTSP test the URL in VLC first. |
| Preview works, `/events` stays empty | Fire a trigger first; if still empty, check the model downloaded — see Step 1's "No HEF for this solution". |
| Item is tiny in the frame | Re-aim so the item fills most of the frame. |

## Step 3: Wire the Trigger and Confirm One Classification {#trigger_setup_hailo type=manual required=true verify=true config=devices/trigger_setup.yaml}

Put an item under the camera, fire one trigger, and confirm one classification result arrives on MQTT.

### Prerequisites

- Step 1 finished and the container running.
- `mosquitto_sub` on a machine on the same network, or use the broker container: `docker exec edge-waste-mosquitto mosquitto_sub …`.
- One item to classify that is not textile.

### Deployment Complete

The classifier is running on the Hailo-8 and one classification has completed end to end.

#### Quick verification

1. Open `http://<device-ip>:8080/` and confirm the view covers the drop area with the item filling most of the frame.
2. Subscribe: `mosquitto_sub -h <device-ip> -t '<device-name>/waste/+/results' -v`.
3. Fire one trigger: `curl -X POST http://<device-ip>:8080/trigger`.
4. Confirm one message arrives and `category` matches `top3[0]`.
5. Fire two triggers within 800 ms and confirm you still get one message.

#### The MQTT message

Same format as the Orin preset, with `model.accelerator` set to `hailo`:

```json
{
  "type": "waste_sorting_result",
  "stream_id": "bin1-cam1",
  "category": {
    "class_name": "plastic",
    "china_category": "recyclable",
    "china_category_zh": "可回收物"
  },
  "confidence": 0.913,
  "model": {"name": "efficientnet_lite0_waste8", "accelerator": "hailo"}
}
```

#### Next steps

- Keep both Hailo packages on hold and `force_desc_page_size=4096` in place; upgrading HailoRT stops the model from loading.
- Before production use, point MQTT at a broker with credentials.

### Troubleshooting

| Symptom | Action |
|---|---|
| No message at all | Check whether the HEF is in the models directory. If missing, re-run Step 1; if present, check the container log. |
| Trigger counter does not move | Check `trigger.sources` in `config/config.json`. |
| Two messages per button press | Raise `trigger.debounce_ms` to at least about 300 ms. |
| `configure(hef)` crashes | Set `force_desc_page_size=4096` and reboot the device. |
| Predictions collapse toward one class | Report it to us. |
| Want open-vocabulary classification | Not supported on this preset; use the Orin preset. |

## Preset: reCamera (SG2002) {#recamera}

## Step 1: Deploy the Classifier on reCamera {#deploy_recamera_waste type=recamera_cpp required=true config=devices/recamera_waste.yaml}

The classifier is installed on the reCamera and runs on the camera's own TPU, with no host.

You need the camera reachable over USB or the network, the SSH password for the `recamera` user, and about 10 MB free on `/userdata`.

### Wiring

1. Connect the reCamera over USB-C, or make sure it is reachable on your network
2. Enter its IP address (`192.168.42.1` over USB) and the SSH password for the `recamera` user
3. Deploy

### What lands on the device

The deploy installs the app and the model, writes the stream ID, MQTT target, confidence threshold and other settings to `/etc/waste-sorting.conf`, and starts the app. The camera runs one app at a time; the console restores it after a reboot.

### Troubleshooting

| Symptom | Action |
|------|------|
| App exits right after starting | The model did not load. Confirm `/userdata/local/models/efficientnet_lite0_waste8_cv181x_bf16.cvimodel` is present and complete, then redeploy. |
| `start` fails twice in a row after another app was stopped | Reboot the camera. |

## Step 2: Confirm One Classification {#verify_recamera_waste type=manual required=true verify=true}

The app is running after Step 1. Put one item in the drop area and subscribe to the broker entered in Step 1 (the camera itself by default):

```bash
mosquitto_sub -h <camera-ip> -t 'waste/<stream id>/results' -v
```

One item produces one JSON record with the material class and the Chinese four-way category.

### Troubleshooting

| Symptom | Action |
|------|------|
| Nothing arrives on the topic | Check the broker address, port (1883 by default) and credentials entered in Step 1, and subscribe to that broker |
| One record for two items in one shot | Known limitation. Present items one at a time |

## Preset: reCamera Pro {#recamera_pro}

The classifier runs in INT8 on the reCamera Pro's own NPU, with no host.

## Step 1: Deploy the Classifier on reCamera Pro {#deploy_recamera_pro_waste type=recamera_pro_app required=true config=devices/recamera_pro_waste.yaml}

Install the `waste-sorting` app from the App Center on the camera's web console first; this step applies your settings and makes it the active app. Activating it stops any other app running on the camera.

You need the web console's admin credentials and about 10 MB free on `/userdata`.

### Wiring

Fill in a device name. To send results to another system, also fill in a broker address; each classification is published as one JSON record on `waste/<device name>/results`. With the broker left empty, results are shown only in the app's panel on the camera.

### Troubleshooting

| Symptom | Action |
|------|------|
| The app is not in the App Center list | Install `waste-sorting` from the App Center first; this step does not install it |
| Activation times out | Re-run the step; if it keeps failing, check the app's state in the App Center |
| The app starts but never classifies | Confirm the model is present in `/userdata/local/models/waste-sorting/` |
| Nothing arrives on the broker, but the camera's panel shows results | Check the broker address, port and credentials |

## Step 2: Confirm One Classification {#verify_recamera_pro_waste type=manual required=true verify=true}

Put one item in the drop area and confirm a new result: in the app's panel if the broker was left empty, or by subscribing to the broker:

```bash
mosquitto_sub -h <broker-ip> -t 'waste/<device name>/results' -v
```

Use the broker's port and credentials if it needs them. One item produces one JSON record.

### Troubleshooting

| Symptom | Action |
|------|------|
| Nothing arrives on the topic | Check the broker, port and device name; the device name is the topic's second segment |
| The broker rejects the connection | Use the username and password entered in Step 1 |
| No result anywhere, including the camera | Confirm in the App Center that `waste-sorting` is still the active app |

## Preset: Camera + reComputer RK3588 {#recomputer_rk3588}

The classifier runs in INT8 on the reComputer RK3588 NPU, for one host serving several bins or when the camera cannot be replaced.

## Step 1: Deploy the Classifier on reComputer RK3588 {#deploy_recomputer_rk3588_waste type=manual required=true verify=true config=devices/recomputer_rk3588_waste.yaml}

Follow the four sub-steps: check the model, install the RKNN Lite runtime, prepare one input frame, and run the classifier.

You need SSH access to the board, a few hundred MB free, and the converted model. To convert it yourself you need an x86_64 Linux host with `rknn-toolkit2` 2.3.2; conversion does not run on the board.

### Troubleshooting

| Symptom | Action |
|------|------|
| A bare `RKNN_ERR_FAIL` at `init_runtime` | Install the Python binding version that matches the board's `librknnrt` |
| No model file to check | Convert the model on an x86_64 Linux host with `rknn-toolkit2` 2.3.2 and copy it to the board |
