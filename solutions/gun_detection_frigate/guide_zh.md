## 套餐: NVIDIA Jetson {#jetson}

在 NVIDIA Jetson 上用 Frigate NVR 做实时枪支检测，检测到枪支时自动录像和截图，可通过 MQTT 对接报警系统。

- **设备：** NVIDIA Jetson (reComputer)；网络摄像头可选，不接时用演示视频。
- **软件：** 目标设备已安装 Docker 和 NVIDIA Container Toolkit。
- **网络：** 摄像头、Jetson 和这台电脑在同一网络。

## 步骤 1: 初始化摄像头 {#init_cameras_jetson type=manual required=false}

获取网络摄像头的 RTSP 视频流地址。只用演示视频时跳过。

### 接线

1. 将网络摄像头接入与 Jetson 相同的网络
2. 在路由器 DHCP 客户端列表或厂商搜索工具里查到摄像头 IP
3. 打开摄像头 Web 管理界面（通常为 `http://<摄像头IP>`），确认已启用 RTSP
4. 记录 RTSP 地址，用 VLC（**媒体 > 打开网络串流**）测试能播放

> **常见 RTSP 地址格式：**
> - **海康威视：** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`（主码流）或 `/102`（子码流）
> - **大华：** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`（主码流）或 `&subtype=1`（子码流）
> - **通用 ONVIF：** 使用摄像头的 ONVIF 发现工具获取流地址

检测建议用子码流，录像用主码流。

### 故障排查

| 现象 | 处理 |
|------|------|
| 无法访问摄像头管理界面 | 用 `ping <摄像头IP>` 测试，确认摄像头与电脑在同一子网 |
| RTSP 流无法播放 | 确认已启用 RTSP，核对用户名和密码，先用 VLC 测试 |
| 网络上找不到摄像头 | 重启摄像头电源，检查网线，用厂商搜索工具（如海康 SADP、大华 ConfigTool） |

## 步骤 2: 部署 Frigate {#deploy_frigate_jetson type=docker_deploy required=true config=devices/jetson_deploy.yaml}

将 Frigate NVR 和枪支检测模型部署到 NVIDIA Jetson。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

通过 SSH 部署到网络上的 Jetson。

### 接线

1. 将 Jetson 接入与电脑相同的网络
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 可选填写 RTSP 摄像头地址（最多 2 个）
4. 点击 **部署**。首次启动需要 5-10 分钟编译模型

### 部署完成

打开 **http://\<设备IP\>:5000**，能看到两路演示视频上的枪支检测框；填写了 RTSP 地址时，你的摄像头也会出现。

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 NVIDIA 运行时 | `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 5000 被占用 | `docker stop $(docker ps -q --filter publish=5000)` |
| 首次启动很慢 | 首次编译模型需 5-10 分钟，之后启动不再编译 |
| 容器反复重启 | 执行 `docker logs frigate` 查看原因，常见为 GPU 内存或驱动问题 |
| RTSP 摄像头未显示 | 用 VLC 验证地址，按步骤 3 修改 `config/config.yml` 后重启 |

### 部署目标 {#jetson_local type=local config=devices/jetson_deploy.yaml}

部署到本机。本机须为已安装 Docker 和 NVIDIA Container Toolkit 的 NVIDIA GPU 设备。

### 接线

1. 确认本机已安装 Docker 和 NVIDIA Container Toolkit
2. 点击 **部署**。首次启动需要 5-10 分钟编译模型

### 部署完成

打开 **http://localhost:5000**，能看到两路演示视频上的枪支检测框。

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 NVIDIA 运行时 | `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 端口 5000 被占用 | `docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 执行 `docker logs frigate` 查看原因，常见为 GPU 内存或驱动问题 |

## 步骤 3: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

点击下方按钮打开 Frigate 面板。

### 故障排查
| 现象 | 处理 |
|------|------|
| 页面无法加载 | 确认上一步部署成功 |
| 主机/端口错误 | 部署到远程设备时，把地址换成设备 IP |
### 部署完成

#### 快速验证

1. 打开 Frigate 面板，在 **Birdseye** 视图查看所有摄像头
2. 确认演示视频上出现枪支检测框
3. 点击事件，能看到带时间戳的截图

#### 添加或修改摄像头

SSH 登录设备，编辑配置文件：

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

保存后重启 Frigate：

```bash
docker compose restart
```

#### 后续步骤

- 通过 MQTT（端口 1883）配置告警通知
- 在 `config/config.yml` 中调整检测阈值（`objects.filters.gun.threshold`）
- 设置录像保留天数（`record.retain.days`）
- [Frigate 官方文档](https://docs.frigate.video/)

## 套餐: reComputer AI Industrial R21 + Hailo {#r2000_hailo}

在 reComputer AI Industrial R21 上用 Frigate NVR 和 Hailo 加速器做实时枪支检测，检测到枪支时自动录像和截图，可通过 MQTT 对接报警系统。

- **设备：** reComputer AI Industrial R21 + Hailo；网络摄像头可选，不接时用演示视频。
- **软件：** 目标设备已安装 Docker 和 Hailo 加速器，至少 4 GB 可用磁盘。
- **网络：** 摄像头、R21 和这台电脑在同一网络。

## 步骤 1: 初始化摄像头 {#init_cameras_r2000 type=manual required=false}

获取网络摄像头的 RTSP 视频流地址。只用演示视频时跳过。

### 接线

1. 将网络摄像头接入与 R21 相同的网络
2. 在路由器 DHCP 客户端列表或厂商搜索工具里查到摄像头 IP
3. 打开摄像头 Web 管理界面（通常为 `http://<摄像头IP>`），确认已启用 RTSP
4. 记录 RTSP 地址，用 VLC（**媒体 > 打开网络串流**）测试能播放

