---
name: prepare-deb-package
description: Prepare Debian packages for reCamera C++ deployment. Use when creating .deb packages for reCamera devices, configuring init scripts, or setting up binary deployment files.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Prepare Debian Packages for reCamera

Guide for creating .deb packages that deploy C++ applications to reCamera devices.

## Overview

reCamera devices run a BusyBox-based Linux system that uses:
- `opkg` for package management (not apt/dpkg)
- SysVinit for service management (not systemd)
- RISCV64 architecture (cv181x chip)

## Directory Structure

```
solutions/[solution_id]/
├── solution.yaml
├── guide.md
├── guide_zh.md
├── gallery/
├── packages/                      # Deb packages and models
│   ├── [app]-detector_x.x.x_riscv64.deb
│   └── [model].cvimodel
└── devices/
    └── recamera_[variant].yaml    # Device config
```

## Device Configuration Template

Create `devices/recamera_[variant].yaml`:

```yaml
version: "1.0"
id: recamera_yolo11
name: reCamera YOLO11 Detector
name_zh: reCamera YOLO11 检测器
type: recamera_cpp

detection:
  method: network_scan
  manual_entry: true
  requirements: []

# SSH connection config
ssh:
  port: 22
  default_user: recamera
  default_host: 192.168.42.1
  connection_timeout: 30
  command_timeout: 300

# C++ application deployment config
binary:
  # .deb package (includes init script)
  deb_package:
    path: packages/yolo11-detector_0.1.1_riscv64.deb
    name: yolo11-detector
    includes_init_script: true    # deb contains /etc/init.d/S*

  # Model files
  models:
    - path: packages/model.cvimodel
      target_path: /userdata/local/models
      filename: model.cvimodel

  # Service configuration
  service_name: yolo11-detector
  service_priority: 92            # S92yolo11-detector

  # MQTT external access (optional)
  mqtt_config:
    enable: true
    port: 1883
    allow_anonymous: true

  # Conflict service handling
  conflict_services:
    stop:                         # Stop before deployment
      - S03node-red
      - S91sscma-node
      - S93sscma-supervisor
    disable:                      # Disable autostart (S* -> K*)
      - node-red
      - sscma-node
      - sscma-supervisor

  auto_start: true

> **Cloud materials**: `deb_package.path` and `models[].path` accept URLs (e.g., `https://cdn.example.com/package.deb`). Files are automatically downloaded and cached before deployment.

# User inputs
user_inputs:
  - id: host
    name: Device IP Address
    name_zh: 设备 IP 地址
    type: text
    default: "192.168.42.1"
    required: true
    validation:
      pattern: "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"

  - id: password
    name: SSH Password
    name_zh: SSH 密码
    type: password
    default: "recamera"
    required: true

# Deployment steps (shown to user)
steps:
  - id: connect
    name: SSH Connect
    name_zh: SSH 连接
  - id: precheck
    name: Check Device State
    name_zh: 检查设备状态
  - id: prepare
    name: Stop Conflicting Services
    name_zh: 停止冲突服务
  - id: transfer
    name: Transfer Files
    name_zh: 传输文件
  - id: install
    name: Install Package
    name_zh: 安装软件包
  - id: models
    name: Deploy Model
    name_zh: 部署模型
  - id: mqtt
    name: Configure MQTT
    name_zh: 配置 MQTT
  - id: disable
    name: Disable Conflicts
    name_zh: 禁用冲突服务
  - id: start
    name: Start Service
    name_zh: 启动服务
  - id: verify
    name: Verify
    name_zh: 验证

post_deployment:
  open_browser: false
```

## Creating the .deb Package

### Package Structure

```
yolo11-detector_0.1.1_riscv64/
├── DEBIAN/
│   ├── control
│   └── postinst
├── usr/
│   └── bin/
│       └── yolo11-detector       # The compiled binary
└── etc/
    └── init.d/
        └── S92yolo11-detector    # SysVinit script
