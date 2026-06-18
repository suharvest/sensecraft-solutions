## 套餐: Jetson 一体化部署 {#jetson}

在单台 Jetson 上部署完整的语音对话栈。机器人能听、能想（本地 AI）、能说、能表达情绪——端到端延迟低于 1 秒。

| 设备 | 用途 |
|------|------|
| NVIDIA Jetson Orin NX 16GB | 运行 AI 对话、语音、视觉和机器人控制 |
| Reachy Mini | 带双臂、头部、天线和摄像头的桌面机器人 |

**将会部署：**
- **机器人控制** — 电机、摄像头、传感器管理
- **对话引擎** — AI 对话 + 情绪系统 + 网页仪表盘
- **视觉分析** — 人脸检测、情绪识别、人物追踪（GPU 加速）
- **Edge LLM 对话服务** — Qwen3-4B TensorRT 运行时，驱动机器人的思考能力

**前置条件：**
- Reachy Mini 通过 USB 连接到 Jetson
- Jetson 已安装 JetPack 6.x，可通过 SSH 连接，需要联网

## 步骤 1: 部署语音服务 {#speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

部署 GPU 加速的语音识别（ASR）和语音合成（TTS）服务。预构建镜像已包含所有依赖和模型，拉取后即可运行。

### 部署目标 {#speech_remote type=remote config=devices/speech_deploy.yaml default=true}

通过 SSH 一键部署到 Jetson。

### 接线

1. 将 Jetson 连接到网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 点击 **部署** — 系统会自动拉取预构建镜像并启动服务

### 部署完成

语音服务已在 `http://<jetson-ip>:8621` 运行。快速测试：

```bash
# 检查服务状态
curl http://<jetson-ip>:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 确认 IP 地址和凭据正确。先在电脑上试 `ssh 用户名@IP` |
| 镜像拉取慢 | 镜像压缩后约 8GB，确保 Jetson 网络稳定 |
| 服务未启动 | 查看日志：`ssh 用户名@IP "cd reachy-jetson-voice && docker compose logs"` |
| 健康检查失败 | 首次启动需约 40 秒预热模型，稍等后重试 |

### 部署目标 {#speech_local type=local config=devices/speech_deploy.yaml}

直接在当前机器上部署（需要 NVIDIA GPU）。

### 接线

1. 确保已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署** 开始安装

> **注意：** 首次启动可能需要 10-15 分钟下载 Docker 镜像和初始化模型。

### 部署完成

语音服务已在 `http://localhost:8621` 运行。快速测试：

```bash
# 检查服务状态
curl http://localhost:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 未找到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 8621 已被占用 | 停止占用 8621 端口的服务 |
| 容器不断重启 | 查看日志：`docker logs reachy-jetson-voice-speech-1` |
| 健康检查失败 | 首次启动需约 40 秒预热模型，稍等后重试 |

## 步骤 2: 部署 Edge LLM 对话服务 {#edge_llm_service type=docker_deploy required=true config=devices/edge_llm_deploy.yaml target_inherit_from=speech_service}

在同一台 Jetson 上部署 TensorRT 加速的 Qwen3-4B 对话服务。

### 部署目标 {#edge_llm_remote type=remote config=devices/edge_llm_deploy.yaml default=true}

通过 SSH 部署到 Jetson（凭据继承自步骤 1）。

### 接线

1. 复用步骤 1 的 SSH 凭据（部署器会自动继承）
2. 点击 **部署** — 系统会拉取预构建镜像并启动容器

> **注意：** 首次启动约需 10 分钟 — 容器会下载预构建 TensorRT engine、Qwen3-4B AWQ 权重，并运行预热推理。后续重启会很快。

### 部署完成

Edge LLM 服务运行在 `http://<jetson-ip>:11435`。快速测试：

