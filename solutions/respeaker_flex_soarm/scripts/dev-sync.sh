#!/bin/bash
# Dev-time hot-sync helper. Pushes a list of files to seeed-orin-nx's
# bind-mount path under voice-arm-v2-build/, sudo-copies them into the
# read-only-owned destination, and restarts the voice-arm container.
#
# After this lands the new code is live in the container without a
# rebuild — Python re-imports from the bind-mount on restart.
#
# Usage: ./dev-sync.sh [file1] [file2] ...
#   With no args: sync everything (voice_arm/ + agent core .py + dashboard)
set -euo pipefail

HOST="${HOST:-100.111.134.124}"
DEVICE="${DEVICE:-seeed-orin-nx}"
FLEET="uv run --project ${HOME}/project/_hub python ${HOME}/project/_hub/fleet.py"
SOLUTIONS_ROOT="${HOME}/project/app_collaboration/solutions/respeaker_flex_soarm/assets/docker"
OVS_ROOT="${HOME}/project/seeed-local-voice/agent/openvoicestream_agent"
DEVICE_BUILD="/home/seeed/voice-arm-v2-build/assets/docker"

# Map: <source-path-on-mac>:<destination-path-on-device>
declare -a TARGETS

add_target() {
    TARGETS+=("$1:$2")
}

if [ $# -eq 0 ]; then
    # Default set: everything actively edited
    add_target "${SOLUTIONS_ROOT}/voice_arm/app.py"                                "${DEVICE_BUILD}/voice_arm/app.py"
    add_target "${SOLUTIONS_ROOT}/voice_arm/arm_plugin.py"                        "${DEVICE_BUILD}/voice_arm/arm_plugin.py"
    add_target "${SOLUTIONS_ROOT}/voice_arm/arm_tools.py"                         "${DEVICE_BUILD}/voice_arm/arm_tools.py"
    add_target "${SOLUTIONS_ROOT}/voice_arm/tapped_audio_io.py"                   "${DEVICE_BUILD}/voice_arm/tapped_audio_io.py"
    add_target "${SOLUTIONS_ROOT}/voice_arm/openwakeword_source.py"               "${DEVICE_BUILD}/voice_arm/openwakeword_source.py"
    add_target "${OVS_ROOT}/app_base.py"                                          "${DEVICE_BUILD}/ovs_agent_src/agent/openvoicestream_agent/app_base.py"
    add_target "${OVS_ROOT}/slv_client.py"                                        "${DEVICE_BUILD}/ovs_agent_src/agent/openvoicestream_agent/slv_client.py"
    add_target "${OVS_ROOT}/app_mode.py"                                          "${DEVICE_BUILD}/ovs_agent_src/agent/openvoicestream_agent/app_mode.py"
    add_target "${OVS_ROOT}/plugins/debug_dashboard.py"                           "${DEVICE_BUILD}/ovs_agent_src/agent/openvoicestream_agent/plugins/debug_dashboard.py"
else
    # Caller passes one or more macOS source paths; we infer device path.
    for src in "$@"; do
        case "$src" in
            "${SOLUTIONS_ROOT}/"*)
                rel="${src#${SOLUTIONS_ROOT}/}"
                add_target "$src" "${DEVICE_BUILD}/${rel}"
                ;;
            "${OVS_ROOT}/"*)
                rel="${src#${OVS_ROOT}/}"
                add_target "$src" "${DEVICE_BUILD}/ovs_agent_src/agent/openvoicestream_agent/${rel}"
                ;;
            *)
                echo "ERROR: cannot infer device path for $src" >&2
                exit 1
                ;;
        esac
    done
fi

# Push each file to /tmp on device, then sudo-cp into bind source.
declare -a TMP_FILES
declare -a DEST_FILES
i=0
for entry in "${TARGETS[@]}"; do
    src="${entry%%:*}"
    dst="${entry#*:}"
    if [ ! -f "$src" ]; then
        echo "skip (missing): $src" >&2
        continue
    fi
    tmp="/tmp/_devsync_${i}_$(basename "$src")"
    $FLEET push --host "$HOST" "$DEVICE" "$src" "$tmp" >/dev/null 2>&1
    TMP_FILES+=("$tmp")
    DEST_FILES+=("$dst")
    echo "→ $src"
    echo "    -> $dst"
    i=$((i+1))
done

# Sudo-cp all in one shot, then restart.
script="set -e"
for k in "${!TMP_FILES[@]}"; do
    script+=$'\n'"sudo install -m 0644 -o root -g root '${TMP_FILES[$k]}' '${DEST_FILES[$k]}'"
done
script+=$'\n'"sudo docker restart voice-arm"
$FLEET exec --host "$HOST" --sudo --literal --timeout 60 "$DEVICE" -- bash -c "$script" | tail -3

echo
echo "Wait ~20s for boot, then check: docker logs voice-arm --since 30s"
