## Preset: Object Detection & Environment {#object_detection}

Explore foundational edge vision capabilities with general object detection (YOLO) and weather classification. Watch bounding boxes and confidence scores update in real time over WebRTC to experience INT8 model efficiency.

- **Hardware:** reCamera (SG2002) or reCamera Pro (RV1126B); Home Assistant integration optionally requires a PC or reComputer R1100.
- **Recommended Apps:** `yolo-detector` (80 common COCO classes) or `weather-classifier` (weather recognition).
- **Quest:**
  1. Hold a phone, mug, or hand in front of the lens and observe detection boxes and labels rendered within 50ms;
  2. Slowly move the object or partially occlude it, watching the confidence score shift to observe occlusion robustness.

## Step 1: Install Object Detection App {#obj_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select the desired application from the dropdown and deploy it to the camera.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/recamera_console_app.yaml default=true}

Select **Object Detection (yolo-detector)** or **Weather Classification (weather-classifier)** from the dropdown and click **Deploy**.

### Prerequisites

1. Your computer has internet access; the camera does not need internet access (the host computer downloads packages and models).
2. Connect the camera via USB (`192.168.42.1`) or via local network IP.
3. Default credentials are `recamera` / `recamera` (or `recamera.2` on earlier firmware).
4. Console version must be 0.5.5 or higher.

### Deployment Complete

The camera is running the object detection application. The app supports ONVIF and RTSP for NVR and video management systems.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Dropdown empty or incomplete | Host cannot reach `sensecraft-statics.seeed.cc`; verify network and refresh |
| Login rejected | Use camera credentials (default `recamera` / `recamera` or `recamera.2`) |
| Console unresponsive | Camera may still be rebooting; wait one minute and retry |
| Busy prompt | Console is processing another operation; retry when finished |
| App failed to start | Check status in console App page; redeploy if files are missing |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_yolo.yaml}

Configure and activate the object detection app (`yolo-detector`) on reCamera Pro.

### Prerequisites

1. Camera is connected via USB (`192.168.42.1`) or on the local network.
2. Enter the camera web dashboard admin username and password (default `admin`).
3. Ensure the app is installed in the device's App Center. If not, install it from App Center first.

### Deployment Complete

The object detection app is activated and running on reCamera Pro.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login failed | Ensure you use Web console credentials (not SSH), default user is `admin` |
| App not installed | Install the app from the device App Center catalog first |
| Connection timeout | Verify camera IP and HTTPS (port 443) reachability |

---

## Step 2: Open the Console {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera web console to inspect real-time inference and detections.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/console_dashboard.yaml default=true}

Open the camera console to inspect real-time video stream and detection results.

### Prerequisites

1. Sign in with the camera credentials from Step 1.
2. In the **Apps** page, click **Debug** on the active app to view bounding boxes.

### Deployment Complete

Console is available at `http://<camera-ip>/` to inspect video, tune thresholds, and adjust network settings.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Wait a minute for the camera to finish booting, then refresh |
| Live video is black | No app is active; return to Step 1 to deploy an app |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_apps.yaml}

Open the reCamera Pro control panel to view inference results in Live Preview.

### Prerequisites

1. Sign in with the web control panel credentials (default `admin`).
2. Open **Live Preview** in the left sidebar to view the video stream and AI detections.

### Deployment Complete

Control panel is open. You can view detection boxes and confidence scores in Live Preview.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Prefix the URL with `http://` to allow redirects |
| Certificate warning | Self-signed certificate is expected when HTTPS is enabled; proceed safely |
| Video not loading | Confirm the application was successfully activated in the previous step |

---

## Step 3: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant and an MQTT broker. Skip if both are already running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant on the local machine. Requires Docker Desktop running with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk space.
3. Ports 8123 and 1883 available.

### Deployment Complete

1. Open **http://localhost:8123** and follow the onboarding wizard.
2. MQTT broker runs on port 1883 on this machine; supply this address in Step 4.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 in use | Stop existing Home Assistant or Mosquitto instance |
| Docker fails to start | Launch Docker Desktop |
| Container crash loop | Ensure at least 2 GB of memory is available |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote host (e.g. reComputer) on the local network.