> **常见 RTSP 地址格式：**
> - **海康威视：** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`（主码流）或 `/102`（子码流）
> - **大华：** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`（主码流）或 `&subtype=1`（子码流）
> - **通用 ONVIF：** 使用摄像头的 ONVIF 发现工具获取流地址

检测建议用子码流，录像用主码流。

### 故障排查

| 现象 | 处理 |
|------|------|
| 无法访问摄像头管理界面 | 用 `ping <摄像头IP>` 测试，确认摄像头与电脑在同一子网 |
| RTSP 流无法播放 | 确认已启用 RTSP，核对用户名和密码，先用 VLC 测试 |
| 网络上找不到摄像头 | 重启摄像头电源，检查网线，用厂商搜索工具（如海康 SADP、大华 ConfigTool） |

## 步骤 2: 部署 Frigate {#deploy_frigate_r2000 type=docker_deploy required=true config=devices/r2000_hailo_deploy.yaml}

将 Frigate NVR 和枪支检测模型部署到 reComputer AI Industrial R21。

### 部署目标 {#r2000_remote type=remote config=devices/r2000_hailo_deploy.yaml default=true}

通过 SSH 部署到网络上的 R21。部署时会自动检查并安装 HailoRT 4.21.0 驱动，首次约需 5-10 分钟。

### 接线

1. 在设备上执行 `ls /dev/hailo*`，确认显示 `/dev/hailo0`
2. 将设备接入与电脑相同的网络
3. 输入设备的 IP 地址和 SSH 凭据
4. 可选填写 RTSP 摄像头地址（最多 2 个）
5. 点击 **部署**

### 部署完成

打开 **http://\<设备IP\>:5000**，能看到两路演示视频上的枪支检测框；填写了 RTSP 地址时，你的摄像头也会出现。

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 Hailo 设备 | 检查 Hailo 是否插好 M.2 插槽，`ls /dev/hailo*` 应显示 `/dev/hailo0` |
| HailoRT 版本不匹配 | 需要 HailoRT **4.21.0**，用 `dpkg -l hailort` 查看。安装：`curl -sfL https://raw.githubusercontent.com/blakeblackshear/frigate/dev/docker/hailo8l/user_installation.sh \| sudo bash`，然后重启 |
| 磁盘空间不足 | 至少需要 4 GB，执行 `docker system prune -a` 和 `sudo apt clean` 释放空间 |
| 端口 5000 被占用 | `docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 执行 `docker logs frigate-hailo` 查看原因，常见为 Hailo 驱动问题 |
| RTSP 摄像头未显示 | 用 VLC 验证地址，按步骤 3 修改 `config/config.yml` 后重启 |

### 部署目标 {#r2000_local type=local config=devices/r2000_hailo_deploy.yaml}

部署到本机。本机须已安装 Docker 和 Hailo 加速器，至少 4 GB 可用磁盘。

### 接线

1. 执行 `ls /dev/hailo*`，确认显示 `/dev/hailo0`
2. 点击 **部署**

### 部署完成

打开 **http://localhost:5000**，能看到两路演示视频上的枪支检测框。

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 Hailo 设备 | 检查 Hailo 是否插好，`ls /dev/hailo*` 应显示 `/dev/hailo0` |
| 端口 5000 被占用 | `docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 执行 `docker logs frigate-hailo` 查看原因，常见为 Hailo 驱动问题 |

## 步骤 3: 打开面板 {#dashboard_r2000_hailo type=web_dashboard required=true config=devices/dashboard.yaml}

点击下方按钮打开 Frigate 面板。

### 故障排查
| 现象 | 处理 |
|------|------|
| 页面无法加载 | 确认上一步部署成功 |
| 主机/端口错误 | 部署到远程设备时，把地址换成设备 IP |
### 部署完成

#### 快速验证

1. 打开 Frigate 面板，在 **Birdseye** 视图查看所有摄像头
2. 确认演示视频上出现枪支检测框
3. 点击事件，能看到带时间戳的截图

#### 添加或修改摄像头

SSH 登录设备，编辑配置文件：

```bash
cd ~/gun-detection-r2000-hailo
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

保存后重启 Frigate：

```bash
docker compose restart
```

#### 后续步骤

- 通过 MQTT（端口 1883）配置告警通知
- 在 `config/config.yml` 中调整检测阈值（`objects.filters.gun.threshold`）
- 设置录像保留天数（`record.retain.days`）
- [Frigate 官方文档](https://docs.frigate.video/)
