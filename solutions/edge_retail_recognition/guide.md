## Preset: Rockchip NPU — RK3588 / RK3576 {#p1_rockchip}

Both models run on the Rockchip NPU as fp16 `.rknn`: the detector and the
embedder. The console — registration, gallery, UI, broker — runs in containers
on a separate host.

| Device | Purpose |
|---|---|
| Console / on-prem host | Registration service, management UI, MQTT broker, gallery storage |
| reComputer RK3588 series | Detection and embedding, both on the NPU |
| RTSP / USB camera | Frames over the checkout belt or facing the shelf |
| An x86_64 machine | Model conversion. rknn-toolkit2 does not run on the board |

**What has been measured on this hardware**, all on an RK3588 board
(librknnrt 2.3.2, driver 0.9.8):

| Segment | Number |
|---|---|
| Detector, RKNN fp16 vs CPU reference | 99.85% box agreement, 56.7 ms p50 |
| Detector, RKNN INT8 vs CPU reference | 98.35% box agreement, 26.0 ms p50 |
| Embedder (DINOv2-small + ArcFace), RKNN fp16 vs fp32 ONNX CPU | largest gap 0.85 pp across 21 retrieval metrics |
| Embedder, RKNN fp16, one crop, three NPU cores | 48.93 ms p50 / 56.47 ms p95 |
| Embedder, same model on the CPU (dynamic INT8, 4 threads) | 93.45 ms p50 / 94.86 ms p95 |
| Detector and embedder sharing all three cores | embedder 88.94 ms p50, detector 76.91 ms p50 |
| Detector on core 2, embedder on cores 0+1 | embedder 53.19 ms p50, detector 60.88 ms p50 |
| End to end (frame in, recognised item published), core 2 / core 0+1 split, embedding on the device, retrieval on `console:0.2.0` (`embedder_backend=none`, `/v1/gallery/match`) | 924 ms p50, 1153 ms p95 |

Two facts follow from the shared-core row and are worth setting before you deploy:
give each model its own cores (`RETAIL_RKNN_DET_CORE_MASK=2`,
`RETAIL_RKNN_EMBED_CORE_MASK=01`), and do not leave the core mask at `AUTO` —
`AUTO` was measured to use core 0 only, with cores 1 and 2 at 0% throughout.

Nothing was measured on RK3576; the numbers above are RK3588 only.

**What has been measured end to end, and what has not.** The device-side
process that joins detection, embedding, lookup and publishing exists upstream
(`platforms/rk3588/runtime.py` against `platforms/rk3588/runtime.yaml`); this
preset still does not deploy or supervise it — running it on your own line is
your step. What that process was measured doing, once, on a 20-SKU shelf
replay with the console's `embedder_backend=none` and `gallery.match_url`
pointed at `console_stack:0.2.0` (device computes the embedding on its own
NPU, console only does the retrieval): 924 ms p50 / 1153 ms p95 end to end,
zero publish errors, and automatic MQTT reconnect after a 38 s console outage
with no event loss on the device side (the console's own on-disk receipt was
not independently checked). A top-1 comparison against the same crops embedded on a CPU with the fp32
ONNX source model, on the same shelf replay's full 704 `ok`-state crops (40
source frames), matched: RKNN fp16 and CPU fp32 both scored 541/704
(76.85%), 98.72% prediction agreement (695/704), and the 8 disagreements
were all borderline cases with a <0.01 similarity margin; mean cosine
similarity between the two vectors was 0.99969 (the embedding-level
comparison in the table above, 0.85 pp over 21 retrieval metrics, is not
superseded by this). Full record:
edge-retail-recognition `evaluation/runs/2026-09-08-rk3588-console-acceptance-020` §9.

## Step 1: Deploy the Registration Console {#p1_console type=docker_deploy required=true config=devices/console_stack.yaml}

Brings up the registration service, the management UI and the broker on the
console host, and writes the role token table.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from the
  recognition device. No GPU needed.
- **Both container images are published** at
  `sensecraft-missionpack.seeed.cn/solution/edge-retail-console-server:0.1.1`
  and `.../edge-retail-console-web:0.1.0` (linux/amd64 + linux/arm64);
  `RETAIL_SERVER_IMAGE` and `RETAIL_WEB_IMAGE` default to those tags. To
  deploy a local build instead, build the SPA first
  (`npm --prefix web/ui ci && npm --prefix web/ui run build`), then
  `platforms/console/Dockerfile.server` and `platforms/console/Dockerfile.web`,
  and override the two variables. The step checks both images are present
  locally or pullable before touching compose.
