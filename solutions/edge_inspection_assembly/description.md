> ⚠️ **The bundled model is trained on DeepPCB (a bare-board copper-defect dataset), not assembly missing-part data.** For a real assembly station, retrain on your own data (real PCBA plus caliper measurements).

## What it does

A camera watches one inspection station and checks every frame for defects, missing parts and dimensions out of tolerance; any failure makes the frame NG. The verdict goes to the PLC over Modbus TCP and to the MES or historian over MQTT at the same time.

## What you get

- **Missing-part check**: shows which slot is empty and any extra parts.
- **Dimension check**: converts to millimetres with a calibration reference and reports ok, undersize or oversize against nominal ± tolerance.
- **Ready for the PLC**: the coil gives OK/NG, registers give missing count, dimension and tolerance result; PLC programs that read the surface-inspection registers keep working.
- **One MQTT event per frame**: verdict reasons, boxes, missing-part and dimension details for traceability.
- **Per-camera configuration**: missing-part template and measurement area are set per camera; each of the four NG rules can be switched off.

## Where it fits

- PCBA and small-assembly stations where a fixed camera can see every part slot.
- Incoming or outgoing inspection against drawing tolerances.
- PLC lines already using an OK/NG coil that want a reason code.

## Measured results

| Metric | Result |
|---|---|
| Frame captured to verdict on the coil | **P50 10.92 ms / P99 11.18 ms** |
| Defect detection mAP50 | **0.9876** |
| Streams per host at 10 fps | **8** |
| Missing-part check | **6 / 6** matched on the template frame, **6 / 6** flagged after swapping boards |
| Dimension error vs calibration reference | **0.65%** worst case |
| Continuous run | **67 hours**, 0 frames dropped |

Test device: reComputer J30 series (J3011, Orin Nano 8GB); dataset: DeepPCB6 validation set, 205 images.

## Output Interfaces

| Interface | Content |
|---|---|
| MQTT "<device-name>/inspection/<stream-id>/results" | Per-frame verdict, reasons, boxes, missing-part and dimension details |
| Modbus TCP 502 | Coil 0 NG / coil 1 OK; HR 0–7 defect info, HR 8–11 missing count, extra count, millimetres ×100, tolerance code |
| HTTP 8080 "/healthz" "/events" "/preview.mjpg" | Health counters, recent events, live view with boxes and slot areas |

"HR 10 = 0" does not mean 0 mm was measured; read the tolerance code in HR 11 first.

## Semi-automatic Annotation Tool

"tools/annotation/" in the upstream repository runs on a PC: draw boxes, SAM 2.1 generates the slot areas, and the tool exports the missing-part template. See the optional annotation step in the deployment guide.

## Deployment Comparison

| | Camera + reComputer J30 / J40 | Camera + reComputer R2000 (Hailo-8) | reCamera Pro |
|---|---|---|---|
| mAP50 | **0.9876** | **0.9858** | **0.9870** |
| Latency P50 | End to end **10.92 ms** | End to end **11.89 ms** | Inference **30.9 ms** |
| Missing-part and dimension checks | Yes | Yes | No |
| Host required | Yes | Yes | No |
| First deploy | TensorRT engine built on device, ~5 minutes | Three Hailo version checks must pass | — |

## Usage Notes

- Template slot areas are picture coordinates; moving or refocusing the camera means rebuilding them. Fix the camera first.
- The bundled template is an example; replace it with your own product's slots before going live.
- Dimension measurement assumes a single plane: a tilted part, a reference at a different distance, or a low-contrast edge causes error or a failed measurement.
- Reading coil and registers in two requests can span two verdicts; read registers first and treat the coil as the trigger.
- Multiple streams share one register bank holding only the latest verdict; per-stream results come from MQTT.
- The bundled MQTT broker is local and anonymous; use a broker with credentials in production.

## Licensing note

Runtime code and the YOLOX detector are Apache-2.0, with no Ultralytics code or weights. The training data DeepPCB is MIT-licensed; attribution is in "gallery/ATTRIBUTION.md".
