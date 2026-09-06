## Preset: Rockchip NPU — RK3588 / RK3576 {#p1_rockchip}

The detector runs on the Rockchip NPU as an fp16 `.rknn`; the embedder runs on
the Rockchip CPU through onnxruntime, because no RKNN conversion of the embedder
exists. The console — registration, gallery, UI, broker — runs in containers on a
separate host.

| Device | Purpose |
|---|---|
| Console / on-prem host | Registration service, management UI, MQTT broker, gallery storage |
| reComputer RK3588 or RK3576 | Detection on the NPU, embedding on the CPU |
| RTSP / USB camera | Frames over the checkout belt or facing the shelf |
| An x86_64 machine | Model conversion. rknn-toolkit2 does not run on the board |

**What has been measured on this hardware.** The detector, on a Radxa ROCK 5T:
RKNN fp16 agrees with the CPU reference on 99.85% of boxes at 56.7 ms p50, and
the INT8 variant on 98.35% at 26.0 ms p50
(`evaluation/runs/2026-09-06-det-rk3588-radxa/results.md`). Nothing was measured
on RK3576; the numbers above are RK3588 only.

**What has not.** The embedder on this board has never been timed. There is no
RKNN conversion of it and none was attempted. There is also no device-side
service that joins detection, embedding, lookup and publishing — that process
does not exist in the upstream repository for any platform. This preset converts
the model, proves the conversion on the board, and stops there.

## Step 1: Deploy the Registration Console {#p1_console type=docker_deploy required=true config=devices/console_stack.yaml}

Brings up the registration service, the management UI and the broker on the
console host, and writes the role token table.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from the
  recognition device. No GPU needed.
- **Neither container image has been pushed.** Build both on this host from the
  upstream repository, with the SPA built first
  (`npm --prefix web/ui ci && npm --prefix web/ui run build`), then
  `platforms/console/Dockerfile.server` and `platforms/console/Dockerfile.web`.
  The images do not run npm. The step checks both images are present locally
  before touching compose.
- At least an admin token decided. There is no default token and no anonymous
  read; the service refuses to start with an empty token table.
- A reverse proxy terminating TLS in front of the UI before anyone outside the
  local network reaches it.

### Troubleshooting

| Issue | Solution |
|---|---|
| "MISSING: `<image>`" before compose runs | Expected until you build them. Build on this host from the upstream repository and use the tags you built. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Anonymous `GET /v1/gallery` returns 200 | The token gate is not in front of the gallery. Stop and investigate — the step prints this check's result. |
| `GET /v1/gallery` with the admin token returns an empty gallery | Correct before the first registration. |
| Port 8089 already in use | Change the service port in the wizard. Devices must be given the same value — that is the port they pull the gallery from. |

## Step 2: Place the Embedding Model {#p1_embed type=manual required=true config=devices/place_embedder.yaml}

Puts the DINOv2 ONNX where the console mounts it and switches the server off
the placeholder embedder.

### Prerequisites

- The console stack from Step 1, stopped or running — the file is placed next
  to its compose file and picked up on the next `docker compose up -d server`.
- `dinov2b_arcface_products10k_224_b1.onnx`, 348 MB, sha256
  `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`. It is not
  shipped with this package: `use_scope: non-commercial`,
  `redistributable: false` (JD Products-10K terms, inherited by weights
  fine-tuned on it). The backbone `facebook/dinov2-base` is Apache-2.0; the
  restriction comes from the training data.
- 350 MB of free space on the console host.

### Troubleshooting

| Issue | Solution |
|---|---|
| Registration works but every lookup returns the wrong SKU | The server is on the placeholder embedder. Upstream defaults `embedder_backend` to `fake` (`server/config.py`), which hashes the image bytes into a vector. It is not reported by `GET /api/health` and not logged, so this symptom is the only signal. Set `RETAIL_EMBEDDER=onnx`, restart, and register every SKU again. |
| `server` container exits immediately after setting `RETAIL_EMBEDDER=onnx` | Either `RETAIL_EMBEDDER_ONNX` is empty — upstream refuses to start in that combination — or the path does not exist inside the container. Check that the file is in `assets/console/models/` and that the name matches the variable. |
| Galleries registered before and after the switch disagree | They cannot be mixed. Vectors from one embedder are not comparable to vectors from another. Register everything again on the new model. |
| A commercial deployment is planned | Retrain the embedder on first-party or permissively licensed capture and rebuild every gallery version. The shipped weights cannot be used for it. |

