# Deploy Workstation Time and Material Monitoring

## Preset: Jetson local deployment {#jetson_local}

Use a supported Orin NX 8GB/16GB or Orin Nano 8GB with Ubuntu 22.04, L4T 36.4.3 and kernel 5.15.148-tegra. Install the JetPack NVIDIA Container Toolkit and Docker Compose v2. The SSH user must have Docker access without sudo and write access to its home directory. Have at least 18GB free for initial download/extraction and restore points, plus room for your datasets. Training must be stopped before an upgrade.

Deployment uses the release hooks shipped with this solution; older engine builds are stopped before any services are switched.

## Step 1: Deploy the application {#jetson_worktime type=docker_deploy config=devices/jetson_deploy.yaml}

Upload the release files, pull the pinned image, run a real CUDA and GPU NMS check, then start the web and training services. A missing camera does not block deployment.

### Target {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_deploy.yaml default=true}

Enter the device address, SSH user and your password or key. Choose a free web port (default 8088) and leave the encoder on Automatic. Then start deployment.

### Wiring

Connect the Jetson to power and your local network; the viewing browser must reach it directly. Media ports are 8189 TCP/UDP, 8554 TCP, 8889 TCP and 9997 TCP — change their shared offset if another application uses them. Allow the web port and the WebRTC port through your local firewall.

### Deployment Complete

The engine uploads the release files, obtains the fixed candidate image, verifies its layers and performs a real CUDA and GPU NMS check. The initialization service seeds missing configuration and public models. The web and training services start separately; readiness requires SQLite, the media service, the GPU check and a recent trainer heartbeat. A missing camera does not block deployment.

For a disconnected Jetson, first use the application's offline staging/export flow on a connected machine and select ARM64. Transfer the complete offline bundle including image archives to the deployer, then use offline deployment. Do not copy only the Compose file. A maintainer can also run `assets/docker/scripts/package.py export --output /absolute/output/path` on a verified Jetson to create a self-contained archive.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment fails after the service switch | The failure hook restores the previous configuration, database and services; wait for it to finish before retrying |
| SSH connection lost during deployment | The device watchdog recovers within 15 minutes; wait for recovery before retrying, and do not remove `release-state/` during deployment |
| Worried about existing data | Persistent files live under `~/.sensecraft/deployments/jetson_worktime/persistent/` (the engine may display a different resolved directory); back this directory up regularly and keep configurations private |
| Recovery images pruned | Each committed release pins the previous local image by content ID and at most two release checkpoints are kept; do not prune images used by recovery |

The solution ID is `workstation_monitoring`. Deployment uses the retained internal device/step ID and Compose project name `jetson_worktime` to preserve the existing directory and data. See the [name and deployment mapping](docs/operations.md#solution-naming) for details. Manual recovery, diagnostics and limitations are documented in [operations](docs/operations.md) and [validation](docs/validation.md).

## Step 2: Open the monitoring dashboard {#verify_dashboard type=web_dashboard required=false config=devices/dashboard.yaml}

Open the dashboard on the deployed Jetson. The address is filled in from Step 1 (default web port 8088); confirm the page loads and finish the camera setup.

### Deployment Complete

1. Open the displayed Jetson URL. In Settings, add your RTSP camera or select a USB V4L2 device, test the connection and save. Credentials stay in the device's persistent configuration; never put them into solution YAML.
2. Draw the station/seat and material regions before enabling counting. Privacy mode starts enabled.
3. Official base models are preinstalled. Start with YOLO11n and batch 1 on 8GB devices; upload your own compatible YOLO `.pt` model from the Models page when needed.

Nano uses software H.264 at a lower preview profile; NX uses NVIDIA hardware H.264. If a USB camera is added while running, refresh the device list (access uses the host video group). Finish or pause training before an upgrade; after a restart, an unfinished job is marked interrupted and resumes from its latest complete checkpoint on the training page.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not load | Wait for Step 1 to complete, then refresh; confirm the browser reaches the Jetson web port directly and the firewall allows it |
| No camera image | Re-test the RTSP URL or refresh the USB device list; the host user needs video-group access |
| Preview stutters on Nano | Select Software H.264 in Step 1 and redeploy; keep the lower preview profile |
| Hardware encoder unavailable | Select Software H.264 and redeploy; the host multimedia driver must match the supported L4T baseline |
| Training interrupted after a restart | Resume from the latest complete checkpoint on the training page |