# 部署指南

> **草稿 / 禁用。** 不要把本包作为已发布 artifact 部署。

## 套餐：IP 摄像头 + Jetson（草稿）{#jetson}

本套餐记录现有 RTSP 出入口摄像头与 Jetson Orin 主机的部署契约。需要本地
构建镜像、目标 Jetson TensorRT engine、JSON 配置和外部 MQTT broker。

## 步骤 1：部署原生计数应用 {#deploy_counting type=docker_deploy required=true config=devices/jetson_counting.yaml}

compose 将宿主机配置和模型目录挂载进容器。镜像应包含原生 `vb-runtime`
和仅标准库的停车事件层。CUDA、TensorRT、NVDEC 及其他 Jetson ABI 库由宿主机
持有。

### 前置条件

1. 已安装 JetPack 6 和 NVIDIA container runtime。
2. RTSP 地址已独立验证。
3. 将 `assets/config/counting.json` 复制到宿主机，编辑其中的 RTSP 流、MQTT
   broker、站点/设备编号、计数线和目标 engine 路径。
4. `PARKING_IMAGE`、`PARKING_CONFIG` 和 `PARKING_MODELS_DIR` 指向审查过的
   本地输入。可选 `health_port` 默认 `8099`，需与挂载 JSON 中的端口一致。
   可选 `memory_limit` 默认 `0`（Compose 不设置 cgroup 上限）；有界测试可填写
   `768m`。可选 `data_dir` 默认 `./data`，必须是已存在且可写的目录，以便容器
   重启后保留状态。Compose 本地 JSON 日志上限为 8 MiB × 3。 Jetson 预检查要求 `/` 至少有 0.5 GiB 可用空间；该路径假设镜像、模型和
   TensorRT engine 已提前缓存或暂存，余量用于运行文件、日志和元数据。加载或构建这些
   artifact 需另行准备空间；该门槛不代表容量或准确率验收。

### Target {#counting_local type=local device=jetson device_name="Jetson" config=devices/jetson_counting.yaml}

在这台 Jetson 上运行 Docker。

### Target {#counting_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_counting.yaml default=true}

通过 SSH 连接这台 Jetson。

## 步骤 2：验证原生健康状态 {#verify_counting type=http_debug required=true config=devices/health_verify.yaml}

HTTP 验证步骤自动只检查 `/healthz` 返回 HTTP 200。通过后需人工查看响应体中的
runtime 和停车钩子字段。本机检查使用 `127.0.0.1`；远程 Jetson 部署填写 Jetson
可达的局域网或 Fleet 地址。挂载 JSON 的 `health.port`、部署输入
`health_port` 和验证输入 `port` 必须相同，Docker 健康检查在容器内使用该端口。
`memory_limit=0` 表示不设上限；有界测试使用 `768m`。HTTP 200 和响应体检查不代表
准确率或平台验收通过。

## 套餐：IP 摄像头 + RK3576（草稿）{#rk3576}

此禁用套餐需要本地审查过的原生 RK 镜像、面向 RK3576 的 vehicle416 RKNN
artifact、匹配的 `vb.config/1` 文件和宿主机 ABI 路径。该转换 artifact 尚未完成
设备验证。

## 步骤 1：部署 RK3576 计数应用 {#deploy_rk3576_counting type=docker_deploy required=true config=devices/rk3576_counting.yaml}

应用使用 BGR 0–255、左上角 padding、YOLOX COCO-80 解码和两个 RKNN context，默认
流编码为 H.264。H.265 摄像头可在配置中设置 `options.codec: h265`。

部署前，将随包提供的 `assets/config/counting-rk3576.json` 复制到 RK3576 宿主机，
并把该宿主机路径填写为 `PARKING_CONFIG`。编辑复制出的 JSON：`site_id` 和
`device_id` 各不超过 32 个字符；`mqtt.client_id` 和 `mqtt.topic_root` 必须唯一；
顶层 `mqtt` 与 `app.options.mqtt` 两个映射都填写现场 broker 的 host、port、username
和 password（匿名 broker 时 username 和 password 留空）；为每路 RTSP 填真实地址，
并把对应 `options.codec` 设为 `h264` 或 `h265`；填写与固定 vehicle416 artifact
匹配的 `backend.model_path` 和 `backend.model_sha256`；填写
`app.options.counting.line`、方向和容量；填写已存在且可写的
`app.options.state_dir`。将这份已编辑的文件作为 `parking_config` 输入。