```bash
curl http://<jetson-ip>:11435/v1/models
# 预期返回: {"object":"list","data":[{"id":"Qwen/Qwen3-4B-AWQ", ...}]}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 健康检查超时 | 首次启动需下载约 3 GB 的 engine + 权重。查看进度：`docker logs -f edge-llm-chat-service` |
| 预热阶段显存不足 | Edge LLM 需要约 6 GB GPU 显存，请关闭其他占用 GPU 的任务后重新部署 |
| `/v1/models` 返回 502 | 容器还在预热中，等日志出现 `Uvicorn running` 后重试 |

### 部署目标 {#edge_llm_local type=local config=devices/edge_llm_deploy.yaml}

直接在当前机器上部署（需要安装 JetPack 6.x 的 NVIDIA Jetson）。

### 接线

1. 确保已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署** 开始安装

> **注意：** 首次启动需约 10 分钟，用于下载 engine + 权重并完成预热推理。

### 部署完成

Edge LLM 服务运行在 `http://localhost:11435`。快速测试：

```bash
curl http://localhost:11435/v1/models
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 健康检查超时 | 首次启动需下载约 3 GB 的 engine + 权重。查看进度：`docker logs -f edge-llm-chat-service` |
| 预热阶段显存不足 | Edge LLM 需要约 6 GB GPU 显存，请关闭其他占用 GPU 的任务后重新部署 |

## 步骤 3: 部署 Reachy 语音机器人 {#reachy_deploy type=docker_deploy required=true config=devices/reachy_jetson_deploy.yaml target_inherit_from=speech_service}

将机器人控制、对话和视觉服务部署到 Jetson。对话引擎会消费步骤 2 部署的 Edge LLM 服务。


### 部署完成

你的 Reachy Mini 语音机器人已经在运行了！

#### 当前状态

机器人默认运行在**对话模式** — 它会聆听并回应。你跟它说话，它就用一句简短的话回复，并配合相应的情绪和头部/天线动作。无需任何设置，直接说话即可。

#### 服务概览

| 服务 | 端口 | 用途 |
|------|------|------|
| 机器人控制 | 38001 | 电机、摄像头、传感器管理 |
| 对话引擎 | 8640 | AI 对话 + 情绪系统 + 仪表盘 |
| 视觉分析 | 8630 | 人脸检测、情绪识别、人物追踪 |
| Edge LLM 对话服务 | 11435 | Qwen3-4B-AWQ TensorRT — 驱动机器人的思考能力 |
| 语音服务 | 8621 | 听懂你说的话 + 说话给你听（步骤 1 部署） |

#### 后续操作

- 打开**仪表盘** `http://<jetson-ip>:8640` 查看对话日志和机器人状态
- 调整机器人的人格和行为，在 Jetson 上编辑配置中的 `llm.system_prompt`：
  ```bash
  ssh user@<jetson-ip>
  nano ~/reachy-jetson-llm/reachy-claw.jetson.yaml
  # 编辑 llm.system_prompt 改变机器人的说话方式
  docker restart reachy-claw
  ```
- 如需启用可选的待机自言自语（自白模式），在同一配置中设置 `conversation.mode: monologue`，然后 `docker restart reachy-claw`。

### 部署目标 {#reachy_remote type=remote config=devices/reachy_jetson_deploy.yaml default=true}

通过 SSH 一键部署到 Jetson。

### 接线

1. 用 USB 线将 Reachy Mini 连接到 Jetson
2. 确保 Jetson 已联网且 SSH 可访问
3. 输入 Jetson 的 IP 地址和 SSH 凭证
4. 配置数据目录（默认：`~/reachy-data`），用于存储截图和人脸数据库
5. 可选启用**全屏展示模式**，设备开机后自动全屏打开仪表盘
6. 点击 **部署** — 系统会拉取并启动机器人控制、对话和视觉（TensorRT GPU 加速）服务。步骤 2 的 Edge LLM 服务必须已经在运行。

### 部署完成

