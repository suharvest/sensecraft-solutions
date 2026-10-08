# 部署指南

> **草稿 / 禁用。** 不要把本包作为已发布 artifact 部署。

## 套餐：IP 摄像头 + 边缘算力盒子（草稿）{#ip_camera_box}

本套餐记录现有 RTSP 出入口摄像头与边缘主机的部署契约。在部署步骤里选择主机：
Jetson Orin（TensorRT）、RK3588 或 RK3576（RKNN）。每个部署目标都会拉取已发布
镜像并下载对应的目标设备模型包，另需 JSON 配置和外部 MQTT broker。每个部署目标写明了其真机验收
状态。

## 步骤 1：部署原生计数应用 {#deploy_counting type=docker_deploy required=true config=devices/jetson_counting.yaml}

compose 将宿主机配置和模型目录挂载进容器。镜像应包含原生 `vb-runtime`
和仅标准库的停车事件层。在 Jetson 上，CUDA、TensorRT、NVDEC 及其他 Jetson ABI
库由宿主机持有。

RK3576 上应用使用 BGR 0–255、左上角 padding、YOLOX COCO-80 解码和两个 RKNN
context；RK3588 使用三个 RKNN context，输入相同。默认流编码为 H.264；H.265
摄像头可在配置中设置 `options.codec: h265`。

### 前置条件

1. RTSP 地址已独立验证。
2. **Jetson：** 已安装 JetPack 6 和 NVIDIA container runtime。将
   `assets/config/counting.json` 复制到宿主机，编辑其中的 RTSP 流、MQTT
   broker、站点/设备编号、计数线和目标 engine 路径。
   `PARKING_IMAGE` 默认使用已发布镜像；TensorRT engine 模型包下载到
   `PARKING_MODELS_DIR`；`PARKING_CONFIG` 指向你编辑后的 JSON。可选 `health_port` 默认 `8099`，需与挂载 JSON 中的端口一致。
   可选 `memory_limit` 默认 `0`（Compose 不设置 cgroup 上限）；有界测试可填写
   `768m`。可选 `data_dir` 默认 `./data`，必须是已存在且可写的目录，以便容器
   重启后保留状态。Compose 本地 JSON 日志上限为 8 MiB × 3。 Jetson 预检查要求 `/` 至少有 0.5 GiB 可用空间；该路径假设镜像、模型和
   TensorRT engine 已提前缓存或暂存，余量用于运行文件、日志和元数据。加载或构建这些
   artifact 需另行准备空间；该门槛不代表容量或准确率验收。
3. **RK3576 / RK3588：** 已发布的原生 RK 镜像和面向该板卡的 vehicle416 RKNN
   模型包（均在部署时获取）、匹配的 `vb.config/1` 文件和宿主机 ABI 路径。将随包提供的
   `assets/config/counting-rk3576.json` 或 `assets/config/counting-rk3588.json`
   复制到 RK 宿主机，并把该宿主机路径填写为 `PARKING_CONFIG`。编辑复制出的 JSON：`site_id` 和
   `device_id` 各不超过 32 个字符；`mqtt.client_id` 和 `mqtt.topic_root` 必须唯一；
   顶层 `mqtt` 与 `app.options.mqtt` 两个映射都填写现场 broker 的 host、port、username
   和 password（匿名 broker 时 username 和 password 留空）；为每路 RTSP 填真实地址，
   并把对应 `options.codec` 设为 `h264` 或 `h265`；填写与固定 vehicle416 artifact
   匹配的 `backend.model_path` 和 `backend.model_sha256`；填写
   `app.options.counting.line`、方向和容量；填写已存在且可写的
   `app.options.state_dir`。将这份已编辑的文件作为 `parking_config` 输入。
4. **RK3588：** compose 把宿主机 RGA 库挂载为 `librga.so.2`，并从
   `parking_host_lib_dir`（默认 `/lib/aarch64-linux-gnu`）挂载宿主机 GStreamer 运行时与
   `h264parse`（`gstreamer1.0-plugins-bad`）。host 网络下 `app.options.http.port`
   默认 8080；宿主机已有服务占用 8080 时改用其他端口。

