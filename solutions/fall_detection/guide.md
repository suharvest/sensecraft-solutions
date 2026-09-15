## Preset: reCamera 2002 {#recamera}

A reCamera 2002 decides on-device whether someone fell and publishes the event over MQTT.

**Important:** this is an assistive alert, not a certified medical or life-safety system. Long shots, occlusion, low light and fall-like floor activities remain weak cases.

## Step 1: Update the reCamera Console {#update_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

Install console 0.5.5, which manages the camera apps. Already current? It's skipped.

### Prerequisites

1. Connect the reCamera over USB, or put it on the same network as this computer.
2. Over USB the address is `192.168.42.1`; over Wi-Fi use the IP your router shows.
3. The default password is `recamera` (older units use `recamera.2`).
4. The next step, installing fall detection, needs this console version.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Cannot connect | Confirm SSH is enabled and the IP and password are correct |
| Console page does not load after install | Give it 30 seconds to restart, then reload `http://<camera-ip>/` |
| Password rejected | Try `recamera.2`; units shipped with older firmware use it |

---

## Step 2: Install Fall Detection {#deploy_recamera_fall type=recamera_cpp required=true config=devices/recamera_fall.yaml}

Install the pose model and the fall detector, then start it on the camera.

### Wiring

![Camera placement: a side or corner view at 2–3 m works; straight-down and long-shot or occluded views do not.](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/camera-placement-be3fb598.svg)

1. Mount the camera rigidly with a clear, wide view of the area you want covered.
2. Keep the whole person — especially shoulders and hips — visible along the path where a fall would happen.
3. Aim for a side or corner view of the floor area rather than looking straight down.
4. Point it at circulation space, not primarily at a bed or an exercise area — everyday floor activities there read as falls until you have validated them separately.
5. Expect it to detect the fall itself, not the aftermath: starting it while someone is already lying down reports the posture but raises no event.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Service exits immediately | Another camera app is still running; only one app can hold the camera, so reboot and retry |
| Node-RED stopped working after install | Expected — installing takes the camera from Node-RED and any other vision app |
| Falls are missed | Widen the view, improve lighting, keep shoulders and hips visible before and after impact |
| Push-ups trigger an alert | A known fall-like activity; change the view or add downstream human confirmation |
| No MQTT messages | Confirm port 1883 is reachable from your computer and the topic is `recamera/fall-detection/results` |

---

## Step 3: Watch Fall Status {#preview_recamera_fall type=preview required=false config=devices/preview_recamera_fall.yaml}

Click **Connect** to see the skeleton, the state and the event number live.

### Deployment Complete

Alerts go to `recamera/fall-detection/results`, and Home Assistant discovery creates fall state, event ID and person presence entities.

#### Quick verification

1. Click **Connect** and wait for the video to appear.
2. Walk into view — the skeleton should follow you and the card should read
   `NORMAL`.
3. Lie down deliberately on the floor. Within roughly two seconds the card should
   turn red and show a new event number.

#### Next steps

- Add the camera to Home Assistant — the entities appear automatically once your
  broker is shared with it.
- Run a site acceptance test with representative falls and normal activity before
  enabling any notification workflow.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Overlay appears before video | MQTT connects faster than RTSP; wait a few seconds |
| Skeleton disappears near the floor | Reframe the camera; a short post-impact gap is tolerated, long occlusion cannot be classified |
| No overlay at all | Confirm MQTT port 1883 is reachable and the topic matches |

---

## Step 4: Install the Alarm Panel (optional) {#panel_host_recamera type=docker_deploy required=false config=devices/panel_host.yaml}

Skip this step and the deployment is finished: the camera keeps publishing MQTT
events and nothing else changes.

Take it and you install an alarm panel on a separate host: a site overview, zones drawn on the live picture, a no-person and a no-motion timeout per zone, operator confirm or dismiss for each alarm, an audit trail, and a webhook that carries no video.

### Prerequisites

The panel goes on a separate box on the camera's network and needs no AI accelerator: a reComputer R1000 Series, or a Linux machine you already run.

