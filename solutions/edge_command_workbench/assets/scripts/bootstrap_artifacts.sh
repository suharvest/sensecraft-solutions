#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?deployment root required}"
MANIFEST="${2:?manifest path required}"
HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"
REPO="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("repository") or d.get("distribution",{}).get("repository") or d.get("source",{}).get("repository",""))' "$MANIFEST")"
REVISION="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("revision") or d.get("distribution",{}).get("revision") or "")' "$MANIFEST")"
PATH_PREFIX="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("path_prefix", ""))' "$MANIFEST")"
mkdir -p "$ROOT/.cache" "$ROOT/tokenizer"

manifest_value() {
  python3 - "$MANIFEST" "$1" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
value = data
for part in sys.argv[2].split('.'):
    if isinstance(value, list) and part.isdigit():
        value = value[int(part)] if int(part) < len(value) else None
    elif isinstance(value, dict):
        value = value.get(part)
    else:
        value = None
    if value is None:
        break
print("" if value is None else value)
PY
}

download_checked() {
  local relative="$1" destination="$2" expected="$3"
  case "$expected" in
    ""|null|__SET_AFTER_BUILD__)
      echo "Missing checksum in artifacts.json for $relative" >&2
      exit 2
      ;;
  esac
  [[ "$expected" =~ ^[0-9a-fA-F]{64}$ ]] || {
    echo "Invalid SHA256 in artifacts.json for $relative" >&2
    exit 2
  }
  if [ -f "$destination" ] && printf '%s  %s\n' "$expected" "$destination" | sha256sum -c - >/dev/null 2>&1; then
    echo "Checksum already matches: $relative"
    return 0
  fi
  local partial="${destination}.part"
  local url="${HF_ENDPOINT%/}/${REPO}/resolve/${REVISION}/${PATH_PREFIX:+$PATH_PREFIX/}${relative}?download=true"
  mkdir -p "$(dirname "$destination")"
  curl -fL --retry 3 --retry-delay 2 -C - -o "$partial" "$url"
  if ! printf '%s  %s\n' "$expected" "$partial" | sha256sum -c -; then
    local bad="${partial}.bad.$(date +%s)"
    mv -f "$partial" "$bad"
    echo "Checksum mismatch; quarantined partial download at $bad" >&2
    exit 1
  fi
  mv -f "$partial" "$destination"
}

IMAGE_ARCHIVE="$(manifest_value image.archive)"
IMAGE_SHA="$(manifest_value image.sha256)"
EXPECTED_CONFIG_SHA="$(manifest_value image.expected_config_sha256)"
MODEL_SHA="$(manifest_value model.sha256)"
if [ -z "$IMAGE_ARCHIVE" ]; then
  # RKLLM manifests keep one or more platform archives under image.archives.
  STATUS="$(manifest_value status)"
  if [ "$STATUS" != "ready" ] && [ "${ALLOW_DRAFT_ARTIFACTS:-0}" != "1" ]; then
    echo "Refusing RKLLM artifact manifest with status '$STATUS'; publish a ready manifest first" >&2
    exit 2
  fi
  IMAGE_ARCHIVE="$(python3 - "$MANIFEST" <<'PY2'
import json,sys
d=json.load(open(sys.argv[1])); print(d["image"]["archives"][0]["archive"])
PY2
)"
  IMAGE_SHA="$(python3 - "$MANIFEST" <<'PY2'
import json,sys
d=json.load(open(sys.argv[1])); print(d["image"]["archives"][0]["sha256"])
PY2
)"
  EXPECTED_CONFIG_SHA="$(python3 - "$MANIFEST" <<'PY2'
import json,sys
d=json.load(open(sys.argv[1])); print(d["image"]["archives"][0]["config_sha256"])
PY2
)"
  TARGET="${MODEL_TARGET:-${TARGET:-rk3588}}"
  PLAN="$ROOT/.cache/rkllm-artifact-plan.tsv"
  python3 - "$MANIFEST" "$TARGET" > "$PLAN" <<'PY2'
import json,sys
d=json.load(open(sys.argv[1])); target=sys.argv[2]
models=[x for x in d.get("models",[]) if x.get("target")==target]
if len(models)!=1: raise SystemExit(f"expected one model for target {target}, found {len(models)}")
m=models[0]
if not m.get("sha256") or not m.get("file"): raise SystemExit("model file/checksum missing")
print(f'{m["file"]}\t{m.get("destination","model.rkllm")}\t{m["sha256"]}')
for x in d.get("shared_artifacts",[]):
    if x.get("target") not in (None,target): continue
    if not x.get("sha256") or not x.get("file"): raise SystemExit(f'checksum/file missing for {x}')
    print(f'{x["file"]}\t{x.get("destination",x["file"])}\t{x["sha256"]}')
PY2
  download_checked "$IMAGE_ARCHIVE" "$ROOT/.cache/$IMAGE_ARCHIVE" "$IMAGE_SHA"
  while IFS=$'\t' read -r relative destination checksum; do
    download_checked "$relative" "$ROOT/$destination" "$checksum"
  done < "$PLAN"
else
  download_checked "$IMAGE_ARCHIVE" "$ROOT/.cache/$IMAGE_ARCHIVE" "$IMAGE_SHA"
  download_checked "model.rknn" "$ROOT/model.rknn" "$MODEL_SHA"
  for index in 0 1; do
    filename="$(manifest_value tokenizer.$index.file)"
    checksum="$(manifest_value tokenizer.$index.sha256)"
    download_checked "$filename" "$ROOT/tokenizer/$filename" "$checksum"
  done
fi

IMAGE_TAG="$(manifest_value image.tag)"
if [ -z "$IMAGE_TAG" ]; then
  IMAGE_TAG="$(manifest_value image.logical_image)"
fi
case "$EXPECTED_CONFIG_SHA" in
  ""|null|__SET_AFTER_BUILD__)
    echo "Missing expected_config_sha256 in artifacts.json for $IMAGE_TAG" >&2
    exit 2
    ;;
esac
if docker image inspect "$IMAGE_TAG" >/dev/null 2>&1; then
  docker save "$IMAGE_TAG" | python3 "$ROOT/verify_image_archive.py" - \
    --tag "$IMAGE_TAG" --config-sha256 "$EXPECTED_CONFIG_SHA"
  echo "Exact image tag and config digest already verified: $IMAGE_TAG; skipping docker load."
else
  python3 "$ROOT/verify_image_archive.py" "$ROOT/.cache/$IMAGE_ARCHIVE" \
    --sha256 "$IMAGE_SHA" --tag "$IMAGE_TAG" --config-sha256 "$EXPECTED_CONFIG_SHA"
  docker load --input "$ROOT/.cache/$IMAGE_ARCHIVE"
  docker image inspect "$IMAGE_TAG" >/dev/null 2>&1 || {
    echo "Loaded archive does not provide expected image tag: $IMAGE_TAG" >&2
    exit 1
  }
  docker save "$IMAGE_TAG" | python3 "$ROOT/verify_image_archive.py" - \
    --tag "$IMAGE_TAG" --config-sha256 "$EXPECTED_CONFIG_SHA"
fi
echo "Pinned artifacts ready under $ROOT"
