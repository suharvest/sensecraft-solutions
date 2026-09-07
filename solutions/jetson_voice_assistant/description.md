## What This Capability Does

Adds “listen and speak” capability to robots, devices, and applications. Speech recognition and speech generation run on your local edge device, so audio does not need to go to the cloud after deployment.

## What You Get After Deployment

- A local listening service: send microphone audio in and receive recognized text.
- A local speaking service: send text in and receive playable speech.
- Standard interfaces for robots, web apps, kiosks, industrial systems, or your own AI conversation flow.
- Offline operation after the first deployment downloads the image and models.

## Where It Fits

| Scenario | How to Use It |
|----------|-------------|
| Voice-controlled robots | Turn spoken commands into text, send them to your control logic or LLM, then speak the response back |
| Smart kiosks | Let visitors ask questions out loud, query a knowledge base locally, and hear the answer |
| Industrial voice commands | Trigger actions by voice when operators cannot use a screen or keyboard |
| Private voice entry point | Let multiple devices send audio to one edge device for centralized listening and speaking |

## Interfaces for Your Application

| Capability | How to Connect | Port / Path | Output |
|------------|----------------|-------------|--------|
| Live transcription | WebSocket | `:8621/asr/stream` | Recognized text as it arrives |
| Live speech playback | HTTP POST | `:8621/tts/stream` | Playable audio stream |
| Generate speech file | HTTP POST | `:8621/tts` | WAV file |
| Upload audio for transcription | HTTP POST | `:8621/asr` | Recognized text |
| Service status | HTTP GET | `:8621/health` | Readiness status |

## Technical Specs

| Spec | Jetson Orin NX | RK3588 | RK3576 | Raspberry Pi 5 |
|------|---------------|--------|--------|----------------|
| Speech to text | Paraformer / Qwen3 (TensorRT) | Qwen3 (RKNN) | Qwen3 (RKNN) | Paraformer (ONNX) |
| Text to speech | Matcha-TTS / Qwen3 (TensorRT) | Matcha (RKNN) | Matcha (RKNN) | Matcha (ONNX) |
| Voice-to-Voice Latency (p50) | 58 ms | 394 ms | 1099 ms | — |
| Memory Required | 2 GB | 6 GB | 4 GB | 2 GB |
| Disk Required | 7.5 GB | 4.4 GB | 4.4 GB | 2.8 GB |
| Languages | zh+en / 52 (Qwen3) | zh+en / 52 (Qwen3) | zh+en / 52 (Qwen3) | zh+en |

**Supported Hardware:** Jetson Orin Nano/NX/AGX · RK3576 · RK3588 · Raspberry Pi 4/5
**Network:** Internet needed for first deployment (downloads image + models). Works fully offline after setup.
