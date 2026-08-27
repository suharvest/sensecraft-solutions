## 套餐: AI 摄像头直连 {#recamera}

加一台电脑跑看板，保存历史数据，随时回看人流变化。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，识别人，把结果发到 MQTT |
| 电脑 或 reComputer R1100 | 运行 MQTT broker + InfluxDB + Grafana 看板 + 视频网关 |

摄像头只发 MQTT，不直接写数据库。多台设备（reCamera、Jetson、RK、树莓派）可以接到同一个 broker，数据汇总到同一个看板。

**部署完成后你可以：**
- 用图表看一天、一周的人流变化
- 自定义看板布局
- 导出数据做分析

**前提条件：** Docker 已安装 · 所有设备在同一网络

## 步骤 1: 启动数据看板 {#backend type=docker_deploy required=true config=devices/backend_deploy.yaml}

部署时会自动做一次 ONVIF 探测，把网络上的摄像头找出来并接进视频网关——看板右下角那格画面就是这么来的。**发现走的是组播，跨不了网段**：后端和摄像头不在同一广播域时（比如后端在云上）探测会是空的，那种情况在部署表单里手填摄像头地址。

在你的电脑（或专用服务器）上启动 MQTT broker、数据存储和图表显示服务。后续所有摄像头都往这里发数据。

### 部署目标 {#backend_local type=local config=devices/backend_deploy.yaml default=true}

### 接线

![接线图](gallery/architecture.svg)

确保 Docker Desktop 已安装并运行，至少 2GB 可用磁盘空间。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 关闭占用 8086 或 3000 端口的程序 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 启动后自动停止 | 确保电脑有至少 4GB 内存 |

### 部署目标 {#backend_remote type=remote config=devices/backend_deploy.yaml}

### 接线

![接线图](gallery/architecture.svg)

| 字段 | 示例 |
|------|------|
| 设备 IP | 192.168.1.100 或 reComputer-R110x.local |
| 用户名 | recomputer |
| 密码 | 12345678 |

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping 测试 |
| SSH 认证失败 | 确认用户名密码正确 |

---

## 步骤 2: 让摄像头发送数据 {#recamera type=recamera_cpp required=true config=devices/recamera_cpp.yaml}

在 reCamera 上安装零售分析应用，并告诉它把数据发到哪个 broker。

应用跑在摄像头本地：YOLO11n INT8 约 10 FPS，跨帧跟踪每位顾客，输出驻足状态（浏览 / 驻足 / 需要帮助）和进出店计数。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入 reCamera IP、MQTT 服务器 IP（来自步骤 1），以及安装点名称和摄像头编号

安装点名称和摄像头编号决定 MQTT 主题 `<安装点名称>/retail-vision/results/<摄像头编号>`，也是看板上区分多台设备的依据。同一个门店的多台摄像头用同一个安装点名称、不同的摄像头编号。

这一步会禁用 Node-RED 自启动——检测应用和 Node-RED 抢同一个摄像头，不能同时跑。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 看不到数据 | 确认步骤 1 已完成，reCamera 和服务器在同一网络 |
| 装完启动失败，日志里有 `device_init` 断言 | 上一个占用摄像头的应用没释放 TPU 显存，重启设备即可 |

---

## 步骤 3: 把热力图映射到平面图（可选） {#heatmap type=manual required=false}

默认热力图显示的是摄像头视角。如果想把热力图显示在你店铺的平面图上，用内置的校准工具即可。

### 操作步骤

1. 浏览器打开 **http://\<服务器IP\>:8080**
2. 点击右上角的 **齿轮图标**，打开校准设置
3. 在**校准哪台摄像头**里选中要校准的那台（选"全部"则作为所有未单独校准摄像头的默认值）
4. 左侧上传一张**摄像头截图**，右侧上传你的**店铺平面图**
5. 在摄像头截图上点 **4 个参考点**，再在平面图上点对应的 **4 个位置**
6. 点击**保存**，校准立即生效

平面图是共用的：多台摄像头各自校准后，人流会叠加到同一张平面图上。页面左上角的下拉框可以只看某一台。

**提示：** 选择间距大的明显标志物作为参考点，比如柱子、门口、墙角。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 热力图位置不准 | 重新打开设置，点重置，用更好的参考点重新校准 |
| 换了浏览器后校准还在 | 正常，校准保存在服务器上（`heatmap-config` 数据卷），不在浏览器里 |

