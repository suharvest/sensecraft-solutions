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
| Port 5000 already in use | Run `docker ps --filter publish=5000 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}'` first to inspect what is using port 5000, then stop only the intended container with `docker stop <container_name>` |
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
| Port 5000 already in use | Run `docker ps --filter publish=5000 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}'` first to inspect what is using port 5000, then stop only the intended container with `docker stop <container_name>` |
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
cd ~/gun-detection-frigate/jetson_deploy
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
docker compose -p gun-detection-frigate restart
```

#### Next Steps

- Configure alerts over MQTT (port 1883)
- Adjust the detection threshold in `config/config.yml` (`objects.filters.gun.threshold`)
- Set recording retention (`record.retain.days`)
- [Frigate Documentation](https://docs.frigate.video/)

## Step 4: Deploy Home Assistant (Optional) {#deploy_ha_jetson type=docker_deploy required=false config=devices/ha_host.yaml}

Select this step only if Home Assistant is not installed yet. If Home Assistant is already running on port 8123 on the target host, the deployer detects it and skips installation automatically. If you already have a standalone HAOS or external Home Assistant instance, uncheck this step and proceed to Step 5.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Home Assistant already running on port 8123 | The deployer detects the running instance and skips installation; proceed to Step 5 |
| Local install fails on macOS or Windows | The container uses Docker host networking, which Docker Desktop disables by default on macOS and Windows (requires Docker Desktop 4.34+ with host networking manually enabled in Settings; otherwise deploy remotely via SSH to a Linux host or connect an existing Home Assistant instance) |

### Target: Deploy Locally {#ha_local_jetson type=local default=true}

Deploy Home Assistant on this machine via local Docker.

### Target: Deploy Remotely via SSH {#ha_remote_jetson type=remote}

Deploy Home Assistant on a remote Linux host (such as the Jetson or another LAN server) over SSH.

## Step 5: Connect Frigate to Home Assistant (Optional) {#connect_ha_jetson type=ha_integration required=false config=devices/ha_integration_jetson.yaml}

Connect Frigate to Home Assistant in one step. This step automatically installs the official `frigate-hass-integration` (`v5.15.7`, compatible with HAOS, local Docker HA, and remote Docker HA), restarts Home Assistant, configures both the Frigate and MQTT integrations, and creates the default persistent gun-detection alert automation (`gun_detection_ha_alert`).

### Prerequisites

- **Remote Docker HA:** Enter the HA host SSH credentials in the SSH section at the top and the HA Web UI administrator username and password below (a newly deployed HA instance is initialized automatically with this account). HAOS and local Docker HA do not require manually configuring an SSH Add-on.
- **Cross-host setup:** If Frigate is deployed locally (`localhost`) while Home Assistant runs on another device, replace the host address in `Frigate URL` and `MQTT Broker` with the Frigate device's LAN IP.
- **Existing MQTT integration:** If Home Assistant already has a configured and loaded MQTT integration, the engine reuses that existing connection without overwriting its broker address. Ensure Frigate (`mqtt.host` in `config/config.yml`) and Home Assistant point to the same MQTT broker, and verify in Home Assistant that `frigate/events` messages arrive before enabling alerts.
- **MQTT security:** The bundled Mosquitto broker started with Frigate allows anonymous LAN connections by default to simplify initial setup. For production deployments, configure Mosquitto username/password authentication and ACLs, and fill in `MQTT Username` and `MQTT Password` below.

### Deployment Complete

> **Warning:** Do not directly modify the auto-created `[Managed by SenseCraft: gun_detection_frigate] Gun Detection Alert` automation—redeploying this solution will overwrite managed automations and erase your changes.

To forward gun-detection alerts to your phone without losing your configuration on redeploy, use either option below:

1. **Create a separate custom automation:**
   In Home Assistant, open **Settings → Automations & Scenes → Create Automation → Create new automation**, switch to YAML mode, and create a standalone automation using the Frigate integration's proxied snapshot path `/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg` (so remote phones can load the snapshot through Home Assistant without exposing Frigate directly).

   **iOS Critical Alert example:**

   ```yaml
   alias: "Gun Detection Mobile Push (iOS)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo'] }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           push:
             sound:
               name: default
               critical: 1
               volume: 1.0
   ```

   **Android high-priority channel example:**

   ```yaml
   alias: "Gun Detection Mobile Push (Android)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo'] }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           ttl: 0
           priority: high
           channel: alarm_stream
   ```

   > **Note:** The examples above exclude the built-in demo cameras (`handgun_demo`, `machinegun_demo`) so looping demo videos do not flood your phone; to test mobile push notifications using the built-in demo videos, temporarily remove `and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo']` from the condition.

