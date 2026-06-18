#!/bin/bash
# entrypoint.sh — Probe hardware, seed default config, render the
# ovs-agent yaml, then exec into the agent.
#
# Forked from voice-arm v1; v2 replaces the hand-written pipeline with
# openvoicestream_agent (ovs-agent). The script's job is now:
#   1. seed user-editable configs (actions / prompt / agent.yaml.tmpl)
#   2. resolve the SO-ARM /dev/ttyACM* port
#   3. ensure the openwakeword model is cached locally
#   4. probe PulseAudio + free the reSpeaker mic for ALSA exclusive
#   5. resolve MIC_INDEX via audio_devices.resolve_input_index() so the
#      ovs-agent config gets a concrete PortAudio device index
#   6. render agent.yaml from the template + current env
#   7. exec `ovs-agent run voice_arm --config /opt/.../agent.yaml`
set -e

CONFIG_DIR="${CONFIG_DIR:-/opt/seeed/voice_arm/config}"
DEFAULTS_DIR="/app/default_config"

mkdir -p "$CONFIG_DIR"

# ── seed user-editable configs if missing ─────────────────────────────
for f in actions.yaml prompt.yaml agent.yaml.tmpl audio_profiles.yaml; do
    if [ ! -f "$CONFIG_DIR/$f" ] && [ -f "$DEFAULTS_DIR/$f" ]; then
        cp "$DEFAULTS_DIR/$f" "$CONFIG_DIR/$f"
        echo "[entrypoint] Seeded $CONFIG_DIR/$f"
    fi
done

# ── probe SO-ARM serial port ─────────────────────────────────────────
ARM_PORT="${ARM_PORT:-auto}"
if [ "$ARM_PORT" = "auto" ]; then
    for candidate in /dev/ttyACM0 /dev/ttyACM1 /dev/ttyACM2; do
        if [ -e "$candidate" ]; then
            ARM_PORT="$candidate"
            break
        fi
    done
    if [ "$ARM_PORT" = "auto" ]; then
        echo "[entrypoint] WARN: no /dev/ttyACM* found, falling back to /dev/ttyACM0"
        ARM_PORT="/dev/ttyACM0"
    fi
fi
export ARM_PORT
echo "[entrypoint] ARM_PORT=$ARM_PORT"

# ── ensure openWakeWord onnx models are present (fetch from HF, NOT baked) ──
# openWakeWord's own download_models() pulls from GitHub, which the CN edge
# devices can't reach — that's why the models used to be baked into the image
# (COPY --from a prod image). The models are no longer baked (keeps the image
# slim + portable: a clean rebuild no longer depends on a prior prod image).
# Fetch the 3 small onnx the agent loads (inference_framework="onnx"): the
# wake model + the shared melspectrogram/embedding feature models — from HF
# via the device's HF_ENDPOINT mirror (hf-mirror.com on CN, injected at deploy
# by mirror_resolver). Public repo → no token. Persists across restarts; only
# re-fetched on a fresh container (3 files, a few MB, LAN-fast over the mirror).
MODEL_NAME="${WAKEWORD_MODEL:-hey jarvis}"
MODEL_ID="${MODEL_NAME// /_}_v0.1"
MODEL_DIR="/usr/local/lib/python3.11/site-packages/openwakeword/resources/models"
HF_BASE="${HF_ENDPOINT:-https://hf-mirror.com}"
OWW_HF_REPO="${OWW_HF_REPO:-harvestsu/openwakeword-onnx}"
mkdir -p "$MODEL_DIR"
for f in melspectrogram.onnx embedding_model.onnx "${MODEL_ID}.onnx"; do
    if [ ! -f "$MODEL_DIR/$f" ]; then
        url="${HF_BASE%/}/${OWW_HF_REPO}/resolve/main/$f"
        echo "[entrypoint] fetching openWakeWord model $f from $url"
        if ! curl -fsSL --retry 5 --retry-delay 2 -o "$MODEL_DIR/$f" "$url"; then
            echo "[entrypoint] FATAL: could not fetch openWakeWord model $f from $url" >&2
            exit 1
        fi
    fi
done
echo "[entrypoint] openWakeWord onnx models ready in $MODEL_DIR"

# ── auto-detect TTS playback path (PulseAudio vs direct ALSA) ─────────
SOCKET="${PULSE_SERVER#unix:}"
PULSE_COOKIE="${PULSE_COOKIE:-/tmp/pulse-cookie}"

if [ -f /host-pulse-config/cookie ]; then
    cp /host-pulse-config/cookie "$PULSE_COOKIE" 2>/dev/null || true
    chmod 0600 "$PULSE_COOKIE" 2>/dev/null || true
fi
export PULSE_COOKIE

if [ -n "$SOCKET" ] && [ -S "$SOCKET" ] && timeout 2 pactl info >/dev/null 2>&1; then
    export TTS_PLAY_CMD=paplay
    echo "[entrypoint] PulseAudio detected at $SOCKET"

    # Free the reSpeaker for exclusive ALSA capture (PortAudio path).
    pactl list short sources 2>/dev/null \
      | awk '$2 ~ /(respeaker|xvf|C16K6Ch)/ {print $2}' \
      | while read -r src; do
            pactl suspend-source "$src" 1 >/dev/null 2>&1 \
              && echo "[entrypoint] Suspended pulse source $src"
        done
else
    export TTS_PLAY_CMD=aplay
    unset PULSE_SERVER
    unset PULSE_COOKIE
    echo "[entrypoint] No PulseAudio (or auth failed)"