### 什么时候可以跳过

如果只想看摄像头视角的热力图，不需要映射到平面图，可以跳过。

## 步骤 4: 打开面板 {#dashboard_recamera type=web_dashboard required=true config=devices/dashboard.yaml}

Grafana 面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

### 部署完成

热力图看板已就绪！

**访问服务：**
- **数据看板**：http://\<服务器IP\>:3000 — 用 `admin` / `admin` 登录，查看人流趋势图表
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984 — 摄像头发现与画面预览 — 实时热力图叠加（点齿轮图标可校准平面图）

两个服务在步骤 1 部署时就已自动启动。

**遇到问题？**
- 看不到数据？检查摄像头是否已连接（步骤 2），以及 MQTT 服务器 IP 填的是不是步骤 1 那台机器
- 打不开页面？运行 `docker ps` 检查服务是否在运行

---

## 套餐: reCamera Pro {#recamera_pro}

更新一代的一体机，同样一台摄像头搞定。分析应用随设备的应用中心分发，本套餐负责配置它、把结果发到你的看板。

| 设备 | 用途 |
|------|------|
| reCamera Pro | AI 摄像头，检测、跟踪、驻足状态、进出店计数全在本地 |
| 电脑 或 reComputer R1100 | 运行 MQTT broker + InfluxDB + Grafana 看板 + 视频网关 |

**前提条件：** 设备的应用中心里已安装 `retail-vision` 应用 · Docker 已安装 · 所有设备在同一网络

> 应用本身不随本方案分发——安装需要 release 签名包，签名链不公开。如果目标设备的应用中心里没有它，这一步会明确告诉你，并列出当前装了什么。

## 步骤 1: 启动数据看板 {#backend_pro type=docker_deploy required=true config=devices/backend_deploy.yaml}

部署时会自动做一次 ONVIF 探测，把网络上的摄像头找出来并接进视频网关——看板右下角那格画面就是这么来的。**发现走的是组播，跨不了网段**：后端和摄像头不在同一广播域时（比如后端在云上）探测会是空的，那种情况在部署表单里手填摄像头地址。

跟 AI 摄像头直连套餐是同一套后端。已经部署过就跳过。

### 部署目标 {#backend_pro_local type=local config=devices/backend_deploy.yaml default=true}

### 部署目标 {#backend_pro_remote type=remote config=devices/backend_deploy.yaml}

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 关闭占用 8086 或 3000 端口的程序 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 启动后自动停止 | 确保电脑有至少 4GB 内存 |

## 步骤 2: 配置摄像头 {#recamera_pro_app type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

填入设备的 Web 控制台账号（不是 SSH）、安装点名称，以及步骤 1 那台后端的 MQTT 地址。

MQTT 地址留空也能用——那样结果只在摄像头自带页面上看，不上报到看板。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示应用中心里没有 retail-vision | 先在设备的应用中心安装该应用，再重跑这一步 |
| 看板没有数据 | 确认 MQTT 地址填的是步骤 1 那台机器，且两者在同一网络 |
| 看板上 Avg Dwell 一直是空的 | 正常。Pro 的应用不输出人均驻足时长，其他指标不受影响 |

## 步骤 3: 打开面板 {#dashboard_pro type=web_dashboard required=true config=devices/dashboard.yaml}

Grafana 面板已经运行（登录账号 `admin` / `admin`）。

### 部署完成

**访问地址：**
- **数据看板**：http://\<服务器IP\>:3000
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984 — 摄像头发现与画面预览


### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

---

## 套餐: IP 摄像头 + 瑞芯微 NPU {#rk}

保留现有 IP 摄像头，加一块瑞芯微板卡在本地跑检测。

| 设备 | 用途 |
|------|------|
| reComputer RK3588 或 RK3576 | 在 NPU 上运行人流检测，结果发到 MQTT |
| IP 摄像头（RTSP） | 任何支持 RTSP 输出的摄像头 |
| 电脑 或 同一块板卡 | 运行 MQTT broker + InfluxDB + Grafana 看板 + 视频网关 |

**实测数据：** RK3588 13.2 fps / RK3576 13.3 fps，MQTT 稳定 1 msg/s。视频解码走 MPP 硬解，不占 CPU。

**前提条件：** Docker 已安装 · 板卡已装好 NPU 驱动（`/usr/lib/librknnrt.so` 存在）· 摄像头和板卡在同一网络

