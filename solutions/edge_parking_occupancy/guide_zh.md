# 部署指南

> **草稿 / 禁用。** 不要把本包作为已发布 artifact 部署。

## 套餐：Jetson 多摄像头占用检测（草稿）{#jetson}

本草案描述现有 RTSP 摄像头组与 Jetson Orin 主机。配置必须使用
`core_parking.slots.app:SlotsApp`；`SlotHooks` 不是应用入口。车位多边形、流
地址和目标设备 engine 从宿主机挂载。

设备实测（Jetson Orin Nano，本地构建镜像，640x360 合成片段：停车场静帧 20 s / 黑帧
20 s，1 路 1 fps）：处理 0.988 fps，推理 p50 6.48 ms / p95 6.69 ms，丢帧 0，300 s 内
每个车位 15 次 occupied/free 切换。尚无真实停车视频上的车位准确率；本轮未重测多路容量。

## 步骤 1：部署 SlotsApp {#deploy_occupancy type=docker_deploy required=true config=devices/jetson_occupancy.yaml}

compose 将模型和配置留在镜像外。CUDA、TensorRT、NVDEC 及其他 Jetson ABI 库
由宿主持有。broker 由外部服务提供。

### 前置条件

1. 已安装 JetPack 6 和 NVIDIA container runtime。
2. 每路 RTSP 流已独立验证。
3. 将 `assets/config/slots.json` 复制到宿主机，编辑其中的流、MQTT broker、
   站点/设备编号、车位多边形和目标 engine 路径。
   每个车位多边形只框一个车位，使检测器看到的停放车辆覆盖其面积至少 `occupied_ratio`（0.30）。
   框住多辆小车或远处车辆的大多边形达不到该比例，永远不会报 `occupied`：验收素材上，大 ROI 的
   cover 为 0.0（Orin Nano）和 0.11（RK3588），单车 ROI 为 0.40–0.45。随包 `cam-b1-01` 多边形
   对应验收素材，现场需按自己的摄像头重画全部多边形。
4. 镜像与 vehicle640 engine 来自获准的本地构建。可选 `health_port` 默认 `8099`，
   需与挂载 JSON 中的端口一致。可选 `memory_limit` 默认 `0`（Compose 不设置
   cgroup 上限）；有界测试可填写 `768m`。可选 `data_dir` 默认 `./data`，必须是
   已存在且可写的目录，以便容器重启后保留状态。Compose 本地 JSON 日志上限为 8 MiB × 3。 Jetson 预检查要求 `/` 至少有 0.5 GiB 可用空间；该路径假设镜像、模型和
   TensorRT engine 已提前缓存或暂存，余量用于运行文件、日志和元数据。加载或构建这些
   artifact 需另行准备空间；该门槛不代表容量或准确率验收。

### Target {#occupancy_local type=local device=jetson device_name="Jetson" config=devices/jetson_occupancy.yaml}

在这台 Jetson 上运行 Docker。

### Target {#occupancy_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_occupancy.yaml default=true}

通过 SSH 连接这台 Jetson。

## 步骤 2：验证 SlotsApp 健康状态 {#verify_occupancy type=http_debug required=true config=devices/health_verify.yaml}

HTTP 验证步骤自动只检查 `/healthz` 返回 HTTP 200。通过后需人工查看响应体，并打开
`http://<host>:<app.options.http.port>/slots/editor`（stock 默认端口为 8080）检查
车位多边形。本机检查使用 `127.0.0.1`；远程 Jetson 部署填写 Jetson 可达的局域网或
Fleet 地址。挂载 JSON 的 `health.port`、部署输入 `health_port` 和验证输入 `port` 必须
相同，Docker 健康检查在容器内使用该端口。`memory_limit=0` 表示不设上限；有界测试使用
`768m`。HTTP 200、响应体检查和 editor 页面不代表车位准确率、承载能力或多摄像头验收通过。

## 套餐：RK3576 多摄像头占用检测（草稿）{#rk3576}

此禁用套餐需要本地审查过的原生 RK 镜像、面向 RK3576 的 vehicle640 RKNN
artifact、车位配置和匹配的宿主机 ABI 路径。该转换尚未完成设备验证。

## 步骤 1：部署 RK3576 SlotsApp {#deploy_rk3576_occupancy type=docker_deploy required=true config=devices/rk3576_occupancy.yaml}

应用使用 BGR 0–255、左上角 padding、YOLOX COCO-80 解码和两个 RKNN context，默认
流编码为 H.264。H.265 输入可为每路流设置 `options.codec: h265`。

部署前，将随包提供的 `assets/config/slots-rk3576.json` 复制到 RK3576 宿主机，
并把该宿主机路径填写为 `PARKING_CONFIG`。编辑复制出的 JSON：`site_id` 和
`device_id` 各不超过 32 个字符；`mqtt.client_id` 和 `mqtt.topic_root` 必须唯一；
顶层 `mqtt` 与 `app.options.mqtt` 两个映射都填写现场 broker 的 host、port、username
和 password（匿名 broker 时 username 和 password 留空）；为每路 RTSP 填真实地址，
并把对应 `options.codec` 设为 `h264` 或 `h265`；填写与固定 vehicle640 artifact
匹配的 `backend.model_path` 和 `backend.model_sha256`；在 `app.options.slots` 中
填写车位多边形，并把每组多边形映射到对应的 stream ID；填写已存在且可写的
`app.options.state_dir`。将这份已编辑的文件作为 `parking_config` 输入。

