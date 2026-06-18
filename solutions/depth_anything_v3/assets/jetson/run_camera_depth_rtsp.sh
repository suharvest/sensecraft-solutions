#!/usr/bin/env bash
set -Eeuo pipefail

# Camera depth + mosaic RTSP launcher
# Optional env vars:
#   WORKSPACE_DIR
#   CAMERA_ID(auto/0/1...), CAMERA_WIDTH, CAMERA_HEIGHT, DOWNSAMPLE_FACTOR
#   MODEL_PATH, PUBLISH_RATE
#   USE_CALIBRATION=1, CAMERA_INFO_FILE=/path/to/camera_info.yaml
#   ENABLE_UNDISTORTION=1, UNDISTORTION_BALANCE=0.0..1.0
#   STREAM_FPS, RTSP_PORT, RTSP_MOUNT, ENCODER, BITRATE_KBPS
#   PANEL_WIDTH, PANEL_HEIGHT, MAX_POINTS, POINT_RADIUS

log() { echo "[run_camera_depth_rtsp] $*"; }
warn() { echo "[run_camera_depth_rtsp][WARN] $*" >&2; }
die() { echo "[run_camera_depth_rtsp][ERROR] $*" >&2; exit 1; }

source_relaxed_nounset() {
    local script_path="$1"
    local had_nounset=0
    case "$-" in
        *u*) had_nounset=1 ;;
    esac

    # Some ROS setup scripts read optional vars directly; make them safe under -u.
    set +u
    : "${AMENT_TRACE_SETUP_FILES:=}"
    : "${COLCON_TRACE:=}"
    # shellcheck disable=SC1090
    source "${script_path}"
    local rc=$?

    if [ "${had_nounset}" -eq 1 ]; then
        set -u
    fi
    return "${rc}"
}

is_uint() { [[ "${1:-}" =~ ^[0-9]+$ ]]; }
is_int() { [[ "${1:-}" =~ ^-?[0-9]+$ ]]; }

probe_camera_id() {
    local id="$1"
    local dev="/dev/video${id}"
    [ -e "${dev}" ] || return 1

    if command -v v4l2-ctl >/dev/null 2>&1; then
        v4l2-ctl -d "${dev}" --list-formats-ext >/dev/null 2>&1 || return 1
        timeout 4 v4l2-ctl -d "${dev}" \
            --stream-mmap=1 \
            --stream-count=1 \
            --stream-to="/tmp/camera_probe_${id}.raw" >/tmp/camera_probe_"${id}".log 2>&1
        return $?
    fi

    if command -v python3 >/dev/null 2>&1; then
        timeout 4 python3 -c "import sys,cv2; i=int(sys.argv[1]); c=cv2.VideoCapture(i); ok=c.isOpened() and c.read()[0]; c.release(); sys.exit(0 if ok else 1)" "${id}"
        return $?
    fi

    # Last-resort fallback: only device existence check.
    return 0
}

detect_camera_id() {
    local dev id
    local ids=()
    local ordered=()

    for dev in /dev/video*; do
        [ -e "${dev}" ] || continue
        id="${dev#/dev/video}"
        is_uint "${id}" || continue
        ids+=("${id}")
    done

    # Jetson setups often expose video0 as a non-capture/metadata node.
    # Prefer non-zero IDs by default, but keep this configurable.
    if [ "${CAMERA_AUTO_PREFER_NONZERO:-1}" = "1" ]; then
        for id in "${ids[@]}"; do
            [ "${id}" != "0" ] && ordered+=("${id}")
        done
        for id in "${ids[@]}"; do
            [ "${id}" = "0" ] && ordered+=("${id}")
        done
    else
        ordered=("${ids[@]}")
    fi

    for id in "${ordered[@]}"; do
        if probe_camera_id "${id}"; then
            echo "${id}"
            return 0
        fi
    done

    return 1
}