### 部署目标 {#counting_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_counting.yaml default=true}

预编译的 TensorRT engine 只适用于 Jetson Orin Nano（P3767-0003 / P3767-0004）、L4T R36.4（JetPack 6.2）、TensorRT 10.3；在其他模组或 JetPack 版本上，部署步骤会直接停止。

通过 SSH 连接这台 Jetson。2026-10-08 已验证（Jetson Orin Nano，本地构建镜像，
640x360 30 fps 合成片段，每 6 s 一辆车越线）：处理 29.98 fps，推理 p50 3.58 ms /
p95 3.64 ms，预期 41 次越线全部检出且方向交替。尚无真实出入口视频上的计数准确率。

### 部署目标 {#counting_local type=local device=jetson device_name="Jetson" config=devices/jetson_counting.yaml}

预编译的 TensorRT engine 只适用于 Jetson Orin Nano（P3767-0003 / P3767-0004）、L4T R36.4（JetPack 6.2）、TensorRT 10.3；在其他模组或 JetPack 版本上，部署步骤会直接停止。

在这台 Jetson 上运行 Docker。2026-10-08 已在 Jetson Orin Nano 上验证：处理
29.98 fps，推理 p50 3.58 ms / p95 3.64 ms，合成片段上预期 41 次越线全部检出。尚无
真实出入口视频上的计数准确率。

### 部署目标 {#rk3588_counting_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

通过 SSH 连接 RK3588 主机。2026-10-08 有条件验证：设备实测（Radxa Rock 5T /
RK3588，本地构建镜像 6a5c781d，循环播放 1280x720 H.264 5 fps 停车场片段）：处理
3.0 fps（源 5 fps，约 26 % 帧被丢弃，原因未定位），推理 p50 17.8 ms / p95 20.0 ms，
107 条 MQTT 事件且 seq 连续。片段每 10 s 循环一次，不给出计数准确率。

### 部署目标 {#rk3588_counting_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

通过宿主机路径 fail-closed 预检后，在 RK3588 主机运行 Docker。2026-10-08 有条件
验证（Radxa Rock 5T）：处理 3.0 fps（源 5 fps，约 26 % 帧被丢弃，原因未定位），
推理 p50 17.8 ms / p95 20.0 ms。不给出计数准确率。

### 部署目标 {#rk3576_counting_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_counting.yaml}

通过 SSH 连接 RK3576 主机，并执行相同的路径与 ABI 检查。验收受阻：2026-10-08 的
测试板根分区空间不足，无法加载本包镜像，随包 compose 路径未参与运行；用替代镜像
运行时输出了 MQTT 越线事件。

### 部署目标 {#rk3576_counting_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_counting.yaml}

在 RK3576 主机运行 Docker。预检要求所有用户路径和准确的 vehicle416 模型文件已
存在。验收受阻：RK3576 测试板无法加载本包镜像。

## 步骤 2：验证原生健康状态 {#verify_counting type=http_debug required=true config=devices/health_verify.yaml}

HTTP 验证步骤自动只检查 `/healthz` 返回 HTTP 200。通过后需人工查看响应体中的
runtime 和停车钩子字段。本机检查使用 `127.0.0.1`；远程部署填写主机可达的局域网
或 Fleet 地址——验证步骤不会自动继承引擎的 SSH 主机。Jetson 上，挂载 JSON 的
`health.port`、部署输入 `health_port` 和验证输入 `port` 必须相同，Docker 健康检查
在容器内使用该端口；`memory_limit=0` 表示不设上限，有界测试使用 `768m`。RK3576 /
RK3588 上应用健康服务绑定 `0.0.0.0:8099`，验证输入 `port` 保持 `8099`；compose
健康检查仍在容器内访问 `127.0.0.1:8099`。HTTP 200 和响应体检查不代表准确率、
RKNN 设备兼容性或平台验收通过。