部署完成后约 30 秒，机器人即可就绪。打开仪表盘监控状态：

```
http://<jetson-ip>:8640
```

**默认模式：** 对话模式 — 机器人聆听并回应。你跟它说话，它就用一句简短的话回复，并配合相应的情绪和头部/天线动作。（如需可选的待机自言自语，可设置 `conversation.mode: monologue`，机器人会每隔约 30 秒自言自语一次。）

检查所有服务是否运行：
```bash
ssh user@<jetson-ip> "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 对话响应慢（>10 秒） | Edge LLM 容器状态异常。检查：`docker logs edge-llm-chat-service` 与 `curl http://<jetson-ip>:11435/v1/models` |
| 机器人不动 | 检查 USB 连接。现在已有 udev 规则在机器人插入时自动重连 daemon；如仍不动，重新插拔 USB 线后重启：`docker restart reachy-daemon` |
| 没有声音 | 检查 Reachy Mini 内置扬声器是否正常。检查配置中的 `audio.device` |
| 仪表盘打不开 | 等待 30 秒让服务启动。检查：`curl http://<jetson-ip>:8640/health` |
| 没有摄像头画面 | 视觉服务首次启动需构建 TRT 引擎（约 5 分钟）。检查：`docker logs vision-trt` |
| 开机后摄像头未找到 | USB 摄像头枚举需要 15-30 秒，视觉服务会自动重试（约 90 秒） |
| 摄像头运行一段时间后失联 | USB 电源管理问题。部署已通过 udev 规则禁用自动挂起，如仍然复发请物理拔插 Reachy USB 线 |

### 部署目标 {#reachy_local type=local config=devices/reachy_jetson_deploy.yaml}

直接在当前机器上部署（需要已连接 Reachy Mini 的 NVIDIA Jetson 设备）。

### 接线

1. 用 USB 线将 Reachy Mini 连接到机器
2. 确保已安装 Docker 和 NVIDIA Container Toolkit
3. 点击 **部署** 开始安装

> **注意：** 首次启动可能需要 5-10 分钟下载 Docker 镜像和初始化模型。

### 部署完成

部署完成后约 30 秒，机器人就会开始说话。打开仪表盘监控状态：

```
http://localhost:8640
```

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 未找到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 机器人不动 | 检查 USB 连接。尝试重新插拔 USB 线后重启：`docker restart reachy-daemon` |
| 仪表盘打不开 | 等待 30 秒让服务启动。检查：`curl http://localhost:8640/health` |
| 没有摄像头画面 | 视觉服务首次启动需构建 TRT 引擎（约 5 分钟）。检查：`docker logs vision-trt` |

## 套餐: R2000 + Hailo-8 {#r2000_hailo}

在单台 R2000（树莓派 5 + Hailo-8）上部署完整的 Reachy 语音机器人栈。视觉跑在 Hailo NPU 上，语音和 LLM 通过远程 Jetson 语音助手提供。

| 设备 | 用途 |
|------|------|
| reComputer R2000（Pi 5 + Hailo-8） | 机器人控制、对话、Hailo 加速视觉 |
| Reachy Mini | 通过 USB 连接到 R2000 的桌面机器人 |
| Jetson（远程） | 语音（ASR/TTS）+ Edge LLM（TensorRT-Edge-LLM）——在步骤 1 中部署 |

**将会部署：**
- **机器人控制** — 电机、摄像头、传感器管理
- **对话引擎** — AI 对话 + 情绪系统 + 网页仪表盘
- **视觉分析** — 人脸检测、情绪识别、人物追踪（Hailo-8 NPU）

**前置条件：**
- Reachy Mini 通过 USB 连接到 R2000
- USB 摄像头接在 R2000 上
- Hailo-8 AI HAT 已插入 M.2 插槽，`/boot/firmware/config.txt` 已启用 PCIe Gen3
- Jetson 设备已安装 JetPack 6.x，可通过 SSH 连接，需要联网（语音服务将在步骤 1 中部署）

