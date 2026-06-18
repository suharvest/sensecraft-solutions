## Preset: NVIDIA Jetson {#jetson}

Real-time gun detection using Frigate NVR with TensorRT GPU acceleration on NVIDIA Jetson.

| Device | Purpose |
|--------|---------|
| NVIDIA Jetson (reComputer) | Edge AI with TensorRT GPU acceleration |
| IP Camera (optional) | RTSP video source for monitoring |

**What you'll get:**
- Real-time gun detection with bounding boxes and confidence scores
- Web dashboard for live monitoring and event review
- Automatic recording and snapshots when guns are detected
- MQTT integration for alerts and automation

**Requirements:** Docker + NVIDIA Container Toolkit on target device

## Step 1: Initialize Cameras {#init_cameras_jetson type=manual required=false}

Set up your IP cameras and obtain RTSP stream URLs.

### Wiring

1. Connect your IP camera to the same network as the deployment device
2. Find the camera's IP address (check your router's DHCP client list, or use the manufacturer's tool)
3. Access the camera's web management interface (usually `http://<camera-ip>`)
4. Enable RTSP streaming in the camera settings (usually enabled by default)
5. Note down the RTSP URL for your camera

> **Common RTSP URL formats:**
> - **Hikvision:** `rtsp://admin:password@<ip>:554/Streaming/Channels/101` (main stream) or `/102` (sub stream)
> - **Dahua:** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0` (main) or `&subtype=1` (sub)
> - **Generic ONVIF:** Use the camera's ONVIF discovery tool to find the stream URL

**Tip:** Use the sub stream (lower resolution) for detection to reduce CPU/GPU load, and the main stream for recording.

You can test your RTSP URL with VLC: **Media > Open Network Stream > paste the URL**.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot access camera web interface | Verify camera IP with `ping <camera-ip>`. Check if camera and computer are on the same subnet |
| RTSP stream not working | Verify RTSP is enabled in camera settings. Try with VLC first. Check username/password |
| Camera not found on network | Power cycle the camera. Check Ethernet cable connection. Try manufacturer's discovery tool (e.g., Hikvision SADP, Dahua ConfigTool) |

## Step 2: Deploy Frigate {#deploy_frigate_jetson type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy Frigate NVR with TensorRT-accelerated gun detection to your NVIDIA Jetson.

### Target {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

Deploy to a remote NVIDIA Jetson device via SSH.

### Wiring

1. Connect Jetson to the same network as your computer
2. Enter the Jetson's IP address and SSH credentials
3. Optionally enter your RTSP camera URLs (up to 2 cameras)
4. Click **Deploy** to start installation

> **Note:** First startup takes 5-10 minutes — the system downloads and compiles the gun detection model for TensorRT optimization.

### Deployment Complete

1. Open **http://\<device-ip\>:5000** in your browser
2. You'll see two demo cameras detecting guns in sample videos
3. If you provided RTSP URLs, your cameras will also appear with gun detection enabled

To modify camera configuration later, SSH into the device and edit:

```bash
cd ~/gun-detection-frigate
nano config/config.yml
docker compose restart
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 5000 already in use | Stop existing services: `docker stop $(docker ps -q --filter publish=5000)` |
| Model compilation slow | First startup needs 5-10 min for TensorRT optimization, subsequent starts are instant |
| Container keeps restarting | Check logs: `docker logs frigate` — likely GPU memory or driver issue |
| RTSP camera not showing | Verify RTSP URL works with VLC. Edit `config/config.yml` on the device and restart: `docker compose restart` |

### Target {#jetson_local type=local config=devices/jetson_deploy.yaml}

Deploy directly on the current machine (requires NVIDIA GPU).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed
2. Click **Deploy** to start installation

> **Note:** First startup takes 5-10 minutes for TensorRT model compilation.

### Deployment Complete

1. Open **http://localhost:5000** in your browser
2. You'll see two demo cameras detecting guns in sample videos

To add RTSP cameras, edit the config file and restart:

