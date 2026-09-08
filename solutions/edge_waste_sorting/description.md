# Waste Sorting at the Bin

Trigger a shot, get back what the item is made of and which of the four
Chinese municipal waste streams it belongs in, on MQTT, in one message.

**The baseline classifier is EfficientNet-Lite0 (m1c), not MobileNetV3-Small.**
The original baseline (MobileNetV3-Small, "m1b") collapsed under INT8
quantisation on all three edge chains tested (the Hailo compiler's simulator, RK3576, RK3588);
EfficientNet-Lite0 does not, and is now the shipped baseline. Most accuracy
figures below still come from onnxruntime on an Apple M4 CPU, but the Hailo-8
and RK3588 sections carry real INT8 numbers, both from hardware: RK3588 from an
RK3588 board, Hailo-8 from a bench unit with a Hailo-8 M.2 module — not
yet re-verified on a reComputer R2000 series chassis.
The reCamera section is the exception — those numbers were taken on the camera
itself.

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

An engineering benchmark on two public datasets — **not a compliance or
regulatory classification result**. The four-way mapping is a table this project
maintains, not an authority's certified ruling, and municipal definitions differ
between cities.

| What the drop-off point gets | Typical | Device |
|---|---|---|
| Item in frame to a bin answer | **4.122 ms** per trigger | reComputer J40 series (J4012, Orin NX) |
| Four-way top-1 | **0.9500** | Same model on every accelerator |
| Material top-1, 8 classes | **0.8877** | Same |

**Report both top-1 numbers together**: the four-way figure is higher than the
material figure because glass, metal and plastic confusion is absorbed — all
three map to the same recyclable bin — so quoting only the four-way number
overstates what the model knows about materials.

Accuracy is a model property and carries across accelerators: the Hailo-8 build
scores 0.8889 material top-1 on the full 7417-image validation set and the
RK3588 INT8 build agrees with the fp32 reference on 0.9893 of it.

### Platform support

| Platform | Status |
|---|---|
| Jetson Orin (TensorRT) | Deployed and engine-built on reComputer J40 series (Orin NX) |
| reComputer R2000 (Hailo-8) | Deployment package shipped; the baseline HEF has run the full validation set on a Hailo-8 |
| RK3588 | Inference parity measured on real hardware, fp16 and INT8; **no deployment package** — the conversion and the runtime work, the packaging does not exist |
| RK3576 | Inference parity measured on real hardware with the superseded backbone only; no deployment package |

### What these numbers cover

- **Both datasets are photographs of single items** — one on a plain background,
  one a detection set with objects off-centre and often occluded. Neither is a
  real bin: wet, crushed, stacked, backlit and partially bagged waste sit
  outside the evaluation, so **accuracy at a live drop-off point will be lower
  than these figures** and should be re-measured on your own site imagery.
- **`textile` has no samples in either dataset**, so the model never emits it,
  and every table reports `n/a` for that class rather than 0.
- **`hazardous` (有害垃圾) has no material class mapped to it**, so the model
  shipped in this package never emits it either.
- **`organic` dominates the data** at roughly 48% of both splits, and the
  confusion matrix shows the model pushing uncertain items toward it.
- The two datasets share source photographs; grouping by source batch, origin
  image and perceptual hash merged 430 near-duplicates, 183 of them across the
  two datasets, and groups move between splits as a unit.

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
CPU latency (1.57 ms p50) was the divisor; Lite0's own CPU p50 is 14.7 ms,
which narrows the multiple to roughly 4–5×
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
- **The `residual` category has a leave-one-out AUROC of 0.5795, near chance.**
  Remove "general waste" from the vocabulary and some material word always
  catches those items with high confidence. It is a fallback definition, not a
  visual concept.

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
more often right on the items that trip these gates, have not been checked on hardware
against a real service on Orin.** Treat the fallback stream as a second opinion
to log, not a correction to act on.

## Deployment Comparison

**Camera + reComputer J30 / J40 (Orin)** — the only preset with a model file. The
TensorRT engine is built on the device during deployment, because an engine is
tied to the exact GPU architecture and TensorRT version and cannot be shipped
prebuilt. It is also the only preset offering the open-vocabulary track: the
SigLIP 2 tower at 67 ms per image on CPU needs an accelerator, and the Orin is
the accelerator this package has. Measured on reComputer J40 series (Orin NX):
baseline engine build 68 s, deployed pipeline 4.122 ms / inference 3.533 ms
per trigger — see the Platform support table above for deployment status.

**Camera + reComputer R2000 series (Hailo-8)** — prepares the board, validates
the three Hailo ABI gates, and downloads the EfficientNet-Lite0 HEF. The
shipped HEF has run on Hailo-8 hardware over the full 7417-image val set
(material top-1 0.8889, Chinese four-way 0.9507, agreement vs fp32 CPU 0.9581,
p50 3.166 ms). A from-scratch deploy of the container itself was separately
verified on the same hardware: `/healthz`, `/trigger` and the MQTT output all
returned a real classification matching the golden label for that one image,
and a direct `infer_shard.py` run against a 1060-image subset of the same val
set — using the same HEF but not going through the deployed container's HTTP
or MQTT path — measured agreement 0.9425 and accuracy vs ground truth 0.8453
at p50 3.167 ms, consistent with the full-set figures above.
`evaluation/runs/2026-09-08-harvest-pi-acceptance`

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