### 部署目标 {#rk3576_counting_local type=local device=rk3576_counting device_name="RK3576" config=devices/rk3576_counting.yaml}

在 RK3576 主机运行 Docker。预检要求所有用户路径和准确的 vehicle416 模型文件已存在。

### 部署目标 {#rk3576_counting_remote type=remote device=rk3576_counting device_name="RK3576" config=devices/rk3576_counting.yaml default=true}

通过 SSH 连接 RK3576 主机，并执行相同的路径与 ABI 检查。

## 步骤 2：验证 RK3576 健康状态 {#verify_rk3576_counting type=http_debug required=true config=devices/health_verify_rk.yaml}

要求 `/healthz` 返回 HTTP 200。本机检查使用 `127.0.0.1`；远程 RK 部署填写 RK 板卡
可达的局域网或 Fleet 地址。验证步骤不会自动继承引擎的 SSH 主机。应用健康服务绑定
`0.0.0.0:8099`，compose 健康检查仍在容器内访问 `127.0.0.1:8099`。此项只检查
运行状态，不代表 RKNN 设备兼容性或准确率。

## 套餐：IP 摄像头 + RK3588（草稿）{#rk3588}

此禁用套餐需要本地审查过的原生 RK 镜像、面向 RK3588 的 vehicle416 RKNN
artifact、匹配的 `vb.config/1` 文件和宿主机 ABI 路径。该转换 artifact 尚未完成
设备验证。

## 步骤 1：部署 RK3588 计数应用 {#deploy_rk3588_counting type=docker_deploy required=true config=devices/rk3588_counting.yaml}

RK3588 使用三个 RKNN context。输入保持 BGR 0–255 和左上角 padding，默认流编码为
H.264；H.265 输入可设置 `options.codec: h265`。

部署前，将随包提供的 `assets/config/counting-rk3588.json` 复制到 RK3588 宿主机，
并把该宿主机路径填写为 `PARKING_CONFIG`。编辑复制出的 JSON：`site_id` 和
`device_id` 各不超过 32 个字符；`mqtt.client_id` 和 `mqtt.topic_root` 必须唯一；
顶层 `mqtt` 与 `app.options.mqtt` 两个映射都填写现场 broker 的 host、port、username
和 password（匿名 broker 时 username 和 password 留空）；为每路 RTSP 填真实地址，
并把对应 `options.codec` 设为 `h264` 或 `h265`；填写与固定 vehicle416 artifact
匹配的 `backend.model_path` 和 `backend.model_sha256`；填写
`app.options.counting.line`、方向和容量；填写已存在且可写的
`app.options.state_dir`。将这份已编辑的文件作为 `parking_config` 输入。

### 部署目标 {#rk3588_counting_local type=local device=rk3588_counting device_name="RK3588" config=devices/rk3588_counting.yaml}

通过宿主机路径 fail-closed 预检后，在 RK3588 主机运行 Docker。

### 部署目标 {#rk3588_counting_remote type=remote device=rk3588_counting device_name="RK3588" config=devices/rk3588_counting.yaml default=true}

通过 SSH 连接 RK3588 主机。

## 步骤 2：验证 RK3588 健康状态 {#verify_rk3588_counting type=http_debug required=true config=devices/health_verify_rk.yaml}

要求 `/healthz` 返回 HTTP 200。本机检查使用 `127.0.0.1`；远程 RK 部署填写 RK 板卡
可达的局域网或 Fleet 地址。验证步骤不会自动继承引擎的 SSH 主机。应用健康服务绑定
`0.0.0.0:8099`，compose 健康检查仍在容器内访问 `127.0.0.1:8099`。此项不代表
设备验证或正式计数验收。
