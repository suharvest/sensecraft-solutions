## Preset: Rockchip NPU — RK3588 / RK3576 {#p1_rockchip}

A reComputer RK3588 or RK3576 runs product detection and embedding on the NPU; a Linux server runs the registration service, management UI, MQTT broker and gallery.

- **Server:** a Linux server with Docker; no GPU needed.
- **Camera:** an RTSP or USB camera over the checkout or facing the shelf.
- **Model conversion:** an x86_64 machine; rknn-toolkit2 does not run on the board.
- **Model licences:** the detector and embedder are non-commercial only and not shipped with this solution; a commercial deployment must retrain them on first-party or permissively licensed data.

## Step 1: Deploy the Registration Console {#p1_console type=docker_deploy required=true config=devices/console_stack.yaml}

Starts the registration service, management UI and MQTT broker on the server, and sets the role tokens.

### Prerequisites

- A Linux server with Docker and the compose plugin, reachable from the recognition device.
- At least an admin token. The service allows no anonymous access.
- A TLS reverse proxy in front of the UI before it is reachable from outside the local network.
- The published images are used by default; to use your own build, override `RETAIL_SERVER_IMAGE` and `RETAIL_WEB_IMAGE`.

### Troubleshooting

| Symptom | Action |
|---|---|
| "MISSING: `<image>`" before compose runs | Check the server can reach the registry; for a self-built image, build it on this host first. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Anonymous `GET /v1/gallery` returns 200 | The token check is not in effect. Stop and check the configuration. |
| `GET /v1/gallery` with the admin token returns an empty gallery | Expected before the first registration. |
| Port 8089 already in use | Change the service port and use the same port in the device configuration. |

### Target {#p1_console_remote type=remote config=devices/console_stack.yaml default=true}

Deploy to a Linux server the recognition devices can reach.

### Target {#p1_console_local type=local config=devices/console_stack.yaml}

Deploy to this computer. The recognition devices must be able to reach its IP.

## Step 2: Place the Embedding Model {#p1_embed type=manual required=true config=devices/place_embedder.yaml}

Place the DINOv2-base embedding model in the console's model directory and enable it.

### Prerequisites

- The console from Step 1 deployed.
- `dinov2b_arcface_products10k_224_b1.onnx` (348 MB, sha256 `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`), obtained yourself; non-commercial use only.
- 350 MB of free space on the server.

### Troubleshooting

| Symptom | Action |
|---|---|
| Registration works but every lookup returns the wrong SKU | The embedding model is not enabled. Set `RETAIL_EMBEDDER=onnx`, restart, and register every SKU again. |
| `server` container exits immediately after setting `RETAIL_EMBEDDER=onnx` | Confirm `RETAIL_EMBEDDER_ONNX` is set, and the file is in `assets/console/models/` with a matching name. |
| Galleries registered before and after a model change disagree | Galleries from different models cannot be mixed. Register every SKU again on the new model. |
| A commercial deployment is planned | Retrain the embedder on first-party or permissively licensed data and rebuild the gallery. |

## Step 3: Register SKUs {#p1_register type=web_dashboard required=true config=devices/register_sku.yaml}

In the console's gallery, register each SKU with 3 to 8 photos. Each registration creates a new gallery version.

### Prerequisites

- The admin token from Step 1.
- 3 to 8 photos per SKU: at least front, back and side, in two lighting conditions.
- Settle the embedding model first; changing it later means rebuilding every gallery version.

### Troubleshooting

| Symptom | Action |
|---|---|
| Registration refused with "fewer than three images" | Upload at least three. |
| The same sku_id returns 409 | Pass `replace=true` to replace it. |
| A new version appears but the device still misses the SKU | Device-side fetching, verification and switching of gallery versions is not implemented yet. |
| Top-1 is clearly low | Add more registration photos per SKU first; if still low, fine-tune the model on photos from your site. |

## Step 4: Convert and Check the Detector on Rockchip {#p1_convert type=manual required=true config=devices/rk3588_convert.yaml}

Convert the detector ONNX to `.rknn` on an x86_64 host and copy it to the board.