2. **Use the community Blueprint:**
   Import the **Frigate Notifications Blueprint** in Home Assistant to visually select the camera, the `gun` label, target mobile devices, and critical-alert or silence action buttons. Because it is user-managed, it is preserved when you redeploy this solution.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Home Assistant login fails | Verify the HA Web UI administrator username and password and ensure port 8123 is reachable |
| Frigate or MQTT unreachable from HA | When HA and Frigate run on different hosts, set `Frigate URL` and `MQTT Broker` to the Frigate device's LAN IP instead of `localhost` |
| Existing HA MQTT integration does not receive `frigate/events` | When MQTT is already configured and loaded in HA, the engine reuses the existing connection instead of overwriting its broker address; ensure `mqtt.host` in Frigate's `config/config.yml` and HA point to the same broker, and verify `frigate/events` messages arrive in HA before enabling alerts |

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
| Port 5000 already in use | Run `docker ps --filter publish=5000 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}'` first to inspect what is using port 5000, then stop only the intended container with `docker stop <container_name>` |
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
| Port 5000 already in use | Run `docker ps --filter publish=5000 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}'` first to inspect what is using port 5000, then stop only the intended container with `docker stop <container_name>` |
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
cd ~/gun-detection-r2000-hailo/r2000_hailo_deploy
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
docker compose -p gun-detection-r2000-hailo restart
```

#### Next Steps

- Configure alerts over MQTT (port 1883)
- Adjust the detection threshold in `config/config.yml` (`objects.filters.gun.threshold`)
- Set recording retention (`record.retain.days`)
- [Frigate Documentation](https://docs.frigate.video/)

## Step 4: Deploy Home Assistant (Optional) {#deploy_ha_r2000 type=docker_deploy required=false config=devices/ha_host.yaml}

Select this step only if Home Assistant is not installed yet. If Home Assistant is already running on port 8123 on the target host, the deployer detects it and skips installation automatically. If you already have a standalone HAOS or external Home Assistant instance, uncheck this step and proceed to Step 5.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Home Assistant already running on port 8123 | The deployer detects the running instance and skips installation; proceed to Step 5 |
| Local install fails on macOS or Windows | The container uses Docker host networking, which Docker Desktop disables by default on macOS and Windows (requires Docker Desktop 4.34+ with host networking manually enabled in Settings; otherwise deploy remotely via SSH to a Linux host or connect an existing Home Assistant instance) |

### Target: Deploy Locally {#ha_local_r2000 type=local default=true}

Deploy Home Assistant on this machine via local Docker.

### Target: Deploy Remotely via SSH {#ha_remote_r2000 type=remote}

Deploy Home Assistant on a remote Linux host (such as the R21 or another LAN server) over SSH.

## Step 5: Connect Frigate to Home Assistant (Optional) {#connect_ha_r2000 type=ha_integration required=false config=devices/ha_integration_r2000.yaml}

Connect Frigate to Home Assistant in one step. This step automatically installs the official `frigate-hass-integration` (`v5.15.7`, compatible with HAOS, local Docker HA, and remote Docker HA), restarts Home Assistant, configures both the Frigate and MQTT integrations, and creates the default persistent gun-detection alert automation (`gun_detection_ha_alert`).

### Prerequisites

- **Remote Docker HA:** Enter the HA host SSH credentials in the SSH section at the top and the HA Web UI administrator username and password below (a newly deployed HA instance is initialized automatically with this account). HAOS and local Docker HA do not require manually configuring an SSH Add-on.
- **Cross-host setup:** If Frigate is deployed locally (`localhost`) while Home Assistant runs on another device, replace the host address in `Frigate URL` and `MQTT Broker` with the Frigate device's LAN IP.
- **Existing MQTT integration:** If Home Assistant already has a configured and loaded MQTT integration, the engine reuses that existing connection without overwriting its broker address. Ensure Frigate (`mqtt.host` in `config/config.yml`) and Home Assistant point to the same MQTT broker, and verify in Home Assistant that `frigate/events` messages arrive before enabling alerts.
- **MQTT security:** The bundled Mosquitto broker started with Frigate allows anonymous LAN connections by default to simplify initial setup. For production deployments, configure Mosquitto username/password authentication and ACLs, and fill in `MQTT Username` and `MQTT Password` below.

### Deployment Complete

> **Warning:** Do not directly modify the auto-created `[Managed by SenseCraft: gun_detection_frigate] Gun Detection Alert` automation—redeploying this solution will overwrite managed automations and erase your changes.

To forward gun-detection alerts to your phone without losing your configuration on redeploy, use either option below:

1. **Create a separate custom automation:**
   In Home Assistant, open **Settings → Automations & Scenes → Create Automation → Create new automation**, switch to YAML mode, and create a standalone automation using the Frigate integration's proxied snapshot path `/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg` (so remote phones can load the snapshot through Home Assistant without exposing Frigate directly).

   **iOS Critical Alert example:**

   ```yaml
   alias: "Gun Detection Mobile Push (iOS)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo'] }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           push:
             sound:
               name: default
               critical: 1
               volume: 1.0
   ```

   **Android high-priority channel example:**

   ```yaml
   alias: "Gun Detection Mobile Push (Android)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo'] }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           ttl: 0
           priority: high
           channel: alarm_stream
   ```

   > **Note:** The examples above exclude the built-in demo cameras (`handgun_demo`, `machinegun_demo`) so looping demo videos do not flood your phone; to test mobile push notifications using the built-in demo videos, temporarily remove `and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo']` from the condition.

