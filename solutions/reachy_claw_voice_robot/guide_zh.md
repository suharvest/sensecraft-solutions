## 套餐: Jetson 一体化部署 {#jetson}

语音识别与合成、本地大模型、视觉和机器人控制都部署在一台 Jetson 上。

- **机器人：** Reachy Mini 通过 USB 连接到 Jetson。
- **网络：** Jetson 可通过 SSH 访问，部署时需要联网拉取镜像。

## 步骤 1: 部署语音服务 {#speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

部署语音识别（ASR）和语音合成（TTS）服务，镜像已包含模型。

### 部署目标 {#speech_remote type=remote config=devices/speech_deploy.yaml default=true}

通过 SSH 部署到 Jetson Orin NX 16GB，设备须为 JetPack 6.x。

### 接线

1. 将 Jetson 连接到网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 点击 **部署**

### 部署完成

访问 `http://<jetson-ip>:8621/health`，返回 `{"asr": true, "tts": true, "streaming_asr": true}`。

### 故障排查

| 现象 | 处理 |
|------|----------|
| SSH 连接失败 | 在电脑上先试 `ssh 用户名@IP`，确认 IP 和凭据 |
| 镜像拉取慢 | 镜像压缩后约 8 GB，确保 Jetson 网络稳定 |
| 服务未启动 | 执行 `ssh 用户名@IP "cd reachy-jetson-voice && docker compose logs"` 查看日志 |
| 健康检查失败 | 首次启动约 40 秒预热模型，稍等后重试 |

### 部署目标 {#speech_local type=local config=devices/speech_deploy.yaml}

部署到本机，本机须有 NVIDIA GPU，已安装 Docker 和 NVIDIA Container Toolkit。

### 接线

1. 点击 **部署**，首次下载镜像和初始化模型需要 10-15 分钟

### 部署完成

访问 `http://localhost:8621/health`，返回 `{"asr": true, "tts": true, "streaming_asr": true}`。

### 故障排查

| 现象 | 处理 |
|------|----------|
| 未找到 NVIDIA 运行时 | 执行 `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 8621 已被占用 | 停止占用 8621 端口的服务 |
| 容器不断重启 | 执行 `docker logs reachy-jetson-voice-speech-1` 查看日志 |
| 健康检查失败 | 首次启动约 40 秒预热模型，稍等后重试 |

## 步骤 2: 部署 Edge LLM 对话服务 {#edge_llm_service type=docker_deploy required=true config=devices/edge_llm_deploy.yaml target_inherit_from=speech_service}

在同一台 Jetson 上部署 Qwen3.5-4B 对话服务。首次启动约 10 分钟，需要下载约 3 GB 模型并预热，占用约 6 GB 显存。

### 部署目标 {#edge_llm_remote type=remote config=devices/edge_llm_deploy.yaml default=true}

通过 SSH 部署到步骤 1 的 Jetson，SSH 凭据自动沿用。

### 接线

1. 点击 **部署**

### 部署完成

访问 `http://<jetson-ip>:11435/v1/models`，返回的模型列表含 `Qwen/Qwen3-4B-AWQ`。

### 故障排查

| 现象 | 处理 |
|------|----------|
| 健康检查超时 | 执行 `docker logs -f edge-llm-chat-service` 查看下载进度 |
| 预热阶段显存不足 | 关闭其他占用 GPU 的任务后重新部署 |
| `/v1/models` 返回 502 | 等日志出现 `Uvicorn running` 后重试 |

### 部署目标 {#edge_llm_local type=local config=devices/edge_llm_deploy.yaml}

部署到本机，本机须为 JetPack 6.x 的 Jetson，已安装 Docker 和 NVIDIA Container Toolkit。

### 接线

1. 点击 **部署**

### 部署完成

访问 `http://localhost:11435/v1/models`，返回的模型列表含 `Qwen/Qwen3-4B-AWQ`。

### 故障排查

