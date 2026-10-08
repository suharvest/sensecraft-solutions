# 边缘车牌识别 — 部署指南

> **草稿（staging）。** 所有套餐均未通过真机验收——模型、镜像与应用包仍在
> 各平台任务中产出。以下步骤为预期的部署流程，摘掉「草稿」标前会在真机上
> 重新验证。

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

## 套餐: IP 摄像头 + reComputer J30（Jetson） {#jetson}

保留现有出入口摄像头——Jetson Orin 拉 RTSP 流，用 TensorRT FP16 跑检测与
识别。

## 步骤 1: 部署车牌识别 {#deploy_jetson type=docker_deploy required=true config=devices/jetson_plate.yaml}

在 Jetson 上使用本地构建的停车镜像部署识别栈。部署会从提供的目标设备
模型目录读取检测和中文识别 TensorRT engine。

设备实测（Jetson Orin Nano，本地构建镜像，40 张带标注 CCPD 静图组成的 1080p 30 fps
RTSP 轮播）：1080p 下处理 29.86 fps，检测推理 p50 5.61 ms / p95 5.75 ms，输出 56 条
`parking.plate/1` MQTT 事件及 JPEG 快照。识别准确率尚未验收：正式中文车牌语料（白天、
夜间）未运行，因此不给出准确率。

### 前置条件

1. Jetson 运行 JetPack 6.x，NVIDIA 容器运行时可用。
2. 镜像和 engine 已缓存或预置在宿主机上，此外至少 0.5 GiB 可用磁盘。
3. 已本地构建的停车镜像、渲染后的 `vb.config/1` 文件，以及包含检测和中文识别 TensorRT engine 的目标设备模型目录。
4. 出入口摄像头的 RTSP 地址（如需鉴权请带用户名密码）。
   可选 `health_port` 默认 `8099`，须与挂载 JSON 中的 `health.port` 一致；宿主机 8099
   已被占用时两处一起改。可选 `memory_limit`（默认 `0`，不限）和 `data_dir`（默认
   `./data`，已存在且可写，存放状态和快照）与计数包一致。
5. 摄像头距车道 3–8 m，1080p 及以上。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| engine 或运行时校验失败 | 确认镜像、配置、目标设备 engine 目录、NVIDIA 运行时均正确，且磁盘至少有 0.5 GiB 可用 |
| 摄像头没有画面 | 先用 VLC 测 RTSP 地址；路径或凭据错误是最常见原因 |
| 容器反复重启 | 看日志里的 engine 路径；中断产生的半成品 engine 要删掉 |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_plate.yaml default=true}

从本机通过 SSH 部署到 Jetson。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_plate.yaml}

如果你就在 Jetson 上操作，直接在本机运行。

## 步骤 2: 查看识别结果 {#view_jetson type=web_dashboard required=false config=devices/dashboard.yaml}

打开实时预览——车牌框与最新识别结果。

## 步骤 3: 安装道闸控制器（可选） {#gate_jetson type=script required=false config=devices/gate_controller.yaml}

在 reComputer R1124-10 上安装 MQTT broker 与开闸服务。使用时把 Jetson 的
MQTT 服务器地址指向 R1124。

## 步骤 4: 道闸接线（可选） {#wire_jetson type=manual required=false config=devices/gate_wiring.yaml}

把 R1124-10 的数字输出经中间继电器接到道闸的「开闸」输入，然后上传白名单
并触发一次测试脉冲。

---

## 套餐: IP 摄像头 + reComputer RK3588-30 {#rk3588}

推荐的主机形态——RK3588 NPU 上跑 RKNN INT8，可支撑多路车道摄像头。

## 步骤 1: 部署车牌识别 {#deploy_rk3588 type=docker_deploy required=true config=devices/rk3588_plate.yaml}

在 RK3588 上用转换好的 RKNN 模型部署识别栈。

### 前置条件

1. 板子上已安装 RKNN 运行时（librknnrt）。
2. 至少 6 GB 可用磁盘。
3. 出入口摄像头的 RTSP 地址（如需鉴权请带用户名密码）。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 找不到 librknnrt | 先为该板卡安装 RKNN 运行时（rknpu2） |
| 摄像头没有画面 | 先用 VLC 测 RTSP 地址 |
| 日志里 NPU 空闲 | 确认 RKNN 模型文件下载完整——截断的模型会报错或退化 |

### 部署目标 {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml default=true}

