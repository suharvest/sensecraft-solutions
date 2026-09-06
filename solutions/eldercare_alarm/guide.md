## Preset: IP Camera + reComputer J (Orin) {#orin}

Everything on one Jetson: the EdgeFallKit detector, the alarm service, an MQTT
broker and the confirmation page. The trade is deploy time — the first run builds
a TensorRT engine on the device, which takes several minutes and is why this
preset's timeout is an hour rather than a few minutes.

| Device | Purpose |
|---|---|
| reComputer J30 / J40 (Orin) | Runs the detector, the alarm service, the broker and the confirmation page |
| IP camera | Supplies the RTSP view the detector watches |

**Important**

This is not a medical device and not a certified emergency-response product. It
does not diagnose, treat, or replace a carer's judgement. An alarm is a prompt;
the response stays with a person.

Known weak points, and they matter more here than the accuracy table does:
a fall has to happen on camera to be seen at all, and a person already on the
floor when the detector starts reports as a posture without raising an event.
Long shots, heavy furniture occlusion and low light all reduce detection. Zones
are normalised rectangles over the frame, so re-aiming the camera silently
invalidates them. And the `no_motion` alarm will fire during sleep unless the
zone excludes the bed or the timeout is longer than a nap.

One more thing before you start: the alarm service image is not published yet.
See the Prerequisites below.

## Step 1: Deploy the Alarm Stack {#deploy_orin_alarm type=docker_deploy required=true config=devices/orin_alarm.yaml}

Fill in the device, the camera, the zone and the timeouts. The step uploads the
compose stack, downloads and checksums the pose model, builds the TensorRT
engine, writes both configuration files from what you typed, and then waits until
it has seen a real detector message and a live alarm API before reporting
success.

### Prerequisites

- JetPack 6.x with the NVIDIA container runtime configured for Docker. If
  `docker info | grep -i nvidia` finds nothing, run
  `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`.
- TensorRT dev packages present — the step needs `/usr/src/tensorrt/bin/trtexec`.
- At least 10 GB free.
- The camera's RTSP URL, tested in VLC first.
- **The `eldercare-alarm-arm64:0.1.0` image is not in the registry yet.** Build it
  from the upstream project and tag it as the compose file expects, on the device
  or on a machine that can push:
  `docker build -f docker/Dockerfile -t sensecraft-missionpack.seeed.cn/solution/eldercare-alarm-arm64:0.1.0 .`
  Without it the `eldercare-alarm` service fails to pull and the deploy fails.

### Troubleshooting

| Issue | Solution |
|---|---|
| `This target is not a NVIDIA Jetson` | The address points at a different machine. Check the IP and the SSH user. |
| `trtexec not found` | Install the TensorRT dev packages from the JetPack SDK components. |
| Engine build times out | YOLO11m takes considerably longer than YOLO11s. Re-run the deploy — the ONNX file and the timing cache are kept, so the second attempt is much faster. |
| `pull access denied` on `eldercare-alarm-arm64` | Expected until that image is built or pushed. See the Prerequisites. |
| Verification fails with `No detector result` | The detector is not seeing the camera. Check the RTSP URL in VLC from the Jetson itself, then `docker logs eldercare_alarm_orin-fall-detection-1`. |
| Verification fails on the alarm API | `docker logs eldercare_alarm_orin-eldercare-alarm-1` names the configuration key it rejected. The generated file is `config/eldercare.yaml` under the deploy directory. |
| Alarms never appear on a quiet site | Expected — that is what the timeouts are for. To prove the path, drop the no-person timeout to 1 minute, redeploy, and leave the room. |

### Target {#orin_remote type=remote device=orin device_name="reComputer J" config=devices/orin_alarm.yaml default=true}

Deploy over SSH to a Jetson on the network. This is the normal case: the app runs
on your laptop and the stack goes to the device.

### Target {#orin_local type=local device=orin device_name="reComputer J" config=devices/orin_alarm.yaml}

Deploy on the Jetson itself, when the app is running on the same machine that
will host the alarm service.

