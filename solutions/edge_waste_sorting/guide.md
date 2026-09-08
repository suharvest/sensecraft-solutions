## Preset: Camera + reComputer J30 / J40 (Orin) {#orin}

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

Known weaknesses:

- **One item per image.** There is no detector. Two items in one frame produce
  one answer for an undefined one of them.
- **`textile` has never been trained or tested.** Neither dataset contains a
  cloth category. The model has never predicted it once.
- **`hazardous` (有害垃圾) is never emitted.** No material class maps to it.
- **Domain shift.** Both datasets are photographs of single clean items, not a
  real bin. Accuracy drops on wet, crushed, stacked or bagged waste — collect a
  field set from your own site and re-measure on it.
- **The solution page's Jetson accuracy/consistency figures (top-1 0.8755,
  agreement 0.9991 vs CPU golden, 1060-image subset) come from a separately
  built engine.** Same FP16 engine —
  same ONNX, same precision, same reComputer J40 series (Orin NX) — not the binary
  this deployment step produces. The deployed engine's own build time (68 s)
  and end-to-end pipeline (4.122 ms) / inference (3.533 ms) timings, from one
  reported MQTT event, are measured on the deployed binary.

## Step 1: Deploy Waste Sorting {#deploy_jetson_waste type=docker_deploy required=true config=devices/jetson_waste.yaml}

Uploads the compose stack, downloads the ONNX, builds the TensorRT engine on
the device, writes the source and trigger configuration, and starts the
classifier alongside a local MQTT broker. First start needs to wait for the
engine build: the baseline (EfficientNet-Lite0) engine took 68 s on a
reComputer J40 series (Orin NX).

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
  `efficientnet_lite0_waste8.onnx` onto the device at
  `~/edge-waste-sorting/jetson_waste/models/` beforehand; the sha256 check
  (`e9f9e847de6899ad4341d8f6084823e7c70307e84ac4d0da4bc4911b5b767391`) still
  applies either way. This is the current baseline (EfficientNet-Lite0, m1c) —
  MobileNetV3-Small (m1b) was superseded because it collapsed under INT8 on
  every edge chain tested; see the solution page.
- **The container image has not been pushed.** Build it from the upstream
  repository on the device and either retag it to the name in the compose file
  or set `WASTE_IMAGE` to your local tag.

Choose the classifier track here. `baseline` is the default and the right
choice unless you have read the "Classifier selection" section on the solution
page: EfficientNet-Lite0 has higher top-1 on this taxonomy than the
open-vocabulary track (0.8877 against 0.8501 on the same val split) and is
roughly 4-5x faster on CPU (no Jetson TensorRT number exists for it yet).
`open_vocab` trades top-1 for better calibration, open-set rejection,
either-language answers and adding a class without retraining.

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
| `edge-waste-mosquitto` restart-loops with `Address in use` | Another project's broker on this device already holds 1883 on `network_mode: host` (e.g. an edge_inspection_surface deployment). Change `config/mosquitto.conf` and `config/config.json`'s `mqtt.port` to a free port (e.g. 18831) and `docker compose up -d --force-recreate mosquitto`. |

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

The stack is running and one classification has been measured end to end.

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
    "name": "efficientnet_lite0_waste8",
    "backbone": "efficientnet_lite0",
    "input": "images:1x3x224x224",
    "onnx_sha256": "e9f9e847de6899ad4341d8f6084823e7c70307e84ac4d0da4bc4911b5b767391",
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
  largest risk in the whole solution.

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

- Step 1 finished with `model_track: baseline`, measured working. Do not debug
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
- Step 3 measured, so you know the main stream is healthy before adding a
  second one.
- `vlm.trigger.min_confidence` must not be below `rules.min_confidence`;
  config validation rejects a fallback gate below the reclassification gate.
- The wiring was proved against the real service with a stubbed generation
  backend (5 frames, 5 valid main events, 2 fallback events, 0 rejects).
  Measure real-model latency, and whether the VLM is more often right, on your
  own Orin before acting on its output.