- A x86_64 or arm64 Linux host on the camera's network, with Docker and the
  compose plugin (`docker compose version` has to succeed) and SSH access.
- The exact topic the cameras publish on. Check it from that host before you
  start: `mosquitto_sub -h <camera-or-broker-ip> -t '#' -v`. A reCamera 2002 publishes on `<device-name>/fall-detection/results`, single stream, no stream-id suffix.
- Ports 8080 and 1883 free on that host, or different ports entered in the form.

### Troubleshooting

| Symptom | Action |
|---|---|
| Deploy stops on "Port 8080 is already in use" | Enter another Panel Port in the form, or stop the service the message names. |
| "no message on ... within 20 s" warning at the end | The panel is up but has seen no detector result. Re-check the topic against `mosquitto_sub -t '#' -v`, and that the camera publishes to the broker address entered here. |
| Alarm list stays empty and no-person alarms never fire | The camera has to publish on frames with nobody in view for that timeout to have an input. Falls still work either way. |
| `pull access denied` on `eldercare-alarm-*` | Check that the host can reach the image registry. |

### Target {#panel_host_recamera_remote type=remote device_name="Alarm Panel Host" config=devices/panel_host.yaml default=true}

Deploy to the panel host over SSH.

## Step 5: Open the Alarm Panel {#panel_open_recamera type=web_dashboard required=false config=devices/panel_console.yaml}

Only relevant if you installed the panel in the previous step.

### Deployment Complete

#### Quick verification

- The overview page lists the room you named, with its camera and zone counts.
- An empty alarm list on a quiet site is the correct result — it means the
  service is up and answering.
- To prove the ingest path end to end, drop the zone's no-person timeout to one
  minute on the host (`config/alarm-panel.yaml`, then
  `docker compose restart alarm-panel`), leave the area empty, and confirm an
  alarm appears. Put the real value back afterwards.

#### Next steps

- Draw the zones on the live picture instead of keeping the single whole-frame rectangle the deploy created.
- Point the webhook at your own alerting system if you left it empty.
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a USB microphone and speaker on this host; see Step 6.

### Troubleshooting

| Symptom | Action |
|---|---|
| Page does not load | Check the Panel Port matches what the deploy step used, and that the host firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| A room reads unknown and stream-lost | The panel host cannot reach that camera; check the network. The last-frame time on the card shows when a frame last arrived. |

## Step 6: Voice Check-in (optional) {#voice_checkin_recamera type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service asks the resident out loud whether they are all right and acts on the answer; turning it off leaves the alarm path unchanged.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

### Prerequisites

An OpenVoiceStream instance on the same LAN, with a USB microphone and a speaker plugged into the box running it, not into the camera.

### Deployment Complete

A distress word beats a safe word in the same sentence.

**Privacy:** audio is never written to disk. The audit trail keeps the verdict, confidence, latency and transcribed text; `store_transcript: false` drops the text. Notifications carry no snapshot and no video.

#### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.

### Troubleshooting

| Symptom | Action |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | Confirm the alarm host's audio device is passed into the container, and check `docker compose logs eldercare-alarm` for TTS or playback errors. |

## Preset: reCamera Pro {#recamera_pro}

A reCamera Pro tracks several people and decides on-device whether someone fell, then publishes the event over MQTT.

**Important:** this is an assistive alert, not a certified medical or life-safety system. Long shots, occlusion, low light and fall-like floor activities remain weak cases.

The detector ships in the device's own App Center; this preset **configures the installed app and makes it the running app**. If your device does not have it yet, install it from the App Center first.

## Step 1: Update the Camera Firmware {#firmware_recamera_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

Only needed once, and only if your camera has no App Center yet.

![Device Management, the Embedded tab, and the reCamera Pro entry with its address and ADB port](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/recamera-pro-firmware-update-a9539b3d.gif)

### What to check

