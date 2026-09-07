## Preset: On-Device Transcription {#local_transcribe}

One box in the store does everything: capture, voice activity detection,
transcription, punctuation and optional voiceprint. Transcripts are written as
JSON files into a directory on that box's own disk. No cloud account, no upload,
no database.

| Device | Purpose |
|--------|---------|
| reComputer RK3576 | SenseVoice on the 6 TOPS NPU, capture client on the CPU. Measured on this board: 3.0 s of audio in about 780 ms warm (RTF 0.26), 1.71 GiB resident with punctuation and voiceprint loaded |
| reRouter CM4 | The cheaper CPU-only alternative. Paraformer streaming ASR on four Cortex-A72 cores, no accelerator, no text-to-speech |
| reSpeaker XVF3800 | 4-mic array — AEC, beamforming and noise suppression on its own DSP |

**Important.** This is not a certified transcription product and not a
compliance control. Its output is text of the quality documented on the solution
page, with no legal standing. Recording conversations in a store carries notice
and consent obligations that are yours to meet.

Two known weaknesses decide whether a site works at all: steady background noise
**above 70 dB** defeats the array's noise suppression, and speakers **beyond
about 3 m** fall outside the beamformer's useful coverage. Neither is fixable by
choosing a faster board.

**On the CM4, ASR speed and accuracy have not been measured.** The upstream
bench matrix still lists the CM4 `asr_zh_en` row as TBD. Run a pilot before
committing a fleet to that board.

## Step 1: Flash OpenWrt Firmware {#firmware type=manual required=false}

reRouter CM4 only — skip it on the RK3576. Write the operating system to the
reRouter, then put it on your network. **Skip this step** if your reRouter was
purchased after November 2025 — it already ships with the correct firmware.

### Prerequisites

