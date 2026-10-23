# Eldercare Safety Monitor Deployment Guide

Deploy an all-in-one edge eldercare safety monitoring system on reCamera Pro, integrating visual pose-based fall detection and offline voice distress recognition for zero-latency local alerts.

---

## Preset: reCamera Pro {#recamera_pro}

A single reCamera Pro camera performs video capture, YOLO11n-Pose estimation, SenseVoice offline speech recognition, and event dispatch.

## Step 1: Check or Flash Camera Firmware {#firmware_recamera_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

Required only once if your camera does not yet have the updated firmware containing the userdata mount guard (`RECAMERA_USERDATA_GUARD=1`) and App Center. Skip this step if already updated.

### Prerequisites & Verification

- Open `https://<device-ip>/` in your browser.
- Verify web console login and check that App Center is visible.
- If flashing is needed, download the official release image (`update.img.gz`) and flashing tool.
- Flash command: `sudo ./upgrade_tool uf update.img`.

### Troubleshooting

| Symptom | Action |
|---|---|
| upgrade_tool reports device not found | Verify USB Type-C connection and run `lsusb` to check for Rockchip USB IDs (e.g. `2207:110b`) |
| Cannot enter loader via adb | Ensure network connectivity or hold Recovery/BOOT button while powering on |

## Step 2: Deploy Eldercare Monitor {#deploy_recamera_pro_eldercare type=recamera_pro_app required=true config=devices/recamera_pro_eldercare.yaml}

The deployer inspects App Center on the device. If the app is missing, it automatically downloads and uploads the official signed package (`eldercare-monitor-0.1.5-arm64.tar.gz` and companion `.sig`), verifies and installs it, then configures and activates it.

### Deployment Notes

- **Single active app**: Activating this app stops any previously running app.
- **MQTT is optional**: Leave it empty to inspect results on the device web page; provide a host to forward alerts to Home Assistant or IoT brokers.
- Authentication uses the camera's **web console credentials** (default `admin`/`admin`).

### Target {#recamera_pro_device type=remote device_name="reCamera Pro" config=devices/recamera_pro_eldercare.yaml}

### Troubleshooting

| Symptom | Action |
|---|---|
| Login rejected | Repeated wrong passwords lock your IP. Verify web credentials before retrying |
| Signature verification error | Verify the presence and integrity of `eldercare-monitor-0.1.5-arm64.tar.gz.sig` |
| No detections on startup | Check application logs in App Center to ensure the camera sensor is not held by another process |

## Step 3: View Eldercare Monitor Dashboard {#verify_eldercare type=web_dashboard required=false config=devices/verify_eldercare.yaml}

Open the camera web console to observe skeleton pose overlays and voice recognition logs.

### Deployment Complete

- Navigate to `https://<device-ip>/`.
- Select Eldercare Monitor in App Center to inspect live skeleton pose tracking and voice distress logs.
- When a fall occurs or a distress phrase ("Help", "救命") is spoken, an alarm is triggered immediately and published over MQTT.

### Target {#verify_eldercare_device type=remote device_name="reCamera Pro" config=devices/verify_eldercare.yaml}
