## Preset: Jetson Single Box {#jetson_hub}

Everything on one Jetson Orin: the MQTT broker, the aggregation hub with its
alert workbench, and a detector doing person detection on the GPU through
TensorRT with video decode on NVDEC. No second machine is required — the hub
decodes no video and runs no inference, measured at 1.4% of one CPU core and
44.9 MB of memory while carrying two live streams.

Measured on an Orin NX 16GB, JetPack 6.1, TensorRT 10.3.0, at 1280x720:
in-pipeline inference p50 4.13 ms, full pipeline p50 7.24 ms, 8.5–12.5% of one
CPU core, decode confirmed on NVDEC.

The TensorRT engine is built on your device during deployment and takes about
five to six minutes (361 s measured). That happens once; a redeploy reuses the
engine already on disk.

## Step 1: Deploy the Security Stack {#deploy_edge_security_jetson_hub type=docker_deploy required=true config=devices/jetson_hub_stack.yaml}

Enter the machine's address and your camera's RTSP URL; the engine is built and
three containers are installed and started.

### Prerequisites

- A Jetson Orin on JetPack 6.x. This preset is Jetson-only: the detector loads a
  TensorRT engine and refuses to start on the CPU decoder, and the deploy step
  stops with an explanation on any other machine.
- TensorRT on the board — `libnvinfer.so.10`, the `tensorrt` Python package and
  `/usr/src/tensorrt/bin/trtexec`. All three ship with JetPack; the deploy step
  checks for each one by name.
- The nvidia container runtime registered with Docker. It is what bind-mounts
  libcuda, the L4T GStreamer plugins and `/dev/v4l2-nvdec` into the container.
  If it is missing: `sudo apt-get install -y nvidia-container-toolkit && sudo
  nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`.
- Docker with the compose plugin. The deploy step installs the plugin if only
  the standalone `docker-compose` is present.
- The camera's RTSP URL, H.264, tested in VLC first. A wrong path or wrong
  credentials is the most common failure and it looks identical to a broken
  deployment.
- Ports 8090 (workbench), 1883 (broker) and 8099 (camera preview) free.
- About 6 GB of free disk for the images, the engine and the alert database.

### What to check

- The engine build step ends with `Engine written:` and a sha256. It takes about
  five to six minutes — do not interrupt it.
- The final step prints the hub's `/api/health` response. `mqtt_connected`
  must be true.
- The last step prints `/debug/decode` from the detector. `"decode": "hw"` with
  `"decoder_factory": "nvv4l2decoder"` is the confirmation that NVDEC is really
  in the pipeline.
- The credential step prints the admin login from the hub if this is a first
  boot.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deploy stops at "This preset is Jetson-only" | The target is not a JetPack machine. Use the RK3588 preset, or a Jetson. |
| Deploy stops at "The nvidia container runtime is not registered" | Install `nvidia-container-toolkit`, run `nvidia-ctk runtime configure --runtime=docker`, restart Docker, and deploy again. |
| Engine build fails or produces nothing | Read the trtexec output above the failure. Out of disk is the usual cause — the build needs about 1.7 GB of RAM and leaves a 9 MB engine. |
| Detector logs `deserialize_cuda_engine returned None` | The engine on disk was built by a different TensorRT version or on another machine. Delete `models/yolov8n_fp16.orin.engine` and redeploy; the step rebuilds it. |
| Detector exits with a hardware-decode error | `/dev/v4l2-nvdec` did not reach the container. Check that `runtime: nvidia` took effect: `docker inspect edge_security-detector-1 --format '{{.HostConfig.Runtime}}'`. |
| Hub does not answer on 8090 | `docker compose logs hub`. A port already in use is the usual cause. |
| Detector container restarts in a loop | `docker compose logs detector`. An unreachable RTSP URL is the usual cause; test it in VLC from the same machine. |
| Workbench shows no device | The detector publishes its status every 30 s. Wait a cycle, then check that `mqtt_host` in `config/detector.yaml` is `mosquitto`. |
| Alerts fire twice for one person standing still | The detector is falling behind the stream, so the tracker retires the track and a new track id re-enters the zone. On this preset one 720p camera uses 7.24 ms of a 200 ms frame, so suspect the camera or the network before the detector. |

