## Preset: reCamera {#recamera}

One camera does everything. The console on the camera carries an app gallery —
install object detection, text reading, face analysis, fall detection or people
counting, switch between them from the browser, and send whatever the running
app produces to Home Assistant over MQTT.

| Device | Purpose |
|--------|---------|
| reCamera | Runs the console, the AI app, RTSP, ONVIF and a local MQTT broker |
| Computer or reComputer R1100 | Optional — runs Home Assistant and the MQTT broker for steps 3 to 5 |

**Only one app holds the camera at a time.** Switching apps stops the previous
one and its RTSP and MQTT output; nothing is uninstalled, and switching back
takes a click.

## Step 1: Update the reCamera Console {#deploy_console type=recamera_cpp required=true config=devices/recamera_console.yaml}

Install console 0.5.5, which manages the camera's apps. Already current? It's skipped.

### Prerequisites

1. Connect the camera over USB, or put it on the same network as this computer.
2. Over USB the address is `192.168.42.1`; over Wi-Fi use the IP your router shows.
3. Username `recamera`, default password `recamera` (older units use `recamera.2`).
4. New devices need SSH enabled first — connect over USB, wait about two minutes for boot, open `http://192.168.42.1/#/security`, sign in, and turn on the SSH toggle.
5. Nothing is reinstalled if the console is already 0.5.5 — the version is checked before anything is touched, and the step reports itself as skipped.
6. The camera's operating system is updated separately, in **Device Management → Embedded → reCamera** in this app. That update is not required for this solution; run it if the camera is on an old release, and note that it flashes the whole system and takes several minutes.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; network: check your router for the IP |
| Password rejected | Default is `recamera`; units shipped with older firmware use `recamera.2` |
| Install failed | Restart the camera and run the step again |
| Node-RED stopped working | Expected — the console takes over the camera pipeline. Switch back from the console's system settings; nothing is uninstalled |
| Want the original panel back | Hold the **User** button while plugging in power and release when the red LED stops blinking and stays on — this factory-resets the camera |

---

## Step 2: Choose and Install an App {#open_console type=web_dashboard required=true config=devices/console_dashboard.yaml}

Open the console, install an app from the gallery, activate it, and watch the results.

### Prerequisites

1. Sign in with the camera's own credentials, the same ones as the previous step.
2. Open **Applications**. Installed apps are listed; **Install from cloud** shows what else is available.
3. Your browser does the downloading and pushes the bytes to the camera, so the camera needs no internet of its own — but this computer does.
4. Pick one app and press **Install**. Models come with it, so an app can be a few hundred megabytes; the console shows the size first.
5. Activate the app. Switching hands the camera over and stops whatever was running before.
6. Press **Debug** on the running app to see the live view and its detection results.

### Deployment Complete

The camera is running the app you picked and is usable on its own from here.

The console is at `http://<camera-ip>/`: the app gallery to install or switch
apps, the live view to check what the camera sees, and network, privacy and
system settings on the other pages.

The apps also answer ONVIF, so an NVR or video management system can discover
the camera and pull its stream without you typing an RTSP address.

Steps 3 to 5 are optional. Do them if you want the results in Home Assistant
rather than only on the camera's own page.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Give the camera a minute to finish restarting, then refresh |
| Login rejected | Use the camera's own credentials, default `recamera` / `recamera` |
| Cannot reach the app catalog | This computer cannot reach `sensecraft-statics.seeed.cc`. Use **Upload .deb** instead, or fix the network on this computer — the camera is not the problem |
| Not enough storage | Uninstall an app you are not using; the console reports how much it needs against how much is free |
| Live view is black | No app is running. Activate one from the gallery first |
| App is listed but will not start | Its files are missing. Uninstall it and install it again |
| Camera won't start after enabling privacy blur | That setting swaps a video kernel module and needs a full power cycle — unplug the camera and plug it back in rather than using a software reboot |

---

## Step 3: Deploy Home Assistant {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant and an MQTT broker. Skip this if you already run both.

### Target {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk.
3. Ports 8123 and 1883 free.

### Deployment Complete

