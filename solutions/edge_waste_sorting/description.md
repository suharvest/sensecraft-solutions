# Waste Sorting at the Bin

Trigger a shot, get back what the item is made of and which of the four
Chinese municipal waste streams it belongs in, on MQTT, in one message.

**The baseline classifier is EfficientNet-Lite0 (m1c), not MobileNetV3-Small.**
The original baseline (MobileNetV3-Small, "m1b") collapsed under INT8
quantisation on all three edge chains tested (Hailo emulator, RK3576, RK3588);
EfficientNet-Lite0 does not, and is now the shipped baseline. Most accuracy
figures below still come from onnxruntime on an Apple M4 CPU, but the Hailo-8
and RK3588 sections carry real INT8 numbers: RK3588 numbers are a real Radxa
ROCK 5T device, Hailo-8 numbers are the DFC emulator only — **no Hailo-8
hardware has been used anywhere on this page.** No preset claims
`verified: [hardware]` yet.

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

### Measured boundaries — baseline classifier (EfficientNet-Lite0, m1c)

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Material top-1 (8 classes) | 0.8877 | val, 7417 images; onnxruntime 1.25.1 CPU; ONNX `e9f9e847…`, 13,477,056 B | This project, `evaluation/runs/2026-09-06-m1c-cpu` |
| Material top-5 | 0.9833 | same | same |
| Chinese four-way top-1 | 0.9500 | same; lookup on top of the eight-class argmax | same |
| macro-F1 (7 classes with samples) | 0.8511 | `textile` excluded — zero samples | same |
| Material top-1, held-out test | 0.8802 | test, 7290 images, same split as m1b | same |
| Inference latency (single image, CPU) | mean 16.796 ms / p50 14.724 ms / p95 28.718 ms | `session.run` only, Apple M4 CPU, batch 1 | same |
| Images below 0.5 confidence | 318 (4.3%) | val | same |
| ORT PTQ INT8 vs fp32 agreement (200 val images) | 0.965 | per_channel + MinMax, not a collapse | `evaluation/runs/2026-09-06-m1c-int8-diag-quick` |

**Why the baseline changed.** MobileNetV3-Small (m1b) scored a fraction of a
point higher on this same split (val top-1 0.8792 vs 0.8877 for Lite0 — Lite0
is actually **+0.85pp better**, not worse) but its INT8-quantised graph
collapsed on every edge chain tried: Hailo emulator top-1 0.15, RK3576
agreement 0.10, RK3588 agreement 0.22, all against ~0.98 fp16 agreement on the
same chains (`2026-09-06-m1b-hef`, `2026-09-06-rk3576-cat`,
`2026-09-06-rk3588-radxa`). ORT PTQ reproduced the same collapse, which ruled
out a compiler-specific bug. EfficientNet-Lite0 (no Squeeze-Excite branch, no
hard-swish) does not collapse under the same INT8 pipelines — see the Hailo-8
and RK3588 sections below. The cost is a CPU-only one: mean inference time
rose from 1.886 ms to 16.796 ms (**about 9× slower on CPU**), because Lite0
(13.5 MB ONNX) has more FLOPs than MobileNetV3-Small (6.1 MB). On the edge
NPUs actually tested (Hailo-8 emulator, RK3588), Lite0's latency is close to
or faster than MobileNetV3-Small's — the CPU-only 9× penalty does not carry
over to the NPU numbers below.

**Report both top-1 numbers together.** The four-way figure (0.9500) is much
higher than the material figure (0.8877) because glass↔metal↔plastic confusion
is absorbed — all three map to 可回收物. Quoting only the four-way number
overstates what the model knows about materials.

### MobileNetV3-Small (m1b) — superseded, kept as the INT8-collapse contrast

