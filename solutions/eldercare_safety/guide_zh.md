# 居家养老安全守护部署指南

本方案在 reCamera Pro 设备上运行端侧一体化居家看护系统，结合视觉骨架跌倒检测与离线语音求助转写，实现毫秒级本地告警，全流程无需外网与云端服务。

---

## 套餐: reCamera Pro 一体化部署 {#recamera_pro}

单台 reCamera Pro 独立承担视频采集、YOLO11n-Pose 姿态计算、SenseVoice 离线求助词识别以及 MQTT 告警推送。

## 步骤 1: 检查或刷写固件 {#firmware_recamera_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

若您的 reCamera Pro 尚未刷入包含防清空保护（`RECAMERA_USERDATA_GUARD=1`）及应用中心的新固件，需先执行固件刷写。若设备已刷入新固件，可直接跳过此步。

### 前置要求与检查

- 在浏览器中访问设备 IP：`https://<device-ip>/`。
- 确认可登录管理页面且存在「应用中心」入口。
- 如需刷机，从官方发布地址下载固件镜像：[update.img.gz](https://sensecraft-statics.seeed.cc/solution-app/eldercare_safety/update.img.gz)（SHA-256: `baccc7d6fbd03394ebd5a9b58021eb3a6f2a0f2e5489f3033a2276850f1276cd`）。
- 解压固件：`gzip -dc update.img.gz > update.img`。
- 执行刷写命令（USB 处于 Loader 模式下）：`sudo ./upgrade_tool uf update.img`。

### 故障排查

| 现象 | 排查措施 |
|---|---|
| upgrade_tool 找不到设备 | 检查 Type-C 数据线是否正常连接，执行 `lsusb` 查看是否有 Rockchip 烧录设备 ID（如 `2207:110b`） |
| 无法通过 ADB 进入 Loader | 确认网络可达且 ADB 端口 5555 开放；或按住设备上的 Recovery/BOOT 按键后重新插电进入 Maskrom 模式 |

## 步骤 2: 部署居家看护应用 {#deploy_recamera_pro_eldercare type=recamera_pro_app required=true config=devices/recamera_pro_eldercare.yaml}

部署器会自动检查设备上的应用中心。若应用尚未安装，部署器将自动拉取官方经过安全签名的交付包（`eldercare-monitor-0.1.5-arm64.tar.gz` 及 `.sig` 签名）、流式上传至设备、执行验签安装，并下发配置将其切换为活动应用。

### 部署说明

- 设备为单活动应用架构：激活此应用会自动停止此前处于运行中的其他应用。
- **MQTT 为可选配置**：留空则仅在设备自带 Web 页面展示结果；填写 broker 地址后可将结构化跌倒与求救告警推送到 Home Assistant 或自建报警网关。
- 登录凭据为设备的 **Web 控制台凭据**（出厂默认用户名 `admin`，密码 `admin`）。

### 故障排查

| 现象 | 排查措施 |
|---|---|
| 登录提示 401 或密码错误 | 检查填写的 Web 管理员密码。连续输错会被设备临时锁定 IP |
| 提示签名验证失败 | 确认应用包签名有效，设备出厂已内置对应 Release 验证公钥 |
| 应用启动后无数据 | 登录设备 Web 控制台查看 App 运行日志，确认摄像头未被其他后台进程占用 |

### 部署目标 {#recamera_pro_device type=remote device_name="reCamera Pro" config=devices/recamera_pro_eldercare.yaml}

## 步骤 3: 查看居家看护控制台 {#verify_eldercare type=web_dashboard required=false config=devices/verify_eldercare.yaml}

在浏览器中打开设备控制台，验证跌倒骨架姿态渲染与离线语音识别效果。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 页面无法打开 | 访问 `https://<device-ip>/` 并使用 Web 控制台账号登录。接受自签名证书警告。 |
| MQTT 收不到告警 | 步骤 2 中 MQTT 为可选项；若 broker 地址留空，告警只显示在设备页面。否则请检查 broker 地址与端口（默认 1883）。 |

### 部署完成

- 打开设备管理页面：`https://<device-ip>/`。
- 进入「应用中心」->「Eldercare Monitor」，即可查看带骨骼关键点追踪的实时视频流与求助日志。
- 当受试者发生跌倒、或喊出“救命 / 快来人 / Help”时，页面将实时高亮告警并在 MQTT 主题上派发事件。

### 部署目标 {#verify_eldercare_device type=remote device_name="reCamera Pro" config=devices/verify_eldercare.yaml}