- Open the camera's page first — if **App Center** is there with Fall Detection, skip this step.
- In this app: **Device Management → Embedded → reCamera Pro**, fill in the camera's address, then **Check for device updates**.
- It uses **ADB on port 5555**, not SSH, so the camera must be on the network — USB alone is not enough.
- The update reboots the camera and takes a few minutes. Do not power it off.
- It keeps a copy of the factory files, so **Factory reset** on the same page can roll it back.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Test connection fails | Check the address, and that port 5555 is reachable from this computer |
| Nothing happens after Check for device updates | The camera may already be up to date — look for the App Center on its page |
| App Center still missing afterwards | Reload the page; the camera needs a moment after its reboot |

## Step 2: Configure Fall Detection {#deploy_recamera_pro_fall type=recamera_pro_app required=true config=devices/recamera_pro_fall.yaml}

Point the app at your MQTT broker and make it the running app.

### What to check

- The device runs **one app at a time**, so activating this one stops whatever is currently running.
- **MQTT is optional.** Leave the broker address empty and you watch results on the device's own page; fill it in to forward events to Home Assistant. This camera ships no broker, unlike the 2002.
- The credentials are the **web console's**, not SSH.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| "not installed on this device" | Install Fall Detection from the device's App Center, then run this step again |
| Login rejected | Repeated failures lock your IP for an increasing delay — confirm the password in the console before retrying |
| Nothing arrives on MQTT | Check the broker address is reachable *from the camera*, not just from your computer. If you left it empty, results only appear on the device page — that is by design |

### Target {#recamera_pro_device type=remote device_name="reCamera Pro" config=devices/recamera_pro_fall.yaml}

## Step 3: Watch Fall Status {#verify_recamera_pro_fall type=web_dashboard required=false config=devices/verify_recamera_pro_fall.yaml}

Open the device console and watch the live view while someone walks in front of
the camera.

### Deployment Complete

The camera is now publishing fall events to your broker.

#### What it publishes

| Topic | Content |
|---|---|
| `<device-name>/fall-detection/summary` | `person_count`, `fallen_count` |
| `<device-name>/fall-detection/fall` | `fall_event` on the transition |

These topics carry no skeleton data; the live view with skeletons is on the device console page, opened by this step.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| The camera's page does not open | The firmware has an HTTPS switch; port 80 answers with a redirect to 443. Follow it, or open the `https://` address directly |
| Live view works but no fall events reach the broker | Check the broker address and port in the previous step; the summary topic only appears once a person is detected |
| Fall Detection is listed but will not start | Its AI model is missing. Reinstall it from the App Center on the camera — the install downloads the model with the app |
| A fall is missed near the floor | Reframe the camera; a short post-impact gap is tolerated, long occlusion cannot be classified |

### Target {#recamera_pro_verify type=remote device_name="reCamera Pro" config=devices/verify_recamera_pro_fall.yaml}

## Step 4: Install the Alarm Panel (optional) {#panel_host_recamera_pro type=docker_deploy required=false config=devices/panel_host.yaml}

Skip this step and the deployment is finished: the camera keeps publishing MQTT
events and nothing else changes.

Take it and you install an alarm panel on a separate host: a site overview, zones drawn on the live picture, a no-person and a no-motion timeout per zone, operator confirm or dismiss for each alarm, an audit trail, and a webhook that carries no video.

### Prerequisites

The panel goes on a separate box on the camera's network and needs no AI accelerator: a reComputer R1000 Series, or a Linux machine you already run.

- A x86_64 or arm64 Linux host on the camera's network, with Docker and the
  compose plugin (`docker compose version` has to succeed) and SSH access.
- The exact topic the cameras publish on. Check it from that host before you
  start: `mosquitto_sub -h <camera-or-broker-ip> -t '#' -v`. A reCamera Pro publishes on `<base>/fall-detection/state`; pick reCamera Pro as the Camera Model in the form so the Pro adapter is used.
- Ports 8080 and 1883 free on that host, or different ports entered in the form.

### Troubleshooting