| 现象 | 处理 |
|------|----------|
| 健康检查超时 | 执行 `docker logs -f edge-llm-chat-service` 查看下载进度 |
| 预热阶段显存不足 | 关闭其他占用 GPU 的任务后重新部署 |

## 步骤 3: 部署 Reachy 语音机器人 {#reachy_deploy type=docker_deploy required=true config=devices/reachy_jetson_deploy.yaml target_inherit_from=speech_service}

部署机器人控制、对话和视觉服务。步骤 2 的 Edge LLM 服务须已在运行。


### 部署完成

机器人部署完成后约 30 秒就绪。

#### 当前状态

机器人默认处于对话模式：对它说话，它用一句话回复，并配合情绪和头部、天线动作。

#### 服务概览

仪表盘在 8042 端口；其他端口：机器人控制 38001、视觉 8630、Edge LLM 11435、语音 8621。

#### 后续操作

- 打开仪表盘 `http://<jetson-ip>:8042` 查看对话日志、机器人状态并调整设置。
- 修改人格：编辑当前语音 profile 的 `instructions.txt`。调整麦克风增益 `audio_volume`、VAD 灵敏度 `client_vad_threshold`、`tts_speed`：编辑 `~/reachy-jetson-llm/reachy-voice.yaml`。
- 修改上述文件或在仪表盘改设置后，执行 `docker restart reachy-voice` 生效。

### 部署目标 {#reachy_remote type=remote config=devices/reachy_jetson_deploy.yaml default=true}

通过 SSH 部署到步骤 1 的 Jetson。

### 接线

1. 用 USB 线将 Reachy Mini 连接到 Jetson
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 配置数据目录（默认 `~/reachy-data`），用于存储截图和人脸数据库
4. 可选启用**全屏展示模式**，开机后自动全屏打开仪表盘
5. 点击 **部署**

### 部署完成

打开 `http://<jetson-ip>:8042`，对机器人说一句话，它会回复。

### 故障排查

| 现象 | 处理 |
|------|----------|
| 对话响应慢（>10 秒） | 执行 `docker logs edge-llm-chat-service`，并访问 `http://<jetson-ip>:11435/v1/models` 检查 Edge LLM |
| 机器人不动 | 重新插拔 USB 线后执行 `docker restart reachy-daemon` |
| 没有声音 | 检查 Reachy Mini 内置扬声器和配置中的 `audio.device` |
| 仪表盘打不开 | 等待 30 秒，访问 `http://<jetson-ip>:8042/health` |
| 没有摄像头画面 | 视觉服务首次启动需约 5 分钟构建引擎，执行 `docker logs vision-trt` 查看 |
| 开机后摄像头未找到 | 视觉服务会自动重试约 90 秒，稍等 |
| 摄像头运行一段时间后失联 | 物理拔插 Reachy USB 线 |

### 部署目标 {#reachy_local type=local config=devices/reachy_jetson_deploy.yaml}

部署到本机，本机须为已连接 Reachy Mini 的 Jetson，已安装 Docker 和 NVIDIA Container Toolkit。

### 接线

1. 用 USB 线将 Reachy Mini 连接到本机
2. 点击 **部署**，首次下载镜像和初始化模型需要 5-10 分钟

### 部署完成

打开 `http://localhost:8042`，对机器人说一句话，它会回复。

### 故障排查

| 现象 | 处理 |
|------|----------|
| 未找到 NVIDIA 运行时 | 执行 `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 机器人不动 | 重新插拔 USB 线后执行 `docker restart reachy-daemon` |
| 仪表盘打不开 | 等待 30 秒，访问 `http://localhost:8042/health` |
| 没有摄像头画面 | 视觉服务首次启动需约 5 分钟构建引擎，执行 `docker logs vision-trt` 查看 |

## 套餐: AI Industrial R21 + Hailo-8 {#r2000_hailo}

机器人控制、对话和 Hailo-8 视觉部署在 AI Industrial R21 上，语音和大模型由一台远程 Jetson 提供。