## Step 2: Open the Confirmation Page {#verify_orin_alarm type=web_dashboard required=false config=devices/confirm_ui.yaml}

Enter the Jetson's address and port 8080. The page opens in your browser.

### Deployment Complete

The detector is publishing, the alarm service is consuming it, and the console is
the place where a person acts on what comes out.

#### Quick verification

1. The page loads and shows an alarm list. An empty list is correct on a quiet
   site — it means the service is up and answering.
2. On the Jetson, subscribe to the detector to confirm messages are flowing:
   `docker exec eldercare_alarm_orin-mosquitto-1 mosquitto_sub -h 127.0.0.1 -t '#' -v -C 5`.
3. Force one alarm: edit `config/eldercare.yaml` on the device, set the zone's
   `no_person_timeout_sec` to 60, run `docker compose restart eldercare-alarm`,
   leave the area empty for a minute, and reload the page. Put the real value
   back afterwards.
4. Confirm that alarm on the page. If a webhook is configured, check that your
   endpoint received one POST with the operator name and no media in the payload.

#### Next steps

- Split the single full-frame zone into per-room rectangles if one camera covers
  more than one area, and bind each zone to its stream id.
- Point `notifiers` at the system that should actually receive alarms, and keep
  the idempotency header — it is what makes a retry safe.
- Put credentials and TLS on the broker before this device is reachable from
  outside the local network.

### Troubleshooting

| Issue | Solution |
|---|---|
| Page does not load | Port 8080 may be taken by something else on the Jetson. Check `docker compose ps` and the container logs. |
| Page loads, list always empty | Either nothing has timed out yet, or the subscription topic does not match what the detector publishes. Compare `mqtt.subscriptions` in `config/eldercare.yaml` against a live `mosquitto_sub -t '#' -v`. |
| Alarms appear but no webhook arrives | Check the alarm's state. `escalated` means the send missed its deadline; the retry runs every 30 s and the alarm stays `escalated` on purpose. |
| A `no_person` alarm fires while someone is in the room | The person is outside the zone rectangle, or occluded. Re-check the zone against the live view. |

## Step 3: Voice Check-in (optional) {#voice_checkin type=manual required=false verify=true config=devices/voice_checkin.yaml}

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


## Preset: IP Camera + reComputer R (Hailo) {#hailo}

The same stack on a Hailo-8 accelerator. The detector's hot path is native C++
and the pose model arrives as a precompiled HEF, so there is no on-device engine
build and the deploy is minutes rather than tens of minutes.

| Device | Purpose |
|---|---|
| reComputer R with Hailo-8 | Runs the detector, the alarm service, the broker and the confirmation page |
| IP camera | Supplies the RTSP view the detector watches |

**Important**

This is not a medical device and not a certified emergency-response product. It
does not diagnose, treat, or replace a carer's judgement. An alarm is a prompt;
the response stays with a person.

The same weak points apply: the fall has to happen on camera, someone already on
the floor at start-up raises no event, long shots and occlusion and low light all
reduce detection, zones break silently when the camera is re-aimed, and
`no_motion` fires during sleep unless the zone or the timeout accounts for it.

This preset is additionally ABI-locked to HailoRT 4.21 — the GStreamer plugin,
the user library and the kernel driver all have to be that version. And, as
above, the alarm service image is not published yet.

## Step 1: Deploy the Alarm Stack {#deploy_hailo_alarm type=docker_deploy required=true config=devices/hailo_alarm.yaml}

Same form as the Orin preset. The step checks the accelerator, downloads and
checksums the HEF, writes the detector environment and the alarm configuration,
and verifies a real detector message and a live alarm API before reporting
success.

### Prerequisites

- Raspberry Pi OS or Ubuntu with Docker and the HailoRT 4.21 stack installed:
  `/dev/hailo0` present, `/usr/lib/libhailort.so.4.21.0` present, and the
  HailoRT GStreamer plugin at
  `/usr/lib/aarch64-linux-gnu/gstreamer-1.0/libgsthailo.so`.