| Symptom | Action |
|---|---|
| Deploy stops on "Port 8080 is already in use" | Enter another Panel Port in the form, or stop the service the message names. |
| "no message on ... within 20 s" warning at the end | The panel is up but has seen no detector result. Re-check the topic against `mosquitto_sub -t '#' -v`, and that the camera publishes to the broker address entered here. |
| Alarm list stays empty and no-person alarms never fire | The camera has to publish on frames with nobody in view for that timeout to have an input. Falls still work either way. |
| `pull access denied` on `eldercare-alarm-*` | Check that the host can reach the image registry. |

### Target {#panel_host_recamera_pro_remote type=remote device_name="Alarm Panel Host" config=devices/panel_host.yaml default=true}

Deploy to the panel host over SSH.

## Step 5: Open the Alarm Panel {#panel_open_recamera_pro type=web_dashboard required=false config=devices/panel_console.yaml}

Only relevant if you installed the panel in the previous step.

### Deployment Complete

#### Quick verification

- The overview page lists the room you named, with its camera and zone counts.
- An empty alarm list on a quiet site is the correct result — it means the
  service is up and answering.
- To prove the ingest path end to end, drop the zone's no-person timeout to one
  minute on the host (`config/alarm-panel.yaml`, then
  `docker compose restart alarm-panel`), leave the area empty, and confirm an
  alarm appears. Put the real value back afterwards.

#### Next steps

- Draw the zones on the live picture instead of keeping the single whole-frame rectangle the deploy created.
- Point the webhook at your own alerting system if you left it empty.
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a USB microphone and speaker on this host; see Step 6.

### Troubleshooting

| Symptom | Action |
|---|---|
| Page does not load | Check the Panel Port matches what the deploy step used, and that the host firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| A room reads unknown and stream-lost | The panel host cannot reach that camera; check the network. The last-frame time on the card shows when a frame last arrived. |

## Step 6: Voice Check-in (optional) {#voice_checkin_recamera_pro type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service asks the resident out loud whether they are all right and acts on the answer; turning it off leaves the alarm path unchanged.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

### Prerequisites

An OpenVoiceStream instance on the same LAN, with a USB microphone and a speaker plugged into the box running it, not into the camera.

### Deployment Complete

A distress word beats a safe word in the same sentence.

**Privacy:** audio is never written to disk. The audit trail keeps the verdict, confidence, latency and transcribed text; `store_transcript: false` drops the text. Notifications carry no snapshot and no video.

#### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.

### Troubleshooting

| Symptom | Action |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | Confirm the alarm host's audio device is passed into the container, and check `docker compose logs eldercare-alarm` for TTS or playback errors. |

## Preset: IP Camera + reComputer J30 / J40 {#jetson}

A reComputer J30 / J40 pulls the RTSP streams of your existing IP cameras and tracks several people per stream independently.

- **Camera:** any ONVIF or RTSP IP camera.

**Important:** this is an assistive alert, not a certified medical or life-safety system. Long shots and occlusion lower recall.

## Step 1: Deploy Fall Detection {#deploy_jetson_fall type=docker_deploy required=true config=devices/jetson_fall.yaml}

Deploy the detector and build its inference engine on the Jetson. Allow 10–20 min.

### Prerequisites

1. The Jetson runs JetPack 6.x with the NVIDIA container runtime available.
2. At least 10 GB free disk.
3. Your IP camera's RTSP URL, including credentials if it requires them, for
   example `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`.
4. The first deploy spends most of its time building the inference engine on the device; later deployments reuse it.
5. Match the pose model to the board: **YOLO11s** for Orin Nano, **YOLO11m** for Orin NX.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Engine build fails | Confirm `/usr/src/tensorrt/bin/trtexec` exists and the disk has 10 GB free |
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |
| Container restarts repeatedly | Check the logs for the engine path; a half-built engine from an interrupted run must be deleted |
| Deploy cannot connect | Confirm SSH is reachable and the username is right — Seeed images use `recomputer` or `nvidia` |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_fall.yaml default=true}

Deploy to the Jetson over SSH from this computer.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_fall.yaml}

Run this directly on the Jetson if you are working on the device itself.

---

## Step 2: Watch Fall Status {#preview_jetson_fall type=preview required=false config=devices/preview_jetson_fall.yaml}

