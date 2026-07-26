---
name: prepare-recamera-nodered
description: Prepare Node-RED flows for reCamera deployment. Use when creating flow.json files, configuring InfluxDB connections, or setting up vision processing pipelines on reCamera.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Prepare reCamera Node-RED Flows

Guide for creating and deploying Node-RED flows to reCamera devices.

## Overview

reCamera supports two deployment modes:
- **Node-RED mode**: Visual programming with pre-built nodes for camera, YOLO detection, etc.
- **C++ mode**: Native applications with deb packages (see `prepare-deb-package` skill)

The deployer automatically handles mode switching:
- Stops and disables C++ services when deploying Node-RED
- Restores Node-RED services that may have been disabled by C++ deployment

## Directory Structure

```
solutions/[solution_id]/
├── solution.yaml
├── guide.md
├── guide_zh.md
├── gallery/
├── devices/
│   ├── recamera.yaml              # Node-RED device config
│   └── flow.json                  # Node-RED flow definition
└── docker/                        # Backend services (if needed)
    └── docker-compose.yml
```

## Device Configuration Template

Create `devices/recamera.yaml`:

```yaml
version: "1.0"
id: recamera
name: reCamera Node-RED Configuration
name_zh: reCamera Node-RED 配置
type: recamera_nodered

detection:
  method: network_scan
  manual_entry: true
  requirements: []

nodered:
  flow_file: flow.json              # Flow definition file (in devices/)
  port: 1880                        # Node-RED port on reCamera
  influxdb_node_id: "069087e0ad1b172e"  # ID of InfluxDB config node (for auto-update)

user_inputs:
  - id: recamera_ip
    name: reCamera IP Address
    name_zh: reCamera IP 地址
    type: text
    default: "192.168.42.1"
    placeholder: "192.168.42.1"
    description: IP address of your reCamera device
    description_zh: 您的 reCamera 设备 IP 地址
    required: true
    validation:
      pattern: "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"

  - id: ssh_password
    name: SSH Password
    name_zh: SSH 密码
    type: password
    default: "recamera"
    description: SSH password for service management
    description_zh: SSH 密码（用于服务管理）
    required: false

  - id: influxdb_host
    name: InfluxDB Server IP
    name_zh: InfluxDB 服务器 IP
    type: text
    placeholder: "192.168.1.100"
    description: IP address of InfluxDB server
    description_zh: InfluxDB 服务器 IP 地址
    required: true
    validation:
      pattern: "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"

# Fixed configuration (not shown to user)
influxdb:
  token: "{{influxdb_token}}"
  org: "seeed"
  bucket: "recamera"
  port: 8086

steps:
  - id: prepare
    name: Prepare Device
    name_zh: 准备设备
    description: Stop C++ services, restore Node-RED
    description_zh: 停止 C++ 服务，恢复 Node-RED
  - id: load_flow
    name: Load flow template
    name_zh: 加载流程模板
  - id: configure
    name: Configure InfluxDB connection
    name_zh: 配置 InfluxDB 连接
  - id: connect
    name: Connect to Node-RED
    name_zh: 连接到 Node-RED
  - id: deploy
    name: Deploy flow
    name_zh: 部署流程
  - id: verify
    name: Verify deployment
    name_zh: 验证部署

post_deployment:
  open_browser: false
```

> **Cloud materials**: `nodered.flow_file` accepts URLs. The flow file is automatically downloaded and cached before deployment.

## Flow.json Structure

Create `devices/flow.json`:

```json
[
    {
        "id": "flow-main",
        "type": "tab",
        "label": "Main Flow",
        "disabled": false,
        "info": "Description of your flow"
    },
    {
        "id": "influxdb-config-id",
        "type": "influxdb",
        "hostname": "{{influxdb_host}}",
        "port": "8086",
        "protocol": "http",
        "name": "InfluxDB 2.x",
        "usetls": false,
        "influxdbVersion": "2.0",
        "url": "http://{{influxdb_host}}:8086",
        "org": "seeed",
        "bucket": "recamera",
        "token": "{{influxdb_token}}"
    },
    {
        "id": "camera-input",
        "type": "camera",
        "z": "flow-main",
        "name": "Camera Input",
        "resolution": "1920x1080",
        "fps": 15,
        "x": 120,
        "y": 200,
        "wires": [["yolo-detect"]]
    },
    {
        "id": "yolo-detect",
        "type": "yolo-detect",
        "z": "flow-main",
        "name": "YOLO Detection",
        "model": "yolo11n",
        "confidence": 0.5,
        "classes": ["person"],
        "x": 320,
        "y": 200,
        "wires": [["process-node"]]
    }
]
```

### Key Node Types (reCamera)

