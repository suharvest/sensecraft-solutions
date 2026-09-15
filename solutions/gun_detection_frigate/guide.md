## Preset: NVIDIA Jetson {#jetson}

Real-time gun detection with Frigate NVR on NVIDIA Jetson. Detections trigger recordings and snapshots, and alerts can go to other systems over MQTT.

- **Devices:** NVIDIA Jetson (reComputer); IP camera optional — demo videos run without one.
- **Software:** Docker and NVIDIA Container Toolkit on the target device.
- **Network:** camera, Jetson and this computer on the same network.

## Step 1: Initialize Cameras {#init_cameras_jetson type=manual required=false}

Get the RTSP stream URL of your IP camera. Skip this if you only use the demo videos.

### Wiring

1. Connect the IP camera to the same network as the Jetson
2. Find the camera's IP in your router's DHCP client list or the manufacturer's tool
3. Open the camera's web interface (usually `http://<camera-ip>`) and confirm RTSP is enabled
4. Note the RTSP URL and test it in VLC (**Media > Open Network Stream**)

> **Common RTSP URL formats:**
> - **Hikvision:** `rtsp://admin:password@<ip>:554/Streaming/Channels/101` (main stream) or `/102` (sub stream)
> - **Dahua:** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0` (main) or `&subtype=1` (sub)
> - **Generic ONVIF:** Use the camera's ONVIF discovery tool to find the stream URL

Use the sub stream for detection and the main stream for recording.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cannot access camera web interface | Test with `ping <camera-ip>`; make sure camera and computer are on the same subnet |
| RTSP stream not working | Confirm RTSP is enabled, check username/password, test in VLC first |
| Camera not found on network | Power cycle the camera, check the Ethernet cable, use the manufacturer's discovery tool (e.g., Hikvision SADP, Dahua ConfigTool) |

## Step 2: Deploy Frigate {#deploy_frigate_jetson type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy Frigate NVR and the gun detection model to the NVIDIA Jetson.

### Target {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

Deploy to a Jetson on the network over SSH.

### Wiring

1. Connect the Jetson to the same network as your computer
2. Enter the Jetson's IP address and SSH credentials
3. Optionally enter RTSP camera URLs (up to 2)
4. Click **Deploy**. First startup takes 5-10 minutes to compile the model

### Deployment Complete

Open **http://\<device-ip\>:5000**. The two demo videos show gun detection boxes; RTSP cameras you entered appear as well.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| NVIDIA runtime not found | `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 5000 already in use | `docker stop $(docker ps -q --filter publish=5000)` |
| Slow first startup | Model compilation takes 5-10 minutes the first time only |
| Container keeps restarting | Run `docker logs frigate`; usually a GPU memory or driver issue |
| RTSP camera not showing | Verify the URL in VLC, then edit `config/config.yml` as in step 3 and restart |

### Target {#jetson_local type=local config=devices/jetson_deploy.yaml}

Deploy on this machine. It must be an NVIDIA GPU device with Docker and NVIDIA Container Toolkit installed.

### Wiring

1. Confirm Docker and NVIDIA Container Toolkit are installed
2. Click **Deploy**. First startup takes 5-10 minutes to compile the model

### Deployment Complete

Open **http://localhost:5000**. The two demo videos show gun detection boxes.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| NVIDIA runtime not found | `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 5000 already in use | `docker stop $(docker ps -q --filter publish=5000)` |
| Container keeps restarting | Run `docker logs frigate`; usually a GPU memory or driver issue |

## Step 3: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Click below to open the Frigate dashboard.

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| Page not loading | Make sure the previous step deployed successfully |
| Wrong host/port | If you deployed to a remote device, use its IP in the URL |
### Deployment Complete

#### Quick Verification

1. Open the Frigate dashboard and check the **Birdseye** view for all cameras
2. Confirm gun detection boxes appear on the demo videos
3. Click an event to see its timestamped snapshot

#### Adding or Modifying Cameras

SSH into the device and edit the configuration:

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

Save and restart Frigate:

```bash
docker compose restart
```

#### Next Steps

