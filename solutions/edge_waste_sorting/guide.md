## Preset: Camera + reComputer J (Orin) {#orin}

The only preset with a model file. The TensorRT engine is built on the device
during deployment, because an engine is tied to the exact GPU architecture and
TensorRT version and cannot be shipped prebuilt. It is also the only preset
that offers the open-vocabulary track and the VLM fallback, both optional and
both added after the baseline is running.

| Device | Purpose |
|---|---|
| reComputer J40 / J30 (Jetson Orin) | Runs the classifier on TensorRT, serves the web page and the trigger endpoint, publishes MQTT |
| USB or IP camera | Looks down into the drop area — one item per shot |
| Physical button (optional) | A trigger source; wiring and the GPIO read are integration work outside this package |
| Relay, flap or indicator (optional) | Driven by the actuator callback, which carries the four-way category and binds no pin |

**Important.** This is not a compliance or regulatory classification system.
The Chinese four-way mapping is a table this project maintains, not an
authority's certified ruling, and municipal definitions differ between cities.
Nothing here should be the sole basis for a charging, penalty or compliance
decision.

Known weaknesses, all measured or explicitly unmeasured:

- **One item per image.** There is no detector. Two items in one frame produce
  one answer for an undefined one of them.
- **`textile` has never been trained or tested.** Neither dataset contains a
  cloth category. The model has never predicted it once.
- **`hazardous` (有害垃圾) is never emitted.** No material class maps to it.
- **Domain shift is unmeasured.** Both datasets are photographs of single clean
  items, not a real bin. There is no field set and therefore no number for how
  much accuracy drops on wet, crushed, stacked or bagged waste. Expect a drop.
- **Nothing on this page has run on hardware.** Every figure comes from
  onnxruntime on an Apple M4 CPU.

## Step 1: Deploy Waste Sorting {#deploy_jetson_waste type=docker_deploy required=true config=devices/jetson_waste.yaml}

Uploads the compose stack, downloads the ONNX, builds the TensorRT engine on
the device, writes the source and trigger configuration, and starts the
classifier alongside a local MQTT broker.

### Prerequisites

- A Jetson Orin running JetPack 6.x with the NVIDIA container runtime
  configured. The step checks `/etc/nv_tegra_release`, `trtexec` and the host
  `tensorrt` python package before touching anything.
- At least 10 GB free. The baseline ONNX is 6 MB; the open-vocabulary tower is
  372 MB, and its engine is larger still.
- The camera reachable from the device. For a USB camera, uncomment the
  matching `/dev/videoN` line in `assets/jetson/docker-compose.yml` — the
  container sees no video node otherwise. Never mount all of `/dev`; runc
  refuses to recreate the `/dev/pts` inodes.
- **The model file is not on any CDN.** The download URL in the step is the
  intended destination and nothing has been uploaded to it. Copy
  `mobilenetv3s_waste8.onnx` onto the device at
  `~/edge-waste-sorting/jetson_waste/models/` beforehand; the sha256 check
  (`51c7c0ed7258aec62f653c9b05bafaed85c837be56c331d7f7812c3a2043a28e`) still
  applies either way.
- **The container image has not been pushed.** Build it from the upstream
  repository on the device and either retag it to the name in the compose file
  or set `WASTE_IMAGE` to your local tag.

Choose the classifier track here. `baseline` is the default and the right
choice unless you have read the "Classifier selection" section on the solution
page: it has higher top-1 on this taxonomy (0.8792 against 0.8501 on the same
val split) and is 40× faster. `open_vocab` trades about 3 points of top-1 for
better calibration, open-set rejection, either-language answers and adding a
class without retraining.

### Troubleshooting