### Prerequisites

1. Target host reachable via SSH with Docker installed.
2. Provide host IP, username, and password below.

### Deployment Complete

1. Open **http://<host-ip>:8123** and complete the onboarding wizard.
2. MQTT broker runs on port 1883 of the remote host; supply this address in Step 4.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check network connectivity with ping |
| SSH authentication failed | Verify username and password |
| Port 1883 in use | Existing broker detected; keep it and use it in Step 4 |

---

## Step 4: View Results in Home Assistant (Optional) {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Inspect camera live stream and detection entities on the Home Assistant dashboard.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/ha_dashboard.yaml default=true}

Connect Home Assistant and the camera to the same MQTT broker to auto-discover detection entities, then add a video glance card.

### Prerequisites

1. **Add MQTT Integration**: In Home Assistant **Settings → Devices & Services → Add Integration**, add the **MQTT** integration pointing to the Step 3 broker IP, port 1883 (leave username/password empty). Skip if already configured.
2. **Point Camera to Broker**: In camera console **Integrations → Home Assistant**, enter the Step 3 broker IP and port 1883, test connection, then save.
3. **Inspect Entities**: In Home Assistant **Settings → Devices & Services → MQTT**, locate the camera device and entities.
4. **Add Card**: On the dashboard, add a Picture glance card to overlay detection entities onto the video stream.

### Deployment Complete

The dashboard displays camera video and detection entities. Switching apps updates entities automatically.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No data on broker | Confirm broker IP is reachable from camera |
| Entities unavailable | Confirm the app is actively running on the camera |
| Card has video but no entities | Verify MQTT integration status and entities list |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/ha_dashboard_pro.yaml}

Add reCamera Pro's RTSP video stream and MQTT detection entities to a Home Assistant dashboard card.

### Prerequisites

1. **Add MQTT Integration**: In Home Assistant **Settings → Devices & Services → Add Integration**, add the **MQTT** integration pointing to the Step 3 broker IP, port 1883 (leave username/password empty). Skip if already configured.
2. **Configure Camera MQTT**: If MQTT Broker Address was filled during Step 1 deployment, it connects automatically. Otherwise, in the camera web console App Center, click Configure on the app, enable MQTT under Result Output, set Output Mode to Home Assistant, and enter the broker IP and port 1883.
3. **Inspect Entities**: In **Settings → Devices & Services → MQTT**, verify camera detection entities exist.
4. **Enable RTSP**: In the camera web console **Video Settings → Stream Settings**, enable RTSP and copy the stream URL.
5. **Add Video**: In Home Assistant **Settings → Devices & Services → Add Integration**, select **Generic Camera** and paste the RTSP URL (use TCP transport).
6. **Add Card**: Add a Picture glance card, select Generic Camera as Camera Entity, and add detection entities.

### Deployment Complete

The dashboard shows the camera stream and detection entities.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No stream URL displayed | Enable RTSP protocol in streaming settings |
| Generic Camera cannot connect | Test URL in VLC; set RTSP transport to TCP |
| Entities show unknown | A wait for visual changes in front of the lens is normal before first report |

---

## Preset: Human Behavior & Pose {#human_behavior}

Explore landmark tracking and temporal human action recognition. Learn facial mesh landmarks (468 points), skeletal poses, on-device privacy blurring, and state-machine action recognition.

- **Hardware:** reCamera (SG2002) or reCamera Pro (RV1126B); Home Assistant integration optionally requires a PC or reComputer R1100.
- **Recommended Apps:** `face-analysis` (facial attributes & blur), `facemesh-reader` (drowsiness detection), `fall-detection` (fall alert), `fitness-trainer` (rep counting).
- **Quest:**
  1. Close eyes for 3 seconds in front of the lens to observe the 468-point facial mesh trigger a drowsiness alert;
  2. Enable on-device privacy blur to watch faces masked with Gaussian blur without raw images leaving the edge.

## Step 1: Install Human Behavior App {#human_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select the desired human behavior application from the dropdown and deploy it to the camera.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/recamera_console_app.yaml default=true}

