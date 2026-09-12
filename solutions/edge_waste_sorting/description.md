# Waste Sorting at the Bin

One trigger, one photo, and you get back what the item is made of and which of
China's four household-waste categories it belongs in — delivered as a single
MQTT message.

## What it does

One trigger — a button, an HTTP call, or motion in the frame — makes the device
take a picture, classify the item into one of eight material categories, look
up the China four-way category for that material, and publish an MQTT message
with the material, the four-way category, a top-3 with confidences, and a
reference to the stored image. Image bytes never leave the device; the payload
carries only a path or an object-store URI. An asynchronous callback receives
the four-way result at the same time, so a lid, a relay or an indicator light
can act on it.

## What you get

- **Two answers from one head.** The model predicts eight material classes —
  paper, cardboard, glass, metal, plastic, textile, organic, residual. The
  China four-way sort (recyclable / kitchen / hazardous / other) is a lookup
  table on top, not a second head, so a change in local rules means editing a
  table, not retraining.
- **Trigger-and-capture, not a video stream.** Button, HTTP or motion
  detection, with 800 ms debounce; triggers arriving while one is in flight are
  merged, not queued. A continuous mode exists too — rate-limited, and it only
  publishes after three consecutive frames agree on the top-1.
- **The contract is enforced, not just documented.** Every payload passes
  event-schema validation before publishing; failures are counted and dropped.
- **An optional open-vocabulary track.** A SigLIP 2 vision tower scores
  constant text prototypes; select it with `model.track: open_vocab` at deploy
  time. It adds classes without retraining, answers in Chinese or English from
  the same image embedding, and can score "this is not in my vocabulary". The
  cost is roughly 4-5× the latency.
- **An actuator interface that is not tied to pins.** The runtime calls back
  with a category; where that category goes is integration work, which is why
  the same build runs on boards with different headers.

## Where it fits

- Home and community drop-off points: photograph a single item at the moment of
  disposal and tell the resident which bin it goes in.
- Sorting stations: an operator presents items one by one and wants a second
  opinion plus an audit trail on MQTT.
- Bins with a motorised lid or per-category indicator lights, driven from the
  four-way result via the GPIO callback.

Out of scope: mechanical integration for conveyor sorting, and detecting litter
on the ground — this model assumes one item per image.

## How well it works

| What the drop-off point gets | Typical | Device |
|---|---|---|
| Item in frame to a sorting answer | **4.122 ms** per trigger | reComputer J40 series (J4012, Orin NX) |
| Four-way top-1 | **0.9500** | Same model, consistent across accelerators |
| Material top-1 (8 classes) | **0.8877** | Same as above |
| Material top-1 (1060-image subset), TensorRT vs CPU agreement | **top-1 0.8755, agreement 0.9991** | reComputer J40 / J30 series |

**Read the two top-1 figures together**: the four-way score is higher because
confusions among glass, metal and plastic are all absorbed into "recyclable" —
quoting only the four-way number overstates how well the model tells materials
apart. The Hailo-8 build scores 0.8889 material top-1 on the full 7417-image
validation set.

### Platform support

- **Jetson Orin (TensorRT)** — deployed and verified on the reComputer J40
  series (Orin NX).
- **reComputer R2000 (Hailo-8)** — a deployment package exists; the baseline
  HEF has run the full validation set on a real Hailo-8.
- **RK3588 / RK3576** — conversion and runtime proven on real boards, but no
  deployment package.

### What these numbers cover

- **Both datasets are photos of single items**, not real bins — wet, crushed,
  stacked, backlit or partly bagged waste is outside the evaluation, so
  real-world accuracy will be lower; re-test on images from your own site
  before going live.
- **`textile` has no training samples**, so the model never outputs it;
  **`hazardous` has no material class mapping to it**, so this package's model
  never emits it.
- **`organic` makes up ~48% of the data**, and the model pushes uncertain items
  into it.
- The four-way mapping is a table maintained by this project; municipal rules
  differ from city to city.

## Classifier selection: baseline vs open-vocabulary

Both tracks ship; choose with `model.track`.

**The baseline (EfficientNet-Lite0, closed set) is more accurate on this
taxonomy** (val 0.8877 vs 0.8501). **The open-vocabulary track (SigLIP 2) wins
on things a closed-set head structurally cannot do:**

- **Better calibration** — its confidence tracks the real hit rate more
  closely, which matters when a threshold decides whether a lid moves.
- **Open-set rejection** — it can score "this item is not in my vocabulary"
  (AUROC 0.7538).
- **Cross-lingual answers** — Chinese and English prompts agree on the four-way
  category at 0.9143 from the same visual embedding.
- **New classes without retraining** — a new class is a prompt edit plus a
  prototype rebuild, not a training run.

The cost: ~67 ms per image on CPU, 4-5× the baseline — real-time use needs an
NPU/GPU. Two deployment conclusions: take the hierarchical path (predict the
eight materials, then map to four) instead of predicting the four-way category
directly ("recyclable" is not a visual concept); and `residual` is a fallback
definition, not a visual concept — don't expect it to be "learned".

## Output Interfaces

| Interface | Where | Content |
|---|---|---|
| MQTT `waste/<stream-id>/results` | port 1883 | One JSON per classification: material class, China four-way category, confidence, top-3, trigger source, image reference, model name with ONNX sha256, taxonomy version |
| HTTP `/trigger` | port 8080 | POST to trigger one capture-and-classify |
| HTTP `/preview.mjpg`, `/healthz`, `/events` | port 8080 | Live view, counters with inference timing, recent results with their top-3 |
| GPIO callback | in-process | Asynchronous callback with the four-way result. Not bound to pins — that is integration work. |

Images never ride in the payload. `image_ref.kind` is one of `none` / `local` /
`object_store`; base64 image bytes in a payload are a contract violation and
are rejected before publishing.

## Deployment Comparison

**Camera + reComputer J30 / J40 (Orin)** — the only preset that ships with
model files, and the only one offering the open-vocabulary track. The TensorRT
engine is built on the device at deploy time (tied to the GPU architecture and
TensorRT version); the build measured 68 seconds, with 4.122 ms end-to-end per
trigger in the deployed container.

**Camera + reComputer R2000 series (Hailo-8)** — pass the three Hailo ABI
gates, then download the EfficientNet-Lite0 HEF. The shipped HEF has run the
full 7417-image validation set on a real Hailo-8: material top-1 0.8889,
four-way 0.9507, p50 3.166 ms. The deployment container itself was verified on
the same unit through `/healthz`, `/trigger` and the MQTT trigger path.

## Usage Notes

- **One item per image.** There is no detector. Two items in one frame yield a
  single answer, and which item it describes is undefined.
- **The camera and the drop zone are the whole input.** Framing that leaves the
  item too small in the picture hurts classification.
- **Continuous mode publishes only after three consecutive frames agree on the
  top-1**, and it is rate-limited. Trigger mode has no such smoothing — one
  shot, one answer.
- **The bundled MQTT broker allows anonymous connections (for debugging).**
  Point at a broker with credentials for a real install.
- **The GPIO callback is wired to nothing by default.** `actuator.enabled`
  defaults to false; enabling it without providing binding code changes
  nothing.

## Licensing note

The upstream code and the SigLIP 2 checkpoint
(`google/siglip2-base-patch16-224`) are Apache-2.0. Both training datasets
permit redistribution with attribution: TrashNet (MIT) and Garbage
Classification 3 — Material Identification / Roboflow Universe (CC BY 4.0).
The attribution strings for external materials are in
"gallery/ATTRIBUTION.md".