2. **Use the community Blueprint:**
   Import the **Frigate Notifications Blueprint** in Home Assistant to visually select the camera, the `gun` label, target mobile devices, and critical-alert or silence action buttons. Because it is user-managed, it is preserved when you redeploy this solution.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Home Assistant login fails | Verify the HA Web UI administrator username and password and ensure port 8123 is reachable |
| Frigate or MQTT unreachable from HA | When HA and Frigate run on different hosts, set `Frigate URL` and `MQTT Broker` to the Frigate device's LAN IP instead of `localhost` |
| Existing HA MQTT integration does not receive `frigate/events` | When MQTT is already configured and loaded in HA, the engine reuses the existing connection instead of overwriting its broker address; ensure `mqtt.host` in Frigate's `config/config.yml` and HA point to the same broker, and verify `frigate/events` messages arrive in HA before enabling alerts |

## Preset: reComputer RK3588 {#rk3588}

Real-time gun detection with Frigate NVR and Rockchip NPU acceleration on reComputer RK3588. Detections trigger recordings and snapshots, and alerts can go to other systems over MQTT.

- **Devices:** reComputer RK3588; IP camera optional — demo videos run without one.
- **Software:** Docker and Rockchip NPU runtime (RKNN) on the target device, at least 4 GB free disk.
- **Network:** camera, reComputer RK3588 and this computer on the same network.

## Step 1: Initialize Cameras {#init_cameras_rk3588 type=manual required=false}

Get the RTSP stream URL of your IP camera. Skip this if you only use the demo videos.

### Wiring

1. Connect the IP camera to the same network as the reComputer RK3588
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

## Step 2: Deploy Frigate {#deploy_frigate_rk3588 type=docker_deploy required=true config=devices/rk3588_deploy.yaml}

Deploy Frigate NVR and the RKNN gun detection model to the reComputer RK3588.

> **RTSP Camera Inputs:** `rtsp_url_1` and `rtsp_url_2` configure two independent cameras (`rtsp_camera_1` and `rtsp_camera_2`), with a single stream per camera used for both `detect` and `record`. If you need dual-stream for a single camera (sub stream for detection + main stream for recording), manually edit `config/config.yml` after deployment to configure two `inputs` under the same camera.

### Target {#rk3588_remote type=remote config=devices/rk3588_deploy.yaml default=true}

Deploy to a reComputer RK3588 on the network over SSH.

### Wiring

