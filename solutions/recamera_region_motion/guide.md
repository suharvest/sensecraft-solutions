## Preset: reCamera 2002 {#recamera_2002}

Install the native region motion detector on a reCamera 2002, and seamlessly integrate it with Home Assistant via MQTT. Detection runs directly on the camera without external models or cloud dependencies.

- **Device:** A reCamera 2002 reachable over network or USB SSH.
- **Home Assistant:** A local PC/server running Home Assistant, or an existing Home Assistant instance (HAOS or Docker).
- **Camera exclusivity:** Only one camera pipeline runs at a time. The console coordinates exclusive access before starting the detector.

## Step 1: Install Motion Detection {#install_motion type=recamera_cpp required=true config=devices/recamera_motion.yaml}

Provide the camera address and SSH credentials. The deployer transfers and installs the Debian package, cleans up legacy motion services if present, and starts the native region motion detection service.

### Prerequisites

1. Connect the reCamera via USB or join it to the same local network.
2. The USB connection defaults to `192.168.42.1`; for Wi-Fi use the IP assigned by your router.
3. Default password is `recamera` (or `recamera.2` on earlier firmware).

### Target {#camera type=remote device_name="reCamera 2002" config=devices/recamera_motion.yaml default=true}

USB connections typically use `192.168.42.1`. When using Wi-Fi or Ethernet, enter the camera's current IP address. The default SSH username is `recamera`.

---

## Step 2: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Deploy a canonical Home Assistant instance paired with an Eclipse Mosquitto MQTT broker.

If you already have an existing Home Assistant instance (such as HAOS on another machine) or an external MQTT broker, **skip or uncheck this optional step** and point reCamera to your existing broker address.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant and Mosquitto broker on the local machine. Requires Docker Desktop running with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. Ports 8123 (Home Assistant) and 1883 (Mosquitto) available.
3. If you already run Home Assistant or an MQTT broker elsewhere, skip this step.

### Deployment Complete

1. Open **http://localhost:8123** and complete the initial account onboarding.
2. In Home Assistant, navigate to **Settings -> Devices & Services -> Add Integration**, search for and select **MQTT**.
3. Set the broker address to `127.0.0.1` (or your host IP), port `1883`, leave username/password empty, and save.
4. Mosquitto is now ready to receive auto-discovery configs and detection events from reCamera.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 in use | Stop existing Home Assistant or Mosquitto instance, or skip this step to use the existing service |
| Docker fails to start | Launch Docker Desktop |
| Container crash loop | Ensure at least 2 GB of memory is available |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy Home Assistant and Mosquitto broker to a remote Linux host (e.g., reComputer) on the local network.

### Prerequisites

1. Target host reachable via SSH with Docker installed.
2. Ports 8123 and 1883 available on the target host.
3. Provide host IP, username, and password below.
4. If you already run Home Assistant or an MQTT broker elsewhere, skip this step.

### Deployment Complete

1. Open **http://<host-ip>:8123** and complete the initial account onboarding.
2. In Home Assistant, navigate to **Settings -> Devices & Services -> Add Integration**, search for and select **MQTT**.
3. Set the broker address to `<host-ip>` (or `127.0.0.1` if configuring within the remote host), port `1883`, leave username/password empty, and save.
4. In reCamera Console -> Integrations -> Home Assistant, enter `<host-ip>` and port `1883`.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check network connectivity with ping |
| SSH authentication failed | Verify username and password |
| Port 1883 in use | Existing broker detected; keep it and skip this step |

---

## Step 3: Verify Health & Live Preview {#verify_health type=http_debug required=true config=devices/verify_health.yaml}

Verify camera streaming and live snapshot availability.

### Deployment Complete

- **reCamera Console:** Open `http://<camera-ip>/` in your browser. Under the live view, configure detection parameters and draw polygon detection zones directly on screen.
- **Home Assistant Integration:** In reCamera Console -> Integrations -> Home Assistant, enter your MQTT Broker address (e.g. host IP on port 1883). Home Assistant will automatically discover the `binary_sensor.recamera_motion` entity without any custom plugins.
- **RTSP Stream:** `rtsp://<camera-ip>:8554/live0`
- **Live Snapshot:** `http://<camera-ip>:8001/snapshot.jpg`

### Troubleshooting

| Issue | Resolution |
|-------|------------|
| SSH connection failure | Verify the camera IP, USB cable or network, username, and password. |
| Health check failure | Ensure the device has finished boot and check `http://<camera-ip>:8001/snapshot.jpg` in your browser. |
| Camera preview unavailable | Verify the previous application has released the camera pipeline; reboot the device and re-check. |