| Issue | Solution |
|---|---|
| `This target is not a NVIDIA Jetson` | The host has no `/etc/nv_tegra_release`. You are deploying to the wrong machine. |
| `trtexec not found` | Install the TensorRT dev packages — `sudo apt install tensorrt` on JetPack. |
| `WARNING: nvidia runtime missing` | `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`, then redeploy. |
| Engine build fails with `Static model does not take explicit shapes` | Something added `--minShapes`/`--optShapes`/`--maxShapes`. Both ONNX files are static batch-1 exports; remove those flags. |
| sha256 mismatch on the ONNX | You have a different file. Do not proceed — the engine, the event's `onnx_sha256` and every figure on the solution page all refer to the checksummed file. |
| `docker compose` not found | The step installs or links it. If it still fails, install `docker-compose-plugin` by hand. |
| Compose fails parsing `._docker-compose.yml` | AppleDouble sidecars travelled from a Mac. The step deletes them; if you uploaded by hand, run the same `find … -name '._*' -delete`. |
| Container starts, no camera | The `/dev/videoN` line in the compose file is still commented out. |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_waste.yaml default=true}

Deploy over SSH from this machine to the Orin. This is the normal path: enter
the device IP, SSH credentials, camera address and track.

### Target {#jetson_local type=local device=jetson device_name="Jetson Orin" config=devices/jetson_waste.yaml}

Run the deployment on the Orin itself, when you are already working on the
device and do not want an SSH hop.

## Step 2: Watch the Live Classification {#preview_orin_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

Opens the runtime's own page: the live view, a trigger button, the recent
classifications with their top-3 and four-way category, and the health
endpoint. Use it to aim the camera before the verification step.

### Troubleshooting

| Issue | Solution |
|---|---|
| Page does not load | `docker ps` on the device — the `waste` container should be up. Check `docker logs edge-waste-app`. |
| Page loads, preview is black | The source is wrong or unreachable. For a USB camera check that `/dev/videoN` is mounted into the container; for RTSP test the URL in VLC first. |
| Preview works, `/events` stays empty | Nothing has triggered yet. In `on_demand` mode the runtime only classifies on a trigger — that is the design, not a fault. |
| Item is tiny in the frame | Re-aim. Nothing on the solution page was measured with the item small in the frame. |

## Step 3: Wire the Trigger and Confirm One Classification {#trigger_setup_orin type=manual required=true verify=true config=devices/trigger_setup.yaml}

The end-to-end verification: put an item under the camera, fire a trigger, and
watch exactly one contract-valid event arrive on MQTT.

### Prerequisites

- Step 1 finished and the container running.
- `mosquitto_sub` on some machine on the same network, or use the broker
  container: `docker exec edge-waste-mosquitto mosquitto_sub …`.
- One item to classify that belongs to a class with training data — anything
  but textile.

### Deployment Complete

The stack is running and one classification has been verified end to end.

#### Quick verification

1. Open `http://<device-ip>:8080/` and confirm the live view shows the drop
   area with one item filling a meaningful part of the frame.
2. Subscribe: `mosquitto_sub -h <device-ip> -t '<device-name>/waste/+/results' -v`.
3. Fire one trigger: `curl -X POST http://<device-ip>:8080/trigger`.
4. Confirm exactly one message arrives, and that `category` matches `top3[0]`
   and `confidence` matches `top3[0].confidence`. The runtime rejects payloads
   where they do not, so seeing the message means both held.
5. Confirm `image_ref` carries a path or URI and no image bytes.
6. Fire two triggers within 800 ms and confirm you still get one message —
   that is the debounce merging the second into the request in flight.

#### The MQTT message

```json
{
  "type": "waste_sorting_result",
  "version": "1.0.0",
  "taxonomy_version": "material8/china4-v1",
  "device": "orin-nx",
  "stream_id": "bin1-cam1",
  "frame_id": 4207,
  "timestamp": 1757030400123,
  "trigger": "button",
  "inference_time_ms": 3.7,
  "pipeline_ms": 42.5,
  "category": {
    "class_id": 4,
    "class_name": "plastic",
    "china_category": "recyclable",
    "china_category_zh": "可回收物"
  },
  "confidence": 0.913,
  "top3": [
    {"rank": 0, "class_id": 4, "class_name": "plastic", "confidence": 0.913, "china_category": "recyclable"},
    {"rank": 1, "class_id": 2, "class_name": "glass", "confidence": 0.052, "china_category": "recyclable"},
    {"rank": 2, "class_id": 7, "class_name": "residual", "confidence": 0.021, "china_category": "residual"}
  ],
  "image_ref": {
    "kind": "local",
    "uri": "/var/lib/edge-waste-sorting/captures/2026-09-05/bin1-cam1-4207.jpg"
  },
  "model": {
    "name": "mobilenetv3s_waste8",
    "backbone": "mobilenet_v3_small",
    "input": "images:1x3x224x224",
    "onnx_sha256": "51c7c0ed7258aec62f653c9b05bafaed85c837be56c331d7f7812c3a2043a28e",
    "accelerator": "tensorrt"
  }
}
```

