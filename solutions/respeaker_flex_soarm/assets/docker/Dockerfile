# Slim voice-arm image — no CUDA, no l4t-jetpack base.
#
# voice-arm doesn't use GPU directly: audio I/O, serial bus, HTTP client
# to seeed-voice/edge-llm, and openwakeword (CPU onnxruntime by default).
# GPU inference lives in the companion services (seeed-voice + edge-llm).
#
# The application code (the voice-arm app + its actuator/plugin/tool/wake
# modules) now lives INSIDE the seeed-local-voice agent under
# ``agent/ovs_agent/apps/voice_arm`` + ``agent/ovs_agent/{actuators,
# plugins,tools,wake_sources,audio}``. There is no longer any clone of the
# upstream repo at build time — the build context carries the seeed agent
# directly:
#
#   build-context/
#   ├── agent/                 (pip-installable openvoicestream-agent,
#   │                           package ovs_agent, includes apps/voice_arm)
#   └── default_config/        (actions.yaml / prompt.yaml / agent.yaml.tmpl,
#                               from solutions/.../assets/default_config/)
#
# Populate ``agent/`` + ``default_config/`` in this directory from your seeed
# checkout before ``docker build`` (e.g. rsync ~/project/seeed-local-voice/
# agent here). Protocol constants are vendored in ovs_agent/protocol.py, so
# no app/core/v2v slice is needed. The former prepare-build.sh / .ovs-cache
# / ovs_agent_src clone flow is gone.
#
# Build:
#   docker build -t .../voice-arm:slim .
#
# Override pip mirror at build time:
#   docker build --build-arg PIP_INDEX_URL=... .

FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# pip + apt mirrors (CN devices behind the wall) — override at build time.
# deb.debian.org / pypi.org are unreachable from the edge devices; point both
# at Tsinghua. For non-CN builders pass --build-arg APT_MIRROR=deb.debian.org
# --build-arg PIP_INDEX_URL=https://pypi.org/simple.
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn
ARG APT_MIRROR=mirrors.tuna.tsinghua.edu.cn
ENV PIP_INDEX_URL=${PIP_INDEX_URL} \
    PIP_TRUSTED_HOST=${PIP_TRUSTED_HOST}

# ── system deps ──────────────────────────────────────────────────────
# libportaudio2 for sounddevice (replaces pyaudio); alsa-utils for aplay
# fallback path; pulseaudio-utils for `pactl` source-suspend in entrypoint;
# gettext-base for `envsubst` (agent.yaml template rendering); build-essential
# for any wheels that fall back to sdist (openwakeword sometimes).
RUN if [ -n "$APT_MIRROR" ]; then \
        sed -i "s|deb.debian.org|$APT_MIRROR|g; s|security.debian.org|$APT_MIRROR|g" \
            /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources 2>/dev/null || true; \
    fi && \
    apt-get update && apt-get install -y --no-install-recommends \
        libportaudio2 portaudio19-dev alsa-utils pulseaudio-utils \
        gettext-base \
        build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── python deps ─────────────────────────────────────────────────────────
# No torch: server-loop mode runs VAD server-side (client_vad_backend=off),
# so the agent never loads silero-vad / torch / torchaudio. Dropping them
# saves ~570 MB. App deps: openwakeword, sounddevice, pyaudio, numpy,
# pyserial, PyYAML, fastapi/uvicorn, pysbd, websockets, aiohttp, openai, and
# feetech-servo-sdk (the SO-ARM driver uses it directly — see
# ovs_agent/apps/voice_arm/minimal_so_follower.py).
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --no-compile -r requirements.txt \
 && SP=$(python3 -c "import sysconfig;print(sysconfig.get_paths()['purelib'])") \
 && find "$SP" -depth -type d -name __pycache__ -exec rm -rf {} + \
 && find "$SP" -type f -name '*.pyc' -delete

# Layer C — the seeed ovs_agent package (includes ovs_agent/apps/voice_arm +
# the actuator/plugin/tool/wake_source/audio modules). Copied straight from
# the build context — NO clone. Protocol constants are vendored in
# ovs_agent/protocol.py, so the agent is self-contained — no app/core/v2v
# slice is shipped anymore (and this survives the server-side app/→server/
# rename).
COPY agent/ /opt/openvoicestream/agent/
RUN pip install --no-cache-dir --no-compile /opt/openvoicestream/agent \
 && SP=$(python3 -c "import sysconfig;print(sysconfig.get_paths()['purelib'])") \
 && find "$SP" -depth -type d -name __pycache__ -exec rm -rf {} + \
 && find "$SP" -type f -name '*.pyc' -delete

# ── openWakeWord models: NOT baked ───────────────────────────────────────
# The 3 small onnx (wake model + shared melspectrogram/embedding) are fetched
# at first boot from HF via the device's HF_ENDPOINT mirror — see entrypoint.sh
# (CN devices can't reach openWakeWord's GitHub release URLs, but they CAN
# reach the HF mirror). Keeping models out of the image makes a clean rebuild
# self-contained (no COPY --from a prior prod image) and the image smaller.

# ── app glue (entrypoint + default configs) ───────────────────────────
# The application Python now lives inside the installed agent (apps.voice_arm);
# only the deploy glue is copied flat into /app.
COPY entrypoint.sh ./
COPY default_config/ /app/default_config/
RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/opt/openvoicestream \
    VOICE_SERVICE_URL="http://seeed-voice:8000" \
    LLM_SERVICE_URL="http://edge-llm:8000" \
    CONFIG_DIR=/opt/seeed/voice_arm/config \
    WAKEWORD_MODEL="hey jarvis" \
    MIC_INDEX=auto \
    WAKEWORD_CHANNEL=all \
    WAKEWORD_THRESHOLD=0.5 \
    WAKEWORD_VAD_THRESHOLD=0.0 \
    WAKEWORD_COOLDOWN=2 \
    RECORDING_SECONDS=3 \
    SAMPLE_RATE=16000 \
    LLM_MODEL="Qwen/Qwen3-4B-AWQ" \
    LLM_MAX_TOKENS=256 \
    STT_LANGUAGE=auto \
    TTS_SID=52 \
    TTS_SPEED=1.0 \
    TTS_OUTPUT_DEVICE=auto \
    ARM_PORT=auto \
    ARM_ID=voice_arm \
    ARM_MOVE_DELAY=1.5 \
    ARM_GESTURE_DELAY=0.4 \
    SERIAL_BAUD=1000000 \
    OBSERVATION_PORT=8765

EXPOSE 8765

ENTRYPOINT ["/app/entrypoint.sh"]
