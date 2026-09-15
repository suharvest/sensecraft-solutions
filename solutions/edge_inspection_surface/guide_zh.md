## 套餐: IP 摄像头 + reComputer J30 / J40（Orin） {#orin}

Jetson Orin 拉取摄像头的 RTSP 流做缺陷检测，判定输出到 Modbus TCP 与 MQTT，PLC 可选接入。

- **摄像头：** 任意对着钢带或工件取景的 RTSP 摄像头，准备好带用户名密码的 RTSP 地址并先用 VLC 测过。
- **使用限制：** 仅限内部验证。模型训练自 NEU-DET 的转载版，用于对外 demo、客户现场或商业物料前须先与数据集方确认许可，或用自己的图像重训。crazing 类精度在六类中最低，调阈值无法改善；帧级误报须用自己的产线图像测。
- **网络：** PLC 或 MES 能访问设备的 502（Modbus）和 1883（MQTT）端口。

## 步骤 1: 部署表面质检 {#deploy_jetson_inspection type=docker_deploy required=true config=devices/jetson_inspection.yaml}

部署检测器并在设备上构建 TensorRT engine，预留约 10 分钟，首次启动需等构建完成。

### 前置条件

1. 模型文件未上 CDN（许可未确认）：部署前手工把 `yolox_tiny_neu6.onnx` 放到设备的 `~/edge-inspection-surface/jetson_inspection/models/yolox_tiny_neu6.onnx`，部署时会校验 sha256。
2. 判定阈值默认 0.35。
3. **检测器 Track**：默认 `yolox`；`dfine`、`rtdetrv2` 可选，构建耗时以实际为准，0.35 阈值是按 `yolox` 标定的，换 track 后按自己的产线图像调整。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| engine 构建报 `Static model does not take explicit shapes` | 用上游 `build_engine.sh` 手工构建时设 `TRT_STATIC_SHAPE=true` |
| engine 构建失败或中途停下 | 确认 `/usr/src/tensorrt/bin/trtexec` 存在、磁盘有 10 GB 可用；删掉残留的 `.part` 文件后重试 |
| 容器里 `numpy.core.multiarray failed to import`，或 cv2 导入失败 | 只挂载宿主的 `/usr/lib/python3.10/dist-packages/tensorrt`，不要挂整个 `dist-packages` |
| `docker compose` 去读 `._docker-compose.yml` 报错 | 在 compose 目录执行 `find . -name '._*' -delete` |
| 相机没有画面 | 用 VLC 测 RTSP 地址，检查路径和用户名密码 |
| ONNX 的 sha256 对不上 | 删掉文件，重新拷贝正确的模型文件 |
| 部署连不上 SSH | 确认 SSH 可达、用户名正确（常用 `recomputer`、`nvidia` 或 `ubuntu`） |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_inspection.yaml default=true}

通过 SSH 部署到 Jetson。设备须为 JetPack 6.x 且 NVIDIA container runtime 可用，至少 10 GB 可用磁盘。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson Orin" config=devices/jetson_inspection.yaml}

部署到本机，本机须为 JetPack 6.x 的 Jetson，NVIDIA container runtime 可用，至少 10 GB 可用磁盘。

---

## 步骤 2: 查看实时检测画面 {#preview_orin_inspection type=web_dashboard required=false config=devices/preview_inspection.yaml}

打开设备自带页面，查看实时画面上的检测框和健康计数。

### 部署完成

结果发到 MQTT 1883 端口的 `<设备名>/inspection/<流编号>/results`，判定同时写到 Modbus TCP 502 端口、unit 1 的线圈 0 与 1。

#### 快速验证

1. 打开 `http://<设备 IP>:8080/`，MJPEG 预览在动。
2. 打开 `http://<设备 IP>:8080/healthz`：`inference_time_ms` 为几毫秒，10 FPS 下 `frames_dropped` 为 0，`mqtt.rejected` 为 0。
3. 把一件有缺陷的样品放到相机前，出现带类别名与分数的检测框。
4. 在另一台机器执行 `mosquitto_sub -h <设备 IP> -t '<设备名>/inspection/#' -v`，能收到消息。

#### MQTT 消息

一帧一条，`verdict` 为 OK / NG，`defect_count` 为缺陷数，`detections[]` 为该帧所有检测框（`class_name`、`score`、归一化中心点宽高 `bbox`）。无缺陷时 `primary_class_id` 为 `-1`，对应的 Modbus 寄存器为 `0`。

