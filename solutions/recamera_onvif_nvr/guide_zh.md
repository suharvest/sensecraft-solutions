## 套餐: reCamera 2002W {#recamera_2002}

安装 ONVIF 网关后，预览与 NVR 或 Home Assistant 使用的同一条 RTSP 视频流。

## 步骤 1: 安装 ONVIF 网关 {#deploy_onvif type=recamera_cpp required=true config=devices/recamera_onvif.yaml}

安装网关并启动受应用管理器控制的摄像头服务。

### 前置条件

1. 通过 USB 连接 reCamera，或让它与本机处于同一网络。
2. 新设备请先在摄像头安全页面中启用 SSH。
3. 部署前停止当前占用摄像头的其他应用。

### 接线

1. 通过 USB-C 将 reCamera 连接到本机，或让它与本机接入同一局域网。
2. 等待摄像头完成启动，在部署表单中填写其 IP 地址和 SSH 密码。
3. 点击部署。SenseCraft 会将软件包安装到 `/userdata`，并启动受管理的 ONVIF 服务。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | USB 连接时使用 `192.168.42.1`；网络连接时填写路由器显示的摄像头 IP。 |
| 服务未启动 | 查看 `/var/log/recamera-onvif.log`；可能仍有其他摄像头应用占用设备。 |

## 步骤 2: 预览 ONVIF 视频流 {#preview_onvif type=video_stream required=true verify=true config=devices/rtsp_preview.yaml}

打开带认证的 RTSP 视频流，确认可以看到实时画面。

### 部署完成

在 NVR、VMS 或 Home Assistant 的 ONVIF 集成中使用以下信息：

| 配置项 | 值 |
|--------|----|
| ONVIF 服务 | `http://<camera-ip>:8000/onvif/device_service` |
| 自动发现 | UDP 端口 `3702` 上的 WS-Discovery |
| RTSP 视频流 | `rtsp://admin:recamera.1@<camera-ip>:8554/onvif` |
| 用户名 | `admin` |
| 密码 | `recamera.1` |

Home Assistant 中添加 ONVIF 集成，填入摄像头 IP、端口 `8000` 与上述账号。NVR 或 VMS 请先执行 ONVIF 自动发现；若 VLAN 间无法使用组播发现，则手动添加 ONVIF 服务地址。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 预览没有画面 | 等待摄像头服务启动后重试，并确认没有其他摄像头应用处于活动状态。 |
| NVR 无法发现摄像头 | 确认设备处于同一支持组播的网络；否则手动添加 ONVIF 服务地址。 |
| 认证失败 | 用户名和密码必须分别为 `admin` 与 `recamera.1`。 |
