## It Absorbed the Jetson-Only Package

There used to be a second, Jetson-only industrial security package. It was
merged into this one on 2026-09-07: same topic, different deployment routes, so
one design with several presets rather than two pages. Its capability lives in
the **Jetson Single Box** preset here.

The detection layer and the rule layer were rewritten to talk over a published
MQTT payload contract instead of living in one process. That is what lets an
RK3588 board or a Hailo board run the whole thing, and lets other detector
hardware join later without touching the hub.

**What the older package did, and where it is now**

| Capability it had | Where it lives here |
|---|---|
| TensorRT FP16 person detection on Jetson Orin | Jetson Single Box preset — YOLOv8n on TensorRT 10.3.0, measured 4.13 ms per inference on an Orin NX 16GB |
| GPU video decode (NVDEC) | Same preset, verified in-kernel — `require_hw_decode` is on, so a host without it fails the pre-checks rather than running slowly |
| Restricted zone, line crossing, dwell / loitering | All three, with direction on the line rule and loitering raised on top of the entry alert |
| Browser dashboard, rules drawn on the live frame | The workbench and the rules editor, drawn on a frame proxied from the detector |
| Event persistence across restarts | The hub's alert store, with a snapshot per alert and CSV export |
| Multiple cameras on one box | One detector container per camera, several detectors into one hub — and the detectors no longer have to be the same hardware |
| Orin NX 16GB and Orin Nano 8GB | Both, as `recomputer_j40` and `recomputer_j30` |

**What is gained**: alerts also leave over MQTT, so an NVR or PLC can subscribe
instead of polling, and the rule layer can sit on a different machine from the
detectors.

**What is not a like-for-like replacement.** The older package was one process
with a video-wall dashboard; this one is a detector layer plus a hub, and four
of its browser conveniences did not survive that split:

| What the older dashboard did | Here |
|---|---|
| Add a camera from the dashboard's camera-management panel, while running | **Replaced, and it costs more.** One detector container handles one camera; a second camera means a second container with its own `device_id`, `stream_id` and `preview_port`, or another board. There is no button for it |
| Adaptive grid showing every camera's annotated video on one page | **Gone.** The workbench is an alert list with a snapshot per alert, not a video wall |
| HDMI fullscreen mode, toggled with the F key | **Gone.** There is no wall-display mode |
| Tune the detection confidence from the dashboard | **Replaced by a config file.** `conf_threshold` in `config/detector.yaml`, applied on redeploy — not a live control in the browser |
| Continuous annotated video on the main panel | **Replaced.** A snapshot is stored per alert, and the rules editor draws on a still frame proxied from the detector |

If a control-room video wall is what the site actually wants, this package does
not give it back, and that is the one real regression in the merge.

**One number did not carry over.** The older package advertised YOLO26n at
"~268 QPS, ~3.7 ms" and "30+ FPS on Orin NX" without naming a bench or a clip.
Those figures were never reproduced here, so they are not in the table below.
Every row there names the board it was measured on.

### The old id and the gap it leaves

There is no migration path between the two packages: they never shared a data
store, so an existing install keeps working until it is redeployed.

The old id is **not** an alias for this one. `replaces:` in `solution.yaml` is
not a field the spec defines — it is absent from `spec/solution.schema.json` and
from every model in `packages/`, so it is silently dropped on load and resolves
nothing. It is kept only as a written record of where the package went. The id
is listed in `solutions/.deprecated.json`, which the manifest generator copies
into the manifest's `deprecated` array; that marks it retired, it does not
redirect it.

So anything still holding `industrial_security_jetson` — a bookmark, a link, a
pinned deployment reference — gets a 404 from the moment the directory is
deleted until whoever consumes the manifest is pointed at `edge_security`. That
window is real and nothing in this package closes it.

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

Every number below came off a bench, not a datasheet, and every row names the
board it was measured on. Both detectors ran the same 1280x720 H.264 clip and
the same assertions.

### Detector

| | **Jetson Orin NX 16GB** | **RK3588 (Radxa Rock 5T)** |
|---|---|---|
| Accelerator | GPU, TensorRT 10.3.0, FP16 | NPU, RKNN 2.3.2, int8 |
| Inference, in-pipeline p50 | **4.13 ms** | 41.9 ms (int8) / 72.3 ms (fp16) |
| Full pipeline p50 (capture → published) | **7.24 ms** | 44.3 ms (int8) |
| Detector CPU cost | 8.5–12.5% of one core | 21% of one core |
| Accelerator load at 5 fps | 3.6% duty cycle | NPU 8% (int8) / 26% (fp16) |
| Video decode | NVDEC, verified in-kernel | Rockchip MPP, verified in-kernel |
| Single-stream ceiling, flat out | 167 inferences/s | not measured |
| Engine / model build on device | 307–361 s, one-off | none (model ships prebuilt) |