- **设备：** 一台 JetPack 6.x 的 Jetson（运行语音和大模型，步骤 1 部署语音服务，大模型服务 `edge-llm-chat-service` 须在该 Jetson 上运行），一台 AI Industrial R21。
- **外设：** Reachy Mini 和 USB 摄像头都接在 AI Industrial R21 上。
- **网络：** 两台设备都可通过 SSH 访问，AI Industrial R21 能访问 Jetson 的 8621 和 11435 端口。

## 步骤 1: 部署语音服务 {#hailo_speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

在 Jetson 上部署语音识别（ASR）和语音合成（TTS）服务，镜像已包含模型。

### 部署目标 {#hailo_speech_remote type=remote config=devices/speech_deploy.yaml default=true}

通过 SSH 部署到 Jetson，设备须为 JetPack 6.x。

### 接线

1. 将 Jetson 连接到网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 点击 **部署**

### 部署完成

访问 `http://<jetson-ip>:8621/health`，返回 `{"asr": true, "tts": true, "streaming_asr": true}`。

### 故障排查

| 现象 | 处理 |
|------|----------|
| SSH 连接失败 | 在电脑上先试 `ssh 用户名@IP`，确认 IP 和凭据 |
| 镜像拉取慢 | 镜像压缩后约 8 GB，确保 Jetson 网络稳定 |
| 服务未启动 | 执行 `ssh 用户名@IP "cd reachy-jetson-voice && docker compose logs"` 查看日志 |
| 健康检查失败 | 首次启动约 40 秒预热模型，稍等后重试 |

### 部署目标 {#hailo_speech_local type=local config=devices/speech_deploy.yaml}

部署到本机，本机须有 NVIDIA GPU，已安装 Docker 和 NVIDIA Container Toolkit。

### 接线

1. 点击 **部署**，首次下载镜像和初始化模型需要 10-15 分钟

### 部署完成

访问 `http://localhost:8621/health`，返回 `{"asr": true, "tts": true, "streaming_asr": true}`。

### 故障排查

| 现象 | 处理 |
|------|----------|
| 未找到 NVIDIA 运行时 | 执行 `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 8621 已被占用 | 停止占用 8621 端口的服务 |
| 容器不断重启 | 执行 `docker logs reachy-jetson-voice-speech-1` 查看日志 |
| 健康检查失败 | 首次启动约 40 秒预热模型，稍等后重试 |

## 步骤 2: 部署 Reachy 语音机器人（Hailo） {#reachy_hailo_deploy type=docker_deploy required=true config=devices/reachy_hailo_deploy.yaml target_inherit_from=hailo_speech_service}

在 AI Industrial R21 上部署机器人控制、对话和 Hailo 视觉服务，缺少 Hailo 驱动时会自动安装。


### 部署完成

机器人部署完成后约 30 秒就绪。

#### 当前状态

机器人默认处于对话模式：对它说话，它用一句话回复，并配合情绪和头部、天线动作。

#### 服务概览

仪表盘在 AI Industrial R21 的 8042 端口；其他端口：机器人控制 38001、视觉 8630 / 8631（R21 上），语音 8621、Edge LLM 11435（Jetson 上）。

#### 后续操作

- 打开仪表盘 `http://<r2000-ip>:8042` 查看对话日志、机器人状态并调整设置。
- 修改人格：编辑当前语音 profile 的 `instructions.txt`。调整麦克风增益 `audio_volume`、VAD 灵敏度 `client_vad_threshold`、`tts_speed`：编辑 `~/reachy-jetson-llm/reachy-voice.yaml`。
- 修改上述文件或在仪表盘改设置后，执行 `docker restart reachy-voice` 生效。

### 部署目标 {#reachy_hailo_remote type=remote config=devices/reachy_hailo_deploy.yaml default=true}

通过 SSH 部署到 AI Industrial R21。Hailo-8 须已插入 M.2 插槽，并在 `/boot/firmware/config.txt` 启用 PCIe Gen3。

### 接线

