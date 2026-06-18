## 套餐: 部署语音服务 {#default}

在你的边缘设备上部署流式语音识别（ASR）和语音合成（TTS）服务——支持 Jetson Orin、RK3576、RK3588 和树莓派 5。

| 设备 | 推理引擎 | 最适合 |
|------|---------|--------|
| NVIDIA Jetson Orin | TensorRT-EdgeLLM / sherpa-onnx（GPU） | 最低延迟，多语言，声音克隆 |
| RK3576 / RK3588 | RKNN（NPU） | 高效端侧语音识别 + 语音合成 |
| 树莓派 5 | sherpa-onnx（CPU） | 低成本中英文语音输入输出 |

**部署完成后你可以：**
- 实时流式语音识别（WebSocket）
- 低延迟语音合成（HTTP 流式 + 批量）
- 多种语言模式：中文+英文、纯英文、或 52 种语言 Qwen3
- 通过 HTTP + WebSocket API（端口 8621）调用

**前提条件：** 可通过 SSH 连接设备 · 需要联网拉取 Docker 镜像和下载模型 · 磁盘空间：Jetson 7.5 GB，RK 4.4 GB，树莓派 2.8 GB

## 步骤 1: 部署语音服务 {#speech_service type=docker_deploy required=true config=devices/jetson_deploy.yaml}

将语音服务部署到你的边缘设备。预构建镜像已包含所有依赖，模型在首次启动时自动下载。

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_deploy.yaml default=true}

### 接线

1. 将 Jetson 连接到网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 从下拉菜单选择语音配置
4. 点击 **部署** — 系统会自动拉取镜像并启动服务

### 部署完成

服务已在 `http://<设备 IP>:8621` 运行。快速测试：

```bash
curl http://<设备 IP>:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}

curl -X POST http://<设备 IP>:8621/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，我是你的语音助手。", "sid": 0}' \
  --output test.wav
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 确认 IP 地址和凭据正确。先在电脑上试 `ssh 用户名@IP` |
| 镜像拉取慢 | 镜像压缩后约 2 GB，确保设备网络稳定 |
| 服务未启动 | 查看日志：`ssh 用户名@IP "cd openvoicestream && docker compose logs"` |
| 健康检查失败 | 首次启动需约 40 秒预热模型，稍等后重试 |
| 内存不足 | 确保 Jetson 有 8GB+ 内存，且没有其他 GPU 任务在运行 |
| 未找到 NVIDIA 运行时 | 安装：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson（本地）" config=devices/jetson_deploy.yaml}

直接部署到当前机器（需要本机是 Jetson，并已安装 NVIDIA Container Toolkit）。

### 接线

1. 确认本机已安装 Docker 和 NVIDIA Container Toolkit
2. 从下拉菜单选择语音配置
3. 点击 **部署** — 系统会自动拉取镜像并启动服务

### 部署完成

服务已在 `http://localhost:8621` 运行。快速测试：

```bash
curl http://localhost:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 未找到 Docker | 安装 Docker：`curl -fsSL https://get.docker.com \| sh` |
| 未找到 NVIDIA 运行时 | 安装：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 镜像拉取慢 | 镜像压缩后约 2 GB，确保网络稳定 |
| 健康检查失败 | 首次启动需约 40 秒预热模型，稍等后重试 |
| 内存不足 | 确保 Jetson 有 8GB+ 内存，且没有其他 GPU 任务在运行 |

### 部署目标 {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_deploy.yaml}

### 接线

1. 将 RK3576 设备连接到网络
2. 输入设备 IP 和 SSH 凭据
3. 从下拉菜单选择语音配置
4. 点击 **部署** — 模型在首次启动时自动下载

### 部署完成

服务已在 `http://<设备 IP>:8621` 运行。快速测试：

```bash
curl http://<设备 IP>:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 确认 IP 和凭据正确。默认用户名：`cat` |
| NPU 未检测到 | 确保 `rknpu` 驱动已加载：`ls /dev/rknpu` |
| 模型未下载 | 检查网络和 HF endpoint。模型约 3.6 GB，可能需要 10-20 分钟 |
| 健康检查失败 | 首次启动需约 60 秒初始化模型 |
| 内存不足 | RK3576 需要 4GB+ 可用内存，RK3588 需要 6GB+ |

### 部署目标 {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_deploy.yaml}

### 接线

1. 将 RK3588 设备连接到网络
2. 输入设备 IP 和 SSH 凭据
3. 从下拉菜单选择语音配置
4. 点击 **部署** — 模型在首次启动时自动下载

### 部署完成

服务已在 `http://<设备 IP>:8621` 运行。快速测试：

```bash
curl http://<设备 IP>:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 确认 IP 和凭据正确。默认用户名：`cat` |
| NPU 未检测到 | 确保 `rknpu` 驱动已加载：`ls /dev/rknpu` |
| 模型未下载 | 检查网络和 HF endpoint。模型约 3.6 GB，可能需要 10-20 分钟 |
| 健康检查失败 | 首次启动需约 60 秒初始化模型 |
| 内存不足 | RK3588 需要 6GB+ 可用内存 |

### 部署目标 {#rpi_remote type=remote device=rpi device_name="Raspberry Pi" config=devices/rpi_deploy.yaml}

### 接线

1. 将树莓派连接到网络
2. 输入树莓派的 IP 地址和 SSH 凭据
3. 从下拉菜单选择语音配置
4. 点击 **部署** — CPU 镜像仅 568 MB

### 部署完成

服务已在 `http://<设备 IP>:8621` 运行。快速测试：

```bash
curl http://<设备 IP>:8621/health
# 预期返回: {"asr": true, "tts": true, "streaming_asr": true}
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 确认 IP 和凭据正确。默认用户名：`pi` |
| 服务未启动 | 检查 Docker 是否已安装：`docker --version` |
| 健康检查失败 | 首次启动需约 30 秒预热模型 |
| ASR 不工作 | 树莓派 4 ASR-only 配置无 TTS。树莓派 5 建议用 `rpi5-default` |

## 步骤 2: 语音演示 {#voice_demo type=voice_chat required=false config=devices/voice_demo.yaml}

直接在此页面体验已部署的语音服务。输入设备 IP 地址，然后使用下方面板测试语音识别和语音合成。

### 语音识别（ASR）

按住 **录音** 按钮说话，语音将被实时识别，转录文字会即时显示在屏幕上。

### 文字转语音（TTS）

输入任意文字，点击 **生成** 即可听到语音播放。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 麦克风无法使用 | 浏览器弹出权限请求时请点击允许 |
| ASR 没有识别结果 | 确认服务正在运行：`curl http://<IP>:8621/health` |
| TTS 播放无声音 | 检查浏览器音量是否静音，尝试较短的文字 |
### 部署完成

恭喜！本地语音服务已运行。

#### 快速验证

1. 在浏览器打开 `http://<设备 IP>:8621/health` — 所有字段应显示 `true`
2. 用上面的 `curl` 命令测试语音合成
3. 将你的应用连接到 API 接口

#### API 接口一览

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 服务健康检查 |
| `/asr/stream` | WebSocket | 实时流式语音识别 |
| `/tts` | POST | 文字转语音（返回 WAV） |
| `/tts/stream` | POST | 流式文字转语音（返回原始 PCM） |
| `/asr` | POST | 离线语音识别（上传 WAV 文件） |

#### 后续步骤

- 接入你的大语言模型，完成语音助手流水线：ASR → LLM → TTS
- 部署后可在"设备管理"页面调整语音配置
- [OpenVoiceStream GitHub](https://github.com/suharvest/openvoicestream)
