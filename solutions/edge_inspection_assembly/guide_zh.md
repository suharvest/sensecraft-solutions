## 套餐: 摄像头 + reComputer J30 / J40（Orin） {#jetson}

检测、缺件比对、尺寸测量、Modbus TCP 与 MQTT 都跑在一台 Jetson Orin 上，摄像头用任意 RTSP / ONVIF 摄像头、USB 摄像头或录制文件。

- **模型：** 随包模型训练在 DeepPCB（裸板铜箔缺陷数据集）上，只用于跑通链路；真实工位需要用自己的图像重训。
- **已知限制：** 期望件 ROI 是画面坐标，摄像头移动后模板失效；零件倾斜或标定物与被测面不共面会让测量偏差；所有摄像头共享一份 Modbus 寄存器，逐路结果只能从 MQTT 取。
- **网络：** 摄像头对 Jetson 可达，PLC 能访问 Jetson 的 502 端口。

## 步骤 1: 部署质检运行时 {#deploy_jetson_assembly type=docker_deploy required=true config=devices/jetson_assembly.yaml}

下载模型、在设备上构建 TensorRT engine（首次约五分钟），然后启动运行时与 MQTT broker。

### 前置条件

- 设备端口 1883、502、8080 空闲。
- RTSP 地址已用 VLC 测试过。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| `Image ... is not on this device` | 确认设备能访问 `sensecraft-missionpack.seeed.cn` 后重新部署 |
| engine 构建失败 | 确认 `/usr/src/tensorrt/bin/trtexec` 存在、磁盘有 10 GB 可用；删掉上次中断留下的 `*.engine.part` 后重试 |
| ONNX 校验和不符 | 删掉模型文件，重新部署让它重新下载 |
| 摄像头没有画面 | 用 VLC 测 RTSP 地址，检查路径和用户名密码 |
| 容器每 30 秒左右重启一次 | 录制文件未开循环时播放到结尾会退出，属正常 |
| 部署连不上 | 确认 SSH 可达、用户名正确（常用 `recomputer` 或 `nvidia`） |
| Modbus 502 端口被拒 | 主机上有别的 Modbus server 占用，或容器没起来，执行 `docker logs edge-inspection-assembly-app` 查看 |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_assembly.yaml default=true}

通过 SSH 部署到网络上的 Jetson。设备须为 JetPack 6.x 并装有 TensorRT dev 包、Docker 已配 NVIDIA runtime，至少 10 GB 可用磁盘。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_assembly.yaml}

部署到本机，本机须为 Jetson。要求同远程部署：JetPack 6.x 并装有 TensorRT dev 包、Docker 已配 NVIDIA runtime，至少 10 GB 可用磁盘。

## 步骤 2: 建立尺寸标定 {#calibrate_dimension_jetson type=manual required=false config=devices/calibrate_dimension.yaml}

可选，只在需要尺寸判定时做。跳过时尺寸段报 `uncalibrated`、Modbus HR 11 = 4，不影响缺件比对。

### 前置条件

- 一个与被测面**同平面**的标定物：ArUco 标记（示例为 `DICT_4X4_50`、id 7、宽 25 mm）或已知宽度的参考物。打印的标记用卡尺量一遍。
- 一件合格品，用来核对结果。
- 步骤 1 已完成。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| `check_aruco.py` 非零退出 | 用 `opencv-contrib-python-headless` 重建镜像 |
| 报 `status: uncalibrated` | 检查 `calibration.roi` 是否框住标定物，`aruco_dict` 与 `aruco_id` 是否与打印的标记一致 |
| 报 `status: not_found` | 提高对比度，或把测量 ROI 画到正确的特征上 |
| 测量结果稳定偏差百分之几 | 让标定物与被测面共面，`ref_object_width_mm` 填卡尺实测宽度 |
| 名义尺寸的件全判 NG | 量一批合格品，把 `tolerance_mm` 设在它们的离散范围之上 |

