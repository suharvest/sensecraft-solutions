## 套餐: 目标检测 {#object_detection}

在 reComputer RK3576 或 RK3588 上部署 YOLO 11 目标检测，提供图片检测 REST API 和 MJPEG 实时视频流，支持 80 种 COCO 物体类别。

- **设备：** reComputer RK3576 或 RK3588；实时视频检测需要 USB 摄像头（可选）。
- **软件：** 设备已安装 Docker，可通过 SSH 访问。
- **模型：** 部署时可选极速版、均衡版、精确版。

## 步骤 1: 部署 YOLO 11 {#cv_deploy type=docker_deploy required=true config=devices/cv_rk3576_deploy.yaml}

将目标检测容器部署到设备。

### 部署目标 {#cv_rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/cv_rk3576_deploy.yaml default=true}

通过 SSH 部署到 RK3576。

### 接线

1. 将 RK3576 接入与电脑相同的网络
2. 需要实时视频检测时接上 USB 摄像头
3. 选择模型大小（先用极速版）
4. 填写设备 IP、SSH 用户名和密码
5. 点击 **部署**

### 部署完成

1. 检测 API：`http://<设备IP>:8000/api/models/yolo11/predict`
2. 实时视频流：`http://<设备IP>:8000/api/video_feed`（需要摄像头）

### 故障排查

| 现象 | 处理 |
|------|------|
| SSH 连接失败 | 检查 IP 地址、用户名、密码 |
| 未检测到 NPU | 确认设备为 RK3576 且已加载 RKNPU 内核模块 |
| 未检测到摄像头 | 检查 USB 摄像头连接；没有摄像头时仍可用图片检测 API |
| 镜像拉取缓慢 | 检查网络，镜像约 1-2GB |

### 部署目标 {#cv_rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/cv_rk3588_deploy.yaml}

通过 SSH 部署到 reComputer RK3588 系列设备。

### 接线

1. 将 RK3588 接入与电脑相同的网络
2. 需要实时视频检测时接上 USB 摄像头
3. 选择模型大小（先用极速版）
4. 填写设备 IP、SSH 用户名和密码
5. 点击 **部署**

### 部署完成

1. 检测 API：`http://<设备IP>:8000/api/models/yolo11/predict`
2. 实时视频流：`http://<设备IP>:8000/api/video_feed`（需要摄像头）

### 故障排查

| 现象 | 处理 |
|------|------|
| SSH 连接失败 | 检查 IP 地址、用户名、密码 |
| RK3588 平台未检测到 | 确认设备为 reComputer RK3588 系列 |
| 未检测到摄像头 | 检查 USB 摄像头连接；没有摄像头时仍可用图片检测 API |
| 镜像拉取缓慢 | 检查网络，镜像约 1-2GB |

### 部署目标 {#cv_rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/cv_rk3576_deploy.yaml}

部署到本机。本机须为已安装 Docker 的 RK3576 设备。首次启动需要 5-10 分钟。

### 接线

1. 确认本机已安装 Docker
2. 点击 **部署**

### 部署完成

在浏览器打开 **http://localhost:8000**，能看到检测服务在运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| Docker 未安装 | `curl -fsSL https://get.docker.com \| sudo sh` |
| 端口 8000 被占用 | 停止占用该端口的服务 |
| 容器反复重启 | 执行 `docker logs ai_lab_cv` 查看原因 |

### 部署目标 {#cv_rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/cv_rk3588_deploy.yaml}

部署到本机。本机须为已安装 Docker 的 RK3588 设备。首次启动需要 5-10 分钟。

### 接线

1. 确认本机已安装 Docker
2. 点击 **部署**

### 部署完成

在浏览器打开 **http://localhost:8000**，能看到检测服务在运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| Docker 未安装 | `curl -fsSL https://get.docker.com \| sudo sh` |
| 端口 8000 被占用 | 停止占用该端口的服务 |
| 容器反复重启 | 执行 `docker logs ai_lab_cv` 查看原因 |


