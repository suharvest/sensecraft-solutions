## 套餐: IP 摄像头 + 边缘算力盒子 {#ip_camera_box}

出入口的网络摄像头把画面送给旁边的 reComputer，设备在画面里的计数线上统计车辆进出，并把场内车辆数和剩余车位发到你的 MQTT 服务器。

| 设备 | 用途 |
|------|------|
| reComputer J30 / J40（Jetson Orin Nano / Orin NX，JetPack 6.2）或 reComputer RK3588 / RK3576 系列 | 分析摄像头画面、统计进出车辆 |
| 出入口网络摄像头 | 拍摄车道，提供 RTSP 视频流 |
| MQTT 服务器 | 接收进出记录和剩余车位 |

**部署完成后你可以：**

- 每辆车越线时收到一条进出记录（方向、车型）
- 实时拿到场内车辆数和剩余车位
- 把数据接入停车管理系统、余位显示屏或 Home Assistant

**前提条件：** 摄像头 RTSP 地址可用 · 一台 MQTT 服务器（现场已有的或自行安装 Mosquitto） · 首次部署时设备能联网

## 步骤 1: 部署车辆计数应用 {#deploy_counting type=docker_deploy required=true config=devices/jetson_counting.yaml}

在 reComputer 上安装计数应用，填写摄像头和 MQTT 服务器。计数线在步骤 2 画。

### 前置条件

1. 已在电脑上用 VLC 打开过摄像头的 RTSP 地址，能看到出入口画面。
2. 已知道 MQTT 服务器的 IP 地址和端口（通常是 1883），以及用户名和密码（允许匿名连接则不需要）。
3. reComputer 已开机、接入局域网，并能访问互联网下载应用和模型。
4. Jetson：reComputer J30 / J40（Jetson Orin Nano / Orin NX），系统为 JetPack 6.2。其他模组或系统版本会在部署第一步停止。
5. 设备上至少有 1 GB 可用磁盘空间。

### 接线

1. 用网线把 reComputer 和摄像头接到同一个局域网（摄像头用 PoE 交换机供电时，reComputer 接在同一台交换机上即可）。
2. 摄像头固定拍摄车道，让车辆从画面一侧驶向另一侧，整辆车能完整入镜。
3. 填写摄像头地址、MQTT 服务器、停车场编号、出入口编号和车位总数，点击部署。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示 UNSUPPORTED_JETSON_MODULE 或 UNSUPPORTED_JETPACK | 本方案只支持 reComputer J30 / J40（Jetson Orin Nano / Orin NX）+ JetPack 6.2，换用对应设备或重刷系统 |
| 提示 MISSING_BOARD_LIBRARIES（RK3588 / RK3576） | 提示里列出了缺少的库，按板卡厂商的说明安装 RKNN 运行库、MPP/RGA、gstreamer1.0-rockchip 和 gstreamer1.0-plugins-bad 后重新部署 |
| 下载模型或应用失败 | 确认设备能访问互联网，然后重新部署；已下载的部分会复用 |
| 磁盘空间不足 | 清理设备上不用的文件或镜像，保证至少 1 GB 可用空间 |
| 计数服务没有启动，或等待就绪超时 | 在设备上运行 `docker logs edge-parking-counting-jetson`（RK3588 为 `edge-parking-counting-rk3588`，RK3576 为 `edge-parking-counting-rk3576`）查看报错 |
| 日志里出现 Address already in use | 设备上已有其他程序占用端口：8080 被占用时改「计数服务端口」；8099 被占用时，Jetson 改「状态检查端口」，RK3588 / RK3576 需先停掉占用 8099 的程序。改好后重新部署 |
| 填写的编号被拒绝 | 停车场编号和出入口编号只能用字母、数字、- 和 _ |

### 部署完成

部署最后一步会等计数服务就绪，日志显示部署成功即表示服务已在运行。接着在步骤 2 画计数线。

### 部署目标: reComputer J30 / J40（远程部署） {#counting_remote type=remote device=jetson device_name="reComputer J30 / J40" config=devices/jetson_counting.yaml default=true}

从这台电脑通过 SSH 部署到局域网里的 reComputer J30 / J40（Jetson Orin Nano / Orin NX，JetPack 6.2）。

