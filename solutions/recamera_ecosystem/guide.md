## Preset: Object Detection & Environment {#object_detection}

Experience foundational edge vision capabilities — YOLO general object detection and weather classification. Observe bounding boxes and confidence score changes over a low-latency WebRTC stream.

- **Devices:** reCamera (SG2002) or reCamera Pro (RV1126B); a PC or reComputer R1100 when forwarding to Home Assistant.
- **Recommended Apps:** `yolo-detector` (80 common object classes) or `weather-classifier` (weather condition detection).
- **Hands-on Quests:**
  1. Hold a phone, bottle, or hand into the frame; observe bounding boxes and class labels rendered in ~50ms;
  2. Slowly move the object or partially occlude it to see how confidence scores react.

## Step 1: Upgrade reCamera Console (SG2002) {#obj_deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

Install console version 0.5.5. Existing 0.5.5 installations will be skipped automatically. If using reCamera Pro, skip directly to Step 4.

### Prerequisites

1. Connect the camera over USB (address `192.168.42.1`) or place it on the same network.
2. Username `recamera`, default password `recamera` (older firmware uses `recamera.2`).
3. For brand new units, enable SSH under `http://192.168.42.1/#/security` first.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection failed | Use `192.168.42.1` over USB; check router DHCP list over network |
| Wrong password | Default is `recamera` (older firmware uses `recamera.2`) |
| Installation failed | Reboot camera and rerun this step |
| Node-RED unavailable | Console takes over the camera; switch back under Console System Settings |
| Factory reset | Hold **User** button while powering up until red LED turns solid |

---

## Step 2: Install Object Detection App (SG2002) {#obj_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select **Object Detection (yolo-detector)** or **Weather Classification (weather-classifier)** from the dropdown and click **Deploy**.

### Prerequisites

1. Your PC needs internet access to fetch packages; the camera itself does not need internet.
2. IP address and password match Step 1.
3. Packages and models range from tens to hundreds of megabytes; progress is shown on screen.

### Deployment Complete

The camera is running the selected object detection app. ONVIF and RTSP streams are active for NVR or VMS discovery.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dropdown empty | PC cannot reach `sensecraft-statics.seeed.cc`; fix connection and refresh |
| Login rejected | Use camera credentials `recamera` / `recamera` (or `recamera.2`) |
| Console busy | Camera is handling another operation; retry in a minute |
| Failed to start | Check status in console Applications tab; redeploy if files are missing |

---

## Step 3: Open Console & Debug View (SG2002) {#obj_open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera console to inspect the real-time inference video feed and detection metrics.

### Prerequisites

1. Log in with camera credentials from Step 1.
2. In the **Applications** tab, click **Debug** on the running app to see the live feed and bounding boxes.
3. Wave items in front of the lens to check confidence and inference latency.

### Deployment Complete

Console URL is `http://<camera-ip>/` for streaming, threshold tuning, and networking setup.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Wait 60s for camera reboot to finish, then refresh |
| Black video stream | No app is active; return to Step 2 to deploy an app |

---

## Step 4: Check & Update Firmware (reCamera Pro) {#obj_firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

For reCamera Pro users only. Skip if your camera already displays the App Center.

### Prerequisites

1. Open camera web page; if App Center is present, skip this step.
2. Fill in device IP and ADB port 5555, then click **Check & Update Device**.

---

## Step 5: Launch Object Detection (reCamera Pro) {#obj_open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

Open reCamera Pro App Center, install and start the object detection app.

### Prerequisites

1. Log in with camera panel credentials.
2. Open **App Center** from sidebar, select object detection app, and click **Start**.
3. View live video and detection results in **Live Preview**.

---

## Step 6: Deploy Home Assistant (Optional) {#obj_deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Launch Home Assistant and an MQTT broker container. Skip if already running.

### Target {#obj_ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant locally on Docker Desktop with ports 8123 and 1883 available.

### Target {#obj_ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote edge host (e.g. reComputer) on the local network.

---

## Step 7: Connect Camera to Home Assistant (Optional) {#obj_connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Connect camera and Home Assistant to the same MQTT broker for automatic entity discovery.

### Prerequisites

1. Home Assistant is accessible.
2. Enter broker IP and port 1883 in camera console Integrations page.

---

## Step 8: View Results in Home Assistant (Optional) {#obj_ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Add a Picture glance card to display the live RTSP stream alongside detection entity badges.

---

## Preset: Human Behavior & Pose {#human_behavior}

Advanced edge vision: landmark tracking, skeletal pose estimation, and on-device privacy protection (local face blur).

- **Devices:** reCamera (SG2002) or reCamera Pro (RV1126B); a PC or reComputer R1100 when forwarding to Home Assistant.
- **Recommended Apps:** `face-analysis` (attributes and privacy blur), `facemesh-reader` (drowsiness), `fall-detection` (fall alert), `fitness-trainer` (rep counting).
- **Hands-on Quests:**
  1. Close eyes for 3 seconds or yawn to see how 468 facial landmarks trigger a drowsiness alert;
  2. Enable Privacy Blur and observe how faces are blurred on-device before RTSP streaming.

## Step 1: Upgrade reCamera Console (SG2002) {#human_deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

Install console version 0.5.5. Existing 0.5.5 installations will be skipped automatically. If using reCamera Pro, skip directly to Step 4.

### Prerequisites

1. Connect camera over USB (`192.168.42.1`) or LAN IP.
2. Username `recamera`, default password `recamera`.

---

## Step 2: Install Human Behavior App (SG2002) {#human_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select **Face Analysis (face-analysis)**, **Drowsiness Detection (facemesh-reader)**, **Fall Detection (fall-detection)**, or **Fitness Trainer (fitness-trainer)** and deploy.

### Prerequisites