```bash
cd ~/gun-detection-frigate
nano config/config.yml
docker compose restart
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 5000 already in use | Stop existing services: `docker stop $(docker ps -q --filter publish=5000)` |
| Container keeps restarting | Check logs: `docker logs frigate` — likely GPU memory or driver issue |

## Step 3: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The Frigate dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |
### Deployment Complete

Congratulations! Frigate gun detection system is now running.

#### Quick Verification

1. Open the Frigate dashboard in your browser (URL shown after deployment)
2. Check the **Birdseye** view for all-camera overview
3. Verify gun detections appear with bounding boxes on demo videos
4. Click on events to see recorded snapshots with timestamps

#### Adding or Modifying Cameras

To add more RTSP cameras or change existing ones, SSH into the device and edit the configuration:

```bash
cd ~/gun-detection-frigate
nano config/config.yml
```

Add camera entries under `cameras:`:

```yaml
  my_camera:
    enabled: true
    ffmpeg:
      inputs:
        - path: rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
          roles:
            - detect
            - record
    detect:
      width: 1920
      height: 1080
      fps: 5
    objects:
      track:
        - gun
```

Common RTSP URL formats:
- **Hikvision:** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`
- **Dahua:** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`

Then restart Frigate:

```bash
docker compose restart
```

#### Next Steps

- Configure notification alerts via MQTT (broker runs on port 1883)
- Adjust detection thresholds in `config/config.yml` (`objects.filters.gun.threshold`)
- Set up recording retention policies (`record.retain.days`)
- [Frigate Documentation](https://docs.frigate.video/)

## Preset: reComputer R2000 + Hailo {#r2000_hailo}

Real-time gun detection using Frigate NVR with Hailo AI accelerator on reComputer R2000.

| Device | Purpose |
|--------|---------|
| reComputer R2000 + Hailo | Edge AI with Hailo NPU acceleration |
| IP Camera (optional) | RTSP video source for monitoring |

**What you'll get:**
- Real-time gun detection with bounding boxes and confidence scores
- Web dashboard for live monitoring and event review
- Automatic recording and snapshots when guns are detected
- MQTT integration for alerts and automation

**Requirements:** Docker on target device · Hailo AI accelerator installed

## Step 1: Initialize Cameras {#init_cameras_r2000 type=manual required=false}

Set up your IP cameras and obtain RTSP stream URLs.

### Wiring

1. Connect your IP camera to the same network as the deployment device
2. Find the camera's IP address (check your router's DHCP client list, or use the manufacturer's tool)
3. Access the camera's web management interface (usually `http://<camera-ip>`)
4. Enable RTSP streaming in the camera settings (usually enabled by default)
5. Note down the RTSP URL for your camera

