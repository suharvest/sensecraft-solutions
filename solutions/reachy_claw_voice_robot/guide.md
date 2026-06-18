## Preset: Jetson All-in-One {#jetson}

Deploy the full voice conversation stack on a single Jetson device. The robot will listen, think with a local AI model, speak, and express emotions — all under 1 second latency.

| Device | Purpose |
|--------|---------|
| NVIDIA Jetson Orin NX 16GB | Runs AI conversation, speech, vision, and robot control |
| Reachy Mini | Desktop robot with arms, head, antennas, and camera |

**What gets deployed:**
- **Robot Control** — motor, camera, and sensor management
- **Conversation Engine** — AI dialogue + emotion system + web dashboard
- **Vision Analysis** — face detection, emotion recognition, and person tracking (GPU-accelerated)
- **Edge LLM Chat Service** — Qwen3-4B TensorRT runtime that powers the robot's thinking ability

**Prerequisites:**
- Reachy Mini connected to Jetson via USB
- Jetson with JetPack 6.x, SSH access, and internet

## Step 1: Deploy Speech Service {#speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

Deploy the GPU-accelerated speech recognition (ASR) and voice synthesis (TTS) service. The pre-built image includes all dependencies and models — just pull and run.

### Target {#speech_remote type=remote config=devices/speech_deploy.yaml default=true}

Deploy to your Jetson over SSH with one click.

### Wiring

1. Connect your Jetson to the network
2. Enter the Jetson's IP address and SSH credentials
3. Click **Deploy** — the system will pull the pre-built image and start the service automatically

### Deployment Complete

Speech service is running at `http://<jetson-ip>:8621`. Quick test:

```bash
# Check service health
curl http://<jetson-ip>:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify the IP address and credentials. Try `ssh username@ip` from your computer first |
| Image pull slow | The image is ~8GB compressed. Ensure stable internet on the Jetson |
| Service not starting | Check logs: `ssh user@ip "cd reachy-jetson-voice && docker compose logs"` |
| Health check fails | First startup takes ~40 seconds for model warmup. Wait and retry |

### Target {#speech_local type=local config=devices/speech_deploy.yaml}

Deploy directly on the current machine (requires NVIDIA GPU).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed
2. Click **Deploy** to start installation

> **Note:** First startup may take 10-15 minutes for Docker image download and model initialization.

### Deployment Complete

Speech service is running at `http://localhost:8621`. Quick test:

```bash
# Check service health
curl http://localhost:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 8621 already in use | Stop existing services on port 8621 |
| Container keeps restarting | Check logs: `docker logs reachy-jetson-voice-speech-1` |
| Health check fails | First startup takes ~40 seconds for model warmup. Wait and retry |

## Step 2: Deploy Edge LLM Chat Service {#edge_llm_service type=docker_deploy required=true config=devices/edge_llm_deploy.yaml target_inherit_from=speech_service}

Deploy the TensorRT-accelerated Qwen3-4B chat service on the same Jetson.

### Target {#edge_llm_remote type=remote config=devices/edge_llm_deploy.yaml default=true}

Deploy to your Jetson over SSH (credentials inherited from Step 1).

### Wiring

1. Reuse the SSH credentials from Step 1 (the deployer inherits them)
2. Click **Deploy** — the system will pull the prebuilt image and start the container

> **Note:** First startup takes ~10 minutes — the container downloads a prebuilt TensorRT engine and the Qwen3-4B AWQ weights, then runs warmup inference. Subsequent restarts are fast.

### Deployment Complete

Edge LLM service is reachable at `http://<jetson-ip>:11435`. Quick test:

```bash
curl http://<jetson-ip>:11435/v1/models
# Expected: {"object":"list","data":[{"id":"Qwen/Qwen3-4B-AWQ", ...}]}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Health check times out | First run downloads ~3 GB of engine + weights. Watch progress: `docker logs -f edge-llm-chat-service` |
| Out of memory during warmup | Edge LLM needs ~6 GB GPU memory; close other GPU workloads and redeploy |
| `/v1/models` returns 502 | Container is still warming up; wait until logs print `Uvicorn running` then retry |

### Target {#edge_llm_local type=local config=devices/edge_llm_deploy.yaml}

Deploy directly on the current machine (requires NVIDIA Jetson with JetPack 6.x).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed
2. Click **Deploy** to start installation

> **Note:** First startup takes ~10 minutes for engine + weights download and warmup inference.

### Deployment Complete

Edge LLM service is reachable at `http://localhost:11435`. Quick test:

