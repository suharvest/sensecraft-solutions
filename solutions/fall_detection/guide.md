## Preset: reCamera 2002 {#recamera}

One device does everything: the camera sees the room, decides on-device whether
someone fell, and publishes the event over MQTT.

| Device | Purpose |
|--------|---------|
| reCamera 2002 | Pose estimation, temporal fall logic, RTSP and MQTT, all local |

**Important:** this is an assistive alert, not a certified medical or
life-safety system. On the untouched 27-clip Subject 4 test it reached 74.1%
accuracy and 83.3% fall recall; on an independent external set recall was 58.8%.
Long shots, occlusion, low light and fall-like floor activities remain weak cases.

## Step 1: Update the reCamera Console {#update_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

Install console 0.5.5, which manages the camera apps. Already current? It's skipped.

### Prerequisites

1. Connect the reCamera over USB, or put it on the same network as this computer.
2. Over USB the address is `192.168.42.1`; over Wi-Fi use the IP your router shows.
3. The default password is `recamera` (older units use `recamera.2`).
4. Nothing is reinstalled if the console is already 0.5.5 — the version is checked before anything is touched, and the step reports itself as skipped.
5. The console is what turns fall detection on and off in the camera's app gallery, and what switches between vision apps, so it has to be current before the next step.

### Troubleshooting

| Issue | Solution |
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

| Issue | Solution |
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

The camera is ready for a supervised site trial. Alerts and diagnostics go to
`recamera/fall-detection/results`, and Home Assistant discovery exposes the fall
state, event ID and person presence.

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

| Issue | Solution |
|-------|----------|
| Overlay appears before video | MQTT connects faster than RTSP; wait a few seconds |
| Skeleton disappears near the floor | Reframe the camera; a short post-impact gap is tolerated, long occlusion cannot be classified |
| No overlay at all | Confirm MQTT port 1883 is reachable and the topic matches |

---

## Step 4: Install the Alarm Panel (optional) {#panel_host_recamera type=docker_deploy required=false config=devices/panel_host.yaml}

Skip this step and the deployment is finished: the camera keeps publishing MQTT
events and nothing else changes.

Take it and you add a panel next to the cameras — a site overview of rooms,
cameras and zones, zone rectangles drawn on each camera's live picture, a
no-person and a no-motion timeout per zone, an operator who confirms or dismisses
each alarm, an SQLite audit trail, and a webhook whose payload carries no video.

The camera cannot host it. The detector there is a native process installed as a .deb, and the camera
offers no filesystem, SQLite or web server for the panel. So the panel goes on a
separate box on the same network, which needs no AI accelerator: a reComputer
R1000 Series, or a Linux machine you already run.

### Prerequisites

- A x86_64 or arm64 Linux host on the camera's network, with Docker and the
  compose plugin (`docker compose version` has to succeed) and SSH access.
- The exact topic the cameras publish on. Check it from that host before you
  start: `mosquitto_sub -h <camera-or-broker-ip> -t '#' -v`. A reCamera 2002 publishes on `<device-name>/fall-detection/results`, single stream, no stream-id suffix.
- Ports 8080 and 1883 free on that host, or different values entered in the form
  — the deploy checks both before it starts and names the process holding one.

### Troubleshooting

| Symptom | What to do |
|---|---|
| Deploy stops on "Port 8080 is already in use" | Enter another Panel Port in the form, or stop the service the message names. |
| "no message on ... within 20 s" warning at the end | The panel is up but has seen no detector result. Re-check the topic against `mosquitto_sub -t '#' -v`, and that the camera publishes to the broker address entered here. |
| Alarm list stays empty and no-person alarms never fire | The camera has to publish on frames with nobody in view for that timeout to have an input. Falls still work either way. |
| `pull access denied` on `eldercare-alarm-*` | Check registry auth and network reachability from the host — both architectures are published. |

### Target {#panel_host_recamera_remote type=remote device_name="Alarm Panel Host" config=devices/panel_host.yaml default=true}

