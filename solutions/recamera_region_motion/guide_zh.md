## 套餐: reCamera 2002 {#recamera_2002}

在 reCamera 2002 上安装官方原生选区运动检测服务，并通过 MQTT 无缝接入 Home Assistant。算法直接在摄像头 CPU 本机运行，无需深度学习模型或云端依赖。

- **设备:** 通过网络或 USB SSH 可访问的 reCamera 2002。
- **Home Assistant:** 运行 Home Assistant 的本地电脑/服务器，或现有的 Home Assistant 实例（HAOS 或 Docker）。
- **摄像头独占:** 同一时间只能运行一条视频管线。控制台会在启动新检测器前协调独占访问。

## 步骤 1: 安装运动检测服务 {#install_motion type=recamera_cpp required=true config=devices/recamera_motion.yaml}

提供摄像头地址与 SSH 凭据。部署引擎会自动传输并安装 Debian 软件包，清理旧版本冲突服务，并启动官方原生选区运动检测服务。

### 准备工作

1. 通过 USB 连接 reCamera 或将其接入同一局域网。
2. USB 连接默认地址为 `192.168.42.1`；Wi-Fi 请使用路由器分配的 IP。
3. 默认密码为 `recamera`（早期固件尝试 `recamera.2`）。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| SSH 连接失败 | USB 连接使用 `192.168.42.1`；Wi-Fi 或有线网络使用相机 IP。SSH 用户名为 `recamera`，密码为 `recamera`，早期固件为 `recamera.2`。 |
| 检测服务未启动 | 部署器启动前会停止其他摄像头服务（Node-RED、YOLO 检测、人脸与跌倒检测等应用）。预览仍为空时，重启相机后重新运行本步骤。 |
| 设备上已有旧版运动检测包 | 本步骤安装前会停止旧版 `recamera-motion` 服务并卸载该包。 |

### 部署目标 {#camera type=remote device_name="reCamera 2002" config=devices/recamera_motion.yaml default=true}

USB 连接通常使用 `192.168.42.1`。使用 Wi-Fi 或以太网时，请输入摄像头当前的 IP 地址。默认 SSH 用户名为 `recamera`。

---

## 步骤 2: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

一键部署官方 Home Assistant 及配套的 Eclipse Mosquitto MQTT Broker 容器栈。

如果您已有运行中的外部 Home Assistant（如其他设备上的 HAOS）或现成的 MQTT Broker，**可直接跳过或取消勾选此步骤**，在 reCamera 控制台直接填入现有 Broker 地址。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant 和 Mosquitto Broker。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. Docker Desktop 已安装并运行。
2. 8123（Home Assistant）与 1883（Mosquitto）端口可用。
3. 若局域网内已有 HA 或 MQTT Broker，可直接跳过此步骤。

### 部署完成

1. 打开 **http://localhost:8123**，完成初始管理员账号设置。
2. 在 Home Assistant 中进入 **设置 (Settings) -> 设备与服务 (Devices & Services) -> 添加集成 (Add Integration)**，搜索并选择 **MQTT**。
3. Broker 地址填写本机 IP 或 `127.0.0.1`，端口 `1883`，用户名与密码留空，保存完成配置。
4. Mosquitto 此时已准备好接收来自 reCamera 的自动发现配置与检测事件。

### 故障排查

| 现象 | 解决方法 |
|------|------|
| 8123 或 1883 端口被占用 | 停掉现有的 Home Assistant 或 Mosquitto，或直接跳过此步骤使用现有服务 |
| Docker 起不来 | 打开 Docker Desktop 应用 |
| 容器反复重启 | 确认至少有 2 GB 可用内存 |

### 部署目标 {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

部署到局域网内的远程 Linux 边缘主机（如 reComputer）。

### 前置条件

1. 目标主机已安装 Docker，且可通过 SSH 访问。
2. 目标主机 8123 与 1883 端口可用。
3. 在下方填写主机 IP、用户名和密码。
4. 若已有外部 HA 或 Broker，可直接跳过此步骤。

### 部署完成

1. 打开 **http://<host-ip>:8123**，完成初始管理员账号设置。
2. 在 Home Assistant 中进入 **设置 (Settings) -> 设备与服务 (Devices & Services) -> 添加集成 (Add Integration)**，搜索并选择 **MQTT**。
3. Broker 地址填写远程主机 IP `<host-ip>`，端口 `1883`，用户名密码留空，保存完成配置。
4. 在 reCamera 控制台的「集成 -> Home Assistant」中填入该主机 IP 与端口 `1883`。

### 故障排查

| 现象 | 解决方法 |
|------|------|
| 连接超时 | 用 ping 确认网络连通 |
| SSH 认证失败 | 检查用户名密码是否正确 |
| 1883 端口已被占用 | 检测到已有 Broker；保留现有服务并跳过此步骤即可 |

---

## 步骤 3: 验证服务与实时预览 {#verify_health type=http_debug required=true config=devices/verify_health.yaml}

检查摄像头出流与实时画面抓拍是否正常。

### 部署完成

- **reCamera 控制台:** 在浏览器打开 `http://<camera-ip>/`。在实时调试画面下方，可直接用鼠标在视频上划定多边形选区，调整灵敏度与面积阈值。
- **Home Assistant 自动发现:** 在控制台「集成（Integrations）-> Home Assistant」页面填入 MQTT Broker 地址（主机 IP:1883），HA 将自动发现并生成运动传感器实体（`binary_sensor.recamera_motion`），无需安装任何第三方插件。
- **RTSP 视频流:** `rtsp://<camera-ip>:8554/live0`
- **实时快照:** `http://<camera-ip>:8001/snapshot.jpg`

### 故障排查

| 现象 | 解决方法 |
|---|---|
| SSH 连接失败 | 检查摄像头 IP、USB 线缆或网络、用户名及密码。 |
| 健康检查失败 | 确认设备已完成启动，并在浏览器中尝试直接访问 `http://<camera-ip>:8001/snapshot.jpg`。 |
| 摄像头预览不可用 | 确认前一个应用已完全释放摄像头管线；可重启设备后重新尝试。 |