## 步骤 3: 查看判定结果 {#preview_assembly_jetson type=web_dashboard required=false config=devices/preview_assembly.yaml}

打开 8080 端口面板，查看实时计数、最近事件和带检测框与缺件 ROI 的预览。

### 部署完成

工位每帧发一条 MQTT 事件，并持续更新 Modbus 寄存器与线圈。

#### 快速验证

1. 打开 `http://<jetson-ip>:8080/healthz`，`frames_processed` 在增长、`mqtt_rejected` 为 0。
2. 执行 `mosquitto_sub -h <jetson-ip> -t '<工位名>/inspection/#' -C 5`，每条事件带 `assembly`、`dimension` 段和 `verdict_reasons`。
3. 从工装上拿走一个期望件：`missing_count` 上升，`verdict` 变成 `NG`。
4. 用 Modbus 客户端连 502 端口、unit 1：Coil 0（NG）与 Coil 1（OK）互斥，HR 8 等于缺件数。

#### 配置期望件清单

在 `config/config.json` 的 `sources[]` 下为每台摄像头单独配置 `assembly` 与 `dimension` 段：

- `assembly.expected[]`：一个装配位一条，填 `class`（模型类别之一）、`roi`（该摄像头画面下归一化的 `[x1, y1, x2, y2]`）、`min_count` 和 `label`（缺件时显示的名字）。
- `dimension`：挂在看得到标定物的那一路，`calibration` 框住标定物，`measurements[]` 每项填 ROI、名义尺寸与 `tolerance_mm`。
- `rules.ng_on_defect`、`ng_on_missing`、`ng_on_extra`、`ng_on_dimension` 分别控制哪些原因判 NG。

#### 读取输出

Modbus TCP，unit 1，端口 502：

| 寄存器 | 含义 |
|---|---|
| Coil 0 / Coil 1 | NG / OK，互斥 |
| HR 0 / HR 1 | 主缺陷类别 ID / 缺陷数 |
| HR 2–5 | 主缺陷框 cx、cy、w、h，归一化 ×10000 |
| HR 6–7 | 心跳，Unix 秒的 uint32 高 / 低字 |
| HR 8 / HR 9 | 缺件数 / 多余件数 |
| HR 10 | 主测量值，毫米 ×100（长边） |
| HR 11 | 公差判定码：0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated |

`HR 10 = 0` 时先读 HR 11。MQTT 主题为 `<工位名>/inspection/<流编号>/results`，`verdict = NG` 不一定意味着 `defect_count > 0`。

#### 下一步

- 把示例期望清单换成自己的装配位，并用自己的图像重训模型。
- 把 `mqtt.host` 指到带凭据的 broker，随包的 mosquitto 为本机匿名访问。
- 加摄像头就往 `sources[]` 里追加。reComputer J30 系列（Orin Nano 8GB）在关闭 MQTT 与 Modbus 时最多稳定运行 8 路 × 10 fps，带完整 I/O 时按更少路数规划。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 面板打不开 | 检查主机防火墙是否放行 8080 端口 |
| 面板能开但预览是黑的 | 看 `/healthz` 里 `frames_processed` 是否在涨，再查容器日志里的摄像头地址 |
| 线圈与寄存器对不上 | 先读寄存器，把线圈当触发信号 |
| 一开线全是 NG | 期望清单还是随包示例，按工位重建 |
| 每条事件里 `dimension.enabled` 都是 false | 该路没有 `dimension` 段，查看标定摄像头那一路的事件 |

## 步骤 4: 用 SAM2 生成期望件清单与 ROI（可选） {#annotate_sam2_jetson type=manual required=false config=devices/annotate_with_sam2.yaml}

可选。在 GPU 工作站上用上游半自动标注工具（`tools/annotation/`）从自己的图像生成 `assembly.expected[]` 模板和 ROI profile，不用手写 ROI。这一步不在质检设备上运行。

### 前置条件

