## 套餐: IP 摄像头 + 边缘算力盒子 {#ip_camera_box}

出入口的网络摄像头把画面送给旁边的 reComputer，设备在画面里的计数线上统计车辆进出，并把场内车辆数和剩余车位发到你的 MQTT 服务器。

| 设备 | 用途 |
|------|------|
| reComputer J30 / J40（Jetson Orin Nano / Orin NX，JetPack 6.2）或 reComputer RK3588 系列 | 分析摄像头画面、统计进出车辆 |
| 出入口网络摄像头 | 拍摄车道，提供 RTSP 视频流 |
| MQTT 服务器 | 接收进出记录和剩余车位 |

**部署完成后你可以：**

- 每辆车越线时收到一条进出记录（方向、车型）
- 实时拿到场内车辆数和剩余车位
- 把数据接入停车管理系统、余位显示屏或 Home Assistant

**前提条件：** 摄像头 RTSP 地址可用 · 一台 MQTT 服务器（现场已有的或自行安装 Mosquitto） · 首次部署时设备能联网

## 步骤 1: 部署车辆计数应用 {#deploy_counting type=docker_deploy required=true config=devices/jetson_counting.yaml}

在 reComputer 上安装计数应用，填写摄像头、MQTT 服务器和计数线位置。

### 前置条件

1. 已在电脑上用 VLC 打开过摄像头的 RTSP 地址，能看到出入口画面。
2. 已知道 MQTT 服务器的 IP 地址和端口（通常是 1883），以及用户名和密码（允许匿名连接则不需要）。
3. reComputer 已开机、接入局域网，并能访问互联网下载应用和模型。
4. Jetson：reComputer J30 / J40（Jetson Orin Nano / Orin NX），系统为 JetPack 6.2。其他模组或系统版本会在部署第一步停止。
5. 设备上至少有 1 GB 可用磁盘空间。

### 接线

1. 用网线把 reComputer 和摄像头接到同一个局域网（摄像头用 PoE 交换机供电时，reComputer 接在同一台交换机上即可）。
2. 摄像头固定拍摄车道，让车辆从画面一侧驶向另一侧，整辆车能完整入镜。
3. 选计数线方向：车辆在画面里左右移动选「竖线」，上下移动选「横线」。计数线要横穿整条车道。
4. 选计数线位置（10–90）：竖线是距画面左边缘的百分比，横线是距画面上边缘的百分比。放在车辆连续行驶通过、整车可见的位置，避开排队等候抬杆的地方。
5. 填写摄像头地址、MQTT 服务器、停车场编号、出入口编号、车位总数和场内现有车辆数，点击部署。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示 UNSUPPORTED_JETSON_MODULE 或 UNSUPPORTED_JETPACK | 本方案只支持 reComputer J30 / J40（Jetson Orin Nano / Orin NX）+ JetPack 6.2，换用对应设备或重刷系统 |
| 提示 MISSING_BOARD_LIBRARIES（RK3588） | 提示里列出了缺少的库，按板卡厂商的说明安装 RKNN 运行库、MPP/RGA、gstreamer1.0-rockchip 和 gstreamer1.0-plugins-bad 后重新部署 |
| 下载模型或应用失败 | 确认设备能访问互联网，然后重新部署；已下载的部分会复用 |
| 磁盘空间不足 | 清理设备上不用的文件或镜像，保证至少 1 GB 可用空间 |
| 计数服务没有启动，或等待就绪超时 | 在设备上运行 `docker logs edge-parking-counting-jetson`（RK3588 为 `edge-parking-counting-rk3588`）查看报错 |
| 日志里出现 Address already in use | 设备上已有其他程序占用端口：8080 被占用时改「计数服务端口」；8099 被占用时，Jetson 改「状态检查端口」，RK3588 需先停掉占用 8099 的程序。改好后重新部署 |
| 填写的编号被拒绝 | 停车场编号和出入口编号只能用字母、数字、- 和 _ |

### 部署完成

