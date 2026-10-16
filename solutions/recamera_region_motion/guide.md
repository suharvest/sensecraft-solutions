## Preset: reCamera 2002 {#recamera_2002}

Install the region motion detector on a reCamera 2002. Detection runs on the camera and does not need an external model or cloud connection.

- **Device:** reCamera 2002 with network or USB SSH access.
- **Network:** the camera and the computer running SenseCraft Solution must be reachable over SSH.
- **Camera ownership:** only one camera pipeline can run at a time. The installer stops the stock ONVIF and SSCMA camera services while this app is active.

## Step 1: Install Motion Detection {#install_motion type=recamera_cpp required=true config=devices/recamera_motion.yaml}

Enter the camera address and SSH credentials. The installer transfers and installs the Debian package, then starts the service through the reCamera application manager.

### Target {#camera type=remote device_name="reCamera 2002" config=devices/recamera_motion.yaml default=true}

The USB connection usually uses `192.168.42.1`. For Wi-Fi or Ethernet, use the camera's current IP address. The default SSH user is `recamera`.

## Step 2: Check the Service {#verify_health type=http_debug required=true config=devices/verify_health.yaml}

Request `/api/health`. A successful response confirms that the HTTP service is running. The JSON response includes RTSP, snapshot, and webhook state.

### Deployment Complete

- HTTP API: `http://<camera-ip>:8080/api/health`
- RTSP stream: `rtsp://<camera-ip>:8554/live0`
- Home Assistant: install the [reCamera integration](https://github.com/yyling0101-a11y/recamera-ha) to draw regions, view snapshots, and receive alerts.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| SSH connection fails | Check the camera IP, USB cable or network, username, and password. |
| HTTP health check fails | Check the app status in Solution and inspect `/var/log/recamera-motion.log` on the camera. |
| Camera preview is unavailable | Stop this app from Solution before starting another app that uses the camera. |
