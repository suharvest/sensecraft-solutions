## 套餐: Jetson 单机部署 {#jetson_hub}

一台 Jetson Orin 运行全部服务：MQTT broker、告警工作台和人体检测器（TensorRT 推理、NVDEC 硬解），不需要第二台机器。

- **摄像头：** 一路 H.264 RTSP 摄像头，先用 VLC 测通地址。
- **首次部署：** 会在设备上构建 TensorRT 引擎，约五到六分钟，只构建一次。

## 步骤 1: 部署安防服务栈 {#deploy_edge_security_jetson_hub type=docker_deploy required=true config=devices/jetson_hub_stack.yaml}

填入这台机器的地址和摄像头 RTSP 地址，构建引擎并启动三个容器。

### 前置条件

- JetPack 6.x 的 Jetson Orin，自带 TensorRT；其他机器上部署会直接停止。
- Docker 已注册 nvidia 容器运行时。若缺失：`sudo apt-get install -y nvidia-container-toolkit && sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`。
- 8090（工作台）、1883（broker）、8099（摄像头预览）端口空闲。
- 约 6 GB 可用磁盘。

### 检查内容

- 引擎构建结束时打印 `Engine written:`，中途不要打断。
- 部署输出中 `mqtt_connected` 为 true，解码为 `"decode": "hw"`。
- 首次启动时会打印管理员登录信息。

### 故障排查

| 现象 | 处理 |
|------|------|
| 部署停在「This preset is Jetson-only」 | 目标机器不是 JetPack 系统，改用 RK3588 套餐或换一台 Jetson。 |
| 部署停在「The nvidia container runtime is not registered」 | 按前置条件安装 `nvidia-container-toolkit`，重启 Docker 后重新部署。 |
| 引擎构建失败 | 查看失败位置上方的 trtexec 输出，通常是磁盘不足。 |
| 检测器日志出现 `deserialize_cuda_engine returned None` | 删掉 `models/yolov8n_fp16.orin.engine` 后重新部署，引擎会重建。 |
| 检测器因硬解不可用退出 | 确认 nvidia 容器运行时已注册，重新部署。 |
| 8090 无响应 | 执行 `docker compose logs hub`，通常是端口被占用。 |
| detector 容器反复重启 | 执行 `docker compose logs detector`，通常是 RTSP 地址不通，在同一台机器上用 VLC 验证。 |
| 工作台里看不到设备 | 等 30 秒；再确认 `config/detector.yaml` 里的 `mqtt_host` 是 `mosquitto`。 |
| 一个人站着不动却连续报警两次 | 先检查摄像头和网络是否卡顿。 |

### 部署目标 {#jetson_hub_host type=remote device_name="reComputer J30 / J40" config=devices/jetson_hub_stack.yaml default=true}

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_jetson_hub type=web_dashboard required=true config=devices/jetson_hub_dashboard.yaml}

登录、画一条边界，走过去看第一条告警。

### 部署完成

broker、hub 和检测器已在这台机器上运行。

#### 首次登录

1. 打开 `http://<机器地址>:8090`。
2. 用户名 `admin`，密码是部署步骤打印的随机密码。输出被截断时，在机器上执行 `docker exec <hub 容器> cat /data/initial-password.txt`，第二行是密码。首次登录需修改密码。
3. 打开**设备**页，检测器应显示在线，解码为 `hw`。

#### 画第一条规则

1. 打开**规则**页，编辑器以检测器的实时画面为底图。
2. 画一个多边形作为禁区，或画一条线作为越线规则；越线可限定方向 `forward`、`backward` 或 `any`。
3. 区域可以设滞留时长，停留超时会另出一条滞留告警。
4. 保存后走进该区域，告警会在一秒内出现在**工作台**页，并附现场快照。

#### 视频墙

**工作台 → 视频墙。** 可选 1、2、4、6、9 格或「自动」，每格叠加检测框和该路的禁区、越线。按 `F` 全屏，`Esc` 退出。设备离线或流重连时，格子转灰并显示原因。

#### 不重启就改置信度

1、2、4 格布局下每格有置信度滑块，拖动后从下一帧生效，重启后保留。调低更灵敏、误报更多；调高更保守。界面提示结果未知时，到设备页刷新查看检测器上报的值。

#### 在浏览器里加一路摄像头

