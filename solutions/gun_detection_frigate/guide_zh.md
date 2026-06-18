## 套餐: NVIDIA Jetson {#jetson}

使用 Frigate NVR 在 NVIDIA Jetson 上进行实时枪支检测，搭配 TensorRT GPU 加速。

| 设备 | 用途 |
|------|------|
| NVIDIA Jetson (reComputer) | 支持 TensorRT GPU 加速的边缘 AI 设备 |
| 网络摄像头（可选） | RTSP 监控视频源 |

**部署完成后你可以：**
- 实时检测画面中的枪支，显示检测框和置信度
- 通过 Web 仪表盘查看实时监控和事件回放
- 检测到枪支时自动录像和截图
- 通过 MQTT 集成报警和自动化系统

**前提条件：** 目标设备已安装 Docker + NVIDIA Container Toolkit

## 步骤 1: 初始化摄像头 {#init_cameras_jetson type=manual required=false}

设置网络摄像头并获取 RTSP 视频流地址。

### 接线

1. 将网络摄像头连接到与部署设备相同的网络
2. 查找摄像头 IP 地址（查看路由器 DHCP 客户端列表，或使用厂商搜索工具）
3. 访问摄像头 Web 管理界面（通常为 `http://<摄像头IP>`）
4. 在摄像头设置中启用 RTSP 串流（通常默认已启用）
5. 记录摄像头的 RTSP 地址

> **常见 RTSP 地址格式：**
> - **海康威视：** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`（主码流）或 `/102`（子码流）
> - **大华：** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`（主码流）或 `&subtype=1`（子码流）
> - **通用 ONVIF：** 使用摄像头的 ONVIF 发现工具获取流地址

**提示：** 建议使用子码流（低分辨率）做检测以减少 CPU/GPU 负载，主码流用于录像。

可使用 VLC 测试 RTSP 地址：**媒体 > 打开网络串流 > 粘贴地址**。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 无法访问摄像头管理界面 | 用 `ping <摄像头IP>` 验证连通性。检查摄像头与电脑是否在同一子网 |
| RTSP 流无法播放 | 确认摄像头设置中已启用 RTSP。先用 VLC 测试。检查用户名和密码 |
| 网络上找不到摄像头 | 重启摄像头电源。检查网线连接。尝试使用厂商搜索工具（如海康 SADP、大华 ConfigTool） |

## 步骤 2: 部署 Frigate {#deploy_frigate_jetson type=docker_deploy required=true config=devices/jetson_deploy.yaml}

将 Frigate NVR 和 TensorRT 加速的枪支检测 AI 部署到 NVIDIA Jetson。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

通过 SSH 部署到远程 NVIDIA Jetson 设备。

### 接线

1. 将 Jetson 连接到与电脑相同的网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 可选填写 RTSP 摄像头地址（最多 2 个）
4. 点击 **部署** 开始安装

> **提示：** 首次启动需要 5-10 分钟——系统会下载并编译枪支检测模型以进行 TensorRT 优化。

### 部署完成

1. 在浏览器打开 **http://\<设备IP\>:5000**
2. 你将看到两个演示摄像头正在检测枪支
3. 如果填写了 RTSP 地址，你的摄像头也会出现并启用枪支检测

后续修改摄像头配置，SSH 登录设备并编辑：