Same split, same images, same CPU. This model is no longer the shipped
baseline; it stays on this page because its INT8 failure is the reason the
baseline changed, and because its fp16 numbers remain a valid contrast.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Material top-1 (8 classes) | 0.8792 | val, 7417 images; ONNX `51c7c0ed…` | This project, `evaluation/runs/2026-09-06-m1b-cpu` |
| Material top-5 | 0.9854 | same | same |
| Chinese four-way top-1 | 0.9519 | same | same |
| macro-F1 (7 classes with samples) | 0.8292 | `textile` excluded | same |
| Material top-1, held-out test | 0.8807 | test, 7290 images | This project, `evaluation/runs/2026-09-05-w1-cpu` baseline column |
| Inference latency (single image, CPU) | mean 1.886 ms / p50 1.769 ms / p95 2.276 ms | `session.run` only, Apple M4 CPU, batch 1 | `evaluation/runs/2026-09-06-m1b-cpu` |
| Images below 0.5 confidence | 335 (4.5%) | val | same |
| **INT8 collapse — Hailo-8 emulator** | top-1 0.15, agreement 0.115 vs CPU/native (200 val images) | fp16 agreement on the same 200 images is 1.000 | `evaluation/runs/2026-09-06-m1b-hef` |
| **INT8 collapse — RK3576 (cat-remote, real hardware)** | agreement 0.10 vs CPU golden | fp16 agreement 0.98 on the same device | `evaluation/runs/2026-09-06-rk3576-cat` |
| **INT8 collapse — RK3588 (radxa, real hardware)** | agreement 0.22 vs CPU golden | fp16 agreement 0.98 on the same device | `evaluation/runs/2026-09-06-rk3588-radxa` |

**Root cause, not fully proven.** Excluding the SE branch numerically did not
fix the collapse, and ORT PTQ reproduced it independent of any vendor
compiler — this is whole-network degradation, not a localised op issue. A
concrete defect exists in the training recipe: `AdamW(model.parameters(),
weight_decay=1e-4)` applies weight decay to BatchNorm gamma/bias, and 4 of 34
`BatchNorm2d` layers in the m1b checkpoint have `running_var`/`|gamma|`
degraded to float32 denormal magnitude, at the same layers where the
INT8 accuracy cliff appears. EfficientNet-Lite0 has the same weight-decay
setting and the same kind of weight outliers (max `|w|` 35.70 vs m1b's 52.35,
only 32% lower) yet does **not** collapse — the drop in outlier magnitude is
too small to explain the swing from 0.115 to 0.89+ agreement on its own. The
more likely reading is that SE-gating and hard-swish are structurally more
INT8-sensitive, and the weight-decay defect is a background factor that
amplifies that sensitivity rather than causing it outright. No ablation (e.g.
retraining m1b with a no-decay parameter group) has been run to confirm
either reading.

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

### Hailo-8 — baseline compiled and INT8-verified on the DFC emulator, no Hailo-8 hardware

| Path | Status |
|---|---|
| Baseline EfficientNet-Lite0 (m1c) → HEF | **Compiled successfully, one attempt, no fix needed.** `hailo optimize` and `compiler` both exit 0 on the first try — Lite0 has no Squeeze-Excite branch, so it never hits the `avgpool` shift-range issue m1b needed a model-script fix for. On 200 val images (DFC 3.31.0 / HailoRT 4.21.0 emulator): INT8 vs CPU/native top-1 agreement **0.890**, accuracy vs ground truth **0.755** (native/CPU is 0.795 on the same images) — a 4-point drop, not a collapse. Cosine similarity to CPU: mean 0.948, min 0.441. **All of these numbers are from the x86 emulator on the compile host (wsl2-local); no Hailo-8 PCIe card was used.** `evaluation/runs/2026-09-06-m1c-hef` |
| Baseline MobileNetV3-Small (m1b) → HEF | Compiled, but INT8 collapses: emulator agreement 0.115, accuracy vs ground truth 0.150 (near the 1/7 random baseline). Superseded by Lite0 for this reason — see the contrast table above. `evaluation/runs/2026-09-06-m1b-hef` |
| SigLIP 2 vision tower → HEF | Unchanged by the m1c work. `hailo parser` passes end to end with no unsupported op. `hailo optimize` (INT8 PTQ, 256 calibration images, optimization_level=1) **fails** with `NegativeSlopeExponentNonFixable` at layer `ne_activation_mul_and_add78` — "Desired shift is 16.0, but op has only 8 data bits". No optimized HAR, no compiler run, no HEF. |