## 步骤 1: 部署语音服务 {#hailo_speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

在 Jetson 上部署 GPU 加速的语音识别（ASR）和语音合成（TTS）服务。预构建镜像已包含所有依赖和模型，拉取后即可运行。

### 部署目标 {#hailo_speech_remote type=remote config=devices/speech_deploy.yaml default=true}

通过 SSH 一键部署到 Jetson。

### 接线

1. 将 Jetson 连接到网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 点击 **部署** — 系统会自动拉取预构建镜像并启动服务

### 部署完成

语音服务已在 `http://<jetson-ip>:8621` 运行。快速测试：

```bash
# 检查服务状态
curl http://<jetson-ip>:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 确认 IP 地址和凭据正确。先在电脑上试 `ssh 用户名@IP` |
| 镜像拉取慢 | 镜像压缩后约 8GB，确保 Jetson 网络稳定 |
| 服务未启动 | 查看日志：`ssh 用户名@IP "cd reachy-jetson-voice && docker compose logs"` |
| 健康检查失败 | 首次启动需约 40 秒预热模型，稍等后重试 |

### 部署目标 {#hailo_speech_local type=local config=devices/speech_deploy.yaml}

直接在当前机器上部署（需要 NVIDIA GPU）。

### 接线

1. 确保已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署** 开始安装

> **注意：** 首次启动可能需要 10-15 分钟下载 Docker 镜像和初始化模型。

### 部署完成

语音服务已在 `http://localhost:8621` 运行。快速测试：

```bash
# 检查服务状态
curl http://localhost:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 未找到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 8621 已被占用 | 停止占用 8621 端口的服务 |
| 容器不断重启 | 查看日志：`docker logs reachy-jetson-voice-speech-1` |
| 健康检查失败 | 首次启动需约 40 秒预热模型，稍等后重试 |

## 步骤 2: 部署 Reachy 语音机器人（Hailo） {#reachy_hailo_deploy type=docker_deploy required=true config=devices/reachy_hailo_deploy.yaml target_inherit_from=hailo_speech_service}

将机器人控制、对话和 Hailo 加速的视觉服务一步部署到 R2000。部署器会在缺失时自动安装 Hailo 栈。


### 部署完成

你的 Reachy Mini 语音机器人已经在运行了！

#### 当前状态

机器人默认运行在**对话模式** — 它会聆听并回应。你跟它说话，它就用一句简短的话回复，并配合相应的情绪和头部/天线动作。无需任何设置，直接说话即可。

#### 服务概览

| 服务 | 端口 | 用途 |
|------|------|------|
| 机器人控制 | 38001 | 电机、摄像头、传感器管理 |
| 对话引擎 | 8640 | AI 对话 + 情绪系统 + 仪表盘 |
| 视觉分析 | 8630 | 人脸检测、情绪识别、人物追踪 |
| Edge LLM（远程 Jetson） | 11435 | Qwen3-4B-AWQ TensorRT — 驱动机器人的思考能力 |
| 语音服务 | 8621 | 听懂你说的话 + 说话给你听（步骤 1 部署） |

#### 后续操作

- 打开**仪表盘** `http://<r2000-ip>:8640` 查看对话日志和机器人状态
- 调整机器人的人格和行为，编辑配置中的 `llm.system_prompt`：
  ```bash
  ssh pi@<r2000-ip>
  nano ~/reachy-jetson-llm/reachy-claw.jetson.yaml
  # 编辑 llm.system_prompt 改变机器人的说话方式
  docker restart reachy-claw
  ```
- AI 模型由远程 Jetson 上的 Edge LLM 服务（`edge-llm-chat-service`，Qwen/Qwen3-4B-AWQ）提供，不再使用 Ollama。要改变机器人的行为，请编辑上面的 `llm.system_prompt`，而不是更换模型。
- 如需启用可选的待机自言自语（自白模式），在同一配置中设置 `conversation.mode: monologue`，然后 `docker restart reachy-claw`。

