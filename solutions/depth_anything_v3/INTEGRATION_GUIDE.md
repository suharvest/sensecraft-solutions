# SenseCraft Solution for reComputer

## 简介

本文是一份“从已有 Docker 镜像项目接入 SenseCraft Solution App”的完整实操文档。  
目标读者是：你已经有一个可在 reComputer/Jetson 上运行的镜像和启动命令，希望把它接入本仓库 `solutions/`，让用户在前端页面中完成：

1. 填写设备连接信息
2. 点击 Deploy 一键部署
3. （可选）点击 Preview 查看推流画面

本文以已经适配成功的 `depth_anything_v3` 为参考样例，但内容设计为通用流程，你可以直接复用到自己的方案。

---

## 核心步骤

1. 新增 solution 目录与基础文件
2. 配置 `solution.yaml`（方案元数据）
3. 编写 `guide.md / guide_zh.md`（部署步骤与前端展示结构）
4. 绑定 `docker_deploy` + `remote/local target`
5. 配置 `devices/*.yaml`（连接参数、部署行为、预检查）
6. 完善 `assets/*/docker-compose.yml`（把 docker run 迁移为 compose）
7. （可选）增加 `preview` 步骤与 `devices/preview.yaml`
8. 本地启动与验证（前端、API、部署链路）
9. 常见问题排查

---

## 目录结构（以 depth_anything_v3 为例）

```text
solutions/depth_anything_v3/
├── solution.yaml
├── description.md
├── description_zh.md
├── guide.md
├── guide_zh.md
├── devices/
│   ├── jetson.yaml
│   └── preview.yaml              # 可选：需要预览才添加
├── assets/
│   └── jetson/
│       └── docker-compose.yml
├── gallery/
│   ├── da3.png
│   └── engine.png
└── INTEGRATION_GUIDE.md
```

---

## Step 1: 新增 solution

先创建目录（将 `your_solution_id` 替换为你的方案 ID）：

```bash
mkdir -p solutions/your_solution_id/{devices,assets/jetson,gallery}
```

最少需要的文件：

- `solution.yaml`
- `description.md`
- `description_zh.md`
- `guide.md`
- `guide_zh.md`
- `devices/jetson.yaml`
- `assets/jetson/docker-compose.yml`

可选文件（需要预览才添加）：

- `devices/preview.yaml`

---

## Step 2: 配置 solution.yaml

`solution.yaml` 负责“方案卡片和预设信息”，不是具体部署命令执行文件。  
建议先复制 `depth_anything_v3/solution.yaml`，再替换字段。

### 必填字段清单

- `id`: 方案唯一 ID，建议 `^[a-z][a-z0-9_]*$`
- `name` / `name_zh`
- `intro.summary` / `intro.summary_zh`
- `intro.description_file` / `intro.description_file_zh`
- `intro.presets[]`
- `deployment.guide_file` / `deployment.guide_file_zh`

### 最小模板示例

```yaml
version: "1.0"
id: your_solution_id
name: Your Solution Name
name_zh: 你的方案名

intro:
  summary: One-click deployment for your containerized Jetson app.
  summary_zh: 一键部署你的 Jetson 容器化应用。
  description_file: description.md
  description_file_zh: description_zh.md
  cover_image: gallery/cover.png
  category: vision
  tags: [jetson, docker, edge-ai]

  device_catalog:
    recomputer_j4012:
      name: reComputer J4012
      name_zh: reComputer J4012
      product_url: https://www.seeedstudio.com/
      description: Edge AI computer for your workload
      description_zh: 运行你的边缘 AI 工作负载

  presets:
    - id: jetson_default
      name: Jetson Default Preset
      name_zh: Jetson 默认套餐
      description: Deploy to Jetson through SSH.
      description_zh: 通过 SSH 部署到 Jetson。
      device_groups:
        - id: edge_device
          name: Edge Device
          name_zh: 边缘设备
          type: single
          required: true
          options:
            - device_ref: recomputer_j4012
          default: recomputer_j4012

deployment:
  guide_file: guide.md
  guide_file_zh: guide_zh.md
  selection_mode: sequential
```

---

## Step 3: 编写 guide.md / guide_zh.md

这两个文件决定了前端部署页如何渲染“步骤、目标、接线、故障排查”等内容。  
建议把部署逻辑拆成两个步骤：

1. `docker_deploy`：部署容器
2. `preview`（可选）：输入 RTSP 地址并查看画面

