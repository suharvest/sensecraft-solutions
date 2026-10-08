## Preset: Clip + reComputer Jetson {#clip_edge_box}

Recordings sync from the Clip to a reComputer Jetson, are transcribed and split by speaker on the host, and are shown on a local web page.

| Device | Purpose |
|--------|---------|
| reSpeaker Clip | Wearable recording |
| reComputer J40 (Jetson Orin NX, JetPack 6.2) | Syncs recordings, transcribes them, serves the results page |

**What you'll get:**
- A results page in the browser with timestamped transcripts and speaker labels
- An HTTP API to upload recordings or fetch transcripts
- MQTT messages that announce each finished transcript
- Optional AI summaries for each transcript

**Requirements:** Bluetooth on the host (Jetson wireless module) · At least 15 GB of free disk · Internet access for the first deploy

## Step 1: Deploy the transcription service {#deploy_stack type=docker_deploy required=true config=devices/jetson_stack.yaml}

Install the transcription service on the reComputer Jetson and register your Clip.

### Target: Remote deployment {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_stack.yaml default=true}

Deploy from this computer to a reComputer J40 over SSH.

### Prerequisites

- The host is a Jetson Orin NX module running JetPack 6.2; any other module or version stops the deploy at the start with a message
- The host has at least 15 GB of free disk and internet access
- The Clip has been unbound from the phone app

### Wiring

1. Power the reComputer J40 and connect it to the same network as this computer
2. Charge the Clip and place it next to the host
3. Enter the host IP, SSH username and password
4. Enter the Clip name: "Clip" plus the four characters printed on the Clip, e.g. `Clip 7036`; the phone app shows the same name
5. Turn on "Faster sync over Wi-Fi" and "AI summary (optional)" if you need them, then click Deploy

### Deployment Complete

The first deploy downloads the speech models (about 1.8 GB) and starts the services; how long it takes depends on your network speed. Then:

1. Find the API key at the end of the deploy log and keep it
2. Open `http://<host-ip>:8631/` in your browser and enter the API key

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Jetson module or JetPack mismatch | This solution supports Jetson Orin NX with JetPack 6.2 only; use a matching host |
| Not enough disk space | Free up at least 15 GB on the host |
| Model download fails or is slow | Check the host's internet access and deploy again; a completed download is kept |
| Clip name format error | Use the form `Clip 7036`: Clip, a space, and the four characters |
| AI summary is missing the service address | Fill in the service address and model name, or turn AI summary off |
| Port 8631, 8621, 8622 or 1883 in use | Stop the other service using that port on the host and deploy again |

### Target: This computer {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_stack.yaml}

Run SenseCraft Solution on the reComputer J40 itself and deploy there.

### Prerequisites

- This computer is a Jetson Orin NX module running JetPack 6.2
- It has at least 15 GB of free disk and internet access
- The Clip has been unbound from the phone app

### Wiring

1. Make sure this computer is online
2. Charge the Clip and place it next to the host
3. Enter the Clip name, e.g. `Clip 7036`
4. Turn on "Faster sync over Wi-Fi" and "AI summary (optional)" if you need them, then click Deploy

### Deployment Complete

The first deploy downloads the speech models (about 1.8 GB) and starts the services; how long it takes depends on your network speed. Then:

1. Find the API key at the end of the deploy log and keep it
2. Open `http://localhost:8631/` in your browser and enter the API key

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Jetson module or JetPack mismatch | This solution supports Jetson Orin NX with JetPack 6.2 only |
| Permission denied while writing the configuration or models | Use "Remote deployment" from another computer over SSH instead |
| Not enough disk space | Free up at least 15 GB |
| Port 8631, 8621, 8622 or 1883 in use | Stop the other service using that port and deploy again |

## Step 2: Check the service {#verify_stack type=http_debug required=true config=devices/verify_clip.yaml}

Confirm the transcription service is ready.

### Wiring

1. Enter the host IP (`localhost` when you deployed on this computer)
2. Click Check; HTTP 200 means the service is ready

### Deployment Complete

The transcription service is running on your reComputer Jetson.

#### Initial Setup

1. Open `http://<host-ip>:8631/` in your browser and enter the API key shown at the end of the deploy log
2. If you lose the API key, run `sudo cat /opt/clip-private-transcription/config/api_key` on the host
3. To change the Clip, Wi-Fi sync or AI summary settings, edit them in Step 1 and deploy again; leave the API key empty to keep the current one

#### Quick Verification

1. Record about 30 seconds of conversation on the Clip and put it back next to the host
2. Once it has synced, a new transcript appears on the results page with timestamps and speaker labels

Without a Clip at hand, upload a 16 kHz mono WAV recording instead:

```bash
curl -H "Authorization: Bearer <API key>" -F file=@sample.wav http://<host-ip>:8631/v1/transcribe
```

Subscribe to finished-transcript messages: `mosquitto_sub -h <host-ip> -t 'clip-pt/+/transcript/+/ready'`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Returns 503 | Speech recognition is still loading; wait a few minutes and try again |
| Connection refused | Check the host IP, then run `docker ps` on the host to see whether the services are running |
| No new recordings on the results page | Check that the Clip is charged, within Bluetooth range of the host, and not bound to the phone app |
| Several Clips nearby and the wrong one connects | Fill in "Clip Bluetooth address (optional)" in Step 1 and deploy again |
| Sync fails after turning on Wi-Fi sync | Make sure the wireless interface you entered is not the one the host uses for its network; without a spare interface, turn Wi-Fi sync off and use Bluetooth only |
| No summary is generated | Check the AI service address, model name and key; very short recordings get no summary |
