## Preset: Object Detection & Environment {#object_detection}

Experience foundational edge vision capabilities — YOLO general object detection and weather classification. Observe bounding boxes and confidence score changes over a low-latency WebRTC stream.

- **Devices:** reCamera (SG2002) or reCamera Pro (RV1126B); a PC or reComputer R1100 when forwarding to Home Assistant.
- **Recommended Apps:** `yolo-detector` (80 common object classes) or `weather-classifier` (weather condition detection).
- **Hands-on Quests:**
  1. Hold a phone, bottle, or hand into the frame; observe bounding boxes and class labels rendered in ~50ms;
  2. Slowly move the object or partially occlude it to see how confidence scores react.

## Step 1: Upgrade reCamera Console (SG2002) {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

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

## Step 3: Open Console & Debug View (SG2002) {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera console to inspect the real-time inference video feed and detection metrics.

### Prerequisites

1. Log in with camera credentials from Step 1.
2. In the **Applications** tab, click **Debug** on the running app to see the live feed and bounding boxes.

### Deployment Complete

Console URL is `http://<camera-ip>/` for streaming, threshold tuning, and networking setup.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Wait 60s for camera reboot to finish, then refresh |
| Black video stream | No app is active; return to Step 2 to deploy an app |

---

## Step 4: Check & Update Firmware (reCamera Pro) {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

For reCamera Pro users only. Skip if your camera already displays the App Center.

### Prerequisites

1. Open camera web page; if App Center is present, skip this step.
2. Fill in device IP and ADB port 5555, then click **Check & Update Device**.
3. Firmware update runs over network ADB port 5555; USB alone is not sufficient.
4. The camera reboots during update; do not power off. Use **Factory Reset** on the same page to roll back.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test connection fails | Check address and verify port 5555 is reachable from this PC |
| Nothing happens on check | Camera may already be on latest firmware; look for App Center on its page |
| App Center missing after reboot | Reload the page after camera finishes rebooting |

---

## Step 5: Open App Center (reCamera Pro) {#open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

For reCamera Pro users only. Open App Center, install and start the corresponding application.

### Prerequisites

1. Log in with camera panel credentials (not SSH credentials).
2. Open **App Center** from sidebar, select the target application to install, and click **Start**.
3. View live video and detection results in **Live Preview**.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Prefix URL with `http://` to allow proper redirection |
| Certificate warning | Camera uses a self-signed certificate over HTTPS; accept and proceed |
| App Center empty or asks to sign in | Log in to the management dashboard first, then refresh |
| Failed to load catalog | PC cannot reach `sensecraft-statics.seeed.cc`; update catalog URL if self-hosting |
| App fails to start | Model files missing; reinstall the application |

---

## Step 6: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Launch Home Assistant and an MQTT broker container. Skip if already running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant locally on Docker Desktop with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk space.
3. Ports 8123 and 1883 available.

### Deployment Complete

1. Open **http://localhost:8123** and complete the onboarding wizard.
2. MQTT broker listens on port 1883; use this address in Steps 7 & 8.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port 8123 or 1883 busy | Stop existing Home Assistant / Mosquitto containers, or reuse them |
| Docker not running | Launch Docker Desktop application |
| Container restarting | Ensure at least 2 GB of RAM is free |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote edge host (e.g. reComputer) on the local network.

### Prerequisites

1. Target host is reachable over SSH with Docker running.
2. Enter IP address, username, and password below.

### Deployment Complete

1. Open **http://<device-ip>:8123** and complete the onboarding wizard.
2. MQTT broker listens on port 1883 of the remote device; use this address in Steps 7 & 8.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection timeout | Check local network and ping device |
| SSH auth failed | Verify username and password |
| Port 1883 busy | An MQTT broker is already running; retain it and enter its port in Steps 7 & 8 |

---

## Step 7: Connect reCamera to Home Assistant (Optional) {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Connect reCamera (SG2002) and Home Assistant to the same MQTT broker for automatic entity discovery.

### Prerequisites

1. Home Assistant is running and accessible.
2. An MQTT broker reachable by the camera (from Step 6 or external).
3. In camera console: under **Integrations → Home Assistant**, enter broker IP and port 1883.

### Deployment Complete

Detections publish as Home Assistant entities. If entities show unavailable, verify the app is running in the camera console.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No data on broker | Verify broker IP is correct and reachable from camera subnet |
| Entity stays unavailable | Confirm application is active and running in console |

