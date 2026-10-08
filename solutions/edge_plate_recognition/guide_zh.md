# 边缘车牌识别 — 部署指南

> **草稿（staging）。** 仅 IP 摄像头套餐的 Jetson 部署目标通过了真机验收（部署与
> 输出链路，2026-10-08）。其余套餐与部署目标的模型、镜像与应用包仍在各平台任务中
> 产出。以下步骤为预期的部署流程，摘掉「草稿」标前会在真机上重新验证。

## 套餐: reCamera Pro（推荐） {#recamera_pro}

一台摄像头在机上完成检测、识别与 MQTT 事件。需要白名单开闸时加一台
reComputer R1124-10。

## 步骤 1: 安装车牌识别 {#deploy_pro type=recamera_pro_app required=true config=devices/recamera_pro_plate.yaml}

在 reCamera Pro 上配置车牌识别应用并将其设为运行中的应用。应用本身随设备
应用中心分发。

### 前置条件

1. reCamera Pro 已接入网络，且你能登录它的 Web 控制台。
2. 距车道 3–8 m、车牌清晰可辨的安装点位。摄像头需要 12 V 供电——不支持
   PoE。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 设备上找不到应用 | 应用包仍在 staging——上架后先从应用中心安装，再重跑本步骤 |
| 没有车牌事件 | 在预览页画车道 ROI；ROI 外的车牌不识别 |
| 夜间误识别 | 在出入口补红外/白光；信任白名单前先在夜间看一次预览 |

## 步骤 2: 查看识别结果 {#view_pro type=web_dashboard required=false config=devices/dashboard.yaml}

打开实时预览——车牌框与最新识别结果。MQTT 主题上出现带截图链接的车牌
事件，说明管线已端到端跑通。

## 步骤 3: 安装道闸控制器（可选） {#gate_pro type=script required=false config=devices/gate_controller.yaml}

在 reComputer R1124-10 上安装 MQTT broker 与开闸服务。开闸服务订阅车牌
事件、匹配白名单并给数字输出脉冲——带冷却保护，且不会把补发的历史事件
送进道闸。

## 步骤 4: 道闸接线（可选） {#wire_pro type=manual required=false config=devices/gate_wiring.yaml}

把 R1124-10 的数字输出经中间继电器接到道闸的「开闸」输入，然后上传白名单
并触发一次测试脉冲。

---

## 套餐: reCamera 2002 HQ PoE（最低配置） {#recamera_2002}

成本最低的方案：一台 PoE 摄像头守在出入口。最终形态（端上完整识别，或
端上检测 + R1124 主机侧识别）以平台验收实测为准——实测结论会写在这里。

## 步骤 1: 安装车牌识别 {#deploy_2002 type=recamera_cpp required=true config=devices/recamera_plate.yaml}

在 reCamera 2002 上安装车牌识别包（检测、识别、插件）并启动。

### 前置条件

1. reCamera 2002 网络可达（USB 默认 `192.168.42.1`），且你有它的 SSH
   密码。
2. 距车道 3–8 m 的安装点位；PoE 交换机或供电器供电。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 服务启动即退出 | 还有别的摄像头应用在运行；同一时刻只能有一个应用占用摄像头——重启后重试 |
| 装完后 Node-RED 不工作了 | 预期行为——安装会把摄像头从 Node-RED 和其他视觉应用手中接管 |
| 没有车牌事件 | 确认预览页上 ROI 覆盖车道，且安装距离下车牌像素足够 |

## 步骤 2: 查看识别结果 {#view_2002 type=web_dashboard required=false config=devices/dashboard.yaml}

打开实时预览——车牌框与最新识别结果。

## 步骤 3: 安装道闸控制器（可选） {#gate_2002 type=script required=false config=devices/gate_controller.yaml}

在 reComputer R1124-10 上安装 MQTT broker 与开闸服务。降级模式下这台主机
还要跑主机侧识别（plate-host），所以对 2002 来说 R1124 实际上是管线的
一部分，不只是开闸。

## 步骤 4: 道闸接线（可选） {#wire_2002 type=manual required=false config=devices/gate_wiring.yaml}