### Prerequisites

- An x86_64 machine with rknn-toolkit2 2.3.2, onnx 1.16.1 and setuptools below 81.
- The toolkit version matches the board's `librknnrt.so`; a mismatch can load and still produce wrong results.
- The detector ONNX, obtained yourself; academic and non-commercial use only.
- The embedder ONNX from Step 2.
- In the device-side runtime, give detection and embedding separate NPU cores: `RETAIL_RKNN_DET_CORE_MASK=2`, `RETAIL_RKNN_EMBED_CORE_MASK=01`. Do not use `AUTO`.

### Troubleshooting

| Symptom | Action |
|---|---|
| `load_onnx` fails on `onnx.mapping` | Install onnx 1.16.1. |
| `pkg_resources` not found | Downgrade setuptools below 81. |
| INT8 agreement much worse than 98% | Sample calibration images evenly across the whole validation set rather than taking the first N by name. |
| The board has no cv2 or PIL | Letterbox on another machine and ship one `(N, 640, 640, 3)` uint8 BGR `.npy`; the device script needs only numpy and rknnlite. |

## Step 5: Verify Registration, Retrieval and the Device Artifact {#p1_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

Verify console registration and download, and check the converted model against the CPU results.

### Prerequisites

- Steps 1 to 4 complete.
- A clone of the upstream repository with `uv sync` done.
- Photos of your own SKUs from angles you did not register.

### Deployment Complete

#### Quick verification

- `uv run python tools/verify_software_loop.py` passes.
- With the admin token the gallery version increases by one per registration; with no token the console returns 401 or 403.
- `GET /v1/gallery/current/download` returns a tar.gz whose SHA256SUMS verify.
- Box agreement of the `.rknn` against the CPU results (IoU ≥ 0.5) is near 99.85% for fp16 and 98.35% for INT8.

#### Next steps

- Fine-tune both models on data from your own shelf or checkout.
- The device-side process `platforms/rk3588/runtime.py` (config `platforms/rk3588/runtime.yaml`) joins detection, embedding, lookup and publishing; this preset does not deploy or supervise it.
- Measure end-to-end latency with a live camera and real store traffic.

### Troubleshooting

| Symptom | Action |
|---|---|
| Box agreement far below the reference | Check the decode path and the output layout. |
| The software loop passes but nothing works on the board | The loop verifies protocol behaviour only; troubleshoot the board as in Step 4. |
| Gallery download verifies on the server but not on the device | Compare the sha256 on both sides and transfer the file again. |

## Preset: reComputer R2000 (Hailo-8) — Detector on the NPU, Embedder on the CPU {#p2_pi5_hailo}

A reComputer R2000 (Hailo-8) runs product detection on the NPU and embedding on the CPU; a Linux server runs the registration service, management UI, MQTT broker and gallery.

- **Server:** a Linux server with Docker; no GPU needed.
- **Camera:** an RTSP or USB camera over the checkout or facing the shelf.
- **Model compilation:** an x86_64 machine; the Hailo Dataflow Compiler does not run on the device.
- **Model licences:** the detector and embedder are non-commercial only and not shipped with this solution; a commercial deployment must retrain them on first-party or permissively licensed data.
- **Limitation:** this preset has no device-side program joining detection, embedding, lookup and publishing yet; you need to write it.

## Step 1: Deploy the Registration Console {#p2_console type=docker_deploy required=true config=devices/console_stack.yaml}

Starts the registration service, management UI and MQTT broker on a server the device can reach.

### Prerequisites

- A Linux server with Docker and the compose plugin.
- At least an admin token. The service allows no anonymous access.
- A TLS reverse proxy in front of the UI before it is reachable from outside the local network.
- The published images are used by default; to use your own build, override `RETAIL_SERVER_IMAGE` and `RETAIL_WEB_IMAGE`.

### Troubleshooting

| Symptom | Action |
|---|---|
| "MISSING: `<image>`" before compose runs | Check the server can reach the registry; for a self-built image, build it on this host first. |
| Anonymous `GET /v1/gallery` returns 200 | The token check is not in effect. Stop and check the configuration. |
| The device cannot reach the service port | Test the port from the device itself; the device pulls the gallery over it. |
| Port 8089 already in use | Change the service port and use the same port in the device configuration. |