1. 用 USB 线将 Reachy Mini 连接到 AI Industrial R21
2. 将 USB 摄像头插入 AI Industrial R21
3. 输入 AI Industrial R21 的 IP 地址和 SSH 凭据（默认用户名 `pi`）
4. 输入**语音助手主机**：运行语音和大模型的 Jetson IP（例如 `192.168.1.100`）
5. 配置数据目录（默认 `~/reachy-data`）
6. 可选启用**全屏展示模式**，开机后自动全屏打开仪表盘
7. 点击 **部署**

### 部署完成

打开 `http://<r2000-ip>:8042`，对机器人说一句话，它会回复。

### 故障排查

| 现象 | 处理 |
|------|----------|
| `/dev/hailo0` 找不到 | 重新插紧 M.2 槽位上的 Hailo-8 并重启，用 `lspci \| grep -i hailo` 确认识别 |
| `hailo-all` 安装失败 | 按 `vision-hailo` 仓库的 `INSTALL.md` 手动添加 Hailo apt 源 |
| 容器报版本不匹配 | 执行 `sudo apt install --reinstall hailo-all` 后重新部署 |
| FPS 低于 5 | 把 CPU scaling governor 设为 `performance` |
| 仪表盘上没有人脸数据 | 访问 `http://localhost:8630/` 检查视觉服务 |
| 语音不工作 | 在 R21 上访问 `http://<jetson-ip>:8621/health` 确认 Jetson 可达 |
| 机器人不动 | 重新插拔 USB 线后执行 `docker restart reachy-daemon` |

### 部署目标 {#reachy_hailo_local type=local config=devices/reachy_hailo_deploy.yaml}

部署到本机，本机须为装有 Hailo-8 的 AI Industrial R21，已安装 Docker，Reachy Mini 通过 USB 连接。

### 接线

1. 用 USB 线将 Reachy Mini 连接到本机
2. 点击 **部署**，首次下载镜像需要 5-10 分钟

### 部署完成

打开 `http://localhost:8042`，对机器人说一句话，它会回复。

### 故障排查

| 现象 | 处理 |
|------|----------|
| `/dev/hailo0` 找不到 | 重新插紧 M.2 槽位上的 Hailo-8 并重启 |
| 机器人不动 | 重新插拔 USB 线后执行 `docker restart reachy-daemon` |
| 仪表盘打不开 | 等待 30 秒，访问 `http://localhost:8042/health` |

## 套餐: Reachy Mini Wireless（CM4） {#cm4}

机器人控制、对话和 CPU 视觉部署在 Reachy Mini Wireless 自带的 CM4 上，语音和大模型由一台远程 Jetson 提供。

- **设备：** 一台 JetPack 6.x 的 Jetson（运行语音和大模型，步骤 1 部署语音服务，大模型服务 `edge-llm-chat-service` 须在该 Jetson 上运行），一台 Reachy Mini Wireless。
- **网络：** 两台设备都可通过 SSH 访问，CM4 能访问 Jetson 的 8621 和 11435 端口。

## 步骤 1: 部署语音服务 {#cm4_speech_service type=docker_deploy required=true config=devices/speech_deploy.yaml}

在 Jetson 上部署语音识别（ASR）和语音合成（TTS）服务，镜像已包含模型。

### 部署目标 {#cm4_speech_remote type=remote config=devices/speech_deploy.yaml default=true}

通过 SSH 部署到 Jetson，设备须为 JetPack 6.x。

### 接线

1. 将 Jetson 连接到网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 点击 **部署**

### 部署完成

访问 `http://<jetson-ip>:8621/health`，返回 `{"asr": true, "tts": true, "streaming_asr": true}`。

### 故障排查

| 现象 | 处理 |
|------|----------|
| SSH 连接失败 | 在电脑上先试 `ssh 用户名@IP`，确认 IP 和凭据 |
| 镜像拉取慢 | 镜像压缩后约 8 GB，确保 Jetson 网络稳定 |
| 服务未启动 | 执行 `ssh 用户名@IP "cd reachy-jetson-voice && docker compose logs"` 查看日志 |
| 健康检查失败 | 首次启动约 40 秒预热模型，稍等后重试 |