1. Open **http://localhost:8123** and follow the onboarding wizard to create your admin account.
2. An MQTT broker is now listening on port 1883 of this machine. Step 4 asks for its address.
3. The broker runs beside Home Assistant rather than on the camera on purpose: it has to outlive any single camera and any app switch.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 busy | Something already uses it — an existing Home Assistant or Mosquitto. Stop it, or skip this step and use what you have |
| Docker not starting | Open the Docker Desktop application |
| Container keeps restarting | Make sure at least 2 GB RAM is available |

### Target {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

### Prerequisites

1. The target device is on the network and reachable over SSH.
2. Docker is installed and running on it.
3. Enter its IP address, username and password below.

### Deployment Complete

1. Open **http://\<device-ip\>:8123** and follow the onboarding wizard to create your admin account.
2. The MQTT broker listens on port 1883 of that same device. Step 4 asks for its address.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check the network, test with ping |
| SSH authentication failed | Verify the username and password |
| Port 1883 busy on the target | A broker is already running there — keep it and point step 4 at it instead |

---

## Step 4: Connect the Camera to Home Assistant {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

Point Home Assistant and the camera at the same broker. The entities appear on their own.

### Prerequisites

1. Home Assistant is running and you can sign in.
2. An MQTT broker is reachable — the one from step 3, or your own.
3. The camera is running an app, from step 2.

### Deployment Complete

The camera's detection results are now in Home Assistant.

The entities come from MQTT discovery, so nothing is added by hand and the set
changes on its own when you switch to a different app on the camera. Discovery
carries results, not video: for a picture in the dashboard, add the camera's
RTSP URL with the built-in **Generic Camera** integration — the console's
Integrations page shows the exact URL with a copy button.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Test Connection fails on the camera | The broker address must be reachable *from the camera*, not just from this computer. Check that it is the broker's machine address and not `localhost` |
| Saved, but nothing appears in Home Assistant | Confirm the MQTT integration in Home Assistant points at the same broker and port, then restart the running app from the console |
| Entities appear but stay unavailable | No app is running on the camera, or the app was stopped. Activate one from the gallery |
| Entities vanished after switching apps | Expected — each app publishes its own entity set. The previous app's entities are removed when it stops |

---

## Step 5: See the Results in Home Assistant {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Put the picture and the detections on one card.

### Prerequisites

1. **Find what discovery already made.** Settings → Devices & Services → MQTT → the camera's device. Its entities are listed there; note the ones you want on the dashboard.
2. **Add the video separately.** Discovery carries results, not video. Settings → Devices & Services → Add integration → **Generic Camera**, and paste the camera's stream URL:
   - Stream Source URL: `rtsp://<camera-ip>:8554/live0`
   - RTSP transport protocol: **TCP**
   - Leave Verify SSL certificate unticked
   The console's Integrations page shows this exact URL with a copy button, next to a go2rtc snippet if you would rather restream it for lower latency.
3. **Build the card.** Settings → Dashboards → open your dashboard → the pencil to edit → **+ Add card** → **Picture glance**. Set Camera Entity to the Generic Camera you just added, then add the detection entities to the Entities list. They render as icons over the live picture, and the card shows their state on hover.
4. **Or keep them apart.** An **Entities** card lists the values as plain rows, which reads better for counts and timestamps than icons over video. A **History** card on the same entities shows how they moved over the day.
5. **Act on it.** Settings → Automations & scenes → Create automation → trigger **Entity → State** on a detection entity. That is the point of having the values in Home Assistant rather than on the camera.

### Deployment Complete

The camera is now a device in Home Assistant like any other: a picture, a set of
states, and history behind them.

Anything you switch to on the camera republishes its own entities, so the MQTT
device changes shape while the Generic Camera stays put — the video is tied to
the RTSP stream, not to the app.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Generic Camera says it cannot connect | Test the URL in VLC first. If VLC works and Home Assistant does not, force RTSP transport to TCP — UDP is the usual difference |
| Picture is black or stalls after a few seconds | Something else already holds the stream. The camera serves a limited number of RTSP clients; close the console's live view and any VLC window |
| Card shows the camera but no detection icons | Those entities come from MQTT, not from the camera integration. Confirm they exist under Settings → Devices & Services → MQTT before adding them to the card |
| Entities show `unknown` | The app publishes on change, so a fresh entity stays unknown until something happens in front of the camera |
| Picture glance will not accept an entity | It only takes entities with a state, not the device. Add the individual entities rather than the device row |

---

## Preset: reCamera Pro {#recamera_pro}

