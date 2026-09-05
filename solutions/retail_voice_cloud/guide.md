## Preset: Server Stack + Mobile App {#app_capture}

One host runs the whole pipeline. Your existing mobile app records the audio and
uploads it to the ASR endpoint this stack publishes; transcription, redaction,
storage, export and deletion all happen here.

| Device | Purpose |
|--------|---------|
| Stack host (reComputer RK3576, or another arm64 Linux host) | ASR, voice-service, MySQL, MinIO, admin console |
| Mobile app (yours, outside this package) | Captures audio and uploads it to the ASR endpoint |

**Important:** this is not a compliance certification. Redaction covers text
only — the audio is kept unredacted for its retention window. The endpoint this
preset publishes is served by the voiceprint container, whose image is still
pending a build and has not been pushed; until it exists, this preset stops
after the stack is up. Redaction scored precision 0.98 / recall 0.95 on a
114-sample gold set, which means misses happen; low-confidence entities are
flagged for review rather than masked.

## Step 1: Deploy the Voice Server Stack {#cloud_stack type=docker_deploy required=true config=devices/cloud_stack.yaml}

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
6. Three of the images are not on the registry yet. `docker manifest inspect`
   answers "artifact not found" for voice-service, voice-web and the voiceprint
   image, while the speech, MySQL and MinIO images resolve. Push them and
   re-check their digests with `docker buildx imagetools inspect` before this
   step can pull anything.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `up -d` stops on the ASR image | The image is large and the registry may be slow; retry the deploy, it resumes from the layers already pulled |
| voice-service never becomes healthy | `docker logs c4-voice-service` — a leftover `CHANGE_ME_` placeholder in `config/voice-service.yaml` or a MySQL password mismatch between `.env` and the config file is the usual cause |
| Every API call returns 401 | The token you are sending is not in `VOICE_API_TOKENS`; the format is `name:role:token`, comma-separated |
| A call returns 403, not 401 | The credential is valid but its role is too low — deletion and export need admin |
| MySQL cannot be reached from another machine | Intentional: MySQL and MinIO bind to 127.0.0.1 only. Use an SSH tunnel |
| `/ws` on 8080 refuses to connect | The voiceprint container is in the `voiceprint` profile and does not start by default; its image is still pending a build |
| Pull fails with "not found" on voice-service or voice-web | Those images have not been pushed to the registry yet — build and push them, then confirm the digest in the compose file matches what the registry returns |
| Cloud analytics containers appear unexpectedly | They only start with `--profile cloud-analytics`; if they are running, someone enabled it, and text is leaving the host |

### Target {#cloud_stack_remote type=remote device=stack_host device_name="Stack Host" config=devices/cloud_stack.yaml default=true}

Deploy over SSH to a host on the network. This is the normal path.

### Target {#cloud_stack_local type=local device=stack_host device_name="Stack Host" config=devices/cloud_stack.yaml}

Deploy onto this machine, when the stack runs where you are working. Same
compose, same inputs, no SSH credentials.

---

## Step 2: Configure the ASR Endpoint in the Mobile App {#asr_endpoint type=manual required=true config=devices/asr_endpoint.yaml}

Hand the endpoint and the operator token to the app, then connect once yourself
to confirm the endpoint answers.

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

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Login returns a server error | `jwt_key` is still the placeholder — a login cannot be signed and the service refuses rather than returning an empty token |
| Logged in, but delete and export buttons return 403 | The account is viewer; promote it in the `users` table as above |
| Console loads but lists nothing | Nothing has been ingested yet, or the browser is pointed at a different host than the one the devices report to |

---

## Step 4: Verify Transcription and Deletion {#verify_cloud type=manual required=true verify=true config=devices/verify_cloud.yaml}

Say one sentence, check that what landed is redacted, delete it, and prove the
deletion.

### Prerequisites

1. Say something with a phone number in it: "我叫张伟，手机号是 13812345678".
2. Check the newest row — the number must appear as `[[PHONE]]` and the name as
   `[[NAME]]`, with `pii_masked_count` greater than zero.
3. Delete it with `POST /api/v1/privacy/erase` using the admin token, and read
   the residue count in the response. It must be 0.