### 部署目标 {#cm4_speech_local type=local config=devices/speech_deploy.yaml}

部署到本机，本机须有 NVIDIA GPU，已安装 Docker 和 NVIDIA Container Toolkit。

### 接线

1. 点击 **部署**，首次下载镜像和初始化模型需要 10-15 分钟

### 部署完成

访问 `http://localhost:8621/health`，返回 `{"asr": true, "tts": true, "streaming_asr": true}`。

### 故障排查

| 现象 | 处理 |
|------|----------|
| 未找到 NVIDIA 运行时 | 执行 `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 8621 已被占用 | 停止占用 8621 端口的服务 |
| 容器不断重启 | 执行 `docker logs reachy-jetson-voice-speech-1` 查看日志 |
| 健康检查失败 | 首次启动约 40 秒预热模型，稍等后重试 |

## 步骤 2: 部署 Reachy 语音机器人（CM4） {#reachy_cm4_deploy type=docker_deploy required=true config=devices/reachy_cm4_deploy.yaml target_inherit_from=cm4_speech_service}

在 CM4 上部署机器人控制、对话和视觉服务。


### 部署完成

机器人部署完成后约 30 秒就绪。

#### 当前状态

机器人默认处于对话模式：对它说话，它用一句话回复，并配合情绪和头部、天线动作。

#### 服务概览

仪表盘在 CM4 的 8042 端口；其他端口：机器人控制 38001、视觉 8630 / 8631（CM4 上），语音 8621、Edge LLM 11435（Jetson 上）。

#### 后续操作

- 打开仪表盘 `http://<cm4-ip>:8042` 查看对话日志、机器人状态并调整设置。
- 修改人格：编辑当前语音 profile 的 `instructions.txt`。调整麦克风增益 `audio_volume`、VAD 灵敏度 `client_vad_threshold`、`tts_speed`：编辑 `~/reachy-jetson-llm/reachy-voice.yaml`。
- 修改上述文件或在仪表盘改设置后，执行 `docker restart reachy-voice` 生效。

### 部署目标 {#reachy_cm4_remote type=remote config=devices/reachy_cm4_deploy.yaml default=true}

通过 SSH 部署到 Reachy Mini Wireless 的 CM4，CM4 上须已安装 Docker。

### 接线

1. 输入 CM4 的 IP 地址和 SSH 凭据（默认用户名 `pi`）
2. 输入**语音助手主机**：运行语音和大模型的 Jetson IP（例如 `192.168.1.100`）
3. 配置数据目录（默认 `~/reachy-data`）
4. 可选启用**全屏展示模式**，开机后自动全屏打开仪表盘
5. 点击 **部署**

### 部署完成

打开 `http://<cm4-ip>:8042`，对机器人说一句话，它会回复。

### 故障排查

| 现象 | 处理 |
|------|----------|
| Docker 未安装 | 用 get.docker.com 官方脚本安装 |
| 语音不工作 | 在 CM4 上访问 `http://<jetson-ip>:8621/health` 确认 Jetson 可达 |
| 没有摄像头画面 | 执行 `ls /dev/video*`，为空时重新插拔 USB 摄像头 |
| 机器人不动 | 重新插拔 USB 线后执行 `docker restart reachy-daemon` |
| 仪表盘打不开 | 等待 30 秒，访问 `http://localhost:8042/health` |

### 部署目标 {#reachy_cm4_local type=local config=devices/reachy_cm4_deploy.yaml}

直接在 Reachy Mini Wireless 的 CM4 上部署，CM4 上须已安装 Docker。

### 接线

1. 点击 **部署**，首次下载镜像需要 5-10 分钟

### 部署完成

打开 `http://localhost:8042`，对机器人说一句话，它会回复。

### 故障排查

| 现象 | 处理 |
|------|----------|
| Docker 未安装 | 用 get.docker.com 官方脚本安装 |
| 机器人不动 | 重新插拔 USB 线后执行 `docker restart reachy-daemon` |
| 仪表盘打不开 | 等待 30 秒，访问 `http://localhost:8042/health` |