Select **Face Analysis (face-analysis)**, **Fall Detection (fall-detection)**, **Drowsiness Detection (facemesh-reader)**, or **Fitness Trainer (fitness-trainer)** from the dropdown and click **Deploy**.

### Prerequisites

1. Your computer has internet access; camera does not require internet.
2. Connect the camera via USB (`192.168.42.1`) or local network IP.
3. Default credentials are `recamera` / `recamera` (or `recamera.2` on earlier firmware).
4. Console version must be 0.5.5 or higher.

### Deployment Complete

The camera is running the human behavior analysis application.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Dropdown empty or incomplete | Host cannot reach `sensecraft-statics.seeed.cc`; verify network and refresh |
| Login rejected | Use camera credentials (default `recamera` / `recamera` or `recamera.2`) |
| Console unresponsive | Camera may still be rebooting; wait one minute and retry |
| Busy prompt | Console is processing another operation; retry when finished |
| App failed to start | Check status in console App page; redeploy if files are missing |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_fall.yaml}

Configure and activate the fall detection app (`fall-detection`) on reCamera Pro.

### Prerequisites

1. Camera is connected via USB (`192.168.42.1`) or on the local network.
2. Enter the camera web dashboard admin username and password (default `admin`).
3. Ensure the app is installed in the device's App Center. If not, install it from App Center first.

### Deployment Complete

The fall detection application is activated and running on reCamera Pro.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login failed | Ensure you use Web console credentials (not SSH), default user is `admin` |
| App not installed | Install the app from the device App Center catalog first |
| Connection timeout | Verify camera IP and HTTPS (port 443) reachability |

---

## Step 2: Open the Console {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera web console to inspect real-time inference and detections.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/console_dashboard.yaml default=true}

Open the camera console to inspect real-time video stream and detection results.

### Prerequisites

1. Sign in with the camera credentials from Step 1.
2. In the **Apps** page, click **Debug** on the active app to view bounding boxes.

### Deployment Complete

Console is available at `http://<camera-ip>/` to inspect video, tune thresholds, and adjust network settings.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Wait a minute for the camera to finish booting, then refresh |
| Live video is black | No app is active; return to Step 1 to deploy an app |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_apps.yaml}

Open the reCamera Pro control panel to view inference results in Live Preview.

### Prerequisites

1. Sign in with the web control panel credentials (default `admin`).
2. Open **Live Preview** in the left sidebar to view the video stream and AI detections.

### Deployment Complete

Control panel is open. You can view detection boxes and confidence scores in Live Preview.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Prefix the URL with `http://` to allow redirects |
| Certificate warning | Self-signed certificate is expected when HTTPS is enabled; proceed safely |
| Video not loading | Confirm the application was successfully activated in the previous step |

---

## Step 3: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant and an MQTT broker. Skip if both are already running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant on the local machine. Requires Docker Desktop running with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk space.
3. Ports 8123 and 1883 available.

### Deployment Complete

1. Open **http://localhost:8123** and follow the onboarding wizard.
2. MQTT broker runs on port 1883 on this machine; supply this address in Step 4.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 in use | Stop existing Home Assistant or Mosquitto instance |
| Docker fails to start | Launch Docker Desktop |
| Container crash loop | Ensure at least 2 GB of memory is available |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote host (e.g. reComputer) on the local network.

### Prerequisites

1. Target host reachable via SSH with Docker installed.
2. Provide host IP, username, and password below.

### Deployment Complete

1. Open **http://<host-ip>:8123** and complete the onboarding wizard.
2. MQTT broker runs on port 1883 of the remote host; supply this address in Step 4.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check network connectivity with ping |
| SSH authentication failed | Verify username and password |
| Port 1883 in use | Existing broker detected; keep it and use it in Step 4 |

---

## Step 4: View Results in Home Assistant (Optional) {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Inspect camera live stream and detection entities on the Home Assistant dashboard.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/ha_dashboard.yaml default=true}

Connect Home Assistant and the camera to the same MQTT broker to auto-discover detection entities, then add a video glance card.

### Prerequisites