> **Common RTSP URL formats:**
> - **Hikvision:** `rtsp://admin:password@<ip>:554/Streaming/Channels/101` (main stream) or `/102` (sub stream)
> - **Dahua:** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0` (main) or `&subtype=1` (sub)
> - **Generic ONVIF:** Use the camera's ONVIF discovery tool to find the stream URL

**Tip:** Use the sub stream (lower resolution) for detection to reduce CPU/GPU load, and the main stream for recording.

You can test your RTSP URL with VLC: **Media > Open Network Stream > paste the URL**.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot access camera web interface | Verify camera IP with `ping <camera-ip>`. Check if camera and computer are on the same subnet |
| RTSP stream not working | Verify RTSP is enabled in camera settings. Try with VLC first. Check username/password |
| Camera not found on network | Power cycle the camera. Check Ethernet cable connection. Try manufacturer's discovery tool (e.g., Hikvision SADP, Dahua ConfigTool) |

## Step 2: Deploy Frigate {#deploy_frigate_r2000 type=docker_deploy required=true config=devices/r2000_hailo_deploy.yaml}

Deploy Frigate NVR with Hailo-accelerated gun detection to your reComputer R2000.

### Target {#r2000_remote type=remote config=devices/r2000_hailo_deploy.yaml default=true}

Deploy to a remote reComputer R2000 via SSH.

### Wiring

1. Ensure Hailo AI Kit is installed (check with `ls /dev/hailo*`)
2. Connect the device to the same network as your computer
3. Enter the device's IP address and SSH credentials
4. Optionally enter your RTSP camera URLs (up to 2 cameras)
5. Click **Deploy** to start installation

> **Note:** The deployment will automatically check and install the required HailoRT 4.21.0 driver if needed (may take 5-10 minutes on first run). At least 4 GB of free disk space is required.

### Deployment Complete

1. Open **http://\<device-ip\>:5000** in your browser
2. You'll see two demo cameras detecting guns in sample videos
3. If you provided RTSP URLs, your cameras will also appear with gun detection enabled

To modify camera configuration later, SSH into the device and edit:

```bash
cd ~/gun-detection-r2000-hailo
nano config/config.yml
docker compose restart
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Hailo device not found | Check Hailo is properly seated in M.2 slot: `ls /dev/hailo*` should show `/dev/hailo0` |
| HailoRT version mismatch | Frigate requires HailoRT **4.21.0**. Check: `dpkg -l hailort`. Install: `curl -sfL https://raw.githubusercontent.com/blakeblackshear/frigate/dev/docker/hailo8l/user_installation.sh \| sudo bash` then reboot |
| Insufficient disk space | Need at least 4 GB free. Run `docker system prune -a` and `sudo apt clean` to free space |
| Port 5000 already in use | Stop existing services: `docker stop $(docker ps -q --filter publish=5000)` |
| Container keeps restarting | Check logs: `docker logs frigate-hailo` — likely Hailo driver issue |
| RTSP camera not showing | Verify RTSP URL works with VLC. Edit `config/config.yml` on the device and restart: `docker compose restart` |

### Target {#r2000_local type=local config=devices/r2000_hailo_deploy.yaml}

Deploy directly on the current machine (requires Hailo AI accelerator).

### Wiring

1. Ensure Docker is installed and Hailo device is accessible (`ls /dev/hailo*`)
2. Click **Deploy** to start installation

> **Note:** At least 4 GB of free disk space is required for the Frigate Docker image.

### Deployment Complete

1. Open **http://localhost:5000** in your browser
2. You'll see two demo cameras detecting guns in sample videos

To add RTSP cameras, edit the config file and restart:

```bash
nano config/config.yml
docker compose restart
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Hailo device not found | Check Hailo is properly seated: `ls /dev/hailo*` should show `/dev/hailo0` |
| Port 5000 already in use | Stop existing services: `docker stop $(docker ps -q --filter publish=5000)` |
| Container keeps restarting | Check logs: `docker logs frigate-hailo` — likely Hailo driver issue |

## Step 3: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The Frigate dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |
### Deployment Complete

Congratulations! Frigate gun detection system is now running.

#### Quick Verification

1. Open the Frigate dashboard in your browser (URL shown after deployment)
2. Check the **Birdseye** view for all-camera overview
3. Verify gun detections appear with bounding boxes on demo videos
4. Click on events to see recorded snapshots with timestamps

#### Adding or Modifying Cameras

To add more RTSP cameras or change existing ones, SSH into the device and edit the configuration:

```bash
cd ~/gun-detection-frigate
nano config/config.yml
```

Add camera entries under `cameras:`:

```yaml
  my_camera:
    enabled: true
    ffmpeg:
      inputs:
        - path: rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
          roles:
            - detect
            - record
    detect:
      width: 1920
      height: 1080
      fps: 5
    objects:
      track:
        - gun
```

Common RTSP URL formats:
- **Hikvision:** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`
- **Dahua:** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`

Then restart Frigate:

```bash
docker compose restart
```

#### Next Steps

- Configure notification alerts via MQTT (broker runs on port 1883)
- Adjust detection thresholds in `config/config.yml` (`objects.filters.gun.threshold`)
- Set up recording retention policies (`record.retain.days`)
- [Frigate Documentation](https://docs.frigate.video/)
