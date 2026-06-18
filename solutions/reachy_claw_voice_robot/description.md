## What This Solution Does

Turn your Reachy Mini desktop robot into a real-time voice companion. The robot listens to its surroundings, thinks with a local AI model, speaks back, and expresses emotions through head movements and antenna poses — all with under 1 second end-to-end latency, running entirely on your Jetson device.

## Core Value

| Value | Description |
|-------|-------------|
| Real-time Conversation | Under 1 second from hearing your voice to speaking back — fast enough for natural dialogue |
| Emotional Expressions | 14 distinct emotions (happy, curious, surprised, etc.) shown through head movements and antenna poses |
| Fully Local | Everything runs on your Jetson — no cloud, no subscription, no internet required after setup |
| Monologue Mode | Robot automatically generates "inner thoughts" for exhibition/demo scenarios without any user interaction |

## Use Cases

| Scenario | Description |
|----------|-------------|
| Exhibition & Trade Shows | Place the robot at your booth — it talks to itself, reacts to visitors, and draws attention |
| Retail & Reception | Greet customers with natural conversation and emotional expressions |
| Education & Research | Study human-robot interaction with a fully customizable local AI pipeline |
| Office Companion | A desk robot that mutters observations and responds when spoken to |

## Deployment Options

Pick one based on your hardware budget and deployment needs:

| Preset | Hardware | When to choose |
|--------|----------|----------------|
| **Jetson All-in-One** | 1× Jetson Orin NX 16GB | Simplest setup. Speech, vision, and brain on one box. |
| **R2000 + Hailo-8** | 1× reComputer R2000 (Pi 5 + Hailo-8) | Low-power NPU-accelerated vision. Speech and LLM on a remote Jetson via VOICE_ASSISTANT_HOST. |
| **Reachy Mini Wireless (CM4)** | 1× Reachy Mini Wireless with onboard CM4 | Self-contained edge deployment on the robot itself. Speech and LLM on a remote Jetson via VOICE_ASSISTANT_HOST. |

## What You Need

**Hardware (Jetson All-in-One preset):**

| Device | Purpose |
|--------|---------|
| Reachy Mini (by Pollen Robotics) | Desktop robot with arms, head, antennas, and camera |
| NVIDIA Jetson Orin NX 16GB | Runs all AI services — conversation, speech, vision, and robot control |
| USB cable | Connects Reachy Mini to Jetson |

**Hardware (R2000 + Hailo-8 preset):**

| Device | Purpose |
|--------|---------|
| Reachy Mini (by Pollen Robotics) | Desktop robot, USB-connected to the R2000 |
| reComputer R2000 (Pi 5 + Hailo-8) | Robot control, conversation, Hailo-accelerated vision |
| USB camera | Plugged into the R2000 |

**Hardware (Reachy Mini Wireless CM4 preset):**

| Device | Purpose |
|--------|---------|
| Reachy Mini Wireless (by Pollen Robotics) | Desktop robot with onboard CM4 — runs all robot services |
| Jetson (any model) | Remote speech (ASR/TTS) and LLM host, deployed separately |

**Software prerequisites (all presets):**

| Prerequisite | How to Get It |
|-------------|---------------|
| Jetson voice assistant | Deploy the **Jetson Local Voice Assistant** solution first — required for speech and LLM on all presets |
**Network:** Internet required during deployment to download services (~5 GB) and AI model (~1.5 GB). After setup, runs fully offline.