```bash
curl http://localhost:11435/v1/models
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Health check times out | First run downloads ~3 GB of engine + weights. Watch progress: `docker logs -f edge-llm-chat-service` |
| Out of memory during warmup | Edge LLM needs ~6 GB GPU memory; close other GPU workloads and redeploy |

## Step 3: Deploy Reachy Voice Robot {#reachy_deploy type=docker_deploy required=true config=devices/reachy_jetson_deploy.yaml target_inherit_from=speech_service}

Deploy the robot control, conversation, and vision services to your Jetson. The conversation engine consumes the Edge LLM service deployed in Step 2.


### Deployment Complete

Your Reachy Mini voice robot is now running!

#### What's Happening

The robot runs in **Conversation Mode** by default — it listens and responds. Talk to it and it replies in one short sentence, with a matching emotion and head/antenna motion. No setup needed; just speak.

#### Service Overview

| Service | Port | Purpose |
|---------|------|---------|
| Robot Control | 38001 | Motor, camera, and sensor management |
| Conversation Engine | 8640 | AI dialogue + emotion system + dashboard |
| Vision Analysis | 8630 | Face detection, emotion recognition, person tracking |
| Edge LLM Chat Service | 11435 | Qwen3-4B-AWQ TensorRT — powers the robot's thinking ability |
| Speech Service | 8621 | Listens and speaks (deployed in Step 1) |

#### Next Steps

- Open the **Dashboard** at `http://<jetson-ip>:8640` to see conversation logs and robot status
- To tune the robot's personality and behaviour, edit `llm.system_prompt` in the config on the Jetson:
  ```bash
  ssh user@<jetson-ip>
  nano ~/reachy-jetson-llm/reachy-claw.jetson.yaml
  # Edit llm.system_prompt to change how the robot talks
  docker restart reachy-claw
  ```
- To enable optional idle chatter (monologue), set `conversation.mode: monologue` in the same config, then `docker restart reachy-claw`.

### Target {#reachy_remote type=remote config=devices/reachy_jetson_deploy.yaml default=true}

Deploy to your Jetson over SSH with one click.

### Wiring

1. Connect Reachy Mini to Jetson via USB cable
2. Ensure the Jetson is on the network and SSH is accessible
3. Enter the Jetson's IP address and SSH credentials
4. Configure the data directory (default: `~/reachy-data`) for captures and face database
5. Optionally enable **Kiosk Mode** to auto-launch the dashboard fullscreen on boot
6. Click **Deploy** — the system will pull and start robot control, conversation, and vision (TensorRT GPU-accelerated) services. The Edge LLM service from Step 2 must already be running.

### Deployment Complete

The robot is ready within 30 seconds after deployment. Open the dashboard to monitor activity:

```
http://<jetson-ip>:8640
```

**Default mode:** Conversation — the robot listens and responds. Talk to it and it replies in one short sentence with a matching emotion and head/antenna motion. (Optional idle chatter is available via `conversation.mode: monologue`, which makes the robot self-talk roughly every 30 seconds.)

To check all services are running:
```bash
ssh user@<jetson-ip> "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Slow reply (>10 s) | Edge LLM container is degraded. Check: `docker logs edge-llm-chat-service` and `curl http://<jetson-ip>:11435/v1/models` |
| Robot not moving | Check USB connection. A udev rule now auto-reconnects the daemon when the robot is plugged in; if it still won't move, replug the USB cable and restart: `docker restart reachy-daemon` |
| No audio output | Verify Reachy Mini's built-in speaker is working. Check `audio.device` in config |
| Dashboard not loading | Wait 30 seconds for startup. Check: `curl http://<jetson-ip>:8640/health` |
| No camera feed | Vision service builds TRT engines on first boot (~5 min). Check: `docker logs vision-trt` |
| Camera not found on boot | USB camera takes 15-30s to enumerate. Vision service retries automatically (~90s) |
| Camera drops after hours | USB power-management regression. A udev rule disabling autosuspend is installed by the deployer; if it recurs, physically replug the Reachy USB cable |