```bash
cd ~/gun-detection-frigate
nano config/config.yml
docker compose restart
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 5000 被占用 | 停止占用服务：`docker stop $(docker ps -q --filter publish=5000)` |
| 模型编译很慢 | 首次启动需 5-10 分钟进行 TensorRT 优化，后续启动秒开 |
| 容器反复重启 | 查看日志：`docker logs frigate`——可能是 GPU 内存或驱动问题 |
| RTSP 摄像头未显示 | 用 VLC 验证 RTSP 地址是否可用。编辑设备上的 `config/config.yml` 后重启：`docker compose restart` |

### 部署目标 {#jetson_local type=local config=devices/jetson_deploy.yaml}

直接在当前机器上部署（需要 NVIDIA GPU）。

### 接线

1. 确保已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署** 开始安装

> **提示：** 首次启动需要 5-10 分钟进行 TensorRT 模型编译。

### 部署完成

1. 在浏览器打开 **http://localhost:5000**
2. 你将看到两个演示摄像头正在检测枪支

添加 RTSP 摄像头，编辑配置文件后重启：

```bash
cd ~/gun-detection-frigate
nano config/config.yml
docker compose restart
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到 NVIDIA 运行时 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 5000 被占用 | 停止占用服务：`docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 查看日志：`docker logs frigate`——可能是 GPU 内存或驱动问题 |

## 步骤 3: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Frigate 面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |
### 部署完成

恭喜！Frigate 枪支检测系统已部署成功。

#### 快速验证

1. 在浏览器打开 Frigate 仪表盘（部署完成后显示的地址）
2. 查看 **Birdseye** 视图概览所有摄像头
3. 确认演示视频上出现枪支检测框
4. 点击事件查看带时间戳的录像截图

#### 添加或修改摄像头

要添加更多 RTSP 摄像头或修改现有配置，SSH 登录设备并编辑：

```bash
cd ~/gun-detection-frigate
nano config/config.yml
```

在 `cameras:` 下添加摄像头：

```yaml
  my_camera:
    enabled: true
    ffmpeg:
      inputs:
        - path: rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
          roles:
            - detect
            - record
    detect:
      width: 1920
      height: 1080
      fps: 5
    objects:
      track:
        - gun
```

常见 RTSP 地址格式：
- **海康威视：** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`
- **大华：** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`

然后重启 Frigate：

```bash
docker compose restart
```

#### 后续步骤

- 通过 MQTT 配置告警通知（MQTT Broker 运行在端口 1883）
- 在 `config/config.yml` 中调整检测阈值（`objects.filters.gun.threshold`）
- 设置录像保留策略（`record.retain.days`）
- [Frigate 官方文档](https://docs.frigate.video/)

## 套餐: reComputer R2000 + Hailo {#r2000_hailo}

使用 Frigate NVR 在 reComputer R2000 上进行实时枪支检测，搭配 Hailo AI 加速器。

| 设备 | 用途 |
|------|------|
| reComputer R2000 + Hailo | 搭载 Hailo NPU 加速的边缘 AI 设备 |
| 网络摄像头（可选） | RTSP 监控视频源 |

**部署完成后你可以：**
- 实时检测画面中的枪支，显示检测框和置信度
- 通过 Web 仪表盘查看实时监控和事件回放
- 检测到枪支时自动录像和截图
- 通过 MQTT 集成报警和自动化系统

**前提条件：** 目标设备已安装 Docker · 已安装 Hailo AI 加速器

## 步骤 1: 初始化摄像头 {#init_cameras_r2000 type=manual required=false}

设置网络摄像头并获取 RTSP 视频流地址。

### 接线

1. 将网络摄像头连接到与部署设备相同的网络
2. 查找摄像头 IP 地址（查看路由器 DHCP 客户端列表，或使用厂商搜索工具）
3. 访问摄像头 Web 管理界面（通常为 `http://<摄像头IP>`）
4. 在摄像头设置中启用 RTSP 串流（通常默认已启用）
5. 记录摄像头的 RTSP 地址

> **常见 RTSP 地址格式：**
> - **海康威视：** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`（主码流）或 `/102`（子码流）
> - **大华：** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`（主码流）或 `&subtype=1`（子码流）
> - **通用 ONVIF：** 使用摄像头的 ONVIF 发现工具获取流地址

**提示：** 建议使用子码流（低分辨率）做检测以减少 CPU/GPU 负载，主码流用于录像。

可使用 VLC 测试 RTSP 地址：**媒体 > 打开网络串流 > 粘贴地址**。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 无法访问摄像头管理界面 | 用 `ping <摄像头IP>` 验证连通性。检查摄像头与电脑是否在同一子网 |
| RTSP 流无法播放 | 确认摄像头设置中已启用 RTSP。先用 VLC 测试。检查用户名和密码 |
| 网络上找不到摄像头 | 重启摄像头电源。检查网线连接。尝试使用厂商搜索工具（如海康 SADP、大华 ConfigTool） |

## 步骤 2: 部署 Frigate {#deploy_frigate_r2000 type=docker_deploy required=true config=devices/r2000_hailo_deploy.yaml}

将 Frigate NVR 和 Hailo 加速的枪支检测 AI 部署到 reComputer R2000。

### 部署目标 {#r2000_remote type=remote config=devices/r2000_hailo_deploy.yaml default=true}

