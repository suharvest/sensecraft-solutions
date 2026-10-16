## 套餐：reCamera 2002 {#recamera_2002}

在 reCamera 2002 上安装选区运动检测器。检测在摄像头本机运行，不需要外部模型或云服务。

- **设备：** 可通过网络或 USB SSH 访问的 reCamera 2002。
- **网络：** SenseCraft Solution 所在电脑需要能够通过 SSH 访问摄像头。
- **摄像头占用：** 同一时间只能运行一个摄像头视频管线。应用运行时会停止系统自带的 ONVIF 和 SSCMA 摄像头服务。

## 步骤 1：安装运动检测 {#install_motion type=recamera_cpp required=true config=devices/recamera_motion.yaml}

填写摄像头地址和 SSH 凭据。部署器会传输并安装 Debian 软件包，然后通过 reCamera 应用管理器启动服务。

### 部署目标 {#camera type=remote device_name="reCamera 2002" config=devices/recamera_motion.yaml default=true}

USB 连接通常使用 `192.168.42.1`。使用 Wi-Fi 或以太网时，请填写摄像头当前 IP 地址。默认 SSH 用户为 `recamera`。

## 步骤 2：检查服务 {#verify_health type=http_debug required=true config=devices/verify_health.yaml}

请求 `/api/health`。收到成功响应表示 HTTP 服务已运行，JSON 响应会显示 RTSP、抓拍和 Webhook 状态。

### 部署完成

- HTTP API：`http://<摄像头IP>:8080/api/health`
- RTSP 视频流：`rtsp://<摄像头IP>:8554/live0`
- Home Assistant：安装 [reCamera 集成](https://github.com/yyling0101-a11y/recamera-ha)，即可绘制检测区域、查看抓拍并接收告警。

### 故障排查

| 现象 | 处理方法 |
|------|----------|
| SSH 连接失败 | 检查摄像头 IP、USB 线或网络、用户名和密码。 |
| 健康检查失败 | 在 Solution 中查看应用状态，并检查摄像头上的 `/var/log/recamera-motion.log`。 |
| 摄像头预览不可用 | 在 Solution 中停止本应用，再启动其他需要摄像头的应用。 |
