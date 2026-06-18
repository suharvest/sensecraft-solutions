## What This Solution Does

Deploy GPT OSS 20B to an NVIDIA Jetson device with one click. The container starts `llama-server` and exposes an OpenAI-compatible HTTP API on port 8080.

## Core Value

| Benefit | Details |
|---------|---------|
| Local inference | Run a 20B LLM entirely on edge hardware, no cloud dependency |
| OpenAI-compatible API | Use existing SDKs and tools without modification |
| One-click deploy | SSH-based remote deployment, no manual Docker commands |

## Use Cases

| Scenario | How to Use |
|----------|------------|
| Chat bot backend | Connect as the AI engine for local chat applications |
| Voice assistant | Pair with a speech recognition frontend for offline voice AI |
| Multi-platform gateway | Use with OpenClaw to serve WeChat, Telegram, and other platforms |

## Usage Notes

**Hardware Requirements**:
- Jetson Orin NX 16GB or higher (20B model requires ~12-15GB VRAM)
- reComputer J4012 is verified; other Jetson Orin models should confirm sufficient VRAM

**API Endpoint**:
- URL: `http://<jetson-ip>:8080/v1/chat/completions`
- OpenAI-compatible format — works with existing SDKs
- Python example: `import openai; openai.api_base = "http://<jetson-ip>:8080/v1"`

**First Request Latency**:
- Initial request may take 2-5 minutes (model warm-up)
- Check readiness at `http://<jetson-ip>:8080/v1/models`
- After warm-up, subsequent requests typically respond in 1-3 seconds

**Token & Context**:
- Default context window ~2048 tokens; adjustable during deployment
- Larger context (`Llama Context` parameter) uses more VRAM
- Keep single requests under 1000 tokens to avoid VRAM overflow
