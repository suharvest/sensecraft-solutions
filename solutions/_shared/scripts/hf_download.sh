#!/usr/bin/env bash
# Shared HuggingFace download helper.
#
# This is a library, not an executable. Source it from a deployment script:
#
#     source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../../../_shared/scripts/hf_download.sh"
#     hf_download_file  Tongyi-MAI/Z-Image-Turbo tokenizer/tokenizer.json /tmp/tokenizer.json
#     hf_download_subtree harvestsu/some-repo trt-engines-bf16 /opt/models/engines
#
# Public API:
#   hf_download_file    <repo> <rfilename> <dest_path>
#   hf_download_subtree <repo> <remote_prefix> <local_dir>
#
# Environment variables consumed:
#   HF_ENDPOINT_HOST    Optional. If set (e.g. "hf-mirror.com"), this host is
#                       tried first. If unset, the default order is
#                       huggingface.co -> hf-mirror.com (the historical
#                       primary+fallback behaviour).
#
# This helper deliberately uses host-side curl + python3 (json parsing) so
# images do not need the heavy `huggingface_hub` python package.

# --- source guard ------------------------------------------------------------
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  echo "hf_download.sh must be sourced, not executed directly" >&2
  exit 1
fi

# NOTE(deps): requires bash 4+, curl, and python3 on the host. Solutions
# that invoke this helper from a minimal alpine container (which ships
# /bin/sh only) or via a non-bash shell will fail. The solution-validation
# skill should fail validation if the calling script targets sh/dash.
# Require bash — the helper uses bash arrays (HF_HOST_ORDER=(...)) which
# silently break under sh/zsh/dash.
if [ -z "${BASH_VERSION:-}" ]; then
  echo "ERROR: hf_download.sh requires bash (not sh/zsh/dash)" >&2
  return 1 2>/dev/null || exit 1
fi

# --- host order --------------------------------------------------------------
# Build HF_HOST_ORDER respecting $HF_ENDPOINT_HOST (if set).
_hf_build_host_order() {
  local primary="huggingface.co"
  local mirror="hf-mirror.com"
  HF_HOST_ORDER=()
  if [ -n "${HF_ENDPOINT_HOST:-}" ]; then
    HF_HOST_ORDER+=("${HF_ENDPOINT_HOST}")
    # Append the standard hosts as last-resort fallbacks (skip duplicates).
    for h in "$primary" "$mirror"; do
      if [ "$h" != "${HF_ENDPOINT_HOST}" ]; then
        HF_HOST_ORDER+=("$h")
      fi
    done
  else
    HF_HOST_ORDER=("$primary" "$mirror")
  fi
}
_hf_build_host_order

# --- dependency checks -------------------------------------------------------
if ! command -v curl >/dev/null 2>&1; then
  echo "hf_download.sh: curl is required" >&2
  return 1 2>/dev/null || exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "hf_download.sh: python3 is required" >&2
  return 1 2>/dev/null || exit 1
fi

# --- internals ---------------------------------------------------------------

# Probe hosts in HF_HOST_ORDER; echo the first that answers the API root for
# the given repo. Returns 1 if all hosts fail.
pick_host() {
  local repo="$1"
  local host
  for host in "${HF_HOST_ORDER[@]}"; do
    if curl -fsSL --connect-timeout 8 --max-time 15 \
         -o /dev/null "https://${host}/api/models/${repo}" 2>/dev/null; then
      echo "$host"
      return 0
    fi
  done
  return 1
}