## Step 3: Register SKUs {#p1_register type=web_dashboard required=true config=devices/register_sku.yaml}

Opens the console's product gallery. Register each SKU from 3 to 8 photographs;
each registration mints a new immutable gallery version.

### Prerequisites

- The admin token from Step 1.
- 3–8 photographs per SKU: at minimum front, back and side, in two lighting
  conditions. Fewer than three is refused.
- A decision about which embedder the console runs, because it cannot be changed
  later without rebuilding every gallery version. Vectors from two different
  models are not comparable.

### Troubleshooting

| Issue | Solution |
|---|---|
| Registration refused with "fewer than three images" | By design. Supply at least three. |
| The same sku_id returns 409 | Also by design. Pass `replace=true` if you mean to replace it; that mints a new version. |
| A new version appears but the device still misses the SKU | It has not fetched and switched yet. Allow one poll period plus the download; the switch happens only after SHA verification. |
| Top-1 is much worse than the published figure | Check registration count first (one image per SKU measured 51.11%, eight measured 79.11% on the same model), then assume domain gap — the models were fine-tuned on e-commerce packshots. |

## Step 4: Convert and Check the Detector on Rockchip {#p1_convert type=manual required=true config=devices/rk3588_convert.yaml}

Converts the ONNX to `.rknn` on an x86_64 host, copies it to the board, and
settles where embedding runs.

### Prerequisites

- An x86_64 machine with rknn-toolkit2 2.3.2, onnx pinned to 1.16.1 and
  setuptools below 81. Later onnx versions dropped `onnx.mapping` and fail
  inside `load_onnx`; setuptools 81 removed `pkg_resources`.
- The toolkit version must match the board's `librknnrt.so` version. A mismatch
  does not always fail loudly — it can load and produce wrong numbers.
- The detector ONNX. It is not shipped with this package: its weights are
  trained on SKU-110K, which is academic and non-commercial with derivative
  works forbidden.

### Troubleshooting

| Issue | Solution |
|---|---|
| `load_onnx` fails on `onnx.mapping` | onnx is too new. Pin 1.16.1. |
| `pkg_resources` not found | setuptools 81 or later. Pin below 81. |
| INT8 agreement much worse than 98% | Check how the calibration set was sampled. Taking the first N files by name lands inside one capture batch, and the quantisation scales are then set by that batch alone. Sample evenly across the whole validation directory. |
| The board has no cv2 or PIL | Do not install them if other projects share that Python. Letterbox elsewhere and ship one `(N, 640, 640, 3)` uint8 BGR `.npy`; the device script needs only numpy and rknnlite. |

## Step 5: Verify Registration, Retrieval and the Device Artifact {#p1_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

Reproduces the software loop, exercises the console API, reproduces the parity
number for your own converted artifact, and records what is still unverified.

### Prerequisites

- Steps 1 to 4 complete.
- A clone of the upstream repository with `uv sync` done, for the software loop
  and the CPU golden.
- Photographs of your own SKUs from angles you did not register, for the
  retrieval check.

### Deployment Complete

#### Quick verification

- `uv run python tools/verify_software_loop.py` passes — registration, events,
  queries and rollback all assert clean against a FakeEmbedder and an in-memory
  broker.
- The console returns a gallery version that increased once per registration
  with the admin token, and 401 or 403 with no token.
- `GET /v1/gallery/current/download` returns a tar.gz whose SHA256SUMS verify.
- Your `.rknn` reproduces box agreement near the reference for your precision:
  99.85% for fp16, 98.35% for INT8, both at IoU ≥ 0.5 against the CPU golden.

#### Next steps

- Fine-tune both models on capture from your own shelf. The upstream model card
  says outright that shelf and checkout deployment needs first-party data.
- Write the device-side pipeline. Detection, embedding, gallery lookup and
  publishing exist as separate pieces; nothing joins them yet.
- Time the embedder on this board. It has never been measured on RK3588, and it
  is the stage that decides whether shelf frames are workable.

### Troubleshooting

