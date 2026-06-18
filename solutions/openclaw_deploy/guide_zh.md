## 套餐: OpenClaw 算力网关 {#openclaw_basic}

部署 OpenClaw AI 消息网关，可选利用设备算力运行本地 AI 模型。

| 设备 | 用途 |
|------|------|
| reComputer Jetson | 运行 OpenClaw 网关和 GPU 加速的本地 AI 模型 |

**部署完成后你可以：**
- AI 聊天网关支持 20+ 消息平台
- 可选在设备上运行本地模型——对话数据不出内网
- 通过 Web 管理界面进行配置

**前提条件：** 已安装 Docker · 需要联网（首次下载镜像）

## 步骤 1: 部署 OpenClaw {#deploy_openclaw type=docker_deploy required=true config=devices/openclaw_deploy.yaml}

部署 OpenClaw（龙虾机器人）AI 网关。如果启用了本地模型，会自动启动并配置好。


### 部署完成

OpenClaw（龙虾机器人）AI 网关已部署完成。按照上方步骤中的"部署完成"指引登录后，即可开始使用。

#### 试试对话

1. 在左侧菜单点击 **聊天**，发送一条消息验证 AI 是否正常响应
2. 如果启用了本地模型，已自动配置好，无需额外设置

#### 连接消息平台

1. 在左侧菜单点击 **频道**，添加你的消息平台（微信、Telegram、Discord 等）
2. 按照 OpenClaw 界面中的提示完成平台授权
3. 通过已连接的平台发送一条测试消息

#### 后续步骤