## 步骤 1: 启动数据看板 {#backend_rk type=docker_deploy required=true config=devices/backend_deploy.yaml}

部署时会自动做一次 ONVIF 探测，把网络上的摄像头找出来并接进视频网关——看板右下角那格画面就是这么来的。**发现走的是组播，跨不了网段**：后端和摄像头不在同一广播域时（比如后端在云上）探测会是空的，那种情况在部署表单里手填摄像头地址。

跟其他套餐是同一套后端。可以部署在这块板卡上，也可以部署在另一台机器上。已经部署过就跳过。

### 部署目标 {#backend_rk_local type=local config=devices/backend_deploy.yaml default=true}

### 部署目标 {#backend_rk_remote type=remote config=devices/backend_deploy.yaml}

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 关闭占用 8086 或 3000 端口的程序 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 启动后自动停止 | 确保电脑有至少 4GB 内存 |

## 步骤 2: 部署检测器 {#rk_detector type=docker_deploy required=true config=devices/rk_deploy.yaml}

通过 SSH 把检测器部署到板卡。选对板卡型号——模型是按 NPU 型号编译的，装错了加载不了。

如果后端就在这块板卡上，MQTT 地址保持 `127.0.0.1` 即可。

### 部署目标 {#rk_remote type=remote config=devices/rk_deploy.yaml default=true}

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 容器起不来，报 librknnrt 相关错误 | 板卡上缺 NPU 用户态库，确认 `/usr/lib/librknnrt.so` 存在 |
| 看板没数据 | 用 `ffprobe rtsp://...` 确认摄像头地址能通；检查 MQTT 地址填对 |
| 帧率明显偏低、CPU 占满 | 硬解没生效。容器里 `/root/.cache` 是 tmpfs 就是为了避免插件缓存问题，检查 MPP 库有没有挂进去 |

## 步骤 3: 打开面板 {#dashboard_rk type=web_dashboard required=true config=devices/dashboard.yaml}

### 部署完成

**访问地址：**
- **数据看板**：http://\<服务器IP\>:3000
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984 — 摄像头发现与画面预览


### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

---

## 套餐: IP 摄像头 + 树莓派 5（Hailo） {#hailo}

保留现有 IP 摄像头，加一块 Hailo-8 加速卡在本地跑检测。热路径是原生 C++，容器里没有 Torch / Ultralytics / ONNX Runtime / Python。

| 设备 | 用途 |
|------|------|
| 树莓派 5 + Hailo-8（或 reComputer R 系列） | 在加速卡上运行人流检测，结果发到 MQTT |
| IP 摄像头（RTSP） | 任何支持 RTSP 输出的摄像头 |
| 电脑 或 同一块板卡 | 运行 MQTT broker + InfluxDB + Grafana 看板 + 视频网关 |

**实测数据：** 对 15 fps 的 RTSP 源跟到 14.3 fps，MQTT 0.94 msg/s。不限速时同一条流水线跑到 234 fps、单帧推理 2.5–2.9 ms——约 15 倍源速率的余量。

**前提条件：** Docker 已安装 · HailoRT **4.21** 已装好（驱动、用户库、GStreamer 插件三者版本必须一致）· 摄像头和板卡在同一网络

> **一块 Hailo-8 同时只能跑一个应用。** HailoRT 把物理设备独占给单个进程。板子上如果已经有别的 Hailo 应用在跑（人脸识别之类），这个检测器起不来，会报 `HAILO_OUT_OF_PHYSICAL_DEVICES`。要同时跑多个应用，需要把板上**每一个** Hailo 消费者都改成走 `hailort.service` 多进程调度器，默认是关闭的。

## 步骤 1: 启动数据看板 {#backend_hailo type=docker_deploy required=true config=devices/backend_deploy.yaml}

部署时会自动做一次 ONVIF 探测，把网络上的摄像头找出来并接进视频网关——看板右下角那格画面就是这么来的。**发现走的是组播，跨不了网段**：后端和摄像头不在同一广播域时（比如后端在云上）探测会是空的，那种情况在部署表单里手填摄像头地址。

跟其他套餐是同一套后端。可以部署在这块板卡上，也可以部署在另一台机器上。已经部署过就跳过。

### 部署目标 {#backend_hailo_local type=local config=devices/backend_deploy.yaml default=true}

### 部署目标 {#backend_hailo_remote type=remote config=devices/backend_deploy.yaml}

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 关闭占用 8086 或 3000 端口的程序 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 启动后自动停止 | 确保电脑有至少 4GB 内存 |