1. **Add MQTT Integration**: In Home Assistant **Settings → Devices & Services → Add Integration**, add the **MQTT** integration pointing to the Step 3 broker IP, port 1883 (leave username/password empty). Skip if already configured.
2. **Point Camera to Broker**: In camera console **Integrations → Home Assistant**, enter the Step 3 broker IP and port 1883, test connection, then save.
3. **Inspect Entities**: In Home Assistant **Settings → Devices & Services → MQTT**, locate the camera device and entities.
4. **Add Card**: On the dashboard, add a Picture glance card to overlay detection entities onto the video stream.

### Deployment Complete

The dashboard displays camera video and detection entities. Switching apps updates entities automatically.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No data on broker | Confirm broker IP is reachable from camera |
| Entities unavailable | Confirm the app is actively running on the camera |
| Card has video but no entities | Verify MQTT integration status and entities list |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/ha_dashboard_pro.yaml}

Add reCamera Pro's RTSP video stream and MQTT detection entities to a Home Assistant dashboard card.

### Prerequisites

1. **Add MQTT Integration**: In Home Assistant **Settings → Devices & Services → Add Integration**, add the **MQTT** integration pointing to the Step 3 broker IP, port 1883 (leave username/password empty). Skip if already configured.
2. **Configure Camera MQTT**: If MQTT Broker Address was filled during Step 1 deployment, it connects automatically. Otherwise, in the camera web console App Center, click Configure on the app, enable MQTT under Result Output, set Output Mode to Home Assistant, and enter the broker IP and port 1883.
3. **Inspect Entities**: In **Settings → Devices & Services → MQTT**, verify camera detection entities exist.
4. **Enable RTSP**: In the camera web console **Video Settings → Stream Settings**, enable RTSP and copy the stream URL.
5. **Add Video**: In Home Assistant **Settings → Devices & Services → Add Integration**, select **Generic Camera** and paste the RTSP URL (use TCP transport).
6. **Add Card**: Add a Picture glance card, select Generic Camera as Camera Entity, and add detection entities.

### Deployment Complete

The dashboard shows the camera stream and detection entities.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No stream URL displayed | Enable RTSP protocol in streaming settings |
| Generic Camera cannot connect | Test URL in VLC; set RTSP transport to TCP |
| Entities show unknown | A wait for visual changes in front of the lens is normal before first report |

---

## Preset: Text & Code Reading {#text_reading}

Two-stage vision pipeline. Extract Chinese & English text from labels, screens, and packages with PP-OCR, or decode multiple QR codes concurrently.

- **Hardware:** reCamera (SG2002) or reCamera Pro (RV1126B); Home Assistant integration optionally requires a PC or reComputer R1100.
- **Recommended Apps:** `ppocr-reader` (OCR text reader) or `qrcode-reader` (QR code reader).
- **Quest:**
  1. Hold printed Chinese or English labels in front of the lens to observe text detection and extraction;
  2. Test detection reliability across varying lighting conditions and angles.

## Step 1: Install Text Reading App {#text_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select the desired text or code reading application from the dropdown and deploy it to the camera.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/recamera_console_app.yaml default=true}

Select **OCR Text Reader (ppocr-reader)** or **QR Code Reader (qrcode-reader)** from the dropdown and click **Deploy**.

### Prerequisites

1. Your computer has internet access; camera does not require internet.
2. Connect the camera via USB (`192.168.42.1`) or local network IP.
3. Default credentials are `recamera` / `recamera` (or `recamera.2` on earlier firmware).
4. Console version must be 0.5.5 or higher.

### Deployment Complete

The camera is running the text and code recognition application.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Dropdown empty or incomplete | Host cannot reach `sensecraft-statics.seeed.cc`; verify network and refresh |
| Login rejected | Use camera credentials (default `recamera` / `recamera` or `recamera.2`) |
| Console unresponsive | Camera may still be rebooting; wait one minute and retry |
| Busy prompt | Console is processing another operation; retry when finished |
| App failed to start | Check status in console App page; redeploy if files are missing |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_ocr.yaml}

Configure and activate the text recognition app (`ocr`) on reCamera Pro.

### Prerequisites

1. Camera is connected via USB (`192.168.42.1`) or on the local network.
2. Enter the camera web dashboard admin username and password (default `admin`).
3. Ensure the app is installed in the device's App Center. If not, install it from App Center first.