### Troubleshooting

| Issue | Solution |
|---|---|
| No fallback event ever arrives | Check `/healthz` for the VLM counters. Silent degradation is by design — a slow, unreachable or breaker-open VLM produces no event and does not disturb the main stream. |
| The runtime reports HTTP 502 rather than a connection error | A transparent proxy is intercepting the address, including `127.0.0.1`. Set `no_proxy=127.0.0.1,localhost,<vlm-host>`, or give the container no proxy variables at all. httpx honours `HTTP_PROXY`, and 502-from-proxy is counted the same as a real backend error — same behaviour, misleading attribution. |
| The `ambiguous` gate never fires | Check the reachable range: under softmax with threshold `g`, the gap on the accepted side is at least `2g-1`. At `g=0.6` a margin below 0.2 can never fire. |
| Both gates trip and only `low_confidence` is reported | By design — the stronger reason is reported. |
| The VLM's category differs from the classifier's | Expected, and it does not backfill the main event. Log both and review; the fallback is not yet evidence-backed enough to act on automatically. |
| The flap reacts slowly after enabling the VLM | `vlm.apply_fallback_to_gpio` must stay false. A flap must not wait on a call whose P50 is measured in seconds. |

## Preset: Camera + reComputer R2000 (Hailo-8) {#pi_hailo}

Prepares a Pi 5 with a Hailo-8 (the reComputer R2000 series shipping form
factor), validates the three ABI gates that can only be checked on the
device, and downloads the EfficientNet-Lite0 (m1c) HEF. The shipped HEF has
run on Hailo-8 hardware over the full 7417-image val set: material top-1
0.8889, Chinese four-way 0.9507, agreement with the fp32 CPU baseline 0.9581,
p50 3.166 ms, p95 3.249 ms, inference only. A from-scratch deploy of this
same container was separately verified on the same hardware: `/healthz`,
`/trigger` and the MQTT output all returned a real classification matching
the golden label for that one image, and a direct `infer_shard.py` run
against a 1060-image subset of the same val set — same HEF, not going through
the container's HTTP or MQTT path — measured agreement 0.9425 and accuracy
vs ground truth 0.8453 at p50 3.167 ms, consistent with the full-set figures
above.

| Device | Purpose |
|---|---|
| reComputer R2000 series (Hailo-8, PCIe M.2) | Runs the classifier on the NPU |
| USB or IP camera | Looks down into the drop area — one item per shot |
| Physical button (optional) | A trigger source; wiring and the GPIO read are integration work outside this package |
| Relay, flap or indicator (optional) | Driven by the actuator callback, which carries the four-way category and binds no pin |

**Important.** This is not a compliance or regulatory classification system.
The Chinese four-way mapping is a table this project maintains, not an
authority's certified ruling, and municipal definitions differ between cities.
Nothing here should be the sole basis for a charging, penalty or compliance
decision.

Known weaknesses:

- **The bench is a Pi 5 + M.2 module, not a reComputer R2000 chassis.** Same
  accelerator and same HailoRT, different enclosure, thermals and power
  delivery — measure long-running full-load behaviour on the chassis you ship.
  The open-vocabulary tower still fails INT8 quantisation at
  `hailo optimize`. If you train and self-quantise MobileNetV3-Small
  yourself, verify INT8 for it separately rather than carrying over this
  baseline — it collapsed on this exact compile pipeline (see the solution
  page).
- **One item per image.** There is no detector.
- **`textile` has never been trained or tested**, and `hazardous` is never
  emitted.
- **Domain shift.** The 7417-image val set and the 1060-image
  deploy-verification subset are both public-dataset photographs of single
  items, not live drop-off imagery — collect a field set and re-measure on it.

## Step 1: Deploy the Classifier on reComputer RK3588 {#deploy_recomputer_rk3588_waste type=manual required=true config=devices/recomputer_rk3588_waste.yaml}

