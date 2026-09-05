# Waste Sorting at the Bin

Trigger a shot, get back what the item is made of and which of the four
Chinese municipal waste streams it belongs in, on MQTT, in one message.

**Nothing on this page has run on hardware.** Every accuracy and latency
figure below was measured with onnxruntime on an Apple M4 CPU. There is no
Jetson, Hailo or RKNN number anywhere on this page, and no preset claims
`verified: [hardware]`.

## What it does

A trigger — a button, an HTTP call, or motion in the frame — makes the device
capture one image, classify the item in it into one of eight material classes,
look up the Chinese four-way disposal category from that class, and publish a
single MQTT message with the class, the four-way category, the top-3 with
confidences, and a reference to the stored image. The image bytes never leave
the device; the payload carries a path or object-store URI only. In parallel,
an async callback receives the four-way category so a flap, relay or indicator
can act on it.

## What you get

- **Two layers of answer from one head.** The model predicts eight material
  classes — paper, cardboard, glass, metal, plastic, textile, organic,
  residual. The Chinese four-way category (可回收物 / 厨余垃圾 / 有害垃圾 /
  其他垃圾) is a lookup table on top of that, not a second head, so changing a
  local authority's rules is a table edit rather than a retrain.
- **Trigger-on-demand, not a video stream.** Button, HTTP or motion, with an
  800 ms debounce; a trigger that arrives while one is in flight is merged
  rather than queued. A continuous mode exists, rate-limited and requiring
  three identical top-1 predictions in a row before it publishes.
- **A contract that is checked, not just documented.** Every payload is
  validated against the event schema before it is published, including the two
  rules a JSON Schema cannot express: `category` must equal `top3[0]` and
  `confidence` must equal `top3[0].confidence`. A payload that fails is
  counted and dropped.
- **An optional open-vocabulary track.** A SigLIP 2 vision tower scored
  against constant text prototypes, selectable per deployment with
  `model.track: open_vocab`. It adds classes without retraining, answers in
  Chinese or English from the same image embedding, and can score "this is not
  in my vocabulary" — none of which a closed-set head can do. It is 40× slower.
- **An actuator interface with no pin binding.** The runtime calls back with a
  category; where that goes is integration work, which is why the same build
  runs on boards with different headers.

## Where it fits

- Household and community drop-off points: photograph one item at the moment
  of disposal and tell the resident which bin it goes in.
- Sorting stations where an operator presents items one at a time and wants a
  second opinion plus an audit trail on MQTT.
- Bins with a motorised flap or a lane indicator, driven from the four-way
  category through the GPIO callback.

Not in scope: conveyor-belt sorting with mechanical actuation, and street-level
litter detection. The latter is a second phase and needs a detector, not a
classifier — this model assumes one item per image.

## How well it works

**This is not a compliance or regulatory classification system.** The four-way
mapping is a table this project maintains, not an authority's certified ruling,
and municipal definitions differ between cities. Nothing here should be the
sole basis for a charging, penalty or compliance decision.

Two classifiers were measured on the **same split**, same images, same 224²
input, same post-processing, on the same Apple M4 CPU.

### Measured boundaries — baseline classifier (MobileNetV3-Small)

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Material top-1 (8 classes) | 0.8792 | val, 7417 images / 1882 groups; TrashNet 392 + GC3 7025; onnxruntime 1.25.1 CPU; ONNX `51c7c0ed…` | This project, `evaluation/runs/2026-09-06-m1b-cpu` |
| Material top-5 | 0.9854 | same | same |
| Chinese four-way top-1 | 0.9519 | same; lookup on top of the eight-class argmax | same |
| macro-F1 (7 classes with samples) | 0.8292 | `textile` excluded — zero samples | same |
| Material top-1, held-out test | 0.8807 | test, 7290 images; first measurement on this split | This project, `evaluation/runs/2026-09-05-w1-cpu` baseline column |
| Inference latency (single image) | mean 1.886 ms / p50 1.769 ms / p95 2.276 ms | `session.run` only, Apple M4 CPU, batch 1 | `evaluation/runs/2026-09-06-m1b-cpu` |
| Images below 0.5 confidence | 335 (4.5%) | val | same |