- 一台装有上游 `edge-inspection-assembly` 仓库的 GPU 工作站（`--backend otsu` 不需要 GPU，效果较弱）。
- 自己的工位图像与一份 COCO 风格的类别表。

### 故障排查

| 现象 | 处理 |
|------|------|
| SAM2 后端起不来或很慢 | 确认工作站有 GPU，或改用 `--backend otsu` 重跑 |
| 设备上的运行时拒绝生成的模板 | 把这一步产出的 `assembly.expected[]` 模板与 ROI profile 一起重新拷过去并重新加载 |
| SAM2 提不出有用的框 | 类别表补上你的零件，先手工标几个类再重跑 |

## 套餐: 摄像头 + reComputer R2000（Hailo-8） {#hailo}

检测跑在 Hailo-8 加速卡上，缺件比对、尺寸测量、Modbus TCP 与 MQTT 跑在 reComputer R2000 上，摄像头用任意 RTSP / ONVIF 摄像头、USB 摄像头或录制文件。模型已预编译，板子上没有构建步骤。

- **模型：** 随包模型训练在 DeepPCB（裸板缺陷数据集）上，真实工位需要用自己的图像重训。
- **已知限制：** 期望件 ROI 是画面坐标，摄像头移动后模板失效；标定物须与被测面共面；所有摄像头共享一份 Modbus 寄存器。加路数前先在这块板上测一路。
- **网络：** 摄像头对设备可达，PLC 能访问设备的 502 端口。

## 步骤 1: 部署质检运行时 {#deploy_hailo_assembly type=docker_deploy required=true config=devices/hailo_assembly.yaml}

检查 Hailo 运行环境，下载模型，然后启动运行时与 MQTT broker。

### 前置条件

- 设备端口 1883、502、8080 空闲。
- RTSP 地址已用 VLC 测试过。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| `No /dev/hailo0` | 检查加速卡是否插好，用 `lspci` 与 `dmesg` 查看 PCIe 链路 |
| `libhailort.so.4.21.0 not found` | 把驱动、库和 Python 绑定都装成 HailoRT 4.21.x，并执行 `apt-mark hold hailort hailort-pcie-driver` |
| 容器里 `import hailo_platform` 失败 | 宿主 Python 版本须与镜像一致（3.11，Pi OS bookworm） |
| identify 正常但 `configure(hef)` 崩 | 在 `/etc/modprobe.d/` 里给 `hailo_pci` 加 `force_desc_page_size=4096` 并重启 |
| `Image ... is not on this device` | 确认设备能访问 `sensecraft-missionpack.seeed.cn` 后重新部署 |
| HEF 校验和不符 | 删掉 HEF 文件，重新部署让它重新下载 |
| 摄像头没有画面 | 用 VLC 测 RTSP 地址 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="reComputer R2000" config=devices/hailo_assembly.yaml default=true}

通过 SSH 部署到网络上的 reComputer R2000。设备须装有 HailoRT 4.21.x、`/dev/hailo0` 存在，至少 4 GB 可用磁盘。

### 部署目标 {#hailo_local type=local device=hailo device_name="reComputer R2000" config=devices/hailo_assembly.yaml}

部署到本机，本机须为 reComputer R2000。要求同远程部署：HailoRT 4.21.x、`/dev/hailo0` 存在，至少 4 GB 可用磁盘。

## 步骤 2: 建立尺寸标定 {#calibrate_dimension_hailo type=manual required=false config=devices/calibrate_dimension.yaml}

可选，只在需要尺寸判定时做。跳过时尺寸段报 `uncalibrated`、Modbus HR 11 = 4，不影响缺件比对。

### 前置条件