1. Confirm NPU and hardware codec device nodes exist on the device (e.g., `/dev/rknpu` or `/dev/dri`)
2. Connect the device to the same network as your computer
3. Enter the device's IP address and SSH credentials
4. Optionally enter RTSP camera URLs (up to 2)
5. Click **Deploy**

### Deployment Complete

Open **http://\<device-ip\>:5000**. The two demo videos show gun detection boxes; RTSP cameras you entered appear as well.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| NPU or codec device node not found | Confirm the target runs the reComputer RK3588 OS image with Rockchip NPU/MPP drivers loaded (`ls /dev/rknpu /dev/dri`) |
| Insufficient disk space | At least 4 GB is needed; run `docker system prune -a` and `sudo apt clean` |
| Port 5000 already in use | Run `docker ps --filter publish=5000 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}'` first to inspect what is using port 5000, then stop only the intended container with `docker stop <container_name>` |
| Container keeps restarting | Run `docker compose -p gun-detection-rk3588 logs` in `~/gun-detection-rk3588/rk3588_deploy` to inspect NPU or runtime errors |
| RTSP camera not showing | Verify the URL in VLC, then edit `config/config.yml` as in step 3 and restart |

### Target {#rk3588_local type=local config=devices/rk3588_deploy.yaml}

Deploy on this machine. It must be a reComputer RK3588 with Docker, Rockchip NPU runtime, and at least 4 GB free disk.

### Wiring

1. Confirm Docker is running and NPU device nodes exist (e.g., `/dev/rknpu` or `/dev/dri`)
2. Optionally enter RTSP camera URLs (up to 2)
3. Click **Deploy**

### Deployment Complete

Open **http://localhost:5000**. The two demo videos show gun detection boxes; RTSP cameras you entered appear as well.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| NPU or codec device node not found | Confirm the machine runs the reComputer RK3588 OS image with Rockchip NPU/MPP drivers loaded (`ls /dev/rknpu /dev/dri`) |
| Port 5000 already in use | Run `docker ps --filter publish=5000 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}'` first to inspect what is using port 5000, then stop only the intended container with `docker stop <container_name>` |
| Container keeps restarting | Run `docker compose -p gun-detection-rk3588 logs` in `~/gun-detection-rk3588/rk3588_deploy` to inspect NPU or runtime errors |