**视频墙 → 添加摄像头。** 选择检测器，粘贴 RTSP 地址并命名，按钮显示完成即该路已出图。加一路后在设备页查看检测器 CPU 占用，有余量再加下一路。格子上的垃圾桶图标可移除摄像头，已有告警保留。

#### 处理告警列表

每条告警可标记为已确认或误报，支持撤销、批量处理和导出 CSV。界面支持中英文。

#### 对外输出的内容

| 主题 | 内容 |
|---|---|
| `sensecraft/security/<device_id>/detections/<stream_id>` | 逐帧人体检测框，带跟踪编号 |
| `sensecraft/security/<device_id>/status` | 在线状态和解码方式 |
| `sensecraft/security/<device_id>/events/<stream_id>` | hub 判定的告警事件 |

本套餐的 1883 端口只允许本机访问。需要其他机器订阅时：把 compose 文件里 mosquitto 端口映射从 `127.0.0.1:1883:1883` 改成 `1883:1883`，同时在 `config/mosquitto.conf` 加 `password_file`、在 `config/detector.yaml` 配上对应凭据。不加密码直接开放端口，网络内任何设备都能发送伪造告警。

#### 增加第二路摄像头

可以在视频墙添加摄像头，或在这台机器上再起一个检测器容器（各自配置 `device_id`、`stream_id` 和 `preview_port`），也可以用 RK3588 套餐部署一块独立板卡。

### 故障排查

| 现象 | 处理 |
|------|------|
| 登录时密码不对 | 执行 `docker compose logs hub \| grep -i admin` 查看生成的密码。 |
| 规则编辑器只有灰底、没有画面 | 把 `config/detector.yaml` 里的 `preview_advertise_host` 改成机器的局域网地址，不要用 `127.0.0.1`。 |
| 告警没有快照缩略图 | 查看检测器日志。 |
| 越线时不报警 | 在设备页确认检测速率正常，人被持续检测到。 |

## 套餐: RK3588 单机部署 {#rk3588}

一块 RK3588 板卡运行全部服务：MQTT broker、告警工作台和人体检测器（NPU 推理、板载硬解），不需要第二台机器。

- **摄像头：** 一路 H.264 RTSP 摄像头。

## 步骤 1: 部署安防服务栈 {#deploy_edge_security_rk3588 type=docker_deploy required=true config=devices/rk3588_detector.yaml}

填入板卡地址和摄像头地址，在板卡上启动三个容器。

### 前置条件

- 板卡已安装 `rknpu2` 运行时（存在 `/usr/lib/librknnrt.so`），板卡的 `python3` 能 import `rknn_toolkit_lite2`。
- 存在硬解节点 `/dev/mpp_service`；检测器不支持 CPU 解码。
- 8090（工作台）、1883（broker）、8099（摄像头预览）端口空闲。
- 约 6 GB 可用磁盘。

### 检查内容

- 部署输出中能看到 hub 健康检查返回，首次启动时打印管理员登录信息。
- 解码为 `"decode": "hw"`。

### 故障排查

| 现象 | 处理 |
|------|------|
| 部署停在 "rknnlite is not importable" | 在板卡上执行 `pip3 install rknn_toolkit_lite2`，确认装在系统 `python3` 下而不是 venv。 |
| 检测器报解码器错误后退出 | 在板卡上安装 `gstreamer1.0-rockchip1` 和 `gstreamer1.0-plugins-bad`，重新部署。 |
| 部署成功但检测器仍是旧版本 | 在板卡上 `docker pull` 对应镜像后重新部署。 |
| 模型加载报版本不匹配 | 执行 `strings /usr/lib/librknnrt.so \| grep 'librknnrt version'`，查看实际版本；随镜像发布的模型按 2.3.2 构建。 |
| 每次启动都打印 `W Query dynamic range failed` | 无需处理。 |
| hub 里看不到检测器 | 等 30 秒；确认 `config/detector.yaml` 里的 `mqtt_host` 为 `mosquitto`。 |
| 8090 无响应 | 执行 `docker compose logs hub`，通常是端口被占用。 |

### 部署目标 {#rk3588_board type=remote device_name="RK3588" config=devices/rk3588_detector.yaml default=true}

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_rk3588 type=web_dashboard required=true config=devices/rk3588_dashboard.yaml}

打开工作台，确认解码方式为硬解。

### 部署完成

工作台地址是 `http://<板卡地址>:8090`。

#### 快速验证