The same flow on the newer camera. Its App Center carries the apps, each app
carries its own output settings, and the results reach Home Assistant the same
way.

| Device | Purpose |
|--------|---------|
| reCamera Pro | Runs the App Center, the AI app, RTSP, and each app's own MQTT configuration |
| Computer or reComputer R1100 | Optional — runs Home Assistant and the MQTT broker for steps 3 to 5 |

**Two differences that matter.** This camera ships no MQTT broker of its own,
so results stay on the device until you give it a broker address in step 4 —
and that address is set per app, not once for the camera.

## Step 1: Check and Update Firmware {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

Only needed once, and only if your camera has no App Center yet.

![Device Management, the Embedded tab, and the reCamera Pro entry with its address and ADB port](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/recamera-pro-firmware-update-a9539b3d.gif)

### Prerequisites

1. Open the camera's page first — if the **App Center** is there, skip this step.
2. In this app: **Device Management → Embedded → reCamera Pro**, fill in the camera's address, then **Check for device updates**.
3. It uses **ADB on port 5555**, not SSH, so the camera must be on the network — USB alone is not enough.
4. The update reboots the camera and takes a few minutes. Do not power it off.
5. It keeps a copy of the factory files, so **Factory reset** on the same page can roll it back.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Test connection fails | Check the address, and that port 5555 is reachable from this computer |
| Nothing happens after Check for device updates | The camera may already be up to date — look for the App Center on its page |
| App Center still missing afterwards | Reload the page; the camera needs a moment after its reboot |

---

## Step 2: Choose and Install an App {#open_appcenter_pro type=web_dashboard required=true config=devices/recamera_pro_apps.yaml}

Open the App Center, install an app, start it, and watch what it detects.

### Prerequisites

1. Sign in with the camera dashboard's credentials — these are not SSH credentials.
2. Open **App Center** in the sidebar. Installed apps are listed there; the **+** button opens an install dialog that reads the online catalog.
3. Your browser downloads each package, checks its SHA-256 and uploads it to the camera, so the camera itself never reaches the internet — this computer does. Models already on the device are skipped, and the dialog says how many are left to transfer.
4. Some apps need a runtime component as well. The dialog asks before downloading it; declining cancels the install rather than leaving a half-installed app.
5. Press **Start** on the app's card. Only one inference app runs at a time, so starting one stops the other.
6. The App Center has no preview of its own. Open **Live Preview** or **Live View** in the sidebar to see the picture and the detections.

### Deployment Complete

The camera is running the app you picked.

Results are visible on the camera's own pages and go no further until step 4 —
unlike the reCamera, this one has no broker on board.

Steps 3 to 5 are optional. Do them if you want the results in Home Assistant.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The page does not open | Enter the address as `http://` and let the browser follow the redirect. The firmware has an HTTPS switch: with it on, port 80 redirects to 443; with it off, an `https://` address redirects back to 80 |
| Certificate warning | Expected when the HTTPS switch is on — the camera signs its own certificate. Continue past the warning |
| App Center is empty or asks you to sign in | The management API is gated by the dashboard's own login cookie. Sign in to the dashboard first, then reopen the tab |
| Failed to load catalog | This computer cannot reach `sensecraft-statics.seeed.cc`. The catalog URL is editable in the install dialog if you host your own |
| Checksum mismatch — refusing to install | The download was corrupted or the package was republished. Reload the catalog and retry |
| An app is listed but will not start | Its model is missing. Reinstall it — the install downloads the model with the app |
| No detections in Live Preview | Another inference app may still hold the camera; confirm the one you installed is the running one |

---

## Step 3: Deploy Home Assistant {#deploy_ha_pro type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

Start Home Assistant and an MQTT broker. Skip this if you already run both.

### Target {#ha_local_pro type=local config=devices/homeassistant_deploy.yaml default=true}

### Prerequisites

1. Docker Desktop installed and running.
2. At least 2 GB free disk.
3. Ports 8123 and 1883 free.

### Deployment Complete

1. Open **http://localhost:8123** and follow the onboarding wizard to create your admin account.
2. An MQTT broker is now listening on port 1883 of this machine. Step 4 asks for its address.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 busy | Something already uses it — an existing Home Assistant or Mosquitto. Stop it, or skip this step and use what you have |
| Docker not starting | Open the Docker Desktop application |
| Container keeps restarting | Make sure at least 2 GB RAM is available |