---

## Step 8: Connect reCamera Pro to Home Assistant (Optional) {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

Configure MQTT output in reCamera Pro app settings; entities will appear automatically in Home Assistant.

### Prerequisites

1. Home Assistant is running and accessible.
2. An MQTT broker reachable by reCamera Pro (from Step 6 or external).
3. The AI app is active and running on the camera.

### Deployment Complete

Detections appear in Home Assistant. This configuration applies to the active app; repeat in Configure when switching to another app.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No Result Output in config | App does not support MQTT output; detections remain local |
| No broker messages | Verify broker address is non-empty and reachable from camera |
| Save rejected | Broker host cannot be empty; base topic cannot contain `+`, `#` or spaces |
| Saved but nothing in HA | Set Output Mode to **Home Assistant** and confirm identical broker settings |
| Entity unavailable | Verify application is currently running in App Center |

---

## Step 9: See reCamera Results in Home Assistant (Optional) {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

View reCamera (SG2002) video stream and detection entities on your Home Assistant dashboard.

### Prerequisites

1. **Find Entities:** Under **Settings → Devices & Services → MQTT**, locate the camera device and note entities.
2. **Add Card:** Add a **Picture glance** card on your dashboard, combining the video stream with detection entities.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Card shows video but no icons | Verify Home Assistant integration status in camera console |
| Entity shows unknown | Values update upon changes detected in the camera view |

---

## Step 10: See reCamera Pro Results in Home Assistant (Optional) {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

Combine reCamera Pro video stream and detection entities on a single dashboard card.

### Prerequisites

1. **Find Entities:** Under **Settings → Devices & Services → MQTT**, locate camera entities.
2. **Enable RTSP:** In camera panel: **Live View → Stream Settings**, select RTSP, enable stream, and copy the RTSP URL.
3. **Add Camera:** In Home Assistant: **Settings → Devices & Services → Add Integration → Generic Camera**, paste RTSP URL, set transport to **TCP**.
4. **Build Card:** On dashboard, add a **Picture glance** card pointing to Generic Camera with detection entities listed.

### Deployment Complete

Dashboard displays real-time camera video with overlaid detection entities.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No RTSP stream URL | RTSP not enabled or another protocol selected |
| Generic Camera cannot connect | Test URL with VLC; ensure TCP transport is selected |
| Black or freezing video | Close camera web preview and any open VLC players |
| No detection icons on card | Confirm MQTT output is configured on active app (Step 8) |
| Entity shows unknown | Values update upon new detections in camera frame |

---

## Preset: Human Behavior & Pose {#human_behavior}

Explore advanced keypoint topology and temporal action recognition. Learn facial landmark detection (FaceMesh), skeletal pose estimation, on-device privacy masking, and state-machine-driven action tracking.

- **Devices:** reCamera (SG2002) or reCamera Pro (RV1126B); a PC or reComputer R1100 when forwarding to Home Assistant.
- **Recommended Apps:** `face-analysis` (demographics & privacy blur), `facemesh-reader` (drowsiness detection), `fall-detection` (fall alarm), `fitness-trainer` (rep counter).
- **Hands-on Quests:**
  1. Close eyes for 3 seconds or simulate yawning to trigger the drowsiness alert via 468 facial landmarks;
  2. Enable Privacy Blur mode in the console and verify faces are Gaussian-blurred on-device before streaming.

## Step 1: Upgrade reCamera Console (SG2002) {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

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

## Step 2: Install Human Behavior App (SG2002) {#human_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select **Face Analysis (face-analysis)**, **Drowsiness Detection (facemesh-reader)**, **Fall Detection (fall-detection)**, or **Fitness Trainer (fitness-trainer)** and click **Deploy**.

### Prerequisites

1. PC needs internet access to fetch packages; the camera does not need internet.
2. For privacy blur experimentation, enable Privacy Blur in console system settings after deployment.

### Deployment Complete

The camera is running the human behavior analysis app.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dropdown empty | PC cannot reach `sensecraft-statics.seeed.cc`; fix connection and refresh |
| Login rejected | Use camera credentials `recamera` / `recamera` (or `recamera.2`) |
| Console busy | Camera is handling another operation; retry in a minute |
| Failed to start | Check status in console Applications tab; redeploy if files are missing |