A separate box beside the camera, for when one host serves several bins or the
camera cannot be replaced. The classifier runs on the RK3588 NPU in INT8.

Before you start you need SSH access to the board, a few hundred MB free, and
either the prebuilt model or an x86_64 Linux host with `rknn-toolkit2` 2.3.2 to
convert it — the conversion does not run on the board. The four sub-steps take
you through checking the model, installing the RKNN Lite runtime, preparing one
input frame, and running it.

One thing will stop you if you skip it: the Python binding has to match the
`librknnrt` already on the board, and a mismatch surfaces as a bare
`RKNN_ERR_FAIL` at `init_runtime` with nothing else to go on.

Measured on RK3588 hardware over the full 7417-image validation set: INT8
(calib256+mmse) gives material top-1 0.8881, agreement with the fp32 CPU
baseline 0.9893, p50 2.728 ms, p95 3.417 ms, inference only. fp16 gives
material top-1 0.8882, agreement 0.9988, at p50 5.575 ms, p95 9.904 ms — so
INT8 is 51% faster with no material difference on accuracy.

These are reference figures from an RK3588 development board, not a
reComputer chassis; they will be updated once a reComputer unit has been
re-measured.

## Step 1: Deploy the Classifier on reCamera Pro {#deploy_recamera_pro_waste type=recamera_pro_app required=true config=devices/recamera_pro_waste.yaml}

The classifier runs on the camera's own NPU in INT8 — no host, no accelerator
card, no network hop in the classification path.

It ships as an App Center application, `waste-sorting`. Install it from the App
Center on the camera's web console, then this step names it, applies your
settings and makes it the active app. The App Center runs one app at a time, so
activating it stops whatever was running before. The model is not inside the
package: the App Center delivers it separately into
`/userdata/local/models/waste-sorting/`.

You need the web console's admin credentials and about 10 MB free on
`/userdata`. There is nothing to build and nothing to copy by hand.

Fill in a device name and, if you want the events elsewhere, a broker address.
Leave the broker empty and results stay readable on the camera. With a broker,
every classification arrives on `waste/<device name>/results` as one JSON
record carrying the top-3 with per-class confidence, the material class and the
Chinese four-way category, the inference time and both model hashes — the same
shape this solution publishes on every other platform.

Measured on this hardware over 1060 validation images: eight-class material
top-1 0.8764, Chinese four-way top-1 0.9566, agreement with the fp32 CPU
baseline 0.9906, p50 6.380 ms, p95 7.014 ms — inference only, excluding
capture and preprocessing, with the camera's built-in application running.

INT8 and fp16 were also measured against each other on this hardware in a
separate round, both with the built-in application stopped: p50 5.824 ms and
16.956 ms, so INT8 is 2.9x faster. Across INT8, fp16 and fp32 on a host, the
top-1 spread over these 1060 images is under 0.2 pp.

## Step 1: Deploy the Classifier on reCamera {#deploy_recamera_waste type=recamera_cpp required=true config=devices/recamera_waste.yaml}

Installs the `.deb` and places the BF16 model at `/userdata/local/models/`.
The whole classifier runs on the camera's own SG2002 TPU — no host, no
accelerator card, no network hop in the classification path.

Before you start you need the camera reachable over USB or the network, the
SSH password for the `recamera` user, and about 10 MB free on `/userdata`.

### Wiring

1. Connect the reCamera over USB-C, or make sure it is reachable on your network
2. Enter its IP address (USB gives it `192.168.42.1`) and the SSH password for
   the `recamera` user
3. Deploy

### What lands on the device

| Path | What |
|------|------|
| `/usr/local/bin/waste-sorting` | The application |
| `/etc/init.d/K92waste-sorting` | Its init script, parked |
| `/userdata/local/models/efficientnet_lite0_waste8_cv181x_bf16.cvimodel` | The model, 8.3 MB |
| `/etc/waste-sorting.conf` | Stream ID, MQTT target, confidence threshold and debounce frames, written from the fields below |