The Jetson figures are from an Orin NX 16GB on JetPack 6.1 (L4T R36.4.3); the
RK3588 figures from a Radxa Rock 5T on kernel 6.1.84.

### End to end, against a ground-truth video

The timing errors come from a 130 s clip whose crossing and entry instants are
known frame by frame, replayed over RTSP into the live pipeline.

| | **Jetson Orin NX 16GB** | **RK3588 (Radxa Rock 5T)** |
|---|---|---|
| Capture to alert | 117.4 ms p50, 297.0 ms p95 | not measured separately |
| Line-crossing instant vs. truth | 0.109–0.268 s error | 0.085–0.248 s error |
| Direction correctness | 8/8, no wrong-direction alerts | 8/8, no wrong-direction alerts |
| Zone-entry instant vs. truth | 0.090 s error | 0.056–0.057 s error |
| Loitering dwell vs. truth | 0.090–0.290 s error | 0.080–0.233 s error |
| Snapshots | 8/8 real JPEG | 8/8 real JPEG |

### Hub

Measured **3.7% of one CPU core and 52.8 MB RSS** on the RK3588 board while that board also runs a detector.
No separate figure was taken on the Orin NX. That is why every
preset puts the hub on the detection machine instead of asking for a second one.

### Accuracy

**int8 vs. fp16 on RK3588, COCO person: −0.52 AP@.5:.95 overall, −0.61 on small
targets.** int8 is the default there because it is 42% faster in the pipeline
for that cost. The Jetson path runs FP16 and pays no quantization penalty.

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

Two inputs to that table are extrapolated rather than measured, and should be
confirmed on the target resolution before anyone sells an eight-stream box:

- **Per-stream CPU at 1080p 15 fps.** Scaling the measured 8.5–12.5% of one core
  at 720p 5 fps gives roughly 0.5–0.7 of a core per stream, ~4–5 of the 8 cores
  at eight streams. **Needs verifying.**
- **NVDEC session capacity for 8×1080p15 concurrent.** The Orin NX decoder is
  specified well above that in aggregate pixel rate, but everything here was
  measured with one stream. **Needs verifying.**

## What Is Verified and What Is Not

Verified on real hardware:

- The Jetson TensorRT detector, on an Orin NX 16GB, including that it is really
  decoding on NVDEC — `/dev/v4l2-nvdec` open in the container process, NVMM
  provenance in the negotiated pipeline caps — rather than having fallen back to
  the CPU.
- The RK3588 detector, including the same check against the board's hardware
  decoder.
- The Hailo-8 detector on a Raspberry Pi 5, including that its software decode
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

Not verified, and not claimed:

- **The reCamera detection node is not built.** The payload contract is
  published so it can be added without changing the hub, but nothing here runs
  on one. The Hailo node is built and verified; see the Hailo preset.
- **Capacity beyond two concurrent streams is untested end to end.** The
  multi-stream numbers above are GPU and memory measurements taken with worker
  processes, not eight cameras and eight sets of rules.
- **Small-target accuracy rests on COCO.** The calibration footage contained
  almost no distant people, so a wide-angle overhead site at 30 m is outside
  what was measured. Re-check on footage from the site before committing to it.

## Hardware You Need

| Role | Requirement |
|---|---|
| Camera | Any fixed RTSP camera. H.264 is required — the Jetson and RK3588 presets decode it in hardware, and the Hailo preset decodes it on the CPU because the Pi 5 has no H.264 decoder. The camera must not move after the rules are drawn. |
| Detection node | A Jetson Orin (Orin Nano 8GB or Orin NX 16GB) on JetPack 6.x with TensorRT and the nvidia container runtime, **or** an RK3588 board with the `rknpu2` runtime and `rknn_toolkit_lite2` installed, **or** a Raspberry Pi 5 with a Hailo-8 on the PCIe slot, its driver and matching HailoRT. |
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
  NPU and decode on the board's hardware decoder.
- **Hailo Single Box** — a Raspberry Pi 5 with a Hailo-8 watching one camera,
  inference on the accelerator. Decode runs on the CPU here, which is the
  primary path rather than a fallback: the board has no H.264 decoder, so the
  detector's CPU figure covers decode as well as inference.
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

Neither preset is close to that limit on one camera — the Jetson detector spends
7.24 ms on a 200 ms frame, the RK3588 one 44.3 ms — but it is what you will see
first if you point too many cameras at one box, or run something else heavy
beside it. Check the detection rate on the Devices page before blaming a rule.
