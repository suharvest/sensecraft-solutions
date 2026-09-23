# Waste Sorting at the Bin

Photograph one item and get its material and China four-way waste category over MQTT.

## What it does

A button, an HTTP call or motion in the frame triggers a photo. The device classifies the item into one of 8 material classes and derives the China four-way category (recyclable / kitchen / hazardous / other). The result goes out over MQTT and can drive a lid, relay or indicator light. Images stay on the device.

## What you get

- **One trigger, one answer**: button, HTTP or motion trigger with 800 ms debounce.
- **Two-level result**: material class plus four-way category, with top-3 confidences.
- **Local rules by table edit**: the four-way category is a lookup, so rule changes need no retraining.
- **Optional open-vocabulary mode**: add classes without retraining, answer in Chinese or English, flag items outside the vocabulary.
- **Actuator callback**: the four-way result can drive a lid, relay or indicator light.
- **Local debug page**: live view, inference timing, recent results.

## Where it fits

- Home and community drop-off points: photograph a single item and show which bin it goes in.
- Sorting stations: an operator presents items one by one, with a record on MQTT.
- Bins with a motorised lid or per-category indicator lights.

Not for: conveyor sorting, or detecting litter on the ground.

## Measured results

| Metric | Result |
|---|---|
| Trigger to result | **4.122 ms** (reComputer J40 series, Orin NX) |
| Four-way top-1 | **0.9500** |
| Material top-1 (8 classes) | **0.8877** |
| reComputer R2000 (Hailo-8) material / four-way top-1 | **0.8889 / 0.9507**, p50 **3.166 ms** / p95 **3.249 ms** |
| reComputer R2000 (Hailo-8) vs fp32 host, same images | **0.12 pp** accuracy difference |
| reComputer R2000 (Hailo-8) p50→p95 spread | **0.08 ms**, vs **0.69 ms** on the other NPU preset (reComputer RK3588) at the same 3.2 ms median |
| reCamera (SG2002), 1060-image subset | material top-1 **0.8792**, four-way top-1 **0.9566**, p50 **24.3 ms**, peak resident memory **11.6 MB**; BF16, **+0.47 pp** vs fp32 host on the same images |
| reCamera Pro, 1060-image subset | material top-1 **0.8764**, four-way top-1 **0.9566**, p50 **5.8 ms** / p95 **6.0 ms**; INT8 is **2.9x** the speed of fp16 on this camera and **4.2x** the reCamera figure; INT8/fp16/host fp32 agree within **0.2 pp** |
| reComputer RK3588, full 7417-image validation set | material top-1 **0.8882**, p50 **3.2 ms** / p95 **3.9 ms**; fp16 gives the same top-1 at p50 **6.0 ms** (INT8 **1.9x** faster); both within **0.05 pp** of fp32 host |
| reComputer J30/J40 (TensorRT), 1060-image subset | material top-1 **0.8755**, **99.91%** agreement vs CPU (first measured on J40, reproduces bit-identically on J30) |
| reComputer R2000 (Hailo-8), inference steadiness | p50 **3.2 ms**, p95 only **0.08 ms** above the median (0.69 ms on RK3588) |
| reComputer R2000 (Hailo-8), full 7417-image validation set | material top-1 **0.8889**, four-way top-1 **0.9507**; INT8 within **0.12 pp** of fp32 on the host for the same images |

Test data is photos of single items (full 7417-image validation set on Hailo-8 and RK3588; a 1060-image subset on the two all-in-one cameras); wet, crushed, stacked or bagged waste is not included.

## Classifier selection: baseline vs open-vocabulary

| | Baseline (EfficientNet-Lite0) | Open-vocabulary (SigLIP 2) |
|---|---|---|
| Material top-1 | **0.8877** | **0.8501** |
| New classes without retraining | No | Yes |
| Out-of-vocabulary rejection AUROC | — | **0.7538** |
| Chinese/English four-way agreement | — | **0.9143** |
| Speed | Baseline | ~**67 ms** per image on CPU, 4-5× slower |

Select with `model.track` at deploy time.

## Output Interfaces

| Interface | Content |
|---|---|
| MQTT `waste/<stream-id>/results` | One message per classification: material, four-way category, top-3, image reference |
| HTTP `/trigger` | Trigger one capture-and-classify |
| HTTP `/preview.mjpg`, `/healthz`, `/events` | Live view, counters and timing, recent results |
| GPIO callback | Four-way result callback; wiring is integration work |

## Deployment Comparison

| | Camera + reComputer J30 / J40 | Camera + reComputer R2000 (Hailo-8) |
|---|---|---|
| Open-vocabulary mode | Yes | No |
| Measured | **4.122 ms** per trigger | Material top-1 **0.8889**, p50 **3.166 ms** |
| First deploy | TensorRT engine built on device, **68 seconds** measured | Three Hailo version checks must pass |

## Usage Notes

- One item per image: two items in one frame yield a single answer.
- The model never outputs textile or hazardous.
- Uncertain items lean toward organic (~48% of the training data).
- The four-way mapping may differ from your city's rules; check it and re-test on site images before going live.
- An item too small in the frame lowers accuracy.
- The bundled MQTT broker allows anonymous connections; use a broker with credentials in production.
- The actuator callback is off by default (`actuator.enabled: false`) and needs your own binding code.

## Licensing note

The code and the SigLIP 2 checkpoint (`google/siglip2-base-patch16-224`) are Apache-2.0. The training datasets TrashNet (MIT) and Garbage Classification 3 — Material Identification / Roboflow Universe (CC BY 4.0) allow redistribution with attribution; the attribution strings are in "gallery/ATTRIBUTION.md".
