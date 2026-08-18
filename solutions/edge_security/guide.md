## Preset: Single Box {#jetson_hub}

Everything on one machine: the MQTT broker, the aggregation hub with its alert
workbench, and one CPU detector watching a single camera.

The detector here runs on ONNX Runtime on the CPU. There is no TensorRT
detection path in this project yet, so the Jetson GPU is not used — the board
is serving as a quiet arm64 machine with enough cores. Budget about 2.5 cores
for one 720p camera at 15 fps.

## Step 1: Deploy the Security Stack {#deploy_edge_security_jetson_hub type=docker_deploy required=true config=devices/jetson_hub_stack.yaml}

Enter the machine's address and your camera's RTSP URL; three containers are
installed and started.

### Prerequisites

- Docker with the compose plugin on the target machine. The deploy step
  installs the plugin if only the standalone `docker-compose` is present.
- The camera's RTSP URL, tested in VLC first. A wrong path or wrong credentials
  is the most common failure and it looks identical to a broken deployment.
- Ports 8090 (workbench), 1883 (broker) and 8099 (camera preview) free.
- About 5 GB of free disk for the images and the alert database.

### What to check

- The final step prints the hub's `/api/health` response. `mqtt_connected`
  must be true.
- The same step prints the admin credential from the hub log if this is a first
  boot.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Hub does not answer on 8090 | `docker compose logs hub`. A port already in use is the usual cause. |
| Detector container restarts in a loop | `docker compose logs detector`. An unreachable RTSP URL is the usual cause; test it in VLC from the same machine. |
| Workbench shows no device | The detector publishes its status every 30 s. Wait a cycle, then check that `mqtt_host` in `config/detector.yaml` is `mosquitto`. |
| Alerts fire twice for one person standing still | The detector is falling behind the stream, so the tracker retires the track and a new track id re-enters the zone. Raise the inference thread count, or drop the camera to a lower resolution. |

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
   reported as `sw` — this preset decodes on the CPU, so `sw` is correct here.

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
or a separate board using the RK3588 preset. Two concurrent streams is the
largest configuration measured; treat anything beyond that as untested.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login page loads but the credential is rejected | Read the hub log for the generated password: `docker compose logs hub \| grep -i admin`. |
| Rule editor shows a grey canvas instead of a frame | The detector's preview URL is not reachable from your browser. Check that `preview_advertise_host` in `config/detector.yaml` is the machine's LAN address, not `127.0.0.1`. |
| Alerts have no snapshot thumbnail | The hub asks the detector for a snapshot when an alert fires; a snapshot over 200 KB is rejected. Check the detector log. |
| Nothing fires when you cross the line | Line rules need a direction change across the line between two consecutive frames of the same track. Confirm the person is being tracked — the Devices page shows the detection rate. |

## Preset: RK3588 Detector {#rk3588}

A detection node on an RK3588 board: person detection on the NPU, video decode
on the board's hardware decoder. It publishes into a hub that runs elsewhere,
so deploy the Hub Only preset first if you do not already have one.

Measured on this board with the int8 model at 1280x720: inference p50 41.9 ms
inside the live pipeline, NPU core 8% busy, 21% of one CPU core, decode
confirmed on hardware.

## Step 1: Deploy the Detector {#deploy_edge_security_rk3588 type=docker_deploy required=true config=devices/rk3588_detector.yaml}

Enter the board address, your camera URL and the address of the hub the results
should go to.

### Prerequisites

- The board's `rknpu2` runtime installed, so `/usr/lib/librknnrt.so` exists.
- `rknn_toolkit_lite2` importable by the board's `python3`. The deploy step
  copies it into the container and fails early if it cannot find it.
- The Rockchip hardware decoder present as `/dev/mpp_service`. The detector
  refuses to start on CPU decode rather than falling back silently.
- An H.264 camera stream. The hardware decode path is built for H.264.
- A hub already reachable on port 1883.

### What to check

- The final step prints `/debug/decode` from the running detector: the element
  GStreamer actually instantiated. `"decode": "hw"` with
  `"decoder_factory": "mppvideodec"` is the result you want.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deploy stops at "rknnlite is not importable" | Install it on the board: `pip3 install rknn_toolkit_lite2`. It ships as a wheel and often lands in a venv the deploy step cannot see. |
| Detector exits complaining about the decoder | The MPP plugin was not staged. Check `gstmpp/` next to the compose file on the board; if it is empty, install `gstreamer1.0-rockchip1` and `gstreamer1.0-plugins-bad`. |
| Model fails to load with a version error | The version in the filename is not the version in the binary. Read the real one: `strings /usr/lib/librknnrt.so \| grep 'librknnrt version'`. The shipped model is built for 2.3.2. |
| `W Query dynamic range failed` on every start | Harmless. It is what a static-shape model prints on this runtime. |
| Detector runs but the hub never lists it | `mqtt_host` in `config/detector.yaml` must be an address the board can reach, and port 1883 must be open on the hub machine. |

### Target {#rk3588_board type=remote device_name="RK3588" config=devices/rk3588_detector.yaml default=true}

## Step 2: Check It in the Workbench {#dashboard_edge_security_rk3588 type=web_dashboard required=true config=devices/rk3588_dashboard.yaml}

Open the hub and confirm the new board appears as online with hardware decode.

### Deployment Complete

The board is detecting people and publishing into your hub.

#### Quick verification

1. Open **Devices** in the workbench. The board appears under the detector name
   you chose.
2. Its decode column should read `hw`. A `hw` reading here is a claim the
   detector makes about its own live pipeline, read off the negotiated
   GStreamer caps rather than from the config file.
3. Open **Rules**, pick this device and stream, and draw a zone or a line. The
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

- Repeat this preset for each additional board. Give every detector a distinct
  name; the topic is keyed on it.
- Two concurrent streams is the largest configuration measured on one hub.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Device page shows decode `sw` | The detector is configured to refuse CPU decode, so a `sw` row means `require_hw_decode` was turned off by hand. Turn it back on and find out why MPP is missing. |
| Duplicate alerts for one motionless person | The detector is falling behind and the tracker is issuing new track ids. Check the detection rate on the Devices page against the camera's frame rate. |
| Rule canvas is grey for this device | `preview_advertise_host` must be the board's LAN address so the hub can fetch a frame from port 8099. |

## Preset: Hub Only {#hub_only}

The broker, the rule engine and the alert workbench on one always-on machine.
No video is decoded here and no inference runs here — the hub judges rules from
the JSON detectors send it, measured at 1.4% CPU and 44.9 MB of memory while
carrying two live streams.

Deploy this first when you have more than one site, then point each detector at
it.

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

Deploy the RK3588 Detector preset on a board and give it this machine's address
as the hub. Any device that publishes the documented payloads joins the same
way — the payload contract is what the hub consumes, not a particular product.
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