| Type | Description | Key Properties |
|------|-------------|----------------|
| `camera` | Camera input | resolution, fps |
| `yolo-detect` | YOLO object detection | model, confidence, classes |
| `privacy-blur` | Privacy masking | blur_radius, classes |
| `heatmap-overlay` | Heatmap visualization | decay_rate, color_map |
| `influxdb` | InfluxDB config | url, org, bucket, token |
| `influxdb out` | Write to InfluxDB | measurement, bucket |

### Template Variables

Use `{{variable}}` syntax for dynamic configuration:
- `{{influxdb_host}}` - Replaced with user-provided InfluxDB IP
- The deployer updates these before sending to Node-RED

## Mode Switching

### C++ → Node-RED

When deploying Node-RED to a device running C++ apps:

1. **Pre-check**: Detect current mode (clean/cpp/nodered/mixed)
2. **Stop C++ services**: `/etc/init.d/S92yolo*-detector stop`
3. **Disable C++ autostart**: Rename `S*` → `K*`
4. **Uninstall C++ packages**: `opkg remove yolo*-detector`
5. **Restore Node-RED**: Rename `K*node-red` → `S*node-red`
6. **Start Node-RED**: `/etc/init.d/S03node-red start`
7. **Deploy flow**: POST to Node-RED Admin API

### Conflict Services

| Service | Priority | Description |
|---------|----------|-------------|
| node-red | S03 | Node-RED runtime |
| sscma-node | S91 | SSCMA Node.js service |
| sscma-supervisor | S93 | SSCMA supervisor |
| yolo*-detector | S92 | YOLO C++ detectors |

## Update guide.md

Add deployment step:

```markdown
## Step 2: Configure reCamera {#recamera type=recamera_nodered required=true config=devices/recamera.yaml}

Deploy the heatmap flow to reCamera.

### Wiring

![Connect reCamera](gallery/recamera_network.png)

1. Connect reCamera to the same network as your computer
2. Enter reCamera IP address (USB default: 192.168.42.1)
3. Enter InfluxDB server IP (from Step 1)
4. Optionally enter SSH password for automatic service management
5. Click Deploy button

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection refused | Ensure reCamera is powered on and connected to network |
| Node-RED not responding | SSH into device and run `/etc/init.d/S03node-red restart` |
| Flow deploy failed | Check Node-RED logs: `journalctl -u node-red` |
| C++ services still running | Provide SSH password for automatic cleanup |
```

## Testing

### Check reCamera Status

```bash
# SSH into reCamera
ssh recamera@192.168.42.1

# Check Node-RED status
/etc/init.d/S03node-red status

# View Node-RED logs
cat /var/log/node-red.log

# Check if C++ services exist
ls /etc/init.d/S*yolo* /etc/init.d/K*yolo* 2>/dev/null

# List installed packages
opkg list-installed | grep -E 'yolo|detector'
```

### Test Node-RED API

```bash
# Get current flows
curl http://192.168.42.1:1880/flows

# Check Node-RED status
curl http://192.168.42.1:1880/settings
```

## InfluxDB Integration

### Required Backend

The reCamera flow typically sends data to an InfluxDB instance. Deploy the backend first:

```yaml
# docker-compose.yml
services:
  influxdb:
    image: influxdb:2.7
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=adminpassword
      - DOCKER_INFLUXDB_INIT_ORG=seeed
      - DOCKER_INFLUXDB_INIT_BUCKET=recamera
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN={{influxdb_token}}
    volumes:
      - influxdb_data:/var/lib/influxdb2

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    depends_on:
      - influxdb
```

### Connection Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| influxdb_host | (user input) | InfluxDB server IP |
| influxdb_port | 8086 | InfluxDB port |
| influxdb_org | seeed | Organization name |
| influxdb_bucket | recamera | Bucket name |
| influxdb_token | {{influxdb_token}} | API token |

## Reference Solutions

- `solutions/recamera_heatmap_grafana/` - Heatmap with InfluxDB + Grafana

## 镜像源自动加速 (Mirror Resolver)

reCamera Node-RED 部署涉及两条不同的安装路径，mirror 注入只覆盖其中一条：

- ✅ **`recamera_nodered_deployer`**（subprocess `npm install ...`）：会自动注入 `NPM_CONFIG_REGISTRY=https://registry.npmmirror.com`（国内设备），大包安装速度大幅提升
- ❌ **`nodered_deployer`**（走 Node-RED Admin HTTP API 装 module）：**不受 mirror 控制** —— Node-RED 上游限制，install 行为完全在 Node-RED runtime 内，env 注入不到

**实战建议**：
- 如果新方案需要装较大或被墙的 npm 包，**优先用 `recamera_nodered_deployer`** 路径
- 走 HTTP API 的方案，若部署反馈 module install 超时，建议改为 deployer subprocess 路径或在设备上预装

flow.json 内的 image / model 下载链接由 deployer 直接发给 reCamera，**不经过 mirror_resolver** —— 如要替换源，需要在 flow.json 里写 mirror URL 或自行做模板替换。
