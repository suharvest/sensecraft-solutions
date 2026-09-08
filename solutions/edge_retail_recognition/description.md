## What it does

A camera watches a checkout belt or a shelf. A single-class detector finds every
product in the frame — it does not classify them, it only says "there is a
product here". Each box is cropped, embedded into a 512-dimensional vector, and
looked up in a FAISS gallery by cosine similarity. At the checkout the results
are aggregated by track id so one item passing the camera is counted once; on
the shelf they are aggregated per planogram slot and reported as ok, empty,
wrong SKU or unknown. The whole thing goes out as one MQTT message per frame,
carrying the gallery version and the model hashes that produced it.

The point of the split is registration. Adding a SKU means photographing it 3
to 8 times and posting the images to the console — the detector never learns
about it, and the embedder never learns about it either. The gallery gains a new
immutable version. The console side of that protocol is implemented — versions
are immutable, each carries SHA256SUMS, and rollback re-verifies the target
version before switching without minting a new one. The device-side runtime
that would fetch a version, verify its checksums and switch atomically does not
exist yet. Nothing retrains.

## What you get

- **A single-class YOLOX-Tiny detector** in two fixed presets: 640² for the
  checkout, 1280² for the shelf. The input size is a property of the compiled
  artifact and is never changed at run time — the two presets exist precisely
  so that shelf frames are not squeezed through a checkout-sized input.
- **A DINOv2 embedder fine-tuned with ArcFace** on e-commerce product imagery,
  in two sizes: DINOv2-base (348 MB fp32) and DINOv2-small (23.5 MB dynamically
  quantised INT8, for CPU paths).
- **A versioned gallery** — immutable version directories with vectors, a SKU
  table, a FAISS index, a manifest and SHA256SUMS; atomic switch, single-writer
  lock, rollback. Every version records which embedding model and which
  preprocessing produced it, because vectors from two different models are not
  comparable and the symptom of mixing them is "nothing is recognised".
- **A registration and query service plus a management UI**, in three
  containers with an MQTT broker. Token-gated with three roles and no anonymous
  read.
- **Platform conversion paths** for Rockchip NPU (RKNN) and Hailo-8 (HEF), with
  the conversion scripts, the calibration recipes and the parity procedure that
  checks a converted artifact against the CPU reference.

## Where it fits

A checkout lane where the till should read a basket rather than a barcode. A
shelf that should report gaps and misplacements without anyone walking it. A
store that adds and drops SKUs weekly and cannot wait for a training run each
time.

It does not fit anywhere that needs a certified retail scale, a legally binding
price, or theft detection. It counts what it can see, and it has no view on what
it cannot.

## How well it works

| What the checkout gets | Typical | Device |
|---|---|---|
| Frame captured to a recognised item published | **22.30 ms p50 / 42.75 ms p95** | reComputer J40 (Orin NX 16GB) |
| Frames dropped over a 2956-frame checkout replay | **0** | reComputer J40 |
| Item recognition, 8 photos registered per SKU | **84.67% top-1 / 96.66% top-5** | Model figure, carries across hosts |
| Item recognition, 1 photo registered per SKU | **51.11% top-1** | Same |

Registration depth is what moves accuracy most, so photograph each SKU from
several angles when you register it. The J40 replay ran the full device-side
runtime — detector, embedder, gallery lookup, MQTT publish. Measured on the
Orin NX unit (reComputer J40) only; the smaller Orin Nano option in the same
family (reComputer J30) has not been tested.

A shelf host does the same job more slowly: on a reComputer RK3588 running a
20-SKU shelf replay with retrieval on the registration console, frame to
published item is 924 ms p50 / 1153 ms p95, with zero publish errors and
automatic MQTT reconnection after a 38 s console outage. On the full 704 crops
from that same replay, RKNN fp16 and CPU fp32 both scored 541/704 top-1 and
agreed on the same predicted SKU in 695/704 cases. The Hailo-8 and RK3576
presets stop at model conversion.

The Hailo-8, RK3588 and RK3576 figures are reference values taken on the same
accelerator chip platform as the matching reComputer preset; they will be
updated after a re-test on the reComputer units. Per-accelerator conversion
detail and quantisation results are in the engineering wiki.

## Output Interfaces

| Interface | Where | Carries |
|---|---|---|
| MQTT "retail/v1/events" | Broker, 1883 | One message per frame with every box: track id, bbox, SKU, similarity, top-2 margin, OCR block, fallback flag, plus the gallery version and the model hashes |
| HTTP "/v1/gallery/*" | Service, 8089 | Registration, version listing, per-version manifest, the tar.gz devices pull, and rollback |
| HTTP "/api/*" | UI, 8080 | Event list, per-box event detail, and the summary behind the checkout/shelf board |