## 步骤 2: 试试检测效果 {#cv_verify type=image_predict}

确认检测服务正常工作。

### 模式: 图片检测 {#cv_image_mode config=devices/cv_image.yaml default=true}
上传一张图片测试目标检测。

### 故障排查
| 现象 | 处理 |
|------|------|
| 没有检测结果 | 换一张包含人或车辆的图片 |
| 连接被拒绝 | 等 15-30 秒让服务启动 |

### 模式: 实时视频 {#cv_video_mode config=devices/cv_stream.yaml}
查看带检测框的实时摄像头画面（需要 USB 摄像头）。

### 故障排查
| 现象 | 处理 |
|------|------|
| 黑屏 | 检查 USB 摄像头连接 |
| 无视频流 | 检查 MJPEG 地址 |


## 套餐: 大模型对话 {#llm_chat}

在 reComputer RK3576 上部署 DeepSeek-R1 大语言模型，提供本地运行的 OpenAI 兼容对话 API。

- **设备：** reComputer RK3576；7B 模型需要 8GB 以上内存。
- **软件：** 设备已安装 Docker，可通过 SSH 访问。
- **模型：** 部署时可选 5 种变体（1.5B/7B，不同量化方式）。

## 步骤 1: 部署 DeepSeek-R1 {#llm_deploy type=docker_deploy required=true config=devices/llm_rk3576_deploy.yaml}

将大模型容器部署到 RK3576。

### 部署目标 {#llm_rk3576_remote type=remote config=devices/llm_rk3576_deploy.yaml default=true}

通过 SSH 部署到 RK3576。

### 接线

1. 将 RK3576 接入与电脑相同的网络
2. 选择模型变体
3. 填写设备 IP、SSH 用户名和密码
4. 点击 **部署**

### 部署完成

对话 API：`http://<设备IP>:8001/v1/chat/completions`，可用任何 OpenAI 兼容客户端连接。

### 故障排查

| 现象 | 处理 |
|------|------|
| SSH 连接失败 | 检查 IP 地址、用户名、密码 |
| 未检测到 NPU | 确认设备为 RK3576 且已加载 RKNPU 内核模块 |
| 内存不足（7B 模型） | 7B 变体需要 8GB 以上内存，改用 1.5B 变体 |
| 镜像拉取缓慢 | 检查网络，镜像 1-4GB，取决于变体 |

### 部署目标 {#llm_rk3576_local type=local config=devices/llm_rk3576_deploy.yaml}

部署到本机。本机须为已安装 Docker 的 RK3576 设备。首次启动需要 10-20 分钟。

### 接线

1. 确认本机已安装 Docker
2. 点击 **部署**

### 部署完成

对话 API：`http://localhost:8001/v1/chat/completions`，可用任何 OpenAI 兼容客户端连接。

### 故障排查

| 现象 | 处理 |
|------|------|
| 未安装 Docker | `curl -fsSL https://get.docker.com \| sudo sh` |
| 端口 8001 被占用 | 停止占用该端口的服务 |
| 未检测到 NPU | 确认设备为 RK3576 且已加载 RKNPU 内核模块 |
| 容器反复重启 | 执行 `docker logs ai_lab_llm` 查看原因 |
| 内存不足 | 至少需要 8GB 内存 |


## 步骤 2: 试试对话 {#llm_verify type=text_chat required=false config=devices/llm_chat.yaml}

发送一条消息测试大模型。

### 故障排查
| 现象 | 处理 |
|------|------|
| 连接被拒绝 | 等 30-60 秒让模型加载 |
| 超时 | 7B 模型加载较慢，最多等 2 分钟 |
| 空响应 | 执行 `docker logs ai_lab_llm` 查看原因 |


## 套餐: 视觉对话 {#vlm_chat}

在 reComputer RK3576 上部署 Qwen2.5-VL 视觉语言模型，提供本地运行的 OpenAI 兼容视觉 API，支持图片描述和视觉问答。

