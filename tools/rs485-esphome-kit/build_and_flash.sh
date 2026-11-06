#!/usr/bin/env bash
# tools/rs485-esphome-kit/build_and_flash.sh
# Build ESPHome firmware, extract binary, auto-detect target serial port, and flash to device.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE=""
PORT=""
BAUD=460800
OUTPUT_DIR="${SCRIPT_DIR}/dist_bin"
BUILD_ONLY=false
FLASH_ONLY_BIN=""
DOCKER_IMAGE="esphome/esphome:latest"

log_info() {
    echo -e "\033[1;32m[INFO]\033[0m $*"
}

log_warn() {
    echo -e "\033[1;33m[WARN]\033[0m $*"
}

log_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $*"
}

auto_detect_port() {
    log_info "Probing connected USB serial devices..."
    local candidates=()
    shopt -s nullglob
    for p in /dev/ttyACM* /dev/ttyUSB* /dev/cu.usbmodem* /dev/cu.usbserial*; do
        if [ -e "$p" ]; then
            candidates+=("$p")
        fi
    done
    shopt -u nullglob

    if [ ${#candidates[@]} -eq 0 ]; then
        log_error "No USB serial port detected. Please connect your Seeed Studio XIAO board."
        return 1
    fi

    # Pick the first available port (or latest connected)
    PORT="${candidates[0]}"
    log_info "Auto-detected port: ${PORT} (from ${#candidates[@]} candidate(s): ${candidates[*]})"
}

compile_firmware() {
    local cfg="$1"
    log_info "Compiling ESPHome configuration: ${cfg}..."

    local cfg_abs
    cfg_abs="$(cd "$(dirname "$cfg")" && pwd)/$(basename "$cfg")"
    local cfg_dir
    cfg_dir="$(dirname "$cfg_abs")"
    local cfg_base
    cfg_base="$(basename "$cfg_abs")"

    if command -v docker &>/dev/null; then
        log_info "Using Docker esphome image to compile..."
        docker run --rm \
            -v "${cfg_dir}:/config" \
            "${DOCKER_IMAGE}" \
            compile "/config/${cfg_base}"
    elif command -v esphome &>/dev/null; then
        log_info "Using local esphome CLI to compile..."
        esphome compile "$cfg_abs"
    else
        log_error "Neither Docker nor local esphome CLI found. Cannot compile firmware."
        return 1
    fi

    # Locate and extract compiled binary
    mkdir -p "${OUTPUT_DIR}"
    local bin_source=""
    local node_name
    node_name="$(basename "$cfg" .yaml)"

    # Look for .esphome/build/<name>/.pioenvs/<name>/firmware.bin or firmware.factory.bin
    local search_paths=(
        "${cfg_dir}/.esphome/build/${node_name}/.pioenvs/${node_name}/firmware.factory.bin"
        "${cfg_dir}/.esphome/build/${node_name}/.pioenvs/${node_name}/firmware.bin"
        "${cfg_dir}/.esphome/build/${node_name}/firmware.bin"
    )

    for p in "${search_paths[@]}"; do
        if [ -f "$p" ]; then
            bin_source="$p"
            break
        fi
    done

    # Fallback search if path pattern differed
    if [ -z "$bin_source" ] && [ -d "${cfg_dir}/.esphome/build" ]; then
        bin_source="$(find "${cfg_dir}/.esphome/build" -name "*factory.bin" | head -n 1 || true)"
        if [ -z "$bin_source" ]; then
            bin_source="$(find "${cfg_dir}/.esphome/build" -name "firmware.bin" | head -n 1 || true)"
        fi
    fi

    if [ -n "$bin_source" ] && [ -f "$bin_source" ]; then
        local target_bin="${OUTPUT_DIR}/${node_name}.factory.bin"
        cp "$bin_source" "$target_bin"
        log_info "Successfully extracted binary to: ${target_bin}"
        FLASH_TARGET_BIN="$target_bin"
    else
        log_warn "Compilation completed, but binary not found in standard locations."
        FLASH_TARGET_BIN=""
    fi
}

flash_binary() {
    local bin="$1"
    local port="$2"
    local baud="$3"

    if [ ! -f "$bin" ]; then
        log_error "Target binary file not found: ${bin}"
        return 1
    fi

    log_info "Flashing ${bin} to ${port} at ${baud} baud..."
    if command -v esptool.py &>/dev/null; then
        esptool.py --port "$port" --baud "$baud" write_flash 0x0 "$bin"
    elif python3 -m esptool version &>/dev/null; then
        python3 -m esptool --port "$port" --baud "$baud" write_flash 0x0 "$bin"
    elif command -v uv &>/dev/null && uv run esptool.py version &>/dev/null; then
        uv run esptool.py --port "$port" --baud "$baud" write_flash 0x0 "$bin"
    elif command -v docker &>/dev/null && [ -e "$port" ]; then
        log_info "Using Docker esphome container to flash over serial..."
        docker run --rm \
            --device="${port}:${port}" \
            -v "$(dirname "$bin"):/dist" \
            "${DOCKER_IMAGE}" \
            run --no-logs --device "${port}" "/dist/$(basename "$bin")" || {
                # Fallback esptool invocation inside container
                docker run --rm \
                    --device="${port}:${port}" \
                    -v "$(dirname "$bin"):/dist" \
                    --entrypoint esptool.py \
                    "${DOCKER_IMAGE}" \
                    --port "${port}" --baud "${baud}" write_flash 0x0 "/dist/$(basename "$bin")"
            }
    else
        log_error "No esptool or flashing utility available to flash device."
        return 1
    fi
    log_info "Firmware flash completed successfully!"
}

show_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Compile ESPHome configuration, extract firmware binary, and flash to connected XIAO board.

Options:
    -c, --config <file>     Path to ESPHome YAML configuration file
    -p, --port <device>     Target serial port (e.g. /dev/ttyACM0). Auto-detected if omitted.
    -b, --baud <rate>       Flashing baud rate (default: 460800)
    -o, --output-dir <dir>  Directory to save compiled .bin artifacts (default: ./dist_bin)
    --build-only            Compile and extract .bin only; skip flashing
    --flash-only <bin>      Flash pre-built binary without compiling
    -h, --help              Show this help message
EOF
}

main() {
    FLASH_TARGET_BIN=""

    while [ $# -gt 0 ]; do
        case "$1" in
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -p|--port)
                PORT="$2"
                shift 2
                ;;
            -b|--baud)
                BAUD="$2"
                shift 2
                ;;
            -o|--output-dir)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            --build-only)
                BUILD_ONLY=true
                shift
                ;;
            --flash-only)
                FLASH_ONLY_BIN="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    if [ -n "$FLASH_ONLY_BIN" ]; then
        if [ -z "$PORT" ]; then
            auto_detect_port
        fi
        flash_binary "$FLASH_ONLY_BIN" "$PORT" "$BAUD"
        return 0
    fi

    if [ -z "$CONFIG_FILE" ]; then
        log_error "Missing required --config argument."
        show_help
        exit 1
    fi

    compile_firmware "$CONFIG_FILE"

    if [ "$BUILD_ONLY" = true ]; then
        log_info "Build-only flag specified. Skipping flashing step."
        return 0
    fi

    if [ -n "$FLASH_TARGET_BIN" ]; then
        if [ -z "$PORT" ]; then
            auto_detect_port
        fi
        flash_binary "$FLASH_TARGET_BIN" "$PORT" "$BAUD"
    fi
}

main "$@"
