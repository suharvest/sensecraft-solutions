## 套餐: Jetson 一键深度估计演示 {#jetson_depth}

通过本平台一键将 Depth Anything V3 部署到 Jetson 设备。

| 设备 | 用途 |
|------|------|
| NVIDIA Jetson (reComputer) | 运行 Depth Anything V3 Docker 容器 |
| USB 摄像头（可选） | 提供实时深度推理输入 |

**部署后你将获得：**
- 通过 SSH 自动远程部署
- 预配置 GPU 运行时的 Docker 容器
- Jetson 上可直接使用的 Depth Anything V3 运行环境

**前提条件：** Jetson 运行 Linux 且可 SSH 连接，并已安装 Docker

## 步骤 1: 部署 Depth Anything V3 {#deploy_depth_anything type=docker_deploy required=true config=devices/jetson_deploy.yaml}

将容器化运行环境部署到 Jetson。用户无需手动输入任何终端命令。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

通过 SSH 一键部署到 Jetson。

### 接线

1. 将 Jetson 连接到与电脑相同的网络
2. 如需实时深度推理，请接入 USB 摄像头
3. 填写 Jetson 的 IP、SSH 用户名和密码
4. 点击 **Deploy**

### 部署完成

1. Docker 容器已在 Jetson 上运行
2. 你可以基于该运行环境继续后续应用集成
3. 部署过程无需额外命令输入

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| SSH 连接失败 | 检查 IP、用户名、密码，并确认 Jetson 已开启 SSH 服务 |
| Docker 运行时检查失败 | 确认 Jetson 已安装 Docker 且可用 NVIDIA runtime |
| Docker 权限不足（未加入 docker 组） | 在 Jetson 执行 `sudo usermod -aG docker <ssh-user>`，然后执行 `newgrp docker`（或退出重登），用 `docker info` 验证后重试 |
| 磁盘空间不足 | 清理 Jetson 根分区空间后重试 |
| 部署超时 | 保持 Jetson 在线，检查网络质量后重试 |

### 部署目标 {#jetson_local type=local config=devices/jetson_deploy.yaml}

直接在当前机器上部署（需要 NVIDIA GPU）。

### 接线

1. 确保已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署** 开始安装

> **提示：** 首次启动需要 5-10 分钟进行 TensorRT 模型编译和 Docker 镜像下载。

### 部署完成

1. Docker 容器已在本机运行
2. USB 摄像头推理已在容器中自动启动
3. RTSP 推流地址：`rtsp://localhost:8554/depth`
4. 使用 **步骤 2：预览深度视频流** 查看实时画面

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 8554 被占用 | 停止占用 8554 端口的服务 |
| 容器反复重启 | 查看日志：`docker logs depth_anything_v3`——可能是 GPU 内存或驱动问题 |

## 步骤 2: 预览深度视频流 {#preview_depth_stream type=preview required=false config=devices/preview.yaml}

通过该步骤在平台页面直接查看 Jetson 推理输出的 RTSP 视频流。

### 接线

1. 将 USB 摄像头接到 Jetson，确认设备节点存在（如 `/dev/video0`）
2. 确认 Jetson 推理管线已经输出 RTSP（推荐地址：`rtsp://<jetson-ip>:8554/depth`）
3. 在本步骤填写 RTSP 地址
4. 点击 **Connect** 开始预览

### 部署完成

1. 预览窗口可以看到实时视频
2. 如果推理管线输出的是深度图或叠加图，这里会实时显示
3. 无需重新部署步骤 1，可随时断开或重连预览

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 预览黑屏 | 先用 VLC 验证 RTSP 地址可播放，再回到页面重试 |
| 连接超时 | 检查运行本平台的电脑是否可访问 Jetson 的 `8554` 端口 |
| 只看到原始画面 | 说明 Jetson 当前推的是相机原始流，请切换为推理输出流地址 |
### 部署完成

Depth Anything V3 运行环境已成功部署到 Jetson。

#### 验证清单

1. 当前页面中部署状态为成功
2. 服务容器保持运行状态
3. 可以直接进入下一步业务集成流程
