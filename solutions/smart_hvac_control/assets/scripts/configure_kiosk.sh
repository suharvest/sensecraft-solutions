#!/bin/bash
# Configure Kiosk mode - Auto-start application in fullscreen on boot
# Usage: ./configure_kiosk.sh <username> [app_url]

set -e

KIOSK_USER="${1:-user}"
APP_URL="${2:-http://localhost:8280}"

echo ">>> Configuring Kiosk mode for user: ${KIOSK_USER}..."

# Check if user exists
if ! id "${KIOSK_USER}" &>/dev/null; then
    echo "Error: User '${KIOSK_USER}' does not exist"
    exit 1
fi

# Create kiosk startup script
SCRIPT_DIR="/home/${KIOSK_USER}/.local/bin"
AUTOSTART_DIR="/home/${KIOSK_USER}/.config/autostart"

sudo -u "${KIOSK_USER}" mkdir -p "${SCRIPT_DIR}"
sudo -u "${KIOSK_USER}" mkdir -p "${AUTOSTART_DIR}"

# Create kiosk launch script
cat > /tmp/kiosk.sh << EOF
#!/bin/bash
# HVAC Kiosk Launcher

# Wait for network and services to be ready
sleep 15

# Disable screen saver and power management
xset s off
xset -dpms
xset s noblank

# Start fullscreen browser
if command -v chromium-browser &> /dev/null; then
    chromium-browser --kiosk --noerrdialogs --disable-infobars \\
        --disable-session-crashed-bubble --disable-restore-session-state \\
        --check-for-update-interval=31536000 \\
        "${APP_URL}"
elif command -v chromium &> /dev/null; then
    chromium --kiosk --noerrdialogs --disable-infobars \\
        --disable-session-crashed-bubble --disable-restore-session-state \\
        --check-for-update-interval=31536000 \\
        "${APP_URL}"
elif command -v firefox &> /dev/null; then
    firefox --kiosk "${APP_URL}"
else
    echo "No supported browser found"
    exit 1
fi
EOF

sudo mv /tmp/kiosk.sh "${SCRIPT_DIR}/kiosk.sh"
sudo chown "${KIOSK_USER}:${KIOSK_USER}" "${SCRIPT_DIR}/kiosk.sh"
sudo chmod +x "${SCRIPT_DIR}/kiosk.sh"

# Create autostart desktop entry
cat > /tmp/kiosk.desktop << EOF
[Desktop Entry]
Type=Application
Name=HVAC Kiosk
Comment=HVAC Automation Control System Kiosk Mode
Exec=${SCRIPT_DIR}/kiosk.sh
X-GNOME-Autostart-enabled=true
Hidden=false
NoDisplay=false
EOF

sudo mv /tmp/kiosk.desktop "${AUTOSTART_DIR}/kiosk.desktop"
sudo chown "${KIOSK_USER}:${KIOSK_USER}" "${AUTOSTART_DIR}/kiosk.desktop"

echo ">>> Kiosk mode configured successfully!"
echo ">>> The application will auto-start as ${KIOSK_USER} after reboot"
echo ">>> Application URL: ${APP_URL}"
