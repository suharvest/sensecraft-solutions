> **Dataset license pending.** The bundled weights are trained on a repost of NEU-DET; retrain on your own images before external demos or commercial use.

## What it does

A fixed camera watches a steel strip or workpiece. The device checks every frame for six surface defect classes (crazing, inclusion, patches, pitted_surface, rolled-in_scale, scratches) and sends the OK/NG verdict to the line over a Modbus TCP coil and MQTT at the same time. Everything runs on the device; images never leave it.

## What you get

- **A verdict a PLC can use directly**: coil 0 is NG, coil 1 is OK; registers carry defect class, count and position.
- **One MQTT result per frame**: verdict, reasons and all detection boxes.
- **Local debug page**: live view with boxes, timing and counters, recent verdicts.
- **Several cameras per host**: 8 stable streams at 10 FPS.
- **Optional anomaly detection**: trained on defect-free images only, highlights defect regions the detector never learned.

## Where it fits

- Strip and coil surface inspection, with the verdict wired to a reject or marking station.
- Retrofitting PLC-driven lines through Modbus alone.
- Recording line data before a real deployment, for re-labelling and setting the threshold.

## Measured results

| Metric | Result |
|---|---|
| Frame captured to verdict on the coil | **P50 9.298 ms / P99 9.549 ms** (reComputer J40 series); **P50 10.56 ms** (reComputer J30 series) |
| Defect detection mAP50 | **0.7577** |
| Precision / recall at threshold 0.35 | **0.7652 / 0.6969** |
| Per-class mAP50 | scratches **0.9685**, pitted surface **0.9301**, crazing **0.3603** |
| Streams per host at 10 FPS | **8** |
| reComputer R2000 (Hailo-8) | **P50 11.61 ms / P99 16.63 ms**, mAP50 **0.7091** |

Test conditions: NEU6 validation set, 290 images, fed as a 640×640 / 10 FPS video stitched from validation images.

## Detector selection

| Model | Whole-frame misses (290 frames) | CPU latency | Hailo-8 |
|---|---|---|---|
| YOLOX-Tiny (default) | **7** | Baseline | Supported |
| D-FINE-S / RT-DETRv2-S | **0-1** | ~2-3× | Not supported |

Switch via "model.track" in "config/config.json".

## Unsupervised Anomaly Detection (Optional)

EfficientAD-S trains on defect-free reference images only and highlights regions that look unlike them. The result is a separate "anomaly_score" field and does not change the OK/NG verdict. Use it as a region heatmap, not a whole-frame switch; before enabling, collect OK samples with the real camera and recalibrate "anomaly.threshold".

## Output Interfaces

| Interface | Content |
|---|---|
| Modbus TCP 502, coils 0-1 | NG / OK verdict |
| Modbus TCP 502, HR 0-7 | Defect class, count, primary defect position, heartbeat |
| MQTT "<device-name>/inspection/<stream-id>/results" | Per-frame verdict, reasons and boxes |
| HTTP 8080 "/preview.mjpg", "/healthz", "/events", "/snapshot.jpg" | Live view, health counters, recent verdicts |

## Deployment Comparison

| | IP camera + reComputer J30 / J40 | IP camera + reComputer R2000 (Hailo-8) |
|---|---|---|
| Coil latency P50 | **9.298 ms** (J40) / **10.56 ms** (J30) | **11.61 ms** |
| mAP50 | **0.7577** | **0.7091** |
| Optional DETR detectors | Yes | No |
| Prerequisite | TensorRT engine built on device | Three Hailo version checks must pass |

## Usage Notes

- The threshold is a business decision: raising it from 0.35 to 0.6 moves precision 0.765→0.865 and whole-frame misses from 7 to 39.
- Every validation image has a defect; measure the false-alarm rate on your own line images.
- The deploy steps configure one camera; add more to the on-device "streams" list and restart the container.
- Multiple streams share one Modbus register bank and the latest verdict wins; per-stream results come from MQTT.
- The measured input was synthetic video; stress-test with your own video source before fixing a stream count.
- The bundled MQTT broker is anonymous and for debugging; use a broker with credentials in production.

## Licensing note

The runtime code and every model (YOLOX, D-FINE, RT-DETRv2, EfficientAD-S) are Apache-2.0, with no Ultralytics code or weights. **The license of the NEU-DET repost used for training is not confirmed**, so the bundled weights must not be used for external demos or commercial use; for commercial use, retrain on your own images and replace the weights.