**Report both top-1 numbers together.** The four-way figure (0.9519) is much
higher than the material figure (0.8792) because glass↔metal↔plastic confusion
is absorbed — all three map to 可回收物. Quoting only the four-way number
overstates what the model knows about materials.

### Measured boundaries — open-vocabulary track (SigLIP 2 ViT-B/16)

Same split, same images, same post-processing, same machine.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Material top-1 (8 classes) | 0.8501 | val, 7417 images; English prompt set `waste8-en/v1`, template `t02`, 16-shot α=0.8, temperature 0.0075 | This project, `evaluation/runs/2026-09-05-w1-cpu` |
| Material top-5 | 0.9987 | same | same |
| Chinese four-way top-1 | 0.9393 | same; hierarchical path (eight classes then mapped) | same |
| macro-F1 (7 classes) | 0.7460 | same | same |
| ECE (15 bins) | 0.0221 | same | same |
| Open-set AUROC | 0.7538 | mean over the 7 classes with samples, leave-one-class-out, score = `1 - max softmax` | same |
| Cross-lingual agreement (zh vs en, same image) | 0.8698 material / 0.9143 four-way | one visual embedding, three prototype banks — no preprocessing or sampling noise in this number | same |
| Material top-1, held-out test | 0.8620 | test, 7290 images; templates/α/temperature never searched on it | same |
| Inference latency (single image) | p50 66.93 ms / p95 91.62 ms | Apple M4 CPU, batch 1, vision tower only | same |

### Baseline vs open-vocabulary, same split

| Metric | Baseline (MobileNetV3-Small) | Open-vocab (SigLIP2-B/16) |
|---|---:|---:|
| Material top-1, val | **0.8792** | 0.8501 |
| Material top-1, test | **0.8807** | 0.8620 |
| Chinese four-way top-1, val | **0.9519** | 0.9393 |
| macro-F1, val | **0.8292** | 0.7460 |
| ECE (15 bins), val | 0.0308 | **0.0221** |
| Open-set AUROC | not possible — a closed-set head cannot drop a class without retraining | **0.7538** |
| Cross-lingual agreement | no text side | **0.8698 / 0.9143** |
| Zero-shot new class | requires a retrain | **prompt edit** |
| CPU p50 latency | **1.57 ms** | 66.93 ms |

Both columns come from the same val/test files, the same 224² input and the
same softmax/top-k/mapping code path. The baseline column was recomputed on
this split for the comparison; its val top-1 matches the standalone m1b report
to the digit.

### Hailo-8 — nothing compiled yet

| Path | Status |
|---|---|
| Baseline MobileNetV3-Small → HEF | Not attempted. No HEF exists for this solution. |
| SigLIP 2 vision tower → HEF | `hailo parser` passes end to end with no unsupported op. `hailo optimize` (INT8 PTQ, 256 calibration images, optimization_level=1) **fails** with `NegativeSlopeExponentNonFixable` at layer `ne_activation_mul_and_add78` — "Desired shift is 16.0, but op has only 8 data bits". No optimized HAR, no compiler run, no HEF. |

**Hailo path pending: the INT8 quantisation retry is in progress; if it fails
the fallback is distillation into a small student model.** The parse-stage
numerical check did pass — the DFC native emulator matches CPU onnxruntime with
cosine similarity 1.0 and identical top-1 on all 20 comparison images — so the
ONNX→HAR translation introduces no error. That is the half of the question that
can be answered without a Hailo-8; the INT8 half cannot.

This does not support the claim that SigLIP2 cannot run on a Hailo-8. One
attempt was made at one optimization level with one calibration set, and the
error message itself names three possible causes; only one of them
(calibration-set normalisation) has been checked and ruled out.

### RK3588 (Radxa ROCK 5T) — inference parity verified on hardware, no deployment package