部署最后一步会等计数服务就绪，日志显示部署成功即表示服务已在运行。在浏览器打开 `http://<设备IP>:8080/preview`（本机部署时设备 IP 为 127.0.0.1，端口以「计数服务端口」为准），能看到实时画面和计数线（也可以在步骤 2 直接打开）。

### 部署目标: reComputer J30 / J40（远程部署） {#counting_remote type=remote device=jetson device_name="reComputer J30 / J40" config=devices/jetson_counting.yaml default=true}

从这台电脑通过 SSH 部署到局域网里的 reComputer J30 / J40（Jetson Orin Nano / Orin NX，JetPack 6.2）。

### 部署目标: reComputer J30 / J40（本机部署） {#counting_local type=local device=jetson device_name="reComputer J30 / J40" config=devices/jetson_counting.yaml}

在 reComputer J30 / J40（Jetson Orin Nano / Orin NX，JetPack 6.2）本机上直接部署。

### 部署目标: RK3588（远程部署） {#rk3588_counting_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

从这台电脑通过 SSH 部署到局域网里的 reComputer RK3588 系列，每秒处理约 3 帧。

### 部署目标: RK3588（本机部署） {#rk3588_counting_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

在 reComputer RK3588 系列本机上直接部署，每秒处理约 3 帧。

## 步骤 2: 查看计数画面 {#view_counting type=web_dashboard required=false config=devices/preview.yaml}

打开计数预览，确认摄像头画面和计数线位置正常。

### 接线

1. 设备 IP 和计数服务端口会自动带入步骤 1 的值；本机部署时为 127.0.0.1
2. 打开预览页面，确认能看到摄像头实时画面和黄色计数线
3. 计数线不在车辆整车可见的位置时，回到步骤 1 调整「计数线位置（%）」后重新部署

### 部署完成

计数应用已在运行。车辆越过计数线时，进出记录和场内概况会发送到你的 MQTT 服务器。

#### 初始设置

1. 「场内现有车辆数」是第一次启动时的计数起点；之后设备重启或重新部署会沿用已保存的计数。
2. 「车位总数」用于计算剩余车位，按停车场实际车位数填写。
3. 场内车辆数与实际不符需要重设时：先在步骤 1 填入正确的「场内现有车辆数」并重新部署，再在设备上运行下面的命令（RK3588 把 `C=` 后的名称换成 `edge-parking-counting-rk3588`，`gate-a` 换成你的出入口编号）：

   ```bash
   C=edge-parking-counting-jetson
   D=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/data/edge-parking"}}{{.Source}}{{end}}{{end}}' $C)
   docker stop $C
   sudo rm "$D/gate-a/occupancy.json"
   docker start $C
   ```

#### 快速验证

1. 在能访问 MQTT 服务器的电脑上订阅计数主题（把 `demo-lot` 换成你填写的停车场编号）：

   ```bash
   mosquitto_sub -h <MQTT 服务器 IP> -p 1883 -t 'demo-lot/parking/#' -v
   ```

2. 让一辆车驶入出入口。越线后几秒内会收到一条 `.../crossing` 消息，`direction` 为 `in`，以及一条 `.../occupancy` 消息，`occupancy` 加 1、`free` 减 1。
3. 让车辆驶出，应收到 `direction` 为 `out` 的记录，`occupancy` 减 1。
4. 驶入被记成 `out`、驶出被记成 `in` 时，把「进场方向」改为另一项后重新部署。
5. 有车辆越线却没有记录时，把计数线挪到整车清晰可见、车辆连续行驶通过的位置；使用 RK3588 时，确认车辆在画面中停留约 1 秒以上。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 确认 IP 是计数设备的地址、端口与步骤 1 的「计数服务端口」一致，电脑和设备在同一网络 |
| 页面打开了但没有画面 | 设备连不上摄像头：在同一网络里用 VLC 重新打开 RTSP 地址，检查路径、用户名和密码；RK3588 还要确认「摄像头视频编码」与摄像头设置一致。改好后重新部署 |
| 收不到 MQTT 消息 | 检查 MQTT 服务器地址、端口、用户名和密码，并确认设备能访问该服务器的 1883 端口，改好后重新部署 |