### Target {#p2_console_remote type=remote config=devices/console_stack.yaml default=true}

Deploy to a Linux server the recognition devices can reach.

### Target {#p2_console_local type=local config=devices/console_stack.yaml}

Deploy to this computer. The recognition devices must be able to reach its IP.

## Step 2: Place the Embedding Model {#p2_embed type=manual required=true config=devices/place_embedder_pi.yaml}

Place the INT8-quantised DINOv2-small embedding model in the console's model directory and enable it. The gallery must be built with the same model the device runs and cannot be mixed with other presets' models.

### Prerequisites

- The console from Step 1 deployed.
- `dinov2s_arcface_products10k_224_b1_dynint8.onnx` (sha256 `50e886aeab7b61a7eebe6ea3492b2d3ba0e74a859acedcbb9e9917b2b60454f6`), obtained yourself; non-commercial use only.
- 30 MB of free space on the server.

### Troubleshooting

| Symptom | Action |
|---|---|
| Registration works but every lookup returns the wrong SKU | The embedding model is not enabled. Set `RETAIL_EMBEDDER=onnx`, restart, and register every SKU again. |
| `server` container exits immediately after setting `RETAIL_EMBEDDER=onnx` | Confirm `RETAIL_EMBEDDER_ONNX` is set, and the file is in `assets/console/models/` with a matching name. |
| Galleries registered before and after a model change disagree | Galleries from different models cannot be mixed. Register every SKU again on the new model. |
| A commercial deployment is planned | Retrain the embedder on first-party or permissively licensed data and rebuild the gallery. |

## Step 3: Register SKUs {#p2_register type=web_dashboard required=true config=devices/register_sku.yaml}

Register each SKU with 3 to 8 photos. Each registration creates a new gallery version.

### Prerequisites

- The admin token from Step 1.
- 3 to 8 photos per SKU covering front, back and side in two lighting conditions.
- The console running the DINOv2-small model from Step 2.

### Troubleshooting

| Symptom | Action |
|---|---|
| Registration refused with "fewer than three images" | Upload at least three. |
| Gallery built with base, device runs small | Rebuild the gallery with the model the device runs. |
| A new version appears but the device still misses the SKU | Device-side fetching, verification and switching of gallery versions is not implemented yet. |
| Registration is slow | Embedding runs on the server CPU, once per SKU at registration. |

## Step 4: Compile the HEF and Prepare the Pi {#p2_compile type=manual required=true config=devices/pi_hailo_compile.yaml}

Compile the detector HEF on an x86_64 host and prepare the HailoRT environment on the device.

### Prerequisites

- HailoRT and the PCIe driver on the device at the same version (4.21.0), both held, with matching firmware.
- `/etc/modprobe.d/hailo.conf` carrying `force_desc_page_size=4096`.
- `/dev/hailo0` present and not held by another process.
- An x86_64 machine with the Hailo AI SW Suite container, and a writable calibration directory.

### Troubleshooting

| Symptom | Action |
|---|---|
| Single-context compilation fails | Expected; the compiler falls back to a two-context partition. |
| The compile container cannot write its cache | Make the mounted working directory world-writable. |
| Boxes in the right count, coordinates all wrong | Get the output order with `HEF.get_output_vstream_infos()`; never sort by name. |
| Another process holds `/dev/hailo0` | Stop that process. |
| Embedding is clearly slow | Confirm four threads and that you run the INT8 model, not fp32. |

## Step 5: Verify Registration, Retrieval and the Device Artifact {#p2_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

Verify console registration and check the HEF against the CPU results.

### Prerequisites

- Steps 1 to 4 complete.
- A clone of the upstream repository with `uv sync` done.
- Photos of your own SKUs from unregistered angles.

### Deployment Complete

#### Quick verification