| Issue | Solution |
|---|---|
| Box agreement far below the reference | Not a quantisation problem at that magnitude. Check the decode path and the output layout first. |
| The software loop passes but nothing works on the board | Expected — the loop runs against a FakeEmbedder and an in-memory broker on a development machine, and proves protocol behaviour only. |
| Gallery download verifies on the host but not on the device | Compare the sha256 on both sides before blaming the device; a truncated transfer looks like corruption. |

## Preset: Raspberry Pi 5 + Hailo-8 — Detector on the NPU, Embedder on the CPU {#p2_pi5_hailo}

The only preset where both stages have run on the target hardware. The detector
is an INT8 HEF on the Hailo-8; the embedder is a dynamically quantised INT8
DINOv2-small on the Pi's own four cores, because the NPU path for it does not
work.

| Device | Purpose |
|---|---|
| Console / on-prem host | Registration service, management UI, MQTT broker, gallery storage |
| Raspberry Pi 5 + Hailo-8 (M.2) | Detection on the NPU, embedding on the CPU |
| RTSP / USB camera | Frames over the checkout belt or facing the shelf |
| An x86_64 machine | HEF compilation. The Hailo Dataflow Compiler does not run on the Pi |

**What has been measured on this hardware.** Detection: 9.04 ms p50, 9.10 ms
p95, 110.4 fps single-stream, 94.77% box agreement with the CPU reference on 200
images (`evaluation/runs/2026-09-06-det-hef/`, both boundary files `status:
measured`). End to end with letterboxing, assembly, decode and NMS: 18.74 ms p50
/ 24.25 ms p95 — the NMS over ~160 boxes costs more than the inference.
Embedding: 91.95 ms p50 / 105.98 ms p95 per crop on four threads, within 0.65
percentage points of its own fp32 retrieval accuracy across seven configurations
(`evaluation/runs/2026-09-06-embed-small/` §8).

**Why the embedder is on the CPU.** Both Hailo DFC quantisation attempts failed
the ≤3 point acceptance threshold. The default profile lost 21 to 44 points of
top-1; the aggressive profile collapsed, producing an identical vector for all
8171 evaluation images with AUROC exactly 50.00
(`evaluation/runs/2026-09-06-embed-hailo/`). No embedder HEF was produced, so
there is no device latency for that path either.

**The number to plan around is 92 ms per crop.** A five-item checkout basket is
about half a second of embedding. A shelf frame at the measured density of 157.6
boxes is about 14 seconds. Shelf use needs frame skipping or slot-level
sampling, and that decision belongs before installation, not after.

## Step 1: Deploy the Registration Console {#p2_console type=docker_deploy required=true config=devices/console_stack.yaml}

Same console stack as every preset — registration service, management UI, broker
— on a host reachable from the Pi.

### Prerequisites

- A Linux host with Docker and the compose plugin. No GPU needed.
- **Neither container image has been pushed.** Build both on this host from the
  upstream repository, SPA first. The step checks both are present locally
  before touching compose.
- At least an admin token. There is no default and no anonymous read.
- A reverse proxy terminating TLS in front of the UI before it is reachable from
  outside the local network.

### Troubleshooting

| Issue | Solution |
|---|---|
| "MISSING: `<image>`" before compose runs | Expected until you build them. |
| Anonymous `GET /v1/gallery` returns 200 | The token gate is not in front of the gallery. Stop and investigate. |
| The Pi cannot reach the service port | Devices pull the gallery over that port, not through the UI. Check it from the Pi, not from a browser on another network. |
| Port 8089 already in use | Change it in the wizard and give devices the same value. |

## Step 2: Place the Embedding Model {#p2_embed type=manual required=true config=devices/place_embedder.yaml}

Puts the DINOv2 ONNX where the console mounts it and switches the server off
the placeholder embedder.

### Prerequisites

- The console stack from Step 1, stopped or running — the file is placed next
  to its compose file and picked up on the next `docker compose up -d server`.
- `dinov2b_arcface_products10k_224_b1.onnx`, 348 MB, sha256
  `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`. It is not
  shipped with this package: `use_scope: non-commercial`,
  `redistributable: false` (JD Products-10K terms, inherited by weights
  fine-tuned on it). The backbone `facebook/dinov2-base` is Apache-2.0; the
  restriction comes from the training data.