### 部署目标: reComputer J30 / J40（本机部署） {#counting_local type=local device=jetson device_name="reComputer J30 / J40" config=devices/jetson_counting.yaml}

在 reComputer J30 / J40（Jetson Orin Nano / Orin NX，JetPack 6.2）本机上直接部署。

### 部署目标: RK3588（远程部署） {#rk3588_counting_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

从这台电脑通过 SSH 部署到局域网里的 reComputer RK3588 系列，每秒处理约 3 帧。

### 部署目标: RK3588（本机部署） {#rk3588_counting_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

在 reComputer RK3588 系列本机上直接部署，每秒处理约 3 帧。

### 部署目标: RK3576（远程部署） {#rk3576_counting_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_counting.yaml}

从这台电脑通过 SSH 部署到局域网里的 reComputer RK3576 系列，实测每秒处理 30 帧。

### 部署目标: RK3576（本机部署） {#rk3576_counting_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_counting.yaml}

在 reComputer RK3576 系列本机上直接部署，实测每秒处理 30 帧。

## 步骤 2: 画计数线 {#draw_line type=web_dashboard required=false config=devices/counting_editor.yaml}

打开计数线设置页，把计数线画在车道上，确认进出方向，填写场内现有车辆数。

### 接线

1. 设备 IP 和计数服务端口自动带入步骤 1 的值（本机部署时为 127.0.0.1），打开设置页，能看到摄像头实时画面。
2. 在画面上按住鼠标拖出一条线，横穿整条车道；拖动线两端的圆点可以微调。线放在车辆连续行驶通过、整车可见的位置，避开排队等候抬杆的地方。
3. 看线两侧的「进 IN」和「出 OUT」：「进」要在车辆驶入停车场后所在的一侧。反了就点「交换进出」。
4. 点「保存」。保存后立即生效，设备重启或重新部署后保留。
5. 在「场内现有车辆数」填入现在场内已停的车辆数，点「设置」。

### 部署完成

计数线已生效。车辆越过计数线时，进出记录和场内概况会发送到你的 MQTT 服务器。

#### 初始设置

1. 场内车辆数与实际不符时，随时在本页「场内现有车辆数」填入正确的数，点「设置」。
2. 「车位总数」用于计算剩余车位，在步骤 1 填写。要修改时在步骤 1 填入新值重新部署，已保存的计数线保留。

#### 快速验证

1. 保持设置页打开，让一辆车驶入出入口。车辆被框出，越线后「今日驶入」加 1，「在场」加 1，「空余」减 1。
2. 让车辆驶出，「今日驶出」加 1，「在场」减 1。
3. 驶入被记成驶出时，点「交换进出」，再点「保存」。
4. 在能访问 MQTT 服务器的电脑上订阅计数主题（把 `demo-lot` 换成你填写的停车场编号）。车辆越线后几秒内会收到一条 `.../crossing` 消息（`direction` 为 `in` 或 `out`）和一条 `.../occupancy` 消息：

   ```bash
   mosquitto_sub -h <MQTT 服务器 IP> -p 1883 -t 'demo-lot/parking/#' -v
   ```

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 确认 IP 是计数设备的地址、端口与步骤 1 的「计数服务端口」一致，电脑和设备在同一网络 |
| 页面打开了但没有画面 | 设备连不上摄像头：在同一网络里用 VLC 重新打开 RTSP 地址，检查路径、用户名和密码；RK3588 / RK3576 还要确认「摄像头视频编码」与摄像头设置一致。改好后重新部署 |
| 车辆越线了但计数不变 | 把线挪到整车清晰可见、车辆连续行驶通过的位置，点「保存」；线要横穿整条车道。使用 RK3588 时，确认车辆在画面中停留约 1 秒以上 |
| 驶入和驶出记反了 | 点「交换进出」，再点「保存」 |
| 提示「线太短」 | 拖动距离太短，重新在画面上拖出一条更长的线 |
| 点「保存」提示保存失败 | 刷新页面重新画线；仍然失败时在设备上运行 `docker logs edge-parking-counting-jetson`（RK3588 为 `edge-parking-counting-rk3588`，RK3576 为 `edge-parking-counting-rk3576`）查看报错 |
| 收不到 MQTT 消息 | 检查 MQTT 服务器地址、端口、用户名和密码，并确认设备能访问该服务器的 1883 端口，改好后重新部署 |
