## Preset: Jetson All-in-One {#jetson}

Speech recognition and synthesis, the local LLM, vision and robot control all run on one Jetson.

- **Robot:** Reachy Mini connected to the Jetson via USB.
- **Network:** The Jetson is reachable over SSH and has internet access during deployment to pull images.

## Step 1: Deploy Speech Service {#speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

Deploys the speech recognition (ASR) and voice synthesis (TTS) service; the image includes the models.

### Target {#speech_remote type=remote config=devices/speech_deploy.yaml default=true}

Deploy over SSH to a Jetson Orin NX 16GB running JetPack 6.x.

### Wiring

1. Connect the Jetson to the network
2. Enter the Jetson's IP address and SSH credentials
3. Click **Deploy**

### Deployment Complete

Open `http://<jetson-ip>:8621/health`; it returns `{"asr": true, "tts": true, "streaming_asr": true}`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| SSH connection failed | Try `ssh username@ip` from your computer first and check the IP and credentials |
| Image pull slow | The image is ~8 GB compressed; ensure stable internet on the Jetson |
| Service not starting | Run `ssh user@ip "cd reachy-jetson-voice && docker compose logs"` |
| Health check fails | First startup takes ~40 seconds for model warmup; wait and retry |

### Target {#speech_local type=local config=devices/speech_deploy.yaml}

Deploy to this machine, which needs an NVIDIA GPU with Docker and the NVIDIA Container Toolkit installed.

### Wiring

1. Click **Deploy**; the first image download and model initialization take 10-15 minutes

### Deployment Complete

Open `http://localhost:8621/health`; it returns `{"asr": true, "tts": true, "streaming_asr": true}`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| NVIDIA runtime not found | Run `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 8621 already in use | Stop the service using port 8621 |
| Container keeps restarting | Run `docker logs reachy-jetson-voice-speech-1` |
| Health check fails | First startup takes ~40 seconds for model warmup; wait and retry |

## Step 2: Deploy Edge LLM Chat Service {#edge_llm_service type=docker_deploy required=true config=devices/edge_llm_deploy.yaml target_inherit_from=speech_service}

Deploys the Qwen3.5-4B chat service on the same Jetson. First startup takes about 10 minutes to download ~3 GB of model files and warm up, and the service uses about 6 GB of GPU memory.

### Target {#edge_llm_remote type=remote config=devices/edge_llm_deploy.yaml default=true}

Deploy over SSH to the Jetson from Step 1; the SSH credentials carry over.

### Wiring

1. Click **Deploy**

### Deployment Complete

Open `http://<jetson-ip>:11435/v1/models`; the model list includes `Qwen/Qwen3-4B-AWQ`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Health check times out | Run `docker logs -f edge-llm-chat-service` to watch the download |
| Out of memory during warmup | Close other GPU workloads and redeploy |
| `/v1/models` returns 502 | Wait until the logs print `Uvicorn running`, then retry |

### Target {#edge_llm_local type=local config=devices/edge_llm_deploy.yaml}

Deploy to this machine, which must be a Jetson on JetPack 6.x with Docker and the NVIDIA Container Toolkit installed.

### Wiring

1. Click **Deploy**

### Deployment Complete

Open `http://localhost:11435/v1/models`; the model list includes `Qwen/Qwen3-4B-AWQ`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Health check times out | Run `docker logs -f edge-llm-chat-service` to watch the download |
| Out of memory during warmup | Close other GPU workloads and redeploy |

## Step 3: Deploy Reachy Voice Robot {#reachy_deploy type=docker_deploy required=true config=devices/reachy_jetson_deploy.yaml target_inherit_from=speech_service}

Deploys the robot control, conversation and vision services. The Edge LLM service from Step 2 must already be running.


### Deployment Complete

The robot is ready about 30 seconds after deployment.

#### What's Happening

The robot starts in conversation mode: talk to it and it replies in one sentence with a matching emotion and head/antenna motion.

#### Service Overview

The dashboard is on port 8042; other ports: robot control 38001, vision 8630, Edge LLM 11435, speech 8621.

#### Next Steps

- Open the dashboard at `http://<jetson-ip>:8042` to see conversation logs and robot status and to adjust settings.
- To change the persona, edit the active speech profile's `instructions.txt`. To tune mic gain `audio_volume`, VAD sensitivity `client_vad_threshold` or `tts_speed`, edit `~/reachy-jetson-llm/reachy-voice.yaml`.
- After editing these files or changing settings on the dashboard, run `docker restart reachy-voice`.