The panel host is addressed over SSH, like any other Docker target.

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

- Draw the zones on the live picture instead of keeping the single
  whole-frame rectangle the deploy created. Saving bumps a configuration
  version; if a colleague saved first you get a 409 and a reload prompt rather
  than overwriting them.
- Point the webhook at your own alerting system if you left it empty.
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a
  USB microphone and speaker on this host; the description page covers what it
  does before you turn it on.

### Troubleshooting

| Symptom | What to do |
|---|---|
| Page does not load | Check the Panel Port matches what the deploy step used, and that the host firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| A room reads unknown and stream-lost | The camera is unreachable from the panel host, not a fall-detection fault. The last-frame time on the card says when it was last seen. |

## Step 6: Voice Check-in (optional) {#voice_checkin_recamera type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service can ask the
resident out loud whether they are all right and act on the answer, in parallel
with the five-second evidence window. It is off unless you turn it on, and
turning it off again changes nothing else about the alarm path.

What it needs: an OpenVoiceStream instance on the same LAN, with a USB
microphone and a speaker plugged into the box running it. The cameras are not
the audio path — neither reCamera model has a confirmed usable microphone, and
the SG2002 cannot host local ASR at all.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

The asymmetry is deliberate. Mishearing a real cry for help as "I'm fine" would
suppress a real alarm; confirming an alarm nobody needed costs an operator a
few seconds. So a distress word beats a safe word in the same sentence, and
anything the keyword lists do not recognise confirms rather than waits.

**Privacy.** Audio is never written to disk. The raw PCM lives in memory for
the length of one listening window and is released when the verdict is
produced. What is persisted is the verdict, the confidence and the latency,
plus the transcribed text — and `store_transcript: false` drops the text too,
leaving only the verdict in the audit trail. Notifications carry the same
fields and still carry no snapshot and no video.

### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.
3. `docker compose exec eldercare-alarm python -c "from eldercare.voice import classify; print(classify('救命','zh').verdict)"` prints `help`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | The container has no audio stack unless the `voice` extra is installed and the ALSA device is passed through. Check `docker compose logs eldercare-alarm` for the TTS or playback warning. |

## Preset: reCamera Pro {#recamera_pro}

One device does everything, on newer hardware than the 2002: the camera sees the
room, decides on-device whether someone fell, and publishes the event over MQTT.

| Device | Purpose |
|--------|---------|
| reCamera Pro | Pose estimation, multi-person tracking, temporal fall logic and MQTT, all local |

**Important:** this is an assistive alert, not a certified medical or
life-safety system. Long shots, occlusion, low light and fall-like floor
activities remain weak cases.

The detector ships in the device's own App Center rather than with this
solution, so this preset configures the installed app and makes it active. If
your device does not carry it yet, install it from the App Center first — the
deploy step will tell you, and name what is installed instead.

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

| Issue | Solution |
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

| Issue | Solution |
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

Unlike the other presets this is a mapped summary rather than a per-frame
document, which is what Home Assistant consumes but carries no skeleton — the
live view with skeletons is the console's own page, opened by this step.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The camera's page does not open | The firmware has an HTTPS switch; port 80 answers with a redirect to 443. Follow it, or open the `https://` address directly |
| Live view works but no fall events reach the broker | Check the broker address and port in the previous step; the summary topic only appears once a person is detected |
| Fall Detection is listed but will not start | Its AI model is missing. Reinstall it from the App Center on the camera — the install downloads the model with the app |
| A fall is missed near the floor | Reframe the camera; a short post-impact gap is tolerated, long occlusion cannot be classified |

### Target {#recamera_pro_verify type=remote device_name="reCamera Pro" config=devices/verify_recamera_pro_fall.yaml}

## Step 4: Install the Alarm Panel (optional) {#panel_host_recamera_pro type=docker_deploy required=false config=devices/panel_host.yaml}