1. 用户名 `admin`，密码是部署步骤打印的随机密码（也在 hub 容器的 `/data/initial-password.txt`），按提示修改密码。
2. 打开**设备**页，能看到这块板卡，解码列显示 `hw`。
3. 打开**规则**页，选中这台设备和这一路流，画一个区域或一条线。

#### 关于模型

板卡使用 int8 模型。误报偏多时先调高 `conf_threshold`。广角俯拍、人在远处的场地，先用现场画面验证检测效果。

#### 下一步

- 每增加一块板卡就重复一次本套餐，每台检测器取不同的名字。
- 多块板卡共用一份告警列表时，在一台常开机器上部署「共享 Hub」套餐，把各板卡 `config/detector.yaml` 里的 `mqtt_host` 改成那台机器的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 设备页显示解码为 `sw` | 在 `config/detector.yaml` 中打开 `require_hw_decode`，排查 MPP 硬解。 |
| 一个人站着不动却重复报警 | 在设备页对比检测速率和摄像头帧率。 |
| 规则底图是灰的 | 把 `preview_advertise_host` 改成板卡的局域网地址。 |

## 套餐: Hailo 单机部署 {#hailo}

一块带 Hailo-8 的板卡运行全部服务：MQTT broker、告警工作台和人体检测器，不需要第二台机器。

- **摄像头：** 一路 RTSP 摄像头。
- **解码：** 该板卡没有 H.264 硬解，视频在 CPU 上解码，设备页显示 `decode: "sw"` 属正常。增加摄像头时注意 CPU 占用。

## 步骤 1: 部署安防服务栈 {#deploy_edge_security_hailo type=docker_deploy required=true config=devices/hailo_detector.yaml}

填入板卡地址和摄像头地址，在板卡上启动三个容器。

### 前置条件

- Hailo PCIe 驱动已加载（存在 `/dev/hailo0`），并安装同版本的 `hailort`（存在 `/usr/lib/libhailort.so`）。
- 加速器没有被其他程序占用，被占用时部署会停止。
- 家目录下有与驱动同版本的 HailoRT Python wheel（`hailort-*-cp311-*_aarch64.whl`），从 Hailo developer zone 下载。
- 8090（工作台）、1883（broker）、8099（画面预览）端口空闲。
- 约 4 GB 可用磁盘。

### 检查内容

- 部署输出中能看到 hub 健康检查返回，首次启动时打印管理员登录信息。
- 部署步骤会确认检测器预览画面正常、容器没有反复重启，否则部署失败。
- 工作台设备页显示板卡在线，`"decode": "sw"`。

### 故障排查

| 现象 | 处理 |
|------|------|
| 部署停在「/dev/hailo0 is already held by」 | 停掉占用加速器的程序（常见是另一个视觉容器）后重新部署。 |
| 检测器报 `HAILO_OUT_OF_PHYSICAL_DEVICES(74)` 退出 | 同上。 |
| 部署成功但检测器仍是旧版本 | 在板卡上 `docker pull` 对应镜像后重新部署。 |
| 部署停在「No hailort cp311 wheel found」 | 下载与驱动同版本的 wheel，放到家目录下。 |
| 检测器以 139 或 135 退出 | 重新拉取最新镜像后部署。 |
| 设备页显示 `decode: "sw"` | 该板卡上属正常。 |
| hub 里看不到检测器 | 等 30 秒；确认 `config/detector.yaml` 里的 `mqtt_host` 为 `mosquitto`。 |
| 8090 无响应 | 执行 `docker compose logs hub`，通常是端口被占用。 |

### 部署目标 {#hailo_board type=remote device_name="Hailo 板卡" config=devices/hailo_detector.yaml default=true}

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_hailo type=web_dashboard required=true config=devices/hailo_dashboard.yaml}

打开工作台，画出第一条规则。

### 部署完成

工作台地址是 `http://<板卡地址>:8090`。

#### 首次登录

用户名 `admin`，密码是部署步骤打印的随机密码，首次登录需修改。输出被截断时，在板卡上执行 `docker exec edge_security_hailo-hub-1 cat /data/initial-password.txt`，第二行是密码。

#### 画出第一条规则

打开**规则**页，选中这块板卡的摄像头，在实时画面上作图：多边形是禁区，线段是越线，箭头指向 forward 方向。规则不受分辨率变化影响，摄像头移动后需要重画。

#### 视频墙

