## Preset: reCamera 2002W {#recamera_2002}

Install the ONVIF gateway, then preview the same RTSP stream that your NVR or Home Assistant will use.

## Step 1: Install ONVIF Gateway {#deploy_onvif type=recamera_cpp required=true config=devices/recamera_onvif.yaml}

Install the gateway and start its managed camera service.

### Prerequisites

1. Connect the reCamera by USB or put it on the same network as this computer.
2. Enable SSH in the camera's security page if it is a new device.
3. Stop any other application currently using the camera before deployment.

### Wiring

1. Connect the reCamera to this computer by USB-C, or connect it to the same LAN.
2. Wait until the camera has finished booting, then enter its IP address and SSH password in the deployment form.
3. Click Deploy. SenseCraft installs the package under `/userdata` and starts the managed ONVIF service.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection fails | Use `192.168.42.1` over USB, or enter the camera IP shown by your router. |
| Service does not start | Check `/var/log/recamera-onvif.log`; another camera application may still own the device. |

## Step 2: Preview ONVIF Stream {#preview_onvif type=video_stream required=true verify=true config=devices/rtsp_preview.yaml}

Open the authenticated RTSP stream and confirm that live video is visible.

### Deployment Complete

Use these values in your NVR, VMS, or Home Assistant ONVIF integration:

| Setting | Value |
|---------|-------|
| ONVIF service | `http://<camera-ip>:8000/onvif/device_service` |
| Discovery | WS-Discovery on UDP port `3702` |
| RTSP stream | `rtsp://admin:recamera.1@<camera-ip>:8554/onvif` |
| Username | `admin` |
| Password | `recamera.1` |

For Home Assistant, add an ONVIF integration and enter the camera IP, port `8000`, and the credentials above. For an NVR or VMS, run its ONVIF discovery first; if multicast discovery is unavailable across VLANs, add the ONVIF service URL manually.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No video in the preview | Wait for the camera service to start, then retry. Check that another camera app is not active. |
| NVR cannot discover the camera | Confirm both devices are on the same multicast network, or add the ONVIF URL manually. |
| Authentication is rejected | Use `admin` and `recamera.1` exactly as shown. |