The only on-device measurement this project has. Converted on wsl2-local with
rknn-toolkit2 2.3.2, run on a Radxa ROCK 5T with librknnrt **2.3.2** (the
symlink names it 2.3.0; the in-library version is what matters), 50 val images,
`core_mask=AUTO`.

| Model / precision | Latency p50 / p95 | Agreement with CPU golden | Conditions |
|---|---|---|---|
| MobileNetV3-Small, **fp16** | 4.44 ms / 6.32 ms | top-1 **98%** (49/50) | ONNX sha `aa181dd5…`, 50 val images |
| MobileNetV3-Small, **int8** | 4.70 ms / 11.04 ms | top-1 **22%** (11/50) — **unusable** | 64-image calibration set from train |
| SigLIP 2 vision tower, **fp16** | 169.4 ms / 170.5 ms | embedding cosine mean **0.999617**, min 0.998841 | ONNX sha `6f664af0…`, 191 MB .rknn |

**Do not ship int8 on RK.** The int8 failure is class collapse, not noise: 34 of
50 images collapse onto one class id, against a 14.3% random baseline for the
seven classes with samples — the quantised head has lost its decision
boundaries rather than gained a little error. Fixing it means a larger
calibration set or a per-channel / mixed-precision strategy, neither of which
has been tried. **The RK platform ships fp16 only.**

Note the conditions: this run used a MobileNetV3 ONNX with sha256 `aa181dd5…`,
which is not the m1b file (`51c7c0ed…`) every accuracy figure above refers to.
The parity result is about the runtime, not about accuracy, and the two should
not be combined into an accuracy claim for RK3588.

### Platform support

| Platform | Status |
|---|---|
| Jetson Orin (TensorRT) | Deployment package shipped, untested on hardware |
| Raspberry Pi 5 + Hailo-8 | Deployment package shipped; no HEF exists, INT8 quantisation retry in progress |
| RK3588 | **Inference parity verified on hardware (fp16); no deployment package** — no compose file, no image, no preset. The conversion and the runtime work; the packaging does not exist. |
| CPU (onnxruntime) | Every accuracy figure on this page |

### Caveats that change what you can claim

- **`textile` has zero training samples and zero evaluation samples.** Neither
  source dataset contains a cloth or textile category — the GC3 v2 export has
  no such label, contrary to a widely repeated secondary description of it. The
  eighth logit is still there, and the ONNX output is still `1×8` because the
  output shape is part of the contract, but nothing has ever trained or tested
  it. Every table reports `n/a` for this class, not 0. The model has never
  predicted it once.
- **`hazardous` (有害垃圾) has no material class mapped to it.** It is in the
  enum so the schema stays stable, but this build will never emit it.
- **GC3 reuses TrashNet source photographs, and the deduplication catches it.**
  Grouping is by source batch + origin image + perceptual hash (dhash 8×8,
  Hamming ≤ 3), unioned into connected components; 430 near-duplicate merges,
  **183 of them across the two datasets** — GC3 relabelled a substantial number
  of TrashNet's own photographs as detection boxes. Groups move between splits
  as a unit, and the split asserts that no group and no identical dhash spans
  two splits. Without that, the numbers above would be leakage, not accuracy.
- **Domain shift is not measured.** Both datasets are photographs of single
  items: TrashNet on a white poster board under daylight or indoor light, GC3 a
  detection dataset with objects off-centre and often occluded. Neither is a
  real bin — no wet, crushed, stacked, backlit or partially bagged waste is in
  the evaluation. **No field set has been collected, so there is no number for
  how much accuracy drops in a real bin.** Expect it to drop; the size of the
  drop is unknown.
- **`organic` dominates the data.** It is 48.9% of the training set and 47.1%
  of val, because GC3's `BIODEGRADABLE` class alone accounts for 45407 of
  74090 original boxes. Its recall (0.9791) is well above every other class
  (0.70–0.88), and the confusion matrix shows the model pushing uncertain items
  toward it.
- **`residual` has 20 val samples.** No precision figure for that class should
  be quoted on its own — the open-vocabulary track's 0.2754 precision there is
  an artefact of the sample count as much as of the model.

