## 套餐: Jetson GPT OSS 20B 服务 {#jetson_got_oss}

通过本平台一键将 GPT OSS 20B 部署到你的 Jetson 设备。

| 设备 | 用途 |
|------|------|
| NVIDIA Jetson（reComputer） | 在 Docker 中运行 GPT OSS 20B |

## 步骤 1: 部署 GPT OSS 20B 服务 {#deploy_got_oss type=docker_deploy required=true config=devices/jetson_deploy.yaml}

将容器化的 GPT OSS 20B 运行时通过 SSH 部署到你的 Jetson。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

通过 SSH 一键部署到 Jetson。

### 接线

1. 将 Jetson 和你的电脑接到同一网络
2. 填入 Jetson IP、SSH 用户名和密码
3. 点击 **部署**

### 部署完成

1. GPT OSS 20B 容器已在你的 Jetson 上运行
2. 容器内已启动 `llama-server`
3. 服务地址：`http://<jetson-ip>:8080`
4. 就绪检查地址：`http://<jetson-ip>:8080/v1/models`

### 故障排查

| 问题 | 解决方法 |
|------|--------|
| SSH 连接失败 | 检查 Jetson IP、用户名、密码以及 SSH 服务状态 |
| Docker 运行时检查失败 | 确认已安装 Docker 且具备 NVIDIA runtime |
| 找不到 Docker Compose | 确认已安装 `docker compose` 或 `docker-compose` |
| 服务启动失败 | 登录 Jetson 看日志：`docker compose logs --tail=200` |
| `/v1/models` 返回 `503 {"message":"Loading model"}` | 模型正在预热，首次加载可能需要几分钟 |
| 启动时内存不足 | 降低参数，例如 `Llama NGL=16`、`Llama Context=512` |

### 部署目标 {#jetson_local type=local config=devices/jetson_deploy.yaml}

直接在当前机器上部署（需要具备足够显存的 NVIDIA GPU）。

### 接线

1. 确保已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署** 开始安装

> **提示：** 首次启动可能需要 15-30 分钟下载 Docker 镜像和加载模型。需要至少 20GB 可用磁盘空间。

### 部署完成

1. 在浏览器打开 **http://localhost:8080**
2. 你将看到 GPT OSS 聊天界面，可随时开始对话

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 8080 已被占用 | 停止该端口上的其他服务 |
| 容器反复重启 | 查看日志：`docker compose logs --tail=200` |
| GPU 显存不足 | 20B 模型需要较大显存。可尝试使用更小的模型变体 |


## 步骤 2: 打开服务链接 {#preview_service type=preview required=false config=devices/preview.yaml}

在此步骤直接在浏览器新标签页中打开 Jetson 上的服务地址。

### 接线

1. 在该步骤中填入 Jetson IP
2. 点击 **连接**
3. 平台会在新标签页打开 `http://<jetson-ip>:8080`

### 部署完成

1. 服务页面已在浏览器中打开
2. 你可以回到这里再次点击 **连接** 重新打开

### 故障排查

| 问题 | 解决方法 |
|------|--------|
| 主机输入无效 | 填入有效的 IP 或主机名，例如 `192.168.1.100` |
| 没有打开新标签页 | 允许本站点的弹出窗口后重试 |
| 服务页面打不开 | 确认 Jetson 服务监听在 `8080`，并且网络可达 |

### 部署完成

GPT OSS 20B 运行时已成功部署到你的 Jetson。

#### 验证清单

1. 步骤 1 部署状态显示成功
2. GPT OSS 20B 容器保持运行状态
3. 在步骤 2 中点击 **连接** 能打开 `http://<jetson-ip>:8080`