- `uv run python tools/verify_software_loop.py` passes.
- The console returns an increasing gallery version with the admin token, and 401 or 403 with none.
- Box agreement of the HEF against the CPU results (IoU ≥ 0.5) is near 94.8%, and `hailortcli benchmark` reports around 110 fps.
- The INT8 embedder measures near 92 ms p50 per crop on four threads.

#### Next steps

- Decide the shelf strategy before installing: embedding runs per crop on the CPU, so frames with many boxes take long. Choose frame skipping or slot-level sampling, one of the two.
- Fine-tune both models on your own data.
- Write the device-side program that joins detection, embedding, lookup and publishing.

### Troubleshooting

| Symptom | Action |
|---|---|
| Agreement is normal but detections look wrong on screen | Check the decode threshold (0.25) and the letterbox preprocessing. |
| Detection latency is high | Confirm nothing else holds the accelerator and the pipeline is activated. |
| Die temperature or power draw missing | Not readable on this platform; record as unavailable. |
| Retrieval is clearly low | Test on your own shelf and fine-tune the models from there. |

## Preset: Jetson Orin — TensorRT {#p3_jetson_orin}

A reComputer J40 (Orin NX 16GB) or J30 (Orin Nano 8GB) runs product detection and embedding on the GPU with TensorRT fp16; a Linux server runs the registration service, management UI, MQTT broker and gallery.

- **Server:** a Linux server with Docker; no GPU needed.
- **Camera:** an RTSP or USB camera over the checkout or facing the shelf.
- **Model licences:** the detector and embedder are non-commercial only and not shipped with this solution; a commercial deployment must retrain them on first-party or permissively licensed data.

## Step 1: Deploy the Registration Console {#p3_console type=docker_deploy required=true config=devices/console_stack.yaml}

Starts the registration service, management UI and MQTT broker on the server, and sets the role tokens.

### Prerequisites

- A Linux server with Docker and the compose plugin.
- At least an admin token. The service allows no anonymous access.
- A TLS reverse proxy in front of the UI before it is reachable from outside the local network.
- The published images are used by default; to use your own build, override `RETAIL_SERVER_IMAGE` and `RETAIL_WEB_IMAGE`.

### Troubleshooting

| Symptom | Action |
|---|---|
| "MISSING: `<image>`" before compose runs | Check the server can reach the registry; for a self-built image, build it on this host first. |
| Anonymous `GET /v1/gallery` returns 200 | The token check is not in effect. Stop and check the configuration. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Port 8089 already in use | Change the service port. |

### Target {#p3_console_remote type=remote config=devices/console_stack.yaml default=true}

Deploy to a Linux server the recognition devices can reach.

### Target {#p3_console_local type=local config=devices/console_stack.yaml}

Deploy to this computer. The recognition devices must be able to reach its IP.

## Step 2: Place the Embedding Model {#p3_embed type=manual required=true config=devices/place_embedder_jetson.yaml}

Place the fp32 DINOv2-small embedding model in the console's model directory and enable it. Step 4 builds the TensorRT engine from the same file; it cannot be mixed with other presets' models.

### Prerequisites

- The console from Step 1 deployed.
- `dinov2s_arcface_products10k_224_b1.onnx` (sha256 `7f0136ef6459fdd5461e39e95070c7e964fbe2df4b53309f15f452c60da615be`), obtained yourself; non-commercial use only.
- A few tens of MB of free space on the server.

### Troubleshooting

| Symptom | Action |
|---|---|
| Registration works but every lookup returns the wrong SKU | The embedding model is not enabled. Set `RETAIL_EMBEDDER=onnx`, restart, and register every SKU again. |
| `server` container exits immediately after setting `RETAIL_EMBEDDER=onnx` | Confirm `RETAIL_EMBEDDER_ONNX` is set, and the file is in `assets/console/models/` with a matching name. |
| Galleries registered before and after a model change disagree | Galleries from different models cannot be mixed. Register every SKU again on the new model. |
| A commercial deployment is planned | Retrain the embedder on first-party or permissively licensed data and rebuild the gallery. |

## Step 3: Register SKUs {#p3_register type=web_dashboard required=true config=devices/register_sku.yaml}

Register each SKU with 3 to 8 photos. Each registration creates a new gallery version.