4. Run `assets/tools/delete_proof.sh` from the `sensecraft-voice-service`
   repository root. It stands up its own MySQL and MinIO (`c4-proof-` prefixed
   containers, nothing existing is touched), seeds data, deletes one subject and
   re-checks all three stores. `RESIDUE_COUNT=0` and `RESIDUE_DB_REPORTED=0` are
   the pass condition.
5. The script proves the code path, not your site's data. Both checks matter.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The raw phone number is in the database | Redaction is off — check `privacy.redaction_enabled` in `config/voice-service.yaml`, then stop and re-check everything ingested so far |
| A name was not masked | Recall is 0.95 on the gold set; low-confidence entities are flagged rather than masked. Check `pii_review_count` before calling it a bug |
| Residue count is not zero | An object failed to delete in MinIO — the row is gone but the audio is not. Read the `errors` field and treat the deletion as failed |
| Deletion succeeded but the voiceprint is still there | Expected while the voiceprint service is not running; the cascade has nothing to call |
| `delete_proof.sh` cannot reach the Go module proxy | It passes `GOPROXY=https://goproxy.cn,direct` by default; override `GOPROXY` if your network needs something else |

### Deployment Complete

The stack is running and one subject has been ingested, redacted, deleted and
proven gone. Text ingest and query live on `http://<stack-host>:8081/api/v1/recordings`,
deletion and export on `/api/v1/privacy/*`, and the console on port 3000.

#### Quick verification

1. `docker ps` on the stack host shows `c4-mysql`, `c4-minio`, `c4-ovs-asr`,
   `c4-voice-service` and `c4-voice-web` all up.
2. `curl -sf http://<stack-host>:8081/healthz` returns without error.
3. A request with no token returns 401; a viewer token on the delete route
   returns 403.
4. The newest recording shows placeholders, not raw personal data.
5. The erase response reports residue 0.

#### Next steps

1. Put a TLS terminator in front of the ASR endpoint before anything leaves the
   local network.
2. Run the boundary measurements on the real hardware — concurrency, capture
   duration, WER and persist latency are all unmeasured, so no capacity claim
   should be made from this deployment yet.
3. Build and push the voiceprint image, then start it with
   `docker compose --profile voiceprint up -d asr-voiceprint`, and re-run the
   deletion check with a voiceprint present.
4. Decide the retention window with whoever owns the site's privacy notice; 24
   hours is a default, not a recommendation.

---

## Preset: Server Stack + Edge Collector {#edge_capture}

No app involved. A mic array on an edge box captures, transcribes locally through
OpenVoiceStream and reports into the same stack, which runs on the same box.

| Device | Purpose |
|--------|---------|
| reComputer RK3576 or reRouter CM4 | Capture, local transcription, and the whole server stack |
| reSpeaker XVF3800 | 4-mic array — noise suppression, AEC, beamforming |

**Important:** this is not a compliance certification. Only text is redacted;
audio is kept unredacted for its retention window and is covered by the deletion
flow. Speaker identification is off because the voiceprint image is still pending
a build. On RK3576 the ASR runs on the NPU; on reRouter CM4 it runs on the CPU
and this package pins no image for that path, so you must supply one, and that
path has not been run on real hardware.

## Step 1: Deploy the Collector {#collector_rk3576 type=docker_deploy required=true config=devices/collector_rk3576.yaml}

Same frozen stack as the other preset, plus the capture client bound to the mic
array on this host.

### Wiring

1. Plug the reSpeaker XVF3800 into a USB port on the edge box before deploying.
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
| voice-client restarts in a loop | The ALSA card ID is wrong; `cat /proc/asound/cards` on the device and redeploy with the right number |
| Container runs but nothing is transcribed | `docker logs c4-voice-client` — check it reached the ASR backend on 8621 and that the token is the operator one |
| Permission denied on `/data-iot/respeaker` | The deploy creates those directories; if they pre-existed as root-owned, `chmod -R 0775 /data-iot/respeaker` |
| Deploy fails with `set OVS_ASR_IMAGE ...` | Only the CM4 target: no CPU ASR image is pinned by this package, so you must supply the reference |
| Everything runs but transcripts are empty on CM4 | The CM4 path is unverified here, and the compose memory limit is written for RK3576's memory — a 4 GB CM4 needs it lowered |

