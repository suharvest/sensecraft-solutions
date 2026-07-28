## Preset: reCamera Console {#console}

Replace the camera's built-in control panel with the reCamera Console — one web page to browse and switch AI apps, watch the live view, and manage network and system settings. Start here: the console is how you run everything else.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera whose built-in control panel is upgraded to the console |

**What you'll get:**
- An app gallery — install, switch and configure AI apps from the browser, no SSH needed
- Live view with detection overlays, plus camera orientation and focus controls
- Wi-Fi / HaLow / static IP setup, Home Assistant integration and system settings in one place

**Good to know:** The console takes over the camera pipeline, so the built-in Node-RED editor is switched off during install. You can switch back to Node-RED any time from the console's system settings — nothing is uninstalled.

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install reCamera Console {#deploy_console type=recamera_cpp required=true config=devices/recamera_console.yaml}

Upgrade the camera's control panel to the console. The camera goes offline for about a minute while it restarts.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### What to check

- The install finishes with the service started — the camera's web page reloads on its own within about a minute
- Any AI app you installed earlier is kept and reappears in the console's app gallery

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |
| Want the original panel back | Hold the **User** button while plugging in power, release when the red LED stops blinking and stays on — this factory-resets the camera |

---

## Step 2: Open reCamera Console {#open_console type=web_dashboard required=true config=devices/console_dashboard.yaml}

Open the console in your browser and sign in with your camera's username and password.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Wait a minute for the camera to finish restarting, then refresh |
| Login rejected | Use the camera's own credentials, default `recamera` / `recamera` |
| Live view is black | Open the app gallery and start an app first — the live view shows the running app's output |
| Camera won't start after enabling privacy blur | That setting swaps a video kernel module and needs a full power cycle — unplug the camera and plug it back in rather than using a software reboot |

### Deployment Complete

The console is live at `http://<camera-ip>/`. Everything else on this camera is now managed from here.

Open the app gallery to install or switch AI apps, use the live view to check what the camera sees, and set up Wi-Fi, static IP or Home Assistant from the settings pages. The other presets in this solution install apps that show up in this same gallery.

The apps also answer ONVIF, so an NVR or video management system can discover the camera on the network and pull its stream without you typing an RTSP address.

**If you turn on device-level privacy blur** in the settings: it replaces a video kernel module, so the console will tell you a restart is needed. Power the camera off and on again at the plug — a software reboot does not reset the video hardware and can leave the camera unable to start.

---

## Preset: Retail People Flow Heatmap {#simple}

Just one reCamera - view a live retail people-flow heatmap directly in its web interface, see where shoppers gather and which areas are ignored.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that detects and tracks people, drives the people-flow heatmap |

**What you'll get:**
- Live video with people-flow heatmap overlay (rendered in real-time by the web interface, accumulated from person positions)
- See exactly which shelves and aisles attract shoppers vs which ones get ignored
- Privacy protection (faces auto-blurred)

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Enable People Detection {#deploy_detector type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

Install the person detection program on reCamera so it can identify people in the video.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View Live People Flow Heatmap {#preview type=preview required=false config=devices/preview.yaml}

Click **Connect** to see the live video with people-flow heatmap overlay.

**Tip:** The heatmap accumulates from person positions over time — wait a few minutes for the flow pattern to emerge.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| No heatmap overlay | Wait a few minutes for data to accumulate; make sure Step 1 completed |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live people-flow heatmap.

The heatmap accumulates from person positions over time — areas where shoppers linger or pass through more frequently will glow brighter, helping you spot retail "hot zones" and "cold zones".

---

## Preset: Home Assistant Integration {#ha_integration}

Connect reCamera to Home Assistant for unified smart home monitoring.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera with YOLO detection + RTSP streaming |
| Computer or reComputer R1100 | Runs Home Assistant |

**What you'll get:**
- Live RTSP video stream as an HA camera entity
- AI detection count sensor with per-class breakdown (person, car, etc.)
- FlowFuse Dashboard on reCamera for local debugging

**Requirements:** Docker installed · Same local network for all devices

---

## Step 1: Deploy Home Assistant {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant. Skip this step if you already have HA running.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

### Wiring

1. Make sure Docker Desktop is installed and running
2. Ensure at least 2GB free disk space

### Deployment Complete

1. Open **http://localhost:8123** in your browser
2. Follow the onboarding wizard to create your admin account
3. Remember your username and password — you'll need them in Step 3

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 busy | Close the program using port 8123, or change the port in docker-compose.yml |
| Docker not starting | Open Docker Desktop application |
| Container keeps restarting | Make sure you have at least 2GB RAM available |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

### Wiring

1. Connect the target device to the network
2. Enter IP address, username and password below

### Deployment Complete

1. Open **http://\<device-ip\>:8123** in your browser
2. Follow the onboarding wizard to create your admin account
3. Remember your username and password — you'll need them in Step 3

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check network cable, test with ping |
| SSH authentication failed | Verify username and password |

---

## Step 2: Deploy AI Detection Flow {#deploy_flow type=recamera_nodered required=true config=devices/recamera.yaml}

Install YOLO detection + RTSP streaming flow on reCamera.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 3: Add reCamera to Home Assistant {#configure_ha type=ha_integration required=true config=devices/homeassistant_existing.yaml}

Install the reCamera integration and connect it to Home Assistant.

### Wiring

1. Enter your Home Assistant **IP address** (e.g. `192.168.1.100`)
2. Enter the **HA login username and password** you created during HA setup
3. Enter the **reCamera IP address** — use `192.168.42.1` if connected via USB, or the WiFi IP from your router
4. **HA OS users**: leave the SSH fields empty — the system will set up SSH automatically
5. **Docker HA users**: fill in the SSH username and password of the **host machine** (not the HA login)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| HA login failed | The username and password here are for HA web login, not SSH. Check they are correct |
| Restart takes a long time | HA OS restarts the entire system — this can take 30-90 seconds, please wait |
| SSH addon install failed | HA OS needs internet to download the SSH addon. Check network connectivity |
| File copy failed | HA OS: check disk space. Docker: verify SSH credentials are for the **host machine** |
| `setup_retry` after adding | HA cannot reach reCamera — make sure both devices are on the same network |
| Camera thumbnail blank, but stream works | Known issue: ffmpeg snapshot may time out; the live stream in the dashboard works fine |
| Sensor shows 0 | Normal when nothing is in view; verify at http://\<recamera-ip\>:1880/data |

## Step 4: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The Home Assistant dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your reCamera is now integrated with Home Assistant!

#### Quick Verification

1. Open **http://\<server-ip\>:8123**
2. Go to **Settings → Devices & Services** — you should see **reCamera (your-ip)** listed
3. Click into the device to see both entities
4. Add a **Picture Entity** card to your dashboard for the camera stream

#### Access Points

- **Home Assistant**: http://\<server-ip\>:8123 — your unified smart home dashboard
- **FlowFuse Dashboard**: http://\<recamera-ip\>:1880/dashboard — local debugging UI on reCamera
- **Detection API**: http://\<recamera-ip\>:1880/data — raw detection JSON data

#### Next Steps

- Create **automations** using the detection sensor (e.g. turn on lights when person count > 0)
- Add the camera to a **dashboard card** with Picture Entity or Picture Glance
- Set up **mobile notifications** when specific objects are detected

**Having issues?**
- No video? Check reCamera IP and that Step 2 completed successfully
- No detection data? Make sure objects are in view; check Node-RED at http://\<recamera-ip\>:1880

---

## Preset: OCR Text Reader {#ocr_reader}

Point reCamera at any text — signs, labels, meter displays — and the recognized characters appear on screen in real-time. All processing happens on the camera, no cloud needed.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that reads text from the video |

**What you'll get:**
- Live video with recognized text highlighted on screen
- Works with printed text, signs, labels, and digital displays
- All processing on-device — no cloud, no extra hardware

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install Text Recognition {#deploy_ppocr type=recamera_cpp required=true config=devices/recamera_ppocr.yaml}

Install the text recognition program on reCamera so it can read text in the video.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View OCR Overlay {#preview_ocr type=preview required=false config=devices/preview_ocr.yaml}

Click **Connect** to see the live video with OCR text overlay.

**Tip:** Point the camera at text — signs, labels, screens — for best results.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| No text detected | Make sure text is clearly visible and well-lit; check Step 1 completed |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live OCR overlay.

Point the camera at printed text — the recognized characters will appear above each detected region.

---

## Preset: Face Analysis {#face_analysis}

Point reCamera at people — it detects faces and analyzes age, gender, and emotion in real-time. All processing happens on the camera, no cloud needed.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that analyzes faces in the video |

**What you'll get:**
- Live video with face bounding boxes and analysis labels
- Age, gender, and emotion displayed for each detected face
- All processing on-device — no cloud, no extra hardware

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install Face Analysis {#deploy_face_analysis type=recamera_cpp required=true config=devices/recamera_face_analysis.yaml}

Install the face analysis program on reCamera so it can detect faces and analyze age, gender, and emotion.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View Face Analysis Results {#preview_face_analysis type=preview required=false config=devices/preview_face_analysis.yaml}

Click **Connect** to see the live video with face analysis overlay.

**Tip:** Point the camera at people — each detected face will show age, gender, and emotion.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| No faces detected | Make sure faces are clearly visible and well-lit; check Step 1 completed |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live face analysis overlay.

Each detected face will show age, gender, and emotion — all analyzed on-device in real-time.

---

## Preset: Drowsiness Detection {#facemesh_drowsiness}

Point reCamera at a driver — it tracks eye closure, yawn frequency, and PERCLOS score in real-time. All processing happens on the camera, no cloud needed.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that monitors driver alertness |

**What you'll get:**
- Live video with face bounding boxes and drowsiness metrics
- Real-time EAR (Eye Aspect Ratio) and MAR (Mouth Aspect Ratio) tracking
- PERCLOS drowsiness score and continuous eye closure monitoring
- Yawn detection with 5-minute frequency counter
- Color-coded drowsiness state: Alert, Tired, Drowsy, Danger
- All processing on-device — no cloud, no extra hardware

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install Drowsiness Detection {#deploy_facemesh_drowsiness type=recamera_cpp required=true config=devices/recamera_facemesh_drowsiness.yaml}

Install the FaceMesh drowsiness detection program on reCamera so it can track eye and mouth movements.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View Drowsiness Detection Results {#preview_facemesh_drowsiness type=preview required=false config=devices/preview_facemesh_drowsiness.yaml}

Click **Connect** to see the live video with drowsiness detection overlay.

**Tip:** Point the camera at a face — each detected face will show EAR, MAR, and drowsiness state in real-time.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| No faces detected | Make sure the face is clearly visible and well-lit; check Step 1 completed |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live drowsiness detection overlay.

Each detected face will show EAR/MAR values and a color-coded drowsiness state — all analyzed on-device in real-time.

---

## Preset: Weather Classification {#weather_classification}

Point reCamera outside — it classifies the current weather (clear/cloudy/foggy/rainy/snowy) in real-time. All processing happens on the camera, no cloud needed.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that classifies weather conditions in the video |

**What you'll get:**
- Live video with the current weather label and confidence overlay
- Per-class confidence scores (clear/cloudy/foggy/rainy/snowy)
- Results published to MQTT for downstream automation
- All processing on-device — no cloud, no extra hardware

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install Weather Classification {#deploy_weather type=recamera_cpp required=true config=devices/recamera_weather.yaml}

Install the weather classification program on reCamera so it can classify the current weather condition.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View Weather Classification Results {#preview_weather type=preview required=false config=devices/preview_weather.yaml}

Click **Connect** to see the live video with the weather classification overlay.

**Tip:** Point the camera outside — the overlay updates with the current weather label and confidence as conditions change.

**Note:** The weather label and confidence usually appear a few seconds before the video frame does — MQTT connects faster than the RTSP stream stabilizes. If you see the label but not the video yet, just wait a bit longer; this is expected, not an error.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| Label shows but video doesn't | Normal — RTSP takes a bit longer to start than MQTT; wait a few more seconds |
| No overlay data | Check Step 1 completed and MQTT is reachable on the camera |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live weather classification overlay.

The overlay shows the current weather label, confidence, and per-class scores — all analyzed on-device in real-time.

---

## Step 3: Restore Default Camera Services {#restore_defaults type=recamera_cpp required=false config=devices/restore_defaults.yaml}

Optional — switch the camera back to its stock services (Node-RED, sscma-node) and stop the weather classification program.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |

---

## Preset: Retail People Counting {#retail_vision}

Point reCamera at your entrance or aisle — it counts customers in and out, tracks where they linger, and flags who has been waiting long enough to need help. All processing happens on the camera, no cloud needed.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that detects, tracks and counts people, and analyzes dwell states |

**What you'll get:**
- Live video with per-person tracking, dwell state (browsing / engaged / assistance) and footfall counters
- Automatic entry / exit counting and rolling footfall statistics, published to MQTT
- All processing on-device — no cloud, no extra hardware

**Tip:** The counting zone and directional entry/exit line are drawn afterwards in the camera's own web console (Apps → Retail People Counting → Configure). Until you draw them, the app counts people across the whole frame.

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install Retail People Counting {#deploy_retail type=recamera_cpp required=true config=devices/recamera_retail_vision.yaml}

Install the retail people-counting program on reCamera so it can detect, track and count shoppers in the video.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |

---

## Step 2: View Retail Analytics {#preview_retail type=preview required=false config=devices/preview_retail_vision.yaml}

Click **Connect** to see the live video with per-person tracking and footfall counters.

**Tip:** For entry/exit counts, draw the directional line in the camera web console first; without it the preview still shows tracking and dwell states across the whole frame.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| No overlay data | Make sure Step 1 completed and MQTT is reachable on the camera |
| Counters stay at zero | Draw the entry/exit line in the camera web console, or wait for people to enter the frame |

### Deployment Complete

Camera is ready! Click **Connect** above to view the live retail analytics.

Per-person tracking, dwell states and footfall counters are analyzed on-device in real-time. Draw a counting zone and entry/exit line in the camera's web console to turn the whole-frame counts into zone-scoped, directional footfall.

---

## Preset: Fitness Trainer {#fitness_trainer}

Point reCamera at your workout spot — it counts your reps and tells you when a rep was too shallow. Squats, push-ups or hammer curls, all counted on the camera itself.

| Device | Purpose |
|--------|---------|
| reCamera | AI camera that tracks your joints and counts repetitions |

**What you'll get:**
- Live video with your skeleton drawn on and a rep counter pinned to the corner
- Automatic set tracking — reps roll over into sets, with a "workout complete" signal
- Form hints: a partial squat or a drifting elbow is called out, not silently counted
- Counts published to MQTT, ready for Home Assistant workout logging
- All processing on-device — no phone, no wearable, no video leaving the camera

**Requirements:** New devices need SSH enabled first — connect via USB, wait for boot (~2 min), visit [192.168.42.1/#/security](http://192.168.42.1/#/security), login with `recamera` / `recamera`, enable the SSH toggle

## Step 1: Install Fitness Trainer {#deploy_fitness_trainer type=recamera_cpp required=true config=devices/recamera_fitness_trainer.yaml}

Pick your exercise and install the rep counter on reCamera.

### Wiring

1. USB connection: IP address `192.168.42.1`, plug and play
2. Network/WiFi: Find reCamera's IP in your router admin page
3. Username `recamera`, default password `recamera` (use your own if changed)

### What to check

The pose model ships with the reCamera Console, so nothing extra is downloaded. On firmware older than Console 0.3.x the model may be missing — the installer prints a warning and you can point `MODEL_PATH` in `/etc/fitness-trainer.conf` at any YOLO pose cvimodel.

This app draws a skeleton instead of a detection box, which the camera's own web console only knows how to render from **Console 0.3.3 onward**; on an older console its debug view stays blank. Install the "reCamera Console" preset first (or update it) if you want to watch it there. Step 2 below is unaffected — it renders the skeleton itself.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; Network: check router for IP |
| Wrong password | Default is `recamera`, use your new password if changed |
| Install failed | Restart the camera and try again |
| Warning about a missing pose model | Update the reCamera Console, or set `MODEL_PATH` in `/etc/fitness-trainer.conf` |

---

## Step 2: View Your Reps {#preview_fitness_trainer type=preview required=false config=devices/preview_fitness_trainer.yaml}

Click **Connect**, then stand in frame and do a few reps — the counter moves as you come back up.

**Camera placement matters, and differs per exercise:** squats need your whole body from the side or at 45°, with the **ankles in frame** — a view cropped at the knee gives no reading. Push-ups want a side view near floor height. Hammer curls want a front or side view from the waist up.

**Note:** The counter and skeleton usually appear a few seconds before the video does — MQTT connects faster than the RTSP stream stabilizes. Seeing the overlay before the picture is expected, not an error.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Black screen | Wait 10 seconds for the stream to load; check camera IP is correct |
| Overlay shows but video doesn't | Normal — RTSP takes longer to start than MQTT; wait a few more seconds |
| Stage stuck on "out of frame" | The joints this exercise needs are not visible — for squats, get the ankles in frame |
| Reps not counting | A rep is counted on the way back **up**, when the movement completes; half a rep counts as nothing |
| Counter jumps by two | Slow down slightly — very fast reps can cross both thresholds within the de-bounce window |

### Deployment Complete

Camera is ready! Click **Connect** above to watch the skeleton and rep counter.

Change the exercise, reps and sets any time from the reCamera Console's app page — no redeploy needed. Counts are also published to `recamera/fitness-trainer/results`, and Home Assistant picks up reps, set, exercise and a workout-complete flag automatically via MQTT discovery.

---