每个车位多边形只框一个车位，使检测器看到的停放车辆覆盖其面积至少 `occupied_ratio`（0.30）。
框住多辆小车或远处车辆的大多边形达不到该比例，永远不会报 `occupied`：验收素材上，大 ROI 的
cover 为 0.0（Orin Nano）和 0.11（RK3588），单车 ROI 为 0.40–0.45。随包 RK3576 多边形
为占位值，现场需按自己的摄像头重画全部多边形。

### 部署目标 {#rk3576_occupancy_local type=local device=rk3576_occupancy device_name="RK3576" config=devices/rk3576_occupancy.yaml}

通过所需路径预检后，在 RK3576 主机运行 Docker。

### 部署目标 {#rk3576_occupancy_remote type=remote device=rk3576_occupancy device_name="RK3576" config=devices/rk3576_occupancy.yaml default=true}

通过 SSH 连接 RK3576 主机。

## 步骤 2：验证 RK3576 SlotsApp 健康状态 {#verify_rk3576_occupancy type=http_debug required=true config=devices/health_verify_rk.yaml}

要求 `/healthz` 返回 HTTP 200。本机检查使用 `127.0.0.1`；远程 RK 部署填写 RK 板卡
可达的局域网或 Fleet 地址。验证步骤不会自动继承引擎的 SSH 主机。应用健康服务绑定
`0.0.0.0:8099`，compose 健康检查仍在容器内访问 `127.0.0.1:8099`。此项不代表
车位准确率或设备验证。

## 套餐：RK3588 多摄像头占用检测（草稿）{#rk3588}

此禁用套餐需要本地审查过的原生 RK 镜像、面向 RK3588 的 vehicle640 RKNN
artifact、车位配置和匹配的宿主机 ABI 路径。设备实测（Radxa Rock 5T / RK3588，本地构建
镜像 6a5c781d，合成占用/空位素材，1 路 1 fps，单车 ROI）：17 次 occupied/free 状态切换，
推理 p50 36.6 ms / p95 40.5 ms，丢帧 0。不给出车位准确率；未测多路容量。
compose 把宿主机 RGA 库挂载为 `librga.so.2`，并从 `parking_host_lib_dir`（默认
`/lib/aarch64-linux-gnu`）挂载宿主机 GStreamer 运行时与 `h264parse`
（`gstreamer1.0-plugins-bad`）。host 网络下 `app.options.http.port` 默认 8080；宿主机已有
服务占用 8080 时改用其他端口。

## 步骤 1：部署 RK3588 SlotsApp {#deploy_rk3588_occupancy type=docker_deploy required=true config=devices/rk3588_occupancy.yaml}

RK3588 使用三个 RKNN context。默认流编码为 H.264；摄像头使用 H.265 时设置
`options.codec: h265`。

部署前，将随包提供的 `assets/config/slots-rk3588.json` 复制到 RK3588 宿主机，
并把该宿主机路径填写为 `PARKING_CONFIG`。编辑复制出的 JSON：`site_id` 和
`device_id` 各不超过 32 个字符；`mqtt.client_id` 和 `mqtt.topic_root` 必须唯一；
顶层 `mqtt` 与 `app.options.mqtt` 两个映射都填写现场 broker 的 host、port、username
和 password（匿名 broker 时 username 和 password 留空）；为每路 RTSP 填真实地址，
并把对应 `options.codec` 设为 `h264` 或 `h265`；填写与固定 vehicle640 artifact
匹配的 `backend.model_path` 和 `backend.model_sha256`；在 `app.options.slots` 中
填写车位多边形，并把每组多边形映射到对应的 stream ID；填写已存在且可写的
`app.options.state_dir`。将这份已编辑的文件作为 `parking_config` 输入。

每个车位多边形只框一个车位，使检测器看到的停放车辆覆盖其面积至少 `occupied_ratio`（0.30）。
框住多辆小车或远处车辆的大多边形达不到该比例，永远不会报 `occupied`：验收素材上，大 ROI 的
cover 为 0.0（Orin Nano）和 0.11（RK3588），单车 ROI 为 0.40–0.45。随包 `cam-b1-01` 多边形
对应验收素材，现场需按自己的摄像头重画全部多边形。

### 部署目标 {#rk3588_occupancy_local type=local device=rk3588_occupancy device_name="RK3588" config=devices/rk3588_occupancy.yaml}

通过所需路径预检后，在 RK3588 主机运行 Docker。

### 部署目标 {#rk3588_occupancy_remote type=remote device=rk3588_occupancy device_name="RK3588" config=devices/rk3588_occupancy.yaml default=true}

通过 SSH 连接 RK3588 主机。

## 步骤 2：验证 RK3588 SlotsApp 健康状态 {#verify_rk3588_occupancy type=http_debug required=true config=devices/health_verify_rk.yaml}

要求 `/healthz` 返回 HTTP 200。本机检查使用 `127.0.0.1`；远程 RK 部署填写 RK 板卡
可达的局域网或 Fleet 地址。验证步骤不会自动继承引擎的 SSH 主机。应用健康服务绑定
`0.0.0.0:8099`，compose 健康检查仍在容器内访问 `127.0.0.1:8099`。此项不代表
车位准确率、设备验证或正式多摄像头验收。
