## Preset: Jetson GPT OSS 20B Service {#jetson_got_oss}

Deploy GPT OSS 20B to your Jetson device with one click from this platform.

| Device | Purpose |
|--------|---------|
| NVIDIA Jetson (reComputer) | Runs GPT OSS 20B in Docker |

## Step 1: Deploy GPT OSS 20B Service {#deploy_got_oss type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy the containerized GPT OSS 20B runtime to your Jetson over SSH.

### Target {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

Deploy to your Jetson over SSH with one click.

### Wiring

1. Connect Jetson and your computer to the same network.
2. Fill in Jetson IP, SSH username, and password.
3. Click **Deploy**.

### Deployment Complete

1. The GPT OSS 20B container is running on your Jetson.
2. `llama-server` is started inside the container.
3. The service endpoint is available at `http://<jetson-ip>:8080`.
4. Readiness endpoint is available at `http://<jetson-ip>:8080/v1/models`.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify Jetson IP, username, password, and SSH service status |
| Docker runtime check failed | Ensure Docker is installed and NVIDIA runtime is available |
| Docker Compose unavailable | Ensure `docker compose` or `docker-compose` is installed |
| Service start failed | Inspect logs on Jetson: `docker compose logs --tail=200` |
| `503 {"message":"Loading model"}` on `/v1/models` | Model is still warming up; first run can take several minutes |
| Out-of-memory at startup | Reduce settings, for example set `Llama NGL=16` and `Llama Context=512` |

### Target {#jetson_local type=local config=devices/jetson_deploy.yaml}

Deploy directly on the current machine (requires NVIDIA GPU with sufficient VRAM).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed
2. Click **Deploy** to start installation

> **Note:** First startup may take 15-30 minutes for Docker image download and model loading. Requires at least 20GB free disk space.

### Deployment Complete

1. Open **http://localhost:8080** in your browser
2. You'll see the GPT OSS chat interface ready for interaction

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 8080 already in use | Stop existing services on that port |
| Container keeps restarting | Check logs: `docker compose logs --tail=200` |
| GPU out of memory | The 20B model requires significant GPU memory. Try a smaller model variant |


## Step 2: Open Service Link {#preview_service type=preview required=false config=devices/preview.yaml}

Use this step to open the Jetson service URL directly in a new browser tab.

### Wiring

1. Enter Jetson IP in this step.
2. Click **Connect**.
3. The platform opens `http://<jetson-ip>:8080` in a new tab.

### Deployment Complete

1. The service page opens in your browser.
2. You can return here and click **Connect** again to reopen it.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Invalid host input | Enter a valid IP or hostname, for example `192.168.1.100` |
| New tab not opened | Allow pop-ups for this site and retry |
| Service page not reachable | Confirm Jetson service is listening on `8080` and network is reachable |
### Deployment Complete

GPT OSS 20B runtime has been deployed successfully on your Jetson.

#### Validation Checklist

1. Step 1 deployment status shows success.
2. The GPT OSS 20B container stays in running state.
3. Clicking **Connect** in Step 2 opens `http://<jetson-ip>:8080`.