### Deployment Complete

The text recognition application is activated and running on reCamera Pro.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login failed | Ensure you use Web console credentials (not SSH), default user is `admin` |
| App not installed | Install the app from the device App Center catalog first |
| Connection timeout | Verify camera IP and HTTPS (port 443) reachability |

---

## Step 2: Open the Console {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera web console to inspect real-time inference and detections.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/console_dashboard.yaml default=true}

Open the camera console to inspect real-time video stream and detection results.

### Prerequisites

1. Sign in with the camera credentials from Step 1.
2. In the **Apps** page, click **Debug** on the active app to view bounding boxes.

### Deployment Complete

Console is available at `http://<camera-ip>/` to inspect video, tune thresholds, and adjust network settings.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Wait a minute for the camera to finish booting, then refresh |
| Live video is black | No app is active; return to Step 1 to deploy an app |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_apps.yaml}

Open the reCamera Pro control panel to view inference results in Live Preview.

### Prerequisites

1. Sign in with the web control panel credentials (default `admin`).
2. Open **Live Preview** in the left sidebar to view the video stream and AI detections.

### Deployment Complete

Control panel is open. You can view detection boxes and confidence scores in Live Preview.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Prefix the URL with `http://` to allow redirects |
| Certificate warning | Self-signed certificate is expected when HTTPS is enabled; proceed safely |
| Video not loading | Confirm the application was successfully activated in the previous step |

---

## Step 3: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant and an MQTT broker. Skip if both are already running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant on the local machine. Requires Docker Desktop running with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk space.
3. Ports 8123 and 1883 available.

### Deployment Complete

1. Open **http://localhost:8123** and follow the onboarding wizard.
2. MQTT broker runs on port 1883 on this machine; supply this address in Step 4.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 in use | Stop existing Home Assistant or Mosquitto instance |
| Docker fails to start | Launch Docker Desktop |
| Container crash loop | Ensure at least 2 GB of memory is available |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote host (e.g. reComputer) on the local network.

### Prerequisites

1. Target host reachable via SSH with Docker installed.
2. Provide host IP, username, and password below.

### Deployment Complete

1. Open **http://<host-ip>:8123** and complete the onboarding wizard.
2. MQTT broker runs on port 1883 of the remote host; supply this address in Step 4.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check network connectivity with ping |
| SSH authentication failed | Verify username and password |
| Port 1883 in use | Existing broker detected; keep it and use it in Step 4 |

---

## Step 4: View Results in Home Assistant (Optional) {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Inspect camera live stream and detection entities on the Home Assistant dashboard.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/ha_dashboard.yaml default=true}

Connect Home Assistant and the camera to the same MQTT broker to auto-discover detection entities, then add a video glance card.

### Prerequisites

1. **Add MQTT Integration**: In Home Assistant **Settings → Devices & Services → Add Integration**, add the **MQTT** integration pointing to the Step 3 broker IP, port 1883 (leave username/password empty). Skip if already configured.
2. **Point Camera to Broker**: In camera console **Integrations → Home Assistant**, enter the Step 3 broker IP and port 1883, test connection, then save.
3. **Inspect Entities**: In Home Assistant **Settings → Devices & Services → MQTT**, locate the camera device and entities.
4. **Add Card**: On the dashboard, add a Picture glance card to overlay detection entities onto the video stream.

### Deployment Complete

The dashboard displays camera video and detection entities. Switching apps updates entities automatically.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No data on broker | Confirm broker IP is reachable from camera |
| Entities unavailable | Confirm the app is actively running on the camera |
| Card has video but no entities | Verify MQTT integration status and entities list |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/ha_dashboard_pro.yaml}

Add reCamera Pro's RTSP video stream and MQTT detection entities to a Home Assistant dashboard card.

### Prerequisites