### 部署目标 {#reachy_hailo_remote type=remote config=devices/reachy_hailo_deploy.yaml default=true}

通过 SSH 一键部署到 R2000。

### 接线

1. 用 USB 线将 Reachy Mini 连接到 R2000
2. 将 USB 摄像头插入 R2000
3. 确保 R2000 已联网且 SSH 可访问
4. 输入 R2000 的 IP 地址和 SSH 凭据（默认用户名: `pi`）
5. 输入**语音助手主机**——运行语音 + LLM 的 Jetson IP（例如 `192.168.1.100`）
6. 配置数据目录（默认: `~/reachy-data`）
7. 可选启用**全屏展示模式**，设备开机后自动全屏打开仪表盘
8. 点击**部署**——系统会：
   - 检测并在缺失时安装 Hailo 栈（驱动 + 用户态）
   - 拉取并启动机器人控制、对话和 Hailo 加速的视觉服务

### 部署完成

部署完成后约 30 秒，机器人就会开始说话。打开仪表盘：

```
http://<r2000-ip>:8640
```

验证所有服务：
```bash
ssh pi@<r2000-ip> "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| `/dev/hailo0` 找不到 | 重新插紧 M.2 槽位上的 Hailo HAT，重启后重试。`lspci \| grep -i hailo` 查 PCIe 识别 |
| `hailo-all` 安装失败 | 手动添加 Hailo apt 源——见 `vision-hailo` 仓库的 `INSTALL.md` |
| 容器报版本不匹配 | 宿主机驱动和容器内用户态版本必须一致：`sudo apt install --reinstall hailo-all` 后重新部署 |
| FPS 低于 5 | 检查 CPU 频率：设置 scaling governor 为 `performance` |
| 仪表盘上没有人脸数据 | 验证视觉服务：`curl http://localhost:8630/` |
| 语音不工作 | 验证 VOICE_ASSISTANT_HOST 可访问：`curl http://<jetson-ip>:8621/health` |
| 机器人不动 | 检查 USB 连接。尝试重新插拔后重启：`docker restart reachy-daemon` |

### 部署目标 {#reachy_hailo_local type=local config=devices/reachy_hailo_deploy.yaml}

直接在当前机器上部署（需要 R2000 + Hailo-8，Reachy Mini 通过 USB 连接）。

### 接线

1. 用 USB 线将 Reachy Mini 连接到机器
2. 确保已安装 Docker
3. 点击 **部署** 开始安装

> **注意：** 首次启动可能需要 5-10 分钟下载 Docker 镜像。

### 部署完成

部署完成后约 30 秒，机器人就会开始说话。打开仪表盘：

```
http://localhost:8640
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| `/dev/hailo0` 找不到 | 重新插紧 M.2 槽位上的 Hailo HAT，重启后重试 |
| 机器人不动 | 检查 USB 连接。尝试重新插拔后重启：`docker restart reachy-daemon` |
| 仪表盘打不开 | 等待 30 秒让服务启动。检查：`curl http://localhost:8640/health` |

# 服务总览（R2000 套餐）

| 服务 | 主机 | 端口 | 作用 |
|------|------|------|------|
| 语音服务 | Jetson（远程） | 8621 | ASR + TTS |
| Edge LLM | Jetson（远程） | 11435 | TensorRT-Edge-LLM（Qwen/Qwen3-4B-AWQ） |
| 机器人控制 | R2000 | 38001 | Reachy daemon（电机） |
| 对话引擎 | R2000 | 8640 | 对话 + 仪表盘 |
| 视觉（Hailo） | R2000 | 8630 / 8631 | 人脸检测 + 情绪识别 + 追踪 |

---

## 套餐: Reachy Mini Wireless（CM4） {#cm4}