- Configure alerts over MQTT (port 1883)
- Adjust the detection threshold in `config/config.yml` (`objects.filters.gun.threshold`)
- Set recording retention (`record.retain.days`)
- [Frigate Documentation](https://docs.frigate.video/)

## Preset: reComputer AI Industrial R21 + Hailo {#r2000_hailo}

Real-time gun detection with Frigate NVR and a Hailo accelerator on reComputer AI Industrial R21. Detections trigger recordings and snapshots, and alerts can go to other systems over MQTT.

- **Devices:** reComputer AI Industrial R21 + Hailo; IP camera optional — demo videos run without one.
- **Software:** Docker and the Hailo accelerator on the target device, at least 4 GB free disk.
- **Network:** camera, R21 and this computer on the same network.

## Step 1: Initialize Cameras {#init_cameras_r2000 type=manual required=false}

Get the RTSP stream URL of your IP camera. Skip this if you only use the demo videos.

### Wiring

1. Connect the IP camera to the same network as the R21
2. Find the camera's IP in your router's DHCP client list or the manufacturer's tool
3. Open the camera's web interface (usually `http://<camera-ip>`) and confirm RTSP is enabled
4. Note the RTSP URL and test it in VLC (**Media > Open Network Stream**)

> **Common RTSP URL formats:**
> - **Hikvision:** `rtsp://admin:password@<ip>:554/Streaming/Channels/101` (main stream) or `/102` (sub stream)
> - **Dahua:** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0` (main) or `&subtype=1` (sub)
> - **Generic ONVIF:** Use the camera's ONVIF discovery tool to find the stream URL

Use the sub stream for detection and the main stream for recording.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cannot access camera web interface | Test with `ping <camera-ip>`; make sure camera and computer are on the same subnet |
| RTSP stream not working | Confirm RTSP is enabled, check username/password, test in VLC first |
| Camera not found on network | Power cycle the camera, check the Ethernet cable, use the manufacturer's discovery tool (e.g., Hikvision SADP, Dahua ConfigTool) |

## Step 2: Deploy Frigate {#deploy_frigate_r2000 type=docker_deploy required=true config=devices/r2000_hailo_deploy.yaml}

Deploy Frigate NVR and the gun detection model to the reComputer AI Industrial R21.

### Target {#r2000_remote type=remote config=devices/r2000_hailo_deploy.yaml default=true}

Deploy to an R21 on the network over SSH. The deployment checks for and installs the HailoRT 4.21.0 driver if needed (5-10 minutes on first run).

### Wiring

1. Run `ls /dev/hailo*` on the device and confirm `/dev/hailo0` is listed
2. Connect the device to the same network as your computer
3. Enter the device's IP address and SSH credentials
4. Optionally enter RTSP camera URLs (up to 2)
5. Click **Deploy**

### Deployment Complete

Open **http://\<device-ip\>:5000**. The two demo videos show gun detection boxes; RTSP cameras you entered appear as well.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Hailo device not found | Check Hailo is seated in the M.2 slot; `ls /dev/hailo*` should show `/dev/hailo0` |
| HailoRT version mismatch | HailoRT **4.21.0** is required; check with `dpkg -l hailort`. Install: `curl -sfL https://raw.githubusercontent.com/blakeblackshear/frigate/dev/docker/hailo8l/user_installation.sh \| sudo bash`, then reboot |
| Insufficient disk space | At least 4 GB is needed; run `docker system prune -a` and `sudo apt clean` |
| Port 5000 already in use | `docker stop $(docker ps -q --filter publish=5000)` |
| Container keeps restarting | Run `docker logs frigate-hailo`; usually a Hailo driver issue |
| RTSP camera not showing | Verify the URL in VLC, then edit `config/config.yml` as in step 3 and restart |

### Target {#r2000_local type=local config=devices/r2000_hailo_deploy.yaml}

Deploy on this machine. It needs Docker, the Hailo accelerator and at least 4 GB free disk.

### Wiring

1. Run `ls /dev/hailo*` and confirm `/dev/hailo0` is listed
2. Click **Deploy**

### Deployment Complete

Open **http://localhost:5000**. The two demo videos show gun detection boxes.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Hailo device not found | Check Hailo is seated; `ls /dev/hailo*` should show `/dev/hailo0` |
| Port 5000 already in use | `docker stop $(docker ps -q --filter publish=5000)` |
| Container keeps restarting | Run `docker logs frigate-hailo`; usually a Hailo driver issue |

## Step 3: Open Dashboard {#dashboard_r2000_hailo type=web_dashboard required=true config=devices/dashboard.yaml}

Click below to open the Frigate dashboard.

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| Page not loading | Make sure the previous step deployed successfully |
| Wrong host/port | If you deployed to a remote device, use its IP in the URL |
### Deployment Complete

#### Quick Verification

1. Open the Frigate dashboard and check the **Birdseye** view for all cameras
2. Confirm gun detection boxes appear on the demo videos
3. Click an event to see its timestamped snapshot

#### Adding or Modifying Cameras

SSH into the device and edit the configuration:

```bash
cd ~/gun-detection-r2000-hailo
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

Save and restart Frigate:

```bash
docker compose restart
```

#### Next Steps

- Configure alerts over MQTT (port 1883)
- Adjust the detection threshold in `config/config.yml` (`objects.filters.gun.threshold`)
- Set recording retention (`record.retain.days`)
- [Frigate Documentation](https://docs.frigate.video/)