```

### DEBIAN/control

```
Package: yolo11-detector
Version: 0.1.1
Architecture: riscv64
Maintainer: Seeed Studio <support@seeed.cc>
Description: YOLO11 object detector for reCamera
 Detects objects using YOLO11 model and publishes to MQTT.
```

### DEBIAN/postinst

```bash
#!/bin/sh
chmod +x /usr/bin/yolo11-detector
chmod +x /etc/init.d/S92yolo11-detector
exit 0
```

### SysVinit Script Template

Create `etc/init.d/S92yolo11-detector`:

```bash
#!/bin/sh

NAME="yolo11-detector"
DAEMON="/usr/bin/yolo11-detector"
PIDFILE="/var/run/${NAME}.pid"
LOGFILE="/var/log/${NAME}.log"

# Model and config paths
MODEL_PATH="/userdata/local/models/yolo11n_detection_cv181x_int8.cvimodel"
MQTT_HOST="localhost"
MQTT_PORT="1883"

start() {
    echo "Starting $NAME..."
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "$NAME already running"
        return 0
    fi

    $DAEMON \
        --model "$MODEL_PATH" \
        --mqtt-host "$MQTT_HOST" \
        --mqtt-port "$MQTT_PORT" \
        > "$LOGFILE" 2>&1 &

    echo $! > "$PIDFILE"
    echo "$NAME started (PID: $(cat $PIDFILE))"
}

stop() {
    echo "Stopping $NAME..."
    if [ -f "$PIDFILE" ]; then
        kill $(cat "$PIDFILE") 2>/dev/null
        rm -f "$PIDFILE"
    fi
    killall $NAME 2>/dev/null || true
    echo "$NAME stopped"
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "$NAME is running (PID: $(cat $PIDFILE))"
    else
        echo "$NAME is not running"
        return 1
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0
```

### Build Commands

```bash
# Set permissions
chmod +x yolo11-detector_0.1.1_riscv64/DEBIAN/postinst
chmod +x yolo11-detector_0.1.1_riscv64/etc/init.d/S92yolo11-detector

# Build package
dpkg-deb --build yolo11-detector_0.1.1_riscv64
```

## Service Priority Reference

| Priority | Service | Description |
|----------|---------|-------------|
| 03 | node-red | Node-RED (default app) |
| 91 | sscma-node | SSCMA Node service |
| 92 | yolo*-detector | YOLO detectors |
| 93 | sscma-supervisor | SSCMA supervisor |

## Deployment Flow

1. **Pre-check**: Detect current device state (Node-RED/C++/Clean)
2. **Cleanup**: Stop and disable conflicting services
3. **Transfer**: Upload .deb and model files via SCP
4. **Install**: `opkg install --force-reinstall /tmp/package.deb`
5. **Deploy models**: Copy to `/userdata/local/models/`
6. **Configure MQTT**: Enable external access if needed
7. **Start service**: Run init script
8. **Verify**: Check service status

## Update guide.md

Add deployment step:

```markdown
## Step 2: Deploy YOLO Detector {#deploy_yolo type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

Deploy the YOLO11 object detector to reCamera.

### Wiring

![Connect reCamera](gallery/recamera_connect.png)

1. Connect reCamera to computer via USB or ensure on same network
2. Enter reCamera IP address (default: 192.168.42.1 for USB)
3. Enter SSH password (default: recamera)
4. Click Deploy button

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Check IP and password, try 'recamera' or 'recamera.2' |
| Package install failed | Device may have incompatible version, contact support |
| Service won't start | Check logs: `cat /var/log/yolo11-detector.log` |
```

## Testing on Device

```bash
# SSH into reCamera
ssh recamera@192.168.42.1

# Check installed packages
opkg list-installed | grep yolo

# Check service status
/etc/init.d/S92yolo11-detector status

# View logs
cat /var/log/yolo11-detector.log

# Check MQTT output
mosquitto_sub -h localhost -t "sscma/v0/#" -v
```

## Reference Solutions

- `solutions/recamera_heatmap_grafana/` - Example with YOLO11/YOLO26 variants
