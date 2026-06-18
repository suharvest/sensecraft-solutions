# reCamera Ecosystem 实际部署记录

> 日期：2026-02-10
> 环境：reCamera 192.168.10.158（WiFi），HA OS 192.168.10.11

---

## 步骤 2：部署 AI 识别流程（reCamera）

**结果：已跳过** — reCamera 上已经运行了目标 flow（84 个节点）。

验证方式：
```bash
# 检查 /data 端点
curl http://192.168.10.158:1880/data
# 返回 {"total":0,"timestamp":"2026-02-10T10:09:18.406Z"}

# 检查 RTSP 流
ffprobe "rtsp://admin:admin@192.168.10.158:554/live"
# 返回 1920x1080 H.264 视频流

# 检查 flow 内容（通过 Node-RED API）
curl http://192.168.10.158:1880/flows | python3 -c "import json,sys; print(len(json.load(sys.stdin)),'nodes')"
# 84 nodes
```

flow 包含的关键组件：
- `http in` GET `/data` — HA 集成轮询的检测数据接口
- `stream` — RTSP 视频流节点
- `sscma` + `model` + `camera` — YOLO 检测链路
- `ui-*` — FlowFuse Dashboard 界面（调试用）

Node-RED 依赖模块：
- `@flowfuse/node-red-dashboard` 1.26.0
- `node-red-contrib-os` 0.2.1

---

## 步骤 3：在 HA 中安装 reCamera 集成

### 3.1 HA 登录凭据

| 用途 | 用户名 | 密码 |
|------|--------|------|
| HA 网页登录 | chaihuo | 20260124 |
| SSH Addon | chaihuo | 20240124 |

**注意**：HA 网页密码和 SSH Addon 密码是分开配置的，不一样！

### 3.2 认证获取（API 方式）

HA 使用 OAuth 风格的认证流程：

```bash
# 1. 启动登录流
RESP=$(curl -s -X POST http://192.168.10.11:8123/auth/login_flow \
  -H "Content-Type: application/json" \
  -d '{"client_id":"http://192.168.10.11:8123/","handler":["homeassistant",null],"redirect_uri":"http://192.168.10.11:8123/"}')
FLOW_ID=$(echo "$RESP" | python3 -c "import json,sys; print(json.load(sys.stdin)['flow_id'])")

# 2. 提交凭据
RESULT=$(curl -s -X POST "http://192.168.10.11:8123/auth/login_flow/$FLOW_ID" \
  -H "Content-Type: application/json" \
  -d '{"client_id":"http://192.168.10.11:8123/","username":"chaihuo","password":"20260124"}')
AUTH_CODE=$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['result'])")

# 3. 换取 access token
TOKEN_RESP=$(curl -s -X POST http://192.168.10.11:8123/auth/token \
  -d "grant_type=authorization_code&code=$AUTH_CODE&client_id=http://192.168.10.11:8123/")
# token 有效期 1800 秒
```

### 3.3 查看已安装的 Addon

通过 WebSocket API 查看（REST hassio 端点返回 401，需用 WS）：

```python
import asyncio, json, websockets

async def main():
    async with websockets.connect("ws://192.168.10.11:8123/api/websocket") as ws:
        await ws.recv()  # auth_required
        await ws.send(json.dumps({"type": "auth", "access_token": TOKEN}))
        await ws.recv()  # auth_ok
        await ws.send(json.dumps({
            "id": 1, "type": "supervisor/api",
            "endpoint": "/addons", "method": "get"
        }))
        msg = json.loads(await ws.recv())
        for a in msg["result"]["addons"]:
            print(f"{a['slug']}: {a['name']} ({a['state']})")
```

当前已安装的 Addon：
- `core_samba` — Samba share（停止）
- `core_configurator` — File editor（运行中）
- `core_mosquitto` — Mosquitto broker（运行中）
- `fb59d657_nodered` — Node-RED（运行中）
- `fb59d657_ssh` — Advanced SSH & Web Terminal（运行中）

### 3.4 SSH 连接 HA OS

SSH Addon 配置（通过 WS API 读取 `/addons/fb59d657_ssh/info` 的 `options` 字段）：
```json
{
  "ssh": {
    "username": "chaihuo",
    "password": "20240124",
    "authorized_keys": [],
    "sftp": false
  }
}
```

连接命令：
```bash
sshpass -p '20240124' ssh -o StrictHostKeyChecking=no chaihuo@192.168.10.11
```

**注意**：
- SCP 不可用（`subsystem request failed on channel 0`），因为 sftp 被禁用
- `docker` 命令不可用（Protection Mode 限制）
- `sudo` 可用，写入 `/config` 需要 sudo

### 3.5 复制 custom_components 文件

由于 SCP 不可用，使用 tar + base64 管道传输：

