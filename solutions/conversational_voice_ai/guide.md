## Preset: Cloud or OpenAI-Compatible LLM {#cloud_llm}

Speech remains local while recognized text is sent to Qwen API or another OpenAI-compatible endpoint. The default is Alibaba Cloud Model Studio's Beijing endpoint; replace the base URL, key, and model ID for another provider.

| Device | Purpose |
|--------|---------|
| RK3576 / RK3588 / Orin Nano / Orin NX | Runs local speech and the duplex agent |
| Qwen API or compatible endpoint | Generates conversational replies |

**Requirements:** Continuous internet · valid API key · streaming Chat Completions support

**Optional wake word:** Select **Wake word required** in the deployment form and
enter any short Chinese or English phrase. The bundled open-vocabulary
sherpa-onnx detector compiles it on startup and plays a short 880 Hz
confirmation tone when it is accepted. **Always listening** remains the default;
the phrase and sensitivity are retained in the Agent state volume.

## Step 1: Deploy the Cloud-Backed Voice Terminal {#deploy_cloud type=docker_deploy required=true config=devices/cloud_rk3576.yaml}

After deployment, users can interrupt a spoken answer at any time.

### Target {#cloud_rk3576 type=remote device=rk3576 device_name="RK3576" config=devices/cloud_rk3576.yaml default=true}

Run speech on RK3576 and connect to a cloud or LAN model.

### Wiring

1. Connect the AEC microphone and speaker
2. Fill in the SSH details and the model endpoint settings
3. The Qwen defaults use the current low-latency `qwen3.5-flash` model

The reSpeaker may be connected before deployment or hot-plugged after the
Agent starts. The Agent selects a physical capture device by stable USB product
identity, ignores HDMI/DP pseudo-inputs, and recovers after unplug/replug without
restarting the container.

### Deployment Complete

Ask a question. Within one second of playback starting, speak again; the current answer should stop immediately.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| API returns 401 | Confirm the API key belongs to the endpoint's region |
| Speech is recognized but no reply plays | Inspect the agent LLM error and confirm streaming output is supported |
| Audio does not recover after hot-plug | Confirm the new Agent image is running and Compose has the dynamic `/dev/snd` mount plus the `116:*` cgroup rule |

### Target {#cloud_local type=local device=jetson config=devices/cloud_jetson.yaml}

Deploy directly on the machine running SenseCraft Solution. This local target
requires a Jetson Orin with JetPack 6.2, Docker, and NVIDIA Container Toolkit.

### Wiring

1. Connect the AEC microphone and speaker to this machine
2. Fill in the model endpoint settings and the assistant personality
3. Deploy and wait for speech model warmup

### Deployment Complete

Ask a question, then speak while the reply is playing to verify interruption.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Local deployment is unsupported | Use the remote target unless this machine is a Jetson Orin running JetPack 6.2 |
| NVIDIA runtime missing | Install NVIDIA Container Toolkit and restart Docker |

### Target {#cloud_rk3588 type=remote device=rk3588 device_name="RK3588" config=devices/cloud_rk3588.yaml}

Run speech on RK3588 and connect to a cloud or LAN model.

### Wiring

1. Connect the AEC microphone and speaker
2. Fill in the SSH details and the model endpoint settings
3. Deploy and wait for the speech models to become ready

### Deployment Complete

Complete two turns, then interrupt the third answer. The dashboard should move from speaking to barged-in/listening.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Replies repeat | Confirm the microphone exposes a real AEC channel and retry at a lower speaker volume |
| Audio continues after interruption | Confirm the agent drains playback; avoid external players that buffer several seconds |

### Target {#cloud_jetson type=remote device=jetson device_name="Jetson Orin" config=devices/cloud_jetson.yaml}

Run speech on Orin Nano or Orin NX and connect to a cloud or LAN model.

### Wiring

1. Connect the AEC microphone and speaker
2. Choose the Orin Nano or Orin NX voice profile
3. Fill in the SSH details and the model endpoint settings

### Deployment Complete

After warmup, complete two turns and speak during playback to verify interruption.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| CUDA initialization fails | Check JetPack 6.2, TensorRT 10.3, and the NVIDIA container runtime |
| Orin Nano runs out of memory | Use `jetson-qwen3asr-matcha`; do not start a local 4B model on Nano |

### Target {#cloud_rpi5 type=remote device=rpi5 device_name="Raspberry Pi 5" config=devices/cloud_rpi5.yaml}

Run the CPU speech stack on a Raspberry Pi 5 and connect to a cloud or LAN model. **English only** — this board has no Qwen3-ASR backend, and Whisper's Chinese error rate on it (50.30% short / 57.74% long CER) makes Chinese a refusal rather than a degraded option.

### Wiring

1. Connect the AEC microphone and speaker
2. Fill in the SSH details and the model endpoint settings
3. Leave the conversation language on English; any other value stops the deployment before services start

The reSpeaker may be connected before deployment or hot-plugged after the
Agent starts.

### Deployment Complete

Ask a question in English. Within one second of playback starting, speak again; the current answer should stop immediately.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment stops with "not supported" | The language you picked is not served on this board; select English |
| Replies are slow | CPU-only ASR and TTS share four cores; close other workloads or move to an NPU board |
| Audio does not recover after hot-plug | Confirm Compose has the dynamic `/dev/snd` mount plus the `116:*` cgroup rule |

