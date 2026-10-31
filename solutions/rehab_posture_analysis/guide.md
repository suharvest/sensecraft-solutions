## Preset: reCamera Pro {#recamera_pro}

Deploy the 33-keypoint clinical rehabilitation posture analysis application on reCamera Pro (RV1126B).
Leverages hardware RKNN INT8 NPU acceleration and renders real-time skeletal topology with an interactive HUD dashboard over Result Hub v2 WebSocket.

- **Hardware:** reCamera Pro (RV1126B) powered on and connected to the local network or host via USB/Ethernet.
- **Model:** Hardware-accelerated 33-keypoint YOLO11n-Pose INT8 model (`.rknn`).
- **Privacy:** 100% on-device edge processing. Video frames stay on the camera; only quantified kinematics and geometry primitives are emitted.

## Step 1: Deploy Rehab Posture Analysis {#deploy_rehab_pro type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

Install and activate the rehabilitation posture analysis application on reCamera Pro via its native App Center runtime.

### Prerequisites

1. Connect reCamera Pro to your local network router via Ethernet, or connect via USB-C to your workstation.
2. Ensure the device IP is reachable (default HTTPS on port 443 with self-signed certificate).
3. Select your desired target rehabilitation exercise (Squat, Shoulder Abduction, Bicep Curl, or Seated Knee Extension).

### Deployment & Configuration

Enter the reCamera Pro address and web credentials (default user: `admin`). The system uploads the application package (`rehab-posture-analysis-v0.1.0-core.tar.gz`), applies the configured exercise parameters, and starts the service.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Login rejected or connection refused | The step logs in to the web console on HTTPS port 443 with the `admin` account. Check the device IP and the web console password. |
| Wrong exercise is running | The exercise (Squat, Shoulder Abduction, Bicep Curl, Seated Knee Extension) is set in this step; run the step again with the intended exercise. |
| Browser shows a certificate warning | The camera uses a self-signed certificate on port 443; continue to the page. |

---

## Step 2: Open Rehab Live Dashboard {#verify_rehab_pro type=web_dashboard required=true config=devices/verify_recamera_pro.yaml}

Open the interactive Result Hub v2 dashboard to observe live skeletal tracking, joint angles, and real-time compensation alerts.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Page does not open | Use `https://<camera-ip>/#/apps/rehab-posture-analysis` and confirm Step 1 finished. Accept the self-signed certificate warning. |
| Not all 33 landmarks are tracked | Stand or sit 2.0-3.5 m from the camera so the whole body is in frame. |
| No compensation warning appears | Confirm the exercise selected in Step 1 matches the movement being performed. |

### Deployment Complete

- Open `https://<camera-ip>/#/apps/rehab-posture-analysis` in your modern web browser.
- **Patient Verification:** Stand or sit in front of the camera (2.0–3.5m away). Verify that all 33 anatomical landmarks (shoulders, elbows, wrists, hips, knees, ankles, heels, and toes) are tracked.
- **Kinematics & Repetitions:** Perform the selected exercise. Observe the real-time repetition counter, ROM angle gauge, and dynamic quality score (100.0 max).
- **Compensation Warning:** Trigger an intentional compensation (e.g. knee valgus or shoulder shrug) to verify that the joint turns red and an audible/visual guidance tip is presented.

---

## Preset: reCamera 2002 {#recamera_2002}

Deploy the rehabilitation kinematics tracking service on reCamera 2002 (SG2002 RISC-V 1GHz).
Runs the INT8 cvimodel on CVI TPU and outputs lightweight web stream / video OSD without consuming host PC compute.

- **Hardware:** reCamera 2002 (SG2002) connected via USB (default RNDIS `192.168.42.1`) or local Wi-Fi/Ethernet.
- **Memory Optimization:** Tailored for 256MB DDR3 RAM with zero-copy TPU execution.

## Step 1: Deploy Rehab Service on reCamera 2002 {#deploy_rehab_2002 type=recamera_cpp required=true config=devices/recamera_2002.yaml}

Transfer the INT8 cvimodel and launch the rehabilitation posture analysis service.

### Prerequisites

1. Connect reCamera 2002 via USB. Default IP is `192.168.42.1`.
2. Default SSH login: user `recamera`, password `recamera`.
3. Camera exclusivity: active conflicting video pipelines are automatically managed.

### Target {#camera_2002 type=remote device_name="reCamera 2002" config=devices/recamera_2002.yaml default=true}

Deploy to the reCamera 2002 device over SSH.

### Troubleshooting

| Symptom | Fix |
|---|---|
| SSH connection fails | Over USB use `192.168.42.1`; over Wi-Fi or Ethernet use the IP shown by your router. The SSH user is `recamera`. |
| Password rejected | Try `recamera.1` (pre-filled in the form) or `recamera`. |
| No video or metrics after deployment | Only one camera pipeline runs at a time. Reboot the camera and run the step again. |

---

## Step 2: Verify Video Stream & OSD {#verify_rehab_2002 type=web_dashboard required=true config=devices/verify_recamera_2002.yaml}

Verify camera video streaming and real-time rehabilitation kinematics overlay.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Page does not open | Use `http://<camera-ip>/` (HTTP, not HTTPS) and confirm Step 1 finished. |
| Joints or repetition metrics missing | Keep the whole body in frame and in good lighting. |

### Deployment Complete

- Open `http://<camera-ip>/` in your browser.
- Confirm live video stream display with 33 skeletal joints and real-time repetition/ROM metrics.