## Step 3: Open Dashboard {#dashboard_rk3588 type=web_dashboard required=true config=devices/dashboard.yaml}

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
cd ~/gun-detection-rk3588/rk3588_deploy
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
docker compose -p gun-detection-rk3588 restart
```

#### Next Steps

- Configure alerts over MQTT (port 1883)
- Adjust the detection threshold in `config/config.yml` (`objects.filters.gun.threshold`)
- Set recording retention (`record.retain.days`)
- [Frigate Documentation](https://docs.frigate.video/)

## Step 4: Deploy Home Assistant (Optional) {#deploy_ha_rk3588 type=docker_deploy required=false config=devices/ha_host.yaml}

Select this step only if Home Assistant is not installed yet. If Home Assistant is already running on port 8123 on the target host, the deployer detects it and skips installation automatically. If you already have a standalone HAOS or external Home Assistant instance, uncheck this step and proceed to Step 5.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Home Assistant already running on port 8123 | The deployer detects the running instance and skips installation; proceed to Step 5 |
| Local install fails on macOS or Windows | The container uses Docker host networking, which Docker Desktop disables by default on macOS and Windows (requires Docker Desktop 4.34+ with host networking manually enabled in Settings; otherwise deploy remotely via SSH to a Linux host or connect an existing Home Assistant instance) |

### Target: Deploy Locally {#ha_local_rk3588 type=local default=true}

Deploy Home Assistant on this machine via local Docker.

### Target: Deploy Remotely via SSH {#ha_remote_rk3588 type=remote}

Deploy Home Assistant on a remote Linux host (such as the reComputer RK3588 or another LAN server) over SSH.

## Step 5: Connect Frigate to Home Assistant (Optional) {#connect_ha_rk3588 type=ha_integration required=false config=devices/ha_integration_rk3588.yaml}

Connect Frigate to Home Assistant in one step. This step automatically installs the official `frigate-hass-integration` (`v5.15.7`, compatible with HAOS, local Docker HA, and remote Docker HA), restarts Home Assistant, configures both the Frigate and MQTT integrations, and creates the default persistent gun-detection alert automation (`gun_detection_ha_alert`).

### Prerequisites

- **Remote Docker HA:** Enter the HA host SSH credentials in the SSH section at the top and the HA Web UI administrator username and password below (a newly deployed HA instance is initialized automatically with this account). HAOS and local Docker HA do not require manually configuring an SSH Add-on.
- **Cross-host setup:** If Frigate is deployed locally (`localhost`) while Home Assistant runs on another device, replace the host address in `Frigate URL` and `MQTT Broker` with the Frigate device's LAN IP.
- **Existing MQTT integration:** If Home Assistant already has a configured and loaded MQTT integration, the engine reuses that existing connection without overwriting its broker address. Ensure Frigate (`mqtt.host` in `config/config.yml`) and Home Assistant point to the same MQTT broker, and verify in Home Assistant that `frigate/events` messages arrive before enabling alerts.
- **MQTT security:** The bundled Mosquitto broker started with Frigate allows anonymous LAN connections by default to simplify initial setup. For production deployments, configure Mosquitto username/password authentication and ACLs, and fill in `MQTT Username` and `MQTT Password` below.

### Deployment Complete

> **Warning:** Do not directly modify the auto-created `[Managed by SenseCraft: gun_detection_frigate] Gun Detection Alert` automation—redeploying this solution will overwrite managed automations and erase your changes.

To forward gun-detection alerts to your phone without losing your configuration on redeploy, use either option below:

1. **Create a separate custom automation:**
   In Home Assistant, open **Settings → Automations & Scenes → Create Automation → Create new automation**, switch to YAML mode, and create a standalone automation using the Frigate integration's proxied snapshot path `/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg` (so remote phones can load the snapshot through Home Assistant without exposing Frigate directly).

   **iOS Critical Alert example:**

   ```yaml
   alias: "Gun Detection Mobile Push (iOS)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo'] }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           push:
             sound:
               name: default
               critical: 1
               volume: 1.0
   ```

   **Android high-priority channel example:**

   ```yaml
   alias: "Gun Detection Mobile Push (Android)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo'] }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           ttl: 0
           priority: high
           channel: alarm_stream
   ```

   > **Note:** The examples above exclude the built-in demo cameras (`handgun_demo`, `machinegun_demo`) so looping demo videos do not flood your phone; to test mobile push notifications using the built-in demo videos, temporarily remove `and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo']` from the condition.

2. **Use the community Blueprint:**
   Import the **Frigate Notifications Blueprint** in Home Assistant to visually select the camera, the `gun` label, target mobile devices, and critical-alert or silence action buttons. Because it is user-managed, it is preserved when you redeploy this solution.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Home Assistant login fails | Verify the HA Web UI administrator username and password and ensure port 8123 is reachable |
| Frigate or MQTT unreachable from HA | When HA and Frigate run on different hosts, set `Frigate URL` and `MQTT Broker` to the Frigate device's LAN IP instead of `localhost` |
| Existing HA MQTT integration does not receive `frigate/events` | When MQTT is already configured and loaded in HA, the engine reuses the existing connection instead of overwriting its broker address; ensure `mqtt.host` in Frigate's `config/config.yml` and HA point to the same broker, and verify `frigate/events` messages arrive in HA before enabling alerts |

## Preset: reComputer RK3576 {#rk3576}

Real-time gun detection with Frigate NVR and Rockchip NPU acceleration on reComputer RK3576. Detections trigger recordings and snapshots, and alerts can go to other systems over MQTT.

- **Devices:** reComputer RK3576; IP camera optional — demo videos run without one.
- **Software:** Docker and Rockchip NPU runtime (RKNN) on the target device, at least 4 GB free disk.
- **Network:** camera, reComputer RK3576 and this computer on the same network.

## Step 1: Initialize Cameras {#init_cameras_rk3576 type=manual required=false}

Get the RTSP stream URL of your IP camera. Skip this if you only use the demo videos.

### Wiring

1. Connect the IP camera to the same network as the reComputer RK3576
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

## Step 2: Deploy Frigate {#deploy_frigate_rk3576 type=docker_deploy required=true config=devices/rk3576_deploy.yaml}