Skip this step and the deployment is finished: the camera keeps publishing MQTT
events and nothing else changes.

Take it and you add a panel next to the cameras — a site overview of rooms,
cameras and zones, zone rectangles drawn on each camera's live picture, a
no-person and a no-motion timeout per zone, an operator who confirms or dismisses
each alarm, an SQLite audit trail, and a webhook whose payload carries no video.

The camera cannot host it. The detector there is an App Center application, and the camera
offers no filesystem, SQLite or web server for the panel. So the panel goes on a
separate box on the same network, which needs no AI accelerator: a reComputer
R1000 Series, or a Linux machine you already run.

### Prerequisites

- A x86_64 or arm64 Linux host on the camera's network, with Docker and the
  compose plugin (`docker compose version` has to succeed) and SSH access.
- The exact topic the cameras publish on. Check it from that host before you
  start: `mosquitto_sub -h <camera-or-broker-ip> -t '#' -v`. A reCamera Pro publishes on `<base>/fall-detection/state`; pick reCamera Pro as the Camera Model in the form so the Pro adapter is used.
- Ports 8080 and 1883 free on that host, or different values entered in the form
  — the deploy checks both before it starts and names the process holding one.

### Troubleshooting

| Symptom | What to do |
|---|---|
| Deploy stops on "Port 8080 is already in use" | Enter another Panel Port in the form, or stop the service the message names. |
| "no message on ... within 20 s" warning at the end | The panel is up but has seen no detector result. Re-check the topic against `mosquitto_sub -t '#' -v`, and that the camera publishes to the broker address entered here. |
| Alarm list stays empty and no-person alarms never fire | The camera has to publish on frames with nobody in view for that timeout to have an input. Falls still work either way. |
| `pull access denied` on `eldercare-alarm-*` | Check registry auth and network reachability from the host — both architectures are published. |

### Target {#panel_host_recamera_pro_remote type=remote device_name="Alarm Panel Host" config=devices/panel_host.yaml default=true}

The panel host is addressed over SSH, like any other Docker target.

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

- Draw the zones on the live picture instead of keeping the single
  whole-frame rectangle the deploy created. Saving bumps a configuration
  version; if a colleague saved first you get a 409 and a reload prompt rather
  than overwriting them.
- Point the webhook at your own alerting system if you left it empty.
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a
  USB microphone and speaker on this host; the description page covers what it
  does before you turn it on.

### Troubleshooting

| Symptom | What to do |
|---|---|
| Page does not load | Check the Panel Port matches what the deploy step used, and that the host firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| A room reads unknown and stream-lost | The camera is unreachable from the panel host, not a fall-detection fault. The last-frame time on the card says when it was last seen. |

## Step 6: Voice Check-in (optional) {#voice_checkin_recamera_pro type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service can ask the
resident out loud whether they are all right and act on the answer, in parallel
with the five-second evidence window. It is off unless you turn it on, and
turning it off again changes nothing else about the alarm path.

What it needs: an OpenVoiceStream instance on the same LAN, with a USB
microphone and a speaker plugged into the box running it. The cameras are not
the audio path — neither reCamera model has a confirmed usable microphone, and
the SG2002 cannot host local ASR at all.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

The asymmetry is deliberate. Mishearing a real cry for help as "I'm fine" would
suppress a real alarm; confirming an alarm nobody needed costs an operator a
few seconds. So a distress word beats a safe word in the same sentence, and
anything the keyword lists do not recognise confirms rather than waits.

**Privacy.** Audio is never written to disk. The raw PCM lives in memory for
the length of one listening window and is released when the verdict is
produced. What is persisted is the verdict, the confidence and the latency,
plus the transcribed text — and `store_transcript: false` drops the text too,
leaving only the verdict in the audit trail. Notifications carry the same
fields and still carry no snapshot and no video.

### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.
3. `docker compose exec eldercare-alarm python -c "from eldercare.voice import classify; print(classify('救命','zh').verdict)"` prints `help`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | The container has no audio stack unless the `voice` extra is installed and the ALSA device is passed through. Check `docker compose logs eldercare-alarm` for the TTS or playback warning. |

## Preset: IP Camera + reComputer J30 / J40 {#jetson}

Keep the cameras you already have. A Jetson Orin pulls their RTSP streams, runs a
larger pose model, and tracks several people per stream independently.

| Device | Purpose |
|--------|---------|
| reComputer J30 / J40 | Pose inference, tracking, fall logic and MQTT for every stream |
| IP camera | Supplies the RTSP video; any ONVIF or RTSP camera works |

**Important:** this is an assistive alert, not a certified medical or
life-safety system. On the untouched 27-clip Subject 4 test the YOLO11m
configuration reached 85.2% accuracy and 100% fall recall; on an independent
external set the deployed recall was 52.9%, limited by pose coverage in long shots
and occlusion.

## Step 1: Deploy Fall Detection {#deploy_jetson_fall type=docker_deploy required=true config=devices/jetson_fall.yaml}

Deploy the detector and build its inference engine on the Jetson. Allow 10–20 min.

### Prerequisites

1. The Jetson runs JetPack 6.x with the NVIDIA container runtime available.
2. At least 10 GB free disk — the pose model and the built engine live on the device.
3. Your IP camera's RTSP URL, including credentials if it requires them, for
   example `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`.
4. Expect the first deploy to spend most of its time building the inference engine on the device. A TensorRT engine is tied to the exact GPU architecture and TensorRT version, so it cannot be shipped prebuilt. Measured on Orin Nano: 461 s for YOLO11s. Later deployments reuse it.
5. Match the pose model to the board — **YOLO11s** for Orin Nano, **YOLO11m** for Orin NX. YOLO11m is the more accurate row in the table on the solution page; YOLO11s leaves more headroom for additional camera streams.

### Troubleshooting

| Issue | Solution |
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

The Jetson is ready for a supervised site trial. Results go to
`recamera/fall-detection/results/<stream-id>`, one topic per camera, so several
cameras stay separable downstream.

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
- Measure real throughput before adding streams — the published FPS figures are
  inference-core only and exclude decoding, tracking and MQTT.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the Jetson is reachable |
| Overlay but no video | The preview pulls RTSP straight from the camera; confirm this computer can reach it too |
| Boxes flicker between people | Raise the tracker IoU threshold, or reframe so people overlap less |

---

## Step 3: Open the Alarm Panel {#panel_open_jetson type=web_dashboard required=false config=devices/panel_console.yaml}

The alarm panel came up with the detector in Step 1 — same compose file, same
device, port 8080 by default. It turns the event stream into alarms someone signs
off on: a site overview, zones drawn on each camera's live picture, a no-person
and a no-motion timeout per zone, confirm and dismiss recorded against an
operator, an SQLite audit trail, and a webhook whose payload carries no video.

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
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a
  USB microphone and speaker on this device; the description page covers what it
  does before you turn it on.

### Troubleshooting

| Symptom | What to do |
|---|---|
| Page does not load | Check the Alarm Panel Port matches what the deploy step used, and that the device firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| Falls raise alarms but no-person alarms never do | The detector config ships `publish_empty_frames: true`, which that timeout depends on. If you replaced `config/config.json` with the device's own copy, set the key again. |

## Step 4: Voice Check-in (optional) {#voice_checkin_jetson type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service can ask the
resident out loud whether they are all right and act on the answer, in parallel
with the five-second evidence window. It is off unless you turn it on, and
turning it off again changes nothing else about the alarm path.

What it needs: an OpenVoiceStream instance on the same LAN, with a USB
microphone and a speaker plugged into the box running it. The cameras are not
the audio path — neither reCamera model has a confirmed usable microphone, and
the SG2002 cannot host local ASR at all.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