### Target {#jetson_hub_host type=remote device_name="reComputer J" config=devices/jetson_hub_stack.yaml default=true}

## Step 2: Open the Alert Workbench {#dashboard_edge_security_jetson_hub type=web_dashboard required=true config=devices/jetson_hub_dashboard.yaml}

Log in, draw one boundary, and walk across it to see the first alert.

### Deployment Complete

The broker, the hub and one detector are running on the machine you chose.

#### First login

1. The workbench opens at `http://<machine>:8090`.
2. Log in with `admin` / `admin`. The hub forces a password change on first
   login; the new password is stored hashed with bcrypt.
3. Open **Devices**. Your detector should be listed as online, with `decode`
   reported as `hw` — this preset decodes on NVDEC, and the detector refuses to
   start on the CPU decoder, so anything else means it is not running.

#### Draw your first rule

1. Open **Rules**. The editor loads a live frame pulled from the detector, so
   what you draw lands where you mean it.
2. Draw a polygon for a restricted zone, or a line for a crossing rule. A line
   rule can require a direction — `forward`, `backward`, or `any`.
3. A zone can also carry a dwell time; a person who stays inside longer than
   that raises a separate loitering alert on top of the entry alert.
4. Save, then walk into the area. The alert appears in **Workbench** within a
   second, with the snapshot the hub requested from the detector.

#### Working the alert list

Each alert can be acknowledged or marked a false positive, with an undo bar for
the last action, and batch mode for clearing a backlog. The filtered list
exports to CSV. The interface is available in English and Chinese.

#### What it publishes

| Topic | Contents |
|---|---|
| `sensecraft/security/<device_id>/detections/<stream_id>` | per-frame person boxes with track ids |
| `sensecraft/security/<device_id>/status` | retained online/offline plus the decoder actually in use |
| `sensecraft/security/<device_id>/events/<stream_id>` | the hub's verdicts, tagged `origin: hub` |

Point an NVR, a PLC gateway or your own alerting service at port 1883 and
subscribe to the events topic rather than polling the API.

#### Adding a second camera

One detector container handles one camera. A second camera means a second
detector — either another container on this machine with its own `device_id`,
`stream_id` and `preview_port`, or a separate board using the RK3588 preset.

On an Orin NX 16GB the multi-process route is measured to hold up to eight
streams: each additional detector process costs 208 MB of unified memory, and
eight 1080p streams at 15 fps is 120 inferences/s against a measured GPU ceiling
of 236, so about 51% GPU. Four processes each inferring at 5 fps showed no
interference (p50 4.02–4.07 ms, the same as one process alone). Two things in
that budget are extrapolated rather than measured and should be confirmed before
committing to eight cameras: the per-stream CPU cost at 1080p 15 fps, and
NVDEC's concurrent session capacity.

Two concurrent streams is the largest configuration measured end to end, hub and
rules included.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login page loads but the credential is rejected | Read the hub log for the generated password: `docker compose logs hub \| grep -i admin`. |
| Rule editor shows a grey canvas instead of a frame | The detector's preview URL is not reachable from your browser. Check that `preview_advertise_host` in `config/detector.yaml` is the machine's LAN address, not `127.0.0.1`. |
| Alerts have no snapshot thumbnail | The hub asks the detector for a snapshot when an alert fires; a snapshot over 200 KB is rejected. Check the detector log. |
| Nothing fires when you cross the line | Line rules need a direction change across the line between two consecutive frames of the same track. Confirm the person is being tracked — the Devices page shows the detection rate. |

## Preset: RK3588 Single Box {#rk3588}

Everything on one RK3588 board: the MQTT broker, the aggregation hub with its
alert workbench, and a detector doing person detection on the NPU with video
decode on the board's hardware decoder. No second machine is required — the hub
decodes no video and runs no inference, measured at 1.4% of one CPU core and
44.9 MB of memory while carrying two live streams.