1. **Add MQTT Integration**: In Home Assistant **Settings → Devices & Services → Add Integration**, add the **MQTT** integration pointing to the Step 3 broker IP, port 1883 (leave username/password empty). Skip if already configured.
2. **Configure Camera MQTT**: If MQTT Broker Address was filled during Step 1 deployment, it connects automatically. Otherwise, in the camera web console App Center, click Configure on the app, enable MQTT under Result Output, set Output Mode to Home Assistant, and enter the broker IP and port 1883.
3. **Inspect Entities**: In **Settings → Devices & Services → MQTT**, verify camera detection entities exist.
4. **Enable RTSP**: In the camera web console **Video Settings → Stream Settings**, enable RTSP and copy the stream URL.
5. **Add Video**: In Home Assistant **Settings → Devices & Services → Add Integration**, select **Generic Camera** and paste the RTSP URL (use TCP transport).
6. **Add Card**: Add a Picture glance card, select Generic Camera as Camera Entity, and add detection entities.

### Deployment Complete

The dashboard shows the camera stream and detection entities.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No stream URL displayed | Enable RTSP protocol in streaming settings |
| Generic Camera cannot connect | Test URL in VLC; set RTSP transport to TCP |
| Entities show unknown | A wait for visual changes in front of the lens is normal before first report |

---

## Preset: Retail Flow & Passenger Analytics {#spatial_retail}

ByteTrack multi-target tracking with virtual tripwires. Counts passenger entries and exits while tracking dwell time and assistance states.

- **Hardware:** reCamera (SG2002) or reCamera Pro (RV1126B); Home Assistant integration optionally requires a PC or reComputer R1100.
- **Recommended Apps:** `retail-vision` (passenger counting and dwell detection).
- **Quest:**
  1. Walk across the virtual tripwire to observe passenger count incrementing in real time;
  2. Dwell in the zone beyond the threshold duration to observe the assistance alert event.

## Step 1: Install Retail Analytics App {#retail_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

Select the desired passenger analytics application from the dropdown and deploy it to the camera.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/recamera_console_app.yaml default=true}

Select **Retail People Counting (retail-vision)** from the dropdown and click **Deploy**.

### Prerequisites

1. Your computer has internet access; camera does not require internet.
2. Connect the camera via USB (`192.168.42.1`) or local network IP.
3. Default credentials are `recamera` / `recamera` (or `recamera.2` on earlier firmware).
4. Console version must be 0.5.5 or higher.

### Deployment Complete

The camera is running the retail analytics application.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Dropdown empty or incomplete | Host cannot reach `sensecraft-statics.seeed.cc`; verify network and refresh |
| Login rejected | Use camera credentials (default `recamera` / `recamera` or `recamera.2`) |
| Console unresponsive | Camera may still be rebooting; wait one minute and retry |
| Busy prompt | Console is processing another operation; retry when finished |
| App failed to start | Check status in console App page; redeploy if files are missing |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_retail.yaml}

Configure and activate the retail analytics app (`retail-vision`) on reCamera Pro.

### Prerequisites

1. Camera is connected via USB (`192.168.42.1`) or on the local network.
2. Enter the camera web dashboard admin username and password (default `admin`).
3. Ensure the app is installed in the device's App Center. If not, install it from App Center first.

### Deployment Complete

The retail analytics application is activated and running on reCamera Pro.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login failed | Ensure you use Web console credentials (not SSH), default user is `admin` |
| App not installed | Install the app from the device App Center catalog first |
| Connection timeout | Verify camera IP and HTTPS (port 443) reachability |

---

## Step 2: Open the Console {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

Open the camera web console to inspect real-time inference and detections.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/console_dashboard.yaml default=true}

Open the camera console to inspect real-time video stream and detection results.

### Prerequisites

1. Sign in with the camera credentials from Step 1.
2. In the **Apps** page, click **Debug** on the active app to view bounding boxes.

### Deployment Complete

Console is available at `http://<camera-ip>/` to inspect video, tune thresholds, and adjust network settings.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Wait a minute for the camera to finish booting, then refresh |
| Live video is black | No app is active; return to Step 1 to deploy an app |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_apps.yaml}

Open the reCamera Pro control panel to view inference results in Live Preview.

### Prerequisites

1. Sign in with the web control panel credentials (default `admin`).
2. Open **Live Preview** in the left sidebar to view the video stream and AI detections.

### Deployment Complete

