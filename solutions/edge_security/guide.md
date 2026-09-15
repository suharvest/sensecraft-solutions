## Preset: Jetson Single Box {#jetson_hub}

One Jetson Orin runs everything: the MQTT broker, the alert workbench, and the person detector (TensorRT inference, NVDEC decode). No second machine is required.

- **Camera:** one H.264 RTSP camera. Test the URL in VLC first.
- **First deployment:** the TensorRT engine is built on the device, which takes about five to six minutes and happens once.

## Step 1: Deploy the Security Stack {#deploy_edge_security_jetson_hub type=docker_deploy required=true config=devices/jetson_hub_stack.yaml}

Enter the machine's address and the camera's RTSP URL; the engine is built and three containers are started.

### Prerequisites

- A Jetson Orin on JetPack 6.x, which ships TensorRT. The deploy step stops on any other machine.
- The nvidia container runtime registered with Docker. If it is missing: `sudo apt-get install -y nvidia-container-toolkit && sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`.
- Ports 8090 (workbench), 1883 (broker) and 8099 (camera preview) free.
- About 6 GB of free disk.

### What to check

- The engine build ends with `Engine written:`. Do not interrupt it.
- The deploy output shows `mqtt_connected` true and `"decode": "hw"`.
- On first boot the admin login is printed.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Deploy stops at "This preset is Jetson-only" | The target is not a JetPack machine. Use the RK3588 preset, or a Jetson. |
| Deploy stops at "The nvidia container runtime is not registered" | Install `nvidia-container-toolkit` as in the prerequisites, restart Docker, and deploy again. |
| Engine build fails | Read the trtexec output above the failure. Out of disk is the usual cause. |
| Detector logs `deserialize_cuda_engine returned None` | Delete `models/yolov8n_fp16.orin.engine` and redeploy; the engine is rebuilt. |
| Detector exits with a hardware-decode error | Confirm the nvidia container runtime is registered, then redeploy. |
| Hub does not answer on 8090 | `docker compose logs hub`. A port already in use is the usual cause. |
| Detector container restarts in a loop | `docker compose logs detector`. An unreachable RTSP URL is the usual cause; test it in VLC from the same machine. |
| Workbench shows no device | Wait 30 s, then check that `mqtt_host` in `config/detector.yaml` is `mosquitto`. |
| Alerts fire twice for one person standing still | Check the camera and the network for stalls first. |

### Target {#jetson_hub_host type=remote device_name="reComputer J30 / J40" config=devices/jetson_hub_stack.yaml default=true}

## Step 2: Open the Alert Workbench {#dashboard_edge_security_jetson_hub type=web_dashboard required=true config=devices/jetson_hub_dashboard.yaml}

Log in, draw one boundary, and walk across it to see the first alert.

### Deployment Complete

The broker, the hub and the detector are running on this machine.

#### First login

1. Open `http://<machine>:8090`.
2. Log in as `admin` with the random password the deploy step printed. If the output was truncated, run `docker exec <hub container> cat /data/initial-password.txt` on the machine; line 2 is the password. You must change it on first login.
3. Open **Devices**. The detector should be online with decode `hw`.

#### Draw your first rule

1. Open **Rules**. The editor uses a live frame from the detector as its backdrop.
2. Draw a polygon for a restricted zone, or a line for a crossing rule. A line rule can require a direction: `forward`, `backward` or `any`.
3. A zone can carry a dwell time; staying longer raises a separate loitering alert.
4. Save, then walk into the area. The alert appears in **Workbench** within a second, with a snapshot.

#### The video wall

**Workbench → Video wall.** Choose 1, 2, 4, 6 or 9 tiles, or Auto. Each tile shows the detection boxes plus that stream's zone and tripwire. Press `F` for fullscreen and `Esc` to exit. A tile whose device is offline or whose stream is reconnecting turns grey and shows the reason.

#### Tuning confidence without a restart

At the 1, 2 and 4 layouts each tile has a confidence slider. The change applies from the next frame and survives a restart. Lower is more sensitive with more false alarms; higher is more conservative. If the console says the result is unknown, reload the Devices page and read the value the detector reports.