**What "0.89 agreement" does and does not support.** It supports: EfficientNet-Lite0
INT8-quantises without the pattern collapse MobileNetV3-Small showed on the
same compile pipeline and the same calibration set, and `hailo optimize`
needed no SE-branch workaround to get there. It does not support: that the HEF
classifies waste correctly on a real Hailo-8 — no Hailo-8 hardware exists in
this project's evaluation chain, so board-level latency, thermal behaviour and
accuracy are all unmeasured. The calibration set (256 images) is also below
the ~1024-image threshold the DFC documentation typically recommends, and was
reused unchanged from the m1b run rather than resampled for Lite0.

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

### RK3588 (Radxa ROCK 5T) — real hardware, baseline INT8 now usable

On-device measurement, real hardware — not an emulator. Converted on
wsl2-local with rknn-toolkit2 2.3.2, run on a Radxa ROCK 5T with librknnrt
**2.3.2** (the symlink names it 2.3.0; the in-library version is what
matters), 50 val images, `core_mask=AUTO`, per-channel quantisation.

| Model / precision | Latency p50 / p95 (mean) | Agreement with CPU golden | Accuracy vs ground truth | Conditions |
|---|---|---|---|---|
| **EfficientNet-Lite0 (m1c), fp16** | 7.906 ms / 8.129 ms (7.041 ms) | 1.00 | 0.78 | ONNX sha `e9f9e847…`, 50 val images |
| EfficientNet-Lite0 (m1c), int8 calib64+normal | 3.780 ms / 3.984 ms (3.807 ms) | 0.90 | 0.72 | 63-image calibration, `normal` algorithm |
| EfficientNet-Lite0 (m1c), int8 calib64+mmse | 3.785 ms / 3.981 ms (3.808 ms) | 0.98 | 0.78 | 63-image calibration, `mmse` algorithm |
| EfficientNet-Lite0 (m1c), int8 calib256+normal | 3.766 ms / 3.920 ms (3.500 ms) | 0.90 | 0.72 | 252-image calibration, `normal` algorithm |
| **EfficientNet-Lite0 (m1c), int8 calib256+mmse** — recommended | 3.803 ms / 4.003 ms (3.834 ms) | **1.00** | **0.78** | 252-image calibration, `mmse` algorithm; matches fp16 on both agreement and accuracy, **52% faster** |
| MobileNetV3-Small (m1b, superseded), fp16 | 4.44 ms / 6.32 ms | 0.98 | — | ONNX sha `aa181dd5…`, contrast only |
| MobileNetV3-Small (m1b, superseded), int8 | 4.70 ms / 11.04 ms | **0.22 — collapsed** | — | 64-image calibration, contrast only |

**Recommended config: `calib256+mmse`.** It matches fp16 exactly on both
agreement (1.00) and accuracy (0.78) while running 52% faster (int8 gets a
real NPU acceleration path on RK3588 that the collapsed m1b int8 graph never
reached — m1b's int8 was *slower* than its own fp16, 4.70 ms vs 4.44 ms,
evidence its execution never engaged the INT8 fast path). All four Lite0 INT8
variants land in a 0.90–1.00 agreement band; none collapse. `mmse` is 40–90×
slower to convert than the default `normal` algorithm (17.3 min vs 11.5 s at
256 calibration images) — a one-time conversion cost, not a runtime cost.
Root cause of the m1b collapse: see the contrast table above — PTQ produces
whole-network degradation on MobileNetV3-Small independent of the RK
compiler, with a training-recipe weight-decay defect on BatchNorm as a
suspected but unconfirmed contributing factor. `evaluation/runs/2026-09-06-m1c-rk3588-radxa`,
`evaluation/runs/2026-09-06-rk3588-radxa` (m1b contrast)

SigLIP 2 vision tower on the same device, unaffected by the m1c work:

| Model / precision | Latency p50 / p95 | Agreement with CPU golden | Conditions |
|---|---|---|---|
| SigLIP 2 vision tower, **fp16** | 169.4 ms / 170.5 ms | embedding cosine mean **0.999617**, min 0.998841 | ONNX sha `6f664af0…`, 191 MB .rknn |

Note the conditions on the m1b contrast row: that run used a MobileNetV3 ONNX
with sha256 `aa181dd5…`, which is not the m1b file (`51c7c0ed…`) every m1b
accuracy figure above refers to. That parity result is about the runtime, not
about accuracy, and the two should not be combined into an accuracy claim.

### RK3576 (EmbedFire LubanCat-3) — real hardware, m1b only, not retested with m1c

