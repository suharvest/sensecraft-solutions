## What This Reference Design Does

This reference design helps developers and solution integrators get started with edge AI agents using minimal hardware (a single SenseCAP Watcher and a USB-C cable). It walks through a step-by-step technical progression: starting with natural streaming voice conversation and agent pairing, adding proactive vision wake-up and voice parameter tuning, and advancing to dual-chip on-device face recognition.

## Three Progressive Presets

| Tier | Core Hardware | Key Experience | Best For |
|------|---------------|----------------|----------|
| **Voice Dialog & Agent** ✨ | SenseCAP Watcher (+ optional host) | Out-of-the-box streaming voice conversation; 6-digit code pairs with SenseCraft AI to customise agents and MCP linkages | Developers exploring voice agents and workstation integration |
| **Proactive Vision Wake** | SenseCAP Watcher alone | Gives the device eyes: greets upon seeing a person; voice explanations and tuning for threshold, duration, and cooldown interval | Developers exploring edge vision-to-voice proactive wake-up |
| **On-Device Face Recognition** | SenseCAP Watcher alone | Dual-chip architecture (ESP32-S3 + Himax WE2); local 20-face NVS storage, greets by name, familiar mode | Privacy-sensitive smart greeting and office reception |

## Key Capabilities

| Capability | How It Works | Value |
|---|---|---|
| **Natural Streaming Voice Dialog** | Low-latency streaming ASR + LLM + TTS via SenseCraft AI platform or Xiaozhi | Continuous natural conversations, personality templates, and custom voice synthesis |
| **Proactive Vision Wake** | Edge vision trigger (`self.vision.mode`) initiates conversation upon human presence | Breaks away from passive wake words for natural greeting interaction |
| **Voice-Driven Parameter Tuning** | Query and adjust threshold, duration, and interval via `self.model.param_set` | Tune sensitivity and false-alarm rejection in real time through voice without reflashing |
| **On-Device Face Recognition** | Himax WE2 runs SCRFD + MobileFaceNet; ESP32 manages local 128D embeddings | Complete local privacy without cloud uploads; offline face verification |

## Deployment Requirements

- **Minimal Hardware:** One SenseCAP Watcher and a USB-C cable for presets 1 and 2.
- **Network:** 2.4 GHz Wi-Fi only (5 GHz not supported).
- **Face Capacity & Lighting:** Up to 20 faces in local NVS; works best in normal indoor lighting at face height.