### Deployment footprint

| Item | Size |
|---|---|
| Baseline ONNX (`mobilenetv3s_waste8.onnx`) | 6,118,606 B |
| SigLIP 2 vision tower ONNX (`siglip2_vision_224.onnx`) | 371,695,898 B |
| Prototype banks + calibration report | ~155 KB total |

## Classifier selection: baseline vs open-vocabulary

Both tracks are real and both are shipped. The choice is not "old vs new".

**The baseline is more accurate on this taxonomy.** Same split, same images:
0.8792 vs 0.8501 on val, 0.8807 vs 0.8620 on test — the closed-set head leads
by about 3 points on val and 2 on test. That is the metric the open-vocabulary
track does not win.

**What the open-vocabulary track wins is everything the closed set structurally
cannot do:**

- **Calibration.** ECE 0.0221 vs 0.0308 on val, 0.0250 vs 0.0345 on test. Its
  confidence means more, which matters when a threshold decides whether the
  flap moves.
- **Open-set rejection.** AUROC 0.7538 for "this item is not in my vocabulary".
  The closed-set head cannot produce this number at all — removing a class from
  a fixed softmax head means retraining.
- **Cross-lingual answers.** 0.8698 agreement between Chinese and English
  prompts on the material classes, 0.9143 after mapping to the four-way
  categories, from a single visual embedding. The baseline has no text side.
- **Adding a class without retraining.** A new category is a prompt edit and a
  prototype rebuild, not a training run — the direct answer to `textile` having
  no data.

**The cost is 40× latency:** p50 66.93 ms vs 1.57 ms on the same M4 CPU. That
is not an implementation gap — ViT-B/16 at 224² is roughly 17.6 GFLOPs against
MobileNetV3-Small's 0.06. **Open-vocabulary is not a real-time CPU option.** Its
landing places are (a) a form factor with an NPU or GPU, or (b) as a teacher for
a distilled student model.

Two further findings from the calibration run, both of which shape how the
track is deployed:

- **Use the hierarchical path, not direct four-way prediction.** English
  eight-class predictions mapped to the four categories score 0.9393; Chinese
  prompts predicting the four categories directly score 0.8478. "Recyclable" is
  not a visual concept; "glass bottle" is.
- **The `residual` category is the weakest thing in the open-vocabulary
  setup.** Its leave-one-out AUROC is 0.5795, near chance: remove "general
  waste" from the vocabulary and some material word always catches those items
  with high confidence. It is a fallback definition, not a visual concept.

## Output Interfaces

| Interface | Where | What it carries |
|---|---|---|
| MQTT `waste/<stream-id>/results` | port 1883 | One JSON per classification: material class, Chinese four-way category, confidence, top-3, trigger source, image reference, model name and ONNX sha256, taxonomy version |
| MQTT `waste/<stream-id>/fallback` | port 1883 | Optional `waste_fallback` event — a VLM second opinion on an ambiguous item, keyed by frame_id. Never changes the main event. |
| HTTP `/trigger` | port 8080 | POST fires one capture-and-classify |
| HTTP `/preview.mjpg`, `/healthz`, `/events` | port 8080 | Live view, counters and inference time, recent results with their top-3 |
| GPIO callback | in-process | Async callback carrying the four-way category. No pin binding — that is integration work. |

The image is never in the payload. `image_ref.kind` is `none`, `local` or
`object_store`; base64 image bytes in a payload are a contract violation and
are rejected before publishing.

### The `waste_fallback` side channel

Off by default. When enabled, an item that trips either gate — top-1 below
`vlm.trigger.min_confidence`, or top-1 minus top-2 below `vlm.trigger.margin` —
is sent to an external VLM service, and its answer is published as a separate
event on the fallback topic. **It never backfills the main event.**