## Deployment Comparison

| Preset | Detector | Embedder | Best for |
|---|---|---|---|
| reComputer RK3588 series | RKNN fp16 on the NPU, 56.7 ms p50, 99.85% agreement | onnxruntime on the CPU | Rockchip toolchain, INT8 available at 26.0 ms p50. With the embedder swapped to RKNN on the NPU (not the CPU path in this row), the full device-side loop also ran end to end once (20-SKU shelf replay, 924 ms p50) |
| reComputer RK3576 | RKNN fp16 on both NPU cores, 51.05 ms p50, 99.91% agreement | RKNN fp16 on both NPU cores, 56.38 ms p50, max 0.36pp retrieval gap vs fp32 | Both stages on the NPU; smaller, two-core Rockchip option |
| reComputer R2000 (Hailo-8) | INT8 HEF, 9.04 ms p50, 94.77% agreement | Dynamic INT8 DINOv2-small on the CPU, 91.95 ms per crop | The fastest detector path; both stages measured on one board |
| reCamera Pro | RKNN fp16 on the onboard NPU, 112.3 ms p50, 99.91% agreement | RKNN fp16 on the onboard NPU, 77.5 ms p50, cosine 0.998 vs fp32 | All-in-one camera; both stages measured on the same board |
| reComputer J40 (Jetson Orin NX, TensorRT) | TensorRT fp16 on the GPU, 5.18 ms p50, 99.91% agreement | TensorRT fp16 on the GPU, 4.23 ms p50, max 0.24pp retrieval gap vs fp32 | Fastest per-stage numbers measured; full device-side loop also run end to end (2956-frame checkout replay, zero dropped frames) |

The Hailo-8, RK3588 and RK3576 rows are reference values taken on the same
accelerator chip platform as the matching reComputer preset; they will be
updated after a re-test on the reComputer units. The reCamera Pro and
reComputer J40 rows are measured on a reComputer unit itself — a reComputer J40
integrated-machine measurement, not a reference board.

## Usage Notes

- **Register from at least three views.** Fewer than three is refused. Front,
  back, side, two lighting conditions is the working minimum; the measured jump
  from one image to eight is 28 percentage points of top-1.
- **Budget the frame by crop count, not by frame rate.** On the Hailo-8 path,
  detection is 9 ms and embedding is 92 ms per crop. A five-item basket is about
  half a second. A shelf frame at the measured density of 157.6 boxes is about
  14 seconds, so shelf use needs frame skipping or slot-level sampling.
- **The container images are built at deploy time.** Both are built on the
  console host from the upstream repository, with the SPA built first — the
  images do not run npm.
- **The bundled broker is anonymous plaintext.** Anyone who can reach port 1883
  can publish forged recognition events. Add accounts and TLS before this goes
  into a store.
- **Keep the model, the preprocessing and the gallery version together.** A
  gallery built with one embedder is not readable by another. The version
  manifest records both hashes for exactly this reason.
- **The models were fine-tuned on e-commerce packshots.** The upstream model
  card states that shelf and checkout deployment still needs first-party
  capture. Measure on your own shelf before promising anything about it.

## Licensing note

This package ships no model weights and no dataset imagery. Both are constrained,
and the constraints are inherited by anything trained on them:

- **Detector weights — academic and non-commercial only, derivative works
  forbidden.** They are trained on SKU-110K, whose Trax licence permits academic
  and non-commercial use and whose clause (iii) forbids derivative works. The
  trained weights carry "use_scope: academic-only", "redistributable: false".
- **Embedder weights — non-commercial.** Fine-tuned on JD Products-10K, whose
  terms restrict the database to non-commercial research and education. The
  weights carry "use_scope: non-commercial", "redistributable: false". The
  backbones themselves ("facebook/dinov2-base", "facebook/dinov2-small") are
  Apache-2.0 — the restriction comes from the training data, not the backbone.
- **Grocery Store Dataset — MIT**, used for retrieval evaluation only, and the
  only commercially usable dataset in the set.
- **RPC (CC BY-NC-SA 4.0), Unitail-OCR (academic only), GroZi-120 (licence
  unverified)** appear in the upstream evaluation plan and carry non-commercial
  or unverified scope.
- **The project's own code is Apache-2.0.**

A commercial deployment must retrain both models on first-party or permissively
licensed capture, and rebuild every gallery version afterwards. Per-artifact
fields — "license_id", "use_scope", "redistributable", "source_revision",
"sha256" — are in the upstream model cards; the summary is in
"gallery/ATTRIBUTION.md".
