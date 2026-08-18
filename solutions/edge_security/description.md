## Relationship to "Industrial Security on Jetson"

This is the multi-platform rebuild of the existing `industrial_security_jetson`
solution: the same three rules (restricted zone, line crossing, loitering) and
the same browser dashboard, rewritten so the detection layer and the rule layer
talk over a published MQTT payload contract instead of living in one process.
That is what lets an RK3588 board run the whole thing today and lets other
detector hardware join later without touching the hub.

**One difference decides which one to use: this package has no TensorRT path.**
The Jetson preset here runs a CPU / ONNX detector and leaves the GPU idle.

- **Need GPU inference on a Jetson** — keep using **Industrial Security on
  Jetson**. It is the only one of the two with a TensorRT detector.
- **Deploying on RK3588**, or on any arm64 / x86_64 box where a CPU detector is
  fast enough, or **you want alerts on MQTT and several detectors under one
  alert list** — use this one. The other solution is Jetson-only.

A TensorRT detection layer is being added here. Once it lands, this solution
takes over from `industrial_security_jetson` and that one is retired.

## What This Solution Does

Cameras watch an area. Edge boxes find the people in the picture. One hub turns
that into three kinds of alert and puts them in a list someone can work
through:

- **Restricted zone** — a person enters a polygon you drew on the camera view.
- **Line crossing** — a person crosses a line. The rule can require a
  direction, so "entered the yard" and "left the yard" are separate alerts.
- **Loitering** — a person stays inside a zone longer than the dwell time you
  set, raised on top of the entry alert rather than instead of it.

The detection layer and the judging layer are separate processes talking over
MQTT. That is what makes this a site solution rather than a single-camera demo:
one hub carries several detectors, of different kinds, in different rooms, and
the operator sees one alert list.

## What the Operator Actually Sees

A browser workbench served by the hub, in English or Chinese:

- **Workbench** — the alert list with a snapshot per alert, filters by device,
  stream, rule and time, acknowledge / false-positive with an undo bar, batch
  mode for clearing a backlog, and CSV export of whatever is filtered.
- **Rules** — boundaries drawn directly on a live frame pulled from the
  detector, so a zone lands where it was meant to. Rule changes are versioned.
- **Devices** — which detectors are online, how fast each is producing
  detections, and whether each one is decoding on hardware or on the CPU.

Alerts also go back out on MQTT, so an NVR, a PLC gateway or an existing
alerting system can subscribe rather than poll.

## Measured, and Where

Every number below came off a bench, not a datasheet.

| | Result |
|---|---|
| Capture to alert, end to end | 208.7 ms p50, 392.1 ms p95 (CPU detector) |
| Line-crossing instant vs. ground truth | 0.009-0.25 s error, no wrong-direction alerts |
| Zone-entry instant vs. ground truth | 0.025-0.057 s error |
| Loitering dwell vs. ground truth | within 0.25 s |
| Hub cost while judging two live streams | 1.4% of one CPU, 44.9 MB RSS |
| RK3588 detector, int8, 1280x720 | 41.9 ms p50 inference in-pipeline, NPU 8%, 21% of one CPU core, hardware decode |
| CPU detector, aarch64, 1280x720 | 30-37 ms inference, 14.92 fps against a 15 fps source |
| int8 vs. fp16 accuracy, COCO person | -0.52 AP@.5:.95 overall, -0.61 on small targets |

The timing errors come from a 130 s video whose crossing and entry instants are
known frame by frame, replayed over RTSP into the live pipeline.

## What Is Verified and What Is Not

Verified on real hardware:

- The CPU / ONNX detector.
- The RK3588 detector, including that it is really decoding on the board's
  hardware decoder rather than having fallen back to the CPU.
- The hub — rules, cooldown, alert lifecycle, storage, the REST and WebSocket
  API.
- The browser workbench.
- The ground-truth assertions in the table above.

Not verified, and not claimed:

- **No TensorRT detection path exists.** The Jetson Single Box preset runs the
  CPU / ONNX detector; the GPU is idle. If you need GPU inference on a Jetson
  today, use `industrial_security_jetson` instead.
- **reCamera and Hailo detection nodes are not built.** The payload contract is
  published so they can be added without changing the hub, but nothing here
  runs on them.
- **Capacity beyond two concurrent streams is untested.** Two is the largest
  configuration measured.
- **Small-target accuracy rests on COCO.** The calibration footage contained
  almost no distant people, so a wide-angle overhead site at 30 m is outside
  what was measured. Re-check on footage from the site before committing to it.

## Hardware You Need

| Role | Requirement |
|---|---|
| Camera | Any fixed RTSP camera. H.264 is required for the RK3588 preset's hardware decode path. The camera must not move after the rules are drawn. |
| Detection node | RK3588 board with the `rknpu2` runtime and `rknn_toolkit_lite2` installed, or any arm64 / x86_64 machine with about 2.5 spare CPU cores per 720p stream. |
| Aggregation host | Not required. The broker and the hub run on the detection machine itself. Only the optional Shared Hub preset needs a separate always-on arm64 or x86_64 machine with Docker. |
| Network | Detectors reach the hub on port 1883. Operators reach the hub on 8090. The camera preview on 8099 must be reachable from the operator's browser, otherwise the rule editor has no backdrop. |

## Choosing a Preset

Both deployment presets are self-contained: broker, hub and detector on one
machine, and the workbench is served from that same machine when the deploy
finishes.

- **Jetson Single Box** — a Jetson watching one camera with the CPU / ONNX
  detector.
- **RK3588 Single Box** — an RK3588 board watching one camera, inference on the
  NPU and decode on the board's hardware decoder.
- **Shared Hub (Optional Expansion)** — not a deployment path on its own. Use it
  only after several detector boxes are running and you want one alert list
  across them; it installs the broker and hub on a separate always-on machine,
  and each detector's `mqtt_host` is then repointed at it.

## One Failure Mode Worth Knowing Before You Start

If a detector cannot keep up with its camera, the symptom is not "slow" — it is
**wrong alerts**. Frames arrive in clumps, the gap between published frames
exceeds the tracker's patience, the tracker issues a new id for the same
person, and that new id has never been in the zone, so the zone alert fires
again. It reads as a broken rule engine and it is not.

Two things prevent it: cap the detector's inference threads instead of letting
one detector claim the whole machine (measured: 900% CPU and 138 ms inference
uncapped, against 250% and 50 ms capped), and check the detection rate on the
Devices page before blaming a rule.
