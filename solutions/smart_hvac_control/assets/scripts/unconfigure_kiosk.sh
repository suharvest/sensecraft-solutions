#!/bin/bash
# Unconfigure Kiosk mode - Remove auto-start configuration
# Usage: ./unconfigure_kiosk.sh <username>

set -e

KIOSK_USER="${1:-user}"

echo ">>> Removing Kiosk mode configuration for user: ${KIOSK_USER}..."

# Check if user exists
if ! id "${KIOSK_USER}" &>/dev/null; then
    echo "Error: User '${KIOSK_USER}' does not exist"
    exit 1
fi

# Define paths
SCRIPT_DIR="/home/${KIOSK_USER}/.local/bin"
AUTOSTART_DIR="/home/${KIOSK_USER}/.config/autostart"

# Remove autostart desktop entry
if [ -f "${AUTOSTART_DIR}/kiosk.desktop" ]; then
    rm -f "${AUTOSTART_DIR}/kiosk.desktop"
    echo ">>> Removed autostart entry"
fi

# Remove kiosk script
if [ -f "${SCRIPT_DIR}/kiosk.sh" ]; then
    rm -f "${SCRIPT_DIR}/kiosk.sh"
    echo ">>> Removed kiosk script"
fi

echo ">>> Kiosk mode has been disabled!"
echo ">>> The system will boot normally after reboot"
