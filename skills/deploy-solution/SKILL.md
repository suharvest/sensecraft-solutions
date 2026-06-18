---
name: deploy-solution
description: Deploy an IoT solution via the provisioning station API. Use this skill whenever the user asks to deploy, flash, install, or set up any solution on devices — even if they don't say "deploy" explicitly. Also use it when troubleshooting a failed deployment or checking deployment status.
user_invocable: true
arguments:
  - name: solution_id
    description: "Solution ID to deploy (optional — will list available solutions if omitted)"
    required: false
---

# Deploy Solution Skill

Deploy IoT solutions through the provisioning station backend API. The core workflow is:
**discover backend → pick solution → get deploy-info → fill parameters → start → monitor → verify**.

## 1. Discover Backend

```bash
# Default port is 3260, verify it's running
curl -s http://127.0.0.1:3260/api/health
```

Set `BASE=http://127.0.0.1:3260` for all subsequent commands. If the health check fails, the user needs to start the backend first (`./dev.sh`).

## 2. Deployment Flow

### Step 1: List solutions

```bash
curl -s $BASE/api/solutions?lang=en | python3 -m json.tool
```

### Step 2: Get deploy-info (the key endpoint)

This is the AI-friendly endpoint — it returns structured parameters and a ready-to-fill request template. Always use this instead of `/deployment`.

```bash
# Without preset — returns all presets and all steps
curl -s "$BASE/api/solutions/{solution_id}/deploy-info?lang=en"

# With preset — returns only steps for that preset (recommended)
curl -s "$BASE/api/solutions/{solution_id}/deploy-info?lang=en&preset_id=grafana"
```

**Response structure:**
- `presets` — available presets with IDs and names
- `steps[]` — each step with `device_id`, `type`, `required`, `parameters`, and optional `targets`
- `request_template` — a JSON body you can fill in and POST directly to `/deployments/start`

The `request_template` has `<REQUIRED: ...>` placeholders for values the user must provide, and sensible defaults for everything else. This is your starting point — show it to the user and fill in the blanks.

### Step 3: Detect devices (optional but helpful)

Auto-detect USB/serial devices and network devices:

```bash
# Detect USB/serial devices for a solution
curl -s "$BASE/api/devices/detect/{solution_id}?preset={preset_id}"

# Scan local network for SSH-capable devices (reCamera, Jetson, etc.)
curl -s "$BASE/api/devices/scan-mdns"

# Check local Docker availability
curl -s "$BASE/api/docker-devices/local/check"
```

Use detected device info to pre-fill connection parameters.

### Step 4: Confirm parameters with user

Show the `request_template` from Step 2. Key things to confirm:
- **Device IPs** — user must provide these (or use detected values)
- **Passwords** — verify defaults are correct
- **Preset selection** — if multiple presets, ask which one
- **Target selection** — for `docker_deploy` steps with multiple targets

### Step 5: Start deployment

```bash
curl -s -X POST $BASE/api/deployments/start \
  -H "Content-Type: application/json" \
  -d '{
    "solution_id": "...",
    "preset_id": "...",
    "selected_devices": ["step1", "step2"],
    "device_connections": {
      "step1": { "host": "192.168.1.100", "username": "user", "password": "pass" },
      "step2": {}
    }
  }'
```

Returns `{ "deployment_id": "..." }`.

**Target routing for `docker_deploy` steps:**

When a step has type `docker_deploy` with multiple targets (local + remote), specify which target via the `target` key in `device_connections`. Target IDs come from the `targets` array in the deploy-info response.

```json
{
  "device_connections": {
    "deploy_step": {
      "target": "jetson_remote",
      "host": "192.168.1.100",
      "username": "user",
      "password": "pass",
      "auto_replace_containers": true
    }
  }
}
```

- Without `target`, uses the default target (marked `default: true` in deploy-info)
- For remote targets, include `host`, `username`, `password`
- Set `auto_replace_containers: true` to replace existing containers

### Step 6: Monitor deployment

**Option A — HTTP polling (simpler, recommended for scripts):**

```bash
# Concise summary with errors/warnings
curl -s $BASE/api/deployments/{deployment_id}/summary

# Full status with per-step progress
curl -s $BASE/api/deployments/{deployment_id}

# Detailed logs (for debugging)
curl -s $BASE/api/deployments/{deployment_id}/logs
```

Poll `/summary` every 3-5 seconds until `status` is `completed` or `failed`.