### Target {#reachy_remote type=remote config=devices/reachy_jetson_deploy.yaml default=true}

Deploy over SSH to the Jetson from Step 1.

### Wiring

1. Connect Reachy Mini to the Jetson via USB cable
2. Enter the Jetson's IP address and SSH credentials
3. Configure the data directory (default `~/reachy-data`) for captures and the face database
4. Optionally enable **Kiosk Mode** to open the dashboard fullscreen on boot
5. Click **Deploy**

### Deployment Complete

Open `http://<jetson-ip>:8042` and say something to the robot; it replies.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Slow reply (>10 s) | Run `docker logs edge-llm-chat-service` and open `http://<jetson-ip>:11435/v1/models` to check the Edge LLM |
| Robot not moving | Replug the USB cable and run `docker restart reachy-daemon` |
| No audio output | Check Reachy Mini's built-in speaker and `audio.device` in the config |
| Dashboard not loading | Wait 30 seconds, then open `http://<jetson-ip>:8042/health` |
| No camera feed | The vision service builds its engines on first boot (~5 min); run `docker logs vision-trt` |
| Camera not found on boot | The vision service retries automatically for about 90 seconds; wait |
| Camera drops after hours | Physically replug the Reachy USB cable |

### Target {#reachy_local type=local config=devices/reachy_jetson_deploy.yaml}

Deploy to this machine, which must be a Jetson with Reachy Mini connected and Docker and the NVIDIA Container Toolkit installed.

### Wiring

1. Connect Reachy Mini to this machine via USB cable
2. Click **Deploy**; the first image download and model initialization take 5-10 minutes

### Deployment Complete

Open `http://localhost:8042` and say something to the robot; it replies.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| NVIDIA runtime not found | Run `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Robot not moving | Replug the USB cable and run `docker restart reachy-daemon` |
| Dashboard not loading | Wait 30 seconds, then open `http://localhost:8042/health` |
| No camera feed | The vision service builds its engines on first boot (~5 min); run `docker logs vision-trt` |

## Preset: AI Industrial R21 + Hailo-8 {#r2000_hailo}

Robot control, conversation and Hailo-8 vision run on the AI Industrial R21; speech and the LLM come from a remote Jetson.

- **Devices:** A Jetson on JetPack 6.x for speech and the LLM (Step 1 deploys the speech service; the LLM service `edge-llm-chat-service` must be running on that Jetson), and an AI Industrial R21.
- **Peripherals:** Reachy Mini and a USB camera both connect to the AI Industrial R21.
- **Network:** Both devices are reachable over SSH, and the AI Industrial R21 can reach ports 8621 and 11435 on the Jetson.

## Step 1: Deploy Speech Service {#hailo_speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

Deploys the speech recognition (ASR) and voice synthesis (TTS) service on the Jetson; the image includes the models.

### Target {#hailo_speech_remote type=remote config=devices/speech_deploy.yaml default=true}

Deploy over SSH to a Jetson running JetPack 6.x.

### Wiring

1. Connect the Jetson to the network
2. Enter the Jetson's IP address and SSH credentials
3. Click **Deploy**

### Deployment Complete

Open `http://<jetson-ip>:8621/health`; it returns `{"asr": true, "tts": true, "streaming_asr": true}`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| SSH connection failed | Try `ssh username@ip` from your computer first and check the IP and credentials |
| Image pull slow | The image is ~8 GB compressed; ensure stable internet on the Jetson |
| Service not starting | Run `ssh user@ip "cd reachy-jetson-voice && docker compose logs"` |
| Health check fails | First startup takes ~40 seconds for model warmup; wait and retry |

### Target {#hailo_speech_local type=local config=devices/speech_deploy.yaml}

Deploy to this machine, which needs an NVIDIA GPU with Docker and the NVIDIA Container Toolkit installed.

### Wiring

1. Click **Deploy**; the first image download and model initialization take 10-15 minutes

### Deployment Complete

