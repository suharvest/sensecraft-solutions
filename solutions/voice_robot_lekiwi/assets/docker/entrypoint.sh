#!/bin/bash
set -e

MODEL_NAME="${WAKEWORD_MODEL:-hey jarvis}"
MODEL_ID="${MODEL_NAME// /_}_v0.1"
MODEL_DIR="/usr/local/lib/python3.11/site-packages/openwakeword/resources/models"
MODEL_FILE="$MODEL_DIR/${MODEL_ID}.tflite"

if [ ! -f "$MODEL_FILE" ]; then
    echo "[entrypoint] Model '$MODEL_NAME' not cached, downloading..."
    python3 -c "
import openwakeword.utils
openwakeword.utils.download_models(model_names=['$MODEL_ID'])
print('[entrypoint] Downloaded $MODEL_ID')
"
fi

exec python3 pipeline.py