Measured on this board with the int8 model at 1280x720: inference p50 41.9 ms
inside the live pipeline, NPU core 8% busy, 21% of one CPU core, decode
confirmed on hardware.

## Step 1: Deploy the Security Stack {#deploy_edge_security_rk3588 type=docker_deploy required=true config=devices/rk3588_detector.yaml}

Enter the board address and your camera URL; three containers are installed and
started on the board.

### Prerequisites

- The board's `rknpu2` runtime installed, so `/usr/lib/librknnrt.so` exists.
- `rknn_toolkit_lite2` importable by the board's `python3`. The deploy step
  copies it into the container and fails early if it cannot find it.
- The Rockchip hardware decoder present as `/dev/mpp_service`. The detector
  refuses to start on CPU decode rather than falling back silently.
- An H.264 camera stream. The hardware decode path is built for H.264.
- Ports 8090 (workbench), 1883 (broker) and 8099 (camera preview) free on the
  board.
- About 6 GB of free disk for the two images, the staged board libraries and
  the alert database.

### What to check

- The step prints the hub's `/api/health` response, and the admin credential
  from the hub log if this is a first boot.
- It then prints `/debug/decode` from the running detector: the element
  GStreamer actually instantiated. `"decode": "hw"` with
  `"decoder_factory": "mppvideodec"` is the result you want.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deploy stops at "rknnlite is not importable" | Install it on the board: `pip3 install rknn_toolkit_lite2`. It ships as a wheel and often lands in a venv the deploy step cannot see. |
| Detector exits complaining about the decoder | The MPP plugin was not staged. Check `gstmpp/` next to the compose file on the board; if it is empty, install `gstreamer1.0-rockchip1` and `gstreamer1.0-plugins-bad`. |
| Model fails to load with a version error | The version in the filename is not the version in the binary. Read the real one: `strings /usr/lib/librknnrt.so \| grep 'librknnrt version'`. The shipped model is built for 2.3.2. |
| `W Query dynamic range failed` on every start | Harmless. It is what a static-shape model prints on this runtime. |
| Detector runs but the hub never lists it | The broker is in the same stack, so `mqtt_host` in `config/detector.yaml` should read `mosquitto`. The detector publishes its status every 30 s — wait a cycle before concluding anything. |
| Hub does not answer on 8090 | `docker compose logs hub`. A port already in use on the board is the usual cause. |

### Target {#rk3588_board type=remote device_name="RK3588" config=devices/rk3588_detector.yaml default=true}

## Step 2: Open the Alert Workbench {#dashboard_edge_security_rk3588 type=web_dashboard required=true config=devices/rk3588_dashboard.yaml}

Open the workbench on the board itself and confirm hardware decode.

### Deployment Complete

The board is detecting people and judging rules on itself. The workbench is at
`http://<board>:8090`.

#### Quick verification

1. Log in with `admin` / `admin` and set a new password when prompted.
2. Open **Devices** in the workbench. The board appears under the detector name
   you chose.
3. Its decode column should read `hw`. A `hw` reading here is a claim the
   detector makes about its own live pipeline, read off the negotiated
   GStreamer caps rather than from the config file.
4. Open **Rules**, pick this device and stream, and draw a zone or a line. The
   backdrop is a real frame from this board.

#### About the model

The board ships the int8 model. Against fp16 on COCO person it loses 0.52
AP@.5:.95 overall and 0.61 on small targets, and in exchange inference drops
from 72.3 ms to 41.9 ms and NPU load from 26% to 8%. The end-to-end rule
assertions are unchanged between the two. int8's failure mode is extra
low-confidence boxes rather than missed people, so raise `conf_threshold`
before reaching for fp16.

The small-target result rests on COCO. Before deploying to a wide-angle
overhead site where people appear at 30 m, re-check accuracy on footage from
that site.

#### Next steps

- Repeat this preset for each additional board. Each one is self-contained and
  keeps its own alert list. Give every detector a distinct name; the topic is
  keyed on it.
- If you would rather have one alert list across several boards, deploy the
  Shared Hub preset on a separate always-on machine and change `mqtt_host` in
  each board's `config/detector.yaml` to that machine's address. That is an
  optional expansion, not a requirement.