Control panel is open. You can view detection boxes and confidence scores in Live Preview.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Prefix the URL with `http://` to allow redirects |
| Certificate warning | Self-signed certificate is expected when HTTPS is enabled; proceed safely |
| Video not loading | Confirm the application was successfully activated in the previous step |

---

## Step 3: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant and an MQTT broker. Skip if both are already running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

Deploy Home Assistant on the local machine. Requires Docker Desktop running with ports 8123 and 1883 available.

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk space.
3. Ports 8123 and 1883 available.

### Deployment Complete

1. Open **http://localhost:8123** and follow the onboarding wizard.
2. MQTT broker runs on port 1883 on this machine; supply this address in Step 4.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 in use | Stop existing Home Assistant or Mosquitto instance |
| Docker fails to start | Launch Docker Desktop |
| Container crash loop | Ensure at least 2 GB of memory is available |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

Deploy to a remote host (e.g. reComputer) on the local network.

### Prerequisites

1. Target host reachable via SSH with Docker installed.
2. Provide host IP, username, and password below.

### Deployment Complete

1. Open **http://<host-ip>:8123** and complete the onboarding wizard.
2. MQTT broker runs on port 1883 of the remote host; supply this address in Step 4.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check network connectivity with ping |
| SSH authentication failed | Verify username and password |
| Port 1883 in use | Existing broker detected; keep it and use it in Step 4 |

---

## Step 4: View Results in Home Assistant (Optional) {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Inspect camera live stream and detection entities on the Home Assistant dashboard.

### Mode: reCamera (SG2002) {#recamera_sg2002 config=devices/ha_dashboard.yaml default=true}

Connect Home Assistant and the camera to the same MQTT broker to auto-discover detection entities, then add a video glance card.

### Prerequisites

1. **Add MQTT Integration**: In Home Assistant **Settings → Devices & Services → Add Integration**, add the **MQTT** integration pointing to the Step 3 broker IP, port 1883 (leave username/password empty). Skip if already configured.
2. **Point Camera to Broker**: In camera console **Integrations → Home Assistant**, enter the Step 3 broker IP and port 1883, test connection, then save.
3. **Inspect Entities**: In Home Assistant **Settings → Devices & Services → MQTT**, locate the camera device and entities.
4. **Add Card**: On the dashboard, add a Picture glance card to overlay detection entities onto the video stream.

### Deployment Complete

The dashboard displays camera video and detection entities. Switching apps updates entities automatically.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No data on broker | Confirm broker IP is reachable from camera |
| Entities unavailable | Confirm the app is actively running on the camera |
| Card has video but no entities | Verify MQTT integration status and entities list |

### Mode: reCamera Pro (RV1126B) {#recamera_pro config=devices/ha_dashboard_pro.yaml}

Add reCamera Pro's RTSP video stream and MQTT detection entities to a Home Assistant dashboard card.

### Prerequisites

1. **Add MQTT Integration**: In Home Assistant **Settings → Devices & Services → Add Integration**, add the **MQTT** integration pointing to the Step 3 broker IP, port 1883 (leave username/password empty). Skip if already configured.
2. **Configure Camera MQTT**: If MQTT Broker Address was filled during Step 1 deployment, it connects automatically. Otherwise, in the camera web console App Center, click Configure on the app, enable MQTT under Result Output, set Output Mode to Home Assistant, and enter the broker IP and port 1883.
3. **Inspect Entities**: In **Settings → Devices & Services → MQTT**, verify camera detection entities exist.
4. **Enable RTSP**: In the camera web console **Video Settings → Stream Settings**, enable RTSP and copy the stream URL.
5. **Add Video**: In Home Assistant **Settings → Devices & Services → Add Integration**, select **Generic Camera** and paste the RTSP URL (use TCP transport).
6. **Add Card**: Add a Picture glance card, select Generic Camera as Camera Entity, and add detection entities.

### Deployment Complete

The dashboard shows the camera stream and detection entities.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No stream URL displayed | Enable RTSP protocol in streaming settings |
| Generic Camera cannot connect | Test URL in VLC; set RTSP transport to TCP |
| Entities show unknown | A wait for visual changes in front of the lens is normal before first report |
