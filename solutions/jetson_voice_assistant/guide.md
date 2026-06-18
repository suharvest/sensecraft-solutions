## Preset: Deploy Speech Service {#default}

Deploy a streaming speech recognition (ASR) and voice synthesis (TTS) service on your edge device — Jetson Orin, RK3576, RK3588, or Raspberry Pi 5.

| Device | Engine | Best For |
|--------|--------|----------|
| NVIDIA Jetson Orin | TensorRT-EdgeLLM / sherpa-onnx (GPU) | Lowest latency, multilingual, voice clone |
| RK3576 / RK3588 | RKNN (NPU) | Efficient on-device ASR + TTS |
| Raspberry Pi 5 | sherpa-onnx (CPU) | Low-cost Chinese+English voice I/O |

**What you'll get:**
- Real-time streaming speech recognition (WebSocket)
- Low-latency voice synthesis (HTTP streaming + batch)
- Multiple language modes: Chinese+English, English-only, or 52-language Qwen3
- HTTP + WebSocket API on port 8621

**Requirements:** SSH access to device · Internet to pull Docker image and download models · Disk space: 7.5 GB (Jetson), 4.4 GB (RK), or 2.8 GB (RPi)

## Step 1: Deploy Speech Service {#speech_service type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy the speech service to your edge device. The pre-built image includes all dependencies — models auto-download on first start.

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_deploy.yaml default=true}

### Wiring

1. Connect your Jetson to the network
2. Enter the Jetson's IP address and SSH credentials
3. Choose a voice profile from the dropdown
4. Click **Deploy** — the system will pull the image and start the service

### Deployment Complete

Service is running at `http://<device-ip>:8621`. Quick test:

```bash
curl http://<device-ip>:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}

curl -X POST http://<device-ip>:8621/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, I am your voice assistant.", "sid": 0}' \
  --output test.wav
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP and credentials. Try `ssh username@ip` from your computer |
| Image pull slow | The image is ~2 GB compressed. Ensure stable internet on the device |
| Service not starting | Check logs: `ssh user@ip "cd openvoicestream && docker compose logs"` |
| Health check fails | First startup takes ~40 seconds for model warmup. Wait and retry |
| Out of memory | Ensure Jetson has 8GB+ RAM and no other GPU tasks running |
| NVIDIA runtime missing | Install: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |

### Target {#jetson_local type=local device=jetson device_name="Jetson (Local)" config=devices/jetson_deploy.yaml}

Deploy directly on the current machine (requires Jetson with NVIDIA Container Toolkit installed).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed on this machine
2. Choose a voice profile from the dropdown
3. Click **Deploy** — the system will pull the image and start the service

### Deployment Complete

Service is running at `http://localhost:8621`. Quick test:

```bash
curl http://localhost:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not found | Install Docker: `curl -fsSL https://get.docker.com \| sh` |
| NVIDIA runtime missing | Install: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| Image pull slow | The image is ~2 GB compressed. Ensure stable internet |
| Health check fails | First startup takes ~40 seconds for model warmup. Wait and retry |
| Out of memory | Ensure Jetson has 8GB+ RAM and no other GPU tasks running |

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_deploy.yaml}

### Wiring

1. Connect your RK3576 device to the network
2. Enter the device IP and SSH credentials
3. Choose a voice profile from the dropdown
4. Click **Deploy** — models download on first start

### Deployment Complete

Service is running at `http://<device-ip>:8621`. Quick test:

```bash
curl http://<device-ip>:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP and credentials. Default user: `cat` |
| NPU not detected | Ensure `rknpu` driver is loaded: `ls /dev/rknpu` |
| Models not downloading | Check internet and HF endpoint. Models ~3.6 GB, may take 10-20 minutes |
| Health check fails | First startup takes ~60 seconds for model initialization |
| Out of memory | RK3576 needs 4GB+ RAM available. RK3588 needs 6GB+ |

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_deploy.yaml}

### Wiring

1. Connect your RK3588 device to the network
2. Enter the device IP and SSH credentials
3. Choose a voice profile from the dropdown
4. Click **Deploy** — models download on first start

### Deployment Complete

Service is running at `http://<device-ip>:8621`. Quick test:

```bash
curl http://<device-ip>:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP and credentials. Default user: `cat` |
| NPU not detected | Ensure `rknpu` driver is loaded: `ls /dev/rknpu` |
| Models not downloading | Check internet and HF endpoint. Models ~3.6 GB, may take 10-20 minutes |
| Health check fails | First startup takes ~60 seconds for model initialization |
| Out of memory | RK3588 needs 6GB+ RAM available |

### Target {#rpi_remote type=remote device=rpi device_name="Raspberry Pi" config=devices/rpi_deploy.yaml}

### Wiring

1. Connect your Raspberry Pi to the network
2. Enter the Pi's IP address and SSH credentials
3. Choose a voice profile from the dropdown
4. Click **Deploy** — the CPU-only image is only 568 MB

### Deployment Complete

Service is running at `http://<device-ip>:8621`. Quick test:

```bash
curl http://<device-ip>:8621/health
# Expected: {"asr": true, "tts": true, "streaming_asr": true}
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP and credentials. Default user: `pi` |
| Service not starting | Check Docker is installed: `docker --version` |
| Health check fails | First startup takes ~30 seconds for model warmup |
| ASR not working | RPi 4 with ASR-only profile has no TTS. Use `rpi5-default` on Pi 5 for both |

## Step 2: Voice Demo {#voice_demo type=voice_chat required=false config=devices/voice_demo.yaml}

Try the deployed speech service directly from this page. Enter the device IP address, then use the panels below to test speech recognition and voice synthesis.

### Speech Recognition (ASR)

Press and hold the **Record** button to speak. Your speech will be recognized in real-time and the transcribed text will appear on screen.

### Text to Speech (TTS)

Type any text and click **Generate** to hear it spoken.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Microphone not working | Allow microphone access when prompted by your browser |
| ASR shows no results | Verify the service is running: `curl http://<ip>:8621/health` |
| TTS playback silent | Check browser audio is not muted. Try a shorter text first |
### Deployment Complete

Congratulations! Your local voice service is running.

#### Quick Verification

1. Open `http://<device-ip>:8621/health` in your browser — all fields should show `true`
2. Test voice synthesis with the `curl` command above
3. Connect your application to the API endpoints

#### API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/asr/stream` | WebSocket | Real-time streaming speech recognition |
| `/tts` | POST | Text-to-speech (returns WAV) |
| `/tts/stream` | POST | Streaming text-to-speech (returns raw PCM) |
| `/asr` | POST | Offline speech recognition (upload WAV file) |

#### Next Steps

- Connect your LLM to complete the voice assistant pipeline: ASR → LLM → TTS
- Adjust voice profile from the Devices page after deployment
- [OpenVoiceStream GitHub](https://github.com/suharvest/openvoicestream)