**工作台 → 视频墙。** 可选 1、2、4、6、9 格或「自动」，每格叠加检测框和该路的禁区、越线。按 `F` 全屏，`Esc` 退出。设备离线或流重连时，格子转灰并显示原因。

#### 不重启就改置信度

1、2、4 格布局下每格有置信度滑块，拖动后从下一帧生效，重启后保留。调低更灵敏、误报更多；调高更保守。界面提示结果未知时，到设备页刷新查看检测器上报的值。

#### 在浏览器里加一路摄像头

**视频墙 → 添加摄像头。** 选择检测器，粘贴 RTSP 地址并命名，按钮显示完成即该路已出图。格子上的垃圾桶图标可移除摄像头，已有告警保留。

#### 上报的内容

检测结果发到 `sensecraft/security/<device_id>/detections/<stream_id>`，告警事件发到 `.../events/<stream_id>`，在线状态发到 `.../status`。检测框坐标按原始画面归一化。

#### 增加第二路摄像头

每加一路都会增加 CPU 解码负载。先加一路，在设备页查看检测器 CPU 占用，有余量再加下一路。

### 故障排查

| 现象 | 处理 |
|------|------|
| 规则编辑器里实时画面加载不出来 | 把 `config/detector.yaml` 里的 `preview_advertise_host` 改成板卡的局域网地址，不要用 `127.0.0.1`。 |
| 告警没有快照 | broker 重启过的话，等 30 秒让检测器重连。 |

## 套餐: 共享 Hub（可选扩展） {#hub_only}

只在已有多台检测设备、需要共用一份告警列表时使用。Jetson、RK3588 和 Hailo 套餐各自已包含 hub，不需要本套餐。

本套餐在一台常开机器上运行 broker 和告警工作台，不带检测器。部署后把每台检测器 `config/detector.yaml` 里的 `mqtt_host` 从 `mosquitto` 改成这台机器的地址，并重启检测器。

## 步骤 1: 部署 Hub {#deploy_edge_security_hub_only type=docker_deploy required=true config=devices/hub_stack.yaml}

填入这台机器的地址，启动 broker 与 hub。

### 前置条件

- 一台常开的 arm64 或 x86_64 机器，装有 Docker。
- 8090 与 1883 端口空闲。
- 约 3 GB 可用磁盘，告警数据会随告警量增长。

### 检查内容

- 部署输出中能看到 hub 健康检查返回，首次启动时打印管理员登录信息。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8090 无响应 | 执行 `docker compose logs hub`，通常是端口冲突。 |
| 检测器反复连上又掉线 | 一个 broker 只运行一个 hub。 |
| 最初几条告警之后不再出告警 | 查看 `/api/health` 里的 `handler_errors`，持续增长时查看 hub 日志。 |

### 部署目标 {#hub_host_machine type=remote device_name="Hub Host" config=devices/hub_stack.yaml default=true}

### 部署目标 {#hub_local type=local config=devices/hub_stack.yaml}

在运行 SenseCraft Solution 的本机上运行 Hub，不需要 SSH。其他板卡上的检测器通过 MQTT 接入。

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_hub_only type=web_dashboard required=true config=devices/hub_dashboard.yaml}

登录并改密；检测器接入之前，设备列表是空的。

### 部署完成

hub 已运行，在 1883 端口等待检测器接入。

#### 首次登录

1. 打开 `http://<机器地址>:8090`。
2. 用户名 `admin`，密码是部署步骤打印的随机密码（也在 hub 容器的 `/data/initial-password.txt`），按提示修改密码。
3. 检测器接入之前**设备**页为空。

#### 接入检测器

在每台检测设备上编辑 compose 文件旁边的 `config/detector.yaml`，把 `mqtt_host` 改成这台机器的地址，再执行 `docker compose up -d detector`。

#### 数据存放位置

告警数据库、快照和规则配置都在 compose 文件旁边的 `data/` 目录，备份这个目录。

#### 预留扩展

目前可接入 Jetson、RK3588 和 Hailo 检测器，reCamera 检测节点尚未提供。

### 故障排查

| 现象 | 处理 |
|------|------|
| 检测器在线离线来回跳 | 每台检测器使用不同的名字。 |
| 告警没有缩略图 | 检测器没有响应快照请求，告警仍会记录。查看检测器日志。 |
| 各站点设备时间不一致 | 无需处理，规则判定和排序使用 hub 的时钟。 |
