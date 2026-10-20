## 套餐：reCamera 2002 {#recamera_2002}

在 reCamera 2002 上安装选区运动检测器。检测在摄像头本机运行，不需要外部模型或云服务。

- **设备：** 可通过网络或 USB SSH 访问的 reCamera 2002。
- **网络：** SenseCraft Solution 所在电脑需要能够通过 SSH 访问摄像头。
- **摄像头占用：** 同一时间只能运行一个摄像头视频管线。应用运行时会由控制台自动协调让出摄像头硬件。

## 步骤 1: 更新 reCamera 控制台 {#update_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.6 控制台，它负责管理相机应用。已经是该版本会自动跳过。

### 前置条件

1. 用 USB 连接 reCamera，或让它和这台电脑处于同一网络。
2. USB 连接的地址是 `192.168.42.1`；走 Wi-Fi 时用路由器上显示的 IP。
3. 默认密码是 `recamera`（较早期的设备用 `recamera.2`）。

---

## 步骤 2：安装运动检测 {#install_motion type=recamera_cpp required=true config=devices/recamera_motion.yaml}

填写摄像头地址和 SSH 凭据。部署器通过控制台官方接口优雅释放摄像头，传输并安装 Debian 软件包，随后启动并验证运动检测服务。

### 部署目标 {#camera type=remote device_name="reCamera 2002" config=devices/recamera_motion.yaml default=true}

USB 连接通常使用 `192.168.42.1`。使用 Wi-Fi 或以太网时，请填写摄像头当前 IP 地址。默认 SSH 用户为 `recamera`。

---

## 步骤 3：检查服务与实时画面 {#verify_health type=http_debug required=true config=devices/verify_health.yaml}

请求服务健康状态接口、运行状态与实时画面抓拍。收到成功响应表示 HTTP 服务与摄像头管线均正常工作。

### 部署完成

- HTTP API：`http://<摄像头IP>:8080/api/health`
- RTSP 视频流：`rtsp://<摄像头IP>:8554/live0`
- 实时抓拍：`http://<摄像头IP>:8080/api/snapshot.jpg`
- Home Assistant：安装 [reCamera 集成](https://github.com/yyling0101-a11y/recamera-ha)，即可绘制检测区域、查看抓拍并接收告警。

### 故障排查

| 现象 | 处理方法 |
|------|----------|
| SSH 连接失败 | 检查摄像头 IP、USB 线或网络、用户名和密码。 |
| 健康检查失败 | 在 Solution 中查看应用状态，并检查摄像头上的 `/var/log/recamera-motion.log`。 |
| 摄像头预览不可用 | 确认控制台已正常退出旧应用；重启设备后再次检查。 |