- At least 6 GB free.
- The camera's RTSP URL, tested in VLC first.
- **The `eldercare-alarm-arm64:0.1.0` image is not in the registry yet.** Build it
  from the upstream project and tag it as the compose file expects:
  `docker build -f docker/Dockerfile -t sensecraft-missionpack.seeed.cn/solution/eldercare-alarm-arm64:0.1.0 .`

### Troubleshooting

| Issue | Solution |
|---|---|
| `No /dev/hailo0` | The accelerator is not seated or its driver is not loaded. `hailortcli fw-control identify` should answer. |
| `libhailort.so.4.21.0 not found` | A different HailoRT minor version is installed. Move plugin, user library and driver together — changing only the mount will not work. |
| HEF download fails or the checksum fails | The URL is the official Hailo Model Zoo v2.15 build. Re-run the step; the partial file resumes. |
| `pull access denied` on `eldercare-alarm-arm64` | Expected until that image is built or pushed. See the Prerequisites. |
| Verification fails with `No detector result` | Check the container health first — the step prints it. Then check the RTSP URL from the device and `docker logs eldercare_alarm_hailo-fall-detection-1`. |
| Verification fails on the alarm API | `docker logs eldercare_alarm_hailo-eldercare-alarm-1` names the configuration key it rejected. |

### Target {#hailo_remote type=remote device=hailo device_name="reComputer R" config=devices/hailo_alarm.yaml default=true}

Deploy over SSH to the device on the network.

### Target {#hailo_local type=local device=hailo device_name="reComputer R" config=devices/hailo_alarm.yaml}

Deploy on the device itself, when the app is running on it.

## Step 2: Open the Confirmation Page {#verify_hailo_alarm type=web_dashboard required=false config=devices/confirm_ui.yaml}

Enter the device's address and port 8080. The page opens in your browser.

### Deployment Complete

The detector is publishing, the alarm service is consuming it, and the console is
the place where a person acts on what comes out.

#### Quick verification

1. The page loads and shows an alarm list. An empty list is correct on a quiet
   site.
2. On the device, confirm messages are flowing:
   `docker exec eldercare_alarm_hailo-mosquitto-1 mosquitto_sub -h 127.0.0.1 -t '#' -v -C 5`.
3. Force one alarm: set the zone's `no_person_timeout_sec` to 60 in
   `config/eldercare.yaml`, run `docker compose restart eldercare-alarm`, leave
   the area empty for a minute, reload the page, then restore the value.
4. Confirm that alarm on the page and check your webhook endpoint received one
   POST with the operator name and no media in the payload.

#### Next steps

- Split the single full-frame zone into per-room rectangles and bind each to its
  stream id.
- Point `notifiers` at the system that should actually receive alarms.
- Put credentials and TLS on the broker before the device is reachable from
  outside the local network.

### Troubleshooting

| Issue | Solution |
|---|---|
| Page does not load | Port 8080 may be taken. Check `docker compose ps` and the container logs. |
| Page loads, list always empty | Compare `mqtt.subscriptions` in `config/eldercare.yaml` against a live `mosquitto_sub -t '#' -v`. |
| Alarms appear but no webhook arrives | `escalated` means the send missed its deadline; retries continue every 30 s and the state stays `escalated` by design. |
| A `no_person` alarm fires while someone is in the room | The person is outside the zone rectangle, or occluded. Re-check the zone against the live view. |

## Step 3: Voice Check-in (optional) {#voice_checkin type=manual required=false verify=true config=devices/voice_checkin.yaml}

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


## Preset: reCamera + Alarm Gateway {#recamera}

The cameras already run fall detection on their own — the 2002 as a native
process, the Pro as an App Center application — and this solution does not touch
them. The alarm service goes on a gateway machine beside them, brought up by
hand, because that gateway is whatever the site already has and the deploy form
has no device class for "any Linux host".

| Device | Purpose |
|---|---|
| reCamera 2002 or reCamera Pro | Detects falls and publishes the event stream |
| Gateway host (any x86_64 or arm64 Linux machine) | Runs the alarm service, the broker and the confirmation page |

**Important**