---

## Step 3: Open Console & Debug View (SG2002) {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera console to inspect the real-time inference video feed and detection metrics.

### Prerequisites

1. Log in with camera credentials from Step 1.
2. In the **Applications** tab, click **Debug** on the running app to see the live feed and bounding boxes.

### Deployment Complete

Console URL is `http://<camera-ip>/` for streaming, threshold tuning, and networking setup.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Wait 60s for camera reboot to finish, then refresh |
| Black video stream | No app is active; return to Step 2 to deploy an app |

---

## Step 4: Check & Update Firmware (reCamera Pro) {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

For reCamera Pro users only. Skip if your camera already displays the App Center.

### Prerequisites

1. Open camera web page; if App Center is present, skip this step.
2. Fill in device IP and ADB port 5555, then click **Check & Update Device**.
3. Firmware update runs over network ADB port 5555; USB alone is not sufficient.
4. The camera reboots during update; do not power off. Use **Factory Reset** on the same page to roll back.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test connection fails | Check address and verify port 5555 is reachable from this PC |
| Nothing happens on check | Camera may already be on latest firmware; look for App Center on its page |
| App Center missing after reboot | Reload the page after camera finishes rebooting |

---

## Step 5: Open App Center (reCamera Pro) {#open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

For reCamera Pro users only. Open App Center, install and start the corresponding application.

### Prerequisites

1. Log in with camera panel credentials (not SSH credentials).
2. Open **App Center** from sidebar, select the target application to install, and click **Start**.
3. View live video and detection results in **Live Preview**.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Prefix URL with `http://` to allow proper redirection |
| Certificate warning | Camera uses a self-signed certificate over HTTPS; accept and proceed |
| App Center empty or asks to sign in | Log in to the management dashboard first, then refresh |
| Failed to load catalog | PC cannot reach `sensecraft-statics.seeed.cc`; update catalog URL if self-hosting |
| App fails to start | Model files missing; reinstall the application |

---

## Step 6: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Launch Home Assistant and an MQTT broker container. Skip if already running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant locally on Docker Desktop with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk space.
3. Ports 8123 and 1883 available.

### Deployment Complete

1. Open **http://localhost:8123** and complete the onboarding wizard.
2. MQTT broker listens on port 1883; use this address in Steps 7 & 8.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port 8123 or 1883 busy | Stop existing Home Assistant / Mosquitto containers, or reuse them |
| Docker not running | Launch Docker Desktop application |
| Container restarting | Ensure at least 2 GB of RAM is free |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote edge host (e.g. reComputer) on the local network.

### Prerequisites

1. Target host is reachable over SSH with Docker running.
2. Enter IP address, username, and password below.

### Deployment Complete

1. Open **http://<device-ip>:8123** and complete the onboarding wizard.
2. MQTT broker listens on port 1883 of the remote device; use this address in Steps 7 & 8.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection timeout | Check local network and ping device |
| SSH auth failed | Verify username and password |
| Port 1883 busy | An MQTT broker is already running; retain it and enter its port in Steps 7 & 8 |

---

## Step 7: Connect reCamera to Home Assistant (Optional) {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Connect reCamera (SG2002) and Home Assistant to the same MQTT broker for automatic entity discovery.

### Prerequisites

1. Home Assistant is running and accessible.
2. An MQTT broker reachable by the camera (from Step 6 or external).
3. In camera console: under **Integrations → Home Assistant**, enter broker IP and port 1883.

### Deployment Complete

Detections publish as Home Assistant entities. If entities show unavailable, verify the app is running in the camera console.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No data on broker | Verify broker IP is correct and reachable from camera subnet |
| Entity stays unavailable | Confirm application is active and running in console |

---

## Step 8: Connect reCamera Pro to Home Assistant (Optional) {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

Configure MQTT output in reCamera Pro app settings; entities will appear automatically in Home Assistant.

### Prerequisites

1. Home Assistant is running and accessible.
2. An MQTT broker reachable by reCamera Pro (from Step 6 or external).
3. The AI app is active and running on the camera.

### Deployment Complete

