## What the Solution Does

Draw a line or a zone, and anyone crossing it raises an alert. Restricted-zone, line-crossing, and loitering alerts are judged entirely on the edge box itself. Operators draw rules, watch the video wall, and disposition alerts in a browser—video never leaves the site.

- **Restricted Zone Intrusion**: Triggers when a tracked person enters a polygon drawn on the camera view.
- **Line Crossing**: Triggers when a person crosses a tripwire line. The rule can enforce directional counting, so entering and exiting produce distinct alerts, and reverse movements remain silent.
- **Loitering / Dwell**: Triggers when a person remains inside a zone past a configurable threshold, escalating as an additional alert on top of intrusion.

The detection layer and the rule engine run as decoupled processes communicating over MQTT. One hub can aggregate multiple detectors across rooms and heterogeneous hardware into a single alert list.

## Core Value

- **Reuse Existing Cameras**: Accepts standard RTSP H.264 streams directly—no need to replace existing security cameras.
- **No Extra Server Required**: Detection, tracking, rule evaluation, event storage, and web console run on the same edge host.
- **Zero Video Upload**: Video processing is strictly local; only structured alert JSON and JPEG snapshots leave the box.
- **Full Operator Console**: Adaptive 1–9 tile video wall, fullscreen duty mode, live alert disposition, and CSV export.
- **Direct On-Frame Rule Authoring**: Draw polygons and tripwires directly over the live stream with immediate effect without restarting containers.

## Suitable Scenarios

Places where the boundary can be clearly framed, the camera is fixed, and crossings must be alerted immediately:

- **Perimeters and Restricted Areas**: Switchrooms, chemical stores, server-room doors. Draw a zone for immediate entry alerts.
- **Corridors and Gateways**: Lay a line across an aisle or doorway to monitor one-way passage without false alarms on return trips.
- **Dwell Anomaly Points**: Beside sensitive machinery or high-value shelving. Staying past the timeout raises a loitering alert.

**Usage Notes and Limitations**:
- Built for person detection; not suitable for vehicles, packages, or equipment tracking without model retuning.
- Cameras must be mounted rigidly; moving a camera invalidates geometric boundaries and requires redrawing rules.

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

## Measured Performance

Every number below came off a bench, not a datasheet. The timing errors come
from a 130 s 1280x720 H.264 clip whose crossing and entry instants are known
frame by frame, replayed over RTSP into the live pipeline at 5 fps.

| What the site gets | Typical | Device |
|---|---|---|
| Line crossing to alert | **0.109-0.268 s** | Jetson Orin NX 16GB |
| Entering a restricted zone to alert | **0.090 s** | Same |
| Loitering call against the truth instant | **0.090-0.290 s** | Same |
| Direction | **8/8 correct**, no wrong-direction alerts | Same |
| Capture to alert | **117.4 ms** p50 (297.0 ms p95) | Same |

Every alert stored a decodable JPEG from the scene, 8/8.
The reComputer RK3588 series lands in the same range on the same clip
(0.085-0.248 s on line crossing, 8/8 on direction, 8/8 snapshots), so **choose
hardware by stream count, not by timing accuracy**.

The Jetson figures are from an Orin NX 16GB on JetPack 6.1 (L4T R36.4.3); the
RK3588 figures are from a same-SoC development board on kernel 6.1.84, not
yet re-verified on a reComputer RK3588 series chassis.

**Accuracy.** int8 vs. fp16 on RK3588, COCO person: -0.52 AP@.5:.95 overall,
-0.61 on small targets. int8 is the default there because it is 42% faster in
the pipeline for that cost. The Jetson path runs FP16 and pays no quantization
penalty.

## How Many Cameras One Jetson Carries

The measurements that decide this were taken on an Orin NX 16GB.

- **GPU ceiling: 236 inferences/s** across all contexts. Worker processes flat
  out: 1 → 166.7/s, 2 → 231.2/s, 4 → 237.0/s, 8 → 235.8/s. Aggregate throughput
  is flat from two workers on, so the GPU is the shared resource and it
  saturates there.
- **208 MB of unified memory per additional detector process**, each holding its
  own engine, context and Python runtime. System used RAM went 3977 MB baseline
  → 4172 / 4394 / 4600 / 4822 MB at one to four processes.
- **No interference at realistic rates.** Four processes each inferring at 5 fps
  measured p50 4.02 / 4.07 / 4.04 / 4.02 ms — indistinguishable from one process
  running alone.

| Streams (1080p @ 15 fps) | What to do |
|---|---|
| **1 – 8** | Run one detector container per camera. No new code. Eight streams is 1.7 GB of the board's 15.6 GB and 120 inferences/s against the 236 ceiling — about 51% GPU, so per-frame latency stays near the unloaded figure instead of climbing into the queueing regime. |
| **8 – 16** | A dynamic-batch engine, once someone has measured it. Batching amortizes the 1.21 ms of per-inference enqueue overhead, but a batch cannot dispatch until the slowest stream delivers its frame, which adds up to 67 ms to every alert. |
| **16+, 4K, or tiled display** | DeepStream. Past 16 streams the CPU-side preprocessing does become the constraint, and NVMM zero-copy is the only way around it. DeepStream 7.x for JetPack 6.1 also wants 1.5–2 GB of disk and pins you to a JetPack/`pyds` version pair. |

Everything in the table above was measured with one stream at 720p 5 fps, where
one stream costs 8.5–12.5% of one core. Measure two things at your own target
resolution before committing to an eight-stream box: per-stream CPU at
1080p 15 fps, and NVDEC session capacity for 8×1080p15 concurrent.

## What Is Verified

Verified on real hardware:

