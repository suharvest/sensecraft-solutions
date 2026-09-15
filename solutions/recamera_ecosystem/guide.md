## Preset: reCamera {#recamera}

Install object detection, text reading, face analysis, fall detection or people counting from the reCamera console, switch between them in the browser, and optionally send the results to Home Assistant over MQTT.

- **Devices:** reCamera; steps 4 to 6 (Home Assistant) also need a computer or reComputer R1100.
- **Network:** this computer needs internet access while installing apps.
- **Limit:** one app runs at a time. Switching apps stops the previous one and its RTSP and MQTT output; nothing is uninstalled.

## Step 1: Update the reCamera Console {#deploy_console type=recamera_cpp required=true config=devices/recamera_console.yaml}

Install console 0.5.5. The step is skipped if the camera is already on that version.

### Prerequisites

1. Connect the camera over USB (address `192.168.42.1`), or put it on the same network as this computer (use the IP your router shows).
2. Username `recamera`, default password `recamera` (older units use `recamera.2`).
3. New devices need SSH enabled first: connect over USB, wait about two minutes, open `http://192.168.42.1/#/security`, sign in, and turn on the SSH toggle.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cannot connect | USB: use `192.168.42.1`; network: check your router for the IP |
| Password rejected | Default is `recamera`; units with older firmware use `recamera.2` |
| Install failed | Restart the camera and run the step again |
| Node-RED stopped working | The console has taken over the camera; switch back from the console's system settings |
| Want the original panel back | Hold the **User** button while plugging in power and release when the red LED stops blinking and stays on; this factory-resets the camera |

---

## Step 2: Choose and Install an App {#install_app type=recamera_console_app required=true config=devices/recamera_console_app.yaml}

Pick an app from the dropdown and press **Deploy**. Download, install and activation run automatically.

### Prerequisites

1. This computer has internet access; the camera does not need it.
2. Address and password carry over from the previous step.
3. An app with its models can be a few hundred megabytes; progress is shown during deployment.

### Deployment Complete

The camera is running the app you picked. The apps answer ONVIF, so an NVR or video management system can discover the camera and pull its stream.

Steps 4 to 6 are optional and bring the results into Home Assistant.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Dropdown is empty or short | This computer cannot reach `sensecraft-statics.seeed.cc`; fix the network and press refresh |
| Login rejected | Use the camera's credentials, default `recamera` / `recamera` (`recamera.2` on older units). Repeated failures lock login for 60s |
| Console not answering | The camera may still be restarting; wait a minute and deploy again |
| "busy" error | The console is running another app operation; retry when it finishes |
| Not enough storage | Uninstall an unused app from the console first |
| Installed but not running | Check its status on the console's Applications page; if files are missing, deploy this step again |
| Camera won't start after enabling privacy blur | Unplug the camera and plug it back in; a software reboot is not enough |

---

## Step 3: Open the Console {#open_console type=web_dashboard required=true config=devices/console_dashboard.yaml}

Open the camera's console and check the app's detection results.

### Prerequisites

1. Sign in with the camera credentials from step 1.
2. On **Applications**, press **Debug** on the active app for the live view and detection results.
3. Switch apps on **Applications**; **Install from cloud** lists the rest of the catalog.

### Deployment Complete

The console is at `http://<camera-ip>/`: install or switch apps, check the live view, and change network, privacy and system settings.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page won't load | Wait a minute for the camera to finish restarting, then refresh |
| Login rejected | Use the camera's credentials, default `recamera` / `recamera` |
| Live view is black | No app is running; go back one step and deploy an app |

---

## Step 4: Deploy Home Assistant {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant and an MQTT broker. Skip this if you already run both.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk.
3. Ports 8123 and 1883 free.

### Deployment Complete

1. Open **http://localhost:8123** and create your admin account in the onboarding wizard.
2. The MQTT broker listens on port 1883 of this machine. Step 5 asks for its address.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port 8123 or 1883 busy | Stop the existing Home Assistant or Mosquitto, or skip this step and use it |
| Docker not starting | Open the Docker Desktop application |
| Container keeps restarting | Make sure at least 2 GB RAM is available |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

### Prerequisites

1. The target device is reachable over SSH and has Docker installed and running.
2. Enter its IP address, username and password below.

### Deployment Complete

1. Open **http://\<device-ip\>:8123** and create your admin account in the onboarding wizard.
2. The MQTT broker listens on port 1883 of that device. Step 5 asks for its address.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection timeout | Check the network, test with ping |
| SSH authentication failed | Verify the username and password |
| Port 1883 busy on the target | A broker is already running there; keep it and enter it in step 5 |

---