Click **Connect** to see each tracked person boxed, labelled and state-coloured.

### Deployment Complete

Results go to `recamera/fall-detection/results/<stream-id>`, one topic per camera.

#### Quick verification

1. Click **Connect** and wait for the camera's video to appear.
2. Walk into view — a box should follow you, labelled with a track number and
   `NORMAL`.
3. Lie down deliberately. The box should turn red and the card should show a new
   event number.

#### Adding more cameras

The detector handles several streams at once. Add them to the `streams` list in
the configuration on the device and restart the container; each stream keeps its
own tracking state and gets its own MQTT topic.

#### Next steps

- Point your alerting system at the MQTT topic, or add the broker to Home
  Assistant to pick up the discovery entities.
- Measure the actual frame rate on site before adding streams.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the Jetson is reachable |
| Overlay but no video | The preview pulls RTSP straight from the camera; confirm this computer can reach it too |
| Boxes flicker between people | Raise the tracker IoU threshold, or reframe so people overlap less |

---

## Step 3: Open the Alarm Panel {#panel_open_jetson type=web_dashboard required=false config=devices/panel_console.yaml}

The alarm panel was deployed with the detector in Step 1 on the same device, port 8080 by default. It provides a site overview, zones drawn on the live picture, a no-person and a no-motion timeout per zone, confirm and dismiss recorded against an operator, and a webhook that carries no video.

### Deployment Complete

#### Quick verification

- The overview page lists the zone you named in the deploy form.
- An empty alarm list on a quiet site is the correct result — it means the
  service is up and answering.
- To prove the ingest path end to end, drop the zone's no-person timeout to one
  minute on the device (`config/alarm-panel.yaml`, then
  `docker compose restart alarm-panel`), leave the area empty, and confirm an
  alarm appears. Put the real value back afterwards.

#### Next steps

- Draw the zones on the live picture instead of keeping the single whole-frame
  rectangle the deploy created.
- Point the webhook at your own alerting system if you left it empty.
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a USB microphone and speaker on this device; see Step 4.

### Troubleshooting

| Symptom | Action |
|---|---|
| Page does not load | Check the Alarm Panel Port matches what the deploy step used, and that the device firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| Falls raise alarms but no-person alarms never do | The detector config ships `publish_empty_frames: true`, which that timeout depends on. If you replaced `config/config.json` with the device's own copy, set the key again. |

## Step 4: Voice Check-in (optional) {#voice_checkin_jetson type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service asks the resident out loud whether they are all right and acts on the answer; turning it off leaves the alarm path unchanged.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

### Prerequisites

An OpenVoiceStream instance on the same LAN, with a USB microphone and a speaker plugged into the box running it, not into the camera.

### Deployment Complete

A distress word beats a safe word in the same sentence.

**Privacy:** audio is never written to disk. The audit trail keeps the verdict, confidence, latency and transcribed text; `store_transcript: false` drops the text. Notifications carry no snapshot and no video.

#### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.

### Troubleshooting

| Symptom | Action |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | Confirm the alarm host's audio device is passed into the container, and check `docker compose logs eldercare-alarm` for TTS or playback errors. |

## Preset: IP Camera + reComputer RK3576 / RK3588 {#rk}

The detector runs on the NPU of a reComputer RK3576 / RK3588, with the same MQTT output as the other presets.

- **Camera:** any ONVIF or RTSP IP camera.

**Important:** this is an assistive alert, not a certified medical or life-safety system.

## Step 1: Deploy Fall Detection {#deploy_rk_fall type=docker_deploy required=true config=devices/rk3588_fall.yaml}

Deploy the detector to your Rockchip board. Allow about 5 minutes.

### Prerequisites

