## 套餐: 部署图片生成服务 {#jetson_image_gen}

在 Jetson Orin NX 上一键部署 Z-Image-Turbo HTTP API 进行本地文生图和图生图。

| 设备 | 用途 |
|------|------|
| NVIDIA Jetson Orin NX (16GB) | 使用 TensorRT BF16 加速运行 Z-Image-Turbo 6B 模型 |

**部署后你将获得：**
- 一键部署 — 支持远程 SSH 部署或直接在 Jetson 上本地部署
- 端口 8000 上的 HTTP API，支持文生图和图生图
- 完全离线运行，无需云服务
- 512px 生成约 100 秒，384px 约 73 秒

**前提条件：** Jetson Orin NX 16GB + JetPack 6 + NVIDIA Docker 运行时 + 网络连通（首次部署会自动从 HuggingFace 下载模型权重和 TRT 引擎；huggingface.co 不通时自动切换到 hf-mirror.com）。

## 步骤 1: 部署图片生成服务 {#deploy_service type=docker_deploy required=true config=devices/jetson_deploy.yaml}

将 Z-Image-Turbo API 容器部署到 Jetson。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

通过 SSH 一键部署到你的 Jetson Orin NX。

### 接线

1. 确保 Jetson 在同一网络中且 SSH 已启用
2. 填写 Jetson IP、SSH 凭据、模型根目录和输出目录
3. 点击 **部署** —— 首次运行会自动下载所选分辨率对应的模型权重和 TRT 引擎

### 部署完成

1. Z-Image-Turbo API 在 Jetson 端口 8000 上运行
2. 健康检查地址：`http://<jetson-ip>:8000/health`
3. 生成的图片保存在输出目录中

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| SSH 连接失败 | 检查 IP、用户名、密码，确认 Jetson SSH 服务已启用 |
| 找不到 Docker | 在 Jetson 上安装 Docker 和 NVIDIA Container Toolkit |
| HuggingFace 下载失败 | 脚本会自动切换到 `hf-mirror.com`；若两者都不通，请在 Jetson 上配置代理或手动准备 `$MODEL_ROOT` 内容 |
| 下载中断 | 重新部署即可 —— 未完成的 `.part` 文件会丢弃，已下载完成的文件不会重复下载 |
| API 无响应 | 检查容器日志：`docker logs z-image-api` |
| Docker 权限不足 | 运行 `sudo usermod -aG docker <user>` 并重新登录 |
| 生成时内存不足 | 容器会根据分辨率自动配置缓存层数（512 用 18 层，384 用 23 层） |

### 部署目标 {#jetson_local type=local config=devices/jetson_deploy.yaml}

直接在 Jetson 上部署（已连接键盘和显示器）。

### 接线

1. 确保 Jetson 上已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署** —— 首次运行会自动下载所选分辨率对应的模型权重和 TRT 引擎

### 部署完成

1. Z-Image-Turbo API 在本机端口 8000 上运行
2. 健康检查地址：`http://localhost:8000/health`
3. 生成的图片保存在输出目录中

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 找不到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| HuggingFace 下载失败 | 脚本会自动切换到 `hf-mirror.com`；若两者都不通，请配置代理或手动准备 `$MODEL_ROOT` 内容 |
| 下载中断 | 重新部署即可 —— 未完成的 `.part` 文件会丢弃，已下载完成的文件不会重复下载 |
| API 无响应 | 检查容器日志：`docker logs z-image-api` |
| 端口 8000 被占用 | 停止占用 8000 端口的其他服务 |

## 步骤 2: 生成图片 {#verify_api type=image_text_to_image required=false config=devices/verify_api.yaml}

输入提示词来生成图片。每次生成需要 1-2 分钟。生成结果会直接显示在验证面板中。

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 健康检查失败 | 确认 Jetson 可达且端口 8000 未被防火墙拦截 |
| 生成返回错误 | 查看容器日志：`docker logs z-image-api` |
| 请求超时 | 生成需要 1-2 分钟，将 HTTP 客户端超时时间增加到 180 秒 |
### 部署完成

Z-Image-Turbo 已成功部署到你的 Jetson 上。

#### API 参考

##### 健康检查
```bash
curl http://<jetson-ip>:8000/health
```

##### 文生图
```bash
curl -X POST http://<jetson-ip>:8000/generate_json -H 'Content-Type: application/json' -d '{"prompt": "一只可爱的猫，照片级真实感", "num_steps": 4}'
```

##### 图生图
```bash
curl -X POST http://<jetson-ip>:8000/generate -F 'prompt=一只戴着红围巾的猫' -F 'image=@/path/to/reference.png' -F 'num_steps=8' -F 'strength=0.65'
```

#### 验证清单

1. 健康检查返回 `{"success": true}`
2. 文生图请求返回包含图片 URL 的响应
3. 生成的 PNG 文件出现在输出目录中
