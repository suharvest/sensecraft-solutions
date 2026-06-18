## 预设: 目标检测 {#object_detection}

一键将 YOLO 11 目标检测部署到 reComputer RK3576 或 RK3588。

| 设备 | 用途 |
|------|------|
| reComputer RK3576 / RK3588 | 使用 RKNN NPU 加速运行 YOLO 11 |
| USB 摄像头（可选） | 实时视频检测输入 |

**部署后你将获得：**
- 本地运行的 YOLO 11 检测 API
- 3 种模型大小可选：极速版（最快）、均衡版、精确版（最准）
- 图片/视频检测 REST API + MJPEG 实时视频流
- 开箱即用，支持 80 种 COCO 物体类别

**前提条件：** RK3576 或 RK3588 设备可通过 SSH 访问 + 已安装 Docker

## 步骤 1: 部署 YOLO 11 {#cv_deploy type=docker_deploy required=true config=devices/cv_rk3576_deploy.yaml}

将目标检测容器部署到 RK35xx 设备。

### 部署目标 {#cv_rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/cv_rk3576_deploy.yaml default=true}

通过 SSH 一键部署到 RK3576。

### 接线

1. 将 RK3576 连接到与电脑相同的网络
2. 如需实时视频检测，请连接 USB 摄像头
3. 选择模型大小（初学者推荐极速版）
4. 填写设备 IP、SSH 用户名和密码
5. 点击 **部署**

### 部署完成

1. YOLO 容器已在 RK3576 上运行
2. 检测 API：`http://<设备IP>:8000/api/models/yolo11/predict`
3. 实时视频流：`http://<设备IP>:8000/api/video_feed`（需要摄像头）
4. Web 预览：`http://<设备IP>:8000`（如可用）

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| SSH 连接失败 | 检查 IP 地址、用户名、密码 |
| 未检测到 NPU | 确认设备为 RK3576 且已加载 RKNPU 内核模块 |
| 未检测到摄像头 | 检查 USB 摄像头是否已连接。无摄像头时仍可通过图片上传 API 进行检测 |
| 镜像拉取缓慢 | 检查网络连接，镜像约 1-2GB |

### 部署目标 {#cv_rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/cv_rk3588_deploy.yaml}

通过 SSH 一键部署到 RK3588 设备（reComputer / ROCK 5T）。

### 接线

1. 将 RK3588 连接到与电脑相同的网络
2. 如需实时视频检测，请连接 USB 摄像头
3. 选择模型大小（初学者推荐极速版）
4. 填写设备 IP、SSH 用户名和密码
5. 点击 **部署**

### 部署完成

1. YOLO 容器已在 RK3588 上运行
2. 检测 API：`http://<设备IP>:8000/api/models/yolo11/predict`
3. 实时视频流：`http://<设备IP>:8000/api/video_feed`（需要摄像头）

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| SSH 连接失败 | 检查 IP 地址、用户名、密码 |
| RK3588 平台未检测到 | 确认设备为 RK3588 系列（reComputer / ROCK 5T） |
| 未检测到摄像头 | 检查 USB 摄像头是否已连接。无摄像头时仍可通过图片上传 API 进行检测 |
| 镜像拉取缓慢 | 检查网络连接，镜像约 1-2GB |

### 部署目标 {#cv_rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/cv_rk3576_deploy.yaml}

直接在当前机器上部署（需要 RK3576 设备）。

### 接线

1. 确保当前机器已安装 Docker
2. 点击 **部署** 开始安装

> **提示：** 首次启动可能需要 5-10 分钟下载 Docker 镜像和初始化模型。

### 部署完成

1. 在浏览器打开 **http://localhost:8000**
2. 你将看到 YOLO 检测服务正在运行

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| Docker 未安装 | 安装 Docker：`curl -fsSL https://get.docker.com | sudo sh` |
| 端口 8000 被占用 | 停止占用该端口的服务 |
| 容器反复重启 | 查看日志：`docker logs ai_lab_cv` |

### 部署目标 {#cv_rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/cv_rk3588_deploy.yaml}

直接在当前机器上部署（需要 RK3588 设备）。

### 接线

1. 确保当前机器已安装 Docker
2. 点击 **部署** 开始安装

