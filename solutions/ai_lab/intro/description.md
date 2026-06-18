## What This Lab Does

A one-stop sandbox to try popular open-source AI models on your reComputer RK3576 / RK3588. Pick a preset, deploy with one click, and start calling the API — everything runs on the device, no cloud needed.

| Preset | Model | What you get | Hardware |
|--------|-------|--------------|----------|
| Object Detection | YOLO 11 (Nano / Small / Medium) | Detect 80 common objects in images or live video | RK3576 or RK3588 |
| LLM Chat | DeepSeek-R1 (1.5B / 7B, multiple quantizations) | OpenAI-compatible chat API, fully local | RK3576 (8GB recommended for 7B) |
| Vision Chat | Qwen2.5-VL | Describe images, answer questions about pictures | RK3576 (8GB+) |

## Output Interfaces

| Preset | Endpoint | Method | Description |
|--------|----------|--------|-------------|
| Object Detection | :8000/api/models/yolo11/predict | POST | Upload image, returns bounding boxes |
| Object Detection | :8000/api/video_feed | GET | MJPEG stream with detection overlay |
| LLM Chat | :8001/v1/chat/completions | POST | OpenAI-compatible chat (supports streaming) |
| Vision Chat | :8002/v1/chat/completions | POST | OpenAI-compatible vision chat (text + image) |
| Vision Chat | :8002/docs | GET | Interactive API docs (Swagger UI) |

**Quick start — Object Detection:**
```bash
curl -X POST http://<device-ip>:8000/api/models/yolo11/predict \
  -F "file=@photo.jpg" -F "conf=0.5"
```

**Quick start — Chat (LLM or VLM):**
```bash
curl http://<device-ip>:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"rkllm-model","messages":[{"role":"user","content":"Hello!"}],"max_tokens":256}'
```

## Core Value

- **One platform, three models** — try detection, chat, and vision without setting up three different stacks
- **Local-only by default** — your images and conversations never leave the device
- **Standard APIs** — REST + OpenAI-compatible interfaces, drop-in for existing clients
- **NPU accelerated** — Rockchip NPU runs inference efficiently on low-power hardware

## Integration Scenarios

| Scenario | Which preset | How it fits |
|----------|--------------|-------------|
| Security camera intrusion detection | Object Detection | Call predict API from NVR for person/vehicle alerts |
| Air-gapped chatbot or code assistant | LLM Chat | OpenAI-compatible client points to local endpoint |
| Document screening / image triage | Vision Chat | Send page screenshots, ask questions in natural language |
| Robot perception + dialog | Object Detection + LLM | Pair detection output with LLM reasoning on the same device |

## Technical Specs

| Spec | Value |
|------|-------|
| Object Detection latency | ~30ms/frame (RK3576) · ~20ms (RK3588) |
| LLM token speed | Depends on variant — 1.5B fastest, 7B strongest |
| Memory needed | 4GB for 1.5B LLM · 8GB+ for 7B LLM and Vision Chat |
| Disk needed | 3–10GB per preset, depending on model |
| Supported hardware | reComputer RK3576 (all presets) · reComputer RK3588 / ROCK 5T (Object Detection only) |

## Good to Know

- Each preset deploys independently — you can have all three running on the same RK3576 (they use different ports: 8000 / 8001 / 8002)
- First startup downloads the Docker image (1–4GB) and loads the model — allow a few minutes
- Object Detection works with or without a camera (image upload always works)
- LLM and Vision Chat are RK3576-only because they require RKLLM NPU support not yet available on RK3588
- All conversations and detections stay on-device — nothing is sent to a cloud
