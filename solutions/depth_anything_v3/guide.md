## Preset: Jetson One-Click Depth Demo {#jetson_depth}

Deploy Depth Anything V3 to your Jetson device with one click from this platform.

| Device | Purpose |
|--------|---------|
| NVIDIA Jetson (reComputer) | Runs Depth Anything V3 in Docker |
| USB Camera (optional) | Real-time depth inference input |

**What you'll get:**
- Automatic remote deployment through SSH
- Preconfigured Docker container with GPU runtime
- Ready-to-run Depth Anything V3 environment on Jetson

**Requirements:** Jetson on Linux + SSH reachable + Docker available

## Step 1: Deploy Depth Anything V3 {#deploy_depth_anything type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy the containerized runtime to your Jetson. No terminal command input is required from the user.

### Target {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

Deploy to your Jetson over SSH with one click.

### Wiring

1. Connect Jetson to the same network as your computer
2. Plug in USB camera if you want live depth inference
3. Fill in Jetson IP, SSH username, and password
4. Click **Deploy**

### Deployment Complete

1. The Docker container is running on your Jetson
2. USB camera inference starts automatically in the container
3. RTSP output is published at `rtsp://<jetson-ip>:8554/depth`
4. No additional command input is required for deployment completion

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP address, username, password, and that Jetson SSH service is enabled |
| Docker runtime check failed | Ensure Docker is installed and NVIDIA runtime is available on Jetson |
| Docker permission denied (not in docker group) | Run `sudo usermod -aG docker <ssh-user>`, then `newgrp docker` (or log out/in), verify with `docker info`, and retry deployment |
| Disk space not enough | Free space on Jetson root partition and deploy again |
| Deployment timeout | Keep Jetson online and retry after checking network quality |
| RTSP stream not available | Check camera is attached under `/dev/video*` and inspect logs: `docker logs depth_anything_v3` |
| `Failed to read frame from camera` in logs | Set **Camera ID** to `auto` or try `1` (some USB cameras expose capture on `/dev/video1` instead of `/dev/video0`) |

### Target {#jetson_local type=local config=devices/jetson_deploy.yaml}

Deploy directly on the current machine (requires NVIDIA GPU).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed
2. Click **Deploy** to start installation

> **Note:** First startup may take 5-10 minutes for TensorRT model compilation and Docker image download.

### Deployment Complete

1. The Docker container is running on this machine
2. USB camera inference starts automatically in the container
3. RTSP output is published at `rtsp://localhost:8554/depth`
4. Use **Step 2: Preview Depth Video Stream** to view the stream

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 8554 already in use | Stop existing services on that port |
| Container keeps restarting | Check logs: `docker logs depth_anything_v3` — likely GPU memory or driver issue |

## Step 2: Preview Depth Video Stream {#preview_depth_stream type=preview required=false config=devices/preview.yaml}

Use this step to view your Jetson RTSP inference stream directly in the platform UI.

### Wiring

1. Connect a USB camera to Jetson (check it appears as `/dev/video0` or another `/dev/video*`)
2. Ensure your inference pipeline publishes RTSP on Jetson (recommended path: `rtsp://<jetson-ip>:8554/depth`)
3. In this step, enter that RTSP URL
4. Click **Connect** to start preview

### Deployment Complete

1. Live stream is visible in the preview window
2. If your pipeline outputs depth/overlay frames, they are shown in real time
3. You can disconnect/reconnect without redeploying Step 1

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Preview black screen | Verify RTSP URL with VLC first, then retry in this page |
| Connection timeout | Confirm Jetson port `8554` is reachable from the machine running this platform |
| Only raw camera seen | Your Jetson pipeline is likely publishing camera passthrough; switch RTSP source to your inference output stream |
### Deployment Complete

Depth Anything V3 runtime has been deployed successfully on your Jetson.

#### Validation Checklist

1. Deployment status shows success in this page
2. The service container stays in running state
3. You can proceed to your next product integration step directly