- 350 MB of free space on the console host.

### Troubleshooting

| Issue | Solution |
|---|---|
| Registration works but every lookup returns the wrong SKU | The server is on the placeholder embedder. Upstream defaults `embedder_backend` to `fake` (`server/config.py`), which hashes the image bytes into a vector. It is not reported by `GET /api/health` and not logged, so this symptom is the only signal. Set `RETAIL_EMBEDDER=onnx`, restart, and register every SKU again. |
| `server` container exits immediately after setting `RETAIL_EMBEDDER=onnx` | Either `RETAIL_EMBEDDER_ONNX` is empty — upstream refuses to start in that combination — or the path does not exist inside the container. Check that the file is in `assets/console/models/` and that the name matches the variable. |
| Galleries registered before and after the switch disagree | They cannot be mixed. Vectors from one embedder are not comparable to vectors from another. Register everything again on the new model. |
| A commercial deployment is planned | Retrain the embedder on first-party or permissively licensed capture and rebuild every gallery version. The shipped weights cannot be used for it. |

## Step 3: Register SKUs {#p2_register type=web_dashboard required=true config=devices/register_sku.yaml}

Register each SKU from 3 to 8 photographs. Each registration mints a new
immutable gallery version.

### Prerequisites

- The admin token from Step 1.
- 3–8 photographs per SKU covering front, back and side in two lighting
  conditions.
- The DINOv2-small embedder, if this Pi is the reference: the gallery must be
  built with the same model the device runs, or nothing matches.

### Troubleshooting

| Issue | Solution |
|---|---|
| Registration refused with "fewer than three images" | By design. |
| Gallery built with base, device runs small | Vectors are not comparable across models. Rebuild the gallery with the model the device actually runs. |
| A new version appears but the device still misses the SKU | Allow one poll period plus the download; the switch happens after SHA verification. |
| Registration is slow | Embedding on the console host is CPU work. It is per-image, not per-frame, so this is a one-time cost per SKU. |

## Step 4: Compile the HEF and Prepare the Pi {#p2_compile type=manual required=true config=devices/pi_hailo_compile.yaml}

Pins the HailoRT stack, compiles the detector HEF on an x86_64 host, and sets
the embedder on the CPU with the frame budget that follows from it.

### Prerequisites

- HailoRT and the PCIe driver at the same version on the Pi, both held, with the
  firmware matching. The measured run used 4.21.0 throughout, against DFC 3.31.0
  on the compile side.
- `/etc/modprobe.d/hailo.conf` carrying `force_desc_page_size=4096`. The Pi 5
  uses 16 KB pages and the Hailo-8 expects 4 KB descriptors.
- `/dev/hailo0` present and not held by another process. The measured numbers
  are for exclusive use of the accelerator.
- An x86_64 machine with the Hailo AI SW Suite container, and a calibration
  directory it can write to.

### Troubleshooting

| Issue | Solution |
|---|---|
| Single-context compilation fails | Expected on this model. The compiler falls back to a two-context partition; the runtime cost of that fallback is already inside the measured 9.04 ms. |
| The compile container cannot write its cache | Make the mounted working directory world-writable. Its `hailo` user is not your uid. |
| Boxes in the right count, coordinates all wrong | The output vstream order. Enumerate with `HEF.get_output_vstream_infos()`, never by sorting the names — on hardware they descend within each scale. |
| Another process holds `/dev/hailo0` | Stop it for the duration. Sharing the accelerator changes every number on this page. |
| Embedding is far slower than 92 ms | Check thread count (the measurement used four) and check you are running the dynamic-INT8 model, not the fp32 one — fp32 measured 180.75 ms. |

## Step 5: Verify Registration, Retrieval and the Device Artifact {#p2_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

Reproduces the software loop, exercises the console API, reproduces the parity
number for your own HEF, and records what is still unverified.

### Prerequisites

- Steps 1 to 4 complete.
- A clone of the upstream repository with `uv sync` done.
- Photographs of your own SKUs from unregistered angles.

### Deployment Complete

#### Quick verification

- `uv run python tools/verify_software_loop.py` passes.
- The console returns an increasing gallery version with the admin token, and
  401 or 403 with none.
