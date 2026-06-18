## Preset: Deploy to Jetson {#default}

Run AI-accelerated person intrusion detection on your reComputer Industrial (Jetson Orin), with multi-camera support, live video and configurable safety rules in a browser dashboard, and SQLite event persistence.

| Device | Purpose |
|--------|---------|
| reComputer Industrial (Jetson Orin NX / Nano) | Runs the AI detection pipeline with GPU acceleration |
| RTSP IP camera | Provides the live video feed (multiple cameras supported) |

**What you'll get:**
- Live annotated video stream (bounding boxes + zones + lines) in the browser — multi-camera adaptive grid layout
- Configurable restricted zones, fence lines, and dwell-time rules per camera
- Event log with SQLite persistence — survives restarts, filterable by date
- HTTP API for stats / events / live MJPEG (`/api/stats`, `/api/events`, `/api/stream`)
- HDMI fullscreen mode — press **F** key to toggle fullscreen display

**Requirements:** Jetson with JetPack 6.x · Docker + NVIDIA runtime · SSH access · Working RTSP camera URL

**Detection Models:** YOLO26n (default, NMS-free, ~268 QPS) · YOLOv8n · YOLOv5n — TensorRT FP16 accelerated

## Step 1: Initialize Camera {#init_camera type=manual required=false}

Set up your IP camera(s) and grab their RTSP URLs. Multi-camera support allows you to connect multiple cameras simultaneously.


1. Connect the IP camera(s) and the Jetson to the same network (or PoE switch)
2. Find the camera's IP — check your router's DHCP list, or use the camera vendor's discovery tool
3. Log into the camera's web UI, make sure RTSP streaming is enabled (it usually is by default)
4. Note down the RTSP URL(s) — you'll paste them in Step 2

> **Common RTSP URL formats:**
> - **Hikvision:** `rtsp://admin:password@<ip>:554/Streaming/Channels/101` (main) or `/102` (sub)
> - **Dahua:** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0` (main) or `&subtype=1` (sub)
> - **Generic ONVIF:** Use the vendor's ONVIF tool to discover the stream URL

**Tip:** Test the URL in VLC first (**Media → Open Network Stream → paste URL**). If VLC can't play it, the deployment won't work either.

**Multi-camera tip:** You can add or remove cameras dynamically from the web dashboard after deployment.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot reach camera web UI | `ping <camera-ip>`. Verify the camera and your computer are on the same subnet |
| RTSP stream fails in VLC | Re-check username/password. Some cameras need RTSP enabled in settings explicitly |
| Don't know the RTSP path | Try the vendor defaults above, or look it up in the camera's user manual |
| Stream stutters or freezes in VLC | Switch to the sub-stream URL (lower resolution / bitrate) — main streams may exceed your network capacity |

## Step 2: Deploy Industrial Security Service {#deploy type=docker_deploy required=true config=devices/deploy.yaml}

Deploy the detection service to your Jetson. The deployer pulls the prebuilt image, writes your RTSP URL into the config, and starts the container.

### Target {#deploy_local type=local config=devices/deploy.yaml default=true}

Deploy on this machine directly (only works when SenseCraft Solution app is running on the Jetson itself).

### Wiring

1. Confirm Docker + NVIDIA runtime are installed on this Jetson
2. Paste the **RTSP URL** from Step 1
3. Click **Deploy**

> **Note:** First start takes 1-2 minutes to compile a Jetson GPU-optimized detection engine. The compiled engine is cached, subsequent restarts are instant.

### Deployment Complete

The dashboard is at **http://localhost:8080**. You should see:
- Live annotated video on the main panel
- A yellow restricted zone and a magenta fence line drawn on the frame (defaults — edit them in the browser)
- Stats (FPS, detection count) updating in real time

Quick API check:

```bash
curl http://localhost:8080/api/stats
# Expected: JSON with current FPS, detection count, recent events