- The Jetson TensorRT detector, on an Orin NX 16GB, including that it is really
  decoding on NVDEC — `/dev/v4l2-nvdec` open in the container process, NVMM
  provenance in the negotiated pipeline caps — rather than having fallen back to
  the CPU.
- The RK3588 detector, including the same check against the board's hardware
  decoder.
- The Hailo-8 detector on the Hailo-8 reference board (not the reComputer Industrial R20 series chassis), including that its software decode
  is the primary path rather than a fallback, and that it publishes alerts with
  decodable snapshots.
- All three presets deployed as containers, end to end, with the compose files
  and deploy steps shipped here.
- The hub — rules, cooldown, alert lifecycle, storage, the REST and WebSocket
  API.
- The browser workbench.
- The ground-truth assertions in the tables above.

**The broker accepts anonymous clients, and only the Shared Hub preset exposes
it.** Mosquitto ships with `allow_anonymous true` in every preset. In the three
single-box presets it is bound to loopback — the detector and the hub reach it
over the compose network, so nothing on the LAN can publish to it. The Shared
Hub preset is the exception by design: remote detectors have to reach 1883, so
that one listens on the network, and anything that can reach the port can
publish on the detection topics — including fabricated detections and verdicts,
which a security workbench will display as real alerts. Put that host on a
management or camera VLAN, and add a `password_file` to
`assets/hub/config/mosquitto.conf` with matching credentials in each detector's
config. The same applies if you republish a single-box broker on the LAN to
attach a second detector: change the port binding and add the password file,
not just the first. The workbench on 8090 is unaffected — it requires a login.

Scope of the numbers above:

- **The reCamera detection node is not built.** The payload contract is
  published so it can be added without changing the hub. The Hailo node is
  built and verified; see the Hailo preset.
- **The multi-stream numbers are GPU and memory measurements taken with worker
  processes**, not eight cameras and eight sets of rules. Run a site pilot at
  your own stream count before committing to it.
- **Small-target accuracy rests on COCO.** The calibration footage contained
  almost no distant people, so a wide-angle overhead site at 30 m is outside
  what was measured. Re-check on footage from the site before committing to it.

## Hardware You Need

| Role | Requirement |
|---|---|
| Camera | Any fixed RTSP camera. H.264 is required — the Jetson and RK3588 presets decode it in hardware, and the Hailo preset decodes it on the CPU because the Pi 5 has no H.264 decoder. The camera must not move after the rules are drawn. |
| Detection node | A Jetson Orin (Orin Nano 8GB or Orin NX 16GB) on JetPack 6.x with TensorRT and the nvidia container runtime, **or** an RK3588 board with the `rknpu2` runtime and `rknn_toolkit_lite2` installed, **or** a reComputer Industrial R20 series unit with a Hailo-8 on the PCIe slot, its driver and matching HailoRT. |
| Aggregation host | Not required. The broker and the hub run on the detection machine itself. Only the optional Shared Hub preset needs a separate always-on arm64 or x86_64 machine with Docker. |
| Disk | About 6 GB free on the detection machine for the Jetson and RK3588 presets — detector image, hub image, the TensorRT engine built there, and the alert database. The Hailo preset needs about 4 GB; it builds no engine. |
| Network | Detectors reach the hub on port 1883. Operators reach the hub on 8090. The camera preview on 8099 must be reachable from the operator's browser, otherwise the rule editor has no backdrop. **Only the Shared Hub preset exposes 1883 on the network**; the single-box presets bind it to loopback. See the broker note below. |

## Choosing a Preset

All three deployment presets are self-contained: broker, hub and detector on
one machine, and the workbench is served from that same machine when the
deploy finishes.

- **Jetson Single Box** — a Jetson Orin watching one camera, inference on the
  GPU through TensorRT and decode on NVDEC. The engine is built on the device
  during deployment, which adds about five minutes to the first install.
- **RK3588 Single Box** — an RK3588 board watching one camera, inference on the
  NPU and decode on the board's hardware decoder. On this board the hub itself
  costs **3.7% of one CPU core and 52.8 MB RSS** while it also runs the
  detector, so one board carries both.
- **Hailo Single Box** — a reComputer Industrial R20 series unit with a Hailo-8 watching one camera,
  inference on the accelerator. Measured at 1280x720: **7.7 ms per inference,
  9.5 ms for the full pipeline, 8.7-13.0% of one CPU core**. Decode runs on the CPU here, which is the
  primary path rather than a fallback: the board has no H.264 decoder, so the
  detector's CPU figure covers decode as well as inference.
- **Shared Hub (Optional Expansion)** — not a deployment path on its own. Use it
  only after several detector boxes are running and you want one alert list
  across them; it installs the broker and hub on a separate always-on machine,
  and each detector's `mqtt_host` is then repointed at it. The aggregation host
  itself needs no accelerator — verified on an RK3588 board carrying both
  detectors at **3.7% of one CPU core and 52.8 MB RSS**.

## One Failure Mode Worth Knowing Before You Start

If a detector cannot keep up with its camera, the symptom is not "slow" — it is
**wrong alerts**. Frames arrive in clumps, the gap between published frames
exceeds the tracker's patience, the tracker issues a new id for the same
person, and that new id has never been in the zone, so the zone alert fires
again. It reads as a broken rule engine and it is not.

Neither preset is close to that limit on one camera — the Jetson detector spends
7.24 ms on a 200 ms frame, the RK3588 one 44.3 ms — but it is what you will see
first if you point too many cameras at one box, or run something else heavy
beside it. Check the detection rate on the Devices page before blaming a rule.

> 📖 **Engineering Reference:** Full architecture internals, measured benchmarks, and failure modes are documented in the [Engineering Wiki · Edge Security Alerting](https://wiki.seeedstudio.com/solutions/edge-security/).
