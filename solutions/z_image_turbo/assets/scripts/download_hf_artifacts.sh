#!/usr/bin/env bash
# Download Z-Image-Turbo weights + TRT engines from HuggingFace.
# Falls back to hf-mirror.com when huggingface.co is unreachable.
#
# Usage: download_hf_artifacts.sh <MODEL_ROOT> <RESOLUTION>
#   MODEL_ROOT  - target directory (e.g. /home/nvidia/models)
#   RESOLUTION  - "384" or "512"
#
# Layout produced:
#   $MODEL_ROOT/z-image-turbo-fp8-diffusers/
#       tokenizer/{tokenizer.json,tokenizer_config.json}
#       scheduler/scheduler_config.json
#       vae/config.json
#     (only the small config files needed by pipeline_trt_no_torch.py — the
#      multi-GB safetensors weights are NOT downloaded; weights are baked into
#      the TRT engines)
#   $MODEL_ROOT/axera-onnx/trt-text-encoder-split-g4/
#   $MODEL_ROOT/axera-onnx/trt-engines-bf16/        (only when RESOLUTION=512)
#   $MODEL_ROOT/axera-onnx/trt-engines-384-bf16/    (only when RESOLUTION=384)

set -e

MODEL_ROOT="${1:?MODEL_ROOT required}"
RESOLUTION="${2:?RESOLUTION required}"

WEIGHTS_REPO="Tongyi-MAI/Z-Image-Turbo"
ENGINES_REPO="harvestsu/z-image-turbo-jetson-trt-artifacts"

# Source the shared HF download helper. It defines hf_download_file /
# hf_download_subtree and respects $HF_ENDPOINT_HOST for mirror selection.
#
# Layout differs between local solution dir (nested under _shared/) and
# remote deploy dir (flat, helper SCP'd alongside this script). Honor
# HF_DOWNLOAD_HELPER env var so the remote deployer can point at the
# flat location explicitly.
# shellcheck source=../../../_shared/scripts/hf_download.sh
HF_DOWNLOAD_HELPER="${HF_DOWNLOAD_HELPER:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../../_shared/scripts/hf_download.sh}"
source "$HF_DOWNLOAD_HELPER"

# Pick engine subdir from resolution.
# ENGINE_SUBDIR    = LOCAL dir name (what the compose mounts at /engines).
# ENGINE_REPO_PREFIX = the artifact repo's ACTUAL path for these engines.
# These differ: the repo stores everything under engines/orin-nx-jp6-trt10.3/.
REPO_BASE="engines/orin-nx-jp6-trt10.3"
if [ "$RESOLUTION" = "384" ]; then
  ENGINE_SUBDIR="trt-engines-384-bf16"
  ENGINE_REPO_PREFIX="$REPO_BASE/384-bf16"
else
  ENGINE_SUBDIR="trt-engines-bf16"
  ENGINE_REPO_PREFIX="$REPO_BASE/512-bf16"
fi
TEXT_ENCODER_REPO_PREFIX="$REPO_BASE/text-encoder-split-g4"

# --------- main ---------
mkdir -p "$MODEL_ROOT"

WEIGHTS_DIR="$MODEL_ROOT/z-image-turbo-fp8-diffusers"
TEXT_ENCODER_DIR="$MODEL_ROOT/axera-onnx/trt-text-encoder-split-g4"
ENGINE_DIR="$MODEL_ROOT/axera-onnx/$ENGINE_SUBDIR"

# 1) Tokenizer + scheduler + vae configs — small files only.
#    The container runs no_torch pipeline; safetensors weights are baked into
#    the TRT engines and not needed.
WEIGHTS_FILES=(
  "tokenizer/tokenizer.json"
  "tokenizer/tokenizer_config.json"
  "scheduler/scheduler_config.json"
  "vae/config.json"
)
echo "==> Ensuring base configs in $WEIGHTS_DIR"
for rfile in "${WEIGHTS_FILES[@]}"; do
  dest="$WEIGHTS_DIR/$rfile"
  if [ -f "$dest" ]; then
    echo "  skip (exists): $rfile"
    continue
  fi
  echo "  fetch: $rfile"
  hf_download_file "$WEIGHTS_REPO" "$rfile" "$dest" || exit 1
done

# 2) Text encoder engine — shared across resolutions
if [ -d "$TEXT_ENCODER_DIR" ] && [ -n "$(ls -A "$TEXT_ENCODER_DIR" 2>/dev/null)" ]; then
  echo "==> Text encoder present: $TEXT_ENCODER_DIR (skip)"
else
  echo "==> Downloading text encoder to $TEXT_ENCODER_DIR"
  hf_download_subtree "$ENGINES_REPO" "$TEXT_ENCODER_REPO_PREFIX" "$TEXT_ENCODER_DIR"
fi

# 3) Resolution-specific UNet/VAE engine
if [ -d "$ENGINE_DIR" ] && [ -n "$(ls -A "$ENGINE_DIR" 2>/dev/null)" ]; then
  echo "==> Engine for ${RESOLUTION} present: $ENGINE_DIR (skip)"
else
  echo "==> Downloading ${RESOLUTION} engine to $ENGINE_DIR"
  hf_download_subtree "$ENGINES_REPO" "$ENGINE_REPO_PREFIX" "$ENGINE_DIR"
fi

echo "==> All artifacts ready."