- 一个与被测面**同平面**的标定物：ArUco 标记（示例为 `DICT_4X4_50`、id 7、宽 25 mm）或已知宽度的参考物。打印的标记用卡尺量一遍。
- 一件合格品，用来核对结果。
- 步骤 1 已完成。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| `check_aruco.py` 非零退出 | 用 `opencv-contrib-python-headless` 重建镜像 |
| 报 `status: uncalibrated` | 检查 `calibration.roi`、`aruco_dict` 与 `aruco_id` |
| 报 `status: not_found` | 提高对比度，或把测量 ROI 画到正确的特征上 |
| 测量结果稳定偏差百分之几 | 让标定物与被测面共面，`ref_object_width_mm` 填卡尺实测宽度 |
| 名义尺寸的件全判 NG | 量一批合格品，把 `tolerance_mm` 设在它们的离散范围之上 |

## 步骤 3: 查看判定结果 {#preview_assembly_hailo type=web_dashboard required=false config=devices/preview_assembly.yaml}

打开 8080 端口面板，查看实时计数、最近事件和带检测框与缺件 ROI 的预览。

### 部署完成

工位每帧发一条 MQTT 事件，并持续更新 Modbus 寄存器与线圈。

#### 快速验证

1. 打开 `http://<设备IP>:8080/healthz`，`frames_processed` 在增长、`mqtt_rejected` 为 0。
2. 执行 `mosquitto_sub -h <设备IP> -t '<工位名>/inspection/#' -C 5`，每条事件带 `assembly`、`dimension` 段和 `verdict_reasons`。
3. 从工装上拿走一个期望件：`missing_count` 上升，`verdict` 变成 `NG`。
4. 用 Modbus 客户端连 502 端口、unit 1：Coil 0（NG）与 Coil 1（OK）互斥，HR 8 等于缺件数。
5. 记下面板里的帧率和 `inference_ms_avg`，作为这块板的实际性能。

#### 配置期望件清单

在 `config/config.json` 的 `sources[]` 下为每台摄像头单独配置 `assembly` 与 `dimension` 段：

- `assembly.expected[]`：一个装配位一条，填 `class`（模型类别之一）、`roi`（该摄像头画面下归一化的 `[x1, y1, x2, y2]`）、`min_count` 和 `label`（缺件时显示的名字）。
- `dimension`：挂在看得到标定物的那一路，`calibration` 框住标定物，`measurements[]` 每项填 ROI、名义尺寸与 `tolerance_mm`。
- `rules.ng_on_defect`、`ng_on_missing`、`ng_on_extra`、`ng_on_dimension` 分别控制哪些原因判 NG。

#### 读取输出

Modbus TCP，unit 1，端口 502：

| 寄存器 | 含义 |
|---|---|
| Coil 0 / Coil 1 | NG / OK，互斥 |
| HR 0 / HR 1 | 主缺陷类别 ID / 缺陷数 |
| HR 2–5 | 主缺陷框 cx、cy、w、h，归一化 ×10000 |
| HR 6–7 | 心跳，Unix 秒的 uint32 高 / 低字 |
| HR 8 / HR 9 | 缺件数 / 多余件数 |
| HR 10 | 主测量值，毫米 ×100（长边） |
| HR 11 | 公差判定码：0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated |

`HR 10 = 0` 时先读 HR 11。MQTT 主题为 `<工位名>/inspection/<流编号>/results`，`verdict = NG` 不一定意味着 `defect_count > 0`。

#### 下一步

- 把示例期望清单换成自己的装配位，并用自己的图像重训模型。
- 把 `mqtt.host` 指到带凭据的 broker，随包的 mosquitto 为本机匿名访问。
- 加路数之前先测一路。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 面板打不开 | 检查主机防火墙是否放行 8080 端口 |
| 面板能开但预览是黑的 | 看 `/healthz` 里 `frames_processed` 是否在涨，再查容器日志 |
| 线圈与寄存器对不上 | 先读寄存器，把线圈当触发信号 |
| 一开线全是 NG | 期望清单还是随包示例，按工位重建 |

## 步骤 4: 用 SAM2 生成期望件清单与 ROI（可选） {#annotate_sam2_hailo type=manual required=false config=devices/annotate_with_sam2.yaml}