The init script is installed parked (`K92`, not `S92`) on purpose. Only one
application may hold the camera at a time, so starting it is the console's job.

There is no INT8 cvimodel for this graph — TPU-MLIR 1.7 does not finish
calibration for it — so the model shipped here is BF16, and no INT8 accuracy
or latency figure exists for this camera.

Measured on this hardware over 1060 validation images, fed through the same
preprocessing offline (center crop, no camera capture path): material top-1
0.8792, Chinese four-way top-1 0.9566, agreement with the fp32 CPU baseline
0.9915, p50 24.276 ms, p95 24.323 ms (pure inference, excluding capture and
preprocessing), peak resident memory 11.6 MB. Measure end-to-end accuracy
through the camera's own capture and crop on your own site.

### Troubleshooting

| Issue | Solution |
|------|----------|
| App exits right after starting | The model failed to load. Confirm `/userdata/local/models/efficientnet_lite0_waste8_cv181x_bf16.cvimodel` is present and matches the sha256 in the device config — a partial or missing file makes the app exit before it ever touches the camera. |
| `start` fails twice in a row right after another gallery app was stopped | The VPSS group is a driver-side resource that a process-level "is the camera free" check does not see. Reboot the camera; it recovers immediately. |

## Step 1: Deploy Waste Sorting on Hailo {#deploy_hailo_waste type=docker_deploy required=true config=devices/hailo_waste.yaml}

Uploads the compose stack, checks the three Hailo ABI gates, then downloads
and verifies the EfficientNet-Lite0 HEF.

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
- **The container image has not been pushed.** Build it from the upstream
  repository on the device and either retag it to the name in the compose file
  or set `WASTE_IMAGE` to your local tag.
- **The HEF is downloaded by the deployer.** Step 1 fetches
  `efficientnet_lite0_waste8_u8_t2.hef` from the CDN and verifies it against
  sha256 `c514a4636dea5d9b3d0fb93f2d4a3dbe15ca907228122e3ed42bc894fce391d1`
  before use. The device needs outbound HTTPS to
  `sensecraft-statics.seeed.cc`; nothing has to be copied on by hand.

### Troubleshooting

| Issue | Solution |
|---|---|
| `No /dev/hailo0` | The card is not seated, or `hailo_pci` is not loaded. `lspci \| grep -i hailo` and `dmesg \| grep -i hailo`. |
| `libhailort.so.4.21.0 not found` | This deployment is ABI-locked to HailoRT 4.21. Install that version; do not mix versions across the driver, the library and the python bindings. |
| `expected both hailort and hailort-pcie-driver on hold` | `sudo apt-mark hold hailort hailort-pcie-driver`. |
| `hailo_pci is missing force_desc_page_size=4096` | `echo 'options hailo_pci force_desc_page_size=4096' \| sudo tee /etc/modprobe.d/hailo.conf && sudo reboot`. |
| `No HEF for this solution` | Step 1's download or its sha256 check did not pass. Re-run Step 1; if the device has no outbound HTTPS to `sensecraft-statics.seeed.cc`, fetch the file elsewhere, place it at the path the step names and verify it against the sha256 above. |
| Python import error on `_pyhailort` | The host bindings are mounted into the container and only import under the same Python minor. Bookworm is 3.11, trixie is 3.13. |
| Your own trained MobileNetV3-Small INT8s badly on Hailo | Expected — do not quantise it directly. MobileNetV3-Small (m1b) collapsed to near-random accuracy on this exact compile pipeline (agreement 0.115 vs CPU/native). EfficientNet-Lite0 is the baseline for this reason. |

### Target {#hailo_remote type=remote device=hailo device_name="reComputer R2000 series" config=devices/hailo_waste.yaml default=true}

Deploy over SSH from this machine to the Pi. This is the normal path.

### Target {#hailo_local type=local device=hailo device_name="reComputer R2000 series" config=devices/hailo_waste.yaml}