Detections appear in Home Assistant. This configuration applies to the active app; repeat in Configure when switching to another app.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No Result Output in config | App does not support MQTT output; detections remain local |
| No broker messages | Verify broker address is non-empty and reachable from camera |
| Save rejected | Broker host cannot be empty; base topic cannot contain `+`, `#` or spaces |
| Saved but nothing in HA | Set Output Mode to **Home Assistant** and confirm identical broker settings |
| Entity unavailable | Verify application is currently running in App Center |

---

## Step 9: See reCamera Results in Home Assistant (Optional) {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

View reCamera (SG2002) video stream and detection entities on your Home Assistant dashboard.

### Prerequisites

1. **Find Entities:** Under **Settings → Devices & Services → MQTT**, locate the camera device and note entities.
2. **Add Card:** Add a **Picture glance** card on your dashboard, combining the video stream with detection entities.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Card shows video but no icons | Verify Home Assistant integration status in camera console |
| Entity shows unknown | Values update upon changes detected in the camera view |

---

## Step 10: See reCamera Pro Results in Home Assistant (Optional) {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

Combine reCamera Pro video stream and detection entities on a single dashboard card.

### Prerequisites

1. **Find Entities:** Under **Settings → Devices & Services → MQTT**, locate camera entities.
2. **Enable RTSP:** In camera panel: **Live View → Stream Settings**, select RTSP, enable stream, and copy the RTSP URL.
3. **Add Camera:** In Home Assistant: **Settings → Devices & Services → Add Integration → Generic Camera**, paste RTSP URL, set transport to **TCP**.
4. **Build Card:** On dashboard, add a **Picture glance** card pointing to Generic Camera with detection entities listed.

### Deployment Complete

Dashboard displays real-time camera video with overlaid detection entities.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No RTSP stream URL | RTSP not enabled or another protocol selected |
| Generic Camera cannot connect | Test URL with VLC; ensure TCP transport is selected |
| Black or freezing video | Close camera web preview and any open VLC players |
| No detection icons on card | Confirm MQTT output is configured on active app (Step 8) |
| Entity shows unknown | Values update upon new detections in camera frame |

---

## Preset: Text & Code Reading {#text_reading}

Learn two-stage vision pipelines (text localization + OCR character recognition) and dense QR barcode decoding on resource-constrained edge hardware.

- **Devices:** reCamera (SG2002) or reCamera Pro (RV1126B); a PC or reComputer R1100 when forwarding to Home Assistant.
- **Recommended Apps:** `ppocr-reader` (bilingual OCR text recognition) or `qrcode-reader` (dense QR decoding).
- **Hands-on Quests:**
  1. Hold a business card, ID badge, or parcel label 15~25 cm in front of the lens; observe printed text cropped and output as JSON;
  2. Present multiple QR codes simultaneously to watch instantaneous parallel decoding.

## Step 1: Upgrade reCamera Console (SG2002) {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

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

## Step 2: Install Text Reading App (SG2002) {#text_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select **OCR Text Reader (ppocr-reader)** or **QR Code Reader (qrcode-reader)** and click **Deploy**.

### Prerequisites

1. PC needs internet access to fetch packages; the camera does not need internet.
2. The PP-OCR model includes common Chinese and English character libraries.

### Deployment Complete

The camera is running the text and code recognition app.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dropdown empty | PC cannot reach `sensecraft-statics.seeed.cc`; fix connection and refresh |
| Login rejected | Use camera credentials `recamera` / `recamera` (or `recamera.2`) |
| Console busy | Camera is handling another operation; retry in a minute |
| Failed to start | Check status in console Applications tab; redeploy if files are missing |

---

## Step 3: Open Console & Debug View (SG2002) {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera console to inspect the real-time inference video feed and detection metrics.

### Prerequisites

1. Log in with camera credentials from Step 1.
2. In the **Applications** tab, click **Debug** on the running app to see the live feed and bounding boxes.

### Deployment Complete

Console URL is `http://<camera-ip>/` for streaming, threshold tuning, and networking setup.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Wait 60s for camera reboot to finish, then refresh |
| Black video stream | No app is active; return to Step 2 to deploy an app |

---

## Step 4: Check & Update Firmware (reCamera Pro) {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

For reCamera Pro users only. Skip if your camera already displays the App Center.

### Prerequisites