### Prerequisites

- The admin token from Step 1.
- 3 to 8 photos per SKU: front, back and side, in two lighting conditions.
- The console running the DINOv2-small model from Step 2; otherwise retrieval on the device is invalid.

### Troubleshooting

| Symptom | Action |
|---|---|
| Registration refused with "fewer than three images" | Upload at least three. |
| The same sku_id returns 409 | Pass `replace=true` to replace it. |
| Gallery version does not increase | The registration failed the image quality check. The response names the image. |

## Step 4: Build the TensorRT Engines {#p3_build type=manual required=true config=devices/jetson_trt_build.yaml}

Build the detection and embedding fp16 engines on the board and verify their SHA.

### Prerequisites

- A reComputer J40 (Orin NX 16GB) with JetPack 6.2 and TensorRT 10.3. Build the engines on the board that runs them; they cannot be copied between boards.
- The detector ONNX, obtained yourself; academic and non-commercial use only.
- The embedder ONNX from Step 2.
- `platforms/jetson/build_engines.py` from the upstream repository at commit `16d1347` or later.

### Troubleshooting

| Symptom | Action |
|---|---|
| `trtexec` fails with "Static model does not take explicit shapes" | Do not pass `--shapes`; use `build_engines.py` at commit `16d1347` or later. |
| An engine built on one board fails on another | Build on each board. |
| `runtime.py --dry-run` exits with code 2 | Rebuild, or run `build_engines.py --update-config` to refresh the recorded hash. |
| Box agreement clearly low | Check the decode and the output layout. |
| Retrieval results differ noticeably | Check the embedder ONNX sha256 is `7f0136ef…`. |

## Step 5: Verify Registration, Retrieval and the Device Artifact {#p3_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

Verify console registration and download, the engine checks, and device-side detection and retrieval.

### Prerequisites

- Steps 1 to 4 complete.
- A clone of the upstream repository with `uv sync` done.

### Deployment Complete

#### Quick verification

- `uv run python tools/verify_software_loop.py` passes.
- The console returns an increasing gallery version with the admin token, and 401 or 403 with none.
- `GET /v1/gallery/current/download` returns a tar.gz whose SHA256SUMS verify.
- `platforms/jetson/runtime.py --config platforms/jetson/runtime.yaml --dry-run` passes.
- Box agreement is near 99.91%, and the maximum retrieval-metric difference from fp32 is near 0.24 percentage points.
- A checkout replay through `platforms/jetson/runtime.py` shows `frames_dropped`, `capture_drop` and `embed_drop` all at 0 in `/healthz`.

#### Running it end to end

To run the device-side program on your own board, set up four items in `runtime.yaml`:

1. **Frames.** For a USB camera, set `sources[0].kind` to `usb` and `uri` to the device path (e.g. `/dev/video0`); for RTSP, follow the comment in `runtime.yaml`.
2. **Gallery.** Use the gallery registered through the console in Steps 1–3, or build one under `gallery.root` with `python3 platforms/make_runtime_gallery.py --config platforms/jetson/runtime.yaml --skus-json <SKU list>`.
3. **MQTT.** Set `mqtt.host` to your own broker.
4. **Start it.** Run `python3 platforms/jetson/runtime.py --config platforms/jetson/runtime.yaml --dry-run` first, then run it without `--dry-run`. For start on boot, use `platforms/jetson/retail-runtime.service`.

#### Next steps

- Run a long soak test before a 24/7 deployment.
- For the shelf scene, re-measure latency at the shelf configuration's 1280² input.

### Troubleshooting

| Symptom | Action |
|---|---|
| `runtime.py --dry-run` exits with code 2 | Rebuild with `build_engines.py --update-config`, which writes the new hash back. |
| Latency is clearly high | Check `nvpmodel -q` is on `MAXN_SUPER` and nothing else holds the GPU. |
| The software loop passes | It verifies protocol behaviour only; device accuracy is confirmed by the agreement checks above. |
| Checking what each preset has verified | This preset and the RK3588 preset have device-side runtime measurements; the Hailo-8 and RK3576 presets stop at model conversion. |
