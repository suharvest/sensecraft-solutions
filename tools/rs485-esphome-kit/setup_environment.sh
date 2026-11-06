#!/usr/bin/env bash
# tools/rs485-esphome-kit/setup_environment.sh
# Environment configuration, udev setup, tmpfs mounting, and seed warmup for XIAO RS485 ESPHome nodes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEEDS_DIR="${SCRIPT_DIR}/warmup_seeds"
TMPFS_MOUNT="/tmp/esphome-cache"
UDEV_RULE_FILE="/etc/udev/rules.d/99-xiao-rs485.rules"
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

check_dependencies() {
    log_info "Checking tool dependencies..."
    local missing=()
    for cmd in docker python3; do
        if ! command -v "$cmd" &>/dev/null; then
            missing+=("$cmd")
        fi
    done

    if [ ${#missing[@]} -gt 0 ]; then
        log_warn "Missing tools: ${missing[*]}. Please ensure required packages are installed."
    else
        log_info "All primary dependencies found."
    fi
}

setup_udev_rules() {
    log_info "Configuring udev rules for Seeed Studio XIAO ESP32 USB devices..."
    local rules_content
    rules_content="# Seeed Studio XIAO ESP32 Serial / JTAG rules
# Espressif USB JTAG / CDC Serial (XIAO ESP32-C3 / S3 / C6)
SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"303a\", ATTRS{idProduct}==\"1001\", MODE=\"0666\", GROUP=\"dialout\"
SUBSYSTEM==\"usb\", ATTRS{idVendor}==\"303a\", ATTRS{idProduct}==\"1001\", MODE=\"0666\", GROUP=\"dialout\"

# WCH CH340 / CH341 USB to Serial
SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"1a86\", ATTRS{idProduct}==\"7523\", MODE=\"0666\", GROUP=\"dialout\"
SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"1a86\", ATTRS{idProduct}==\"55d4\", MODE=\"0666\", GROUP=\"dialout\"

# Silicon Labs CP210x USB to Serial
SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"10c4\", ATTRS{idProduct}==\"ea60\", MODE=\"0666\", GROUP=\"dialout\"

# FTDI FT232 USB to Serial
SUBSYSTEM==\"tty\", ATTRS{idVendor}==\"0403\", ATTRS{idProduct}==\"6001\", MODE=\"0666\", GROUP=\"dialout\"
"

    if [ "$EUID" -eq 0 ]; then
        echo "$rules_content" > "$UDEV_RULE_FILE"
        if command -v udevadm &>/dev/null; then
            udevadm control --reload-rules || true
            udevadm trigger || true
        fi
        log_info "udev rules installed to ${UDEV_RULE_FILE}"
    elif command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
        echo "$rules_content" | sudo tee "$UDEV_RULE_FILE" > /dev/null
        if command -v udevadm &>/dev/null; then
            sudo udevadm control --reload-rules || true
            sudo udevadm trigger || true
        fi
        log_info "udev rules installed to ${UDEV_RULE_FILE} using sudo."
    else
        log_warn "Root or passwordless sudo permissions required to write to ${UDEV_RULE_FILE}."
        log_warn "To install manually, write the rules into ${UDEV_RULE_FILE} and run: sudo udevadm control --reload-rules && sudo udevadm trigger"
    fi
}

setup_tmpfs() {
    log_info "Setting up tmpfs cache at ${TMPFS_MOUNT} to accelerate builds..."
    mkdir -p "${TMPFS_MOUNT}"
    if mountpoint -q "${TMPFS_MOUNT}"; then
        log_info "tmpfs already mounted at ${TMPFS_MOUNT}."
        return 0
    fi

    if [ "$EUID" -eq 0 ]; then
        mount -t tmpfs -o size=2G,mode=0777 tmpfs "${TMPFS_MOUNT}"
        log_info "tmpfs mounted at ${TMPFS_MOUNT} (2GB)."
    elif command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
        sudo mount -t tmpfs -o size=2G,mode=0777 tmpfs "${TMPFS_MOUNT}"
        log_info "tmpfs mounted at ${TMPFS_MOUNT} using sudo."
    else
        log_warn "Cannot mount tmpfs without root; using standard directory cache at ${TMPFS_MOUNT}."
    fi
}

warmup_single_chip() {
    local chip="$1"
    local seed_yaml="${SEEDS_DIR}/warmup_seed_${chip}.yaml"

    if [ ! -f "$seed_yaml" ]; then
        log_error "Warmup seed not found: ${seed_yaml}"
        return 1
    fi

    log_info "Warming up chip ${chip} with seed ${seed_yaml}..."
    if command -v docker &>/dev/null; then
        log_info "Running docker compile for ${chip}..."
        docker run --rm \
            -v "${SCRIPT_DIR}:/work" \
            -v "${TMPFS_MOUNT}:/root/.platformio" \
            -w /work \
            "${DOCKER_IMAGE}" \
            compile "warmup_seeds/warmup_seed_${chip}.yaml" || {
                log_warn "Docker compile for ${chip} finished with non-zero exit code (network or image check)."
            }
    elif command -v esphome &>/dev/null; then
        log_info "Running local esphome compile for ${chip}..."
        esphome compile "$seed_yaml" || {
            log_warn "Local esphome compile for ${chip} finished with non-zero exit code."
        }
    else
        log_warn "Neither docker nor esphome CLI found. Skipping active compilation for ${chip}."
    fi
}

warmup_all_chips() {
    log_info "Starting compilation warmup for C3, S3, and C6 chips..."
    for chip in c3 s3 c6; do
        warmup_single_chip "$chip"
    done
    log_info "Warmup cycle completed."
}

show_help() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Configure environment, tmpfs, udev rules, and preheat ESPHome compilers for XIAO RS485 nodes.

Options:
    --all           Run full setup: dependencies, udev, tmpfs, and preheat seeds (default)
    --udev          Configure udev rules for ESP32/XIAO USB devices
    --tmpfs         Mount tmpfs cache for faster platformio compilation
    --warmup        Run docker warmup compile for C3, S3, and C6 seeds
    -h, --help      Show this help message
EOF
}

main() {
    if [ $# -eq 0 ]; then
        check_dependencies
        setup_udev_rules
        setup_tmpfs
        warmup_all_chips
        return 0
    fi

    while [ $# -gt 0 ]; do
        case "$1" in
            --all)
                check_dependencies
                setup_udev_rules
                setup_tmpfs
                warmup_all_chips
                ;;
            --udev)
                setup_udev_rules
                ;;
            --tmpfs)
                setup_tmpfs
                ;;
            --warmup)
                warmup_all_chips
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
        shift
    done
}

main "$@"