#### Adding a camera from the browser

**Video wall → Add camera.** Pick the detector, paste the RTSP address and name it; when the button completes, the tile is live. After adding one, check the detector's CPU figure on the Devices page before adding the next. The trash icon on a tile removes a camera; its alerts are kept.

#### Working the alert list

Each alert can be acknowledged or marked a false positive, with undo, batch mode and CSV export. The interface is available in English and Chinese.

#### What it publishes

| Topic | Contents |
|---|---|
| `sensecraft/security/<device_id>/detections/<stream_id>` | per-frame person boxes with track ids |
| `sensecraft/security/<device_id>/status` | online status and decoder in use |
| `sensecraft/security/<device_id>/events/<stream_id>` | alert events judged by the hub |

In this preset port 1883 accepts local connections only. To let another machine subscribe, change the mosquitto port mapping in the compose file from `127.0.0.1:1883:1883` to `1883:1883`, add a `password_file` to `config/mosquitto.conf`, and set matching credentials in `config/detector.yaml`. Opening the port without a password lets any device on the network publish forged alerts.

#### Adding a second camera

Add it from the video wall, run another detector container on this machine with its own `device_id`, `stream_id` and `preview_port`, or deploy a separate board with the RK3588 preset.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Login rejects the password | Run `docker compose logs hub \| grep -i admin` to read the generated password. |
| Rule editor shows a grey canvas instead of a frame | Set `preview_advertise_host` in `config/detector.yaml` to the machine's LAN address, not `127.0.0.1`. |
| Alerts have no snapshot thumbnail | Check the detector log. |
| Nothing fires when you cross the line | On the Devices page, confirm the detection rate is normal and the person is detected continuously. |

## Preset: RK3588 Single Box {#rk3588}

One RK3588 board runs everything: the MQTT broker, the alert workbench, and the person detector (NPU inference, on-board hardware decode). No second machine is required.

- **Camera:** one H.264 RTSP camera.

## Step 1: Deploy the Security Stack {#deploy_edge_security_rk3588 type=docker_deploy required=true config=devices/rk3588_detector.yaml}

Enter the board address and your camera URL; three containers are started on the board.

### Prerequisites

- The `rknpu2` runtime installed (`/usr/lib/librknnrt.so` exists), and `rknn_toolkit_lite2` importable by the board's `python3`.
- The hardware decoder node `/dev/mpp_service` present; the detector does not run on CPU decode.
- Ports 8090 (workbench), 1883 (broker) and 8099 (camera preview) free.
- About 6 GB of free disk.

### What to check

- The deploy output shows the hub health response, and the admin login on first boot.
- Decode reads `"decode": "hw"`.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Deploy stops at "rknnlite is not importable" | Run `pip3 install rknn_toolkit_lite2` on the board, under the system `python3` rather than a venv. |
| Detector exits complaining about the decoder | Install `gstreamer1.0-rockchip1` and `gstreamer1.0-plugins-bad` on the board and redeploy. |
| Deploy succeeds but the detector is still an older build | `docker pull` the image on the board, then redeploy. |
| Model fails to load with a version error | Run `strings /usr/lib/librknnrt.so \| grep 'librknnrt version'` to read the actual version; the shipped model is built for 2.3.2. |
| `W Query dynamic range failed` on every start | No action needed. |
| Hub does not list the detector | Wait 30 s; confirm `mqtt_host` in `config/detector.yaml` is `mosquitto`. |
| Hub does not answer on 8090 | `docker compose logs hub`. A port already in use is the usual cause. |

### Target {#rk3588_board type=remote device_name="RK3588" config=devices/rk3588_detector.yaml default=true}

## Step 2: Open the Alert Workbench {#dashboard_edge_security_rk3588 type=web_dashboard required=true config=devices/rk3588_dashboard.yaml}

Open the workbench and confirm hardware decode.

### Deployment Complete

The workbench is at `http://<board>:8090`.