Open `http://localhost:8621/health`; it returns `{"asr": true, "tts": true, "streaming_asr": true}`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| NVIDIA runtime not found | Run `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 8621 already in use | Stop the service using port 8621 |
| Container keeps restarting | Run `docker logs reachy-jetson-voice-speech-1` |
| Health check fails | First startup takes ~40 seconds for model warmup; wait and retry |

## Step 2: Deploy Reachy Voice Robot (Hailo) {#reachy_hailo_deploy type=docker_deploy required=true config=devices/reachy_hailo_deploy.yaml target_inherit_from=hailo_speech_service}

Deploys the robot control, conversation and Hailo vision services on the AI Industrial R21, installing the Hailo driver if it is missing.


### Deployment Complete

The robot is ready about 30 seconds after deployment.

#### What's Happening

The robot starts in conversation mode: talk to it and it replies in one sentence with a matching emotion and head/antenna motion.

#### Service Overview

The dashboard is on port 8042 of the AI Industrial R21; other ports: robot control 38001 and vision 8630 / 8631 on the R21, speech 8621 and Edge LLM 11435 on the Jetson.

#### Next Steps

- Open the dashboard at `http://<r2000-ip>:8042` to see conversation logs and robot status and to adjust settings.
- To change the persona, edit the active speech profile's `instructions.txt`. To tune mic gain `audio_volume`, VAD sensitivity `client_vad_threshold` or `tts_speed`, edit `~/reachy-jetson-llm/reachy-voice.yaml`.
- After editing these files or changing settings on the dashboard, run `docker restart reachy-voice`.

### Target {#reachy_hailo_remote type=remote config=devices/reachy_hailo_deploy.yaml default=true}

Deploy over SSH to the AI Industrial R21. The Hailo-8 must be seated in the M.2 slot with PCIe Gen3 enabled in `/boot/firmware/config.txt`.

### Wiring

1. Connect Reachy Mini to the AI Industrial R21 via USB cable
2. Plug the USB camera into the AI Industrial R21
3. Enter the AI Industrial R21's IP address and SSH credentials (default user `pi`)
4. Enter the **Voice Assistant Host**: the IP of the Jetson running speech and the LLM (e.g. `192.168.1.100`)
5. Configure the data directory (default `~/reachy-data`)
6. Optionally enable **Kiosk Mode** to open the dashboard fullscreen on boot
7. Click **Deploy**

### Deployment Complete

Open `http://<r2000-ip>:8042` and say something to the robot; it replies.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `/dev/hailo0` not found | Reseat the Hailo-8 in the M.2 slot and reboot; check `lspci \| grep -i hailo` |
| `hailo-all` install fails | Add the Hailo apt source manually as described in `INSTALL.md` in the `vision-hailo` repo |
| Container fails with version mismatch | Run `sudo apt install --reinstall hailo-all`, then redeploy |
| FPS below 5 | Set the CPU scaling governor to `performance` |
| No face data on dashboard | Open `http://localhost:8630/` to check the vision service |
| Speech not working | On the R21, open `http://<jetson-ip>:8621/health` to confirm the Jetson is reachable |
| Robot not moving | Replug the USB cable and run `docker restart reachy-daemon` |

### Target {#reachy_hailo_local type=local config=devices/reachy_hailo_deploy.yaml}

Deploy to this machine, which must be an AI Industrial R21 with Hailo-8, Docker installed and Reachy Mini connected via USB.

### Wiring

1. Connect Reachy Mini to this machine via USB
2. Click **Deploy**; the first image download takes 5-10 minutes

### Deployment Complete

Open `http://localhost:8042` and say something to the robot; it replies.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `/dev/hailo0` not found | Reseat the Hailo-8 in the M.2 slot and reboot |
| Robot not moving | Replug the USB cable and run `docker restart reachy-daemon` |
| Dashboard not loading | Wait 30 seconds, then open `http://localhost:8042/health` |

## Preset: Reachy Mini Wireless (CM4) {#cm4}

Robot control, conversation and CPU vision run on the CM4 inside Reachy Mini Wireless; speech and the LLM come from a remote Jetson.

- **Devices:** A Jetson on JetPack 6.x for speech and the LLM (Step 1 deploys the speech service; the LLM service `edge-llm-chat-service` must be running on that Jetson), and a Reachy Mini Wireless.
- **Network:** Both devices are reachable over SSH, and the CM4 can reach ports 8621 and 11435 on the Jetson.

## Step 1: Deploy Speech Service {#cm4_speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

Deploys the speech recognition (ASR) and voice synthesis (TTS) service on the Jetson; the image includes the models.