Deploy Frigate NVR and the RKNN gun detection model to the reComputer RK3576.

> **RTSP Camera Inputs:** `rtsp_url_1` and `rtsp_url_2` configure two independent cameras (`rtsp_camera_1` and `rtsp_camera_2`), with a single stream per camera used for both `detect` and `record`. If you need dual-stream for a single camera (sub stream for detection + main stream for recording), manually edit `config/config.yml` after deployment to configure two `inputs` under the same camera.

### Target {#rk3576_remote type=remote config=devices/rk3576_deploy.yaml default=true}

Deploy to a reComputer RK3576 on the network over SSH.

### Wiring

1. Confirm NPU and hardware codec device nodes exist on the device (e.g., `/dev/rknpu` or `/dev/dri`)
2. Connect the device to the same network as your computer
3. Enter the device's IP address and SSH credentials
4. Optionally enter RTSP camera URLs (up to 2)
5. Click **Deploy**

### Deployment Complete

Open **http://\<device-ip\>:5000**. The two demo videos show gun detection boxes; RTSP cameras you entered appear as well.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| NPU or codec device node not found | Confirm the target runs the reComputer RK3576 OS image with Rockchip NPU/MPP drivers loaded (`ls /dev/rknpu /dev/dri`) |
| Insufficient disk space | At least 4 GB is needed; run `docker system prune -a` and `sudo apt clean` |
| Port 5000 already in use | Run `docker ps --filter publish=5000 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}'` first to inspect what is using port 5000, then stop only the intended container with `docker stop <container_name>` |
| Container keeps restarting | Run `docker compose -p gun-detection-rk3576 logs` in `~/gun-detection-rk3576/rk3576_deploy` to inspect NPU or runtime errors |
| RTSP camera not showing | Verify the URL in VLC, then edit `config/config.yml` as in step 3 and restart |

### Target {#rk3576_local type=local config=devices/rk3576_deploy.yaml}

Deploy on this machine. It must be a reComputer RK3576 with Docker, Rockchip NPU runtime, and at least 4 GB free disk.

### Wiring

1. Confirm Docker is running and NPU device nodes exist (e.g., `/dev/rknpu` or `/dev/dri`)
2. Optionally enter RTSP camera URLs (up to 2)
3. Click **Deploy**

### Deployment Complete

Open **http://localhost:5000**. The two demo videos show gun detection boxes; RTSP cameras you entered appear as well.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| NPU or codec device node not found | Confirm the machine runs the reComputer RK3576 OS image with Rockchip NPU/MPP drivers loaded (`ls /dev/rknpu /dev/dri`) |
| Port 5000 already in use | Run `docker ps --filter publish=5000 --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}'` first to inspect what is using port 5000, then stop only the intended container with `docker stop <container_name>` |
| Container keeps restarting | Run `docker compose -p gun-detection-rk3576 logs` in `~/gun-detection-rk3576/rk3576_deploy` to inspect NPU or runtime errors |