1. The board runs a vendor image with the NPU driver and `librknnrt.so` present, plus Docker.
2. At least 6 GB free disk for the runtime image and the pose model.
3. Your IP camera's RTSP URL, with credentials if it needs them.
4. Choose the deployment target that matches your board; RK3588 and RK3576 models are not interchangeable. This deployment installs one camera stream.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| `librknnrt.so not found` | Install the board's `rknpu2` runtime package |
| Model fails to load | The model must match the board — re-run the step with the correct board selected |
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |
| Low frame rate | Other NPU workloads compete for the accelerator; check what else is running on the board |

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_fall.yaml default=true}

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_fall.yaml}

### Target {#rk_local type=local device=rk3588 device_name="reComputer RK3576 / RK3588" config=devices/rk_auto_fall.yaml}

---

## Step 2: Watch Fall Status {#preview_rk_fall type=preview required=false config=devices/preview_rk_fall.yaml}

Click **Connect** to see each tracked person boxed, labelled and state-coloured.

### Deployment Complete

The board is publishing to `recamera/fall-detection/results/<stream-id>`, one topic
per camera.

#### Quick verification

1. Click **Connect** and wait for the camera's video to appear.
2. Walk into view — a box should follow you, labelled with a track number.
3. Lie down deliberately. The box should turn red and the card should show a new
   event number.

#### Next steps

- Point your alerting system at the MQTT topic, or add the broker to Home Assistant.
- Run a site acceptance test before relying on it.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the board is reachable |
| Skeleton offset from the person | Report it to Seeed |
| Boxes flicker between people | Raise the tracker IoU threshold, or reframe so people overlap less |

---

## Step 3: Open the Alarm Panel {#panel_open_rk type=web_dashboard required=false config=devices/panel_console.yaml}

The alarm panel was deployed with the detector in Step 1 on the same device, port 8080 by default. It provides a site overview, zones drawn on the live picture, a no-person and a no-motion timeout per zone, confirm and dismiss recorded against an operator, and a webhook that carries no video.

### Deployment Complete

#### Quick verification

- The overview page lists the zone you named in the deploy form.
- An empty alarm list on a quiet site is the correct result — it means the
  service is up and answering.
- To prove the ingest path end to end, drop the zone's no-person timeout to one
  minute on the device (`config/alarm-panel.yaml`, then
  `docker compose restart alarm-panel`), leave the area empty, and confirm an
  alarm appears. Put the real value back afterwards.

#### Next steps

- Draw the zones on the live picture instead of keeping the single whole-frame
  rectangle the deploy created.
- Point the webhook at your own alerting system if you left it empty.
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a USB microphone and speaker on this device; see Step 4.

### Troubleshooting

| Symptom | Action |
|---|---|
| Page does not load | Check the Alarm Panel Port matches what the deploy step used, and that the device firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| Falls raise alarms but no-person alarms never do | That timeout needs the detector to publish on frames with nobody in view; confirm the MQTT topic still gets messages when nobody is in front of the camera. |

## Step 4: Voice Check-in (optional) {#voice_checkin_rk type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service asks the resident out loud whether they are all right and acts on the answer; turning it off leaves the alarm path unchanged.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

### Prerequisites

An OpenVoiceStream instance on the same LAN, with a USB microphone and a speaker plugged into the box running it, not into the camera.

### Deployment Complete

A distress word beats a safe word in the same sentence.

**Privacy:** audio is never written to disk. The audit trail keeps the verdict, confidence, latency and transcribed text; `store_transcript: false` drops the text. Notifications carry no snapshot and no video.

#### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.

### Troubleshooting

| Symptom | Action |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | Confirm the alarm host's audio device is passed into the container, and check `docker compose logs eldercare-alarm` for TTS or playback errors. |

## Preset: IP Camera + reComputer R2000 (Hailo) {#hailo}

The detector runs on a reComputer R2000 with a Hailo-8 accelerator, with the same MQTT output as the other presets.

- **Camera:** any ONVIF or RTSP IP camera.

**Important:** this is an assistive alert, not a certified medical or life-safety system.

## Step 1: Deploy Fall Detection {#deploy_hailo_fall type=docker_deploy required=true config=devices/hailo_fall.yaml}

Deploy the detector to your Hailo-equipped device. Allow about 5 minutes.

### Prerequisites