**Option B — WebSocket (real-time logs):**

```bash
# Single deployment
websocat "ws://127.0.0.1:3260/ws/logs/{deployment_id}"

# All deployments
websocat "ws://127.0.0.1:3260/ws/all"
```

Note: the WebSocket path is `/ws/logs/`, not `/ws/deployments/`.

### Step 7: Cancel if needed

```bash
curl -s -X POST $BASE/api/deployments/{deployment_id}/cancel
```

## 3. Common Device Credentials

| Device | Default IP | Username | Password |
|--------|-----------|----------|----------|
| reCamera (USB) | 192.168.42.1 | recamera | recamera |
| reCamera (network) | varies | recamera | recamera |
| reComputer / Jetson | varies | recomputer | 12345678 |

## 4. Debugging Failures

1. Check `summary.errors` for high-level error messages
2. Check `summary.warnings` for clock sync, timeout, or retry issues
3. Use `/logs` endpoint for full deployment trace
4. Common issues:
   - **"Missing host"**: `host` not provided in `device_connections`
   - **Clock sync warning**: reCamera via USB has no NTP — deployer syncs automatically
   - **SSH timeout**: device unreachable — verify IP and power
   - **Docker conflict**: set `auto_replace_containers: true` to replace existing containers

## 5. Complete Example

```bash
BASE=http://127.0.0.1:3260

# 1. Get deploy-info (use request_template as starting point)
curl -s "$BASE/api/solutions/recamera_heatmap_grafana/deploy-info?preset_id=grafana" \
  | python3 -m json.tool

# 2. Start deployment
DEPLOY_ID=$(curl -s -X POST "$BASE/api/deployments/start" \
  -H "Content-Type: application/json" \
  -d '{
    "solution_id": "recamera_heatmap_grafana",
    "preset_id": "grafana",
    "selected_devices": ["backend", "recamera"],
    "device_connections": {
      "backend": {},
      "recamera": {
        "host": "192.168.42.1",
        "password": "recamera"
      }
    }
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['deployment_id'])")

echo "Deployment ID: $DEPLOY_ID"

# 3. Poll until done
while true; do
  STATUS=$(curl -s "$BASE/api/deployments/$DEPLOY_ID/summary")
  echo "$STATUS" | python3 -m json.tool
  STATE=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
  [ "$STATE" = "completed" ] || [ "$STATE" = "failed" ] && break
  sleep 3
done
```

## 6. Authentication

- **localhost**: no authentication needed
- **Remote access**: add `X-API-Key: <key>` header (user configures in settings)

## 7. 镜像源自动加速 (Mirror Resolver)

部署时后端会自动探测目标设备的网络环境（Docker Hub / HuggingFace / PyPI / Debian 各 endpoint 可达性），国内不可达的源自动注入 CN mirror。**作用域仅限本次部署，不修改设备全局配置**（不改 `daemon.json` / `/etc/environment` / `sources.list`）。

覆盖的下载源：
- Docker → `docker.m.daocloud.io` 前缀（compose `image:` 字段重写到 tempfile）
- pip → `PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple`
- HuggingFace → `HF_ENDPOINT_HOST=hf-mirror.com` + `HF_ENDPOINT=https://hf-mirror.com`
- apt → `apt_extra_args` 内联 `-o Acquire::http::Proxy=...`
- npm → `NPM_CONFIG_REGISTRY=https://registry.npmmirror.com`

**配置入口**：
- 全局默认：`device_groups.yaml` 顶层 `defaults.network_region: auto | cn | global`（默认 `auto`）
- 单设备覆盖：`devices/*.yaml` 加 `network_region:` 字段
- 海外设备建议显式设 `global` 跳过探测，省 ~3s

**调试要点**：
- 部署日志关键字：`Mirror context resolved`（看到这行说明探测完成、注入生效）
- 探测失败时 fail-open（warning + 继续部署，不阻断）
- compose image 重写写到 tempfile，原 compose 文件不变（tempfile 路径在日志里）
- 私有 registry（image 含 `/` 且第一段含 `.` 或 `:`，如 `nvcr.io/...`、`192.168.1.1:5000/...`）自动跳过重写
- `compose_dir` 模式仅重写顶层 compose 文件，嵌套子目录不动
- 不接入 mirror 注入的 deployer：`nodered_deployer`（走 HTTP API）、固件烧录类（himax/esp32/recamera_cpp）、`script_deployer`