The asymmetry is deliberate. Mishearing a real cry for help as "I'm fine" would
suppress a real alarm; confirming an alarm nobody needed costs an operator a
few seconds. So a distress word beats a safe word in the same sentence, and
anything the keyword lists do not recognise confirms rather than waits.

**Privacy.** Audio is never written to disk. The raw PCM lives in memory for
the length of one listening window and is released when the verdict is
produced. What is persisted is the verdict, the confidence and the latency,
plus the transcribed text — and `store_transcript: false` drops the text too,
leaving only the verdict in the audit trail. Notifications carry the same
fields and still carry no snapshot and no video.

### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.
3. `docker compose exec eldercare-alarm python -c "from eldercare.voice import classify; print(classify('救命','zh').verdict)"` prints `help`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | The container has no audio stack unless the `voice` extra is installed and the ALSA device is passed through. Check `docker compose logs eldercare-alarm` for the TTS or playback warning. |

## Preset: IP Camera + reComputer RK3576 / RK3588 {#rk}

Run the detector on a Rockchip NPU board. Same algorithm and same MQTT output as
the other presets, using the board's own NPU instead of a GPU.

| Device | Purpose |
|--------|---------|
| reComputer RK3576 / RK3588 | Pose inference on the NPU, tracking, fall logic and MQTT |
| IP camera | Supplies the RTSP video; any ONVIF or RTSP camera works |

**Important:** this is an assistive alert, not a certified medical or life-safety
system. Each board runs a temporal profile trained and frozen on its own pose traces.
Accuracy is reported for the solution as a whole on the introduction page — the
27-clip test set cannot separate the platforms, so there are no per-board
figures.

## Step 1: Deploy Fall Detection {#deploy_rk_fall type=docker_deploy required=true config=devices/rk3588_fall.yaml}

Deploy the detector to your Rockchip board. Allow about 5 minutes.

### Prerequisites

1. The board runs a vendor image with the NPU driver and `librknnrt.so` present, plus Docker.
2. At least 6 GB free disk for the runtime image and the pose model.
3. Your IP camera's RTSP URL, with credentials if it needs them.
4. Choose the deployment target that matches your board. A model compiled for RK3588 does not run on RK3576 or the reverse, so the target selects which model is downloaded — it is not cosmetic.
5. The 2026-09-05 production-path benchmark stopped other inference applications and used a fixed 640×640 H.264, 15 FPS RTSP source. The optimized YOLOv8s INT8 profile verified 1 stream on RK3576 and 5 streams on RK3588 at the 14.5 FPS-per-route gate; the next boundary failed on both boards. This deployment form still installs one stream with the existing YOLO11n FP16 model and board-specific temporal profile.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `librknnrt.so not found` | Install the board's `rknpu2` runtime package; the container mounts the host copy on purpose |
| Model fails to load | The model must match the board — re-run the step with the correct board selected |
| No video from the camera | Test the RTSP URL in VLC first; most failures are a wrong path or wrong credentials |
| Low frame rate | Other NPU workloads compete for the accelerator; check what else is running before blaming the detector |

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
- Before relying on it, run your own acceptance test — the frozen figure measures
  the temporal gate, not the alert your automation actually receives.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the board is reachable |
| Skeleton offset from the person | Report it — this runtime sends coordinates in the letterboxed model space and the preview corrects for it |
| Boxes flicker between people | Raise the tracker IoU threshold, or reframe so people overlap less |

---

## Step 3: Open the Alarm Panel {#panel_open_rk type=web_dashboard required=false config=devices/panel_console.yaml}

The alarm panel came up with the detector in Step 1 — same compose file, same
device, port 8080 by default. It turns the event stream into alarms someone signs
off on: a site overview, zones drawn on each camera's live picture, a no-person
and a no-motion timeout per zone, confirm and dismiss recorded against an
operator, an SQLite audit trail, and a webhook whose payload carries no video.

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
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a
  USB microphone and speaker on this device; the description page covers what it
  does before you turn it on.