Run the deployment on the Pi itself, when you are already working on the device.

## Step 2: Watch the Live Classification {#preview_hailo_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

Opens the runtime's own page: the live view, a trigger button, the health
endpoint. If Step 1 could not fetch the HEF, the live view still comes up but
classification results do not.

### Troubleshooting

| Issue | Solution |
|---|---|
| Page does not load | `docker ps` on the device — the `waste` container should be up. Check `docker logs edge-waste-app`. |
| Page loads, preview is black | The source is wrong or unreachable. For a USB camera check that `/dev/videoN` is mounted into the container; for RTSP test the URL in VLC first. |
| Preview works, `/events` stays empty | If no HEF was placed on the device, the model never loads and nothing is ever classified — see Step 1's "No HEF for this solution" troubleshooting entry. |
| Item is tiny in the frame | Re-aim. Nothing on the solution page was measured with the item small in the frame. |

## Step 3: Wire the Trigger and Confirm One Classification {#trigger_setup_hailo type=manual required=true verify=true config=devices/trigger_setup.yaml}

The end-to-end verification. If the HEF was placed on the device in Step 1,
this confirms your own deployment reaches the same result as the 7417-image
val-set measurement in Step 1. If the HEF is still missing, run the framing
and subscription substeps now so everything but the model is confirmed.

### Prerequisites

- Step 1 attempted, the three ABI gates passed, and the container running.
- `mosquitto_sub` on some machine on the same network, or use the broker
  container: `docker exec edge-waste-mosquitto mosquitto_sub …`.
- One item to classify that belongs to a class with training data — anything
  but textile.

### Deployment Complete

The board is prepared and the stack is running, and classification runs on the
Hailo-8. If Step 1 did not get the HEF onto the device, classification is
blocked on it; the trigger and MQTT path can still be exercised.

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
    "name": "efficientnet_lite0_waste8",
    "backbone": "efficientnet_lite0",
    "input": "images:1x3x224x224",
    "onnx_sha256": "e9f9e847de6899ad4341d8f6084823e7c70307e84ac4d0da4bc4911b5b767391",
    "accelerator": "hailo"
  }
}
```

The payload shape is identical across platforms; only `model.accelerator`
differs. `stream_id` is in the payload on purpose — read it there rather than
parsing the topic.

#### Next steps

- Compare the accuracy and latency you measure against the reference run for
  this HEF on the solution page: material top-1 0.8889, China-4 0.9507,
  p50 3.166 ms over the full 7417-image validation set.
- Keep the ABI state you just established: both Hailo packages held, and
  `force_desc_page_size=4096` in place. This HEF, compiled against the Hailo compiler
  3.31.0 / HailoRT 4.21.0, needs exactly this.
- Point MQTT at a broker with credentials before this leaves the bench.

### Troubleshooting

| Issue | Solution |
|---|---|
| No message at all | Check whether the HEF is present on the device (`ls` the models directory). If it is missing, Step 1 failed at the fetch step. If it is present, check the container log for a different fault. |
| Trigger counter does not move | The trigger source is not configured. Check `trigger.sources` in `config/config.json`. |
| Two messages per button press | The debounce is too short for a bouncing switch. Raise `trigger.debounce_ms`; below roughly 300 ms a bouncing button fires twice. |
| `configure(hef)` crashes | `force_desc_page_size=4096` is missing or the reboot after setting it never happened. |
| Confidence thresholds behave differently from the Orin preset | The 4.3%-below-0.5 figure on the solution page is CPU FP32. This board's INT8 confidence distribution is a different measurement — that is expected, not a bug, but if you see it collapse toward one class, compare against the 0.9581 hardware agreement figure from the full val-set measurement; a large gap from that number is worth reporting. |
| Want open-vocabulary or VLM fallback here | Not offered on this preset. The SigLIP 2 INT8 quantisation fails at `hailo optimize`, and the VLM fallback steps are Orin-only. |
