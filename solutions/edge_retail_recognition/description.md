## What it does

A camera watches the checkout belt or a shelf. A single-class detector boxes
every product in the frame — it does not classify, it only answers "there is a
product here". Each box is cropped, encoded into a 512-dimension vector, and
looked up by cosine similarity in a FAISS product library. The checkout lane
aggregates by track id so a product passing the camera is counted once; the
shelf aggregates by planogram slot and reports four states: ok, empty,
wrong_sku, unknown. One MQTT message per frame carries the results, along with
the library version and model hashes that produced them.

The point of this split is registration. Adding a SKU means taking 3 to 8
photos and sending them to the management service — neither the detector nor
the embedder learns anything, no retraining, and the library gains one
immutable version (with SHA256SUMS, rollable back). The management side is
implemented; the on-device runtime that pulls new versions automatically does
not exist yet — versions are shipped with the deployment for now.

## What you get

- **A single-class YOLOX-Tiny detector** in two fixed presets: checkout 640²
  and shelf 1280². Input size is a property of the compiled artifact and does
  not change at runtime.
- **A DINOv2 embedder fine-tuned with ArcFace**, in two sizes: DINOv2-base
  (348 MB fp32) and DINOv2-small (23.5 MB dynamic-quantised INT8, for the CPU
  path).
- **A versioned product library** — immutable version directories holding
  vectors, the SKU table, the FAISS index, a manifest and SHA256SUMS; atomic
  switchover, a single-writer lock, and rollback. Every version records which
  embedding model produced it, because vectors from different models are not
  comparable.
- **A registration and query service with a management UI** — three containers
  plus an MQTT broker, with three role-token tiers and no anonymous reads.
- **Conversion paths per platform**: Rockchip NPU (RKNN) and Hailo-8 (HEF),
  with conversion scripts, calibration recipes, and a parity flow that aligns
  the converted artifacts against the CPU reference.

## Where it fits

Checkout lanes that should read a basket of goods instead of scanning item by
item. Shelves that should report out-of-stock and misplacement without a person
walking the aisle. Stores that rotate SKUs weekly and cannot wait for a
training run each time.

Not for legal metrology, legally binding prices, or loss-prevention use — it
only counts what it can see.

## How well it works

| What the checkout gets | Typical | Device |
|---|---|---|
| Frames dropped in a 2956-frame checkout replay | **0** | reComputer J40 (Orin NX 16GB) |
| Product recognition, DINOv2-base, 8 registrations per SKU | **top-1 84.67% / top-5 96.66%** | Model figures, hold across hosts |
| Product recognition, DINOv2-small, 8 vs 1 registrations per SKU | **top-1 79.11% → 51.11%** | Same as above |

Registration count is the biggest accuracy lever — going from 1 to 8 photos
moves top-1 by 28 points on the same model — so shoot each SKU from several
angles when registering.

A shelf-tier host does the same job more slowly: on a reComputer RK3588
replaying a 20-SKU shelf, frame-to-result published is p50 924 ms /
p95 1153 ms with zero publish errors. The Hailo-8 preset currently stops at
model conversion.

## Output Interfaces

| Interface | Where | Content |
|---|---|---|
| MQTT "retail/v1/events" | broker, 1883 | One message per frame with every box: track id, bbox, SKU, similarity, top-2 gap, OCR blocks, fallback flags, plus the library version and model hashes |
| HTTP "/v1/gallery/*" | service, 8089 | Registration, version list, per-version manifest, the tar.gz devices pull, and rollback |
| HTTP "/api/*" | UI, 8080 | Event list, per-event box detail, and the aggregates behind the checkout/shelf dashboards |

## Deployment Comparison

| Preset | Detector | Embedder | Best for |
|---|---|---|---|
| reComputer J40 (Jetson Orin NX, TensorRT) | GPU TensorRT fp16, p50 5.18 ms | GPU TensorRT fp16, p50 4.23 ms | Fastest measured path; 2956-frame checkout replay with zero drops |
| reComputer J30 (Jetson Orin Nano, TensorRT) | GPU TensorRT fp16, p50 5.88 ms | GPU TensorRT fp16, p50 5.06 ms | Also benchmarked end to end: 6726-frame replay, zero drops |
| reComputer RK3588 series | NPU RKNN fp16, p50 56.7 ms (INT8 reaches 26.0 ms) | CPU onnxruntime | Rockchip toolchain; shelf replay proven end to end (p50 924 ms) |
| reComputer RK3576 | Dual-core NPU RKNN fp16, p50 51.05 ms | Dual-core NPU RKNN fp16, p50 56.38 ms | Smaller Rockchip option with both stages on the NPU |
| reComputer R2000 (Hailo-8) | INT8 HEF, p50 9.04 ms | CPU dynamic INT8 DINOv2-small, 91.95 ms per crop | Fastest detection of the five |
| reCamera Pro | On-board NPU RKNN fp16, p50 112.3 ms | On-board NPU RKNN fp16, p50 77.5 ms | All-in-one camera, no host in the chain |

## Usage Notes

- **Register at least three views.** Fewer than three photos is rejected.
  Front, back and side under two lighting conditions is a working minimum;
  measured top-1 gains 28 points going from 1 to 8 photos.
- **Budget a frame by crop count, not by frame rate.** On the Hailo-8 path,
  detection is 9 ms and embedding is 92 ms per crop: a five-item basket takes
  about half a second; a shelf frame at measured density takes ~14 s, so shelf
  scenarios need frame decimation or per-slot sampling.
- **Two container images are built at deploy time**, both on the management
  host from the upstream repository, and the SPA must be built first.
- **The bundled broker is anonymous and plaintext.** Add accounts and TLS
  before going into a store.
- **Model, preprocessing and library version are bound together.** A library
  built by one embedder is unreadable by another — that is why the version
  manifest records both hashes.
- **The models are fine-tuned on studio product photos.** Test with your own
  shelf images before making any commitment about your shelves.

## Licensing note

The project code and the DINOv2 backbones are Apache-2.0, but **neither bundled
model weight may be used commercially**: the detector weights are trained on
SKU-110K (academic and non-commercial use only, no derivative works), and the
embedder weights are fine-tuned on JD Products-10K (non-commercial research and
education only). Commercial deployment means retraining both models on
self-collected or permissively licensed data and rebuilding every library
version. Summary in "gallery/ATTRIBUTION.md".