### Target {#reachy_local type=local config=devices/reachy_jetson_deploy.yaml}

Deploy directly on the current machine (requires NVIDIA Jetson with Reachy Mini connected).

### Wiring

1. Connect Reachy Mini to the machine via USB cable
2. Ensure Docker and NVIDIA Container Toolkit are installed
3. Click **Deploy** to start installation

> **Note:** First startup may take 5-10 minutes for Docker image download and model initialization.

### Deployment Complete

The robot should start talking within 30 seconds after deployment. Open the dashboard to monitor activity:

```
http://localhost:8640
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Robot not moving | Check USB connection. Try replugging the USB cable and restart: `docker restart reachy-daemon` |
| Dashboard not loading | Wait 30 seconds for startup. Check: `curl http://localhost:8640/health` |
| No camera feed | Vision service builds TRT engines on first boot (~5 min). Check: `docker logs vision-trt` |

## Preset: R2000 + Hailo-8 {#r2000_hailo}

Deploy the full Reachy voice robot stack on a single R2000 (Raspberry Pi 5 + Hailo-8). Vision runs on the Hailo NPU, while speech and LLM are consumed from a remote Jetson voice assistant.

| Device | Purpose |
|--------|---------|
| reComputer R2000 (Pi 5 + Hailo-8) | Robot control, conversation, Hailo-accelerated vision |
| Reachy Mini | Desktop robot connected to the R2000 via USB |
| Jetson (remote) | Speech (ASR/TTS) + Edge LLM (TensorRT-Edge-LLM) — deployed in Step 1 |

**What gets deployed:**
- **Robot Control** — motor, camera, and sensor management
- **Conversation Engine** — AI dialogue + emotion system + web dashboard
- **Vision Analysis** — face detection, emotion recognition, and person tracking (Hailo-8 NPU)

**Prerequisites:**
- Reachy Mini connected to R2000 via USB
- USB camera attached to R2000
- Hailo-8 AI HAT seated in M.2 slot, PCIe Gen3 enabled in `/boot/firmware/config.txt`
- Jetson device with JetPack 6.x, SSH access, and internet (speech service will be deployed in Step 1)

## Step 1: Deploy Speech Service {#hailo_speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

Deploy the GPU-accelerated speech recognition (ASR) and voice synthesis (TTS) service to your Jetson. The pre-built image includes all dependencies and models — just pull and run.

### Target {#hailo_speech_remote type=remote config=devices/speech_deploy.yaml default=true}

Deploy to your Jetson over SSH with one click.

### Wiring

1. Connect your Jetson to the network
2. Enter the Jetson's IP address and SSH credentials
3. Click **Deploy** — the system will pull the pre-built image and start the service automatically

### Deployment Complete

Speech service is running at `http://<jetson-ip>:8621`. Quick test:

```bash
# Check service health
curl http://<jetson-ip>:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify the IP address and credentials. Try `ssh username@ip` from your computer first |
| Image pull slow | The image is ~8GB compressed. Ensure stable internet on the Jetson |
| Service not starting | Check logs: `ssh user@ip "cd reachy-jetson-voice && docker compose logs"` |
| Health check fails | First startup takes ~40 seconds for model warmup. Wait and retry |

### Target {#hailo_speech_local type=local config=devices/speech_deploy.yaml}

Deploy directly on the current machine (requires NVIDIA GPU).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed
2. Click **Deploy** to start installation

> **Note:** First startup may take 10-15 minutes for Docker image download and model initialization.

### Deployment Complete

Speech service is running at `http://localhost:8621`. Quick test:

```bash
# Check service health
curl http://localhost:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 8621 already in use | Stop existing services on port 8621 |
| Container keeps restarting | Check logs: `docker logs reachy-jetson-voice-speech-1` |
| Health check fails | First startup takes ~40 seconds for model warmup. Wait and retry |

## Step 2: Deploy Reachy Voice Robot (Hailo) {#reachy_hailo_deploy type=docker_deploy required=true config=devices/reachy_hailo_deploy.yaml target_inherit_from=hailo_speech_service}

Deploy the robot control, conversation, and Hailo-accelerated vision services to your R2000 in one step. The deployer will automatically install the Hailo stack if missing.


### Deployment Complete

Your Reachy Mini voice robot is now running!

#### What's Happening

The robot runs in **Conversation Mode** by default — it listens and responds. Talk to it and it replies in one short sentence, with a matching emotion and head/antenna motion. No setup needed; just speak.

#### Service Overview

| Service | Port | Purpose |
|---------|------|---------|
| Robot Control | 38001 | Motor, camera, and sensor management |
| Conversation Engine | 8640 | AI dialogue + emotion system + dashboard |
| Vision Analysis | 8630 | Face detection, emotion recognition, person tracking |
| Edge LLM (remote Jetson) | 11435 | Qwen3-4B-AWQ TensorRT — powers the robot's thinking ability |
| Speech Service | 8621 | Listens and speaks (deployed in Step 1) |

#### Next Steps

- Open the **Dashboard** at `http://<r2000-ip>:8640` to see conversation logs and robot status
- To tune the robot's personality and behaviour, edit `llm.system_prompt` in the config:
  ```bash
  ssh pi@<r2000-ip>
  nano ~/reachy-jetson-llm/reachy-claw.jetson.yaml
  # Edit llm.system_prompt to change how the robot talks
  docker restart reachy-claw
  ```
- The AI model is served by the Edge LLM service (`edge-llm-chat-service`, Qwen/Qwen3-4B-AWQ) on the remote Jetson — there is no Ollama. To change the robot's behaviour, edit `llm.system_prompt` above rather than swapping the model.
- To enable optional idle chatter (monologue), set `conversation.mode: monologue` in the same config, then `docker restart reachy-claw`.

### Target {#reachy_hailo_remote type=remote config=devices/reachy_hailo_deploy.yaml default=true}

Deploy to your R2000 over SSH with one click.

### Wiring

1. Connect Reachy Mini to R2000 via USB cable
2. Plug the USB camera into the R2000
3. Ensure the R2000 is on the network and SSH is accessible
4. Enter the R2000's IP address and SSH credentials (default user: `pi`)
5. Enter the **Voice Assistant Host** — the IP of the Jetson running speech + LLM (e.g. `192.168.1.100`)
6. Configure the data directory (default: `~/reachy-data`)
7. Optionally enable **Kiosk Mode** to auto-launch the dashboard fullscreen on boot
8. Click **Deploy** — the system will:
   - Verify or install the Hailo stack (driver + userspace) if missing
   - Pull and start robot control, conversation, and Hailo-accelerated vision services

### Deployment Complete

The robot should start talking within 30 seconds. Open the dashboard:

```
http://<r2000-ip>:8640
```

To verify all services:
```bash
ssh pi@<r2000-ip> "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `/dev/hailo0` not found | Reseat the Hailo HAT in the M.2 slot, reboot, retry. Check `lspci \| grep -i hailo` |
| `hailo-all` install fails | Add the Hailo apt source manually — see `INSTALL.md` in the `vision-hailo` repo |
| Container fails with version mismatch | Host driver and container userspace must be the same version. `sudo apt install --reinstall hailo-all` then redeploy |
| FPS below 5 | Check CPU frequency: set scaling governor to `performance` |
| No face data on dashboard | Verify vision service: `curl http://localhost:8630/` |
| Speech not working | Verify VOICE_ASSISTANT_HOST is reachable: `curl http://<jetson-ip>:8621/health` |
| Robot not moving | Check USB connection. Try replugging: `docker restart reachy-daemon` |

### Target {#reachy_hailo_local type=local config=devices/reachy_hailo_deploy.yaml}

Deploy directly on the current machine (requires R2000 with Hailo-8 and Reachy Mini connected via USB).

### Wiring

1. Connect Reachy Mini to the machine via USB
2. Ensure Docker is installed
3. Click **Deploy** to start installation

