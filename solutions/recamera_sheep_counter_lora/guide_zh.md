## 套餐: LoRa 网关（完整系统） {#lora_gateway}

实时计数穿越围栏的绵羊，并将 进/出/在栏 数量发送到您的手机和 Home Assistant 看板——即使在没有 WiFi 的牧场也能正常工作。

| 设备 | 用途 |
|------|------|
| reCamera 2002 | 运行 YOLO 绵羊检测和穿越计数程序 |
| XIAO ESP32-S3 + Wio-SX1262 | LoRa 发射节点（Meshtastic 固件） |
| reComputer R1100 / 树莓派 | 网关——将 LoRa 消息桥接到 MQTT 和 Home Assistant |

**部署后您将获得：**
- 每次羊只穿越围栏时自动更新的 进/出/在栏 计数
- 每 15 分钟一次的 LoRa 心跳，保持所有显示同步
- 带当日总计和趋势历史的 Home Assistant 实时看板
- 离网运行——只有网关电脑需要连接到局域网

**前提条件：** reCamera 通过 USB 或以太网连接 · XIAO ESP32-S3 + Wio-SX1262 LoRa 板 · 在本地网络上运行 Home Assistant 的 reComputer 或树莓派

---

## 步骤 1: 将绵羊计数器部署到 reCamera {#deploy_recamera type=recamera_cpp required=true config=devices/recamera.yaml}

将绵羊计数程序部署到 reCamera，开机自动启动。

### 接线

1. 通过 USB-C 或以太网将 reCamera 连接到您的电脑
2. 将 XIAO ESP32-S3 LoRa 节点连接到 reCamera 的 UART 端口（`/dev/ttyS3`）：
   - XIAO TX → reCamera RX
   - XIAO RX → reCamera TX
   - 共用 GND
3. 输入 reCamera 的 IP 地址（USB 默认为 `192.168.42.1`）和 SSH 密码

### 部署完成

部署会停止 reCamera 默认的 Node-RED 服务。部署完成后，通过 SSH 登录摄像头并查看日志，确认程序正在运行：

```
ssh recamera@192.168.42.1
tail -f /var/log/sheep_counter.log
```

当羊只穿越围栏线时，您应能看到类似 `EVT,IN,1,0,1,123` 的事件出现。

### 故障排查

| 问题 | 解决方案 |
|------|---------|
| SSH 连接失败 | 检查连接线缆；如果密码 `recamera` 无效，请尝试 `recamera.2` |
| 计数器立即退出 | 检查 `/var/log/sheep_counter.log`，然后执行 `/etc/init.d/S85sscma-keepalive restart` |
| 2 分钟后仍无日志输出 | 确认 SSCMA 推理守护进程正在运行：`/etc/init.d/S85sscma-keepalive start` |
| XIAO 未收到 UART 事件 | 确认 XIAO 与 reCamera 共用 GND；检查 `/dev/ttyS3` 接线 |

---

## 步骤 2: 配置 XIAO LoRa 发射节点 {#configure_xiao type=manual required=true}

为 XIAO ESP32-S3 刷写 Meshtastic 固件，并将其配置为串口 + 检测传感器节点。

### 接线