`stream_id` is in the payload on purpose. Read it there — the topic template is
runtime configuration and consumers must not parse the topic.

#### Next steps

- Bind the actuator callback if you have a flap or indicator: set
  `"actuator": {"enabled": true, "min_confidence": 0.5}` and supply the
  integration code. The runtime binds no pin.
- Point MQTT at a broker with credentials before this leaves the bench. The
  bundled broker allows anonymous connections and is for local commissioning.
- Consider the optional steps below: the open-vocabulary track for open-set
  rejection and adding classes, the VLM fallback for a second opinion on
  ambiguous items.
- Collect a field set. Domain shift from these datasets to a real bin is the
  largest unmeasured risk in the whole solution.

### Troubleshooting

| Issue | Solution |
|---|---|
| No message at all | Check `/healthz` — if the trigger counter is not moving, the trigger source is not configured. Check `trigger.sources` in `config/config.json`. |
| Two messages per button press | The debounce is too short for a bouncing switch. Raise `trigger.debounce_ms`; below roughly 300 ms a bouncing button fires twice. |
| Category is always `residual` | Confidence is falling below `rules.min_confidence`, so the fallback category is being published instead of the argmax. Check the lighting, the framing, and whether the item is even in one of the eight classes. |
| Confident but wrong on glass or plastic | The largest confusion in the measured matrix is glass against plastic — transparent bottles overlap in shape and highlights. The four-way category is still correct, because both map to 可回收物. |
| Everything comes back `organic` | `organic` is 48.9% of the training data and the model pushes uncertain items toward it. Better framing and lighting help; a rebalanced retrain is the real fix. |
| Textile item classified as something else | Expected. `textile` has zero training samples and the model has never predicted it. |
| Item is not household waste at all | The baseline has no way to say "not in my vocabulary". That is what the open-vocabulary step below adds. |

## Step 4: Switch to Open-Vocabulary Classification (Optional) {#enable_open_vocab_orin type=manual required=false verify=true config=devices/enable_open_vocab.yaml}

Replaces the closed-set head with a SigLIP 2 vision tower scored against text
prototypes. Read the "Classifier selection" section on the solution page first:
this is a downgrade in top-1 and an upgrade in calibration, open-set rejection,
cross-lingual answers and the ability to add a class without retraining.

### Prerequisites

- Step 1 finished with `model_track: baseline`, verified working. Do not debug
  two changes at once.
- 372 MB for the vision tower ONNX plus space for its engine, on top of what is
  already there.
- The prototype bank and its meta file — checksums in
  `assets/models/SHA256SUMS.open_vocab`. Like the ONNX, nothing has been
  uploaded to the CDN; copy them onto the device by hand and verify with
  `sha256sum -c`.
- Orin only. The Hailo preset cannot offer this: the SigLIP 2 INT8
  quantisation currently fails at `hailo optimize`, and no HEF exists.

### Troubleshooting