> **Note:** First startup may take 5-10 minutes for Docker image download.

### Deployment Complete

The robot should start talking within 30 seconds. Open the dashboard:

```
http://localhost:8640
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `/dev/hailo0` not found | Reseat the Hailo HAT in the M.2 slot, reboot, retry |
| Robot not moving | Check USB connection. Try replugging: `docker restart reachy-daemon` |
| Dashboard not loading | Wait 30 seconds for startup. Check: `curl http://localhost:8640/health` |

# Service Overview (R2000 preset)

| Service | Host | Port | Purpose |
|---------|------|------|---------|
| Speech Service | Jetson (remote) | 8621 | ASR + TTS |
| Edge LLM | Jetson (remote) | 11435 | TensorRT-Edge-LLM (Qwen/Qwen3-4B-AWQ) |
| Robot Control | R2000 | 38001 | Reachy daemon (motors) |
| Conversation Engine | R2000 | 8640 | Dialogue + dashboard |
| Vision (Hailo) | R2000 | 8630 / 8631 | Face detection + emotion + tracking |

---

## Preset: Reachy Mini Wireless (CM4) {#cm4}

Deploy the full Reachy voice robot stack on the Reachy Mini Wireless CM4. Vision runs on the CM4's CPU, while speech and LLM are consumed from a remote Jetson voice assistant.

| Device | Purpose |
|--------|---------|
| Reachy Mini Wireless (CM4) | Robot control, conversation, CPU-based vision |
| Jetson (remote) | Speech (ASR/TTS) + Edge LLM (TensorRT-Edge-LLM) — deployed in Step 1 |

**What gets deployed:**
- **Robot Control** — motor, camera, and sensor management
- **Conversation Engine** — AI dialogue + emotion system + web dashboard
- **Vision Analysis** — face detection, emotion recognition, and person tracking (CPU)

**Prerequisites:**
- Reachy Mini Wireless with onboard CM4
- Docker installed on the CM4
- Jetson device with JetPack 6.x, SSH access, and internet (speech service will be deployed in Step 1)

## Step 1: Deploy Speech Service {#cm4_speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

Deploy the GPU-accelerated speech recognition (ASR) and voice synthesis (TTS) service to your Jetson. The pre-built image includes all dependencies and models — just pull and run.

### Target {#cm4_speech_remote type=remote config=devices/speech_deploy.yaml default=true}

Deploy to your Jetson over SSH with one click.

### Wiring

1. Connect your Jetson to the network
2. Enter the Jetson's IP address and SSH credentials
3. Click **Deploy** — the system will pull the pre-built image and start the service automatically

### Deployment Complete

Speech service is running at `http://<jetson-ip>:8621`. Quick test:

```bash
# Check service health
curl http://<jetson-ip>:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify the IP address and credentials. Try `ssh username@ip` from your computer first |
| Image pull slow | The image is ~8GB compressed. Ensure stable internet on the Jetson |
| Service not starting | Check logs: `ssh user@ip "cd reachy-jetson-voice && docker compose logs"` |
| Health check fails | First startup takes ~40 seconds for model warmup. Wait and retry |

### Target {#cm4_speech_local type=local config=devices/speech_deploy.yaml}

Deploy directly on the current machine (requires NVIDIA GPU).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed
2. Click **Deploy** to start installation

> **Note:** First startup may take 10-15 minutes for Docker image download and model initialization.

### Deployment Complete

Speech service is running at `http://localhost:8621`. Quick test:

