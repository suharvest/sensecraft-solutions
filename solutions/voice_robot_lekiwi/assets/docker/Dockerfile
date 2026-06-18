# Stage 1: Build native extensions
FROM python:3.11-slim-bookworm AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev build-essential && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/install -r requirements.txt
COPY download_default_model.py .
RUN PYTHONPATH=/install python3 download_default_model.py

# Stage 2: Runtime — no compiler toolchain
FROM python:3.11-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 alsa-utils && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.11/site-packages/
COPY *.py entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENV GROQ_API_KEY="" \
    WAKEWORD_MODEL="hey jarvis" \
    MIC_INDEX=auto \
    WAKEWORD_CHANNEL=all \
    WAKEWORD_THRESHOLD=0.03 \
    WAKEWORD_VAD_THRESHOLD=0.0 \
    WAKEWORD_COOLDOWN=2 \
    RECORDING_SECONDS=3 \
    SAMPLE_RATE=16000 \
    LLM_MODEL=llama-3.1-8b-instant \
    LLM_MAX_TOKENS=256 \
    STT_MODEL=whisper-large-v3-turbo \
    STT_LANGUAGE=en \
    TTS_MODEL=canopylabs/orpheus-v1-english \
    TTS_VOICE=autumn \
    TTS_OUTPUT_DEVICE=auto \
    SERIAL_PORT=auto \
    SERIAL_BAUD=115200

ENTRYPOINT ["/app/entrypoint.sh"]