fi

# ── resolve MIC_INDEX into an index OR a sounddevice name substring ──
# resolve_input_index handles MIC_INDEX=auto by reading /proc/asound/cards
# (ALSA-native, immune to PortAudio enumeration gaps) and returning the
# reSpeaker's stable name token (e.g. "XVF3800"); sounddevice matches it by
# name at open time, so card-index drift no longer matters. A numeric
# MIC_INDEX is passed through unchanged. On failure we emit "" (system
# default) — NEVER 0, which on Jetson is the HDMI node (PortAudio -9998).
MIC_INDEX_RESOLVED=$(python3 -c "
import sys
from ovs_agent.audio.devices import resolve_input_index
try:
    print(resolve_input_index('${MIC_INDEX:-auto}'))
except Exception as e:
    print(f'[entrypoint] mic resolution failed: {e}', file=sys.stderr)
    print('')
")
export MIC_INDEX="$MIC_INDEX_RESOLVED"
echo "[entrypoint] MIC_INDEX=$MIC_INDEX"

# ── resolve SPEAKER_DEVICE the same way as the mic ───────────────────
# PortAudio indices are NOT stable across restarts on Jetson, so a static
# SPEAKER_DEVICE=<int> silently lands on a 0-output APE node and TTS plays
# into the void. resolve_output_index scans for the reSpeaker output by
# name; -1 means "let sounddevice use its default".
SPEAKER_DEVICE_RESOLVED=$(python3 -c "
import sys
from ovs_agent.audio.devices import resolve_output_index
try:
    print(resolve_output_index('${SPEAKER_DEVICE:-auto}'))
except Exception as e:
    print('', file=sys.stderr)
    print(f'[entrypoint] speaker resolution failed: {e}', file=sys.stderr)
    print(-1)
")
if [ "$SPEAKER_DEVICE_RESOLVED" = "-1" ]; then
    # Empty → sounddevice picks its own default output.
    export SPEAKER_DEVICE=""
else
    export SPEAKER_DEVICE="$SPEAKER_DEVICE_RESOLVED"
fi
echo "[entrypoint] SPEAKER_DEVICE=$SPEAKER_DEVICE"

# ── decompose service URLs into host+port for envsubst ───────────────
# VOICE_SERVICE_URL=http://seeed-voice:8000 → host=seeed-voice port=8000
parse_url() {
    python3 -c "
from urllib.parse import urlparse
u = urlparse('$1')
print(f'{u.hostname or \"localhost\"} {u.port or $2}')
"
}
read VOICE_SERVICE_HOST VOICE_SERVICE_PORT < <(parse_url "${VOICE_SERVICE_URL:-http://seeed-voice:8000}" 8000)
read LLM_SERVICE_HOST LLM_SERVICE_PORT < <(parse_url "${LLM_SERVICE_URL:-http://edge-llm:8000}" 8000)
export VOICE_SERVICE_HOST VOICE_SERVICE_PORT LLM_SERVICE_HOST LLM_SERVICE_PORT

# Provide defaults for any vars the template references but compose may not export.
export WAKEWORD_MODEL="${WAKEWORD_MODEL:-hey jarvis}"
export WAKEWORD_THRESHOLD="${WAKEWORD_THRESHOLD:-0.5}"
export WAKEWORD_COOLDOWN="${WAKEWORD_COOLDOWN:-2}"
export WAKEWORD_VAD_THRESHOLD="${WAKEWORD_VAD_THRESHOLD:-0.0}"
export STT_LANGUAGE="${STT_LANGUAGE:-auto}"
export TTS_SID="${TTS_SID:-52}"
export TTS_SPEED="${TTS_SPEED:-1.0}"
export LLM_MODEL="${LLM_MODEL:-Qwen/Qwen3-4B-AWQ}"
export ARM_ID="${ARM_ID:-voice_arm}"
export ARM_MOVE_DELAY="${ARM_MOVE_DELAY:-1.5}"
export ARM_GESTURE_DELAY="${ARM_GESTURE_DELAY:-0.4}"
export OBSERVATION_PORT="${OBSERVATION_PORT:-8765}"
export ARM_CLEAR_HISTORY_ON_TOOL_CHANGE="${ARM_CLEAR_HISTORY_ON_TOOL_CHANGE:-false}"
# Single-turn mode (default ON). Multi-turn history hurts Qwen3-4B-AWQ's
# tool-calling reliability — see solution KNOWN_ISSUES.md ISSUE-001.
export ARM_CLEAR_HISTORY_ON_TURN_END="${ARM_CLEAR_HISTORY_ON_TURN_END:-true}"

# ── render agent.yaml from template ──────────────────────────────────
# Always re-render — user edits should be made to agent.yaml.tmpl in the
# bind-mounted config dir, not the rendered file (which we overwrite).
TEMPLATE="$CONFIG_DIR/agent.yaml.tmpl"
RENDERED="$CONFIG_DIR/agent.yaml"
if [ ! -f "$TEMPLATE" ]; then
    TEMPLATE="$DEFAULTS_DIR/agent.yaml.tmpl"
fi
envsubst < "$TEMPLATE" > "$RENDERED"
echo "[entrypoint] Rendered $RENDERED from $TEMPLATE"

# ── PYTHONPATH must include both /app (our modules) and the ovs-agent
# tree root, so `from apps.multi_mode.app import MultiModeApp` resolves.
export PYTHONPATH="/app:/opt/openvoicestream/agent:${PYTHONPATH}"

exec ovs-agent run voice_arm --config "$RENDERED"