```bash
# Check service health
curl http://localhost:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Port 8621 already in use | Stop existing services on port 8621 |
| Container keeps restarting | Check logs: `docker logs reachy-jetson-voice-speech-1` |
| Health check fails | First startup takes ~40 seconds for model warmup. Wait and retry |

## Step 2: Deploy Reachy Voice Robot (CM4) {#reachy_cm4_deploy type=docker_deploy required=true config=devices/reachy_cm4_deploy.yaml target_inherit_from=cm4_speech_service}

Deploy the robot control, conversation, and vision services to your CM4 in one step.


### Deployment Complete

Your Reachy Mini voice robot is now running!

#### What's Happening

The robot runs in **Conversation Mode** by default — it listens and responds. Talk to it and it replies in one short sentence, with a matching emotion and head/antenna motion. No setup needed; just speak.

#### Service Overview

| Service | Port | Purpose |
|---------|------|---------|
| Robot Control | 38001 | Motor, camera, and sensor management |
| Conversation Engine | 8640 | AI dialogue + emotion system + dashboard |
| Vision Analysis | 8630 | Face detection, emotion recognition, person tracking |
| Edge LLM (remote Jetson) | 11435 | Qwen3-4B-AWQ TensorRT — powers the robot's thinking ability |
| Speech Service | 8621 | Listens and speaks (deployed in Step 1) |

#### Next Steps

- Open the **Dashboard** at `http://<cm4-ip>:8640` to see conversation logs and robot status
- To tune the robot's personality and behaviour, edit `llm.system_prompt` in the config:
  ```bash
  ssh pi@<cm4-ip>
  nano ~/reachy-jetson-llm/reachy-claw.jetson.yaml
  # Edit llm.system_prompt to change how the robot talks
  docker restart reachy-claw
  ```
- The AI model is served by the Edge LLM service (`edge-llm-chat-service`, Qwen/Qwen3-4B-AWQ) on the remote Jetson — there is no Ollama. To change the robot's behaviour, edit `llm.system_prompt` above rather than swapping the model.
- To enable optional idle chatter (monologue), set `conversation.mode: monologue` in the same config, then `docker restart reachy-claw`.

### Target {#reachy_cm4_remote type=remote config=devices/reachy_cm4_deploy.yaml default=true}

Deploy to your CM4 over SSH with one click.

### Wiring

1. Ensure the CM4 is on the network and SSH is accessible
2. Enter the CM4's IP address and SSH credentials (default user: `pi`)
3. Enter the **Voice Assistant Host** — the IP of the Jetson running speech + LLM (e.g. `192.168.1.100`)
4. Configure the data directory (default: `~/reachy-data`)
5. Optionally enable **Kiosk Mode** to auto-launch the dashboard fullscreen on boot
6. Click **Deploy** — the system will pull and start all services

### Deployment Complete

The robot should start talking within 30 seconds. Open the dashboard:

```
http://<cm4-ip>:8640
```

To verify all services:
```bash
ssh pi@<cm4-ip> "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not installed | Install via the official script from get.docker.com |
| Speech not working | Verify VOICE_ASSISTANT_HOST is reachable: `curl http://<jetson-ip>:8621/health` |
| No camera feed | Check: `ls /dev/video*`. If empty, replug the USB camera |
| Robot not moving | Check USB connection. Try replugging: `docker restart reachy-daemon` |
| Dashboard not loading | Wait 30 seconds for startup. Check: `curl http://localhost:8640/health` |

### Target {#reachy_cm4_local type=local config=devices/reachy_cm4_deploy.yaml}

Deploy directly on the Reachy Mini Wireless CM4.

### Wiring

1. Ensure Docker is installed on the CM4
2. Click **Deploy** to start installation

> **Note:** First startup may take 5-10 minutes for Docker image download.

### Deployment Complete

The robot should start talking within 30 seconds. Open the dashboard:

```
http://localhost:8640
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not installed | Install via the official script from get.docker.com |
| Robot not moving | Check USB connection. Try replugging: `docker restart reachy-daemon` |
| Dashboard not loading | Wait 30 seconds for startup. Check: `curl http://localhost:8640/health` |

# Service Overview (CM4 preset)

| Service | Host | Port | Purpose |
|---------|------|------|---------|
| Speech Service | Jetson (remote) | 8621 | ASR + TTS |
| Edge LLM | Jetson (remote) | 11435 | TensorRT-Edge-LLM (Qwen/Qwen3-4B-AWQ) |
| Robot Control | CM4 | 38001 | Reachy daemon (motors) |
| Conversation Engine | CM4 | 8640 | Dialogue + dashboard |
| Vision (CM4) | CM4 | 8630 / 8631 | Face detection + emotion + tracking |
