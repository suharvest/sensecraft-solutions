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
| reComputer R2000 (Hailo-8) material / four-way top-1 | **0.8889 / 0.9507**, p50 **3.166 ms** |

Test data is photos of single items (full 7417-image validation set on Hailo-8); wet, crushed, stacked or bagged waste is not included.

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