```bash
cd solutions/recamera_ecosystem/assets/docker/custom_components/recamera

# 打包 → base64 编码 → SSH 管道 → 解码 → 解包
tar cf - *.py manifest.json | base64 | \
  sshpass -p '20240124' ssh -o StrictHostKeyChecking=no chaihuo@192.168.10.11 "
    sudo mkdir -p /config/custom_components/recamera && \
    base64 -d | sudo tar xf - -C /config/custom_components/recamera/
  "

# 清理 macOS 生成的 ._ 元数据文件
sshpass -p '20240124' ssh chaihuo@192.168.10.11 "sudo rm /config/custom_components/recamera/._* 2>/dev/null"
```

最终文件列表（7 个文件）：
```
/config/custom_components/recamera/
├── __init__.py
├── camera.py
├── config_flow.py
├── const.py
├── coordinator.py
├── manifest.json
└── sensor.py
```

**注意**：原 GitHub 仓库没有 `strings.json`，但不影响功能（UI 显示为字段原始 key 名）。

### 3.6 重启 HA

```bash
HA_TOKEN=...
curl -s -X POST http://192.168.10.11:8123/api/services/homeassistant/restart \
  -H "Authorization: Bearer $HA_TOKEN"
```

重启耗时约 15 秒。重启后需重新获取 token（旧 token 失效）。

### 3.7 添加集成（Config Flow）

通过 REST API 添加（也可在 HA UI 中手动操作）：

```bash
# 1. 启动 config flow
curl -s -X POST http://192.168.10.11:8123/api/config/config_entries/flow \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"handler":"recamera","show_advanced_options":false}'
# 返回 form，包含 flow_id 和 data_schema（host + port）

# 2. 提交表单
FLOW_ID="..."
curl -s -X POST "http://192.168.10.11:8123/api/config/config_entries/flow/$FLOW_ID" \
  -H "Authorization: Bearer $HA_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"host":"192.168.10.158","port":1880}'
# 返回 create_entry，state: "loaded"
```

等效 UI 操作：设置 → 设备与服务 → 添加集成 → 搜索 "reCamera" → 填入 IP → 提交

---

## 验证结果

### 实体状态

| 实体 | 状态 | 说明 |
|------|------|------|
| `camera.recamera_stream` | `streaming` | RTSP 流 `rtsp://admin:admin@{ip}:554/live` |
| `sensor.recamera_detection` | `0`~`1` | 每 ~4 秒轮询 `http://{ip}:1880/data`，有物体时变化 |

### 设备注册

```
Device: reCamera (192.168.10.158)
  Manufacturer: Seeed Studio
  Model: reCamera AI (YOLO11n)
  Identifiers: [['recamera', '192.168.10.158']]
```

### Sensor 属性示例

```json
{
  "total": 0,
  "timestamp": "2026-02-10T10:31:12.741Z",
  "icon": "mdi:account-group",
  "friendly_name": "reCamera Detection"
}
```

当检测到物体时 total > 0，属性中还可能出现 `person: 1`, `car: 2` 等分类计数。

### RTSP 流

```
格式: H.264 Constrained Baseline
分辨率: 1920x1080
URL: rtsp://admin:admin@192.168.10.158:554/live
```

从 HA 服务器（192.168.10.11）可以访问 reCamera 的 554 和 1880 端口。

---

## 已知问题

### 1. 摄像头静态快照超时

HA 日志出现 `Timeout while waiting of FFmpeg` 警告。原因是 `camera.py` 的 `async_camera_image` 方法调用 ffmpeg 从 RTSP 截图，在 HA OS 环境下 ffmpeg 连接超时。

**影响**：
- HA 面板中的摄像头卡片缩略图可能显示空白
- 实时流播放（HLS/WebRTC）不受影响

**可能的修复方向**：
- 增加 ffmpeg 超时时间
- 改用 HTTP 快照（如果 reCamera 提供的话）
- 在 `camera.py` 中添加 `-rtsp_transport tcp` 参数

### 2. 无 strings.json

GitHub 源仓库缺少 `strings.json`，导致 config flow 表单显示字段原始 key 名（`host`、`port`）而非友好的标签文字。功能不受影响。

### 3. macOS tar 生成 ._ 文件

从 macOS 用 tar 打包会生成 `._xxx` 元数据文件，需手动清理，否则 HA 可能报警告。

---

## Docker 部署 HA Core 验证（192.168.8.196）

> 日期：2026-02-11
> 环境：Raspberry Pi 5 (aarch64, Debian)，Docker 28.1.1

### 部署过程