- Your HEF reproduces roughly 94.8% box agreement against the CPU golden at IoU
  ≥ 0.5, and `hailortcli benchmark` reports around 110 fps.
- The dynamic-INT8 embedder measures near 92 ms p50 per crop on four threads.

#### Next steps

- Decide the shelf strategy before installing: at 92 ms per crop, a 157-box
  frame is 14 seconds. Frame skipping or slot-level sampling, not both by
  accident.
- Fine-tune both models on your own capture.
- Write the device-side pipeline. Nothing joins detection, embedding, lookup and
  publishing today.

### Troubleshooting

| Issue | Solution |
|---|---|
| Agreement near 94.8% but detections look wrong on screen | Check the decode threshold and the letterbox, not the HEF. The parity procedure uses 0.25 and IoU ≥ 0.5. |
| Latency higher than 9 ms | Something else is holding the accelerator, or the pipeline is not activated. The measurement excludes pre- and post-processing. |
| Die temperature or power draw missing | Not readable on this platform. HailoRT 4.21's `fw-control` has only `identify`, and the Pi's M.2 HAT is not on the current-monitoring list. Recorded as unavailable. |
| Retrieval much worse than published | Domain gap. The models were fine-tuned on e-commerce packshots; measure on your own shelf and fine-tune from there. |

## Preset: Jetson Orin — TensorRT, Not Yet Built {#p3_jetson_orin}

The TensorRT path is in the design and not in the code. Choose this preset to
build and measure it; it does not deploy a working system.

| Device | Purpose |
|---|---|
| Console / on-prem host | Registration service, management UI, MQTT broker, gallery storage |
| reComputer J40 (Orin NX 16GB) or J30 (Orin Nano 8GB) | Where the TensorRT path would run |
| RTSP / USB camera | Frames over the checkout belt or facing the shelf |

**What exists.** The static batch-1 ONNX with opset 11 and its sha256, the
pure-numpy YOLOX decode and NMS in `core_retail.postprocess` that every platform
shares, the onnxruntime CPU golden the other two backends were checked against,
and the parity procedure itself.

**What does not.** A TensorRT detector in `backends/`. An engine build for the
fixed `images:1x3x640x640` profile. A runtime container. The upstream
repository's `platforms/` directory holds console, hailo and rknn — the Jetson
entry in its README was inherited from the donor project and points at files
that were never copied across. And the device-side pipeline is missing on all
three platforms, not only this one.

**No figure anywhere in this package was taken on a Jetson.** The boards
earmarked for this work were on a soak run through 2026-09-08.

## Step 1: Deploy the Registration Console {#p3_console type=docker_deploy required=true config=devices/console_stack.yaml}

The console stack is real and deploys the same way here as in the other two
presets. It is the only part of this preset that does.

### Prerequisites

- A Linux host with Docker and the compose plugin. No GPU needed.
- **Neither container image has been pushed.** Build both on this host from the
  upstream repository, SPA first.
- At least an admin token. No default, no anonymous read.
- A reverse proxy terminating TLS in front of the UI before external access.

### Troubleshooting

| Issue | Solution |
|---|---|
| "MISSING: `<image>`" before compose runs | Expected until you build them. |
| Anonymous `GET /v1/gallery` returns 200 | The token gate is not in front of the gallery. Stop and investigate. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Port 8089 already in use | Change it in the wizard. |

## Step 2: Place the Embedding Model {#p3_embed type=manual required=true config=devices/place_embedder.yaml}

Puts the DINOv2 ONNX where the console mounts it and switches the server off
the placeholder embedder.

### Prerequisites

- The console stack from Step 1, stopped or running — the file is placed next
  to its compose file and picked up on the next `docker compose up -d server`.
- `dinov2b_arcface_products10k_224_b1.onnx`, 348 MB, sha256
  `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`. It is not
  shipped with this package: `use_scope: non-commercial`,
  `redistributable: false` (JD Products-10K terms, inherited by weights
  fine-tuned on it). The backbone `facebook/dinov2-base` is Apache-2.0; the
  restriction comes from the training data.
- 350 MB of free space on the console host.

### Troubleshooting