把 R1124-10 的数字输出经中间继电器接到道闸的「开闸」输入，然后上传白名单
并触发一次测试脉冲。

---

## 套餐: IP 摄像头 + 边缘算力盒子 {#ip_camera_box}

保留现有出入口摄像头——边缘算力盒子拉 RTSP 流，跑检测与识别。在部署步骤里
选择盒子：Jetson（TensorRT FP16）、RK3588 或 RK3576（NPU 上跑 RKNN INT8）、
R2035-12（Hailo-8）。每个部署目标写明了其真机验收状态。

## 步骤 1: 部署车牌识别 {#deploy_host type=docker_deploy required=true config=devices/jetson_plate.yaml}

在所选主机上部署识别栈。Jetson 目标使用已发布的停车镜像和已发布的检测、中文识别
TensorRT engine 模型包（Orin Nano、L4T R36.4 / JetPack 6.2、TensorRT 10.3 构建）；RK3588、RK3576 目标使用已发布的
RKNN 模型包；R2035 目标使用已发布的 HEF 模型包。模型包在部署时下载并校验 SHA-256。

### 前置条件

1. 出入口摄像头的 RTSP 地址（如需鉴权请带用户名密码）。
2. 摄像头距车道 3–8 m，1080p 及以上。
3. **Jetson：** 运行 JetPack 6.x，NVIDIA 容器运行时可用。除镜像和 engine 外
   至少 0.5 GiB 可用磁盘。已发布的停车镜像和 engine 模型包在部署时获取；你需要提供
   渲染后的 `vb.config/1` 文件。
   可选 `health_port` 默认 `8099`，须与挂载 JSON 中的 `health.port` 一致；宿主机
   8099 已被占用时两处一起改。可选 `memory_limit`（默认 `0`，不限）和 `data_dir`
   （默认 `./data`，已存在且可写，存放状态和快照）与计数包一致。
4. **RK3588 / RK3576：** 板子上已安装 RKNN 运行时（librknnrt）、Rockchip MPP/RGA 和
   GStreamer `h264parse` 插件（`gstreamer1.0-plugins-bad`）——容器使用这些宿主机库，
   部署步骤会检查它们是否存在。至少 6 GB 可用磁盘。容器使用宿主机网络：8099（健康
   检查）和 8080（应用 HTTP，即 `config/plate.json` 的 `app.options.http.port`）须空闲。
5. **R2035（Hailo-8）：** 已安装 Hailo-8 驱动与 HailoRT，且存在 `/dev/hailo0`。
   HailoRT 版本必须与驱动一致——需自行从 Hailo Developer Zone 获取。至少 6 GB
   可用磁盘。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 摄像头没有画面 | 先用 VLC 测 RTSP 地址；路径或凭据错误是最常见原因 |
| Jetson：engine 或运行时校验失败 | 确认镜像、配置、目标设备 engine 目录、NVIDIA 运行时均正确，且磁盘至少有 0.5 GiB 可用 |
| Jetson：容器反复重启 | 看日志里的 engine 路径；中断产生的半成品 engine 要删掉 |
| RK3588 / RK3576：找不到 librknnrt | 先为该板卡安装 RKNN 运行时（rknpu2） |
| RK3588：日志里 NPU 空闲 | 确认 RKNN 模型文件下载完整——截断的模型会报错或退化 |
| R2035：找不到 /dev/hailo0 | 先加载 Hailo-8 驱动再部署 |
| R2035：HailoRT 版本不一致 | 安装与驱动匹配的 HailoRT 包——预检会打印它找到的版本 |
| R2035：识别跑在 CPU 上 | 两个 network group 无法共享设备时的预期行为；准确率不受影响，吞吐较低 |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_plate.yaml default=true}

预编译的 TensorRT engine 只适用于 Jetson Orin Nano（P3767-0003 / P3767-0004）、L4T R36.4（JetPack 6.2）、TensorRT 10.3；在其他模组或 JetPack 版本上，部署步骤会直接停止。

