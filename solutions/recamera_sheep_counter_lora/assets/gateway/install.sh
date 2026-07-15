#!/usr/bin/env bash
set -euo pipefail

# Sheep Counter Gateway Install Script
# Deploys meshtastic_mqtt_bridge and ha_bridge to a reComputer/Raspberry Pi
# with systemd auto-start.

INSTALL_DIR="/opt/sheep-gateway"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MQTT_HOST="${MQTT_HOST:-127.0.0.1}"
MQTT_PORT="${MQTT_PORT:-1883}"
SERIAL_PORT="${SERIAL_PORT:-/dev/ttyACM0}"

echo "[install] Sheep Counter Gateway installer"
echo "[install] Target: $INSTALL_DIR"

# 1. Ensure Python 3 and venv are available
if ! command -v python3 &>/dev/null; then
    echo "[install] python3 not found — attempting install..."
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq python3 python3-venv
    elif command -v apk &>/dev/null; then
        apk add --no-cache python3 py3-pip
    else
        echo "[install] ERROR: no package manager found. Install python3 manually." >&2
        exit 1
    fi
fi

# 2. Create install directory and isolated Python environment
echo "[install] Creating Python environment..."
mkdir -p "$INSTALL_DIR"
if ! python3 -m venv "$INSTALL_DIR/venv"; then
    if command -v apt-get &>/dev/null; then
        apt-get update -qq && apt-get install -y -qq python3-venv
        python3 -m venv "$INSTALL_DIR/venv"
    else
        echo "[install] ERROR: python3 venv support is required." >&2
        exit 1
    fi
fi
"$INSTALL_DIR/venv/bin/pip" install --quiet paho-mqtt meshtastic requests

# 3. Copy scripts
echo "[install] Copying bridge scripts to $INSTALL_DIR..."
cp "$SCRIPT_DIR/meshtastic_mqtt_bridge.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/ha_bridge.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/ha_dashboard.yaml" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/meshtastic_mqtt_bridge.py" "$INSTALL_DIR/ha_bridge.py"

# 4. Write environment file
echo "[install] Writing environment file..."
cat >"$INSTALL_DIR/.env" <<EOF
MQTT_HOST=$MQTT_HOST
MQTT_PORT=$MQTT_PORT
SERIAL_PORT=$SERIAL_PORT
EOF
chmod 600 "$INSTALL_DIR/.env"

# 5. Write systemd service for meshtastic-bridge
echo "[install] Creating systemd service: meshtastic-bridge..."
cat >/etc/systemd/system/meshtastic-bridge.service <<'EOF'
[Unit]
Description=Meshtastic to MQTT Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/opt/sheep-gateway/.env
ExecStart=/opt/sheep-gateway/venv/bin/python /opt/sheep-gateway/meshtastic_mqtt_bridge.py
Restart=always
RestartSec=5
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 6. Write systemd service for ha-bridge
echo "[install] Creating systemd service: ha-bridge..."
cat >/etc/systemd/system/ha-bridge.service <<'EOF'
[Unit]
Description=Home Assistant Sheep Counter Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=/opt/sheep-gateway/.env
ExecStart=/opt/sheep-gateway/venv/bin/python /opt/sheep-gateway/ha_bridge.py
Restart=always
RestartSec=5
User=root
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 7. Reload systemd and enable services
echo "[install] Enabling systemd services..."
systemctl daemon-reload
systemctl enable meshtastic-bridge ha-bridge

# 8. Start services
echo "[install] Starting services..."
systemctl restart meshtastic-bridge
systemctl restart ha-bridge

# 9. Health check
echo "[install] Running health check..."
sleep 2
for service in meshtastic-bridge ha-bridge; do
    if systemctl is-active --quiet "$service"; then
        echo "[install] ✓ $service is active"
    else
        echo "[install] ERROR: $service failed to start" >&2
        journalctl -u "$service" -n 20 --no-pager >&2 || true
        exit 1
    fi
done

echo "[install] Done. Dashboard config: $INSTALL_DIR/ha_dashboard.yaml"
