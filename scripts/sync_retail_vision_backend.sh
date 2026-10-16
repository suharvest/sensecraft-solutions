#!/usr/bin/env bash
# Sync the mirrored analytics-backend config from the upstream open-source
# project. Run with no argument to check the mirror matches the pinned ref;
# pass a tag to re-pin and copy.
#
#   scripts/sync_retail_vision_backend.sh                 # check only
#   scripts/sync_retail_vision_backend.sh backend-v0.2.0  # re-pin and copy
#
# Exits non-zero when the mirror has drifted, so CI can gate on it.
set -euo pipefail

MIRROR="solutions/recamera_heatmap_grafana/docker"
PIN="$MIRROR/UPSTREAM"
DIRS=(grafana mosquitto telegraf heatmap-demo go2rtc)

repo=$(sed -n 's/^repo=//p' "$PIN")
ref=$(sed -n 's/^ref=//p' "$PIN")
path=$(sed -n 's/^path=//p' "$PIN")
want_ref="${1:-$ref}"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

if [ -n "${RETAIL_VISION_SRC:-}" ]; then
  # Escape hatch for anyone who cannot reach codeload.github.com — common on
  # networks where this solution is actually deployed. Point it at a local
  # checkout instead. The check then compares against whatever that checkout
  # is on, so verify it is at the pinned ref before trusting a pass.
  echo "using local checkout $RETAIL_VISION_SRC (pinned ref is $ref)"
  src="$RETAIL_VISION_SRC/$path"
else
  # A tarball rather than a clone: no git history to fetch, and it works from a
  # runner with no credentials because the repository is public.
  url="$repo/archive/refs/tags/$want_ref.tar.gz"
  echo "fetching $url"
  curl -fsSL "$url" | tar xz -C "$tmp" --strip-components=1
  src="$tmp/$path"
fi
[ -d "$src" ] || { echo "upstream has no $path/ at $want_ref" >&2; exit 1; }

if [ $# -eq 0 ]; then
  rc=0
  for d in "${DIRS[@]}"; do
    if ! diff -ru "$src/$d" "$MIRROR/$d" >/dev/null 2>&1; then
      echo "DRIFT in $d — upstream $repo@$ref and the mirror differ:" >&2
      diff -ru "$src/$d" "$MIRROR/$d" | head -40 >&2
      rc=1
    fi
  done
  [ $rc -eq 0 ] && echo "mirror matches $repo@$ref"
  exit $rc
fi

for d in "${DIRS[@]}"; do
  rm -rf "${MIRROR:?}/$d"
  cp -R "$src/$d" "$MIRROR/$d"
  echo "synced $d"
done
sed -i.bak "s|^ref=.*|ref=$want_ref|" "$PIN" && rm -f "$PIN.bak"
echo "re-pinned to $want_ref — review the diff before committing"