- At least an admin token decided. There is no default token and no anonymous
  read; the service refuses to start with an empty token table.
- A reverse proxy terminating TLS in front of the UI before anyone outside the
  local network reaches it.

### Troubleshooting

| Issue | Solution |
|---|---|
| "MISSING: `<image>`" before compose runs | The published default could not be pulled — check registry reachability. Only relevant with a self-built override if the tag was never built on this host. |
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
| A new version appears but the device still misses the SKU | The console side provides a versioned, signed gallery; the device-side runtime that would fetch a version, verify its checksums and switch atomically does not exist yet (in progress — see upstream spec). |
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
- The embedder ONNX from Step 2, if you have not placed it yet. Its licence is
  separate from the detector's and no less restrictive: `use_scope:
  non-commercial`, `redistributable: false`, inherited from the JD Products-10K
  training data (the `facebook/dinov2-base` backbone itself is Apache-2.0). It
  must not be redistributed with this package or baked into an image, and a
  commercial deployment has to retrain it on first-party or permissively
  licensed capture and rebuild every gallery version, because vectors from one
  embedder are not comparable to vectors from another.

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
- Run the device-side process on your own line. `platforms/rk3588/runtime.py`
  joins detection, embedding, lookup and publishing against
  `platforms/rk3588/runtime.yaml`; this preset does not deploy or supervise it.
- Measure end-to-end latency against a live camera and real store traffic; the
  924 ms p50 figure above is a synthetic shelf replay, not a live feed.

### Troubleshooting

| Issue | Solution |
|---|---|
| Box agreement far below the reference | Not a quantisation problem at that magnitude. Check the decode path and the output layout first. |
| The software loop passes but nothing works on the board | Expected — the loop runs against a FakeEmbedder and an in-memory broker on a development machine, and proves protocol behaviour only. |
| Gallery download verifies on the host but not on the device | Compare the sha256 on both sides before blaming the device; a truncated transfer looks like corruption. |

## Preset: reComputer R2000 (Hailo-8) — Detector on the NPU, Embedder on the CPU {#p2_pi5_hailo}

The only preset where both stages have run on the target hardware. The detector
is an INT8 HEF on the Hailo-8; the embedder is a dynamically quantised INT8
DINOv2-small on the Pi's own four cores, because the NPU path for it does not
work.

| Device | Purpose |
|---|---|
| Console / on-prem host | Registration service, management UI, MQTT broker, gallery storage |
| reComputer R2000 with Hailo-8 (M.2) | Detection on the NPU, embedding on the CPU |
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

**Why the embedder is on the CPU.** Both Hailo quantisation attempts failed
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
- **Both container images are published** (`edge-retail-console-server:0.1.1`,
  `edge-retail-console-web:0.1.0`); `RETAIL_SERVER_IMAGE`/`RETAIL_WEB_IMAGE`
  default to them. To use a local build instead, build both on this host from
  the upstream repository, SPA first, and override the two variables. The
  step checks both are present locally or pullable before touching compose.
- At least an admin token. There is no default and no anonymous read.
- A reverse proxy terminating TLS in front of the UI before it is reachable from
  outside the local network.

### Troubleshooting

| Issue | Solution |
|---|---|
| "MISSING: `<image>`" before compose runs | The published default could not be pulled — check registry reachability. Only relevant with a self-built override that was never built on this host. |
| Anonymous `GET /v1/gallery` returns 200 | The token gate is not in front of the gallery. Stop and investigate. |
| The Pi cannot reach the service port | Devices pull the gallery over that port, not through the UI. Check it from the Pi, not from a browser on another network. |
| Port 8089 already in use | Change it in the wizard and give devices the same value. |

## Step 2: Place the Embedding Model {#p2_embed type=manual required=true config=devices/place_embedder_pi.yaml}

Puts the DINOv2 ONNX where the console mounts it and switches the server off
the placeholder embedder. This preset uses a dynamically quantised INT8
DINOv2-small, not the DINOv2-base file used by the RK3588 preset — the
gallery is bound to whichever model built it, and the two are not
interchangeable.

### Prerequisites

- The console stack from Step 1, stopped or running — the file is placed next
  to its compose file and picked up on the next `docker compose up -d server`.
- `dinov2s_arcface_products10k_224_b1_dynint8.onnx`, 23,541,073 bytes, sha256
  `50e886aeab7b61a7eebe6ea3492b2d3ba0e74a859acedcbb9e9917b2b60454f6`. It is not
  shipped with this package: `use_scope: non-commercial`,
  `redistributable: false` (JD Products-10K terms, inherited by weights
  fine-tuned on it). The backbone `facebook/dinov2-small` is Apache-2.0; the
  restriction comes from the training data.
- 30 MB of free space on the console host.

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
| A new version appears but the device still misses the SKU | The console side provides a versioned, signed gallery; the device-side runtime that would fetch a version, verify its checksums and switch atomically does not exist yet (in progress — see upstream spec). |
| Registration is slow | Embedding on the console host is CPU work. It is per-image, not per-frame, so this is a one-time cost per SKU. |

## Step 4: Compile the HEF and Prepare the Pi {#p2_compile type=manual required=true config=devices/pi_hailo_compile.yaml}

Pins the HailoRT stack, compiles the detector HEF on an x86_64 host, and sets
the embedder on the CPU with the frame budget that follows from it.

### Prerequisites

- HailoRT and the PCIe driver at the same version on the Pi, both held, with the
  firmware matching. The measured run used 4.21.0 throughout, against the
  compiler version noted in `devices/pi_hailo_compile.yaml` (3.31.0) on the
  compile side.
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

## Preset: Jetson Orin — TensorRT {#p3_jetson_orin}

Both stages run as TensorRT fp16 engines on the Orin NX's own GPU. Measured on
a Seeed reComputer J40 unit itself — a reComputer J40 integrated-machine
measurement, not a reference board: detector 5.18 ms p50 / 5.28 ms p95, 99.91%
box agreement with the CPU reference (50 images, the same batch RK3588 was
checked against); embedder 4.23 ms p50 / 4.69 ms p95, 21 retrieval metrics
within 0.24 percentage points of fp32. A 2956-frame checkout replay ran
through the full device-side runtime — detector, embedder, gallery lookup,
MQTT publish — with zero dropped frames. The RK3588 preset has run a comparable full-loop
measurement too, on a shelf replay (see its own preset section); the Hailo-8
and RK3576 presets stop at model conversion. All figures are n=300,
inference only, on an engine built on the device it ran on.

| Device | Purpose |
|---|---|
| Console / on-prem host | Registration service, management UI, MQTT broker, gallery storage |
| reComputer J40 (Orin NX 16GB) | Detection and embedding, both on the GPU via TensorRT fp16 — the measured unit |
| reComputer J30 (Orin Nano 8GB) | Same family, same role; not tested. The numbers on this page are from the Orin NX (J40) only |
| RTSP / USB camera | Frames over the checkout belt or facing the shelf |

## Step 1: Deploy the Registration Console {#p3_console type=docker_deploy required=true config=devices/console_stack.yaml}

The console stack is real and deploys the same way here as in the other two
presets. Unlike the RK3588 and Hailo-8 presets, this one does not stop at the
console — Step 4 also builds a device-side runtime that has run end to end on
hardware.

### Prerequisites

- A Linux host with Docker and the compose plugin. No GPU needed.
- **Both container images are published**; `RETAIL_SERVER_IMAGE`/
  `RETAIL_WEB_IMAGE` default to them. Build both on this host from the
  upstream repository, SPA first, and override the two variables to use a
  local build instead.
- At least an admin token. No default, no anonymous read.
- A reverse proxy terminating TLS in front of the UI before external access.

### Troubleshooting

| Issue | Solution |
|---|---|
| "MISSING: `<image>`" before compose runs | The published default could not be pulled — check registry reachability. Only relevant with a self-built override that was never built on this host. |
| Anonymous `GET /v1/gallery` returns 200 | The token gate is not in front of the gallery. Stop and investigate. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Port 8089 already in use | Change it in the wizard. |

## Step 2: Place the Embedding Model {#p3_embed type=manual required=true config=devices/place_embedder_jetson.yaml}

Puts the DINOv2 ONNX where the console mounts it and switches the server off
the placeholder embedder. This preset uses the fp32 DINOv2-small ONNX — the
same file the TensorRT engine in Step 4 is built from — not the DINOv2-base
file used by the RK3588 preset or the dynamically quantised INT8 file used by
the Hailo-8 preset: the gallery is bound to whichever model built it.

### Prerequisites

- The console stack from Step 1, stopped or running — the file is placed next
  to its compose file and picked up on the next `docker compose up -d server`.
- `dinov2s_arcface_products10k_224_b1.onnx`, sha256
  `7f0136ef6459fdd5461e39e95070c7e964fbe2df4b53309f15f452c60da615be`. It is not
  shipped with this package: `use_scope: non-commercial`,
  `redistributable: false` (JD Products-10K terms, inherited by weights
  fine-tuned on it). The backbone `facebook/dinov2-small` is Apache-2.0; the
  restriction comes from the training data.
- A few tens of MB of free space on the console host.

### Troubleshooting

| Issue | Solution |
|---|---|
| Registration works but every lookup returns the wrong SKU | The server is on the placeholder embedder. Upstream defaults `embedder_backend` to `fake` (`server/config.py`), which hashes the image bytes into a vector. It is not reported by `GET /api/health` and not logged, so this symptom is the only signal. Set `RETAIL_EMBEDDER=onnx`, restart, and register every SKU again. |
| `server` container exits immediately after setting `RETAIL_EMBEDDER=onnx` | Either `RETAIL_EMBEDDER_ONNX` is empty — upstream refuses to start in that combination — or the path does not exist inside the container. Check that the file is in `assets/console/models/` and that the name matches the variable. |
| Galleries registered before and after the switch disagree | They cannot be mixed. Vectors from one embedder are not comparable to vectors from another. Register everything again on the new model. |
| A commercial deployment is planned | Retrain the embedder on first-party or permissively licensed capture and rebuild every gallery version. The shipped weights cannot be used for it. |

## Step 3: Register SKUs {#p3_register type=web_dashboard required=true config=devices/register_sku.yaml}

Register each SKU from 3 to 8 photographs. Each registration mints a new
immutable gallery version.

### Prerequisites

- The admin token from Step 1.
- 3–8 photographs per SKU, front, back and side, two lighting conditions.
- The DINOv2-small embedder from Step 2: the gallery must be built with the
  same model the reComputer J30 / J40's TensorRT engine was compiled from, or
  retrieval on this preset returns noise.

### Troubleshooting

| Issue | Solution |
|---|---|
| Registration refused with "fewer than three images" | By design. |
| The same sku_id returns 409 | By design. Pass `replace=true` to replace it. |
| Unsure which embedder to standardise on | DINOv2-small measured 79.20% top-1 at eight images per SKU on this preset's own TensorRT engine (fp32 reference is 79.11%; 21 retrieval metrics stay within 0.24pp of fp32 across the board); DINOv2-base (RK3588 preset) measured 84.67% at the same k but has not been converted for TensorRT. |
| Gallery version does not increase | The registration failed the quality gate. The response says which image. |

## Step 4: Build the TensorRT Engines {#p3_build type=manual required=true config=devices/jetson_trt_build.yaml}

Builds the two fp16 engines on the board, verifies their SHA against the
runtime config, and re-runs the parity check that produced the numbers on this
page.

### Prerequisites

- A reComputer J40 (Orin NX 16GB, family key `recomputer_j40`) with JetPack 6.2
  and TensorRT 10.3 — the versions the measured numbers were taken on. The
  engine is built on the board it will run on — engines are bound to the
  device and the TensorRT version, and must not be distributed between boards.
- The detector ONNX. It is not shipped here: the weights are trained on
  SKU-110K, which is academic and non-commercial with derivative works
  forbidden.
- The embedder ONNX from Step 2, if you have not placed it yet. Its licence is
  separate from the detector's and no less restrictive: `use_scope:
  non-commercial`, `redistributable: false`, inherited from the JD Products-10K
  training data (the `facebook/dinov2-small` backbone itself is Apache-2.0). It
  must not be redistributed with this package or baked into an image, and a
  commercial deployment has to retrain it on first-party or permissively
  licensed capture and rebuild every gallery version, because vectors from one
  embedder are not comparable to vectors from another.
- `platforms/jetson/build_engines.py` from the upstream repository at commit
  `16d1347` or later.

### Troubleshooting

| Issue | Solution |
|---|---|
| `trtexec` fails with "Static model does not take explicit shapes" | Both ONNX graphs are static batch-1; do not pass `--shapes`. `build_engines.py` at commit `16d1347`+ already handles this — only pass `--shapes` for a graph with a genuinely dynamic batch axis. |
| An engine built on one board fails on another | Expected. Engines bind to the device and the TensorRT version. Build per board. |
| `runtime.py --dry-run` exits with code 2 | The engine's recomputed sha256 does not match the value in `runtime.yaml`. Rebuild, or re-run `build_engines.py --update-config` to refresh the recorded hash. |
| Parity far below 99.91% (the measured detector box-agreement rate) | At that magnitude it is the decode or the output layout, not fp16 precision. |
| Retrieval delta far above 0.24 percentage points (the measured max across 21 metrics) | Check the ONNX sha256 against `7f0136ef…` — a different embedder weight, not fp16 loss, is the likely cause at that magnitude. |

## Step 5: Verify Registration, Retrieval and the Device Artifact {#p3_verify type=manual required=true verify=true config=devices/verify_recognition.yaml}

Reproduces the software loop, the console round trip, and the device-side
parity procedure that produced the numbers on this page.

### Prerequisites

- Steps 1 to 4 complete.
- A clone of the upstream repository with `uv sync` done.

### Deployment Complete

#### Quick verification

- `uv run python tools/verify_software_loop.py` passes.
- The console returns an increasing gallery version with the admin token, and
  401 or 403 with none.
- `GET /v1/gallery/current/download` returns a tar.gz whose SHA256SUMS verify.
- `platforms/jetson/runtime.py --config platforms/jetson/runtime.yaml
  --dry-run` passes: both engines' sha256 match `runtime.yaml`.
- The detector parity check reports box agreement at or near 99.91% (50
  images) and the retrieval delta check reports at or near 0.24 percentage
  points across 21 metrics.
- A checkout replay through `platforms/jetson/runtime.py` reports 0 dropped
  frames (`frames_dropped`, `capture_drop`, `embed_drop` all 0 in
  `/healthz`).

#### Running it end to end

The measured checkout replay used synthetic footage, not a live camera feed
— reproducing the full chain on your own board means supplying the four
pieces `runtime.yaml` expects:

1. **Frames.** `sources[0].uri` in `runtime.yaml` points at
   `local/frames_checkout`, read as a looping directory of JPEGs at the
   configured `fps`. For a synthetic dry run,
   `uv run python tools/make_checkout_sim.py --grocery-root
   /path/to/GroceryStoreDataset/dataset --skus 30 --events 40 --fps 15
   --seed 20260907 --out evaluation/data/checkout_sim` produces
   `<out>/frames/`; copy or symlink it to
   `platforms/jetson/local/frames_checkout`. For a real camera, change
   `sources[0].kind` to `usb` and `uri` to the device path (e.g.
   `/dev/video0`), or point it at an RTSP source per the comment in
   `runtime.yaml`.
2. **Gallery.** `python3 platforms/make_runtime_gallery.py --config
   platforms/jetson/runtime.yaml --skus-json
   evaluation/data/checkout_sim/gallery_skus.json` builds the version at
   `gallery.root` (`local/gallery`) from the same tool's registration
   photos, embedded with whichever model `runtime.yaml` names — the console
   registration flow from Steps 1-3 is the alternative path once real SKUs
   exist.
3. **MQTT.** `runtime.yaml`'s `mqtt.host` ships pointed at the evaluation
   broker; change it to a broker your deployment controls before running
   anything that publishes real events.
4. **Start it.** `python3 platforms/jetson/runtime.py --config
   platforms/jetson/runtime.yaml` (add `--dry-run` first, per Step 4). A
   `systemd` unit template is at `platforms/jetson/retail-runtime.service`
   if this should survive a reboot.

#### Next steps

- Run a soak beyond one 2956-frame replay if the deployment is 24/7.
- If moving to the shelf scene, retime detection and embedding at the shelf
  preset's 1280² input — the numbers on this page are all from the 640²
  checkout preset.

### Troubleshooting

| Issue | Solution |
|---|---|
| `runtime.py --dry-run` exits with code 2 | An engine's sha256 does not match `runtime.yaml`. Rebuild with `build_engines.py --update-config`, which writes the fresh hash back. |
| Latency far above 5.18 ms (detector) or 4.23 ms (embedder) p50 | Check `nvpmodel -q` is on `MAXN_SUPER` and that nothing else is holding the GPU — the runtime's own concurrent-load figures (8.76 ms / 5.37 ms p50) are the two-model-sharing-one-GPU case, not a regression. |
| The software loop passes and this looks finished | The loop runs on a development machine against a FakeEmbedder. It proves protocol behaviour, not device accuracy — the device-side parity check above is the one that does. |
| Wanting to mark this verified | This preset and the RK3588 preset both have a real device-side runtime measurement — the checkout replay here, a shelf replay on RK3588; the Hailo-8 and RK3576 presets stop at model conversion. |