在 Reachy Mini Wireless CM4 上部署完整的 Reachy 语音机器人栈。视觉跑在 CM4 的 CPU 上，语音和 LLM 通过远程 Jetson 语音助手提供。

| 设备 | 用途 |
|------|------|
| Reachy Mini Wireless（CM4） | 机器人控制、对话、CPU 视觉 |
| Jetson（远程） | 语音（ASR/TTS）+ Edge LLM（TensorRT-Edge-LLM）——在步骤 1 中部署 |

**将会部署：**
- **机器人控制** — 电机、摄像头、传感器管理
- **对话引擎** — AI 对话 + 情绪系统 + 网页仪表盘
- **视觉分析** — 人脸检测、情绪识别、人物追踪（CPU）

**前置条件：**
- Reachy Mini Wireless 自带 CM4
- CM4 上已安装 Docker
- Jetson 设备已安装 JetPack 6.x，可通过 SSH 连接，需要联网（语音服务将在步骤 1 中部署）

## 步骤 1: 部署语音服务 {#cm4_speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

在 Jetson 上部署 GPU 加速的语音识别（ASR）和语音合成（TTS）服务。预构建镜像已包含所有依赖和模型，拉取后即可运行。

### 部署目标 {#cm4_speech_remote type=remote config=devices/speech_deploy.yaml default=true}

通过 SSH 一键部署到 Jetson。

### 接线

1. 将 Jetson 连接到网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 点击 **部署** — 系统会自动拉取预构建镜像并启动服务

### 部署完成

语音服务已在 `http://<jetson-ip>:8621` 运行。快速测试：

```bash
# 检查服务状态
curl http://<jetson-ip>:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 确认 IP 地址和凭据正确。先在电脑上试 `ssh 用户名@IP` |
| 镜像拉取慢 | 镜像压缩后约 8GB，确保 Jetson 网络稳定 |
| 服务未启动 | 查看日志：`ssh 用户名@IP "cd reachy-jetson-voice && docker compose logs"` |
| 健康检查失败 | 首次启动需约 40 秒预热模型，稍等后重试 |

### 部署目标 {#cm4_speech_local type=local config=devices/speech_deploy.yaml}

直接在当前机器上部署（需要 NVIDIA GPU）。

### 接线

1. 确保已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署** 开始安装

> **注意：** 首次启动可能需要 10-15 分钟下载 Docker 镜像和初始化模型。

### 部署完成

语音服务已在 `http://localhost:8621` 运行。快速测试：

```bash
# 检查服务状态
curl http://localhost:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 未找到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 8621 已被占用 | 停止占用 8621 端口的服务 |
| 容器不断重启 | 查看日志：`docker logs reachy-jetson-voice-speech-1` |
| 健康检查失败 | 首次启动需约 40 秒预热模型，稍等后重试 |

## 步骤 2: 部署 Reachy 语音机器人（CM4） {#reachy_cm4_deploy type=docker_deploy required=true config=devices/reachy_cm4_deploy.yaml target_inherit_from=cm4_speech_service}

将机器人控制、对话和视觉服务一步部署到 CM4。


### 部署完成

你的 Reachy Mini 语音机器人已经在运行了！

#### 当前状态

机器人默认运行在**对话模式** — 它会聆听并回应。你跟它说话，它就用一句简短的话回复，并配合相应的情绪和头部/天线动作。无需任何设置，直接说话即可。

#### 服务概览

| 服务 | 端口 | 用途 |
|------|------|------|
| 机器人控制 | 38001 | 电机、摄像头、传感器管理 |
| 对话引擎 | 8640 | AI 对话 + 情绪系统 + 仪表盘 |
| 视觉分析 | 8630 | 人脸检测、情绪识别、人物追踪 |
| Edge LLM（远程 Jetson） | 11435 | Qwen3-4B-AWQ TensorRT — 驱动机器人的思考能力 |
| 语音服务 | 8621 | 听懂你说的话 + 说话给你听（步骤 1 部署） |

#### 后续操作

- 打开**仪表盘** `http://<cm4-ip>:8640` 查看对话日志和机器人状态
- 调整机器人的人格和行为，编辑配置中的 `llm.system_prompt`：
  ```bash
  ssh pi@<cm4-ip>
  nano ~/reachy-jetson-llm/reachy-claw.jetson.yaml
  # 编辑 llm.system_prompt 改变机器人的说话方式
  docker restart reachy-claw
  ```