### Troubleshooting

| Symptom | What to do |
|---|---|
| Page does not load | Check the Alarm Panel Port matches what the deploy step used, and that the device firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| Falls raise alarms but no-person alarms never do | That timeout needs the detector to publish on frames with nobody in view. Confirm the RK runtime still publishes with nobody in front of the camera — that is the first thing to check here. |

## Step 4: Voice Check-in (optional) {#voice_checkin_rk type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service can ask the
resident out loud whether they are all right and act on the answer, in parallel
with the five-second evidence window. It is off unless you turn it on, and
turning it off again changes nothing else about the alarm path.

What it needs: an OpenVoiceStream instance on the same LAN, with a USB
microphone and a speaker plugged into the box running it. The cameras are not
the audio path — neither reCamera model has a confirmed usable microphone, and
the SG2002 cannot host local ASR at all.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

The asymmetry is deliberate. Mishearing a real cry for help as "I'm fine" would
suppress a real alarm; confirming an alarm nobody needed costs an operator a
few seconds. So a distress word beats a safe word in the same sentence, and
anything the keyword lists do not recognise confirms rather than waits.

**Privacy.** Audio is never written to disk. The raw PCM lives in memory for
the length of one listening window and is released when the verdict is
produced. What is persisted is the verdict, the confidence and the latency,
plus the transcribed text — and `store_transcript: false` drops the text too,
leaving only the verdict in the audit trail. Notifications carry the same
fields and still carry no snapshot and no video.

### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.
3. `docker compose exec eldercare-alarm python -c "from eldercare.voice import classify; print(classify('救命','zh').verdict)"` prints `help`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | The container has no audio stack unless the `voice` extra is installed and the ALSA device is passed through. Check `docker compose logs eldercare-alarm` for the TTS or playback warning. |

## Preset: IP Camera + reComputer R2000 (Hailo) {#hailo}

Run the detector on a Hailo-8 accelerator. The hot path is native C++ with no
Python, so the host CPU stays largely free.

| Device | Purpose |
|--------|---------|
| reComputer R2000 with Hailo-8 | Pose inference on the Hailo-8, tracking, fall logic and MQTT |
| IP camera | Supplies the RTSP video; any ONVIF or RTSP camera works |

**Important:** this is an assistive alert, not a certified medical or life-safety
system. A Hailo-specific temporal profile is frozen, with 92.02% pose coverage on the
held-out test. Accuracy is reported for the solution as a whole on the
introduction page — the 27-clip test set cannot separate the platforms.

## Step 1: Deploy Fall Detection {#deploy_hailo_fall type=docker_deploy required=true config=devices/hailo_fall.yaml}

Deploy the detector to your Hailo-equipped device. Allow about 5 minutes.

### Prerequisites

1. A Hailo-8 accelerator present as `/dev/hailo0`, with **HailoRT 4.21** installed — the GStreamer plugin, the user library and the kernel driver must all be that version.
2. Docker, and at least 4 GB free disk.
3. Your IP camera's RTSP URL, with credentials if it needs them.
4. The pose model is downloaded from the official Hailo Model Zoo during deployment and checked against a pinned digest, so nothing needs to be staged by hand.
5. Nothing else may hold the accelerator — HailoRT contexts are exclusive, so stop any other Hailo application first.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `No /dev/hailo0` | The accelerator is not seated or its driver is not loaded; check `hailortcli fw-control identify` |
| `libhailort.so.4.21.0 not found` | This deployment is ABI-locked to HailoRT 4.21; upgrading means changing plugin, library and driver together |
| Container starts then exits | Another process owns the accelerator; HailoRT contexts are exclusive |
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
- Before relying on it, run your own acceptance test — the frozen figure measures
  the temporal gate, not the alert your automation actually receives.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Video but no overlay | The preview reads MQTT separately; confirm port 1883 on the device is reachable |