| Issue | Solution |
|---|---|
| Engine build takes far longer than the baseline's | Expected. This ViT-B/16 has never been engine-built on any board, so there is no reference time. Do not kill it early. |
| Engine build fails with `Static model does not take explicit shapes` | Remove `--minShapes`/`--optShapes`/`--maxShapes`; the export is static batch-1. |
| Latency is far higher than before | Expected: p50 66.93 ms against 1.57 ms on CPU. If that is not acceptable, this track is not for your form factor — the landing places are an accelerator or a distilled student. |
| Confidences all look different | Changing `temperature` changes the confidence distribution and therefore what `min_confidence` means. 0.0075 is the calibrated value; retune the threshold if you change it. |
| Four-way accuracy dropped after switching to a Chinese four-way bank | Use the hierarchical path. Direct four-way prediction scores 0.8478 against 0.9393 for eight classes mapped up. |
| Unknown objects still get a confident material label | Check the leave-one-out figures: `residual` has an AUROC of 0.5795, near chance. Open-set rejection works far better for the material classes than for the catch-all. |

## Step 5: Enable VLM Fallback for Low-Confidence and Ambiguous Items (Optional) {#enable_vlm_fallback_orin type=manual required=false verify=true config=devices/enable_vlm_fallback.yaml}

Sends items the classifier is unsure about to an external VLM service and
publishes its answer as a separate `waste_fallback` event. Additive: it never
enters the classification path, never changes the main event's category, and
every figure on the solution page holds with it off.

### Prerequisites

- A reachable `edge-vision-vlm` instance. This solution does not bundle or
  start that service — typically it runs on a separate Orin box.
- Step 3 verified, so you know the main stream is healthy before adding a
  second one.
- `vlm.trigger.min_confidence` must not be below `rules.min_confidence`;
  config validation rejects a fallback gate below the reclassification gate.
- Understand what has and has not been verified: the wiring was proved against
  the real service with a stubbed generation backend (5 frames, 5 valid main
  events, 2 fallback events, 0 rejects). Real-model latency and whether the
  VLM is actually more often right are pending verification on Orin.

### Troubleshooting

| Issue | Solution |
|---|---|
| No fallback event ever arrives | Check `/healthz` for the VLM counters. Silent degradation is by design — a slow, unreachable or breaker-open VLM produces no event and does not disturb the main stream. |
| The runtime reports HTTP 502 rather than a connection error | A transparent proxy is intercepting the address, including `127.0.0.1`. Set `no_proxy=127.0.0.1,localhost,<vlm-host>`, or give the container no proxy variables at all. httpx honours `HTTP_PROXY`, and 502-from-proxy is counted the same as a real backend error — same behaviour, misleading attribution. |
| The `ambiguous` gate never fires | Check the reachable range: under softmax with threshold `g`, the gap on the accepted side is at least `2g-1`. At `g=0.6` a margin below 0.2 can never fire. |
| Both gates trip and only `low_confidence` is reported | By design — the stronger reason is reported. |
| The VLM's category differs from the classifier's | Expected, and it does not backfill the main event. Log both and review; the fallback is not yet evidence-backed enough to act on automatically. |
| The flap reacts slowly after enabling the VLM | `vlm.apply_fallback_to_gpio` must stay false. A flap must not wait on a call whose P50 is measured in seconds. |

## Preset: Camera + Raspberry Pi 5 (Hailo-8) {#pi_hailo}

Prepares a Pi 5 with a Hailo-8, validates the three ABI gates that can only be
checked on the device, and then stops at a missing model file. The baseline
MobileNetV3-Small has not been compiled to a HEF by this project. Choose this
preset to get the board ready, not to get a running classifier today.

| Device | Purpose |
|---|---|
| Raspberry Pi 5 + Hailo-8 (PCIe M.2) | Would run the classifier on the NPU — the HEF does not exist yet |
| USB or IP camera | Looks down into the drop area — one item per shot |
| Physical button (optional) | A trigger source; wiring and the GPIO read are integration work outside this package |
| Relay, flap or indicator (optional) | Driven by the actuator callback, which carries the four-way category and binds no pin |

**Important.** This is not a compliance or regulatory classification system.
The Chinese four-way mapping is a table this project maintains, not an
authority's certified ruling, and municipal definitions differ between cities.
Nothing here should be the sole basis for a charging, penalty or compliance
decision.

Known weaknesses, all measured or explicitly unmeasured:

- **No HEF exists.** The baseline has never been compiled for Hailo-8; the
  open-vocabulary tower parses cleanly but its INT8 quantisation fails at
  `hailo optimize`. The retry is in progress and distillation is the fallback.