从本机通过 SSH 部署到 Jetson。2026-10-08 已在 Jetson Orin Nano 上验证（部署与
输出链路），本地构建镜像，40 张带标注 CCPD 静图组成的 1080p 30 fps RTSP 轮播：
1080p 下处理 29.86 fps，检测推理 p50 5.61 ms / p95 5.75 ms，输出 56 条
`parking.plate/1` MQTT 事件及 JPEG 快照。识别准确率尚未验收：正式中文车牌语料
（白天、夜间）未运行，因此不给出准确率。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_plate.yaml}

预编译的 TensorRT engine 只适用于 Jetson Orin Nano（P3767-0003 / P3767-0004）、L4T R36.4（JetPack 6.2）、TensorRT 10.3；在其他模组或 JetPack 版本上，部署步骤会直接停止。

如果你就在 Jetson 上操作，直接在本机运行。2026-10-08 已在 Jetson Orin Nano 上
验证（部署与输出链路）：1080p 下 29.86 fps，检测 p50 5.61 ms / p95 5.75 ms，56 条
`parking.plate/1` 事件及快照。识别准确率尚未验收。

### 部署目标 {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml}

从本机通过 SSH 部署到 RK3588。2026-10-08 已在一块 RK3588 板上验证（部署与输出链路）：
按本目标的检查、模型包、配置步骤，用随包 compose、已发布的 `nrd-parking-rk:20261008`
镜像和已发布的 RK3588 模型包，输入 40 张带标注 CCPD 静图组成的 1080p 30 fps RTSP
轮播，约 160 s 内输出 36 条 `parking.plate/1` MQTT 事件及 JPEG 快照。识别准确率尚未验收。

### 部署目标 {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml}

如果你就在 RK3588 上操作，直接在本机运行。与 SSH 目标使用同一 compose、配置和模型包，
SSH 目标已于 2026-10-08 验证（36 条 `parking.plate/1` 事件及快照）；本机部署路径本身未运行。
识别准确率尚未验收。

### 部署目标 {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml}

从本机通过 SSH 部署到 RK3576。2026-10-08 已在一块 RK3576 板上验证（部署与输出链路）：
按本目标的检查、模型包、配置步骤，用随包 compose、已发布的 `nrd-parking-rk:20261008`
镜像和已发布的 RK3576 模型包，输入同一段 1080p 30 fps 轮播，约 170 s 内输出 44 条
`parking.plate/1` MQTT 事件及 JPEG 快照。识别准确率尚未验收。

### 部署目标 {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml}

如果你就在 RK3576 上操作，直接在本机运行。与 SSH 目标使用同一 compose、配置和模型包，
SSH 目标已于 2026-10-08 验证（44 条 `parking.plate/1` 事件及快照）；本机部署路径本身未运行。
识别准确率尚未验收。

### 部署目标 {#hailo_remote type=remote device=hailo device_name="R2035 (Hailo-8)" config=devices/hailo_plate.yaml}

从本机通过 SSH 部署到 R2035。验收受阻：运行镜像
`sensecraft/edge-parking-hailo:0.1.0-draft` 尚未构建，视觉运行时的 Hailo 后端
不打补丁时还不接受车牌检测模型的分层输出。

### 部署目标 {#hailo_local type=local device=hailo device_name="R2035 (Hailo-8)" config=devices/hailo_plate.yaml}

如果你就在 R2035 上操作，直接在本机运行。验收受阻：运行镜像尚未构建，Hailo 后端
需要补丁才能运行车牌检测模型。

## 步骤 2: 查看识别结果 {#view_host type=web_dashboard required=false config=devices/dashboard.yaml}

打开实时预览——车牌框与最新识别结果。

## 步骤 3: 安装道闸控制器（可选） {#gate_host type=script required=false config=devices/gate_controller.yaml}

在 reComputer R1124-10 上安装 MQTT broker 与开闸服务。使用时把识别主机的
MQTT 服务器地址指向 R1124。

## 步骤 4: 道闸接线（可选） {#wire_host type=manual required=false config=devices/gate_wiring.yaml}

把 R1124-10 的数字输出经中间继电器接到道闸的「开闸」输入，然后上传白名单
并触发一次测试脉冲。