## Step 3: Open Dashboard {#dashboard_rk3576 type=web_dashboard required=true config=devices/dashboard.yaml}

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
cd ~/gun-detection-rk3576/rk3576_deploy
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
docker compose -p gun-detection-rk3576 restart
```

#### Next Steps

- Configure alerts over MQTT (port 1883)
- Adjust the detection threshold in `config/config.yml` (`objects.filters.gun.threshold`)
- Set recording retention (`record.retain.days`)
- [Frigate Documentation](https://docs.frigate.video/)

## Step 4: Deploy Home Assistant (Optional) {#deploy_ha_rk3576 type=docker_deploy required=false config=devices/ha_host.yaml}

Select this step only if Home Assistant is not installed yet. If Home Assistant is already running on port 8123 on the target host, the deployer detects it and skips installation automatically. If you already have a standalone HAOS or external Home Assistant instance, uncheck this step and proceed to Step 5.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Home Assistant already running on port 8123 | The deployer detects the running instance and skips installation; proceed to Step 5 |
| Local install fails on macOS or Windows | The container uses Docker host networking, which Docker Desktop disables by default on macOS and Windows (requires Docker Desktop 4.34+ with host networking manually enabled in Settings; otherwise deploy remotely via SSH to a Linux host or connect an existing Home Assistant instance) |

### Target: Deploy Locally {#ha_local_rk3576 type=local default=true}

Deploy Home Assistant on this machine via local Docker.

### Target: Deploy Remotely via SSH {#ha_remote_rk3576 type=remote}

Deploy Home Assistant on a remote Linux host (such as the reComputer RK3576 or another LAN server) over SSH.

## Step 5: Connect Frigate to Home Assistant (Optional) {#connect_ha_rk3576 type=ha_integration required=false config=devices/ha_integration_rk3576.yaml}

Connect Frigate to Home Assistant in one step. This step automatically installs the official `frigate-hass-integration` (`v5.15.7`, compatible with HAOS, local Docker HA, and remote Docker HA), restarts Home Assistant, configures both the Frigate and MQTT integrations, and creates the default persistent gun-detection alert automation (`gun_detection_ha_alert`).

### Prerequisites

- **Remote Docker HA:** Enter the HA host SSH credentials in the SSH section at the top and the HA Web UI administrator username and password below (a newly deployed HA instance is initialized automatically with this account). HAOS and local Docker HA do not require manually configuring an SSH Add-on.
- **Cross-host setup:** If Frigate is deployed locally (`localhost`) while Home Assistant runs on another device, replace the host address in `Frigate URL` and `MQTT Broker` with the Frigate device's LAN IP.
- **Existing MQTT integration:** If Home Assistant already has a configured and loaded MQTT integration, the engine reuses that existing connection without overwriting its broker address. Ensure Frigate (`mqtt.host` in `config/config.yml`) and Home Assistant point to the same MQTT broker, and verify in Home Assistant that `frigate/events` messages arrive before enabling alerts.
- **MQTT security:** The bundled Mosquitto broker started with Frigate allows anonymous LAN connections by default to simplify initial setup. For production deployments, configure Mosquitto username/password authentication and ACLs, and fill in `MQTT Username` and `MQTT Password` below.

### Deployment Complete

> **Warning:** Do not directly modify the auto-created `[Managed by SenseCraft: gun_detection_frigate] Gun Detection Alert` automation—redeploying this solution will overwrite managed automations and erase your changes.

To forward gun-detection alerts to your phone without losing your configuration on redeploy, use either option below:

1. **Create a separate custom automation:**
   In Home Assistant, open **Settings → Automations & Scenes → Create Automation → Create new automation**, switch to YAML mode, and create a standalone automation using the Frigate integration's proxied snapshot path `/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg` (so remote phones can load the snapshot through Home Assistant without exposing Frigate directly).

   **iOS Critical Alert example:**

   ```yaml
   alias: "Gun Detection Mobile Push (iOS)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo'] }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           push:
             sound:
               name: default
               critical: 1
               volume: 1.0
   ```

   **Android high-priority channel example:**

   ```yaml
   alias: "Gun Detection Mobile Push (Android)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo'] }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           ttl: 0
           priority: high
           channel: alarm_stream
   ```

   > **Note:** The examples above exclude the built-in demo cameras (`handgun_demo`, `machinegun_demo`) so looping demo videos do not flood your phone; to test mobile push notifications using the built-in demo videos, temporarily remove `and trigger.payload_json.get('after', {}).get('camera') not in ['handgun_demo', 'machinegun_demo']` from the condition.

2. **Use the community Blueprint:**
   Import the **Frigate Notifications Blueprint** in Home Assistant to visually select the camera, the `gun` label, target mobile devices, and critical-alert or silence action buttons. Because it is user-managed, it is preserved when you redeploy this solution.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Home Assistant login fails | Verify the HA Web UI administrator username and password and ensure port 8123 is reachable |
| Frigate or MQTT unreachable from HA | When HA and Frigate run on different hosts, set `Frigate URL` and `MQTT Broker` to the Frigate device's LAN IP instead of `localhost` |
| Existing HA MQTT integration does not receive `frigate/events` | When MQTT is already configured and loaded in HA, the engine reuses the existing connection instead of overwriting its broker address; ensure `mqtt.host` in Frigate's `config/config.yml` and HA point to the same broker, and verify `frigate/events` messages arrive in HA before enabling alerts |
