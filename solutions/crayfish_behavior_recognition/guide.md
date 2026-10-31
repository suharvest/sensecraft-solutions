# Deployment Guide: Aquaculture Crayfish Behavior & Fighting Recognition

Deploy real-time edge AI crayfish fight/harassment detection, sex classification, and cannibalism risk monitoring on Seeed reCamera.

---

## Preset: reCamera Pro {#recamera_pro}

Autonomous 4-stage funnel vision pipeline running entirely on reCamera Pro (RV1126B 3 TOPS NPU), with 8-frame temporal verification mosaic and multi-frame sex voting.

## Step 1: Deploy Crayfish Behavior App {#deploy_recamera_pro_crayfish type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

The deployer inspects App Center on the reCamera Pro. It automatically downloads and uploads the official signed package (`crayfish-fight-v0.1.2-core.tar.gz`), installs, and activates it.

### Prerequisites

1. Connect reCamera Pro to your local network router via Ethernet, or connect via USB-C to your workstation.
2. Ensure the device IP is reachable (default HTTPS on port 443 with self-signed certificate).
3. Select your desired proximity factor for aggression triage.

### Deployment & Configuration

Enter the reCamera Pro address and web credentials (default user: `admin`). The system uploads the application package (`crayfish-fight-v0.1.2-core.tar.gz`), applies the configured parameters, and starts the service.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Login rejected or connection refused | The step logs in to the web console on HTTPS port 443 with the `admin` account. Check the device IP and the web console password. |
| App is not active after the step finishes | The deployer waits up to 90 s for activation. Confirm the computer can download the package (`crayfish-fight-v0.1.2-core.tar.gz`), then run the step again. |
| Browser shows a certificate warning | The camera uses a self-signed certificate on port 443; continue to the page. |

---

## Step 2: Verify Video Stream {#verify_stream_pro type=video_stream required=true verify=true}

Verify live video streaming and real-time crayfish behavior recognition overlay.

### Deployment Complete

- Open `https://<camera-ip>/` in your browser.
- Verify real-time crayfish detection bounding boxes, proximity interaction triggers, and behavioral classification events.

---

## Preset: reCamera 2002 {#recamera_2002}

Ultra-compact RISC-V edge camera running native SG2002 TPU BF16 models for crayfish detection and cascaded behavior alerts.

## Step 1: Deploy Crayfish Detector {#deploy_recamera_2002_crayfish type=recamera_cpp required=true config=devices/recamera_2002.yaml}

Installs native `crayfish_det_cv181x_bf16.cvimodel` and `crayfish_behavior_cv181x_bf16.cvimodel` alongside the C++ inference and alert daemon.

### Prerequisites

1. Connect reCamera 2002 via USB. Default IP is `192.168.42.1`.
2. Default SSH login: user `recamera`, password `recamera`.
3. Camera exclusivity: active conflicting video pipelines are automatically managed.

### Troubleshooting

| Symptom | Fix |
|---|---|
| SSH connection fails | Over USB use `192.168.42.1`; over Wi-Fi or Ethernet use the IP shown by your router. The SSH user is `recamera`. |
| Password rejected | Try `recamera.1` (pre-filled in the form) or `recamera`; earlier firmware uses `recamera.2`. |
| No video or detections after deployment | Only one camera pipeline runs at a time. Reboot the camera and run the step again. |

### Target {#recamera_2002_device type=remote device_name="reCamera 2002" config=devices/recamera_2002.yaml default=true}

Deploy to the reCamera 2002 device over SSH.

---

## Step 2: Verify Video Stream {#verify_stream_2002 type=video_stream required=true verify=true}

Verify camera video streaming and real-time detection overlay.

### Deployment Complete

- Open `http://<camera-ip>/` in your browser.
- Confirm live video stream display with detected crayfish bounding boxes and proximity alerts.
