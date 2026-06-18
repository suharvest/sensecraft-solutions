## Preset: Jetson NVBlox Deployment {#jetson_nvblox}

![NVBlox Orbbec warehouse demo](gallery/isaac_sim_nvblox_humans.gif)

Deploy the Orbbec Gemini2 plus Isaac ROS NVBlox mapping stack to a Jetson device over SSH.

| Device | Purpose |
|--------|---------|
| NVIDIA Jetson Orin | Runs host-side Orbbec ROS 2 driver plus the long-running NVBlox container |

**What this deployment does**

- Optionally copies `nvblox_images.tar` from the provisioning-station host for the fastest LAN transfer path
- Optionally downloads `nvblox_images.tar` from a custom mirror URL
- Downloads `nvblox_images.tar` with the bundled OneDrive downloader
- Loads the Isaac ROS base image locally on the Jetson
- Prepares the Jetson host ROS 2 and Orbbec workspace
- Builds the derived NVBlox runtime image and workspace on the Jetson
- Starts the host camera driver and the Docker Compose service

**Requirements**

- Jetson Orin with Ubuntu 22.04 and JetPack 6.x
- Orbbec Gemini2 connected to the Jetson
- SSH access to the Jetson
- Internet access on the Jetson for apt, ROS, and GitHub
- At least 30GB of free disk space on the Jetson before deployment
- For the first deployment, 40GB or more is strongly recommended to leave room for the image tar cache and workspace build artifacts

## Step 1: Deploy NVBlox Orbbec {#deploy_nvblox_orbbec type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy the full NVBlox Orbbec stack to your Jetson. The first deployment is intentionally heavy: it prepares both the host environment and the container workspace before the final Compose service starts.

Before you click **Deploy**, make sure the Jetson root filesystem has at least 30GB free. If the base image tar still needs to be downloaded or kept locally, plan for 40GB or more to avoid running out of space mid-deployment.


### Deployment Complete

The NVBlox Orbbec stack has been deployed to your Jetson.

#### Validation Checklist

1. Step 1 shows success in the deployment page.
2. The Compose service `nvblox-orbbec` remains in running state.
3. Container logs include the TF readiness marker.
4. Container logs include the runtime output probe marker.

### Target {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

Deploy to your Jetson over SSH with one click.

### Wiring

1. Connect the Orbbec Gemini2 camera to the Jetson.
2. Connect your Jetson and your computer to the same network.
3. Fill in the Jetson IP address, SSH username, and password.
4. If you already have `nvblox_images.tar` on the provisioning-station host, fill in `Local Base Image Tar Path` to copy it directly to the Jetson.
5. If you host the tar on a faster mirror, fill in `Mirror URL`.
6. Click **Deploy** and keep the Jetson powered on during the full setup.

### Deployment Complete

1. The downloaded base image tar is cached under `~/nvblox_demo/downloads`.
2. The base Isaac ROS image is available locally on the Jetson.
3. The host-side Orbbec ROS 2 workspace is prepared under `~/nvblox_demo/ros2_ws`.
4. The container-side workspace is prepared under `~/nvblox_demo/isaac_ros-dev`.
5. The Compose service `nvblox-orbbec` is running on the Jetson.
6. Success is validated by runtime readiness markers in container logs rather than a preview page.

### Notes

- `tar + docker load` only solves the base image source. Host package installation and source sync still require internet access.
- The fastest path is usually `Local Base Image Tar Path`, because it bypasses Jetson-to-SharePoint throttling and copies over LAN/SSH instead.
- The first run can take a long time because it installs ROS dependencies, clones repositories, and builds workspaces on-device.
- Re-deployments are faster because managed stamp files are reused when the prepared state is still valid.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify Jetson IP, username, password, and SSH service status |
| Runtime validation failed early | Ensure the target device is Jetson Orin with Ubuntu 22.04 and JetPack 6.x |
| Runtime validation reports insufficient disk space | Free space on the Jetson root filesystem until at least 30GB remains. For a first-time deployment, 40GB+ free space is safer |
| Docker Compose unavailable | Install `docker compose` or `docker-compose`, then retry deployment |
| Download succeeded but image check still fails | The tar may not contain the expected tag; inspect `docker images` on the Jetson |
| Host prepare step fails | Check network access from Jetson to apt, ROS, and GitHub endpoints |
| Host camera step fails | Reconnect the Gemini2 camera and confirm the device creates `/dev/video*` nodes |
| Compose service is running but validation fails | Inspect logs on Jetson: `cd ~/nvblox-orbbec/jetson && docker compose logs --tail=200` |


### Target {#jetson_local type=local config=devices/jetson_deploy.yaml}

Deploy NVBlox Orbbec directly on the local machine. This mode is suitable when a Jetson Orin with an Orbbec Gemini2 camera is connected directly to the local machine.

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed on the local machine.
2. Connect the Orbbec Gemini2 camera via USB.
3. Click **Deploy** to start the local deployment.

> **Note:** The first deployment may take 10-15 minutes while the Docker image is built and ROS 2 dependencies installed.

### Deployment Complete

1. The Compose service `nvblox-orbbec` is running locally.
2. The Orbbec camera driver and NVBlox mapping stack run together inside the container.
3. Success is validated by runtime readiness markers in the container logs.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Camera not detected | Check USB connection: `lsusb | grep -i orbbec` |
| Container keeps restarting | Check logs: `docker logs nvblox-orbbec` |
| Docker Compose unavailable | Install `docker compose` plugin, then retry deployment |