- Two concurrent streams is the largest configuration measured on one hub.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Device page shows decode `sw` | The detector is configured to refuse CPU decode, so a `sw` row means `require_hw_decode` was turned off by hand. Turn it back on and find out why MPP is missing. |
| Duplicate alerts for one motionless person | The detector is falling behind and the tracker is issuing new track ids. Check the detection rate on the Devices page against the camera's frame rate. |
| Rule canvas is grey for this device | `preview_advertise_host` must be the board's LAN address so the hub can fetch a frame from port 8099. |

## Preset: Shared Hub (Optional Expansion) {#hub_only}

This is not the normal way to deploy this solution. The Jetson and RK3588
presets each run the broker, the hub and a detector on a single machine, and
neither needs anything installed here.

Use this preset only when detector boxes are already running and you want one
shared alert list across all of them. It puts the broker, the rule engine and
the alert workbench on an always-on machine with no detector of its own — the
hub judges rules from the JSON detectors send it, measured at 1.4% CPU and
44.9 MB of memory while carrying two live streams.

After deploying it, change `mqtt_host` in each detector's `config/detector.yaml`
from `mosquitto` to this machine's address and restart that detector.

## Step 1: Deploy the Hub {#deploy_edge_security_hub_only type=docker_deploy required=true config=devices/hub_stack.yaml}

Enter the machine's address; the broker and the hub are installed and started.

### Prerequisites

- An arm64 or x86_64 machine with Docker that stays powered on.
- Ports 8090 and 1883 free. The deploy step warns if either is already taken.
- About 3 GB of free disk. The alert database and the snapshot files grow with
  the alert volume.

### What to check

- The final step prints `/api/health`, and the admin credential from the hub
  log if this is a first boot.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Hub does not answer on 8090 | `docker compose logs hub`. A port conflict is the usual cause. |
| Detectors connect and drop repeatedly | Two hub processes sharing an MQTT client id disconnect each other in a loop. `GET /api/health` reports the id in use; run only one hub per broker. |
| Alerts stop after the first few | Check `handler_errors` in `/api/health`. A non-zero and rising count means messages are being dropped inside the hub rather than never arriving. |

### Target {#hub_host_machine type=remote device_name="Hub Host" config=devices/hub_stack.yaml default=true}

## Step 2: Open the Alert Workbench {#dashboard_edge_security_hub_only type=web_dashboard required=true config=devices/hub_dashboard.yaml}

Log in and change the password; the device list stays empty until a detector
connects.

### Deployment Complete

The aggregation layer is running and listening for detectors on port 1883.

#### First login

1. The workbench opens at `http://<machine>:8090`.
2. Log in with `admin` / `admin` and set a new password when prompted.
3. **Devices** is empty. That is the expected state until a detector is pointed
   at this machine.

#### Connecting a detector

On each detector box, edit `config/detector.yaml` next to its compose file, set
`mqtt_host` to this machine's address, and run `docker compose up -d detector`.
The broker still running on that box does no harm; nothing subscribes to it any
more. Any device that publishes the documented payloads joins the same way — the payload contract is what the hub consumes, not a particular product.
A detector that carries track ids has its rules judged here; a device that
judges its own rules publishes finished events instead and the hub records them
without re-judging.

#### What is stored here

The alert database, the snapshot files and the rule configuration all live in
the `data/` directory next to the compose file. Back up that directory, not the
container.

#### Reserved for later

reCamera and Hailo detection nodes are not built yet. The payload contract is
published, so adding one does not change anything on this machine.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Detector shows online then offline in a loop | Each detector needs its own name. Two detectors sharing one identity fight over the same retained status topic. |
| Alerts appear with no thumbnail | The hub requests a snapshot from the detector when an alert fires. If the detector cannot answer, the alert is still recorded without an image. |
| Clock differences between sites confuse the ordering | Dwell timers, cooldowns and ordering all use the hub's own clock. Device timestamps are shown for evidence only, so a detector with a wrong clock does not break the rules. |