1. 通过 USB-C 将 XIAO ESP32-S3 连接到电脑
2. 在 Chrome/Edge 中打开 [Meshtastic 网页刷写工具](https://flasher.meshtastic.org/)
3. 选择 **XIAO ESP32-S3** 作为目标设备，刷写最新稳定版 Meshtastic 固件
4. 刷写完成后，打开 [Meshtastic 网页客户端](https://client.meshtastic.org/) 进行配置：
   - **串口模块** → 启用 → 波特率：`115200` → 接收模式：透传
   - **检测传感器模块** → 启用 → 监控 GPIO：`490` → 高电平检测 → 告警消息前缀：`SHEEP`
   - 设置唯一的**节点名称**（如 `SheepGate1`）以便在网格中识别
5. 将 XIAO 与 Meshtastic 兼容的 LoRa 接收器配对（手机 APP 或本地节点）

### 部署完成

配置完成后，短暂将 GPIO 490 拉高来触发一次测试穿越。您应该能看到：
- 30 秒内 Meshtastic 手机 APP 收到 "SHEEP" 告警
- 原始 `EVT,IN,...` 数据作为文本消息出现在您的 Meshtastic 频道中

### 故障排查

| 问题 | 解决方案 |
|------|---------|
| 刷写工具无法检测到 XIAO | 插入 USB 时按住 BOOT 键；端口出现后松开 |
| 网格中无消息 | 检查 RF 频率是否与所有网格节点一致；确认频道预设相同 |
| 串口数据乱码 | 确认 XIAO 串口模块和 reCamera UART 的波特率均为 115200 |
| GPIO 告警未触发 | 验证 sheep_counter 二进制文件在每次穿越时是否向 GPIO 490 发送 ~0.5 秒脉冲 |

---

## 步骤 3: 将网关桥接服务部署到 reComputer {#deploy_gateway type=docker_deploy required=true config=devices/gateway.yaml}

通过 SSH 将桥接服务以两个 Docker 容器（`sheep-meshtastic-bridge`、`sheep-ha-bridge`）部署到网关电脑，把 LoRa 收到的羊只计数通过 MQTT 发布到 Home Assistant。

开始部署前，请确认 Home Assistant 已在局域网中运行，且 MQTT 集成已连接到同一 Broker 并启用自动发现。部署表单中需要填写网关 SSH 连接、MQTT Broker IP 和 Meshtastic 接收器串口。

### 前置条件

- 网关已安装 Docker 和 Docker Compose 插件（`docker compose version` 能输出版本号）。
- 网关首次启动时需能拉取 `python:3.11-slim` 镜像，并从 PyPI 安装 Python 包（`paho-mqtt`、`meshtastic`）。国内网络会自动使用 PyPI 镜像。
- 网关能访问 MQTT Broker 的 1883 端口。请填写 Broker 的局域网 IP；`127.0.0.1` 指向容器自身。
- 如果网关曾用本方案早期的 `install.sh` 安装过，请先停止并禁用它创建的两个 systemd 服务。这两个服务从 `/opt/sheep-gateway` 运行、会自动重启，并占用新容器需要的 Meshtastic 串口：

  ```
  sudo systemctl disable --now meshtastic-bridge ha-bridge
  sudo rm /etc/systemd/system/meshtastic-bridge.service /etc/systemd/system/ha-bridge.service
  sudo systemctl daemon-reload
  ```

  `/opt/sheep-gateway` 不再使用，可用 `sudo rm -rf /opt/sheep-gateway` 删除。

### 接线

1. 将 LoRa 接收节点（第二个 Meshtastic 设备，如串口或 USB Meshtastic 无线电）连接到网关电脑

### 部署完成

部署完成后，验证两个容器是否在运行：

```
ssh recomputer@<网关-ip>
docker ps --filter name=sheep- --format '{{.Names}}\t{{.Status}}'
```

`sheep-meshtastic-bridge` 和 `sheep-ha-bridge` 均应显示 `Up`。首次启动需要安装 Python 包，比之后的重启多约一分钟。

将 `ha_dashboard.yaml` 导入 Home Assistant：
1. 将此方案包中的 `assets/gateway/ha_dashboard.yaml` 复制到 HA 配置目录（使用远程部署时，部署也会将该文件上传到网关的 `~/sheep-gateway/gateway/ha_dashboard.yaml`）
2. 在 HA 中：设置 → 仪表盘 → 导入 → 选择该文件

### 故障排查

| 问题 | 解决方案 |
|------|---------|
| sheep-meshtastic-bridge 反复重启 | 确认 Meshtastic USB 无线电已插入网关，且串口路径正确（`ls /dev/ttyACM*`）；查看 `docker logs sheep-meshtastic-bridge` |
| sheep-ha-bridge 连接失败 | 确认 MQTT Broker IP 的 1883 端口可达，且允许网关连接 |
| 无 MQTT 消息 | 检查 MQTT Broker IP 是否正确，以及 Broker 是否接受 1883 端口的匿名连接 |
| 曾用早期 `install.sh` 安装的网关上，sheep-meshtastic-bridge 无法打开串口 | 旧的 `meshtastic-bridge` systemd 服务仍占用串口；用 `systemctl is-active meshtastic-bridge ha-bridge` 检查，并按前置条件中的步骤禁用这两个服务 |
| 重启后容器不在 | 容器设置了 `restart: unless-stopped`；用 `systemctl is-enabled docker` 确认 Docker 开机自启 |
| 容器日志中 `pip install` 失败 | 网关无法访问 PyPI；检查网关网络或 DNS，然后在 `~/sheep-gateway/gateway` 执行 `docker compose -p sheep_gateway restart`（远程部署），或重新部署此步骤 |

### Target: 网关（远程） {#gateway_remote type=remote device=gateway device_name="reComputer / Raspberry Pi" config=devices/gateway.yaml default=true}

通过 SSH 从本机部署到网关。填写网关 IP 地址和 SSH 凭据，然后填写 MQTT Broker IP 和串口。

### Target: 网关（本机） {#gateway_local type=local device=gateway device_name="reComputer / Raspberry Pi" config=devices/gateway.yaml}

在网关本机上执行部署。填写 MQTT Broker IP 和串口。

---

## 步骤 4: 打开绵羊计数看板 {#verify_dashboard type=web_dashboard required=true config=devices/ha_dashboard.yaml}

整个系统现已运行。点击下方链接打开 Home Assistant 绵羊计数看板，确认实时计数正常更新。

### 部署完成

您的绵羊计数器已上线！看板将显示：

- **进/出/在栏** — 自上次在看板重置后的实时计数
- **最近事件时间** — 最近一次穿越事件的时间戳
- **当日历史** — 24 小时趋势图

#### 快速验证

1. 在摄像头前挥手（或穿越围栏线）模拟一次穿越
2. 观察 reCamera 上 `/var/log/sheep_counter.log` 中出现的 `EVT,IN,...` 日志行
3. 约 30 秒内，HA 看板上的"进"计数器应递增

#### 使用技巧

- 将 reCamera 以一定角度安装在围栏旁，使羊只能清晰地穿越虚拟线
- 如果计数率偏低，请在计数器配置中调整围栏线位置
- LoRa 心跳（每 15 分钟一次的 `HB` 消息）可在无线电中断后保持显示同步

#### 下一步

- [项目源码与文档](https://github.com/biancayoung/recamera-sheep-counter-lora)
- 安装 Meshtastic 手机 APP，在牧场现场接收移动告警

### 故障排查

| 问题 | 解决方案 |
|------|---------|
| 看板页面无数据 | 确认 ha-bridge 正在运行、HA 已启用 MQTT 自动发现，且 `sensor.sheep_*` 实体已出现 |
| 计数未更新 | 手动触发一次穿越；通过 `mosquitto_sub -t sheep/# -v` 检查 MQTT 流量 |
| HA 实体显示"不可用" | 重新导入 `ha_dashboard.yaml` 并重启 ha-bridge 服务 |