#### Quick verification

1. Log in as `admin` with the random password the deploy step printed (also in `/data/initial-password.txt` inside the hub container), and set a new password when prompted.
2. Open **Devices**. The board is listed with decode `hw`.
3. Open **Rules**, pick this device and stream, and draw a zone or a line.

#### About the model

The board uses the int8 model. If false alarms are frequent, raise `conf_threshold` first. For wide-angle overhead sites where people appear far away, verify detection on footage from that site first.

#### Next steps

- Repeat this preset for each additional board, with a distinct name for every detector.
- For one alert list across several boards, deploy the Shared Hub preset on an always-on machine and set `mqtt_host` in each board's `config/detector.yaml` to that machine's address.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Device page shows decode `sw` | Turn `require_hw_decode` on in `config/detector.yaml` and check MPP hardware decode. |
| Duplicate alerts for one motionless person | Compare the detection rate on the Devices page with the camera's frame rate. |
| Rule canvas is grey | Set `preview_advertise_host` to the board's LAN address. |

## Preset: Hailo Single Box {#hailo}

One board with a Hailo-8 runs everything: the MQTT broker, the alert workbench, and the person detector. No second machine is required.

- **Camera:** one RTSP camera.
- **Decode:** this board has no H.264 hardware decoder, so video is decoded on the CPU and the Devices page shows `decode: "sw"`. Watch CPU load when adding cameras.

## Step 1: Deploy the Security Stack {#deploy_edge_security_hailo type=docker_deploy required=true config=devices/hailo_detector.yaml}

Enter the board address and your camera URL; three containers are started on the board.

### Prerequisites

- The Hailo PCIe driver loaded (`/dev/hailo0` exists) and the matching `hailort` package installed (`/usr/lib/libhailort.so` exists).
- Nothing else holding the accelerator; the deploy step stops if it is in use.
- The HailoRT Python wheel (`hailort-*-cp311-*_aarch64.whl`) matching the driver version under your home directory, downloaded from the Hailo developer zone.
- Ports 8090 (workbench), 1883 (broker) and 8099 (camera preview) free.
- About 4 GB of free disk.

### What to check

- The deploy output shows the hub health response, and the admin login on first boot.
- The step confirms the detector preview works and the container is not restarting; otherwise the deployment fails.
- The Devices page shows the board online with `"decode": "sw"`.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Deploy stops at "/dev/hailo0 is already held by" | Stop the program using the accelerator (commonly another vision container) and redeploy. |
| Detector exits with `HAILO_OUT_OF_PHYSICAL_DEVICES(74)` | Same as above. |
| Deploy succeeds but the detector is still an older build | `docker pull` the image on the board, then redeploy. |
| Deploy stops at "No hailort cp311 wheel found" | Download the wheel matching your driver version and place it under your home directory. |
| Detector exits with 139 or 135 | Pull the latest image and redeploy. |
| Devices page shows `decode: "sw"` | Expected on this board. |
| Hub does not list the detector | Wait 30 s; confirm `mqtt_host` in `config/detector.yaml` is `mosquitto`. |
| Hub does not answer on 8090 | `docker compose logs hub`. A port already in use is the usual cause. |

### Target {#hailo_board type=remote device_name="Hailo Board" config=devices/hailo_detector.yaml default=true}

## Step 2: Open the Alert Workbench {#dashboard_edge_security_hailo type=web_dashboard required=true config=devices/hailo_dashboard.yaml}

Open the workbench and draw your first rule.

### Deployment Complete

The workbench is at `http://<board>:8090`.

#### First login

Log in as `admin` with the random password the deploy step printed; you must change it on first login. If the output was truncated, run `docker exec edge_security_hailo-hub-1 cat /data/initial-password.txt` on the board; line 2 is the password.

#### Draw your first rule

Open **Rules**, pick this board's camera, and draw on the live frame: a polygon is a restricted zone, a line is a tripwire whose arrow points forward. Rules survive a resolution change; redraw them if the camera moves.

#### The video wall

