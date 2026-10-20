## Preset: reCamera 2002 {#recamera_2002}

Install the region motion detector on a reCamera 2002. Detection runs directly on the camera without external models or cloud dependencies.

- **Device:** A reCamera 2002 reachable over network or USB SSH.
- **Network:** The host running SenseCraft Solution must be able to reach the camera over SSH.
- **Camera exclusivity:** Only one camera pipeline runs at a time. The console coordinates exclusive access before starting the detector.

## Step 1: Update reCamera Console {#update_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

Install console 0.5.6, which manages camera applications. Devices already at this version are skipped automatically.

### Prerequisites

1. Connect the reCamera via USB or join it to the same local network.
2. The USB connection defaults to `192.168.42.1`; for Wi-Fi use the IP assigned by your router.
3. Default password is `recamera` (or `recamera.2` on earlier firmware).

---

## Step 2: Install Motion Detection {#install_motion type=recamera_cpp required=true config=devices/recamera_motion.yaml}

Provide the camera address and SSH credentials. The deployer gracefully stops active camera services via the console API, transfers and installs the Debian package, then starts and verifies the motion detection service.

### Deploy Target {#camera type=remote device_name="reCamera 2002" config=devices/recamera_motion.yaml default=true}

USB connections typically use `192.168.42.1`. When using Wi-Fi or Ethernet, enter the camera's current IP address. The default SSH username is `recamera`.

---

## Step 3: Check Service & Live Snapshot {#verify_health type=http_debug required=true config=devices/verify_health.yaml}

Probe the service health endpoint, motion status, and camera snapshot. A successful response confirms both the HTTP daemon and video pipeline are streaming.

### Deployment Complete

- HTTP API: `http://<camera-ip>:8080/api/health`
- RTSP Stream: `rtsp://<camera-ip>:8554/live0`
- Live Snapshot: `http://<camera-ip>:8080/api/snapshot.jpg`
- Home Assistant: Install the [reCamera integration](https://github.com/yyling0101-a11y/recamera-ha) to draw detection regions, inspect snapshots, and receive alerts.

### Troubleshooting

| Issue | Resolution |
|-------|------------|
| SSH connection failure | Verify the camera IP, USB cable or network, username, and password. |
| Health check failure | Inspect the application status in Solution and check `/var/log/recamera-motion.log` on the camera. |
| Camera preview unavailable | Verify the previous application has released the camera pipeline; reboot the device and re-check. |