- **One item per image.** There is no detector.
- **`textile` has never been trained or tested**, and `hazardous` is never
  emitted.
- **Domain shift is unmeasured**, and every accuracy figure on the solution
  page is CPU FP32 — an INT8 HEF would have a different confidence
  distribution, also unmeasured.
- **Nothing here has run on a Pi.**

## Step 1: Deploy Waste Sorting on Hailo {#deploy_hailo_waste type=docker_deploy required=true config=devices/hailo_waste.yaml}

Uploads the compose stack, checks the three Hailo ABI gates, then looks for a
HEF and stops because there is none.

### Prerequisites

- Raspberry Pi OS with Docker, a Hailo-8 in the PCIe M.2 slot, and
  `/dev/hailo0` present.
- HailoRT 4.21.x installed, with both `hailort` and `hailort-pcie-driver` held
  in apt. Holding only the driver lets apt upgrade the user-space library out
  from under the HEF.
- `options hailo_pci force_desc_page_size=4096` in `/etc/modprobe.d/`, then a
  reboot. The Pi 5 kernel PAGE_SIZE is 16 KB and the Hailo-8 max descriptor
  page size is 4 KB; without this, `VDevice()` and `hailortcli fw-control
  identify` both succeed and the failure only surfaces at `configure(hef)`.
- At least 4 GB free.
- **The container image has not been pushed**, and **no HEF exists**. The step
  will pass the gates and then fail at the model. That is the expected outcome
  today.

### Troubleshooting

| Issue | Solution |
|---|---|
| `No /dev/hailo0` | The card is not seated, or `hailo_pci` is not loaded. `lspci \| grep -i hailo` and `dmesg \| grep -i hailo`. |
| `libhailort.so.4.21.0 not found` | This deployment is ABI-locked to HailoRT 4.21. Install that version; do not mix versions across the driver, the library and the python bindings. |
| `expected both hailort and hailort-pcie-driver on hold` | `sudo apt-mark hold hailort hailort-pcie-driver`. |
| `hailo_pci is missing force_desc_page_size=4096` | `echo 'options hailo_pci force_desc_page_size=4096' \| sudo tee /etc/modprobe.d/hailo.conf && sudo reboot`. |
| `No HEF for this solution` | Expected. The baseline has not been compiled for Hailo-8 and nothing has been uploaded. The board is prepared; re-run this step once a HEF exists. |
| Python import error on `_pyhailort` | The host bindings are mounted into the container and only import under the same Python minor. Bookworm is 3.11, trixie is 3.13. |

### Target {#hailo_remote type=remote device=hailo device_name="Raspberry Pi 5" config=devices/hailo_waste.yaml default=true}

Deploy over SSH from this machine to the Pi. This is the normal path.

### Target {#hailo_local type=local device=hailo device_name="Raspberry Pi 5" config=devices/hailo_waste.yaml}

Run the deployment on the Pi itself, when you are already working on the device.

## Step 2: Watch the Live Classification {#preview_hailo_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

Opens the runtime's own page. With no HEF the live view and the health endpoint
still come up; the classification results do not.

### Troubleshooting

| Issue | Solution |
|---|---|
| Page does not load | `docker ps` on the device — the `waste` container should be up. Check `docker logs edge-waste-app`. |
| Page loads, preview is black | The source is wrong or unreachable. For a USB camera check that `/dev/videoN` is mounted into the container; for RTSP test the URL in VLC first. |
| Preview works, `/events` stays empty | With no HEF the model never loads, so nothing is ever classified. This is the expected state of this preset today. |
| Item is tiny in the frame | Re-aim. Nothing on the solution page was measured with the item small in the frame. |

## Step 3: Wire the Trigger and Confirm One Classification {#trigger_setup_hailo type=manual required=true verify=true config=devices/trigger_setup.yaml}

The end-to-end verification. On this preset it will not produce an event until
a HEF exists — run the framing and subscription substeps now so everything but
the model is confirmed.

### Prerequisites