This is not a medical device and not a certified emergency-response product. It
does not diagnose, treat, or replace a carer's judgement. An alarm is a prompt;
the response stays with a person.

Same weak points as the other presets — falls must happen on camera, occlusion
and long shots and low light reduce detection, zones break when a camera moves,
`no_motion` fires during sleep — plus one specific to this path: the reCamera
event stream has not been verified on hardware for this solution. The exact topic
and whether the camera publishes on empty frames both need checking on your own
device before the `no_person` alarm can be relied on.

## Step 1: Set Up the Alarm Gateway {#deploy_recamera_alarm type=manual required=true config=devices/recamera_alarm.yaml}

Five substeps: confirm the cameras are publishing, prepare the gateway, edit the
configuration, start the stack, check ingest. Everything you need is in
`assets/recamera/` in this package.

### Prerequisites

- Fall Detection already deployed and running on the cameras.
- A gateway machine on the same network with Docker and the compose plugin.
- **The alarm service image is not published yet.** Build it from the upstream
  project for the gateway's architecture and tag it, or set
  `ELDERCARE_ALARM_IMAGE` to your own tag:
  `docker build -f docker/Dockerfile -t sensecraft-missionpack.seeed.cn/solution/eldercare-alarm-amd64:0.1.0 .`
- `mosquitto_sub` on the gateway, for reading the camera topic before you
  configure anything.

### Troubleshooting

| Issue | Solution |
|---|---|
| `mosquitto_sub -t '#'` shows nothing | The camera is publishing to its own broker, not this one. Point `mqtt.host` at the camera's broker, or configure the camera to publish to the gateway. |
| Topic does not match either sample | Use what you actually see. A 2002 topic maps to `fall_result_v1`, a Pro topic to `recamera_pro_state`. Do not guess from the topic shape. |
| `eldercare-alarm` restarts in a loop | `docker compose logs eldercare-alarm` names the configuration key it rejected. |
| `pull access denied` | Expected until the image is built or pushed. See the Prerequisites. |
| Falls appear but `no_person` never fires | The camera may not publish on empty frames. Watch the topic with nobody in view — if messages stop, that alarm kind cannot work on this camera until the detector is configured to keep publishing. |

## Step 2: Open the Confirmation Page {#verify_recamera_alarm type=web_dashboard required=false config=devices/confirm_ui.yaml}

Enter the gateway's address and port 8080. The page opens in your browser.

### Deployment Complete

The cameras publish, the gateway turns the stream into alarms, and the console is
where a person acts on them.

#### Quick verification

1. The page loads and shows an alarm list. An empty list is correct on a quiet
   site.
2. On the gateway, `curl -s http://127.0.0.1:8080/api/alarms` returns the same
   list — useful when the page is being served but the browser cannot reach it.
3. Force one alarm: set a zone's `no_person_timeout_sec` to 60 in
   `config/eldercare.yaml`, `docker compose restart eldercare-alarm`, leave the
   area empty for a minute, reload the page, then restore the value.
4. Confirm that alarm and check your webhook endpoint received one POST with the
   operator name and no media in the payload.

#### Next steps

- Add one zone per area, each with its own rectangle, stream ids and timeouts.
- If several cameras feed one gateway, bind each zone to its stream ids —
  otherwise a zone accepts frames from every stream.
- Put credentials and TLS on the broker before the gateway is reachable from
  outside the local network.

### Troubleshooting

| Issue | Solution |
|---|---|
| Page does not load | Check `docker compose ps` on the gateway and whether port 8080 is already taken. |
| Page loads, list always empty | The subscription topic does not match. Compare `mqtt.subscriptions` against a live `mosquitto_sub -t '#' -v`. |
| Alarms appear but no webhook arrives | `escalated` means the send missed its deadline; retries continue every 30 s and the state stays `escalated` by design. |
| Zones behave as if merged | An empty `stream_ids` accepts any stream. Bind each zone explicitly when more than one camera feeds the gateway. |

## Step 3: Voice Check-in (optional) {#voice_checkin type=manual required=false verify=true config=devices/voice_checkin.yaml}

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