## 步骤 2: 部署检测器 {#hailo_detector type=docker_deploy required=true config=devices/hailo_deploy.yaml}

通过 SSH 把检测器部署到板卡。部署前会检查 Hailo 运行时版本，不匹配会直接停下来并列出板上实际装的是哪个版本。

模型从 Hailo 官方 Model Zoo 下载并按 sha256 校验，不经第三方转存。

### 部署目标 {#hailo_remote type=remote config=devices/hailo_deploy.yaml default=true}

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 报 `HAILO_OUT_OF_PHYSICAL_DEVICES` | 加速卡被另一个应用占着，先停掉它（见上面的独占说明） |
| 部署时提示 libhailort 版本不符 | 板上的 HailoRT 不是 4.21，升级或降级到 4.21，注意驱动和用户库要一起换 |
| `/dev/hailo0` 不存在 | 加速卡没插好，或 `hailo_pci` 驱动没加载 |
| 看板没数据 | 用 `ffprobe rtsp://...` 确认摄像头地址能通；检查 MQTT 地址填对 |

## 步骤 3: 打开面板 {#dashboard_hailo type=web_dashboard required=true config=devices/dashboard.yaml}

### 部署完成

**访问地址：**
- **数据看板**：http://\<服务器IP\>:3000
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984 — 摄像头发现与画面预览

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

## 套餐: 传统摄像头改造 {#jetson}

手上有 IP 摄像头？加一台 NVIDIA Jetson，让传统摄像头变成智能人流传感器，不用换设备。

| 设备 | 用途 |
|------|------|
| NVIDIA Jetson（Orin 系列） | 在 GPU 上运行 YOLO11n TensorRT 检测，结果发到 MQTT |
| IP 摄像头（RTSP） | 任何支持 RTSP 输出的摄像头 |
| 电脑 或 同一台 Jetson | 运行 MQTT broker + InfluxDB + Grafana 看板 + 视频网关 |

**实测数据：** 单帧推理 9.7 ms（独立测得 48.6 FPS），MQTT 稳定 1 msg/s。跟 RK 和 Hailo 跑的是同一份跟踪与驻足判定代码。

**前提条件：** NVIDIA Jetson（JetPack 6.x）· Docker 含 NVIDIA runtime · 摄像头和 Jetson 在同一网络

## 步骤 1: 启动数据看板 {#backend_jetson type=docker_deploy required=true config=devices/backend_deploy.yaml}

部署时会自动做一次 ONVIF 探测，把网络上的摄像头找出来并接进视频网关——看板右下角那格画面就是这么来的。**发现走的是组播，跨不了网段**：后端和摄像头不在同一广播域时（比如后端在云上）探测会是空的，那种情况在部署表单里手填摄像头地址。

跟其他套餐是同一套后端。可以部署在这台 Jetson 上，也可以部署在另一台机器上。已经部署过就跳过。

### 部署目标 {#backend_jetson_local type=local config=devices/backend_deploy.yaml default=true}

### 部署目标 {#backend_jetson_remote type=remote config=devices/backend_deploy.yaml}

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 关闭占用 8086 或 3000 端口的程序 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 启动后自动停止 | 确保电脑有至少 4GB 内存 |

## 步骤 2: 部署检测器 {#jetson_deploy type=docker_deploy required=true config=devices/jetson_deploy.yaml}

通过 SSH 把检测器部署到 Jetson。

**首次部署会编译 TensorRT engine，需要 2-5 分钟**——TensorRT 的执行计划绑定 GPU 架构和 TensorRT 版本，没法随镜像分发，只能在本机生成。生成好之后存在命名卷里，后续部署直接复用。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网络，用 `ping` 验证 Jetson IP |
| NVIDIA 运行时错误 | 在 Jetson 上运行 `nvidia-smi` 确认 GPU 可用 |
| 没有数据 | 用 `ffprobe rtsp://...` 验证 RTSP 地址；检查 MQTT 地址填对 |
| 首次启动慢 | TensorRT engine 编译，仅一次，2-5 分钟 |

## 步骤 3: 打开面板 {#dashboard_jetson type=web_dashboard required=true config=devices/dashboard.yaml}

### 部署完成

**访问地址：**
- **数据看板**：http://\<服务器IP\>:3000
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984 — 摄像头发现与画面预览


### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

---