curl http://localhost:8080/api/events
# Expected: JSON list of triggered events (empty on first deploy)
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker pull is slow | Image is ~3-5 GB. In China, configure a Docker registry mirror first |
| Detection engine build fails on first start | Confirm JetPack 6.x is installed and `/usr/src/tensorrt` exists. Check `docker logs industrial-security-demo` for details |
| RTSP cannot be opened | Run `ffprobe rtsp://...` from the Jetson to test. Verify the camera and Jetson are on the same network |
| Container keeps restarting | `docker logs industrial-security-demo` — most often the RTSP URL is wrong or the camera is unreachable |
| Dashboard shows blank video | Open browser DevTools → Console / Network. The MJPEG stream is at `/api/stream` — make sure it loads |
| `nvidia-smi` style errors / GPU not found | NVIDIA Container Runtime not installed. Run `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |

### Target {#deploy_remote type=remote config=devices/deploy.yaml}

Deploy to a remote Jetson over SSH.

### Wiring


1. Make sure the Jetson is on the network and reachable via SSH
2. Enter the Jetson IP, SSH username, and password
   - reComputer Industrial defaults: user `nvidia` / password `nvidia` (factory) — change if you've already updated
3. Paste the **RTSP URL** from Step 1
4. Click **Deploy** — the system will pull the image and start the service

> **Note:** First start takes 1-2 minutes to compile a Jetson GPU-optimized detection engine. The compiled engine is cached, subsequent restarts are instant.

### Deployment Complete

The dashboard is at **http://\<jetson-ip\>:8080**. You should see:
- Live annotated video on the main panel
- A yellow restricted zone and a magenta fence line drawn on the frame (defaults — edit them in the browser)
- Stats (FPS, detection count) updating in real time

Quick API check:

```bash
curl http://<jetson-ip>:8080/api/stats
# Expected: JSON with current FPS, detection count, recent events

curl http://<jetson-ip>:8080/api/events
# Expected: JSON list of triggered events (empty on first deploy)
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Try `ssh user@ip` from your computer first. Check IP, username, password |
| Docker pull is slow | Image is ~3-5 GB. In China, configure a Docker registry mirror first |
| Detection engine build fails on first start | Confirm JetPack 6.x is installed and `/usr/src/tensorrt` exists. Check `docker logs industrial-security-demo` for details |
| RTSP cannot be opened | Run `ffprobe rtsp://...` from the Jetson to test. Verify the camera and Jetson are on the same network |
| Container keeps restarting | `docker logs industrial-security-demo` — most often the RTSP URL is wrong or the camera is unreachable |
| Dashboard shows blank video | Open browser DevTools → Console / Network. The MJPEG stream is at `/api/stream` — make sure it loads |
| `nvidia-smi` style errors / GPU not found | NVIDIA Container Runtime not installed. Run `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |

## Step 3: Configure Safety Rules {#dashboard type=manual required=true}

Once the dashboard is open (next step), tune the safety rules to fit your scene:

- **Redraw the restricted zone** by clicking points on the live frame
- **Move the fence line** to where you want intrusion alerts
- **Adjust the dwell-time threshold** (how long someone has to stand in the zone before it counts)
- **Tune the detection confidence** (lower = more sensitive, higher = fewer false positives)

Changes take effect immediately.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Dashboard not loading | Verify port 8080 is open on the Jetson firewall: `sudo ufw status` |
| Video frame is frozen | RTSP feed dropped — check camera, then `docker restart industrial-security-demo` |
| Events never trigger | Confidence threshold too high, or zone doesn't cover the actual person path. Lower confidence to 0.25 and re-test |
| Multiple cameras needed | Multi-camera support is built in — add cameras dynamically from the web dashboard's camera management panel |

## Step 4: Open Dashboard {#open_dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The Industrial Security dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |
### Deployment Complete

Congratulations! Your industrial security monitoring system is running on the edge.

#### Quick Verification

1. Walk into the restricted zone in front of the camera — within ~1 second a bounding box should turn red and an event should appear in the event log
2. Cross the fence line — a line-cross event should fire
3. Stand still in the zone past the dwell threshold — a dwell event should fire
4. Hit `http://<jetson-ip>:8080/api/events` in your browser — the events should be listed there

#### API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/api/stats` | GET | Realtime FPS, detection counts, last event |
| `/api/events` | GET | Event history (`?date=YYYYMMDD` to filter) |
| `/api/config` | GET / POST | Read or update zones / lines / detector thresholds |
| `/api/stream` | GET | Annotated MJPEG video stream |

#### Next Steps

- Hook the `/api/events` endpoint into your existing alarm / SCADA / WeChat-Work bot
- Pipe events to a central log aggregator (Loki / ELK) for multi-site monitoring
- Add multiple cameras via the web dashboard's camera management panel — each camera has independent zones and rules
- [Industrial Security Demo on GitHub](https://github.com/Zhang-zu-hao/Industrial-security-demo)
