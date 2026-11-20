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
cd ~/gun-detection-frigate/jetson_deploy
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
docker compose -p gun-detection-frigate restart
```

#### 后续步骤

- 通过 MQTT（端口 1883）配置告警通知
- 在 `config/config.yml` 中调整检测阈值（`objects.filters.gun.threshold`）
- 设置录像保留天数（`record.retain.days`）
- [Frigate 官方文档](https://docs.frigate.video/)

## 步骤 4: 部署 Home Assistant（可选） {#deploy_ha_jetson type=docker_deploy required=false config=devices/ha_host.yaml}

仅在尚未安装 Home Assistant 时勾选此步骤。如果目标主机 8123 端口已运行 Home Assistant，部署器会自动检测并跳过安装；如果已有独立的 HAOS 或外部 HA 实例，直接取消勾选并跳到步骤 5。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 端口已运行 Home Assistant | 部署器会检测到已有实例并自动跳过安装，直接进入步骤 5 |
| 在 macOS 或 Windows 上本地安装失败 | 容器使用 Docker host 网络模式，Docker Desktop 在 macOS/Windows 上默认未开启该模式（需 Docker Desktop 4.34+ 并在设置中手动开启 host networking，否则请改用远程 SSH 部署到 Linux 主机或接入已有 HA 实例） |

### 部署目标: 本地部署 {#ha_local_jetson type=local default=true}

通过本地 Docker 在当前机器部署 Home Assistant。

### 部署目标: 通过 SSH 远程部署 {#ha_remote_jetson type=remote}

通过 SSH 在远程 Linux 主机（如 Jetson 或局域网内其他服务器）上部署 Home Assistant。

## 步骤 5: 将 Frigate 接入 Home Assistant（可选） {#connect_ha_jetson type=ha_integration required=false config=devices/ha_integration_jetson.yaml}

自动安装官方 `frigate-hass-integration`（`v5.15.7`，兼容 HAOS、本机 Docker 与远程 Docker 版 HA）并重启 Home Assistant，完成 Frigate 集成与 MQTT 集成配置，同时创建默认枪支检测持久化告警自动化（`gun_detection_ha_alert`）。

### 前置条件

- **远程 Docker 版 HA：** 需在顶部 SSH 区域填写 HA 宿主机 SSH 凭据，在下方填写 HA Web UI 管理员账号密码（全新部署的 HA 将自动用此账号完成初始化）；HAOS 或本机 Docker 版无需额外手动配置 SSH Add-on。
- **跨设备部署：** 若 Frigate 本地部署（`localhost`）但 HA 运行在另一台设备，需将 `Frigate URL` 和 `MQTT Broker` 中的地址改为 Frigate 设备的局域网 IP。
- **已有 MQTT 集成：** 如果 Home Assistant 之前已经配置并加载了 MQTT 集成，引擎会直接复用现有连接而不会覆盖其 Broker 地址；此时必须确保 Frigate（`config/config.yml` 中的 `mqtt.host`）与 Home Assistant 使用同一个 MQTT Broker，并在启用告警前于 Home Assistant 中验证能收到 `frigate/events` 消息。

### 部署完成

> **注意：** 请勿直接修改自动创建的 `[Managed by SenseCraft: gun_detection_frigate] Gun Detection Alert` 自动化——重新部署方案会覆盖受管自动化并导致自定义修改丢失。

如需将枪支检测告警推送到手机并确保重新部署后配置不丢失，可通过以下两种方式配置：

1. **新建一条独立的自定义自动化：**
   在 HA「设置 → 自动化与场景 → 创建自动化 → 创建新自动化」中切换为 YAML 编辑模式，新建独立自动化并使用 Frigate 集成代理的抓拍图路径 `/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg`（外网经 HA 代理即可看图，无需直接暴露 Frigate）。

   **iOS Critical Alert 示例：**

   ```yaml
   alias: "Gun Detection Mobile Push (iOS)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           push:
             sound:
               name: default
               critical: 1
               volume: 1.0
   ```

   **Android 高优先级通道示例：**

   ```yaml
   alias: "Gun Detection Mobile Push (Android)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           ttl: 0
           priority: high
           channel: alarm_stream
   ```

2. **使用社区 Blueprint：**
   在 HA 中导入 **Frigate Notifications Blueprint**，可视化选择摄像头、`gun` 标签、目标手机以及强提醒或静音按钮。该方式创建的自动化同样独立于受管自动化，重新部署方案后不会丢失。

### 故障排查

| 现象 | 处理 |
|------|------|
| Home Assistant 登录失败 | 核对 HA Web UI 管理员账号密码，并确认 8123 端口网络可达 |
| HA 无法访问 Frigate 或 MQTT | 当 HA 与 Frigate 运行在不同设备时，将 `Frigate URL` 和 `MQTT Broker` 中的 `localhost` 改为 Frigate 设备的局域网 IP |
| 已有 HA MQTT 集成收不到 `frigate/events` | 若 HA 中已配置并加载了 MQTT 集成，引擎会直接复用现有连接而不会覆盖其 Broker 地址；请确保 Frigate（`config/config.yml` 中的 `mqtt.host`）与 HA 使用同一个 MQTT Broker，并在启用告警前于 HA 中验证能收到 `frigate/events` 消息 |

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
cd ~/gun-detection-r2000-hailo/r2000_hailo_deploy
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
docker compose -p gun-detection-r2000-hailo restart
```