| Overlay but no video | The preview pulls RTSP straight from the camera; confirm this computer can reach it too |
| `inference_time_ms` reads 0 | Expected — the Hailo element does not expose the accelerator call duration at that probe point |

## Step 3: Open the Alarm Panel {#panel_open_hailo type=web_dashboard required=false config=devices/panel_console.yaml}

The alarm panel came up with the detector in Step 1 — same compose file, same
device, port 8080 by default. It turns the event stream into alarms someone signs
off on: a site overview, zones drawn on each camera's live picture, a no-person
and a no-motion timeout per zone, confirm and dismiss recorded against an
operator, an SQLite audit trail, and a webhook whose payload carries no video.

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
- Voice check-in is off by default and needs an OpenVoiceStream instance plus a
  USB microphone and speaker on this device; the description page covers what it
  does before you turn it on.

### Troubleshooting

| Symptom | What to do |
|---|---|
| Page does not load | Check the Alarm Panel Port matches what the deploy step used, and that the device firewall allows it. |
| A login screen appears | The deployment set `ELDERCARE_API_TOKEN`. Enter that token plus an operator name — the name goes on confirm and dismiss receipts. |
| Falls raise alarms but no-person alarms never do | This runtime publishes on every frame and needs no switch, so check the zone's stream id matches the Stream ID from the deploy form instead. |

## Step 4: Voice Check-in (optional) {#voice_checkin_hailo type=manual required=false verify=true config=devices/voice_checkin.yaml}

Optional, off by default. After a fall alarm is raised, the service can ask the
resident out loud whether they are all right and act on the answer, in parallel
with the five-second evidence window. It is off unless you turn it on, and
turning it off again changes nothing else about the alarm path.

What it needs: an OpenVoiceStream instance on the same LAN, with a USB
microphone and a speaker plugged into the box running it. The cameras are not
the audio path — neither reCamera model has a confirmed usable microphone, and
the SG2002 cannot host local ASR at all.

What the answer does:

| Answer | Result |
|---|---|
| A call for help ("救命", "help", "I can't get up") | Confirmed immediately, skipping the rest of the operator window |
| No answer at all | Confirmed immediately |
| Something unreadable | Confirmed immediately |
| "I'm fine" | Default `on_ok: needs_review` — the alarm keeps its normal timing and is flagged for a person to look at. Set `on_ok: dismiss` to close it instead |

The asymmetry is deliberate. Mishearing a real cry for help as "I'm fine" would
suppress a real alarm; confirming an alarm nobody needed costs an operator a
few seconds. So a distress word beats a safe word in the same sentence, and
anything the keyword lists do not recognise confirms rather than waits.

**Privacy.** Audio is never written to disk. The raw PCM lives in memory for
the length of one listening window and is released when the verdict is
produced. What is persisted is the verdict, the confidence and the latency,
plus the transcribed text — and `store_transcript: false` drops the text too,
leaving only the verdict in the audit trail. Notifications carry the same
fields and still carry no snapshot and no video.

### Quick verification

1. `curl -sf http://<ovs-host>:8621/readyz` returns 200.
2. The synthesized prompt is audible from where a fall would happen.
3. `docker compose exec eldercare-alarm python -c "from eldercare.voice import classify; print(classify('救命','zh').verdict)"` prints `help`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Every alarm gets `no_answer` | Either the prompt is inaudible, or the microphone is not being captured. Check the speaker first, then `arecord -l` on the alarm host. |
| Every alarm gets `unclear` | ASR is returning text the keyword lists do not match. Read the transcript in the console and add the phrasing the resident actually uses to `ok_keywords` / `help_keywords`. |
| Alarms close by themselves | `on_ok` is set to `dismiss`. Put it back to `needs_review` unless a person really is reviewing the dismissals. |
| The service starts but never speaks | The container has no audio stack unless the `voice` extra is installed and the ALSA device is passed through. Check `docker compose logs eldercare-alarm` for the TTS or playback warning. |