## Step 2: Verify Conversation and Barge-in {#verify_cloud type=web_dashboard required=true config=devices/dashboard_cloud.yaml}

Watch the listening, thinking, speaking, and barged-in states.

### Deployment Complete

Three normal turns plus an immediate stop when you say “wait” during playback pass the core experience test.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| State changes but there is no sound | Check the default playback device; avoid a PortAudio device with zero output channels |
| Room noise triggers interruptions | Verify the AEC channel first, then raise the client VAD threshold slightly; do not mute capture |

## Step 3: Verify the Selected Language {#voice_chat_cloud type=web_dashboard required=true config=devices/voice_chat_cloud.yaml}

Confirm that the language chosen at deploy time is the language recognized and spoken back.

### Deployment Complete

Two or three turns transcribed in the selected language, answered aloud in the same language, pass this check.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Replies come back in the wrong language | Check the assistant personality prompt; it instructs the model to reply in the user's language |
| Deployment never started | An unsupported (language, device) pair stops before any service starts; pick a language this board serves |
| Transcript language is right but audio is wrong | The speech profile resolved for this pair is marked untested; report the language and board rather than tuning it in place |

## Preset: Fully Local Conversation {#local_llm}

Keep speech and conversation on-device. The packaged paths are RK3588 + RK1828 running Qwen3-4B, or Orin NX 16GB running Qwen3.5-4B.

| Device | Local model |
|--------|-------------|
| RK3588 + RK1828 / RM182X | Qwen3-4B on the PCIe NPU |
| Orin NX 16GB | Qwen3.5-4B alongside Qwen3-ASR + Matcha |

**Requirements:** Internet for first artifact download · initialized RK1828 host driver/firmware · JetPack 6.2 on Orin NX

## Step 1: Deploy Fully Local Voice AI {#deploy_local type=docker_deploy required=true config=devices/local_orin_nx.yaml}

Deploy the speech service, local model service, and resident duplex agent.

### Target {#local_orin_nx type=remote device=orin_nx device_name="Orin NX" config=devices/local_orin_nx.yaml default=true}

Run Qwen3-ASR, Matcha-TTS, and Qwen3.5-4B on Orin NX 16GB.

### Wiring

1. Connect the AEC microphone and speaker
2. Confirm the device is Orin NX 16GB with at least 25GB free disk
3. Enter SSH credentials and deploy

### Deployment Complete

First artifact download and warmup can take several minutes. After both health checks pass, test conversation and interruption.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Model load runs out of memory | Stop other GPU containers; do not deploy this preset to Orin Nano 8GB |
| Engine provenance check fails | Keep the pinned engine revision and do not mix engines built for another TensorRT/JetPack version |

### Target {#local_this_machine type=local device=orin_nx config=devices/local_orin_nx.yaml}

Deploy directly on this machine. The local target requires an Orin NX 16GB
running JetPack 6.2 with enough free memory for speech and Qwen3.5-4B.

### Wiring

1. Connect the AEC microphone and speaker
2. Confirm at least 25GB free disk and stop other GPU workloads
3. Deploy and wait for the local LLM and speech service to become healthy

### Deployment Complete

Disconnect external networking after warmup and verify conversation still works.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Local machine is not Orin NX 16GB | Choose the remote target and select the correct edge device |
| Model load runs out of memory | Stop other GPU containers before deploying |

### Target {#local_rk3588 type=remote device=rk3588_rk1828 device_name="RK3588 + RK1828" config=devices/local_rk3588_rk1828.yaml}

Run speech on RK3588 and Qwen3-4B on the RK1828 card.

### Wiring

1. Confirm independent 12V power, the RK1828 driver service, and its device node
2. Connect the AEC microphone and speaker
3. Enter SSH credentials and deploy

### Deployment Complete

Check health on ports 1828 and 8621, then run multi-turn conversation and interruption tests.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| RK1828 cannot load the model | Check host driver, firmware, and independent power; never run `rknn-smi reset` |
| Another model occupies the card | RK1828 can keep only one large model resident; stop other RK1828 inference services |

## Step 2: Verify Local Conversation and Barge-in {#verify_local type=web_dashboard required=true config=devices/dashboard_local.yaml}

Disconnect external networking and confirm that dialogue continues locally.

### Deployment Complete

Three offline turns plus a successful interruption during playback pass the fully local test.

The application is now continuously monitoring the microphone. Final acceptance must use the real room and real speaker volume: run three turns, interrupt 0.5–1 second after each answer begins, and confirm the old reply stops immediately without losing the interrupting utterance.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| First offline start fails | Complete one online startup so every image and model artifact is cached |
| Replies are too long | Keep the voice prompt to one or two spoken sentences so synthesis stays responsive |

## Step 3: Verify the Selected Language Locally {#voice_chat_local type=web_dashboard required=true config=devices/voice_chat_local.yaml}

Confirm that the language chosen at deploy time is the language recognized and spoken back.

### Deployment Complete

Two or three turns transcribed in the selected language, answered aloud in the same language, pass this check.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Replies come back in the wrong language | Check the assistant personality prompt; it instructs the model to reply in the user's language |
| Deployment never started | An unsupported (language, device) pair stops before any service starts; pick a language this board serves |
| Transcript language is right but audio is wrong | The speech profile resolved for this pair is marked untested; report the language and board rather than tuning it in place |