1. Open camera web page; if App Center is present, skip this step.
2. Fill in device IP and ADB port 5555, then click **Check & Update Device**.
3. Firmware update runs over network ADB port 5555; USB alone is not sufficient.
4. The camera reboots during update; do not power off. Use **Factory Reset** on the same page to roll back.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test connection fails | Check address and verify port 5555 is reachable from this PC |
| Nothing happens on check | Camera may already be on latest firmware; look for App Center on its page |
| App Center missing after reboot | Reload the page after camera finishes rebooting |

---

## Step 5: Open App Center (reCamera Pro) {#open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

For reCamera Pro users only. Open App Center, install and start the corresponding application.

### Prerequisites

1. Log in with camera panel credentials (not SSH credentials).
2. Open **App Center** from sidebar, select the target application to install, and click **Start**.
3. View live video and detection results in **Live Preview**.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Prefix URL with `http://` to allow proper redirection |
| Certificate warning | Camera uses a self-signed certificate over HTTPS; accept and proceed |
| App Center empty or asks to sign in | Log in to the management dashboard first, then refresh |
| Failed to load catalog | PC cannot reach `sensecraft-statics.seeed.cc`; update catalog URL if self-hosting |
| App fails to start | Model files missing; reinstall the application |

---

## Step 6: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Launch Home Assistant and an MQTT broker container. Skip if already running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant locally on Docker Desktop with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk space.
3. Ports 8123 and 1883 available.

### Deployment Complete

1. Open **http://localhost:8123** and complete the onboarding wizard.
2. MQTT broker listens on port 1883; use this address in Steps 7 & 8.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port 8123 or 1883 busy | Stop existing Home Assistant / Mosquitto containers, or reuse them |
| Docker not running | Launch Docker Desktop application |
| Container restarting | Ensure at least 2 GB of RAM is free |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote edge host (e.g. reComputer) on the local network.

### Prerequisites

1. Target host is reachable over SSH with Docker running.
2. Enter IP address, username, and password below.

### Deployment Complete

1. Open **http://<device-ip>:8123** and complete the onboarding wizard.
2. MQTT broker listens on port 1883 of the remote device; use this address in Steps 7 & 8.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection timeout | Check local network and ping device |
| SSH auth failed | Verify username and password |
| Port 1883 busy | An MQTT broker is already running; retain it and enter its port in Steps 7 & 8 |

---

## Step 7: Connect reCamera to Home Assistant (Optional) {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Connect reCamera (SG2002) and Home Assistant to the same MQTT broker for automatic entity discovery.

### Prerequisites

1. Home Assistant is running and accessible.
2. An MQTT broker reachable by the camera (from Step 6 or external).
3. In camera console: under **Integrations → Home Assistant**, enter broker IP and port 1883.

### Deployment Complete

Detections publish as Home Assistant entities. If entities show unavailable, verify the app is running in the camera console.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No data on broker | Verify broker IP is correct and reachable from camera subnet |
| Entity stays unavailable | Confirm application is active and running in console |

---

## Step 8: Connect reCamera Pro to Home Assistant (Optional) {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

Configure MQTT output in reCamera Pro app settings; entities will appear automatically in Home Assistant.

### Prerequisites

1. Home Assistant is running and accessible.
2. An MQTT broker reachable by reCamera Pro (from Step 6 or external).
3. The AI app is active and running on the camera.

### Deployment Complete

Detections appear in Home Assistant. This configuration applies to the active app; repeat in Configure when switching to another app.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No Result Output in config | App does not support MQTT output; detections remain local |
| No broker messages | Verify broker address is non-empty and reachable from camera |
| Save rejected | Broker host cannot be empty; base topic cannot contain `+`, `#` or spaces |
| Saved but nothing in HA | Set Output Mode to **Home Assistant** and confirm identical broker settings |
| Entity unavailable | Verify application is currently running in App Center |

---

## Step 9: See reCamera Results in Home Assistant (Optional) {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

View reCamera (SG2002) video stream and detection entities on your Home Assistant dashboard.

### Prerequisites

1. **Find Entities:** Under **Settings → Devices & Services → MQTT**, locate the camera device and note entities.
2. **Add Card:** Add a **Picture glance** card on your dashboard, combining the video stream with detection entities.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Card shows video but no icons | Verify Home Assistant integration status in camera console |
| Entity shows unknown | Values update upon changes detected in the camera view |

---

## Step 10: See reCamera Pro Results in Home Assistant (Optional) {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

Combine reCamera Pro video stream and detection entities on a single dashboard card.

### Prerequisites