### Target {#cm4_speech_remote type=remote config=devices/speech_deploy.yaml default=true}

Deploy over SSH to a Jetson running JetPack 6.x.

### Wiring

1. Connect the Jetson to the network
2. Enter the Jetson's IP address and SSH credentials
3. Click **Deploy**

### Deployment Complete

Open `http://<jetson-ip>:8621/health`; it returns `{"asr": true, "tts": true, "streaming_asr": true}`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| SSH connection failed | Try `ssh username@ip` from your computer first and check the IP and credentials |
| Image pull slow | The image is ~8 GB compressed; ensure stable internet on the Jetson |
| Service not starting | Run `ssh user@ip "cd reachy-jetson-voice && docker compose logs"` |
| Health check fails | First startup takes ~40 seconds for model warmup; wait and retry |

### Target {#cm4_speech_local type=local config=devices/speech_deploy.yaml}

Deploy to this machine, which needs an NVIDIA GPU with Docker and the NVIDIA Container Toolkit installed.

### Wiring

1. Click **Deploy**; the first image download and model initialization take 10-15 minutes

### Deployment Complete

Open `http://localhost:8621/health`; it returns `{"asr": true, "tts": true, "streaming_asr": true}`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| NVIDIA runtime not found | Run `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 8621 already in use | Stop the service using port 8621 |
| Container keeps restarting | Run `docker logs reachy-jetson-voice-speech-1` |
| Health check fails | First startup takes ~40 seconds for model warmup; wait and retry |

## Step 2: Deploy Reachy Voice Robot (CM4) {#reachy_cm4_deploy type=docker_deploy required=true config=devices/reachy_cm4_deploy.yaml target_inherit_from=cm4_speech_service}

Deploys the robot control, conversation and vision services on the CM4.


### Deployment Complete

The robot is ready about 30 seconds after deployment.

#### What's Happening

The robot starts in conversation mode: talk to it and it replies in one sentence with a matching emotion and head/antenna motion.

#### Service Overview

The dashboard is on port 8042 of the CM4; other ports: robot control 38001 and vision 8630 / 8631 on the CM4, speech 8621 and Edge LLM 11435 on the Jetson.

#### Next Steps

- Open the dashboard at `http://<cm4-ip>:8042` to see conversation logs and robot status and to adjust settings.
- To change the persona, edit the active speech profile's `instructions.txt`. To tune mic gain `audio_volume`, VAD sensitivity `client_vad_threshold` or `tts_speed`, edit `~/reachy-jetson-llm/reachy-voice.yaml`.
- After editing these files or changing settings on the dashboard, run `docker restart reachy-voice`.

### Target {#reachy_cm4_remote type=remote config=devices/reachy_cm4_deploy.yaml default=true}

Deploy over SSH to the CM4 in Reachy Mini Wireless; Docker must be installed on the CM4.

### Wiring

1. Enter the CM4's IP address and SSH credentials (default user `pi`)
2. Enter the **Voice Assistant Host**: the IP of the Jetson running speech and the LLM (e.g. `192.168.1.100`)
3. Configure the data directory (default `~/reachy-data`)
4. Optionally enable **Kiosk Mode** to open the dashboard fullscreen on boot
5. Click **Deploy**

### Deployment Complete

Open `http://<cm4-ip>:8042` and say something to the robot; it replies.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Docker not installed | Install it with the official script from get.docker.com |
| Speech not working | On the CM4, open `http://<jetson-ip>:8621/health` to confirm the Jetson is reachable |
| No camera feed | Run `ls /dev/video*`; if empty, replug the USB camera |
| Robot not moving | Replug the USB cable and run `docker restart reachy-daemon` |
| Dashboard not loading | Wait 30 seconds, then open `http://localhost:8042/health` |

### Target {#reachy_cm4_local type=local config=devices/reachy_cm4_deploy.yaml}

Deploy directly on the CM4 in Reachy Mini Wireless; Docker must be installed on the CM4.

### Wiring

1. Click **Deploy**; the first image download takes 5-10 minutes

### Deployment Complete

Open `http://localhost:8042` and say something to the robot; it replies.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Docker not installed | Install it with the official script from get.docker.com |
| Robot not moving | Replug the USB cable and run `docker restart reachy-daemon` |
| Dashboard not loading | Wait 30 seconds, then open `http://localhost:8042/health` |