- **rpiboot** on your computer, otherwise the eMMC is never recognized
  - **Windows:** run the [rpiboot installer](https://github.com/raspberrypi/usbboot/raw/master/win32/rpiboot_setup.exe)
  - **Mac/Linux:** `git clone --depth=1 https://github.com/raspberrypi/usbboot && cd usbboot && make`
- A USB-C **data** cable, and two Ethernet cables

### Wiring

![Boot mode](gallery/boot-mode.png)

| Device | Connection | Notes |
|--------|------------|-------|
| reRouter CM4 | Case removed to reach the board | Needed to set the boot jumper |
| USB-C cable | reRouter to computer | For eMMC flashing |
| Computer | rpiboot installed | Otherwise the eMMC does not enumerate |

1. Remove the case and jumper **Boot** to **GND** to enter boot mode
2. Connect the USB-C cable and run **rpiboot** — the eMMC appears as a USB drive
3. Download the firmware. Use these builds so the LAN address is `192.168.49.1`: [Global](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/OpenWRT-24.10.3-RPi-4-Factory.img.gz) · [China](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/OpenWRT-24.10.3-RPi-4-Factory-Chinese.img.gz)
4. Write it with [Raspberry Pi Imager](https://www.raspberrypi.com/software/) ("Use custom") or [balenaEtcher](https://etcher.balena.io/)
5. Remove the jumper, reassemble, connect cables, power on

![WAN and LAN](gallery/wan_lan.png)

Connect the **LAN** port to your computer and the **WAN** port to your router. After 1–2 minutes, `http://192.168.49.1` answers; user `root`, password empty.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `192.168.49.1` does not answer | The cable is in the WAN port, or the firmware came from somewhere other than the links above and uses a different address |
| rpiboot does not see the device | The Boot-GND jumper is not seated, or the USB-C cable is charge-only |
| Flashing fails partway | Reformat the target and write again |
| Login rejected | The password is empty — submit the form without typing one |

---

## Step 2: Deploy the Local Voice Stack {#deploy_local type=docker_deploy required=true config=devices/local_rk3576.yaml}

Two containers start: the OpenVoiceStream speech service on port 8621 and the
capture client on port 8090. Nothing else. No cloud endpoint is configured and
no credential is asked for.

The deployment asks for the recognition language, the output directory, the
microphone card ID, and whether to enable voiceprint labelling and punctuation.
On the RK3576 target both are on by default and the measurement above already
includes them; on the CM4 both are off by default, because each adds a resident
model to a 4 GB board.

### Prerequisites

- The board has internet **for this deployment only**. On the RK3576 that is the
  image plus about 825 MB of model artifacts (502 MB SenseVoice RKNN, 294 MB
  CT-Transformer, 28 MB CAM++) — roughly 7 minutes on a 2.5 MB/s link. On the
  CM4 it is two images plus the CPU model set. Afterwards the box needs no
  uplink.
- At least 6 GB free on the RK3576, 4 GB on the CM4.
- Ports 8621 and 8090 are free.
- RK3576 only: the RKNPU driver is bound. The deployment checks
  `/sys/bus/platform/drivers/RKNPU`; a missing `/dev/rknpu` is **not** a fault
  on Seeed's vendor kernel.

### Wiring

| Device | Connection | Notes |
|--------|------------|-------|
| reSpeaker XVF3800 | USB to the edge device | A USB-A host port. On the reComputer the Type-C port is dual-role and may sit in device mode, in which case nothing enumerates. Confirm with `lsusb` — it reports `2886:001a` |
| Edge device | Ethernet to your router | Needed once, to pull images and models. On the reRouter this is the WAN port |
| Computer | Same network | For SSH deployment. On the reRouter, its LAN port |

Before deploying, note the ALSA card number: SSH in and run `arecord -l`. The
array appears as **ArrayUAC10**; the number after `card` is what the deployment
asks for.

### Target {#local_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576" config=devices/local_rk3576.yaml default=true}

Deploy over SSH. The board takes its address from DHCP; the default user is
`recomputer`. The speech service is pinned to the RKNN backend.

### Target {#local_cm4_remote type=remote device=rerouter device_name="reRouter CM4" config=devices/local_rerouter.yaml}

Deploy over SSH to the reRouter. Default address `192.168.49.1`, user `root`,
empty password on a stock image. CPU recognition, no accelerator.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH refused on the reRouter | The cable is in the WAN port, or the address is not `192.168.49.1` |
| Authentication failed on the reRouter | A stock OpenWrt image has no root password — leave the field empty |
| Pre-check reports "RKNPU driver not bound" | The board is not an RK3576, or its kernel lacks the NPU driver. A missing `/dev/rknpu` is not the cause — the check reads `/sys/bus/platform/drivers/RKNPU` |
| Image pull times out | The device has no route to the registry. Check it from the device with `ping` before retrying |
| `speech` stays unhealthy for several minutes | Expected on first boot while the model set downloads. Follow it with `docker logs -f openvoicestream` |
| Model download stalls | Redeploy with the model source switched between the HF mirror and huggingface.co |
| `voice-client` will not start, image not found | The `c4-local` tag is not published yet. Build branch `feature/c4-harden` of sensecraft-voice-client and tag it, or set `VOICE_CLIENT_IMAGE` to your own build. Real-machine check on an RK3576 board that already had `sensecraft-voice-client:ovs-20260901b` cached locally (2026-09-06): that tag also speaks `vad=none` local VAD, `asr_cache`, and `speaker_embedding`, so pointing `VOICE_CLIENT_IMAGE` at it worked as a drop-in without a rebuild — but the tag is not published to any registry, only confirmed present on that one device |
| reSpeaker missing from `lsusb` | Move it to a USB-A host port. `dmesg \| tail` showing `xhci-hcd` bus deregistration means the dual-role controller switched to device mode |
| Out of memory on the CM4 | Set voiceprint and punctuation to Disabled — each loads its own model into 4 GB |
| Container killed under memory pressure on the RK3576 | `mem_limit` is 3000m for a 3.82 GiB board. Disable punctuation first if you also run other workloads here |
| Restarts re-download the models | The named volumes were removed. `rk-sensevoice-rknn` in particular holds the 502 MB artifact; without it every recreate re-downloads. Note that `rk-asr-models` is a generic volume name also used by other RK3576 OVS-based solutions on the same device (observed alongside a `conversational_voice_ai` deployment on `cat-remote`) — it is shared, not solution-scoped, so `docker compose down -v` on this stack would also remove that other solution's cached models |

---

## Step 3: Check the Local Transcript {#verify_local type=manual verify=true required=true config=devices/verify_asr.yaml}

Speak one sentence near the array, then confirm a file appeared on the device.

### Verification

1. Stand within about 3 m of the reSpeaker and say a full sentence in the language you selected
2. Stay quiet for about two seconds — the local VAD needs 0.7 s of silence to close the utterance
3. On the device, run `ls -lt <output-dir>/cache/asr/ | head` — a new `.json` file carries the current timestamp
4. `cat` it: the `text` field is what you said. With punctuation enabled it is punctuated, and with voiceprint enabled there is a `speaker` field too
5. Open `http://<device-ip>:8090/` from the store LAN and watch the same sentence in the live view

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No file appears, page is empty | Run `arecord -l` on the device. If ArrayUAC10 is missing, the array is on a non-host USB port (on the reComputer, the Type-C one); if it is present but the card number differs from what you entered, redeploy with the right one |
| `backend` is not `rk:sensevoice_rknn` on the RK3576 | The NPU path did not load. Confirm the profile reached the container: `docker exec openvoicestream env \| grep OVS_PROFILE` |
| `curl -F "file=@sample.wav" http://<device-ip>:8621/asr` returns correct text but no file is written | The recognizer is fine and the audio path is not — check the card ID and `docker logs sensecraft-voice-client` |
| Transcript is one long run-on line | Punctuation is disabled. Enable it if the board has the memory |
| Words are clipped at the start of each sentence | On the CM4 the local VAD is cutting in — `speechPadSeconds` in the client config is 0.5 s by default, and should not be tuned against a handful of clips. On the RK3576 it means server-side VAD is on: this preset requires `OVS_VAD_BACKEND=none` with the client endpointing locally, because server VAD drops roughly one syllable per cut |
| Recognition is poor and the room is loud | Measure the background level. Above roughly 70 dB the array cannot separate the speaker, and no setting changes that |
| CPU pinned at 100%, transcripts lag behind speech | CM4: turn punctuation off first, then voiceprint. That board runs one recognition at a time by design |

### Deployment Complete

The store box now transcribes locally.

#### Quick verification

1. `docker ps` — `openvoicestream` and `sensecraft-voice-client` both show `Up`
2. `curl http://<device-ip>:8621/readyz` returns a ready status; on the RK3576, `curl -F "file=@sample.wav" http://<device-ip>:8621/asr` also replies with `"backend":"rk:sensevoice_rknn"`
3. A `.json` file with your sentence exists under `<output-dir>/cache/asr/`
4. Unplug the network cable, speak again, and confirm a new file still appears — this is the local-only claim, tested

#### Next steps

- Decide a retention period for `<output-dir>` and enforce it. Nothing rotates that directory
- If audio is not needed, set `voice.output` to `stream` in the client config so only text is written
- Register the regular speakers once through the client page if you want stable voiceprint labels instead of auto-generated ones
- Repeat the noise and distance check at the actual counter position before installing more sites
- If a site later needs multi-site query, export or a hard-delete API, that is the Server Stack preset — it is the same hardware plus a database and a service in front of it

---

## Preset: Server Stack {#cloud_stack}

One host runs the whole pipeline: speech recognition, voiceprint, a service that
redacts text before it is stored, MySQL, MinIO and an admin console with export
and hard delete. It is one deployment on one box — the compose is a single unit
and brings its own database and object store, so there is nothing to add to it
afterwards.

Where the audio comes from is therefore **a choice you make once, in Step 1, by
picking a deploy target**, not a second deployment:

- **From a mobile app you already ship** — pick a Stack Host target. The stack
  publishes an ASR endpoint for the app to point at and runs no capture client.
  Then do Step 2 to hand the endpoint over.
- **From a mic array on this box** — pick a reComputer RK3576 or reRouter CM4
  mic-capture target. The same stack, plus a capture client bound to the array.

**You can have both.** The ASR endpoint is up on all four targets, so an app can
point at the same stack host after you picked a mic-capture target — that needs
**both things**: the mic-capture target, and Step 2 completed. With the array
alone, Step 2 is not needed.

You cannot end up with neither: Step 1 is required and every target brings at
least one capture path. You also cannot end up with two databases, because there
is only ever one deploy.

| Device | Purpose |
|--------|---------|
| Stack host (reComputer RK3576, or another arm64 Linux host) | ASR, voice-service, MySQL, MinIO, admin console |
| Mobile app (yours, outside this package) | Captures audio and uploads it to the ASR endpoint |
| reSpeaker XVF3800 + reComputer RK3576 or reRouter CM4 | The collector alternative to the app |

**Important:** this is not a compliance certification. Redaction covers text
only — the audio is kept unredacted for its retention window and is covered by
the deletion flow. Redaction scored precision 0.98 / recall 0.95 on a
114-sample gold set, which means misses happen; low-confidence entities are
flagged for review rather than masked. Speaker identification is off by
default: the voiceprint container's image is published, but its models
(~564 MB) are not fetched by this deployment and must be placed by hand — see
Step 2's prerequisites — so `speaker.identified` stays false until they are.

## Step 1: Deploy the Voice Server Stack {#deploy_stack type=docker_deploy required=true config=devices/cloud_stack.yaml}

Pulls the frozen images, writes `.env` and the service configuration on the
device, and starts MySQL, MinIO, the ASR backend, voice-service and the admin
console.

### Prerequisites

1. An arm64 Linux host with Docker, reachable over SSH, with at least 20 GB free.
2. Generate four secrets before you start — `openssl rand -hex 32` each — for the
   JWT key, the operator token, the admin token and the MinIO secret key.
3. Decide the retention window now. Raw audio defaults to 24 hours; the deploy
   form offers 6 and 1, and changing it later means editing
   `config/voice-service.yaml` on the device and restarting voice-service.
4. First deploy pulls several GB of images, most of it the speech container. On
   a slow link this is the long part of the deployment, not the startup.
5. The host must be arm64. The frozen images have no amd64 variant, and the
   bundled ASR image is the RK3576 NPU build.
6. All images (voice-service, voice-web, the ASR/voiceprint image, MySQL and
   MinIO) are published and pinned by digest in the compose file. The
   voiceprint container's models are the exception — its image is published
   but the model files are not fetched by this step (see below).

### Wiring

Only for the two mic-capture targets. On an app-capture target there is no
array to wire and nothing here applies.

1. Plug the reSpeaker XVF3800 into a USB port on the box before deploying.
2. Run `cat /proc/asound/cards` and note the card number — it goes into the ALSA
   Card ID field. It is usually 1, but it moves when other audio devices are
   attached.
3. Place the array where the conversation happens: a counter or service desk at
   roughly one metre. Beamforming helps with direction, not with distance.
4. Keep it off surfaces that carry vibration from the box's own fan.
5. Do not connect a second microphone. The pipeline is single-capture, and a
   second card only makes the card number ambiguous.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `up -d` stops on the ASR image | The image is large and the registry may be slow; retry the deploy, it resumes from the layers already pulled |
| voice-service never becomes healthy | `docker logs c4-voice-service` — a leftover `CHANGE_ME_` placeholder in `config/voice-service.yaml` or a MySQL password mismatch between `.env` and the config file is the usual cause |
| Every API call returns 401 | The token you are sending is not in `VOICE_API_TOKENS`; the format is `name:role:token`, comma-separated |
| A call returns 403, not 401 | The credential is valid but its role is too low — deletion and export need admin |
| MySQL cannot be reached from another machine | Intentional: MySQL and MinIO bind to 127.0.0.1 only. Use an SSH tunnel |
| `/ws` on 8080 refuses to connect | The voiceprint container is in the `voiceprint` profile and does not start by default; if you enabled the profile, check its models are in place — see Step 2's prerequisites |
| Voiceprint container exits with `tokens.txt does not exist` | Its models were not fetched by this deployment — run `download_models.sh` from the upstream `sensecraft-asr-service` repository and copy the output into `/data-iot/respeaker/models` |
| Cloud analytics containers appear unexpectedly | They only start with `--profile cloud-analytics`; if they are running, someone enabled it, and text is leaving the host |
| Mic-capture targets: voice-client restarts in a loop | The ALSA card ID is wrong; `cat /proc/asound/cards` on the device and redeploy with the right number |
| Mic-capture targets: containers run but nothing is transcribed | `docker logs c4-voice-client` — check it reached the ASR backend on 8621 and that the token is the operator one |
| Permission denied on `/data-iot/respeaker` | The deploy creates those directories; if they pre-existed as root-owned, `chmod -R 0775 /data-iot/respeaker` |
| Wrong ASR image on the reRouter CM4 target | `OVS_ASR_IMAGE` now defaults to the `rpi-20260721` arm64 CPU build pinned by digest; override it in the deploy inputs only to run a different build |
| Everything runs but transcripts are empty on CM4 | The CM4 path is unverified here, and the compose memory limit is written for RK3576's memory — a 4 GB CM4 needs it lowered |

### Target {#stack_remote type=remote device=stack_host device_name="Stack Host (app capture)" config=devices/cloud_stack.yaml default=true}

Audio comes from your app. Deploy over SSH to a host on the network; the stack
publishes the ASR endpoint and runs no capture client of its own. Continue with
Step 2.

### Target {#stack_local type=local device=stack_host device_name="Stack Host (app capture)" config=devices/cloud_stack.yaml}

The same app-capture stack, deployed onto this machine when it runs where you
are working. Same compose, same inputs, no SSH credentials.

### Target {#collector_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576 (mic capture)" config=devices/collector_rk3576.yaml}

Audio comes from a mic array on this box. The same stack plus a capture client
bound to the array, on the NPU path — the ASR backend is the RK3576 build and
needs no extra input. With the array alone, Step 2 is not needed; to feed an app
into the same stack as well, do Step 2 too.

### Target {#collector_rerouter_remote type=remote device=rerouter device_name="reRouter CM4 (mic capture)" config=devices/collector_rerouter.yaml}

The same stack plus the capture client on the CPU path. Its compose variant
takes the ASR image as a required input, because this package pins none for
CM4. Unverified on real hardware. With the array alone, Step 2 is not needed; to
feed an app into the same stack as well, do Step 2 too.

---

## Step 2: Configure the ASR Endpoint in the Mobile App {#asr_endpoint type=manual required=false config=devices/asr_endpoint.yaml}

Only when an app uploads audio — whether Step 1 picked a Stack Host target, or
picked a mic-capture target and you also want an app feeding the same stack.
Hand the endpoint and the operator token to the app, then connect once yourself
to confirm the endpoint answers. Skip it if the mic array is the only source.

### Prerequisites

1. The app side has to tell you three things first: the WebSocket path and query
   format its ASR client builds, how it passes credentials (custom header,
   `Authorization: Bearer`, or a query parameter), and the audio format it
   uploads. Where a field in the app's configuration screen has no counterpart
   here, fill it in as the app's own configuration page describes.
2. This endpoint accepts a token on any of those three channels and expects raw
   PCM binary frames: 16 kHz, mono, signed 16-bit little-endian, at most 2 MiB
   per message. Anything else has to be converted on the app side.
3. The endpoint URL is `ws://<stack-host>:8080/ws?token=<operator-token>`. Hand
   over the operator token, never the admin token.
4. On connect, the server sends
   `{"type":"connection","message":"WebSocket connected, ready for audio","session_id":"..."}`.
   During capture it sends `{"type":"vad","status":"speech_detected"|"silence",...}`,
   and one `{"type":"final","text":...,"speaker":{...}}` per utterance.
5. Off the LAN, terminate TLS in front of it and hand over `wss://` instead — the
   token travels in the query string.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection closes with HTTP 401 before upgrading | The token is missing or wrong — authentication happens before the WebSocket upgrade, by design |
| HTTP 403 instead | Valid token, but it is a viewer token; `/ws` needs operator |
| Connection succeeds, no `final` ever arrives | Audio is not 16 kHz mono 16-bit PCM, or the app is sending an encoded format (WAV header, Opus, AAC) — this endpoint takes raw samples |
| Connection drops after about 20 s of silence | The read timeout; the client must keep sending frames or reconnect |
| Frames rejected as too large | Messages are capped at 2 MiB — send shorter chunks, roughly 4 KB is the size the pipeline is tuned for |
| `speaker.identified` is always false | Expected while the voiceprint container is not running |

---

## Step 3: Open the Admin Console {#admin_web type=web_dashboard required=false config=devices/admin_web.yaml}

Opens `http://<stack-host>:3000/` — the recordings, keywords, devices, export and
delete surface.

### Prerequisites

1. The first account is created with the admin API token:
   `curl -X POST -H "X-API-Token: <admin-token>" -H "Content-Type: application/json" -d '{"username":"ops","password":"<password>"}' http://<stack-host>:8081/api/v1/users/register`.
2. That account is created as **viewer** — it can read but not delete or export.
   Promote it to admin with the role API (needs an admin credential itself):
   `curl -X PATCH -H "X-API-Token: <admin-token>" -H "Content-Type: application/json" -d '{"role":"admin"}' http://<stack-host>:8081/api/v1/users/<id>/role`.
   Look up `<id>` with `GET /api/v1/users?username=ops` using the same admin
   token, then log in again to get a token carrying the new role. The service
   itself refuses to demote the last remaining admin (409), so this path never
   locks the account out of its own role endpoint.
3. Everything the console shows is post-redaction. There is no view of the
   original text anywhere, because it was never stored.
4. With a collector, the device it registered appears under Devices, keyed by
   MAC.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login returns a server error | `jwt_key` is still the placeholder — a login cannot be signed and the service refuses rather than returning an empty token |
| Logged in, but delete and export buttons return 403 | The account is viewer; promote it with the role API as above |
| Console loads but lists nothing | Nothing has been ingested yet, or the browser is pointed at a different host than the one the app or collector reports to |
| Console shows no devices | The collector has not reported yet — speak once, then reload |
| Console is reachable but the API is not | voice-web is on 3000 and voice-service on 8081; both must be open on the host |

---

## Step 4: Verify Transcription and Deletion {#verify_stack type=manual required=true verify=true config=devices/verify_stack.yaml}

Say one sentence, check that what landed is redacted, delete it, and prove the
deletion.

### Prerequisites

1. Say something with a phone number in it: "我叫张伟，手机号是 13812345678" —
   through the app, or into the mic array on the collector, then stop; segments
   close on silence.
2. Check the newest row — the number must appear as `[[PHONE]]` and the name as
   `[[NAME]]`, with `pii_masked_count` greater than zero.
3. Delete it with `POST /api/v1/privacy/erase` using the admin token. The
   response must report `"status": "complete"`, `"residue_count": 0` and no
   `failed_steps`. The call returns HTTP 200 even when a cascade step fails —
   `status` is the field that says whether this deletion counts as proof.
   `partial` means something (an object in MinIO, a voiceprint, the tombstone)
   was not removed; `residue_count` then also counts those, so it will not be 0.
4. With a collector, confirm the local audio directory
   `/data-iot/respeaker/recordings` no longer holds the deleted session's file —
   that is the third of the three stores.
5. Copy `assets/tools/delete_proof.sh` into the `sensecraft-voice-service`
   repository and run it (it finds the repository root by walking up to the
   first `go.mod`, so `tools/` and `assets/tools/` both work; or set
   `REPO_ROOT=` explicitly). It stands up its own MySQL and MinIO (`c4-proof-` prefixed
   containers, nothing existing is touched), seeds data, deletes one subject and
   re-checks all three stores. `RESIDUE_COUNT=0` and `RESIDUE_DB_REPORTED=0` are
   the pass condition.
6. The script proves the code path, not your site's data. Both checks matter.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Nothing is transcribed at all, with a collector | Check the ALSA card ID first, then `docker logs c4-ovs-asr` for model loading |
| Transcript arrives but is cut short | Server-side VAD closes a segment on silence; the maximum speech duration is 10 s per segment |
| The raw phone number is in the database | Redaction is off — check `privacy.redaction_enabled` in `config/voice-service.yaml`, then stop and re-check everything ingested so far |
| A name was not masked | Recall is 0.95 on the gold set; low-confidence entities are flagged rather than masked. Check `pii_review_count` before calling it a bug |
| Residue count is not zero | Something outside the database survived — an object in MinIO, or a voiceprint. Read `failed_steps` and `errors`, and treat the deletion as failed |
| `status` is `partial` | At least one cascade step failed. `voiceprint_delete` means the voiceprint service was unreachable, `object_delete` means MinIO, `tombstone_write` means the deletion happened but left no receipt. Fix the cause and re-run the erase; it is idempotent |
| Deletion succeeded but the voiceprint is still there | Expected while the voiceprint service is not running (the `voiceprint` profile is off) — the cascade has nothing to call, so the response reports `status: partial` and a non-zero residue rather than a clean 0 |
| Row is redacted but the audio file is still on disk after erase | Read the erase response `errors` field — object deletion failing is a failed deletion, not a partial success |
| Audio still present after 24 hours | Retention is enforced by the service configuration; confirm `raw_audio_retention_hours` in `config/voice-service.yaml` matches what you selected |
| `voiceprint_delete` fails with `connection refused` | `asr.base_url` in `config/voice-service.yaml` must be the compose service name `http://asr-voiceprint:8080`, not `127.0.0.1` — inside its own network namespace voice-service's `127.0.0.1` is itself |
| A phone number read out as one continuous run of digits is not masked | The ASR returns it as Chinese numeral words ("幺三八幺二三四五六七八"), not Arabic digits. The `cn_mobile_spoken` rule covers the 11-digit mobile pattern; ID card and landline numbers read out this way are still not covered — see the known limitations in the solution description |
| `delete_proof.sh` reports `go.mod file not found` | The script is not inside the `sensecraft-voice-service` checkout. Copy it in, or run it with `REPO_ROOT=/path/to/sensecraft-voice-service` |
| `delete_proof.sh` cannot reach the Go module proxy | It passes `GOPROXY=https://goproxy.cn,direct` by default; override `GOPROXY` if your network needs something else |

### Deployment Complete

The stack is running and one subject has been ingested, redacted, deleted and
proven gone. Text ingest and query live on `http://<stack-host>:8081/api/v1/recordings`,
deletion and export on `/api/v1/privacy/*`, and the console on port 3000.

#### Quick verification

1. `docker ps` on the stack host shows `c4-mysql`, `c4-minio`, `c4-ovs-asr`,
   `c4-voice-service` and `c4-voice-web` all up — plus `c4-voice-client` when a
   collector is deployed.
2. `curl -sf http://<stack-host>:8081/healthz` returns without error, and on a
   mic-capture target `curl -sf http://<stack-host>:8621/health` does too —
   that is the recognizer the capture client feeds.
3. A request with no token returns 401; a viewer token on the delete route
   returns 403.
4. The newest recording shows placeholders, not raw personal data.
5. The erase response reports `status: complete` and residue 0 (a
   `partial` status with a non-zero residue means the deletion is not proven),
   and with a collector the audio file is gone from disk.

#### Next steps

1. Put a TLS terminator in front of the ASR endpoint before anything leaves the
   local network.
2. Run the boundary measurements on the real hardware — concurrency, capture
   duration, WER and persist latency are all unmeasured, so no capacity claim
   should be made from this deployment yet.
3. The voiceprint image is published, but this step only creates the models
   directory — it does not populate it. Before starting `asr-voiceprint`, run
   `download_models.sh` from the upstream `sensecraft-asr-service` repository
   and copy its output (SenseVoice ASR, punctuation, speaker and VAD models,
   ~564 MB total) into `/data-iot/respeaker/models` on this device. Then start
   it with `docker compose --profile voiceprint up -d asr-voiceprint` — without
   the models it exits with `tokens.txt does not exist` — and re-run the
   deletion check with a voiceprint present.
4. Decide the retention window with whoever owns the site's privacy notice; 24
   hours is a default, not a recommendation.
5. On CM4, verify the CPU ASR path end to end and lower the ASR container memory
   limit before treating that target as usable.
6. Keep the admin token off the device; it is for operators running deletion and
   export.