通过 SSH 部署到远程 reComputer R2000。

### 接线

1. 确保设备已安装 Hailo AI Kit（运行 `ls /dev/hailo*` 检查）
2. 将设备连接到与电脑相同的网络
3. 输入设备的 IP 地址和 SSH 凭据
4. 可选填写 RTSP 摄像头地址（最多 2 个）
5. 点击 **部署** 开始安装

> **提示：** 部署时会自动检测并安装所需的 HailoRT 4.21.0 驱动（首次安装约需 5-10 分钟）。至少需要 4 GB 可用磁盘空间。

### 部署完成

1. 在浏览器打开 **http://\<设备IP\>:5000**
2. 你将看到两个演示摄像头正在检测枪支
3. 如果填写了 RTSP 地址，你的摄像头也会出现并启用枪支检测

后续修改摄像头配置，SSH 登录设备并编辑：

```bash
cd ~/gun-detection-r2000-hailo
nano config/config.yml
docker compose restart
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到 Hailo 设备 | 检查 Hailo 是否正确安装在 M.2 插槽：`ls /dev/hailo*` 应显示 `/dev/hailo0` |
| HailoRT 版本不匹配 | Frigate 需要 HailoRT **4.21.0**。查看版本：`dpkg -l hailort`。安装正确驱动：`curl -sfL https://raw.githubusercontent.com/blakeblackshear/frigate/dev/docker/hailo8l/user_installation.sh \| sudo bash`，然后重启 |
| 磁盘空间不足 | 至少需要 4 GB 可用空间。运行 `docker system prune -a` 和 `sudo apt clean` 释放空间 |
| 端口 5000 被占用 | 停止占用服务：`docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 查看日志：`docker logs frigate-hailo`——可能是 Hailo 驱动问题 |
| RTSP 摄像头未显示 | 用 VLC 验证 RTSP 地址是否可用。编辑设备上的 `config/config.yml` 后重启：`docker compose restart` |

### 部署目标 {#r2000_local type=local config=devices/r2000_hailo_deploy.yaml}

直接在当前机器上部署（需要 Hailo AI 加速器）。

### 接线

1. 确保已安装 Docker 且 Hailo 设备可访问（`ls /dev/hailo*`）
2. 点击 **部署** 开始安装

> **提示：** Frigate Docker 镜像约需 4 GB 磁盘空间。

### 部署完成

1. 在浏览器打开 **http://localhost:5000**
2. 你将看到两个演示摄像头正在检测枪支

添加 RTSP 摄像头，编辑配置文件后重启：

```bash
nano config/config.yml
docker compose restart
```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到 Hailo 设备 | 检查 Hailo 是否正确安装：`ls /dev/hailo*` 应显示 `/dev/hailo0` |
| 端口 5000 被占用 | 停止占用服务：`docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 查看日志：`docker logs frigate-hailo`——可能是 Hailo 驱动问题 |

## 步骤 3: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Frigate 面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |
### 部署完成

恭喜！Frigate 枪支检测系统已部署成功。

#### 快速验证

1. 在浏览器打开 Frigate 仪表盘（部署完成后显示的地址）
2. 查看 **Birdseye** 视图概览所有摄像头
3. 确认演示视频上出现枪支检测框
4. 点击事件查看带时间戳的录像截图

#### 添加或修改摄像头

要添加更多 RTSP 摄像头或修改现有配置，SSH 登录设备并编辑：

```bash
cd ~/gun-detection-frigate
nano config/config.yml
```

在 `cameras:` 下添加摄像头：

```yaml
  my_camera:
    enabled: true
    ffmpeg:
      inputs:
        - path: rtsp://admin:password@192.168.1.100:554/Streaming/Channels/101
          roles:
            - detect
            - record
    detect:
      width: 1920
      height: 1080
      fps: 5
    objects:
      track:
        - gun
```

常见 RTSP 地址格式：
- **海康威视：** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`
- **大华：** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`

然后重启 Frigate：

```bash
docker compose restart
```

#### 后续步骤

- 通过 MQTT 配置告警通知（MQTT Broker 运行在端口 1883）
- 在 `config/config.yml` 中调整检测阈值（`objects.filters.gun.threshold`）
- 设置录像保留策略（`record.retain.days`）
- [Frigate 官方文档](https://docs.frigate.video/)