- Step 1 attempted, the three ABI gates passed, and the container running.
- `mosquitto_sub` on some machine on the same network, or use the broker
  container: `docker exec edge-waste-mosquitto mosquitto_sub …`.
- One item to classify that belongs to a class with training data — anything
  but textile.

### Deployment Complete

The board is prepared and the stack is running. Classification is blocked on
the missing HEF.

#### Quick verification

1. Open `http://<device-ip>:8080/` and confirm the live view shows the drop
   area with one item filling a meaningful part of the frame.
2. Subscribe: `mosquitto_sub -h <device-ip> -t '<device-name>/waste/+/results' -v`.
3. Fire one trigger: `curl -X POST http://<device-ip>:8080/trigger`.
4. Confirm the trigger counter in `/healthz` moves — the trigger path works
   even when the model does not.
5. Confirm no result event arrives, and that the container log names the
   missing model rather than some other failure.
6. Re-run this step after a HEF is placed on the device; from that point the
   checks are the same as on the Orin preset.

#### The MQTT message

```json
{
  "type": "waste_sorting_result",
  "version": "1.0.0",
  "taxonomy_version": "material8/china4-v1",
  "device": "pi5-hailo",
  "stream_id": "bin1-cam1",
  "frame_id": 4207,
  "timestamp": 1757030400123,
  "trigger": "button",
  "inference_time_ms": 3.7,
  "pipeline_ms": 42.5,
  "category": {
    "class_id": 4,
    "class_name": "plastic",
    "china_category": "recyclable",
    "china_category_zh": "可回收物"
  },
  "confidence": 0.913,
  "top3": [
    {"rank": 0, "class_id": 4, "class_name": "plastic", "confidence": 0.913, "china_category": "recyclable"},
    {"rank": 1, "class_id": 2, "class_name": "glass", "confidence": 0.052, "china_category": "recyclable"},
    {"rank": 2, "class_id": 7, "class_name": "residual", "confidence": 0.021, "china_category": "residual"}
  ],
  "image_ref": {
    "kind": "local",
    "uri": "/var/lib/edge-waste-sorting/captures/2026-09-05/bin1-cam1-4207.jpg"
  },
  "model": {
    "name": "mobilenetv3s_waste8",
    "backbone": "mobilenet_v3_small",
    "input": "images:1x3x224x224",
    "onnx_sha256": "51c7c0ed7258aec62f653c9b05bafaed85c837be56c331d7f7812c3a2043a28e",
    "accelerator": "hailo"
  }
}
```

The payload shape is identical across platforms; only `model.accelerator`
differs. `stream_id` is in the payload on purpose — read it there rather than
parsing the topic.

#### Next steps

- Wait for the HEF. The INT8 quantisation retry is in progress; if it fails the
  fallback is distilling a small student model.
- Keep the ABI state you just established: both Hailo packages held, and
  `force_desc_page_size=4096` in place. A HEF compiled against DFC 3.31.0 /
  HailoRT 4.21.0 will need exactly this.
- Point MQTT at a broker with credentials before this leaves the bench.
- If you need a working classifier now, use the Orin preset — it is the only
  one with a model file.

### Troubleshooting

| Issue | Solution |
|---|---|
| No message at all | Expected with no HEF. Check the container log names the missing model; if it names something else, that is a separate fault. |
| Trigger counter does not move | The trigger source is not configured. Check `trigger.sources` in `config/config.json`. |
| Two messages per button press | The debounce is too short for a bouncing switch. Raise `trigger.debounce_ms`; below roughly 300 ms a bouncing button fires twice. |
| `configure(hef)` crashes once a HEF exists | `force_desc_page_size=4096` is missing or the reboot after setting it never happened. |
| Confidence thresholds behave differently from the Orin preset | The 4.5%-below-0.5 figure is CPU FP32. An INT8 HEF has a different confidence distribution, which nobody has measured. |
| Want open-vocabulary or VLM fallback here | Not offered on this preset. The SigLIP 2 INT8 quantisation fails at `hailo optimize`, and the VLM fallback steps are Orin-only. |