#### 下一步

- 把 Modbus 线圈接到剔除或打标工位，然后做步骤 3。
- 把 MES 或历史库指向 MQTT 主题。
- 加相机前先压测：Orin NX 在不发 MQTT、不写 Modbus 时稳定运行 8 路。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 页面打不开 | 执行 `docker ps` 确认容器已起，并确认 8080 端口没有被占用 |
| 预览在动但从来不出框 | 先看 `/events` 里最近的判定，再确认画面里有缺陷或调低阈值 |
| `frames_dropped` 一直涨 | 调低配置的 FPS，或减少路数 |
| `mqtt.rejected` 非零 | 查看容器日志中的契约校验错误 |

---

## 步骤 3: 核对 Modbus 输出 {#plc_check type=manual required=false verify=true config=devices/plc_check.yaml}

确认 Modbus 主站读到的判定正确。只用 MQTT 的现场可以跳过。

### 前置条件

1. 一台同网段、能做 Modbus TCP 主站的机器。
2. 设备 IP 和部署时填的从站号（下表按 unit 1）。

### 部署完成

寄存器表，502 端口上的 unit 1：

| 地址 | 含义 |
|---|---|
| Coil 0 | NG，与线圈 1 互斥 |
| Coil 1 | OK，与线圈 0 互斥 |
| HR 0 | 主缺陷类别 ID（本帧最高分的框）；OK 时为 0 |
| HR 1 | 缺陷数 |
| HR 2 | 主缺陷框 cx，归一化 x10000 |
| HR 3 | 主缺陷框 cy，归一化 x10000 |
| HR 4 | 主缺陷框 w，归一化 x10000 |
| HR 5 | 主缺陷框 h，归一化 x10000 |
| HR 6 | 心跳 Unix 秒，uint32 高字 |
| HR 7 | 心跳 Unix 秒，uint32 低字 |

#### 快速验证

1. 读 unit 1、端口 502 的线圈 0-1 与 HR 0-7，可用上游仓库的 `python evaluation/read_modbus.py --host <设备 IP> --port 502 --unit 1`。
2. 让有缺陷的样品经过相机时连续采样，线圈对随之翻转。
3. 同一次采样里两个线圈不能同时为 1；读到 `(1,1)` 时停用并排查。
4. NG 帧上 HR 2-5 在 0-10000 内，与 MQTT 消息里的框一致；OK 帧上 HR 0-5 全为 0。
5. 没有新判定时 HR 6-7 仍在递增。

#### 下一步

- PLC 以线圈为触发信号，线圈翻转时寄存器已是该帧数据。
- 对心跳停更报警，用于区分“没有缺陷”和“检测器停止”。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 502 端口连接被拒 | 检查设备上 `config/config.json` 里的 `modbus.enabled`，并确认容器已起 |
| MQTT 有检测结果但寄存器全 0 | 核对从站号，或换一帧 NG 再读 |
| 框的位置对不上 | HR 2-5 是归一化 x10000 的中心点与宽高，除以 10000 再乘画面尺寸 |
| 接了多路相机却只有一组寄存器 | 只有一组寄存器，多路时以最后一次判定为准；逐路结果从 MQTT 取 |

---

## 步骤 4: 启用无监督异常检测（可选） {#enable_anomaly_jetson type=manual required=false verify=true config=devices/enable_anomaly.yaml}

可选。在检测器旁运行 EfficientAD-S（只用无缺陷图训练），把与 OK 参考集不像的帧标出来，包括检测器没学过的缺陷类型。不参与判定。

### 前置条件

- 步骤 1 已完成，改配置并重启容器即可。
- EfficientAD-S 的 ONNX 已手工拷到设备上（未上 CDN）。
- 需要用 `anomaly_score` 做判断时，先用实际检测相机采集自己的 OK 样本标定 `anomaly.threshold`。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| MQTT 事件里没有 `anomaly_score` | 确认 `anomaly.enabled: true` 已保存且容器已重启，查看容器日志里 `anomaly.path` 模型加载错误 |
| `anomaly_score` 对任何样品都接近同一个值 | 用自己相机的 OK 集重新标定 `anomaly.threshold` |
| 按单帧 `anomaly_score` 判异常结果不稳定 | 单帧分数接近随机，改用像素/区域级信号（`heatmap_ref` 加分数） |