## Step 5: Connect the Camera to Home Assistant {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Point Home Assistant and the camera at the same broker. The entities appear automatically.

### Prerequisites

1. Home Assistant is running and you can sign in.
2. An MQTT broker reachable from the camera (from step 4, or your own).
3. An app is running on the camera.

### Deployment Complete

Detection results appear in Home Assistant through MQTT discovery, and the entity set changes when you switch apps. Discovery carries no video; add the picture in step 6.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test Connection fails on the camera | Enter the IP of the broker's machine, not `localhost` |
| Saved, but nothing appears in Home Assistant | Confirm the MQTT integration in Home Assistant uses the same broker and port, then restart the running app from the console |
| Entities appear but stay unavailable | No app is running on the camera; activate one from the console |
| Entities vanished after switching apps | Expected; each app publishes its own entity set |

---

## Step 6: See the Results in Home Assistant {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Put the picture and the detections on one card.

### Prerequisites

1. **Find the entities.** Settings → Devices & Services → MQTT → the camera's device. Note the entities you want on the dashboard.
2. **Add the video.** Settings → Devices & Services → Add integration → **Generic Camera**:
   - Stream Source URL: `rtsp://<camera-ip>:8554/live0` (copy it from the console's Integrations page)
   - RTSP transport protocol: **TCP**
   - Leave Verify SSL certificate unticked
3. **Build the card.** Settings → Dashboards → open your dashboard → pencil to edit → **+ Add card** → **Picture glance**. Set Camera Entity to the Generic Camera, then add the detection entities to the Entities list.
4. **Separate cards (optional).** An **Entities** card lists the values as rows; a **History** card shows how they change.
5. **Automation (optional).** Settings → Automations & scenes → Create automation → trigger **Entity → State** on a detection entity.

### Deployment Complete

The dashboard shows the camera picture and the detection entities. Switching apps changes the MQTT entities; the Generic Camera picture is unaffected.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Generic Camera says it cannot connect | Test the URL in VLC first; if VLC plays and Home Assistant does not, set RTSP transport to TCP |
| Picture is black or stalls after a few seconds | Close the console's live view and any VLC window |
| Card shows the camera but no detection icons | Confirm the entities exist under Settings → Devices & Services → MQTT, then add them to the card |
| Entities show `unknown` | Values appear after something changes in front of the camera |
| Picture glance will not accept an entity | Add individual entities, not the device |

---

## Preset: reCamera Pro {#recamera_pro}

Install apps from the reCamera Pro App Center and optionally send the results to Home Assistant over MQTT.

- **Devices:** reCamera Pro; steps 3 to 5 (Home Assistant) also need a computer or reComputer R1100.
- **Network:** camera and this computer on the same network; this computer needs internet access while installing apps.
- **Limit:** the camera has no built-in MQTT broker, so results stay on the device until you enter a broker address in step 4, and that address is set per app. One inference app runs at a time.

## Step 1: Check and Update Firmware {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

Only needed once, and only if the camera's page has no App Center yet.

![Device Management, the Embedded tab, and the reCamera Pro entry with its address and ADB port](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/recamera-pro-firmware-update-a9539b3d.gif)

### Prerequisites

1. Open the camera's page; if the **App Center** is there, skip this step.
2. In this app: **Device Management → Embedded → reCamera Pro**, fill in the camera's address, then **Check for device updates**.
3. The update uses ADB on port 5555 over the network; USB alone is not enough.
4. The camera reboots during the update, which takes a few minutes. Do not power it off. **Factory reset** on the same page rolls it back.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Test connection fails | Check the address, and that port 5555 is reachable from this computer |
| Nothing happens after Check for device updates | The camera may already be up to date; look for the App Center on its page |
| App Center still missing afterwards | Reload the page after the camera finishes rebooting |

---

## Step 2: Choose and Install an App {#open_appcenter_pro type=web_dashboard required=true config=devices/recamera_pro_apps.yaml}

Open the App Center, install an app and start it.

### Prerequisites

1. Sign in with the camera dashboard's credentials (not SSH credentials).
2. Open **App Center** in the sidebar and press **+** to open the install dialog.
3. If an app needs a runtime component, the dialog asks before downloading it; declining cancels the install.
4. Press **Start** on the app's card. Starting one inference app stops the other.
5. Open **Live Preview** or **Live View** in the sidebar to see the picture and detections.

### Deployment Complete

The camera is running the app you picked. Steps 3 to 5 are optional and bring the results into Home Assistant.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| The page does not open | Enter the address starting with `http://` and let the browser follow the redirect |
| Certificate warning | With HTTPS enabled the camera uses a self-signed certificate; continue past the warning |
| App Center is empty or asks you to sign in | Sign in to the dashboard first, then reopen the tab |
| Failed to load catalog | This computer cannot reach `sensecraft-statics.seeed.cc`; if you host your own catalog, change its URL in the install dialog |
| Checksum mismatch — refusing to install | Reload the catalog and retry |
| An app is listed but will not start | Its model is missing; reinstall the app |
| No detections in Live Preview | Confirm the app you installed is the one running |

---

## Step 3: Deploy Home Assistant {#deploy_ha_pro type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant and an MQTT broker. Skip this if you already run both.

### Target {#ha_local_pro type=local config=devices/homeassistant_deploy.yaml default=true}

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk.
3. Ports 8123 and 1883 free.

### Deployment Complete

1. Open **http://localhost:8123** and create your admin account in the onboarding wizard.
2. The MQTT broker listens on port 1883 of this machine. Step 4 asks for its address.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port 8123 or 1883 busy | Stop the existing Home Assistant or Mosquitto, or skip this step and use it |
| Docker not starting | Open the Docker Desktop application |
| Container keeps restarting | Make sure at least 2 GB RAM is available |

### Target {#ha_remote_pro type=remote config=devices/homeassistant_deploy.yaml}

### Prerequisites

1. The target device is reachable over SSH and has Docker installed and running.
2. Enter its IP address, username and password below.

### Deployment Complete

1. Open **http://\<device-ip\>:8123** and create your admin account in the onboarding wizard.
2. The MQTT broker listens on port 1883 of that device. Step 4 asks for its address.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection timeout | Check the network, test with ping |
| SSH authentication failed | Verify the username and password |
| Port 1883 busy on the target | A broker is already running there; keep it and enter it in step 4 |

---

## Step 4: Connect the Camera to Home Assistant {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

Enter the broker address in the app's configuration; the entities appear in Home Assistant automatically.

### Prerequisites

1. Home Assistant is running and you can sign in.
2. An MQTT broker reachable from the camera (from step 3, or your own).
3. An app is running on the camera.

### Deployment Complete

Detection results appear in Home Assistant. This setting belongs to the current app only: apps you install later start with MQTT output off, so repeat this step in their Configure dialog.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No Result output group in Configure | The app has no MQTT output; its results stay on the device |
| Nothing arrives at the broker | Make sure the broker address is not empty and is reachable from the camera |
| Save is refused | Broker host must not be empty; base topic must not be empty or contain `+`, `#` or a space |
| Saved, but nothing appears in Home Assistant | Set Output mode to **Home Assistant**, and confirm the MQTT integration in Home Assistant uses the same broker and port |
| Entities appear but stay unavailable | No app is running on the camera; start one from the App Center |
| Entities vanished after starting a different app | Expected; each app publishes its own entity set, and an app without MQTT configured publishes none |

---

## Step 5: See the Results in Home Assistant {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

Put the picture and the detections on one card.

### Prerequisites

1. **Find the entities.** Settings → Devices & Services → MQTT → the camera's device. Note the entities you want on the dashboard.
2. **Turn on RTSP.** On the camera: **Live View → Stream Settings**, pick RTSP and enable it, then copy the stream URL shown. Set a username and password on the same page if you want authentication.
3. **Add the video.** In Home Assistant: Settings → Devices & Services → Add integration → **Generic Camera**, paste the URL, and set RTSP transport protocol to **TCP**. With authentication, use `rtsp://user:password@…`.
4. **Build the card.** Settings → Dashboards → open your dashboard → pencil to edit → **+ Add card** → **Picture glance**. Set Camera Entity to the Generic Camera, then add the detection entities to the Entities list.
5. **Separate cards (optional).** An **Entities** card lists the values as rows; a **History** card shows how they change.
6. **Automation (optional).** Settings → Automations & scenes → Create automation → trigger **Entity → State** on a detection entity.

### Deployment Complete

The dashboard shows the camera picture and the detection entities. Switching apps replaces the MQTT entities with the new app's set; the Generic Camera picture is unaffected.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| No stream URL under Stream Settings | RTSP is not enabled or another protocol is selected; picking RTSP turns RTMP and ONVIF off |
| Generic Camera says it cannot connect | Test the URL in VLC first; if VLC plays and Home Assistant does not, set RTSP transport to TCP. Credentials set on the camera go in the URL |
| Picture is black or stalls after a few seconds | Close the camera's Live Preview and any VLC window |
| Card shows the camera but no detection icons | Confirm the running app has MQTT configured (step 4) and the entities exist under Settings → Devices & Services → MQTT |
| Entities show `unknown` | Values appear after something changes in front of the camera |