从本机通过 SSH 部署到 RK3588。

### 部署目标 {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml}

如果你就在 RK3588 上操作，直接在本机运行。

## 步骤 2: 查看识别结果 {#view_rk3588 type=web_dashboard required=false config=devices/dashboard.yaml}

打开实时预览——车牌框与最新识别结果。

## 步骤 3: 安装道闸控制器（可选） {#gate_rk3588 type=script required=false config=devices/gate_controller.yaml}

在 reComputer R1124-10 上安装 MQTT broker 与开闸服务。

## 步骤 4: 道闸接线（可选） {#wire_rk3588 type=manual required=false config=devices/gate_wiring.yaml}

把 R1124-10 的数字输出经中间继电器接到道闸的「开闸」输入，然后上传白名单
并触发一次测试脉冲。

---

## 套餐: IP 摄像头 + reComputer RK3576-30 {#rk3576}

用现有出入口摄像头，RK3576 NPU 上跑 RKNN INT8。

## 步骤 1: 部署车牌识别 {#deploy_rk3576 type=docker_deploy required=true config=devices/rk3576_plate.yaml}

在 RK3576 上用转换好的 RKNN 模型部署识别栈。

### 前置条件

1. 板子上已安装 RKNN 运行时（librknnrt）。
2. 至少 6 GB 可用磁盘。
3. 出入口摄像头的 RTSP 地址（如需鉴权请带用户名密码）。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 找不到 librknnrt | 先为该板卡安装 RKNN 运行时（rknpu2） |
| 摄像头没有画面 | 先用 VLC 测 RTSP 地址 |

### 部署目标 {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml default=true}

从本机通过 SSH 部署到 RK3576。

### 部署目标 {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml}

如果你就在 RK3576 上操作，直接在本机运行。

## 步骤 2: 查看识别结果 {#view_rk3576 type=web_dashboard required=false config=devices/dashboard.yaml}

打开实时预览——车牌框与最新识别结果。

## 步骤 3: 安装道闸控制器（可选） {#gate_rk3576 type=script required=false config=devices/gate_controller.yaml}

在 reComputer R1124-10 上安装 MQTT broker 与开闸服务。

## 步骤 4: 道闸接线（可选） {#wire_rk3576 type=manual required=false config=devices/gate_wiring.yaml}

把 R1124-10 的数字输出经中间继电器接到道闸的「开闸」输入，然后上传白名单
并触发一次测试脉冲。

---

## 套餐: IP 摄像头 + reComputer R2035-12（Hailo-8） {#hailo}

用现有出入口摄像头，Hailo-8 加速器上跑检测与识别。

## 步骤 1: 部署车牌识别 {#deploy_hailo type=docker_deploy required=true config=devices/hailo_plate.yaml}

在 R2035 上用编译好的 HEF 模型部署识别栈。

### 前置条件

1. 已安装 Hailo-8 驱动与 HailoRT，且存在 `/dev/hailo0`。HailoRT 版本必须
   与驱动一致——需自行从 Hailo Developer Zone 获取。
2. 至少 6 GB 可用磁盘。
3. 出入口摄像头的 RTSP 地址（如需鉴权请带用户名密码）。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 找不到 /dev/hailo0 | 先加载 Hailo-8 驱动再部署 |
| HailoRT 版本不一致 | 安装与驱动匹配的 HailoRT 包——预检会打印它找到的版本 |
| 识别跑在 CPU 上 | 两个 network group 无法共享设备时的预期行为；准确率不受影响，吞吐较低 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="R2035" config=devices/hailo_plate.yaml default=true}

从本机通过 SSH 部署到 R2035。

### 部署目标 {#hailo_local type=local device=hailo device_name="R2035" config=devices/hailo_plate.yaml}

如果你就在 R2035 上操作，直接在本机运行。

## 步骤 2: 查看识别结果 {#view_hailo type=web_dashboard required=false config=devices/dashboard.yaml}

打开实时预览——车牌框与最新识别结果。

## 步骤 3: 安装道闸控制器（可选） {#gate_hailo type=script required=false config=devices/gate_controller.yaml}

在 reComputer R1124-10 上安装 MQTT broker 与开闸服务。

## 步骤 4: 道闸接线（可选） {#wire_hailo type=manual required=false config=devices/gate_wiring.yaml}

把 R1124-10 的数字输出经中间继电器接到道闸的「开闸」输入，然后上传白名单
并触发一次测试脉冲。
