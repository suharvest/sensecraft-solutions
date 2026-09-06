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

Everything below was measured. The source path for each number is given so it
can be checked, and where a number does not exist, that is said instead of
estimated.

**Detection, Raspberry Pi 5 + Hailo-8** (`evaluation/runs/2026-09-06-det-hef/`,
both boundary files `status: measured`). The INT8 HEF runs at 9.04 ms p50, 9.10
ms p95, 110.4 fps single-stream. Independent cross-check with `hailortcli
benchmark`: 110.64 fps, 8.21 ms of pure hardware time — the extra 0.8 ms is the
Python vstream round trip. End to end, including letterboxing, output assembly,
decode and NMS, it is 18.74 ms p50 / 24.25 ms p95: the pure-numpy per-class NMS
over roughly 160 boxes costs more than the inference. Box agreement with the CPU
reference is 94.77% on 200 images and 94.68% on 300, at IoU ≥ 0.5. No thermal
throttling over the run; Hailo die temperature and power draw could not be read
on this platform and are recorded as unavailable rather than estimated.

**Detection, RK3588** (`evaluation/runs/2026-09-06-det-rk3588-radxa/results.md`,
Radxa ROCK 5T). RKNN fp16: 99.85% box agreement, 56.7 ms p50 / 89.5 ms p95.
RKNN INT8: 98.35% agreement, 26.0 ms p50 / 33.2 ms p95 — 2.2x faster for 1.5
percentage points of agreement.

**Embedding, Raspberry Pi 5 CPU**
(`evaluation/runs/2026-09-06-embed-small/` §8). Dynamically quantised INT8
DINOv2-small on four threads: 91.95 ms p50 / 105.98 ms p95 per crop, against
180.75 / 233.41 ms for the same model in fp32. Retrieval accuracy is within 0.65
percentage points of that fp32 baseline across all seven measured
configurations — weight-only quantisation costs essentially nothing here. The
static QDQ variant that also quantises activations loses 3.78 to 9.96 points and
is not usable.

**Retrieval accuracy** (`evaluation/runs/2026-09-06-embed-ft/` and
`.../embed-small/`, Grocery Store Dataset, 81 classes, fp32). DINOv2-base at
eight registration images per SKU: 84.67% top-1, 96.66% top-5. DINOv2-small at
the same k: 79.11% top-1. At one registration image per SKU, DINOv2-small drops
to 51.11% — the number of registered views is the single largest lever on the
page. On held-out Products-10K SKUs, DINOv2-base reaches 78.92% top-1 at k=8
across many more classes.

**Detection accuracy** (`evaluation/runs/2026-09-06-det-sku110k/`). On SKU-110K
test the 640² preset reaches 52.84 mAP50-95 and the 1280² preset 56.32. Both are
below the project's own stable threshold of 60, so both boundaries sit in the
failure tier and the package says so. mAP50 at 640 is 88.26: the boxes are
found, they are not placed tightly. Moving to 1280² lifts small-object mAP50-95
from 17.49 to 26.88, which is why the shelf preset exists.

**What has not been measured, and what does not exist.** The embedder does not
run on either NPU. Two Hailo DFC quantisation attempts were made
(`evaluation/runs/2026-09-06-embed-hailo/`) and neither produced a usable
figure. The o2 attempt collapsed: every image maps to an identical vector. The
default attempt lost 20 to 44 points against the fp32 baseline, but that number
is not a conclusion about DFC quantisation — the calibration set fed to the
optimise stage cannot be shown from the record to have been raw 0–255 pixels
rather than an already-normalised array, in which case the `.alls`
normalisation ran twice and part of that gap has nothing to do with
quantisation. The upstream default has been corrected and a dimension check
added; the default tier has to be re-run under the corrected pipeline before
anything can be concluded from it. The RKNN conversion of the embedder was
never attempted. There is no Jetson figure of any kind, and no TensorRT
backend in the repository. OCR reranking is specified and not implemented. And
there is no end-to-end number — no counting accuracy, no shelf-slot accuracy, no
72-hour run — because the process that would join detection, embedding, lookup
and publishing into one device-side service does not exist yet. Every boundary
file carries `reproduced_by: null`.

## Output Interfaces

| Interface | Where | Carries |
|---|---|---|
| MQTT `retail/v1/events` | Broker, 1883 | One message per frame with every box: track id, bbox, SKU, similarity, top-2 margin, OCR block, fallback flag, plus the gallery version and the model hashes |
| HTTP `/v1/gallery/*` | Service, 8089 | Registration, version listing, per-version manifest, the tar.gz devices pull, and rollback |
| HTTP `/api/*` | UI, 8080 | Event list, per-box event detail, and the summary behind the checkout/shelf board |

## Deployment Comparison

| Preset | Detector | Embedder | Measured on hardware | Gap |
|---|---|---|---|---|
| Rockchip NPU | RKNN fp16 on the NPU, 56.7 ms p50, 99.85% agreement | onnxruntime on the Rockchip CPU, never timed | Detector only, on RK3588 | No RKNN embedder conversion; no device pipeline |
| Pi 5 + Hailo-8 | INT8 HEF, 9.04 ms p50, 94.77% agreement | Dynamic INT8 DINOv2-small on the Pi CPU, 91.95 ms per crop | Both stages | No device pipeline; 92 ms per crop caps shelf use |
| Jetson Orin | Not implemented | Not implemented | Nothing | The entire TensorRT path has to be written first |

## Usage Notes

- **Register from at least three views.** Fewer than three is refused. Front,
  back, side, two lighting conditions is the working minimum; the measured jump
  from one image to eight is 28 percentage points of top-1.
- **Budget the frame by crop count, not by frame rate.** On the Pi, detection is
  9 ms and embedding is 92 ms per crop. A five-item basket is about half a
  second. A shelf frame at the measured density of 157.6 boxes is about 14
  seconds, so shelf use needs frame skipping or slot-level sampling.
- **Neither container image has been pushed.** Both are built on the console
  host from the upstream repository, with the SPA built first — the images do
  not run npm.
- **The bundled broker is anonymous plaintext.** Anyone who can reach port 1883
  can publish forged recognition events. Add accounts and TLS before this leaves
  a bench.
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
  trained weights carry `use_scope: academic-only`, `redistributable: false`.
- **Embedder weights — non-commercial.** Fine-tuned on JD Products-10K, whose
  terms restrict the database to non-commercial research and education. The
  weights carry `use_scope: non-commercial`, `redistributable: false`. The
  backbones themselves (`facebook/dinov2-base`, `facebook/dinov2-small`) are
  Apache-2.0 — the restriction comes from the training data, not the backbone.
- **Grocery Store Dataset — MIT**, used for retrieval evaluation only, and the
  only commercially usable dataset in the set.
- **RPC (CC BY-NC-SA 4.0), Unitail-OCR (academic only), GroZi-120 (licence
  unverified)** appear in the upstream evaluation plan and carry non-commercial
  or unverified scope.
- **The project's own code is Apache-2.0.**

A commercial deployment must retrain both models on first-party or permissively
licensed capture, and rebuild every gallery version afterwards. Per-artifact
fields — `license_id`, `use_scope`, `redistributable`, `source_revision`,
`sha256` — are in the upstream model cards; the summary is in
`gallery/ATTRIBUTION.md`.