### Target {#collector_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576" config=devices/collector_rk3576.yaml default=true}

The NPU path. The ASR backend is the RK3576 build and needs no extra input.

### Target {#collector_rerouter_remote type=remote device=rerouter device_name="reRouter CM4" config=devices/collector_rerouter.yaml}

The CPU path. Uses a compose variant whose ASR image is a required input,
because this package pins none for CM4. Unverified on real hardware.

---

## Step 2: Open the Admin Console {#admin_web_edge type=web_dashboard required=false config=devices/admin_web_edge.yaml}

Opens `http://<collector>:3000/` — the same console, on the collector.

### Prerequisites

1. Create the first account with the admin API token, exactly as in the other
   preset:
   `curl -X POST -H "X-API-Token: <admin-token>" -H "Content-Type: application/json" -d '{"username":"ops","password":"<password>"}' http://<collector>:8081/api/v1/users/register`.
2. Promote it with the role API if it needs to delete or export (admin token
   required): `curl -X PATCH -H "X-API-Token: <admin-token>" -H "Content-Type: application/json" -d '{"role":"admin"}' http://<collector>:8081/api/v1/users/<id>/role`.
   New accounts are viewer by default.
3. The Recordings page shows the redacted text. The device the collector
   registered appears under Devices, keyed by MAC.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Console shows no devices | The collector has not reported yet — speak once, then reload |
| Login returns a server error | `jwt_key` is still the placeholder in `config/voice-service.yaml` |
| Console is reachable but the API is not | voice-web is on 3000 and voice-service on 8081; both must be open on the collector |

---

## Step 3: Verify Transcription and Deletion {#verify_edge type=manual required=true verify=true config=devices/verify_edge.yaml}

The same acceptance check, driven by the mic array instead of an app.

### Prerequisites

1. Speak one sentence containing a phone number into the array, then stop —
   segments close on silence.
2. Check the newest row shows `[[PHONE]]` and `[[NAME]]`, and that
   `pii_masked_count` is greater than zero.
3. Erase that session with the admin token and confirm the residue count is 0.
4. Run `assets/tools/delete_proof.sh` from the `sensecraft-voice-service`
   repository root and read `RESIDUE_COUNT=0`.
5. Confirm the local audio directory `/data-iot/respeaker/recordings` no longer
   holds the deleted session's file — that is the third of the three stores.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Nothing is transcribed at all | Check the ALSA card ID first, then `docker logs c4-ovs-asr` for model loading |
| Transcript arrives but is cut short | Server-side VAD closes a segment on silence; the maximum speech duration is 10 s per segment |
| Row is redacted but the audio file is still on disk after erase | Read the erase response `errors` field — object deletion failing is a failed deletion, not a partial success |
| Audio still present after 24 hours | Retention is enforced by the service configuration; confirm `raw_audio_retention_hours` in `config/voice-service.yaml` matches what you selected |

### Deployment Complete

The collector captures, transcribes locally, redacts before storage, and serves
the console and the deletion API from the same box. Nothing leaves the device
unless someone enables the cloud-analytics profile.

#### Quick verification

1. `docker ps` shows `c4-ovs-asr`, `c4-voice-client`, `c4-voice-service`,
   `c4-voice-web`, `c4-mysql` and `c4-minio`.
2. `curl -sf http://<collector>:8621/health` returns without error.
3. Speaking near the array produces a new row within a few seconds.
4. That row contains placeholders, not raw personal data.
5. Erase returns residue 0, and the audio file is gone from disk.

#### Next steps

1. Measure before you promise anything: concurrency, capture duration, WER and
   persist latency are all unmeasured on this hardware.
2. Shorten the audio retention window if the site's privacy notice requires it —
   6 or 1 hour are available at deploy time.
3. On CM4, verify the CPU ASR path end to end and lower the ASR container memory
   limit before treating that target as usable.
4. Keep the admin token off the device; it is for operators running deletion and
   export.