```bash
# 1. 复制文件到远程
ssh harvest@192.168.8.196 "mkdir -p ~/recamera-ha/custom_components/recamera"
scp docker-compose.yml harvest@192.168.8.196:~/recamera-ha/
scp custom_components/recamera/* harvest@192.168.8.196:~/recamera-ha/custom_components/recamera/

# 2. 启动
ssh harvest@192.168.8.196 "cd ~/recamera-ha && docker compose up -d"
# 拉取约 50MB 新层，耗时约 2 分钟，容器启动成功
```

### 验证结果

| 检查项 | 结果 |
|--------|------|
| 容器状态 | Up, port 8123 映射正确 |
| custom_components 挂载 | `docker exec recamera-homeassistant ls /config/custom_components/recamera/` — 7 个文件全部存在 |
| HA 版本 | 2026.2.1 |
| HTTP 状态 | 302（重定向到 onboarding） |
| Onboarding | 通过 API 完成用户创建 + 初始化 |
| Config Flow | 成功启动 recamera handler，返回 form |
| 集成创建 | `create_entry` 成功，但 state=`setup_retry`（因为 192.168.8.x 和 192.168.10.x 跨子网，无法访问 reCamera） |

### Docker 方式 vs HAOS 方式对比

| 项目 | Docker 部署（Step 1） | HAOS 已有实例 |
|------|----------------------|---------------|
| custom_components 安装 | **自动**：docker-compose.yml volume 挂载 | **手动**：需 SSH/Samba 复制到 /config/ |
| 重启 HA | 不需要（首次启动就加载） | 需要重启才能加载新组件 |
| 添加集成 | UI 操作相同 | UI 操作相同 |
| 整体步骤 | 1 步（部署即完成） | 3 步（复制→重启→添加） |

### 结论

Docker 部署方式完全可行，且比 HAOS 简单——`docker-compose.yml` 已经通过 volume 挂载了 custom_components，用户只需 `docker compose up -d` + 在 UI 中添加集成。

### 磁盘空间

部署前可用 2.2G（93% 已用），HA 镜像约 1.2G（大部分层已缓存），实际新增约 50MB。已清理测试环境。

---

## 关键发现

1. **HA REST API vs WebSocket API**：`/api/hassio/*` 端点通过 REST 返回 401，必须用 WebSocket `supervisor/api` 类型的消息来访问 Supervisor API
2. **SCP 在 SSH Addon 不可用**：当 sftp 选项为 false 时，SCP subsystem 不可用，需要用 tar+base64 管道方式传文件
3. **Config Flow API 路径**：`POST /api/config/config_entries/flow`（启动）+ `POST /api/config/config_entries/flow/{flow_id}`（提交表单）
4. **HA 重启后 token 失效**：重启 HA 后旧 access token 不再有效，需要重新走 login flow 获取新 token
5. **reCamera RTSP 需要认证**：URL 格式 `rtsp://admin:admin@{ip}:554/live`，不带认证会返回空
6. **SSH Addon slug 不固定**：社区版 Advanced SSH 的 slug 因仓库不同而异（`a0d7b954_ssh`、`fb59d657_ssh` 等），不能硬编码，需按 addon name 扫描
7. **HA 重启 504 Gateway Timeout**：发送 restart 请求后 HA 即开始关闭，Supervisor 反代返回 504，deployer 需忽略此错误
8. **HAOS 重启耗时较长**：整个 Supervisor 栈重启（不只是 HA Core），实测需要 30-90 秒，wait_for_ha 需要足够长的超时

---

## 自动化 Deployer 测试（2026-02-11）

> 环境：HAOS 192.168.10.11，reCamera 192.168.10.158

### ha_integration_deployer.py E2E 测试结果

通过 API `POST /api/deployments/start` 触发部署：

```json
{
  "solution_id": "recamera_ecosystem",
  "preset_id": "ha_integration",
  "selected_devices": ["configure_ha"],
  "device_connections": {
    "configure_ha": {
      "host": "192.168.10.11",
      "username": "chaihuo",
      "password": "20260124",
      "recamera_ip": "192.168.10.158"
    }
  }
}
```

| 步骤 | 状态 | 耗时 | 说明 |
|------|------|------|------|
| auth | completed | ~1s | HA 登录流程成功 |
| detect | completed | <1s | 正确识别为 HA OS |
| ssh | completed | <1s | 找到 `fb59d657_ssh`（按名称扫描） |
| copy | completed | ~1s | tar+base64 传输 7 个文件 |
| restart | completed | ~40s | 发送重启请求 + 等待回来 + 重新登录 |
| integrate | completed | <1s | 检测到已有集成，跳过创建 |

### 修复的 Bug

1. **504 Gateway Timeout**：`_restart_ha()` 现在忽略 502/503/504 和连接重置错误
2. **等待超时**：`_wait_for_ha()` 默认 180s（原 120s），检查根 URL 而非 `/api/`
3. **SSH 插件发现**：按名称扫描（`*_ssh` + name 包含 "ssh" 或 "terminal"），不再硬编码 slug