> **提示：** 首次启动可能需要 5-10 分钟下载 Docker 镜像和初始化模型。

### 部署完成

1. 在浏览器打开 **http://localhost:8000**
2. 你将看到 YOLO 检测服务正在运行

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| Docker 未安装 | 安装 Docker：`curl -fsSL https://get.docker.com | sudo sh` |
| 端口 8000 被占用 | 停止占用该端口的服务 |
| 容器反复重启 | 查看日志：`docker logs ai_lab_cv` |


## 步骤 2: 试试检测效果 {#cv_verify type=image_predict}

验证检测服务是否正常工作。

### 模式: 图片检测 {#cv_image_mode config=devices/cv_image.yaml default=true}
上传一张图片测试目标检测。

### 故障排查
| 问题 | 解决方案 |
|------|----------|
| 没有检测结果 | 尝试包含人或车辆的图片 |
| 连接被拒绝 | 等待 15-30 秒让服务启动 |

### 模式: 实时视频 {#cv_video_mode config=devices/cv_stream.yaml}
查看带检测框的实时摄像头画面（需要 USB 摄像头）。

### 故障排查
| 问题 | 解决方案 |
|------|----------|
| 黑屏 | 检查 USB 摄像头是否已连接 |
| 无视频流 | 检查 MJPEG 地址是否正确 |


## 预设: 大模型对话 {#llm_chat}

一键将 DeepSeek-R1 大语言模型部署到 reComputer RK3576。

| 设备 | 用途 |
|------|------|
| reComputer RK3576 | 使用 NPU 加速运行 DeepSeek-R1 |

**部署后你将获得：**
- 本地运行的 OpenAI 兼容对话 API
- 5 种模型变体可选（1.5B/7B，不同量化方式）
- 无需云端依赖，所有推理在设备本地完成

**前提条件：** RK3576 设备可通过 SSH 访问 + 已安装 Docker

## 步骤 1: 部署 DeepSeek-R1 {#llm_deploy type=docker_deploy required=true config=devices/llm_rk3576_deploy.yaml}

将 LLM 容器部署到 RK3576 设备。

### 部署目标 {#llm_rk3576_remote type=remote config=devices/llm_rk3576_deploy.yaml default=true}

通过 SSH 一键部署到 RK3576。

### 接线

1. 将 RK3576 连接到与电脑相同的网络
2. 选择要运行的模型变体
3. 填写设备 IP、SSH 用户名和密码
4. 点击 **部署**

### 部署完成

1. LLM 容器已在 RK3576 上运行
2. 对话 API 可通过 `http://<设备IP>:8001/v1/chat/completions` 访问
3. 使用任何 OpenAI 兼容客户端连接即可

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| SSH 连接失败 | 检查 IP 地址、用户名、密码 |
| 未检测到 NPU | 确认设备为 RK3576 且已加载 RKNPU 内核模块 |
| 内存不足（7B 模型） | 7B 变体需要 8GB+ 内存，请改用 1.5B 变体 |
| 镜像拉取缓慢 | 检查网络连接，镜像大小 1-4GB 取决于变体 |

### 部署目标 {#llm_rk3576_local type=local config=devices/llm_rk3576_deploy.yaml}

直接在当前机器上部署（需要 RK3576 设备）。

### 接线

1. 确保当前机器已安装 Docker
2. 点击 **部署** 开始安装

> **提示：** 首次启动可能需要 10-20 分钟，用于下载 Docker 镜像和初始化 LLM 模型。

### 部署完成

1. 对话 API 可通过 `http://localhost:8001/v1/chat/completions` 访问
2. 使用任何 OpenAI 兼容客户端与模型交互

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 未安装 Docker | 安装 Docker：`curl -fsSL https://get.docker.com \| sudo sh` |
| 端口 8001 被占用 | 停止占用该端口的服务 |
| 未检测到 NPU | 确认设备为 RK3576 且已加载 RKNPU 内核模块 |
| 容器反复重启 | 查看日志：`docker logs ai_lab_llm` |
| 内存不足 | LLM 模型至少需要 8GB 内存 |


## 步骤 2: 试试对话 {#llm_verify type=text_chat required=false config=devices/llm_chat.yaml}

发送一条消息测试 LLM。