### Target {#ha_remote_pro type=remote config=devices/homeassistant_deploy.yaml}

### Prerequisites

1. The target device is on the network and reachable over SSH.
2. Docker is installed and running on it.
3. Enter its IP address, username and password below.

### Deployment Complete

1. Open **http://\<device-ip\>:8123** and follow the onboarding wizard to create your admin account.
2. The MQTT broker listens on port 1883 of that same device. Step 4 asks for its address.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check the network, test with ping |
| SSH authentication failed | Verify the username and password |
| Port 1883 busy on the target | A broker is already running there — keep it and point step 4 at it instead |

---

## Step 4: Connect the Camera to Home Assistant {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

Point Home Assistant and the camera at the same broker. The entities appear on their own.

### Prerequisites

1. Home Assistant is running and you can sign in.
2. An MQTT broker is reachable — the one from step 3, or your own.
3. The camera is running an app, from step 2.

### Deployment Complete

The camera's detection results are now in Home Assistant.

**This setting belongs to the app you configured, not to the camera.** Install
another app later and its MQTT output starts off — open its Configure dialog and
repeat this step. That also means switching between two configured apps swaps
one entity set for the other without any further setup.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No Result output group in Configure | That app does not declare an output capability, so it has no MQTT to configure. Its results stay on the device |
| Nothing arrives at the broker | Check the broker address is reachable *from the camera*, not just from this computer. This camera has no broker of its own, so an empty address means nothing leaves the device |
| Save is refused | The form blocks an MQTT channel with no broker host, and a base topic that is empty or contains `+`, `#` or a space |
| Saved, but nothing appears in Home Assistant | Confirm Output mode is **Home Assistant** rather than Custom or Raw JSON, and that the MQTT integration in Home Assistant points at the same broker and port |
| Entities appear but stay unavailable | No app is running on the camera. Start one from the App Center |
| Entities vanished after starting a different app | Expected — each app declares its own entity set, and an unconfigured app publishes none |

---

## Step 5: See the Results in Home Assistant {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

Put the picture and the detections on one card.

### Prerequisites

1. **Find what discovery already made.** Settings → Devices & Services → MQTT → the camera's device. Its entities are listed there; note the ones you want on the dashboard.
2. **Turn RTSP on and read its address off the camera.** On the camera: **Live View → Stream Settings**, pick RTSP as the protocol and enable it. The stream URL appears there with a copy button — the firmware supplies it, so copy it rather than guessing a path. Set a username and password on the same page if you want the stream authenticated.
3. **Add the video separately.** Discovery carries results, not video. In Home Assistant: Settings → Devices & Services → Add integration → **Generic Camera**, paste that URL, and set RTSP transport protocol to **TCP**. If you enabled authentication, put the credentials in the URL as `rtsp://user:password@…`.
4. **Build the card.** Settings → Dashboards → open your dashboard → the pencil to edit → **+ Add card** → **Picture glance**. Set Camera Entity to the Generic Camera, then add the detection entities to the Entities list.
5. **Or keep them apart.** An **Entities** card lists the values as plain rows; a **History** card on the same entities shows how they moved over the day.
6. **Act on it.** Settings → Automations & scenes → Create automation → trigger **Entity → State** on a detection entity.

### Deployment Complete

The camera is now a device in Home Assistant like any other: a picture, a set of
states, and history behind them.

The video and the detections arrive by different routes and behave differently
when you change apps: the Generic Camera keeps working because it reads the
firmware's stream, while the MQTT entities are replaced by whatever the newly
started app publishes — and an app you have not configured for MQTT publishes
none.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No stream URL under Stream Settings | RTSP is not enabled yet, or another protocol is selected. The three are mutually exclusive — picking RTSP turns RTMP and ONVIF off |
| Generic Camera says it cannot connect | Test the URL in VLC first. If VLC works and Home Assistant does not, force RTSP transport to TCP. If you set credentials on the camera, they belong in the URL |
| Picture is black or stalls after a few seconds | Something else already holds the stream; close the camera's own Live Preview and any VLC window |
| Card shows the camera but no detection icons | Those entities come from MQTT. Confirm the running app has MQTT configured (step 4) and that the entities exist under Settings → Devices & Services → MQTT |
| Entities show `unknown` | The app publishes on change, so a fresh entity stays unknown until something happens in front of the camera |