- [OpenClaw 文档](https://github.com/nicepkg/openclaw)
- 在 设置 > 模型 中添加更多 AI 提供者
- 连接更多消息平台

### 部署目标 {#local type=local config=devices/openclaw_deploy.yaml default=true}

在 reComputer Jetson 设备上本地部署（需在 Jetson 上打开本软件）。

### 接线

1. 确保 Docker 已安装并运行
2. 可选勾选 **启用本地模型** 并选择模型
3. 点击 **部署** 启动服务

### 部署完成

1. 复制部署日志中显示的 **网关访问令牌（Token）**
2. 在浏览器打开 **http://localhost:18789**
3. 进入 **概览** 页面（左侧菜单 → "控制" 下的 **概览**）
4. 在 **网关访问** 区域，将 Token 粘贴到 **网关令牌** 输入框中
5. 点击 **连接** 完成认证
6. 连接你的第一个消息平台（微信、Telegram、Discord 等）
7. 如果启用了本地模型，已自动配置好——创建智能体时选择本地模型即可

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 端口 18789 被占用 | 停止占用该端口的服务，或检查 OpenClaw 是否已在运行 |
| 找不到 Docker | 安装 Docker Desktop 并确保已启动 |
| 模型下载慢 | 大模型下载需要时间，检查网络连接 |
| OpenClaw 容器反复重启 | 查看日志：`docker logs openclaw-gateway` |

### 部署目标 {#jetson_remote type=remote config=devices/openclaw_deploy.yaml}

通过 SSH 部署到 reComputer Jetson 设备，利用 GPU 加速本地模型。

### 接线

1. 将 reComputer Jetson 连接到同一局域网
2. 输入 Jetson IP 地址、SSH 用户名和密码
3. 可选勾选 **启用本地模型** 并选择模型
4. 点击 **部署** 启动服务

> 资源要求：仅 OpenClaw 需要 12GB 磁盘 + 4GB 内存；加 Ollama 需要 20GB 磁盘 + 8GB 内存。

### 部署完成

1. 复制部署日志中显示的 **网关访问令牌（Token）**
2. OpenClaw 要求通过 localhost 访问管理界面，**方式 A**：在 Jetson 上接显示器，打开浏览器访问 `http://localhost:18789`；**方式 B**：在你的电脑上运行 `ssh -L 18789:localhost:18789 <用户名>@<Jetson IP>`，然后在本地浏览器打开 `http://localhost:18789`
3. 进入 **概览** 页面（左侧菜单 → "控制" 下的 **概览**）
4. 在 **网关访问** 区域，将 Token 粘贴到 **网关令牌** 输入框中
5. 点击 **连接** 完成认证
6. 连接你的第一个消息平台
7. 如果启用了本地模型，已自动配置好并使用 GPU 加速——创建智能体时选择本地模型即可

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查 Jetson IP 地址、用户名、密码和 SSH 服务是否运行 |
| 未检测到 NVIDIA 运行时 | 确保已安装 NVIDIA 容器运行时：`nvidia-smi` 应能正常执行 |
| Docker Compose 不可用 | 安装：`sudo apt-get install -y docker-compose-plugin` |
| 模型下载慢 | 首次下载需要获取完整模型，后续使用缓存 |
| 磁盘空间不足 | 仅部署 OpenClaw 至少需要 12GB 空闲磁盘；启用 Ollama 后需要 20GB。用 `df -h /` 检查 |
| 系统内存不足 | 仅部署 OpenClaw 至少需要 4GB 内存；启用 Ollama 后需要 8GB。用 `awk '/^MemTotal:/ {print int(($2 + 1048575) / 1048576) "GB"}' /proc/meminfo` 检查 |
| 端口 11434 被占用 | 可能已有本地 AI 服务在运行，部署器会自动使用它 |

## 套餐: OpenClaw 网关 {#openclaw_recomputer_r}

在 reComputer R 系列上部署 OpenClaw AI 消息网关。轻量部署——仅网关服务，无需本地模型。

| 设备 | 用途 |
|------|------|
| reComputer R1100 / R2000 | 运行 OpenClaw 网关服务 |

**部署完成后你可以：**
- 在微信、Telegram、Discord 等 20+ 消息平台上与 AI 对话
- 通过 Web 管理界面统一管理所有渠道
- 连接云端 AI 服务（OpenAI、Claude 等）进行对话

**前提条件：** 已安装 Docker · 需要联网（首次下载镜像）

## 步骤 1: 部署 OpenClaw {#deploy_openclaw_r type=docker_deploy required=true config=devices/recomputer_r_deploy.yaml}

在 reComputer R 上部署 OpenClaw（龙虾机器人）AI 网关。


### 部署完成

OpenClaw（龙虾机器人）AI 网关已部署完成。按照上方步骤中的"部署完成"指引登录后，即可开始使用。

#### 试试对话

1. 在左侧菜单点击 **聊天**，发送一条消息验证 AI 是否正常响应
2. 如果启用了本地模型，已自动配置好，无需额外设置

#### 连接消息平台

1. 在左侧菜单点击 **频道**，添加你的消息平台（微信、Telegram、Discord 等）
2. 按照 OpenClaw 界面中的提示完成平台授权
3. 通过已连接的平台发送一条测试消息

#### 后续步骤

- [OpenClaw 文档](https://github.com/nicepkg/openclaw)
- 在 设置 > 模型 中添加更多 AI 提供者
- 连接更多消息平台

### 部署目标 {#r_local type=local config=devices/recomputer_r_deploy.yaml default=true}

部署在你当前使用的设备上。

### 接线

1. 确保 Docker 已安装并运行
2. 点击 **部署** 启动服务

### 部署完成

1. 复制部署日志中显示的 **网关访问令牌（Token）**
2. 在浏览器打开 **http://localhost:18789**
3. 进入 **概览** 页面（左侧菜单 → "控制" 下的 **概览**）
4. 在 **网关访问** 区域，将 Token 粘贴到 **网关令牌** 输入框中
5. 点击 **连接** 完成认证
6. 连接你的第一个消息平台（微信、Telegram、Discord 等）

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 端口 18789 被占用 | 停止占用该端口的服务，或检查 OpenClaw 是否已在运行 |
| 找不到 Docker | 安装 Docker Desktop 并确保已启动 |
| OpenClaw 容器反复重启 | 查看日志：`docker logs openclaw-gateway` |

### 部署目标 {#r_remote type=remote config=devices/recomputer_r_deploy.yaml}

通过 SSH 部署到 reComputer R 设备。

### 接线

1. 将 reComputer R 连接到同一局域网
2. 输入设备 IP 地址、SSH 用户名和密码
3. 点击 **部署** 启动服务

### 部署完成

1. 复制部署日志中显示的 **网关访问令牌（Token）**
2. OpenClaw 要求通过 localhost 访问管理界面，**方式 A**：在设备上接显示器，打开浏览器访问 `http://localhost:18789`；**方式 B**：在你的电脑上运行 `ssh -L 18789:localhost:18789 <用户名>@<设备 IP>`，然后在本地浏览器打开 `http://localhost:18789`
3. 进入 **概览** 页面（左侧菜单 → "控制" 下的 **概览**）
4. 在 **网关访问** 区域，将 Token 粘贴到 **网关令牌** 输入框中
5. 点击 **连接** 完成认证
6. 连接你的第一个消息平台

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查设备 IP 地址、用户名、密码和 SSH 服务是否运行 |
| Docker Compose 不可用 | 安装：`sudo apt-get install -y docker-compose-plugin` |
| 磁盘空间不足 | 至少需要 4GB 空闲空间，用 `df -h /` 检查 |
| OpenClaw 容器反复重启 | 查看日志：`docker logs openclaw-gateway` |