1. **Find Entities:** Under **Settings → Devices & Services → MQTT**, locate camera entities.
2. **Enable RTSP:** In camera panel: **Live View → Stream Settings**, select RTSP, enable stream, and copy the RTSP URL.
3. **Add Camera:** In Home Assistant: **Settings → Devices & Services → Add Integration → Generic Camera**, paste RTSP URL, set transport to **TCP**.
4. **Build Card:** On dashboard, add a **Picture glance** card pointing to Generic Camera with detection entities listed.

### Deployment Complete

Dashboard displays real-time camera video with overlaid detection entities.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No RTSP stream URL | RTSP not enabled or another protocol selected |
| Generic Camera cannot connect | Test URL with VLC; ensure TCP transport is selected |
| Black or freezing video | Close camera web preview and any open VLC players |
| No detection icons on card | Confirm MQTT output is configured on active app (Step 8) |
| Entity shows unknown | Values update upon new detections in camera frame |

---

## Preset: Retail Flow & Passenger Analytics {#spatial_retail}

Experience multi-target tracking (ByteTrack) coupled with virtual tripwires for retail passenger analytics. Learn how edge devices count entries/exits and track dwell time without cloud dependency.

- **Devices:** reCamera (SG2002) or reCamera Pro (RV1126B); a PC or reComputer R1100 when forwarding to Home Assistant.
- **Recommended Apps:** `retail-vision` (retail passenger flow).
- **Hands-on Quests:**
  1. Define a virtual tripwire on the live feed, walk back and forth in frame, and observe bidirectional entry/exit counts update instantly;
  2. Dwell on one side of the tripwire to observe how the device classifies browsing vs. assistance-needed states.

## Step 1: Upgrade reCamera Console (SG2002) {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

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

## Step 2: Install Retail Analytics App (SG2002) {#retail_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select **Retail People Counting (retail-vision)** and click **Deploy**.

### Prerequisites

1. PC needs internet access to fetch packages; the camera does not need internet.
2. The retail application includes ByteTrack tracking and tripwire counting algorithms.

### Deployment Complete

The camera is running the retail passenger analytics application.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dropdown empty | PC cannot reach `sensecraft-statics.seeed.cc`; fix connection and refresh |
| Login rejected | Use camera credentials `recamera` / `recamera` (or `recamera.2`) |
| Console busy | Camera is handling another operation; retry in a minute |
| Failed to start | Check status in console Applications tab; redeploy if files are missing |

---

## Step 3: Open Console & Debug View (SG2002) {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera console to inspect the real-time inference video feed and detection metrics.

### Prerequisites

1. Log in with camera credentials from Step 1.
2. In the **Applications** tab, click **Debug** on the running app to see the live feed and bounding boxes.

### Deployment Complete

Console URL is `http://<camera-ip>/` for streaming, threshold tuning, and networking setup.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Wait 60s for camera reboot to finish, then refresh |
| Black video stream | No app is active; return to Step 2 to deploy an app |

---

## Step 4: Check & Update Firmware (reCamera Pro) {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

For reCamera Pro users only. Skip if your camera already displays the App Center.

### Prerequisites

1. Open camera web page; if App Center is present, skip this step.
2. Fill in device IP and ADB port 5555, then click **Check & Update Device**.
3. Firmware update runs over network ADB port 5555; USB alone is not sufficient.
4. The camera reboots during update; do not power off. Use **Factory Reset** on the same page to roll back.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test connection fails | Check address and verify port 5555 is reachable from this PC |
| Nothing happens on check | Camera may already be on latest firmware; look for App Center on its page |
| App Center missing after reboot | Reload the page after camera finishes rebooting |

---

## Step 5: Open App Center (reCamera Pro) {#open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

For reCamera Pro users only. Open App Center, install and start the corresponding application.

### Prerequisites

1. Log in with camera panel credentials (not SSH credentials).
2. Open **App Center** from sidebar, select the target application to install, and click **Start**.
3. View live video and detection results in **Live Preview**.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page does not open | Prefix URL with `http://` to allow proper redirection |
| Certificate warning | Camera uses a self-signed certificate over HTTPS; accept and proceed |
| App Center empty or asks to sign in | Log in to the management dashboard first, then refresh |
| Failed to load catalog | PC cannot reach `sensecraft-statics.seeed.cc`; update catalog URL if self-hosting |
| App fails to start | Model files missing; reinstall the application |