### 3.1 关键语法（必须符合）

Preset 头：

- `## Preset: ... {#preset_id}`
- `## 套餐: ... {#preset_id}`

Step 头：

- `## Step 1: ... {#step_id type=docker_deploy required=true config=devices/jetson.yaml}`
- `## 步骤 1: ... {#step_id type=docker_deploy required=true config=devices/jetson.yaml}`

Target 头（用于 docker_deploy）：

- `### Target: Remote Deployment {... type=remote ... default=true}`
- `### 部署目标: 远程部署 {... type=remote ... default=true}`

### 3.2 中英文一致性要求

`guide.md` 和 `guide_zh.md` 必须保持：

- preset ID 一致
- step ID 一致
- step type / required / config 一致
- target ID 一致

只翻译文本，不要改 `{#...}` 元数据。

### 3.3 示例（英文）

```markdown
## Preset: Jetson Default Preset {#jetson_default}

## Step 1: Deploy Application {#deploy_app type=docker_deploy required=true config=devices/jetson.yaml}

### Target: Remote Deployment (Jetson) {#jetson_remote type=remote config=devices/jetson.yaml default=true}

### Wiring
1. Connect Jetson and your PC to the same network.
2. Fill in host/username/password.
3. Click Deploy.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| SSH failed | Check IP and credential |
| Docker unavailable | Install/start Docker |

## Step 2: Preview Stream {#preview_stream type=preview required=false config=devices/preview.yaml}
...
```

---

## Step 4: 绑定 docker_deploy / local deploy / remote deploy

在本项目中，推荐统一使用 `type=docker_deploy`，再通过 `Target` 区分 local/remote。  
`depth_anything_v3` 当前主路径是 remote（Jetson）。

### 推荐策略

- 只有 Jetson 远程部署场景：保留 1 个 remote target
- 同时支持本机调试：增加 local target，并指向 `devices/local.yaml`

### Target 配置示例

```markdown
### Target: Local Deployment {#local type=local config=devices/local.yaml}
### Target: Remote Deployment {#remote type=remote config=devices/jetson.yaml default=true}
```

---

## Step 5: 提供配置信息（devices/jetson.yaml）

`devices/jetson.yaml` 是部署执行核心，建议从 `depth_anything_v3/devices/jetson.yaml` 复制后改造。

### 5.1 你需要暴露给用户的输入项

最常用：

- `host`: Jetson IP
- `username`: SSH 用户名
- `password`: SSH 密码
- `display`: X11 DISPLAY（可选）

按需扩展：

- 编码器、帧率、码率
- 模型参数
- 业务开关（例如是否启用某服务）

### 5.2 docker_remote 核心字段

- `compose_file`: Compose 文件相对路径
- `compose_dir`: 需要一起上传的目录
- `remote_path`: 远端目录模板（可含 `{{username}}`）
- `environment`: 注入容器环境变量
- `options.project_name`
- `options.remove_orphans`

### 5.3 建议保留的 before actions

1. Jetson 基础检测（`/etc/nv_tegra_release`）
2. Docker 可用性检测（`docker info`）
3. NVIDIA runtime 检测
4. Docker Compose 兼容检测与自动安装回退  
   （`docker compose` + `docker-compose` 双路径）

---

## Step 6: 完善 compose 资产

你的用户一般会提供：

- `docker pull ...`
- `docker run ...`
- 容器内应用启动命令（例如 `./run_xxx.sh`）

你需要把它们迁移到 `assets/jetson/docker-compose.yml`。

### 6.1 迁移映射表（docker run -> compose）

| docker run 参数 | compose 对应 |
|---|---|
| `--gpus all` | `runtime: nvidia` + NVIDIA 环境变量 |
| `--network host` | `network_mode: host` |
| `--ipc host` | `ipc: host` |
| `--privileged` | `privileged: true` |
| `-e KEY=VAL` | `environment: - KEY=VAL` |
| `-v src:dst` | `volumes: - src:dst` |
| 镜像名 | `image:` |
| 容器内命令 | `command:` |

### 6.2 示例（和 depth_anything_v3 同类）

```yaml
services:
  your_service:
    image: your_repo/your_image:tag
    container_name: your_solution_id
    restart: unless-stopped
    runtime: nvidia
    network_mode: host
    ipc: host
    privileged: true
    stdin_open: true
    tty: true
    environment:
      - DISPLAY=${DISPLAY:-:0}
      - QT_X11_NO_MITSHM=1
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=all
    volumes:
      - /tmp/.X11-unix:/tmp/.X11-unix
      - /dev:/dev
    command:
      - bash
      - -lc
      - |
        cd /your/workdir
        ./your_start_command.sh
```