#### 后续步骤

- 通过 MQTT（端口 1883）配置告警通知
- 在 `config/config.yml` 中调整检测阈值（`objects.filters.gun.threshold`）
- 设置录像保留天数（`record.retain.days`）
- [Frigate 官方文档](https://docs.frigate.video/)

## 步骤 4: 部署 Home Assistant（可选） {#deploy_ha_r2000 type=docker_deploy required=false config=devices/ha_host.yaml}

仅在尚未安装 Home Assistant 时勾选此步骤。如果目标主机 8123 端口已运行 Home Assistant，部署器会自动检测并跳过安装；如果已有独立的 HAOS 或外部 HA 实例，直接取消勾选并跳到步骤 5。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 端口已运行 Home Assistant | 部署器会检测到已有实例并自动跳过安装，直接进入步骤 5 |
| 在 macOS 或 Windows 上本地安装失败 | 容器使用 Docker host 网络模式，Docker Desktop 在 macOS/Windows 上默认未开启该模式（需 Docker Desktop 4.34+ 并在设置中手动开启 host networking，否则请改用远程 SSH 部署到 Linux 主机或接入已有 HA 实例） |

### 部署目标: 本地部署 {#ha_local_r2000 type=local default=true}

通过本地 Docker 在当前机器部署 Home Assistant。

### 部署目标: 通过 SSH 远程部署 {#ha_remote_r2000 type=remote}

通过 SSH 在远程 Linux 主机（如 R21 或局域网内其他服务器）上部署 Home Assistant。

## 步骤 5: 将 Frigate 接入 Home Assistant（可选） {#connect_ha_r2000 type=ha_integration required=false config=devices/ha_integration_r2000.yaml}

自动安装官方 `frigate-hass-integration`（`v5.15.7`，兼容 HAOS、本机 Docker 与远程 Docker 版 HA）并重启 Home Assistant，完成 Frigate 集成与 MQTT 集成配置，同时创建默认枪支检测持久化告警自动化（`gun_detection_ha_alert`）。

### 前置条件

- **远程 Docker 版 HA：** 需在顶部 SSH 区域填写 HA 宿主机 SSH 凭据，在下方填写 HA Web UI 管理员账号密码（全新部署的 HA 将自动用此账号完成初始化）；HAOS 或本机 Docker 版无需额外手动配置 SSH Add-on。
- **跨设备部署：** 若 Frigate 本地部署（`localhost`）但 HA 运行在另一台设备，需将 `Frigate URL` 和 `MQTT Broker` 中的地址改为 Frigate 设备的局域网 IP。
- **已有 MQTT 集成：** 如果 Home Assistant 之前已经配置并加载了 MQTT 集成，引擎会直接复用现有连接而不会覆盖其 Broker 地址；此时必须确保 Frigate（`config/config.yml` 中的 `mqtt.host`）与 Home Assistant 使用同一个 MQTT Broker，并在启用告警前于 Home Assistant 中验证能收到 `frigate/events` 消息。

### 部署完成

> **注意：** 请勿直接修改自动创建的 `[Managed by SenseCraft: gun_detection_frigate] Gun Detection Alert` 自动化——重新部署方案会覆盖受管自动化并导致自定义修改丢失。

如需将枪支检测告警推送到手机并确保重新部署后配置不丢失，可通过以下两种方式配置：

1. **新建一条独立的自定义自动化：**
   在 HA「设置 → 自动化与场景 → 创建自动化 → 创建新自动化」中切换为 YAML 编辑模式，新建独立自动化并使用 Frigate 集成代理的抓拍图路径 `/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg`（外网经 HA 代理即可看图，无需直接暴露 Frigate）。

   **iOS Critical Alert 示例：**

   ```yaml
   alias: "Gun Detection Mobile Push (iOS)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           push:
             sound:
               name: default
               critical: 1
               volume: 1.0
   ```

   **Android 高优先级通道示例：**

   ```yaml
   alias: "Gun Detection Mobile Push (Android)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           ttl: 0
           priority: high
           channel: alarm_stream
   ```

2. **使用社区 Blueprint：**
   在 HA 中导入 **Frigate Notifications Blueprint**，可视化选择摄像头、`gun` 标签、目标手机以及强提醒或静音按钮。该方式创建的自动化同样独立于受管自动化，重新部署方案后不会丢失。

### 故障排查

| 现象 | 处理 |
|------|------|
| Home Assistant 登录失败 | 核对 HA Web UI 管理员账号密码，并确认 8123 端口网络可达 |
| HA 无法访问 Frigate 或 MQTT | 当 HA 与 Frigate 运行在不同设备时，将 `Frigate URL` 和 `MQTT Broker` 中的 `localhost` 改为 Frigate 设备的局域网 IP |
| 已有 HA MQTT 集成收不到 `frigate/events` | 若 HA 中已配置并加载了 MQTT 集成，引擎会直接复用现有连接而不会覆盖其 Broker 地址；请确保 Frigate（`config/config.yml` 中的 `mqtt.host`）与 HA 使用同一个 MQTT Broker，并在启用告警前于 HA 中验证能收到 `frigate/events` 消息 |

## 套餐: reComputer RK3588 {#rk3588}

在 reComputer RK3588 上用 Frigate NVR 和 Rockchip NPU 加速做实时枪支检测，检测到枪支时自动录像和截图，可通过 MQTT 对接报警系统。

- **设备：** reComputer RK3588；网络摄像头可选，不接时用演示视频。
- **软件：** 目标设备已安装 Docker 和 Rockchip NPU 运行时（RKNN），至少 4 GB 可用磁盘。
- **网络：** 摄像头、reComputer RK3588 和这台电脑在同一网络。

## 步骤 1: 初始化摄像头 {#init_cameras_rk3588 type=manual required=false}

获取网络摄像头的 RTSP 视频流地址。只用演示视频时跳过。

### 接线

1. 将网络摄像头接入与 reComputer RK3588 相同的网络
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

## 步骤 2: 部署 Frigate {#deploy_frigate_rk3588 type=docker_deploy required=true config=devices/rk3588_deploy.yaml}

将 Frigate NVR 和 RKNN 枪支检测模型部署到 reComputer RK3588。

### 部署目标 {#rk3588_remote type=remote config=devices/rk3588_deploy.yaml default=true}

通过 SSH 部署到网络上的 reComputer RK3588。

### 接线

1. 在设备上确认 NPU 和硬件编解码节点存在（如 `/dev/rknpu` 或 `/dev/dri`）
2. 将设备接入与电脑相同的网络
3. 输入设备的 IP 地址和 SSH 凭据
4. 可选填写 RTSP 摄像头地址（最多 2 个）
5. 点击 **部署**

### 部署完成

打开 **http://\<设备IP\>:5000**，能看到两路演示视频上的枪支检测框；填写了 RTSP 地址时，你的摄像头也会出现。

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 NPU 或编解码设备节点 | 确认目标设备使用已加载 Rockchip NPU/MPP 驱动的 reComputer RK3588 系统镜像（`ls /dev/rknpu /dev/dri`） |
| 磁盘空间不足 | 至少需要 4 GB，执行 `docker system prune -a` 和 `sudo apt clean` 释放空间 |
| 端口 5000 被占用 | `docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 进入 `~/gun-detection-rk3588/rk3588_deploy` 执行 `docker compose -p gun-detection-rk3588 logs` 查看 NPU 或运行时报错 |
| RTSP 摄像头未显示 | 用 VLC 验证地址，按步骤 3 修改 `config/config.yml` 后重启 |

### 部署目标 {#rk3588_local type=local config=devices/rk3588_deploy.yaml}

部署到本机。本机须为已安装 Docker 和 Rockchip NPU 运行时的 reComputer RK3588，至少 4 GB 可用磁盘。

### 接线

1. 确认 Docker 正在运行且 NPU 设备节点存在（如 `/dev/rknpu` 或 `/dev/dri`）
2. 点击 **部署**

### 部署完成

打开 **http://localhost:5000**，能看到两路演示视频上的枪支检测框。

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 NPU 或编解码设备节点 | 确认本机使用已加载 Rockchip NPU/MPP 驱动的 reComputer RK3588 系统镜像（`ls /dev/rknpu /dev/dri`） |
| 端口 5000 被占用 | `docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 进入 `~/gun-detection-rk3588/rk3588_deploy` 执行 `docker compose -p gun-detection-rk3588 logs` 查看 NPU 或运行时报错 |

## 步骤 3: 打开面板 {#dashboard_rk3588 type=web_dashboard required=true config=devices/dashboard.yaml}

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
cd ~/gun-detection-rk3588/rk3588_deploy
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
docker compose -p gun-detection-rk3588 restart
```

#### 后续步骤

- 通过 MQTT（端口 1883）配置告警通知
- 在 `config/config.yml` 中调整检测阈值（`objects.filters.gun.threshold`）
- 设置录像保留天数（`record.retain.days`）
- [Frigate 官方文档](https://docs.frigate.video/)

## 步骤 4: 部署 Home Assistant（可选） {#deploy_ha_rk3588 type=docker_deploy required=false config=devices/ha_host.yaml}

仅在尚未安装 Home Assistant 时勾选此步骤。如果目标主机 8123 端口已运行 Home Assistant，部署器会自动检测并跳过安装；如果已有独立的 HAOS 或外部 HA 实例，直接取消勾选并跳到步骤 5。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 端口已运行 Home Assistant | 部署器会检测到已有实例并自动跳过安装，直接进入步骤 5 |
| 在 macOS 或 Windows 上本地安装失败 | 容器使用 Docker host 网络模式，Docker Desktop 在 macOS/Windows 上默认未开启该模式（需 Docker Desktop 4.34+ 并在设置中手动开启 host networking，否则请改用远程 SSH 部署到 Linux 主机或接入已有 HA 实例） |

### 部署目标: 本地部署 {#ha_local_rk3588 type=local default=true}

通过本地 Docker 在当前机器部署 Home Assistant。

### 部署目标: 通过 SSH 远程部署 {#ha_remote_rk3588 type=remote}

通过 SSH 在远程 Linux 主机（如 reComputer RK3588 或局域网内其他服务器）上部署 Home Assistant。

## 步骤 5: 将 Frigate 接入 Home Assistant（可选） {#connect_ha_rk3588 type=ha_integration required=false config=devices/ha_integration_rk3588.yaml}

自动安装官方 `frigate-hass-integration`（`v5.15.7`，兼容 HAOS、本机 Docker 与远程 Docker 版 HA）并重启 Home Assistant，完成 Frigate 集成与 MQTT 集成配置，同时创建默认枪支检测持久化告警自动化（`gun_detection_ha_alert`）。

### 前置条件

- **远程 Docker 版 HA：** 需在顶部 SSH 区域填写 HA 宿主机 SSH 凭据，在下方填写 HA Web UI 管理员账号密码（全新部署的 HA 将自动用此账号完成初始化）；HAOS 或本机 Docker 版无需额外手动配置 SSH Add-on。
- **跨设备部署：** 若 Frigate 本地部署（`localhost`）但 HA 运行在另一台设备，需将 `Frigate URL` 和 `MQTT Broker` 中的地址改为 Frigate 设备的局域网 IP。
- **已有 MQTT 集成：** 如果 Home Assistant 之前已经配置并加载了 MQTT 集成，引擎会直接复用现有连接而不会覆盖其 Broker 地址；此时必须确保 Frigate（`config/config.yml` 中的 `mqtt.host`）与 Home Assistant 使用同一个 MQTT Broker，并在启用告警前于 Home Assistant 中验证能收到 `frigate/events` 消息。

### 部署完成

> **注意：** 请勿直接修改自动创建的 `[Managed by SenseCraft: gun_detection_frigate] Gun Detection Alert` 自动化——重新部署方案会覆盖受管自动化并导致自定义修改丢失。

如需将枪支检测告警推送到手机并确保重新部署后配置不丢失，可通过以下两种方式配置：

1. **新建一条独立的自定义自动化：**
   在 HA「设置 → 自动化与场景 → 创建自动化 → 创建新自动化」中切换为 YAML 编辑模式，新建独立自动化并使用 Frigate 集成代理的抓拍图路径 `/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg`（外网经 HA 代理即可看图，无需直接暴露 Frigate）。

   **iOS Critical Alert 示例：**

   ```yaml
   alias: "Gun Detection Mobile Push (iOS)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           push:
             sound:
               name: default
               critical: 1
               volume: 1.0
   ```

   **Android 高优先级通道示例：**

   ```yaml
   alias: "Gun Detection Mobile Push (Android)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           ttl: 0
           priority: high
           channel: alarm_stream
   ```

2. **使用社区 Blueprint：**
   在 HA 中导入 **Frigate Notifications Blueprint**，可视化选择摄像头、`gun` 标签、目标手机以及强提醒或静音按钮。该方式创建的自动化同样独立于受管自动化，重新部署方案后不会丢失。

### 故障排查

| 现象 | 处理 |
|------|------|
| Home Assistant 登录失败 | 核对 HA Web UI 管理员账号密码，并确认 8123 端口网络可达 |
| HA 无法访问 Frigate 或 MQTT | 当 HA 与 Frigate 运行在不同设备时，将 `Frigate URL` 和 `MQTT Broker` 中的 `localhost` 改为 Frigate 设备的局域网 IP |
| 已有 HA MQTT 集成收不到 `frigate/events` | 若 HA 中已配置并加载了 MQTT 集成，引擎会直接复用现有连接而不会覆盖其 Broker 地址；请确保 Frigate（`config/config.yml` 中的 `mqtt.host`）与 HA 使用同一个 MQTT Broker，并在启用告警前于 HA 中验证能收到 `frigate/events` 消息 |

## 套餐: reComputer RK3576 {#rk3576}

在 reComputer RK3576 上用 Frigate NVR 和 Rockchip NPU 加速做实时枪支检测，检测到枪支时自动录像和截图，可通过 MQTT 对接报警系统。

- **设备：** reComputer RK3576；网络摄像头可选，不接时用演示视频。
- **软件：** 目标设备已安装 Docker 和 Rockchip NPU 运行时（RKNN），至少 4 GB 可用磁盘。
- **网络：** 摄像头、reComputer RK3576 和这台电脑在同一网络。

## 步骤 1: 初始化摄像头 {#init_cameras_rk3576 type=manual required=false}

获取网络摄像头的 RTSP 视频流地址。只用演示视频时跳过。

### 接线

1. 将网络摄像头接入与 reComputer RK3576 相同的网络
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

## 步骤 2: 部署 Frigate {#deploy_frigate_rk3576 type=docker_deploy required=true config=devices/rk3576_deploy.yaml}

将 Frigate NVR 和 RKNN 枪支检测模型部署到 reComputer RK3576。

### 部署目标 {#rk3576_remote type=remote config=devices/rk3576_deploy.yaml default=true}

通过 SSH 部署到网络上的 reComputer RK3576。

### 接线

1. 在设备上确认 NPU 和硬件编解码节点存在（如 `/dev/rknpu` 或 `/dev/dri`）
2. 将设备接入与电脑相同的网络
3. 输入设备的 IP 地址和 SSH 凭据
4. 可选填写 RTSP 摄像头地址（最多 2 个）
5. 点击 **部署**

### 部署完成

打开 **http://\<设备IP\>:5000**，能看到两路演示视频上的枪支检测框；填写了 RTSP 地址时，你的摄像头也会出现。

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 NPU 或编解码设备节点 | 确认目标设备使用已加载 Rockchip NPU/MPP 驱动的 reComputer RK3576 系统镜像（`ls /dev/rknpu /dev/dri`） |
| 磁盘空间不足 | 至少需要 4 GB，执行 `docker system prune -a` 和 `sudo apt clean` 释放空间 |
| 端口 5000 被占用 | `docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 进入 `~/gun-detection-rk3576/rk3576_deploy` 执行 `docker compose -p gun-detection-rk3576 logs` 查看 NPU 或运行时报错 |
| RTSP 摄像头未显示 | 用 VLC 验证地址，按步骤 3 修改 `config/config.yml` 后重启 |

### 部署目标 {#rk3576_local type=local config=devices/rk3576_deploy.yaml}

部署到本机。本机须为已安装 Docker 和 Rockchip NPU 运行时的 reComputer RK3576，至少 4 GB 可用磁盘。

### 接线

1. 确认 Docker 正在运行且 NPU 设备节点存在（如 `/dev/rknpu` 或 `/dev/dri`）
2. 点击 **部署**

### 部署完成

打开 **http://localhost:5000**，能看到两路演示视频上的枪支检测框。

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到 NPU 或编解码设备节点 | 确认本机使用已加载 Rockchip NPU/MPP 驱动的 reComputer RK3576 系统镜像（`ls /dev/rknpu /dev/dri`） |
| 端口 5000 被占用 | `docker stop $(docker ps -q --filter publish=5000)` |
| 容器反复重启 | 进入 `~/gun-detection-rk3576/rk3576_deploy` 执行 `docker compose -p gun-detection-rk3576 logs` 查看 NPU 或运行时报错 |

## 步骤 3: 打开面板 {#dashboard_rk3576 type=web_dashboard required=true config=devices/dashboard.yaml}

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
cd ~/gun-detection-rk3576/rk3576_deploy
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
docker compose -p gun-detection-rk3576 restart
```

#### 后续步骤

- 通过 MQTT（端口 1883）配置告警通知
- 在 `config/config.yml` 中调整检测阈值（`objects.filters.gun.threshold`）
- 设置录像保留天数（`record.retain.days`）
- [Frigate 官方文档](https://docs.frigate.video/)

## 步骤 4: 部署 Home Assistant（可选） {#deploy_ha_rk3576 type=docker_deploy required=false config=devices/ha_host.yaml}

仅在尚未安装 Home Assistant 时勾选此步骤。如果目标主机 8123 端口已运行 Home Assistant，部署器会自动检测并跳过安装；如果已有独立的 HAOS 或外部 HA 实例，直接取消勾选并跳到步骤 5。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 端口已运行 Home Assistant | 部署器会检测到已有实例并自动跳过安装，直接进入步骤 5 |
| 在 macOS 或 Windows 上本地安装失败 | 容器使用 Docker host 网络模式，Docker Desktop 在 macOS/Windows 上默认未开启该模式（需 Docker Desktop 4.34+ 并在设置中手动开启 host networking，否则请改用远程 SSH 部署到 Linux 主机或接入已有 HA 实例） |

### 部署目标: 本地部署 {#ha_local_rk3576 type=local default=true}

通过本地 Docker 在当前机器部署 Home Assistant。

### 部署目标: 通过 SSH 远程部署 {#ha_remote_rk3576 type=remote}

通过 SSH 在远程 Linux 主机（如 reComputer RK3576 或局域网内其他服务器）上部署 Home Assistant。

## 步骤 5: 将 Frigate 接入 Home Assistant（可选） {#connect_ha_rk3576 type=ha_integration required=false config=devices/ha_integration_rk3576.yaml}

自动安装官方 `frigate-hass-integration`（`v5.15.7`，兼容 HAOS、本机 Docker 与远程 Docker 版 HA）并重启 Home Assistant，完成 Frigate 集成与 MQTT 集成配置，同时创建默认枪支检测持久化告警自动化（`gun_detection_ha_alert`）。

### 前置条件

- **远程 Docker 版 HA：** 需在顶部 SSH 区域填写 HA 宿主机 SSH 凭据，在下方填写 HA Web UI 管理员账号密码（全新部署的 HA 将自动用此账号完成初始化）；HAOS 或本机 Docker 版无需额外手动配置 SSH Add-on。
- **跨设备部署：** 若 Frigate 本地部署（`localhost`）但 HA 运行在另一台设备，需将 `Frigate URL` 和 `MQTT Broker` 中的地址改为 Frigate 设备的局域网 IP。
- **已有 MQTT 集成：** 如果 Home Assistant 之前已经配置并加载了 MQTT 集成，引擎会直接复用现有连接而不会覆盖其 Broker 地址；此时必须确保 Frigate（`config/config.yml` 中的 `mqtt.host`）与 Home Assistant 使用同一个 MQTT Broker，并在启用告警前于 Home Assistant 中验证能收到 `frigate/events` 消息。

### 部署完成

> **注意：** 请勿直接修改自动创建的 `[Managed by SenseCraft: gun_detection_frigate] Gun Detection Alert` 自动化——重新部署方案会覆盖受管自动化并导致自定义修改丢失。

如需将枪支检测告警推送到手机并确保重新部署后配置不丢失，可通过以下两种方式配置：

1. **新建一条独立的自定义自动化：**
   在 HA「设置 → 自动化与场景 → 创建自动化 → 创建新自动化」中切换为 YAML 编辑模式，新建独立自动化并使用 Frigate 集成代理的抓拍图路径 `/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg`（外网经 HA 代理即可看图，无需直接暴露 Frigate）。

   **iOS Critical Alert 示例：**

   ```yaml
   alias: "Gun Detection Mobile Push (iOS)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           push:
             sound:
               name: default
               critical: 1
               volume: 1.0
   ```

   **Android 高优先级通道示例：**

   ```yaml
   alias: "Gun Detection Mobile Push (Android)"
   mode: single
   trigger:
     - platform: mqtt
       topic: "frigate/events"
   condition:
     - condition: template
       value_template: "{{ trigger.payload_json is defined and trigger.payload_json.get('type') == 'new' and trigger.payload_json.get('after', {}).get('label') == 'gun' }}"
   action:
     - action: notify.mobile_app_<your_phone>
       data:
         title: "Gun Detected"
         message: "Camera: {{ trigger.payload_json.after.camera }}"
         data:
           image: "/api/frigate/notifications/{{ trigger.payload_json.after.id }}/snapshot.jpg"
           ttl: 0
           priority: high
           channel: alarm_stream
   ```

2. **使用社区 Blueprint：**
   在 HA 中导入 **Frigate Notifications Blueprint**，可视化选择摄像头、`gun` 标签、目标手机以及强提醒或静音按钮。该方式创建的自动化同样独立于受管自动化，重新部署方案后不会丢失。

### 故障排查

| 现象 | 处理 |
|------|------|
| Home Assistant 登录失败 | 核对 HA Web UI 管理员账号密码，并确认 8123 端口网络可达 |
| HA 无法访问 Frigate 或 MQTT | 当 HA 与 Frigate 运行在不同设备时，将 `Frigate URL` 和 `MQTT Broker` 中的 `localhost` 改为 Frigate 设备的局域网 IP |
| 已有 HA MQTT 集成收不到 `frigate/events` | 若 HA 中已配置并加载了 MQTT 集成，引擎会直接复用现有连接而不会覆盖其 Broker 地址；请确保 Frigate（`config/config.yml` 中的 `mqtt.host`）与 HA 使用同一个 MQTT Broker，并在启用告警前于 HA 中验证能收到 `frigate/events` 消息 |