可选。在 GPU 工作站上用上游半自动标注工具（`tools/annotation/`）从自己的图像生成 `assembly.expected[]` 模板和 ROI profile，不用手写 ROI。这一步不在 reComputer R2000 上运行。

### 前置条件

- 一台装有上游 `edge-inspection-assembly` 仓库的 GPU 工作站（`--backend otsu` 不需要 GPU，效果较弱）。
- 自己的工位图像与一份 COCO 风格的类别表。

### 故障排查

| 现象 | 处理 |
|------|------|
| SAM2 后端起不来或很慢 | 确认工作站有 GPU，或改用 `--backend otsu` 重跑 |
| 设备上的运行时拒绝生成的模板 | 把这一步产出的 `assembly.expected[]` 模板与 ROI profile 一起重新拷过去并重新加载 |
| SAM2 提不出有用的框 | 类别表补上你的零件，先手工标几个类再重跑 |

## 套餐: reCamera Pro {#recamera_pro}

检测、OK/NG 判定、Modbus TCP 与 MQTT 全部跑在 reCamera Pro 上，不需要主机。

- **已知限制：** 本套餐只做缺陷检测，不做缺件比对与尺寸测量（需要的话选 Orin 或 Hailo 套餐）。相机同一时刻只运行一个应用中心应用，激活本应用会停掉正在运行的应用。
- **账号：** 相机 Web 控制台的管理员凭据。
- **网络：** PLC 能访问相机的 502 端口；需要 MQTT 时准备一个 broker 地址。

## 步骤 1: 在 reCamera Pro 上部署质检节点 {#deploy_recamera_pro_assembly type=recamera_pro_app required=true config=devices/recamera_pro_assembly.yaml}

先在相机 Web 控制台的应用中心安装 `inspection-assembly`，这一步套用设置并把它设为活动应用。`/userdata` 需要约 20 MB 空间。

填写设备名称；需要把判定发到 broker 时再填 broker 地址，留空时判定仍通过 Modbus TCP 输出。

### 接线

填了 broker 时，每处理一帧向 `inspection/<设备名称>/results` 发一条 JSON 记录（QoS 0），内含判定、缺陷数、检测框与推理耗时。

#### PLC 读到的内容

Modbus TCP 端口 502、从站 1：线圈 0 是 NG、线圈 1 是 OK，保持寄存器 0–11 为类别、缺陷数、主框、心跳，以及缺件与尺寸计数。

### 故障排查

| 现象 | 处理 |
|------|------|
| 应用中心里没有这个应用 | 先在应用中心安装 `inspection-assembly` |
| 激活后另一个应用停了 | 属正常，应用中心同一时刻只运行一个应用 |
| broker 上收不到事件，但面板显示在处理帧 | 检查 broker 地址和凭据，查看状态面板的 `mqtt.last_error` |
| Modbus 502 上什么都没有 | 确认本应用是活动应用，且相机上没有别的进程占用 502 |

## 步骤 2: 确认判定真的出了设备 {#verify_recamera_pro_assembly type=manual required=true verify=true config=devices/verify_recamera_pro_assembly.yaml}

从网络上读 Modbus TCP，确认判定已输出。

1. 把相机对准工位，让板子在画面里
2. 在网络上任意一台机器读端口 502、从站 1 的线圈 0/1 与保持寄存器 0–11
3. 一秒后再读一次

两次读之间 HR 6/7 的心跳递增，且线圈 0 与线圈 1 恰有一个为 1，即通过。画面里是缺陷板时线圈 0 为 1、HR 1 是缺陷数；合格板时线圈 1 为 1、HR 1 为 0。

### 故障排查

| 现象 | 处理 |
|------|------|
| 502 连接被拒 | 确认本应用是活动应用，且没有别的进程占用该端口 |
| 心跳不递增 | 应用从相机自带 `rkipc` 的 RTSP 子码流取图，确认 `rkipc` 在运行 |
| 两个线圈都读到 0 | 第一帧尚未处理完，再读一次 |