---

## Step 7: 可选 Preview 集成（强烈推荐）

如果你的应用会输出 RTSP（例如 `rtsp://<jetson-ip>:8554/xxx`），建议加 preview 步骤。

### 7.1 新增 devices/preview.yaml

最小示例：

```yaml
version: "1.0"
id: preview_stream
name: Stream Preview
name_zh: 画面预览
type: preview

video:
  type: rtsp_proxy

display:
  aspect_ratio: "16:9"
  auto_start: false
  show_stats: true

user_inputs:
  - id: rtsp_url
    name: RTSP URL
    name_zh: RTSP 地址
    type: text
    required: true
    default_template: "rtsp://{{host}}:8554/depth"
```

### 7.2 在 guide 中增加 Step 2

```markdown
## Step 2: Preview Stream {#preview_stream type=preview required=false config=devices/preview.yaml}
```

---

## Step 8: 本地验证流程（必须做）

### 8.1 启动服务

```bat
dev-stop.bat
dev.bat
```

### 8.2 API 验证

```powershell
curl http://127.0.0.1:3260/api/health
curl http://127.0.0.1:3260/api/solutions/your_solution_id?lang=en
curl "http://127.0.0.1:3260/api/solutions/your_solution_id/deploy-info?lang=en"
```

### 8.3 前端验证

1. 打开部署页
2. 选择你的方案
3. 检查 step/target 是否正确显示
4. 输入 SSH 参数并部署
5. 若有 preview，输入 RTSP 地址后点击 Connect

---

## Step 9: 常见问题排查

### 9.1 方案不显示

检查：

1. `solution.yaml` 是否格式正确
2. `id` 是否合法
3. 后端是否已重启并重新加载 solutions

### 9.2 进入部署页时报错

检查：

1. `guide.md` / `guide_zh.md` 元数据头是否规范
2. `config=devices/xxx.yaml` 是否存在
3. 中英文 ID 是否一致

### 9.3 远程部署失败

检查：

1. SSH 连通性（IP/账号/密码/端口）
2. Jetson Docker 是否可用
3. NVIDIA runtime 是否可用
4. Docker Compose 是否可用（`docker compose` 或 `docker-compose`）

### 9.4 Preview 失败

检查：

1. RTSP 地址是否可达（先用 VLC/ffplay 测）
2. RTSP 端口是否开放
3. 本机 FFmpeg 是否可用

---

## 用户提交材料清单（给“已有镜像”的用户）

请让用户至少提供以下信息：

1. 镜像地址  
   例如：`docker pull your_repo/your_image:tag`
2. 启动参数（docker run）  
   包含 `--network`、`--ipc`、`--privileged`、`-e`、`-v` 等
3. 容器内启动命令  
   例如：`cd /workspace && ./run_xxx.sh`
4. 是否需要摄像头  
   必需 / 可选 / 不需要
5. 是否需要推流预览  
   若需要，提供 RTSP 格式、端口、路径
6. 默认账户信息（如有）  
   SSH 用户名、默认端口、默认密码策略

---

## 建议的“最小可交付”标准

完成以下条件后，再提交 PR：

1. 方案卡片可在前端显示
2. Deploy 步骤可执行且日志可追踪
3. Docker 容器可稳定启动
4. 预检查失败信息可读（不是黑盒报错）
5. 如有 Preview，能看到画面或得到明确错误信息

---

## 参考：depth_anything_v3 的关键实现位置

- 方案元信息：`solutions/depth_anything_v3/solution.yaml`
- 部署文档：`solutions/depth_anything_v3/guide.md`
- 设备部署配置：`solutions/depth_anything_v3/devices/jetson.yaml`
- 预览配置：`solutions/depth_anything_v3/devices/preview.yaml`
- Compose 资产：`solutions/depth_anything_v3/assets/jetson/docker-compose.yml`

你可以把 `depth_anything_v3` 当作模板，复制后替换以下内容：

1. `solution.yaml` 的 `id/name/summary/presets`
2. `docker-compose.yml` 的镜像、命令、环境变量
3. `jetson.yaml` 的输入项和 before-actions
4. `guide.md / guide_zh.md` 的业务步骤文案