| Field | What it carries |
|---|---|
| `type` | Always `waste_fallback` |
| `frame_id` | Matches the `waste_sorting_result` event for the same frame |
| `trigger` | `low_confidence` or `ambiguous`. When both gates trip, the stronger one (`low_confidence`) is reported. |
| `category` | The VLM's category, in the same shape as the main event's — one parser serves both streams |
| `confidence` | The VLM's own confidence. Not comparable with the classifier's softmax confidence. |
| `rationale` | One line of reasoning. Never parsed. |
| `explanation` | Longer text, present only with `vlm.explain_on_fallback` — one extra call per fallback |
| `primary_confidence`, `primary_top3` | What the classifier said, copied verbatim, so a consumer can see what tripped the gate |
| `vlm_model`, `vlm_latency_ms`, `prompt_sha256` | Which model, how long its generation took, which prompt template produced the answer |

**Verified as wiring, not as a result.** The path was run end to end against
the real edge-vision-vlm application with its generation backend replaced by a
stub: 5 frames, 5 contract-valid main events, 2 fallback events, 0 rejects.
Request validation, taxonomy matching and the response fields are the service's
real code; the generated text is not, and the run's `vlm_latency_ms` of 12.5 ms
is a hard-coded constant. **Real-model latency, and whether the VLM is actually
more often right on the items that trip these gates, are pending verification
against a real service on Orin.** Treat the fallback stream as a second opinion
to log, not a correction to act on.

## Deployment Comparison

**Camera + reComputer J (Orin)** — the only preset with a model file. The
TensorRT engine is built on the device during deployment, because an engine is
tied to the exact GPU architecture and TensorRT version and cannot be shipped
prebuilt. It is also the only preset offering the open-vocabulary track: the
SigLIP 2 tower at 67 ms per image on CPU needs an accelerator, and the Orin is
the accelerator this package has. Nothing has been measured on it yet.

**Camera + Raspberry Pi 5 (Hailo-8)** — prepares the board and validates the
three Hailo ABI gates, then stops. The baseline HEF has not been compiled, so
there is no model to deploy. Choose it to get the board ready; do not choose it
expecting a running classifier.

## Usage Notes

- **One item per image.** There is no detector. Two items in one frame produce
  one answer, and which one it describes is undefined.
- **The camera and the drop area are the whole input.** Framing that leaves the
  item small in the frame degrades the classification, and none of the figures
  above were measured under such framing.
- **In continuous mode, three identical top-1 predictions in a row are required
  before publishing**, and the mode is rate-limited. Trigger mode has no such
  smoothing — a single shot is a single answer.
- **The bundled MQTT broker allows anonymous connections.** That is for local
  commissioning. A deployment that leaves the bench needs a broker with
  credentials.
- **The GPIO callback is not wired to anything by default.** `actuator.enabled`
  defaults to false; enabling it without providing the binding code changes
  nothing.
- **`vlm.apply_fallback_to_gpio` stays false.** A flap must not wait on a call
  whose P50 is measured in seconds.

## Licensing note

Code in the upstream repository is Apache-2.0. The SigLIP 2 checkpoint
(`google/siglip2-base-patch16-224`, revision `75de2d55…`) is Apache-2.0.

Both training datasets permit redistribution and derivative works with
attribution, so figures and models derived from them may be used externally:

- **TrashNet — MIT License, Copyright (c) 2017 Gary Thung.** Verified against
  two first-party sources: the repository's own `LICENSE` file at commit
  `6fa2b87`, and the `license` field of the official HuggingFace dataset card.
  Note that the upstream project's own SPEC and its survey report both record
  this as CC BY 4.0; that is wrong, and no first-party source states CC BY 4.0.
- **Garbage Classification 3 — Material Identification (Roboflow Universe) —
  CC BY 4.0**, stated verbatim in the export package's own
  `README.dataset.txt`.

Attribution string for external material:

```
TrashNet — Gary Thung and Mindy Yang, https://github.com/garythung/trashnet,
MIT License, Copyright (c) 2017 Gary Thung.
Garbage Classification 3 — Material Identification / Roboflow Universe,
https://universe.roboflow.com/material-identification/garbage-classification-3,
licensed CC BY 4.0.
```

No dataset-derived image is committed in this package. `assets/models/` holds
checksums only; see `gallery/ATTRIBUTION.md`.
