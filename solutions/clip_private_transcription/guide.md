## Preset: Clip + reComputer {#clip_edge_box}

Recordings sync from the Clip to a reComputer, are transcribed and split by speaker on the host, and are shown on a local web page.

| Device | Purpose |
|--------|---------|
| reSpeaker Clip | Wearable recording |
| reComputer J40 (Jetson Orin NX, JetPack 6.2) or reComputer RK3576 (8 GB) | Syncs recordings, transcribes them, serves the results page |

**What you'll get:**
- A results page in the browser with timestamped transcripts and speaker labels
- An HTTP API to upload recordings or fetch transcripts
- MQTT messages that announce each finished transcript
- Optional AI summaries for each transcript

**Requirements:** Bluetooth on the host · Free disk: 15 GB on Jetson, 5 GB on RK3576 · Internet access for the first deploy

## Step 1: Deploy the transcription service {#deploy_stack type=docker_deploy required=true config=devices/jetson_stack.yaml}

Install the transcription service on the reComputer and register your Clip.

### Target: reComputer J40 remote deployment {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_stack.yaml default=true}

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
| Jetson module or JetPack mismatch | This target supports Jetson Orin NX with JetPack 6.2 only; for an RK3576 host choose an RK3576 target |
| Not enough disk space | Free up at least 15 GB on the host |
| Model download fails or is slow | Check the host's internet access and deploy again; a completed download is kept |
| Clip name format error | Use the form `Clip 7036`: Clip, a space, and the four characters |
| AI summary is missing the service address | Fill in the service address and model name, or turn AI summary off |
| Port 8631, 8621, 8622 or 1883 in use | Stop the other service using that port on the host and deploy again |

### Target: reComputer J40 on this computer {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_stack.yaml}

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
| Jetson module or JetPack mismatch | This target supports Jetson Orin NX with JetPack 6.2 only |
| Permission denied while writing the configuration or models | Use "reComputer J40 remote deployment" from another computer over SSH instead |
| Not enough disk space | Free up at least 15 GB |
| Port 8631, 8621, 8622 or 1883 in use | Stop the other service using that port and deploy again |

### Target: reComputer RK3576 remote deployment {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml}

Deploy from this computer to a reComputer RK3576 over SSH.

### Prerequisites

- The host is an RK3576 board with 8 GB of RAM; about 1.6 GB of memory must be free when you deploy
- The host has at least 5 GB of free disk and internet access
- The host has Bluetooth
- The Clip has been unbound from the phone app

### Wiring

1. Power the reComputer RK3576 and connect it to the same network as this computer
2. Charge the Clip and place it next to the host
3. Enter the host IP, SSH username and password
4. Enter the Clip name: "Clip" plus the four characters printed on the Clip, e.g. `Clip 7036`; the phone app shows the same name
5. Turn on "Faster sync over Wi-Fi" and "AI summary (optional)" if you need them, then click Deploy

### Deployment Complete

The first deploy downloads the speech models (about 460 MB) and the speech service (about 1.7 GB) and starts the services; how long it takes depends on your network speed. Then:

1. Find the API key at the end of the deploy log and keep it
2. Open `http://<host-ip>:8631/` in your browser and enter the API key

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The board check reports another board | This target supports RK3576 boards only |
| The board check reports not enough free memory | Stop other services on the host until about 1.6 GB is free, then deploy again |
| Not enough disk space | Free up at least 5 GB on the host |
| Model download fails or is slow | Check the host's internet access and deploy again; a completed download is kept |
| Clip name format error | Use the form `Clip 7036`: Clip, a space, and the four characters |
| AI summary is missing the service address | Fill in the service address and model name, or turn AI summary off |
| Port 8631, 8621 or 1883 in use | Stop the other service using that port on the host and deploy again |

### Target: reComputer RK3576 on this computer {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml}

Run SenseCraft Solution on the reComputer RK3576 itself and deploy there.

### Prerequisites

- This computer is an RK3576 board with 8 GB of RAM; about 1.6 GB of memory must be free
- It has at least 5 GB of free disk, internet access and Bluetooth
- The Clip has been unbound from the phone app

### Wiring

1. Make sure this computer is online
2. Charge the Clip and place it next to the host
3. Enter the Clip name, e.g. `Clip 7036`
4. Turn on "Faster sync over Wi-Fi" and "AI summary (optional)" if you need them, then click Deploy

### Deployment Complete

The first deploy downloads the speech models (about 460 MB) and the speech service (about 1.7 GB) and starts the services; how long it takes depends on your network speed. Then:

1. Find the API key at the end of the deploy log and keep it
2. Open `http://localhost:8631/` in your browser and enter the API key

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The board check reports not enough free memory | Stop other services until about 1.6 GB is free, then deploy again |
| Permission denied while writing the configuration or models | Use "reComputer RK3576 remote deployment" from another computer over SSH instead |
| Not enough disk space | Free up at least 5 GB |
| Port 8631, 8621 or 1883 in use | Stop the other service using that port and deploy again |

## Step 2: Check the service {#verify_stack type=http_debug required=true config=devices/verify_clip.yaml}

Confirm the transcription service is ready.

### Wiring

1. Enter the host IP (`localhost` when you deployed on this computer)
2. Click Check; HTTP 200 means the service is ready

### Deployment Complete

The transcription service is running on your reComputer.

#### Initial Setup

1. Open `http://<host-ip>:8631/` in your browser and enter the API key shown at the end of the deploy log
2. If you lose the API key, run `sudo cat /opt/clip-private-transcription/config/api_key` on the host
3. To change the Clip, Wi-Fi sync or AI summary settings, edit them in Step 1 and deploy again; leave the API key empty to keep the current one
4. Changes saved in the results page's Settings panel are stored in the data volume (`/var/lib/clip-pt/settings.override.yaml`), survive restarts and redeploys, and take priority over the Step 1 values for the same fields. To go back to the Step 1 values, run `sudo docker exec $(sudo docker ps -qf label=com.docker.compose.service=clip-pt) rm /var/lib/clip-pt/settings.override.yaml` and restart the service

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