| Model / precision | Latency p50 / p95 | Agreement with CPU golden | Conditions |
|---|---|---|---|
| MobileNetV3-Small (m1b), **fp16** | 9.49 ms / 12.49 ms | top-1 **98%** (49/50) | `evaluation/runs/2026-09-06-rk3576-cat` |
| MobileNetV3-Small (m1b), **int8** | 4.62 ms / 6.68 ms | top-1 **10%** (5/50) — **unusable, worse than random** | 64-image calibration from train |
| SigLIP 2 vision tower, **fp16** | 152.51 ms / 176.59 ms | embedding cosine mean **0.99965**, min 0.99900 | same run |

**EfficientNet-Lite0 (m1c) has not been converted or run on RK3576.** Only the
m1b numbers above exist for this device; do not assume the RK3588 INT8 result
carries over — RK3576 and RK3588 are different NPU generations with different
INT8 behaviour on this same MobileNetV3-Small graph (10% vs 22% agreement),
so an untested claim either way would be a guess.

### Platform support

| Platform | Status |
|---|---|
| Jetson Orin (TensorRT) | Deployment package shipped, baseline swapped to EfficientNet-Lite0 ONNX; engine has never been built on any Jetson |
| Raspberry Pi 5 + Hailo-8 | Deployment package shipped; baseline HEF compiled and INT8-verified on the DFC emulator only (agreement 0.89) — **no Hailo-8 hardware has run it**. SigLIP2 tower still fails INT8 quantisation |
| RK3588 | **Inference parity verified on real hardware, fp16 and INT8 (baseline, m1c); no deployment package** — no compose file, no image, no preset. The conversion and the runtime work; the packaging does not exist |
| RK3576 | Inference parity verified on real hardware, fp16 and INT8 — **m1b (MobileNetV3-Small) only, not retested with the current m1c baseline**; no deployment package |
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
| Baseline ONNX (`efficientnet_lite0_waste8.onnx`, m1c, current) | 13,477,056 B |
| Baseline ONNX (`mobilenetv3s_waste8.onnx`, m1b, superseded) | 6,118,606 B |
| SigLIP 2 vision tower ONNX (`siglip2_vision_224.onnx`) | 371,695,898 B |
| Prototype banks + calibration report | ~155 KB total |

## Classifier selection: baseline vs open-vocabulary

Both tracks are real and both are shipped. The choice is not "old vs new".

**The baseline model changed after this comparison was run: it is now
EfficientNet-Lite0 (m1c), not MobileNetV3-Small (m1b).** The comparison below
was measured against the old baseline and its numbers are unchanged — Lite0
is marginally more accurate than MobileNetV3-Small on this split (val 0.8877
vs 0.8792) so the "baseline vs open-vocabulary" gap in accuracy does not
narrow, but the "baseline" column's exact figures (0.8792/0.8501 etc.) below
refer to MobileNetV3-Small, not to the model actually shipped today. The
40× latency gap is CPU-only and also predates the swap — MobileNetV3-Small's
CPU latency (1.57 ms p50) was the divisor; Lite0's own CPU p50 is 14.7 ms
(see the baseline table above), which narrows the multiple to roughly 4–5×
against Lite0. Neither track has been re-measured against SigLIP2 since the
baseline swap.

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

**The cost is 40× latency against the old baseline** (p50 66.93 ms vs 1.57 ms
on the same M4 CPU), **or roughly 4–5× against the current baseline**
(66.93 ms vs Lite0's own CPU p50 of ~14.7 ms). That is not an implementation
gap — ViT-B/16 at 224² is roughly 17.6 GFLOPs against MobileNetV3-Small's 0.06
(Lite0's FLOPs are higher than MobileNetV3-Small's but not measured
separately). **Open-vocabulary is not a real-time CPU option.** Its
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

**Camera + Raspberry Pi 5 (Hailo-8)** — prepares the board, validates the
three Hailo ABI gates, and downloads the EfficientNet-Lite0 HEF compiled and
INT8-verified against the DFC emulator (agreement 0.89). **No Hailo-8
hardware has run this HEF** — board-level accuracy and latency are unmeasured.
Choose it to get a real classifier running on real Hailo-8 silicon for the
first time; treat the first on-device result as the actual verification, not
this page's emulator number.

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