# List files under a repo prefix (recursive). Echoes one rfilename per line.
# Args: host, repo, prefix (may be empty for whole repo)
list_files() {
  local host="$1" repo="$2" prefix="$3"
  local url="https://${host}/api/models/${repo}/tree/main?recursive=true"
  [ -n "$prefix" ] && url="${url}&path=${prefix}"
  # NOTE: HF's tree API IGNORES the `path=` query param — it always returns
  # the full repo file list. Without a client-side filter a prefix request
  # silently pulls the WHOLE repo (and the prefix-strip in hf_download_subtree
  # then mismatches, landing files at wrong paths). So filter by prefix here.
  curl -fsSL --connect-timeout 10 --max-time 60 "$url" \
    | HF_SUBTREE_PREFIX="$prefix" python3 -c '
import sys, json, os
prefix = os.environ.get("HF_SUBTREE_PREFIX", "").strip("/")
data = json.load(sys.stdin)
for item in data:
    if item.get("type") != "file":
        continue
    path = item["path"]
    if prefix and not (path == prefix or path.startswith(prefix + "/")):
        continue
    print(path)
'
}

# --- public API --------------------------------------------------------------

# Download one file with host fallback.
# Args: repo, rfilename, dest_path, [preferred_host]
#
# If <preferred_host> is provided (typically the host already chosen by
# pick_host for the parent subtree), it is tried first regardless of
# HF_HOST_ORDER. The remaining hosts in HF_HOST_ORDER are then tried in
# order, skipping the preferred one to avoid a redundant retry. This
# prevents the per-file loop from re-paying the timeout cost of an
# unreachable head-of-list host on every file in a subtree.
hf_download_file() {
  local repo="$1" rfile="$2" dest="$3" preferred="${4:-}"
  mkdir -p "$(dirname "$dest")"

  local -a host_order=()
  if [ -n "$preferred" ]; then
    host_order+=("$preferred")
  fi
  local h
  for h in "${HF_HOST_ORDER[@]}"; do
    if [ "$h" != "$preferred" ]; then
      host_order+=("$h")
    fi
  done

  local host
  for host in "${host_order[@]}"; do
    local url="https://${host}/${repo}/resolve/main/${rfile}"
    if curl -fL --connect-timeout 15 --retry 2 --retry-delay 3 \
         -C - -o "${dest}.part" "$url"; then
      mv "${dest}.part" "$dest"
      return 0
    fi
    rm -f "${dest}.part"
    echo "  [warn] ${host} failed, trying next..." >&2
  done
  echo "  [error] failed to download ${rfile} from any host" >&2
  return 1
}

# Back-compat alias used by the legacy z_image_turbo script naming.
download_file() { hf_download_file "$@"; }

# Download a whole subtree of a repo.
# Args: repo, remote_prefix, local_dir
hf_download_subtree() {
  local repo="$1" prefix="$2" local_dir="$3"

  echo "==> Resolving file list for ${repo}${prefix:+ /${prefix}}"
  local host
  host="$(pick_host "$repo")" || {
    echo "Cannot reach any HF host (${HF_HOST_ORDER[*]})" >&2
    return 1
  }
  echo "    using host: $host"

  local files
  files="$(list_files "$host" "$repo" "$prefix")" || {
    echo "Failed to list files for ${repo}/${prefix}" >&2
    return 1
  }
  if [ -z "$files" ]; then
    echo "No files found under ${repo}/${prefix}" >&2
    return 1
  fi

  local total
  total="$(printf '%s\n' "$files" | wc -l | tr -d ' ')"
  local count=0
  while IFS= read -r rfile; do
    [ -z "$rfile" ] && continue
    count=$((count + 1))
    # Strip prefix to get relative path inside local_dir
    local rel="$rfile"
    if [ -n "$prefix" ]; then
      rel="${rfile#${prefix}/}"
    fi
    local dest="${local_dir}/${rel}"
    if [ -f "$dest" ]; then
      echo "  [${count}/${total}] skip (exists): ${rel}"
      continue
    fi
    echo "  [${count}/${total}] ${rel}"
    hf_download_file "$repo" "$rfile" "$dest" "$host" || return 1
  done <<EOF
$files
EOF
}

# Back-compat alias.
download_subtree() { hf_download_subtree "$@"; }