## 套餐: IP 摄像头 + reComputer R2000（Hailo-8） {#pi_hailo}

reComputer R2000 拉取摄像头的 RTSP 流，在 Hailo-8 上做缺陷检测，判定输出到 Modbus TCP 与 MQTT，PLC 可选接入。模型已预编译，设备上不需要构建。

- **摄像头：** 任意对着钢带或工件取景的 RTSP 摄像头，准备好带用户名密码的 RTSP 地址并先用 VLC 测过。
- **使用限制：** 仅限内部验证。模型训练自 NEU-DET 的转载版，对外或商业使用前须确认许可或用自己的图像重训。crazing 类精度最低；帧级误报须用自己的产线图像测。只支持 `yolox` 检测器。
- **网络：** PLC 或 MES 能访问设备的 502（Modbus）和 1883（MQTT）端口。

## 步骤 1: 在 Hailo 上部署表面质检 {#deploy_hailo_inspection type=docker_deploy required=true config=devices/hailo_inspection.yaml}

部署检测器与预编译的 HEF 模型。部署前会先检查 HailoRT 版本、驱动参数和 Python 版本。

### 前置条件

1. 模型文件未上 CDN（许可未确认）：部署前手工把 HEF 放到设备的 `~/edge-inspection-surface/hailo_inspection/models/yolox_tiny_neu6_o1.hef`，部署时会校验 sha256。
2. 驱动加载参数：`echo 'options hailo_pci force_desc_page_size=4096' | sudo tee /etc/modprobe.d/hailo.conf`，然后重启。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 部署停在 "libhailort.so.4.21.0 not found" | 把 HailoRT 驱动、库和 Python 绑定都装成 4.21.x |
| 部署停在 `force_desc_page_size` 检查 | 按前置条件第 2 条加 modprobe 参数并重启 |
| 容器因 `_pyhailort` 的 import 错误退出 | 宿主系统须为 Pi OS bookworm（Python 3.11）；宿主是 3.13 时用 `--build-arg RUNTIME_IMAGE=...trixie-slim` 重建镜像 |
| 日志里出现 `AssembleError` | HEF 不是本方案那一份，拿 sha256 与 `assets/models/hef_o1.manifest.json` 核对 |
| `docker compose` 去读 `._docker-compose.yml` 报错 | 在 compose 目录执行 `find . -name '._*' -delete` |
| 召回明显偏低 | 确认运行的是默认的 level-1 HEF（`yolox_tiny_neu6_o1.hef`） |
| 相机没有画面 | 用 VLC 测 RTSP 地址，检查路径和用户名密码 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="reComputer R2000" config=devices/hailo_inspection.yaml default=true}

通过 SSH 部署到 reComputer R2000。设备须装 HailoRT 4.21.x（执行 `apt-mark hold hailort hailort-pcie-driver` 锁定版本），至少 4 GB 可用磁盘。

### 部署目标 {#hailo_local type=local device=hailo device_name="reComputer R2000" config=devices/hailo_inspection.yaml}

部署到本机，本机须为 reComputer R2000，装有 HailoRT 4.21.x（两个包都 hold），至少 4 GB 可用磁盘。

---

## 步骤 2: 查看实时检测画面 {#preview_hailo_inspection type=web_dashboard required=false config=devices/preview_inspection.yaml}

打开设备自带页面，查看实时画面上的检测框和健康计数。

### 部署完成

结果发到 MQTT 1883 端口的 `<设备名>/inspection/<流编号>/results`，判定同时写到 Modbus TCP 502 端口、unit 1 的线圈 0 与 1。

#### 快速验证

1. 打开 `http://<设备 IP>:8080/`，MJPEG 预览在动。
2. 打开 `http://<设备 IP>:8080/healthz`：`inference_time_ms` 为几毫秒，10 FPS 下 `frames_dropped` 为 0，`mqtt.rejected` 为 0。
3. 把一件有缺陷的样品放到相机前，出现带类别名与分数的检测框。
4. 在另一台机器执行 `mosquitto_sub -h <设备 IP> -t '<设备名>/inspection/#' -v`，能收到消息。

#### MQTT 消息

一帧一条，`verdict` 为 OK / NG，`defect_count` 为缺陷数，`detections[]` 为该帧所有检测框（`class_name`、`score`、归一化中心点宽高 `bbox`）。无缺陷时 `primary_class_id` 为 `-1`，对应的 Modbus 寄存器为 `0`。

