# Voice-Controlled Grasping Arm

Say **"Hey Jarvis, grab the water bottle"** — the arm looks at the table through its wrist-mounted RGB-D camera, finds the bottle, plans a grasp and picks it up, then tells you what it did. Everything runs on the Jetson: wake word, speech recognition, the LLM that parses your intent, object detection, grasp planning and speech synthesis. No cloud, no online API.

## What it can grasp

| Object | Strategy | Status |
|---|---|---|
| Cardboard boxes | side-face geometric grasp (multi-frame median, force 1.0 N·m) | verified |
| Cups (opaque, short) | side-face grasp, adaptive force | verified |
| Standing bottles (opaque) | cylinder route: level side approach, mid-body grip, fixed 0.8 N·m | verified |
| Bananas | elongated route (grip across the long axis) | verified |
| Oranges | round route: level approach, equator-height grip | verified |
| Transparent bottles | — | not possible: stereo depth cannot see clear plastic + water |

Objects too wide for the 0.100 m jaw get a spoken decline ("The box is too big for me to grip"). Detection runs on the GPU through a prebuilt native TensorRT engine: scene capture takes 0.6–1.6 s and a full voice-to-carry grasp cycle about 11 s.

## How it works

```
reSpeaker mic ─▶ wake word ─▶ streaming ASR ─▶ Qwen3.5-4B (TensorRT-Edge-LLM)
                                                    │  grasp_object("water bottle")
                                                    ▼
                            Orbbec Gemini2 ─▶ YOLOE open-vocab detector (10 classes)
                                                    │  instance mask
                                                    ▼
                              depth cloud ─▶ PCA shape descriptor (elongation /
                              planarity / spine-bend) ─▶ route: box faces |
                              cylinder | elongated | round ─▶ 6-DoF grasp pose
                                                    │
                                                    ▼
                              reBot B601-DM: approach ─ grip (force-controlled)
                              ─ lift ─ carry home ─▶ TTS confirmation
```

Four containers, one compose file:

- **rebot-arm** — the agent: wake word, camera, detection, grasp pipeline, arm control, dashboard (`:8776`) and observation API (`:8775`)
- **seeed-voice** — streaming Qwen3 ASR + MOSS-TTS-Nano speech synthesis (`:8621`)
- **edge-llm** — Qwen3.5-4B-AWQ with MTP speculative decoding on TensorRT-Edge-LLM (`:8000`)
- **warehouse** — an MCP inventory service the agent can consult (`:2125`)

The detector takes its class vocabulary as a runtime input rather than baking it into the weights, so extending the recognizable object list is a config edit — no model re-export, no retraining.

## The one manual step

**Hand-eye calibration** (one-time, ~30 min): grasping needs millimeter-accurate camera-to-arm geometry, which is physically unique to each unit. The guide walks through collecting ~16 poses of a printed ArUco board and solving for the transform. Until it's done, voice chat, detection and the dashboard all work — only grasping waits.

## Requirements

- reComputer J4012 / Jetson Orin NX 16 GB (JetPack 6) — the compose file mounts host CUDA/TensorRT
- reBot B601-DM arm (USB serial) + Orbbec Gemini 2 on the wrist (USB 3.0)
- reSpeaker USB mic + any speaker
- ~8.5 GB of model downloads on first boot (LLM engine, speech engines, detector), plus ~1.4 GB of container images
