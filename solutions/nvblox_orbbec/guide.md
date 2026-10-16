## Preset: Jetson NVBlox Deployment {#jetson_nvblox}

![NVBlox Orbbec warehouse demo](gallery/isaac_sim_nvblox_humans.gif)

Deploy the Orbbec Gemini2 plus Isaac ROS NVBlox mapping stack to a Jetson device over SSH.

| Device | Purpose |
|--------|---------|
| NVIDIA Jetson Orin | Runs the Orbbec camera driver and the NVBlox mapping service |

**Requirements**

- Jetson Orin with Ubuntu 22.04 and JetPack 6.x
- Orbbec Gemini2 connected to the Jetson
- SSH access to the Jetson
- Internet access on the Jetson for apt, ROS, and GitHub
- At least 30GB of free disk space on the Jetson; 40GB or more recommended for the first deployment

## Step 1: Deploy NVBlox Orbbec {#deploy_nvblox_orbbec type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy NVBlox Orbbec to your Jetson. The first deployment takes a long time.


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

1. The Compose service `nvblox-orbbec` stays running on the Jetson.
2. There is no preview page in this version; success is indicated by the runtime readiness markers in the container logs.

### Notes

- Providing the base image tar still requires internet access for dependency installation and source sync.
- The fastest option is usually `Local Base Image Tar Path`, which copies the tar over the LAN.
- Re-deployments skip preparation steps that are already complete.

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
| Camera not detected | Check USB connection: `lsusb \| grep -i orbbec` |
| Container keeps restarting | Check logs: `docker logs nvblox-orbbec` |
| Docker Compose unavailable | Install `docker compose` plugin, then retry deployment |