1. A Hailo-8 accelerator present as `/dev/hailo0`, with **HailoRT 4.21** installed (GStreamer plugin, user library and kernel driver all at that version).
2. Docker, and at least 4 GB free disk.
3. Your IP camera's RTSP URL, with credentials if it needs them.
4. The pose model downloads automatically during deployment.
5. Stop any other application using the Hailo accelerator first.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| `No /dev/hailo0` | The accelerator is not seated or its driver is not loaded; check `hailortcli fw-control identify` |
| `libhailort.so.4.21.0 not found` | Install HailoRT 4.21, with plugin, library and driver all at that version |
| Container starts then exits | Stop the other process using the accelerator |
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |
| Deployment stops before verification | Check the detector log for the `HAILO_BATCH` line, container health, and an MQTT result on the configured topic |

### Target {#hailo_remote type=remote device=hailo device_name="reComputer R2000" config=devices/hailo_fall.yaml default=true}

Deploy to the device over SSH from this computer.

### Target {#hailo_local type=local device=hailo device_name="reComputer R2000" config=devices/hailo_fall.yaml}

Run this directly on the device if you are working on it.

---

## Step 2: Watch Fall Status {#preview_hailo_fall type=preview required=false config=devices/preview_hailo_fall.yaml}

Click **Connect** to see each tracked person boxed, labelled and state-coloured.

### Deployment Complete

The device is publishing to `recamera/fall-detection/results/<stream-id>`, one topic
per camera.

#### Quick verification

1. Click **Connect** and wait for the camera's video to appear.
2. Walk into view — a box should follow you, labelled with a track number.
3. Lie down deliberately. The box should turn red and the card should show a new
   event number.

#### Next steps

- Point your alerting system at the MQTT topic, or add the broker to Home Assistant.
- Run a site acceptance test before relying on it.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the device is reachable |
| Overlay but no video | The preview pulls RTSP straight from the camera; confirm this computer can reach it too |
| `inference_time_ms` reads 0 | Expected; the Hailo runtime does not report this value |

## Step 3: Open the Alarm Panel {#panel_open_hailo type=web_dashboard required=false config=devices/panel_console.yaml}

The alarm panel was deployed with the detector in Step 1 on the same device, port 8080 by default. It provides a site overview, zones drawn on the live picture, a no-person and a no-motion timeout per zone, confirm and dismiss recorded against an operator, and a webhook that carries no video.

### Deployment Complete

#### Quick verification

- The overview page lists the zone you named in the deploy form.
- An empty alarm list on a quiet site is the correct result — it means the
  service is up and answering.
- To prove the ingest path end to end, drop the zone's no-person timeout to one
  minute on the device (`config/alarm-panel.yaml`, then
  `docker compose restart alarm-panel`), leave the area empty, and confirm an
  alarm appears. Put the real value back afterwards.

#### Next steps

- Draw the zones on the live picture instead of keeping the single whole-frame
  rectangle the deploy created.
- Point the webhook at your own alerting system if you left it empty.
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a USB microphone and speaker on this device; see Step 4.

### Troubleshooting

| Symptom | Action |
|---|---|
| Page does not load | Check the Alarm Panel Port matches what the deploy step used, and that the device firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| Falls raise alarms but no-person alarms never do | Check that the zone's stream id matches the Stream ID from the deploy form. |

## Step 4: Voice Check-in (optional) {#voice_checkin_hailo type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service asks the resident out loud whether they are all right and acts on the answer; turning it off leaves the alarm path unchanged.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

### Prerequisites

An OpenVoiceStream instance on the same LAN, with a USB microphone and a speaker plugged into the box running it, not into the camera.

### Deployment Complete

A distress word beats a safe word in the same sentence.

**Privacy:** audio is never written to disk. The audit trail keeps the verdict, confidence, latency and transcribed text; `store_transcript: false` drops the text. Notifications carry no snapshot and no video.

#### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.

### Troubleshooting

| Symptom | Action |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | Confirm the alarm host's audio device is passed into the container, and check `docker compose logs eldercare-alarm` for TTS or playback errors. |