| Issue | Solution |
|---|---|
| Registration works but every lookup returns the wrong SKU | The server is on the placeholder embedder. Upstream defaults `embedder_backend` to `fake` (`server/config.py`), which hashes the image bytes into a vector. It is not reported by `GET /api/health` and not logged, so this symptom is the only signal. Set `RETAIL_EMBEDDER=onnx`, restart, and register every SKU again. |
| `server` container exits immediately after setting `RETAIL_EMBEDDER=onnx` | Either `RETAIL_EMBEDDER_ONNX` is empty — upstream refuses to start in that combination — or the path does not exist inside the container. Check that the file is in `assets/console/models/` and that the name matches the variable. |
| Galleries registered before and after the switch disagree | They cannot be mixed. Vectors from one embedder are not comparable to vectors from another. Register everything again on the new model. |
| A commercial deployment is planned | Retrain the embedder on first-party or permissively licensed capture and rebuild every gallery version. The shipped weights cannot be used for it. |

## Step 3: Register SKUs {#p3_register type=web_dashboard required=true config=devices/register_sku.yaml}

Registration works today and is independent of the missing device path — the
gallery can be built and versioned before anything runs on an Orin.

### Prerequisites

- The admin token from Step 1.
- 3–8 photographs per SKU, front, back and side, two lighting conditions.
- A decision about which embedder builds the gallery, recorded, because whatever
  eventually runs on the Orin has to be the same model.

### Troubleshooting

| Issue | Solution |
|---|---|
| Registration refused with "fewer than three images" | By design. |
| The same sku_id returns 409 | By design. Pass `replace=true` to replace it. |
| Unsure which embedder to standardise on | DINOv2-base measured 84.67% top-1 at eight images per SKU; DINOv2-small measured 79.11% at the same k and is a quarter of the size. Neither has run on an Orin. |
| Gallery version does not increase | The registration failed the quality gate. The response says which image. |

## Step 4: Build the TensorRT Path {#p3_build type=manual required=true config=devices/jetson_trt_build.yaml}

Describes exactly what is missing, how to build the engine, and the parity check
that has to pass before any latency number from it means anything.

### Prerequisites

- An Orin board with JetPack and TensorRT installed. The engine is built on the
  board it will run on — engines are bound to the device and the TensorRT
  version, and must not be distributed between boards.
- The detector ONNX. It is not shipped here: the weights are trained on
  SKU-110K, which is academic and non-commercial with derivative works
  forbidden.
- Willingness to write the backend. This step does not install one.

### Troubleshooting

| Issue | Solution |
|---|---|
| Looking for `platforms/jetson/tools/build_engine.sh` | It is not there. The README entry naming it was inherited from the donor project; the files were never copied across. |
| An engine built on one board fails on another | Expected. Engines bind to the device and the TensorRT version. Build per board. |
| Parity far below the RKNN fp16 reference of 99.85% | At that magnitude it is the decode or the output layout, not fp16 precision. |
| Wanting a latency figure to quote | There is none, and inventing one from another platform would be wrong — RK3588 and Hailo-8 differ from each other by 6x on the same model. |

## Step 5: Verify Registration, Retrieval and the Device Artifact {#p3_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

Reproduces the software loop and the console round trip, which do work today,
and records the device-side gap honestly rather than reporting a green tick.

### Prerequisites

- Steps 1 to 3 complete. Step 4 is a build task and may still be open.
- A clone of the upstream repository with `uv sync` done.

### Deployment Complete

#### Quick verification

- `uv run python tools/verify_software_loop.py` passes.
- The console returns an increasing gallery version with the admin token, and
  401 or 403 with none.
- `GET /v1/gallery/current/download` returns a tar.gz whose SHA256SUMS verify.
- The device-side parity check has nothing to run against yet, and that is the
  accurate result to record.

#### Next steps

- Write the TensorRT detector backend and build an engine on the board.
- Run the parity check against the CPU golden before measuring latency.
- Write the device-side pipeline, which is missing on every platform.

### Troubleshooting

| Issue | Solution |
|---|---|
| Expecting a deployable Jetson system | There is not one. The preset exists so the gap is described rather than silently absent. |
| The software loop passes and this looks finished | The loop runs on a development machine against a FakeEmbedder. It proves protocol behaviour and nothing about any board. |
| Wanting to mark this verified | No preset in this package may carry `verified: [hardware]`. Parts have run on hardware; this package has not. |