### 故障排查
| 问题 | 解决方案 |
|------|----------|
| 连接被拒绝 | 等待 30-60 秒让模型加载 |
| 超时 | 7B 模型加载时间较长，请等待最多 2 分钟 |
| 空响应 | 查看容器日志：`docker logs ai_lab_llm` |


## 预设: 视觉对话 {#vlm_chat}

一键将 Qwen2.5-VL 视觉语言模型部署到 reComputer RK3576。

| 设备 | 用途 |
|------|------|
| reComputer RK3576 | 使用 NPU 加速运行 Qwen2.5-VL |

**部署后你将获得：**
- 同时理解图片和文本的多模态 AI
- 本地运行的 OpenAI 兼容视觉 API
- 图片描述、视觉问答等功能，全部在设备端完成
- `/docs` 路径提供交互式 API 文档

**前提条件：** RK3576 设备（8GB+ 内存）可通过 SSH 访问 + 已安装 Docker

## 步骤 1: 部署 Qwen2.5-VL {#vlm_deploy type=docker_deploy required=true config=devices/vlm_rk3576_deploy.yaml}

将视觉语言模型容器部署到 RK3576 设备。

### 部署目标 {#vlm_rk3576_remote type=remote config=devices/vlm_rk3576_deploy.yaml default=true}

通过 SSH 一键部署到 RK3576。

### 接线

1. 将 RK3576 连接到与电脑相同的网络
2. 填写设备 IP、SSH 用户名和密码
3. 点击 **部署**

### 部署完成

1. VLM 容器已在 RK3576 上运行
2. 视觉对话 API：`http://<设备IP>:8002/v1/chat/completions`
3. API 文档：`http://<设备IP>:8002/docs`

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| SSH 连接失败 | 检查 IP 地址、用户名、密码 |
| 未检测到 NPU | 确认设备为 RK3576 且已加载 RKNPU 内核模块 |
| 内存不足 | VLM 需要 8GB+ 内存，请关闭其他服务释放内存 |
| 镜像拉取缓慢 | 检查网络连接，镜像约 3GB |

### 部署目标 {#vlm_rk3576_local type=local config=devices/vlm_rk3576_deploy.yaml}

直接在当前机器上部署（需要 RK3576 设备）。

### 接线

1. 确保当前机器已安装 Docker
2. 点击 **部署** 开始安装

> **注意：** 首次启动可能需要 10-20 分钟用于下载 Docker 镜像和初始化 VLM 模型。

### 部署完成

1. 在浏览器中打开 **http://localhost:8002**
2. 即可看到视觉语言聊天界面

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| Docker 未安装 | 安装 Docker：`curl -fsSL https://get.docker.com | sudo sh` |
| 端口 8002 已被占用 | 停止该端口上的其他服务 |
| 容器不断重启 | 查看日志：`docker logs ai_lab_vlm` |
| 内存不足 | VLM 模型需要至少 8GB 内存 |

## 步骤 2: 试试视觉对话 {#vlm_verify type=image_text_chat}

发送图片或文字测试 VLM。

### 模式: 图片理解 {#vlm_vision_mode config=devices/vlm_chat.yaml default=true}
上传一张图片并提问。

### 故障排查
| 问题 | 解决方案 |
|------|----------|
| 连接被拒绝 | 等待 60-120 秒让模型加载 |
| 超时 | VLM 模型较大，首次加载需要时间 |

### 模式: 文本对话 {#vlm_text_mode config=devices/vlm_text.yaml}
仅用文本与模型对话。

### 故障排查
| 问题 | 解决方案 |
|------|----------|
| 空响应 | 查看容器日志：`docker logs ai_lab_vlm` |
### 部署完成

AI Lab 已运行起来。能访问的接口取决于你部署的预设：

| 预设 | API 根路径 | 快速验证 |
|------|----------|---------|
| 目标检测 | `http://<设备IP>:8000` | `curl -X POST .../api/models/yolo11/predict -F "file=@photo.jpg"` |
| 大模型对话 | `http://<设备IP>:8001` | `curl .../v1/chat/completions -d '{"messages":[{"role":"user","content":"你好"}]}'` |
| 视觉对话 | `http://<设备IP>:8002` | 打开 `/docs` 进行交互式测试 |

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