- AI 模型由远程 Jetson 上的 Edge LLM 服务（`edge-llm-chat-service`，Qwen/Qwen3-4B-AWQ）提供，不再使用 Ollama。要改变机器人的行为，请编辑上面的 `llm.system_prompt`，而不是更换模型。
- 如需启用可选的待机自言自语（自白模式），在同一配置中设置 `conversation.mode: monologue`，然后 `docker restart reachy-claw`。

### 部署目标 {#reachy_cm4_remote type=remote config=devices/reachy_cm4_deploy.yaml default=true}

通过 SSH 一键部署到 CM4。

### 接线

1. 确保 CM4 已联网且 SSH 可访问
2. 输入 CM4 的 IP 地址和 SSH 凭据（默认用户名: `pi`）
3. 输入**语音助手主机**——运行语音 + LLM 的 Jetson IP（例如 `192.168.1.100`）
4. 配置数据目录（默认: `~/reachy-data`）
5. 可选启用**全屏展示模式**，设备开机后自动全屏打开仪表盘
6. 点击**部署**——系统会拉取并启动所有服务

### 部署完成

部署完成后约 30 秒，机器人就会开始说话。打开仪表盘：

```
http://<cm4-ip>:8640
```

验证所有服务：
```bash
ssh pi@<cm4-ip> "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| Docker 未安装 | 通过 get.docker.com 官方脚本安装 |
| 语音不工作 | 验证 VOICE_ASSISTANT_HOST 可访问：`curl http://<jetson-ip>:8621/health` |
| 没有摄像头画面 | 检查：`ls /dev/video*`。如果为空，重新插拔 USB 摄像头 |
| 机器人不动 | 检查 USB 连接。尝试重新插拔后重启：`docker restart reachy-daemon` |
| 仪表盘打不开 | 等待 30 秒让服务启动。检查：`curl http://localhost:8640/health` |

### 部署目标 {#reachy_cm4_local type=local config=devices/reachy_cm4_deploy.yaml}

直接在 Reachy Mini Wireless CM4 上部署。

### 接线

1. 确保 CM4 上已安装 Docker
2. 点击 **部署** 开始安装

> **注意：** 首次启动可能需要 5-10 分钟下载 Docker 镜像。

### 部署完成

部署完成后约 30 秒，机器人就会开始说话。打开仪表盘：

```
http://localhost:8640
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| Docker 未安装 | 通过 get.docker.com 官方脚本安装 |
| 机器人不动 | 检查 USB 连接。尝试重新插拔后重启：`docker restart reachy-daemon` |
| 仪表盘打不开 | 等待 30 秒让服务启动。检查：`curl http://localhost:8640/health` |

# 服务总览（CM4 套餐）

| 服务 | 主机 | 端口 | 作用 |
|------|------|------|------|
| 语音服务 | Jetson（远程） | 8621 | ASR + TTS |
| Edge LLM | Jetson（远程） | 11435 | TensorRT-Edge-LLM（Qwen/Qwen3-4B-AWQ） |
| 机器人控制 | CM4 | 38001 | Reachy daemon（电机） |
| 对话引擎 | CM4 | 8640 | 对话 + 仪表盘 |
| 视觉（CM4） | CM4 | 8630 / 8631 | 人脸检测 + 情绪识别 + 追踪 |