#### 下一步

- 把 Modbus 线圈接到剔除或打标工位，然后做步骤 3。
- 把 MES 或历史库指向 MQTT 主题。
- 这块板的吞吐和时延以 `/healthz` 上的实际计数为准。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 页面打不开 | 执行 `docker ps` 确认容器已起，并确认 8080 端口没有被占用 |
| 预览在动但从来不出框 | 先看 `/events` 里最近的判定，再确认画面里有缺陷或调低阈值 |
| `frames_dropped` 一直涨 | 调低配置的 FPS |
| `mqtt.rejected` 非零 | 查看容器日志中的契约校验错误 |

---

## 步骤 3: 核对 Modbus 输出 {#plc_check_hailo type=manual required=false verify=true config=devices/plc_check.yaml}

确认 Modbus 主站读到的判定正确。只用 MQTT 的现场可以跳过。

### 前置条件

1. 一台同网段、能做 Modbus TCP 主站的机器。
2. 设备 IP 和部署时填的从站号（下表按 unit 1）。

### 部署完成

寄存器表，502 端口上的 unit 1：

| 地址 | 含义 |
|---|---|
| Coil 0 | NG，与线圈 1 互斥 |
| Coil 1 | OK，与线圈 0 互斥 |
| HR 0 | 主缺陷类别 ID（本帧最高分的框）；OK 时为 0 |
| HR 1 | 缺陷数 |
| HR 2 | 主缺陷框 cx，归一化 x10000 |
| HR 3 | 主缺陷框 cy，归一化 x10000 |
| HR 4 | 主缺陷框 w，归一化 x10000 |
| HR 5 | 主缺陷框 h，归一化 x10000 |
| HR 6 | 心跳 Unix 秒，uint32 高字 |
| HR 7 | 心跳 Unix 秒，uint32 低字 |

#### 快速验证

1. 读 unit 1、端口 502 的线圈 0-1 与 HR 0-7，可用上游仓库的 `python evaluation/read_modbus.py --host <设备 IP> --port 502 --unit 1`。
2. 让有缺陷的样品经过相机时连续采样，线圈对随之翻转。
3. 同一次采样里两个线圈不能同时为 1；读到 `(1,1)` 时停用并排查。
4. NG 帧上 HR 2-5 在 0-10000 内，与 MQTT 消息里的框一致；OK 帧上 HR 0-5 全为 0。
5. 没有新判定时 HR 6-7 仍在递增。

#### 下一步

- PLC 以线圈为触发信号，线圈翻转时寄存器已是该帧数据。
- 对心跳停更报警，用于区分“没有缺陷”和“检测器停止”。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 502 端口连接被拒 | 检查设备上 `config/config.json` 里的 `modbus.enabled`，并确认容器已起 |
| MQTT 有检测结果但寄存器全 0 | 核对从站号，或换一帧 NG 再读 |
| 框的位置对不上 | HR 2-5 是归一化 x10000 的中心点与宽高，除以 10000 再乘画面尺寸 |
| 接了多路相机却只有一组寄存器 | 只有一组寄存器，多路时以最后一次判定为准；逐路结果从 MQTT 取 |

---

## 步骤 4: 启用无监督异常检测（可选） {#enable_anomaly_hailo type=manual required=false verify=true config=devices/enable_anomaly.yaml}

可选。在 CPU 上运行 EfficientAD-S（`accelerator: "cpu"`，该模型没有 Hailo 版本），把与 OK 参考集不像的帧标出来。不参与判定。

### 前置条件

- 步骤 1 已完成，改配置并重启容器即可。
- EfficientAD-S 的 ONNX 已手工拷到设备上（未上 CDN）。
- 需要用 `anomaly_score` 做判断时，先用实际检测相机采集自己的 OK 样本标定 `anomaly.threshold`。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| MQTT 事件里没有 `anomaly_score` | 确认 `anomaly.enabled: true` 已保存且容器已重启，查看容器日志里 `anomaly.path` 模型加载错误 |
| `anomaly_score` 对任何样品都接近同一个值 | 用自己相机的 OK 集重新标定 `anomaly.threshold` |
| 按单帧 `anomaly_score` 判异常结果不稳定 | 单帧分数接近随机，改用像素/区域级信号（`heatmap_ref` 加分数） |