1. PC has internet connectivity; camera operates offline.
2. Privacy blur can be enabled under console settings after deployment.

---

## Step 3: Open Console & Debug View (SG2002) {#human_open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open debug view in camera console to monitor facial landmarks, skeletal pose lines, and exercise counters.

---

## Step 4: Check & Update Firmware (reCamera Pro) {#human_firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

For reCamera Pro users only. Skip if App Center is already present.

---

## Step 5: Launch Human Behavior App (reCamera Pro) {#human_open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

Open reCamera Pro App Center and launch the desired human behavior or pose tracking app.

---

## Step 6: Deploy Home Assistant (Optional) {#human_deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Launch Home Assistant and MQTT broker. Skip if already running.

### Target {#human_ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant locally.

### Target {#human_ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote host.

---

## Step 7: Connect Camera to Home Assistant (Optional) {#human_connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Configure MQTT forwarding to publish face attributes, drowsiness alerts, or fall events into Home Assistant.

---

## Step 8: View Results in Home Assistant (Optional) {#human_ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Add Picture glance cards overlaying fall alerts or person presence badges over the video stream.

---

## Preset: Text & Code Reading {#text_reading}

Two-stage edge vision pipeline: text line localization + CRNN character recognition, plus dense multi-QR decoding.

- **Devices:** reCamera (SG2002) or reCamera Pro (RV1126B); a PC or reComputer R1100 when forwarding to Home Assistant.
- **Recommended Apps:** `ppocr-reader` (Chinese & English OCR) or `qrcode-reader` (QR & barcode reader).
- **Hands-on Quests:**
  1. Hold a badge, business card, or product packaging 15–25 cm in front of the lens; observe text slices extracted to JSON strings in real time;
  2. Display QR codes on your phone to verify multi-code batch decoding.

## Step 1: Upgrade reCamera Console (SG2002) {#text_deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

Install console version 0.5.5. Existing 0.5.5 installations will be skipped automatically. If using reCamera Pro, skip directly to Step 4.

### Prerequisites

1. Connect camera over USB (`192.168.42.1`).
2. Username `recamera`, default password `recamera`.

---

## Step 2: Install Text Reading App (SG2002) {#text_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select **OCR Text Reader (ppocr-reader)** or **QR Code Reader (qrcode-reader)** and click Deploy.

### Prerequisites

1. PC has internet access; camera does not require internet.
2. PP-OCR includes embedded dictionary for alphanumeric and Chinese characters.

---

## Step 3: Open Console & Debug View (SG2002) {#text_open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open console debug view and hold text or barcodes in front of the lens to observe recognized text blocks.

---

## Step 4: Check & Update Firmware (reCamera Pro) {#text_firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

For reCamera Pro users only. Skip if App Center is present.

---

## Step 5: Launch Text Reading App (reCamera Pro) {#text_open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

Open reCamera Pro App Center and launch the text or barcode recognition app.

---

## Step 6: Deploy Home Assistant (Optional) {#text_deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Launch Home Assistant and MQTT broker. Skip if already running.

### Target {#text_ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant locally.

### Target {#text_ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote host.

---

## Step 7: Connect Camera to Home Assistant (Optional) {#text_connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Configure MQTT forwarding to push recognized text or barcode content into Home Assistant sensors.

---

## Step 8: View Results in Home Assistant (Optional) {#text_ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Display real-time scanned text values inside Home Assistant dashboard entity cards.

---

## Preset: Spatial Vision & Retail Flow {#spatial_retail}

Relative 3D monocular depth estimation, alongside ByteTrack multi-target tracking and virtual tripwire line-crossing analytics for retail.

- **Devices:** reCamera (SG2002) or reCamera Pro (RV1126B); a PC or reComputer R1100 when forwarding to Home Assistant.
- **Recommended Apps:** `depth-estimation` (monocular depth) or `retail-vision` (passenger flow & dwell time).
- **Hands-on Quests:**
  1. In depth mode, push your hand from far to near; observe color shifting from cool blue (far) to warm red (near);
  2. In retail mode, set a virtual line to see entry/exit counts increment as someone walks across.

## Step 1: Upgrade reCamera Console (SG2002) {#spatial_deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

Install console version 0.5.5. Existing 0.5.5 installations will be skipped automatically. If using reCamera Pro, skip directly to Step 4.

### Prerequisites

1. Connect camera over USB (`192.168.42.1`).
2. Username `recamera`, default password `recamera`.

---

## Step 2: Install Spatial & Retail App (SG2002) {#spatial_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select **Monocular Depth Estimation (depth-estimation)** or **Retail People Counting (retail-vision)** and click Deploy.

### Prerequisites

1. PC has internet access; camera operates offline.
2. Retail app includes embedded ByteTrack multi-target tracking and tripwire logic.

---

## Step 3: Open Console & Debug View (SG2002) {#spatial_open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open camera console to inspect the real-time depth heatmap or customer counting overlays.

---

## Step 4: Check & Update Firmware (reCamera Pro) {#spatial_firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

For reCamera Pro users only. Skip if App Center is present.

---

## Step 5: Launch Spatial & Retail App (reCamera Pro) {#spatial_open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

Open reCamera Pro App Center and launch the depth estimation or retail counting app.

---

## Step 6: Deploy Home Assistant (Optional) {#spatial_deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Launch Home Assistant and MQTT broker. Skip if already running.

### Target {#spatial_ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant locally.

### Target {#spatial_ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote host.

---

## Step 7: Connect Camera to Home Assistant (Optional) {#spatial_connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Configure MQTT forwarding to stream footfall counts and proximity matrix data into Home Assistant.

---

## Step 8: View Results in Home Assistant (Optional) {#spatial_ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Add history graphs and statistics cards to track customer traffic over time.