---

## Step 6: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Launch Home Assistant and an MQTT broker container. Skip if already running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant locally on Docker Desktop with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk space.
3. Ports 8123 and 1883 available.

### Deployment Complete

1. Open **http://localhost:8123** and complete the onboarding wizard.
2. MQTT broker listens on port 1883; use this address in Steps 7 & 8.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port 8123 or 1883 busy | Stop existing Home Assistant / Mosquitto containers, or reuse them |
| Docker not running | Launch Docker Desktop application |
| Container restarting | Ensure at least 2 GB of RAM is free |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote edge host (e.g. reComputer) on the local network.

### Prerequisites

1. Target host is reachable over SSH with Docker running.
2. Enter IP address, username, and password below.

### Deployment Complete

1. Open **http://<device-ip>:8123** and complete the onboarding wizard.
2. MQTT broker listens on port 1883 of the remote device; use this address in Steps 7 & 8.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection timeout | Check local network and ping device |
| SSH auth failed | Verify username and password |
| Port 1883 busy | An MQTT broker is already running; retain it and enter its port in Steps 7 & 8 |

---

## Step 7: Connect reCamera to Home Assistant (Optional) {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Connect reCamera (SG2002) and Home Assistant to the same MQTT broker for automatic entity discovery.

### Prerequisites

1. Home Assistant is running and accessible.
2. An MQTT broker reachable by the camera (from Step 6 or external).
3. In camera console: under **Integrations → Home Assistant**, enter broker IP and port 1883.

### Deployment Complete

Detections publish as Home Assistant entities. If entities show unavailable, verify the app is running in the camera console.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No data on broker | Verify broker IP is correct and reachable from camera subnet |
| Entity stays unavailable | Confirm application is active and running in console |

---

## Step 8: Connect reCamera Pro to Home Assistant (Optional) {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

Configure MQTT output in reCamera Pro app settings; entities will appear automatically in Home Assistant.

### Prerequisites

1. Home Assistant is running and accessible.
2. An MQTT broker reachable by reCamera Pro (from Step 6 or external).
3. The AI app is active and running on the camera.

### Deployment Complete

Detections appear in Home Assistant. This configuration applies to the active app; repeat in Configure when switching to another app.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No Result Output in config | App does not support MQTT output; detections remain local |
| No broker messages | Verify broker address is non-empty and reachable from camera |
| Save rejected | Broker host cannot be empty; base topic cannot contain `+`, `#` or spaces |
| Saved but nothing in HA | Set Output Mode to **Home Assistant** and confirm identical broker settings |
| Entity unavailable | Verify application is currently running in App Center |

---

## Step 9: See reCamera Results in Home Assistant (Optional) {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

View reCamera (SG2002) video stream and detection entities on your Home Assistant dashboard.

### Prerequisites

1. **Find Entities:** Under **Settings → Devices & Services → MQTT**, locate the camera device and note entities.
2. **Add Card:** Add a **Picture glance** card on your dashboard, combining the video stream with detection entities.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Card shows video but no icons | Verify Home Assistant integration status in camera console |
| Entity shows unknown | Values update upon changes detected in the camera view |

---

## Step 10: See reCamera Pro Results in Home Assistant (Optional) {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

Combine reCamera Pro video stream and detection entities on a single dashboard card.

### Prerequisites

1. **Find Entities:** Under **Settings → Devices & Services → MQTT**, locate camera entities.
2. **Enable RTSP:** In camera panel: **Live View → Stream Settings**, select RTSP, enable stream, and copy the RTSP URL.
3. **Add Camera:** In Home Assistant: **Settings → Devices & Services → Add Integration → Generic Camera**, paste RTSP URL, set transport to **TCP**.
4. **Build Card:** On dashboard, add a **Picture glance** card pointing to Generic Camera with detection entities listed.

### Deployment Complete

Dashboard displays real-time camera video with overlaid detection entities.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No RTSP stream URL | RTSP not enabled or another protocol selected |
| Generic Camera cannot connect | Test URL with VLC; ensure TCP transport is selected |
| Black or freezing video | Close camera web preview and any open VLC players |
| No detection icons on card | Confirm MQTT output is configured on active app (Step 8) |
| Entity shows unknown | Values update upon new detections in camera frame |

---