pick_encoder() {
    local requested="$1"
    local selected="${requested}"

    if ! command -v gst-inspect-1.0 >/dev/null 2>&1; then
        warn "gst-inspect-1.0 not found, cannot validate encoder. Using '${selected}'."
        echo "${selected}"
        return 0
    fi

    if gst-inspect-1.0 "${requested}" >/dev/null 2>&1; then
        echo "${requested}"
        return 0
    fi

    if gst-inspect-1.0 x264enc >/dev/null 2>&1; then
        warn "Encoder '${requested}' unavailable, fallback to x264enc."
        echo "x264enc"
        return 0
    fi

    if gst-inspect-1.0 nvv4l2h264enc >/dev/null 2>&1; then
        warn "Encoder '${requested}' unavailable, fallback to nvv4l2h264enc."
        echo "nvv4l2h264enc"
        return 0
    fi

    die "No usable H.264 encoder found (requested='${requested}')."
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${WORKSPACE_DIR:-${SCRIPT_DIR}}"
if [ ! -f "${WORKSPACE_DIR}/install/setup.bash" ] && [ -f "/workspace/ros2-depth-anything-v3-trt/install/setup.bash" ]; then
    WORKSPACE_DIR="/workspace/ros2-depth-anything-v3-trt"
fi
[ -f "${WORKSPACE_DIR}/install/setup.bash" ] || die "Built workspace not found at '${WORKSPACE_DIR}'."
cd "${WORKSPACE_DIR}"

if [ -z "${ROS_DISTRO:-}" ] && [ -f "/opt/ros/humble/setup.bash" ]; then
    source_relaxed_nounset /opt/ros/humble/setup.bash || die "Failed to source /opt/ros/humble/setup.bash"
fi
[ -n "${ROS_DISTRO:-}" ] || die "ROS 2 environment not found. Expected /opt/ros/humble/setup.bash."

source_relaxed_nounset install/setup.bash || die "Failed to source install/setup.bash"

CAMERA_ID="${CAMERA_ID:-auto}"
CAMERA_WIDTH="${CAMERA_WIDTH:-640}"
CAMERA_HEIGHT="${CAMERA_HEIGHT:-480}"
DOWNSAMPLE_FACTOR="${DOWNSAMPLE_FACTOR:-1}"
MODEL_PATH="${MODEL_PATH:-onnx/DA3METRIC-LARGE.onnx}"
PUBLISH_RATE="${PUBLISH_RATE:-10.0}"

STREAM_FPS="${STREAM_FPS:-6}"
RTSP_PORT="${RTSP_PORT:-8554}"
RTSP_MOUNT="${RTSP_MOUNT:-/depth}"
ENCODER="$(pick_encoder "${ENCODER:-x264enc}")"
BITRATE_KBPS="${BITRATE_KBPS:-1500}"
PANEL_WIDTH="${PANEL_WIDTH:-480}"
PANEL_HEIGHT="${PANEL_HEIGHT:-360}"
MAX_POINTS="${MAX_POINTS:-8000}"
POINT_RADIUS="${POINT_RADIUS:-1}"

is_uint "${RTSP_PORT}" || die "RTSP_PORT must be a positive integer: '${RTSP_PORT}'"
if [[ "${RTSP_MOUNT}" != /* ]]; then
    RTSP_MOUNT="/${RTSP_MOUNT}"
fi

echo "=========================================="
echo "Camera + Depth + PointCloud RTSP Stream"
echo "=========================================="
echo
echo "Available video devices:"
ls -1 /dev/video* 2>/dev/null || true

case "${CAMERA_ID}" in
    auto|AUTO|"")
        if CAMERA_ID="$(detect_camera_id)"; then
            log "Auto-detected CAMERA_ID=${CAMERA_ID} (/dev/video${CAMERA_ID})"
        else
            die "No usable /dev/video* capture device detected."
        fi
        ;;
    *)
        is_uint "${CAMERA_ID}" || die "CAMERA_ID must be numeric or auto: '${CAMERA_ID}'"
        [ -e "/dev/video${CAMERA_ID}" ] || die "Camera device /dev/video${CAMERA_ID} does not exist."
        if ! probe_camera_id "${CAMERA_ID}"; then
            warn "/dev/video${CAMERA_ID} exists but one-frame probe failed."
            warn "Try another CAMERA_ID (for example 1)."
            [ -f "/tmp/camera_probe_${CAMERA_ID}.log" ] && tail -n 30 "/tmp/camera_probe_${CAMERA_ID}.log" || true
            exit 1
        fi
        ;;
esac

# x264 path should run headless and avoid EGL/X11 dependency.
if [ "${ENCODER}" = "x264enc" ]; then
    unset DISPLAY XAUTHORITY GST_GL_WINDOW GST_GL_PLATFORM
    export QT_QPA_PLATFORM=offscreen
    log "Headless x264 mode: DISPLAY/XAUTHORITY/GST_GL_* unset."
else
    export DISPLAY="${DISPLAY:-:0}"
    export XAUTHORITY="${XAUTHORITY:-/root/.Xauthority}"
    export GST_GL_WINDOW="${GST_GL_WINDOW:-dummy}"
    export GST_GL_PLATFORM="${GST_GL_PLATFORM:-egl}"
    log "NVIDIA encoder mode: DISPLAY=${DISPLAY} XAUTHORITY=${XAUTHORITY}"
fi

if command -v ss >/dev/null 2>&1; then
    RTSP_LISTENERS="$(ss -ltnp "( sport = :${RTSP_PORT} )" 2>/dev/null || true)"
    if echo "${RTSP_LISTENERS}" | grep -q "launch_vst"; then
        die "RTSP port ${RTSP_PORT} is occupied by process 'launch_vst'."
    fi
fi

LAUNCH_ARGS=(
    camera_type:=standard
    "camera_id:=${CAMERA_ID}"
    "camera_width:=${CAMERA_WIDTH}"
    "camera_height:=${CAMERA_HEIGHT}"
    "model_path:=${MODEL_PATH}"
    "publish_rate:=${PUBLISH_RATE}"
    "downsample_factor:=${DOWNSAMPLE_FACTOR}"
    "stream_fps:=${STREAM_FPS}"
    "rtsp_port:=${RTSP_PORT}"
    "rtsp_mount:=${RTSP_MOUNT}"
    "encoder:=${ENCODER}"
    "bitrate_kbps:=${BITRATE_KBPS}"
    "panel_width:=${PANEL_WIDTH}"
    "panel_height:=${PANEL_HEIGHT}"
    "max_points:=${MAX_POINTS}"
    "point_radius:=${POINT_RADIUS}"
)

if [ -n "${CAMERA_INFO_FILE:-}" ] && [ -f "${CAMERA_INFO_FILE}" ]; then
    LAUNCH_ARGS+=("camera_info_file:=${CAMERA_INFO_FILE}")
elif [ "${USE_CALIBRATION:-0}" = "1" ]; then
    LAUNCH_ARGS+=(
        use_calibration:=true
        fx:=824.147361
        fy:=823.660879
        cx:=958.275200
        cy:=767.389372
        k1:=1.486308
        k2:=-13.386609
        p1:=21.409334
        p2:=3.817858
        k3:=0.0
    )
else
    LAUNCH_ARGS+=(use_calibration:=false)
fi

if [ "${ENABLE_UNDISTORTION:-0}" = "1" ]; then
    BALANCE="${UNDISTORTION_BALANCE:-0.0}"
    LAUNCH_ARGS+=(enable_undistortion:=true "undistortion_balance:=${BALANCE}")
else
    LAUNCH_ARGS+=(enable_undistortion:=false)
fi

echo "Configuration:"
echo "  - Camera: /dev/video${CAMERA_ID}"
echo "  - Resolution: ${CAMERA_WIDTH}x${CAMERA_HEIGHT}"
echo "  - Downsample factor: ${DOWNSAMPLE_FACTOR}"
echo "  - Publish rate: ${PUBLISH_RATE} Hz"
echo "  - Stream FPS: ${STREAM_FPS}"
echo "  - RTSP: rtsp://127.0.0.1:${RTSP_PORT}${RTSP_MOUNT}"
echo "  - LAN : rtsp://<jetson-ip>:${RTSP_PORT}${RTSP_MOUNT}"
echo "  - Encoder: ${ENCODER} (${BITRATE_KBPS} kbps)"
echo "  - Mosaic panel: ${PANEL_WIDTH}x${PANEL_HEIGHT} (-1 means auto)"
echo "  - Point cloud: max_points=${MAX_POINTS}, point_radius=${POINT_RADIUS}"
echo
echo "Starting camera depth + RTSP stream..."
echo

exec ros2 launch depth_anything_v3 camera_depth_rtsp.launch.py "${LAUNCH_ARGS[@]}"