- **设备：** reComputer RK3576，8GB 以上内存。
- **软件：** 设备已安装 Docker，可通过 SSH 访问。

## 步骤 1: 部署 Qwen2.5-VL {#vlm_deploy type=docker_deploy required=true config=devices/vlm_rk3576_deploy.yaml}

将视觉语言模型容器部署到 RK3576。

### 部署目标 {#vlm_rk3576_remote type=remote config=devices/vlm_rk3576_deploy.yaml default=true}

通过 SSH 部署到 RK3576。

### 接线

1. 将 RK3576 接入与电脑相同的网络
2. 填写设备 IP、SSH 用户名和密码
3. 点击 **部署**

### 部署完成

1. 视觉对话 API：`http://<设备IP>:8002/v1/chat/completions`
2. API 文档：`http://<设备IP>:8002/docs`

### 故障排查

| 现象 | 处理 |
|------|------|
| SSH 连接失败 | 检查 IP 地址、用户名、密码 |
| 未检测到 NPU | 确认设备为 RK3576 且已加载 RKNPU 内核模块 |
| 内存不足 | 关闭其他服务释放内存，需要 8GB 以上 |
| 镜像拉取缓慢 | 检查网络，镜像约 3GB |

### 部署目标 {#vlm_rk3576_local type=local config=devices/vlm_rk3576_deploy.yaml}

部署到本机。本机须为已安装 Docker 的 RK3576 设备。首次启动需要 10-20 分钟。

### 接线

1. 确认本机已安装 Docker
2. 点击 **部署**

### 部署完成

在浏览器打开 **http://localhost:8002**，能看到视觉对话界面。

### 故障排查

| 现象 | 处理 |
|------|------|
| Docker 未安装 | `curl -fsSL https://get.docker.com \| sudo sh` |
| 端口 8002 已被占用 | 停止该端口上的其他服务 |
| 容器不断重启 | 执行 `docker logs ai_lab_vlm` 查看原因 |
| 内存不足 | 至少需要 8GB 内存 |

## 步骤 2: 试试视觉对话 {#vlm_verify type=image_text_chat}

发送图片或文字测试视觉语言模型。

### 模式: 图片理解 {#vlm_vision_mode config=devices/vlm_chat.yaml default=true}
上传一张图片并提问。

### 故障排查
| 现象 | 处理 |
|------|------|
| 连接被拒绝 | 等 60-120 秒让模型加载 |
| 超时 | 首次加载较慢，稍后重试 |

### 模式: 文本对话 {#vlm_text_mode config=devices/vlm_text.yaml}
仅用文本与模型对话。

### 故障排查
| 现象 | 处理 |
|------|------|
| 空响应 | 执行 `docker logs ai_lab_vlm` 查看原因 |
### 部署完成

#### 目标检测 —— 图片上传

```bash
curl -X POST http://<设备IP>:8000/api/models/yolo11/predict \
  -F "file=@photo.jpg" \
  -F "conf=0.5"
```

#### 目标检测 —— 实时视频流

在浏览器中打开：`http://<设备IP>:8000/api/video_feed`

#### 大模型对话 —— 快速调用

```bash
curl http://<设备IP>:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "rkllm-model", "messages": [{"role": "user", "content": "你好！"}], "max_tokens": 256}'
```

#### 视觉对话 —— 图片 + 提问

```bash
curl -X POST http://<设备IP>:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rkllm-vision",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "这张图片里有什么？"},
        {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}}
      ]
    }],
    "max_tokens": 256
  }'
```

#### Python（OpenAI 客户端）—— 适用于大模型对话和视觉对话

```python
import openai
client = openai.OpenAI(base_url="http://<设备IP>:8001/v1", api_key="dummy")
response = client.chat.completions.create(
    model="rkllm-model",
    messages=[{"role": "user", "content": "你好！"}],
    max_tokens=256
)
print(response.choices[0].message.content)
```