**Workbench → Video wall.** Choose 1, 2, 4, 6 or 9 tiles, or Auto. Each tile shows the detection boxes plus that stream's zone and tripwire. Press `F` for fullscreen and `Esc` to exit. A tile whose device is offline or whose stream is reconnecting turns grey and shows the reason.

#### Tuning confidence without a restart

At the 1, 2 and 4 layouts each tile has a confidence slider. The change applies from the next frame and survives a restart. Lower is more sensitive with more false alarms; higher is more conservative. If the console says the result is unknown, reload the Devices page and read the value the detector reports.

#### Adding a camera from the browser

**Video wall → Add camera.** Pick the detector, paste the RTSP address and name it; when the button completes, the tile is live. The trash icon on a tile removes a camera; its alerts are kept.

#### What it publishes

Detections go to `sensecraft/security/<device_id>/detections/<stream_id>`, alert events to `.../events/<stream_id>`, and online status to `.../status`. Box coordinates are normalized against the original frame.

#### Adding a second camera

Each stream adds CPU decode load. Add one, check the detector's CPU figure on the Devices page, and add the next only if there is room.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Live frame does not load in the rule editor | Set `preview_advertise_host` in `config/detector.yaml` to the board's LAN address rather than `127.0.0.1`. |
| Alerts arrive without snapshots | If the broker restarted, wait 30 s for the detector to reconnect. |

## Preset: Shared Hub (Optional Expansion) {#hub_only}

Use this only when several detector devices are already running and should share one alert list. The Jetson, RK3588 and Hailo presets each include a hub and do not need this preset.

This preset runs the broker and the alert workbench on an always-on machine, with no detector. After deploying, change `mqtt_host` in each detector's `config/detector.yaml` from `mosquitto` to this machine's address and restart the detector.

## Step 1: Deploy the Hub {#deploy_edge_security_hub_only type=docker_deploy required=true config=devices/hub_stack.yaml}

Enter this machine's address; the broker and the hub are started.

### Prerequisites

- An always-on arm64 or x86_64 machine with Docker.
- Ports 8090 and 1883 free.
- About 3 GB of free disk; alert data grows with alert volume.

### What to check

- The deploy output shows the hub health response, and the admin login on first boot.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Hub does not answer on 8090 | `docker compose logs hub`. A port conflict is the usual cause. |
| Detectors connect and drop repeatedly | Run only one hub per broker. |
| Alerts stop after the first few | Check `handler_errors` in `/api/health`; if it keeps rising, read the hub log. |

### Target {#hub_host_machine type=remote device_name="Hub Host" config=devices/hub_stack.yaml default=true}

### Target {#hub_local type=local config=devices/hub_stack.yaml}

Run the hub on this machine, the one running SenseCraft Solution. No SSH setup is needed. Detectors on other boards connect over MQTT.

## Step 2: Open the Alert Workbench {#dashboard_edge_security_hub_only type=web_dashboard required=true config=devices/hub_dashboard.yaml}

Log in and change the password; the device list stays empty until a detector
connects.

### Deployment Complete

The hub is running and waiting for detectors on port 1883.

#### First login

1. Open `http://<machine>:8090`.
2. Log in as `admin` with the random password the deploy step printed (also in `/data/initial-password.txt` inside the hub container), and set a new password when prompted.
3. **Devices** is empty until a detector connects.

#### Connecting a detector

On each detector device, edit `config/detector.yaml` next to its compose file, set `mqtt_host` to this machine's address, and run `docker compose up -d detector`.

#### What is stored here

The alert database, snapshots and rule configuration live in the `data/` directory next to the compose file. Back up that directory.

#### Reserved for later

Jetson, RK3588 and Hailo detectors can connect today; a reCamera detection node is not available yet.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Detector shows online then offline in a loop | Give each detector a distinct name. |
| Alerts appear with no thumbnail | The detector did not answer the snapshot request; the alert is still recorded. Check the detector log. |
| Device clocks differ between sites | No action needed; rule timing and ordering use the hub's clock. |
