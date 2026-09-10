## 套餐: 摄像头 + reComputer J30 / J40（Orin） {#jetson}

有实测数据的一条路径。运行时、MQTT broker 与 Modbus server 都跑在同一台 Jetson
Orin 上；首次部署时在设备上构建 TensorRT engine，约五分钟，engine 因此与这块板和
这个 TensorRT 版本绑定。介绍页上的每一个数字都出自这条路径。

| 设备 | 用途 |
|--------|---------|
| reComputer J30 / J40 | 检测、缺件比对、尺寸测量、Modbus TCP server、MQTT broker 与 Web 面板 |
| 摄像头 | 提供检测工位的视频；任意 RTSP 或 ONVIF 摄像头均可，USB 摄像头或录制文件同样可用 |

**重要说明。** 这是一个 demo 包，不是经过认证的计量或安全产品。尺寸模块量的是像素、
按标定物换算——精度取决于你的光学、照明与工装，不能替代验收环节里经过校准的量具。
随包模型训练在 DeepPCB 上，那是裸板铜箔缺陷数据集，在这里的作用是把整条链路证通；
它不是针对你的装配件的缺件检测器，真实工位需要用你自己的图像训练的模型。
三个已知弱点要提前规划：期望件 ROI 是画面坐标，摄像头一动模板就失效；零件倾斜或
标定物与被测面不等距会让每次测量都带偏；所有摄像头共享一份 Modbus 寄存器，
逐路结果只能从 MQTT 取。

## 步骤 1: 部署质检运行时 {#deploy_jetson_assembly type=docker_deploy required=true config=devices/jetson_assembly.yaml}

上传 compose 工程与配置，下载并校验 ONNX 模型，在设备上构建 TensorRT engine，
然后启动运行时与 MQTT broker。

### 前置条件

- JetPack 6.x（L4T r36.x）并装了 TensorRT dev 包，`/usr/src/tensorrt/bin/trtexec`
  存在且可执行。
- Docker 已配好 NVIDIA runtime，磁盘至少 10 GB 可用。
- 设备能拉到运行镜像 `sensecraft-missionpack.seeed.cn/solution/edge-inspection-assembly-jetson:0.1.0-dev`
  （先 `docker pull` 一次，或让 compose 自己拉）。该镜像 2026-09-07 按 linux/arm64
  构建并推送，digest
  `sha256:755f4b1d96052bf97e0cb84fc529d3cd61e6459f6a988144e593b06bdb7af997`。
  设备连不上 registry 时，在板子上构建这个 tag
  （`docker build --network=host -f platforms/jetson/Dockerfile.slim -t
  sensecraft-missionpack.seeed.cn/solution/edge-inspection-assembly-jetson:0.1.0-dev .`），
  或把 `INSPECTION_IMAGE` 指到设备能拉到的 tag。部署会先检查这一条再做别的事。
- 摄像头对 Jetson 可达。RTSP 地址请先用 VLC 测一下。
- 主机上 1883、502、8080 端口空闲——容器用 host 网络，PLC 才能直接访问 Modbus。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| `Image ... is not on this device` | 先 `docker pull sensecraft-missionpack.seeed.cn/solution/edge-inspection-assembly-jetson:0.1.0-dev`；registry 不可达时在板子上构建，或把 `INSPECTION_IMAGE` 指到能拉到的 tag |
| engine 构建失败 | 确认 `/usr/src/tensorrt/bin/trtexec` 存在、磁盘有 10 GB；重试前删掉上次中断留下的 `*.engine.part` |
| ONNX 校验和不符 | 模型文件不是这组实测数据对应的那一份。删掉让该步骤重新下载 |
| 摄像头没有画面 | 先用 VLC 测 RTSP 地址；路径或用户名密码写错是最常见的失败原因 |
| 容器每 30 秒左右重启一次 | 文件源播放到结尾后进程退出——不开循环时录制片段就是这个行为，不是崩溃 |
| 部署连不上 | 确认 SSH 可达、用户名正确；Seeed 镜像常用 `recomputer` 或 `nvidia` |
| Modbus 502 端口被拒 | 主机上已有别的 Modbus server 占着，或者容器没起来——看 `docker logs edge-inspection-assembly-app` |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_assembly.yaml default=true}

从这台电脑通过 SSH 部署到网络上的 Jetson。除非本应用就跑在 Jetson 上，否则用这个。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_assembly.yaml}

部署到本应用所在的这台机器。只有当这台机器就是 Jetson 时才适用。

## 步骤 2: 建立尺寸标定 {#calibrate_dimension_jetson type=manual required=false config=devices/calibrate_dimension.yaml}

可选，只在需要尺寸判定时做。只做期望件比对的工位可以跳过——尺寸段会报
`uncalibrated`、Modbus HR 11 = 4，那是一个已定义的状态，不是故障。

### 前置条件

- 一个与被测面**同平面**的标定物：ArUco 标记（示例期望 `DICT_4X4_50`、id 7、
  宽 25 mm）或任意已知宽度的参考物。打印出来的标记要用卡尺量一遍——
  打印机会按页面缩放。
- 一件合格品，用来核对结果。
- 运行时已部署，自检才能在它的镜像里跑。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| `check_aruco.py` 非零退出 | 这套 OpenCV 没有 `aruco` 模块；镜像换成 `opencv-contrib-python-headless` 重建。钉死的 `opencv-python-headless==4.10.0.84` 是自带的——ArUco 从 OpenCV 4.7 起就在主仓库的 `objdetect` 模块里，不需要 contrib |
| 报 `status: uncalibrated` | 没检出标定物——检查 `calibration.roi` 是否框住它，`aruco_dict` 与 `aruco_id` 是否与你打印的标记一致 |
| 报 `status: not_found` | 测量 ROI 里没有足够大的轮廓；通常是对比度不够或窗口画到了别的特征上 |
| 测量结果稳定偏差百分之几 | 标定物与被测面不共面，或者印出来的标记宽度与 `ref_object_width_mm` 不一致 |
| 名义尺寸的件全判 NG | `tolerance_mm` 比本工位自身的测量误差还紧；量一批合格品，把公差设在这个离散范围之上 |

## 步骤 3: 查看判定结果 {#preview_assembly_jetson type=web_dashboard required=false config=devices/preview_assembly.yaml}

打开运行时自带的 8080 端口面板——实时计数、最近事件，以及带检测框和缺件 ROI 的
MJPEG 预览。

### 部署完成

工位已经在跑。它每帧发一条 MQTT 事件，持续更新 Modbus 寄存器与线圈，并在本地提供面板。

#### 快速验证

1. 打开 `http://<jetson-ip>:8080/healthz`，确认 `frames_processed` 在增长、
   `mqtt_rejected` 保持 0。
2. 订阅结果：
   `mosquitto_sub -h <jetson-ip> -t '<工位名>/inspection/#' -C 5`。
   每条事件里都要有 `assembly` 段（`expected_count`、`matched_count`、
   `missing_count`、`missing[]`）和 `dimension` 段（`calibrated`、
   `mm_per_pixel`、`measurements[]`），以及 `verdict_reasons`。
3. 从工装上拿走一个期望件。`missing_count` 上升，`verdict_reasons` 里出现
   `missing`，即使 `defect_count` 为 0，`verdict` 也变成 `NG`。
4. 用 Modbus 客户端连 502 端口、unit 1 看线圈翻转：Coil 0 = NG 与 Coil 1 = OK
   互斥，HR 8 跟着你刚制造的缺件数走。

#### 配置期望件清单

`assembly` 与 `dimension` 是**逐路**配置的——ROI 是画面坐标，所以每台摄像头在
`config/config.json` 的 `sources[]` 下各带一套（顶层的那份只是兜底）。随包示例是
由一张 DeepPCB 图生成的六条：

```json
{
  "stream_id": "line1-pcb",
  "uri": "rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101",
  "kind": "rtsp",
  "fps": 10,
  "assembly": {
    "expected": [
      {"class": "open", "roi": [0.29328, 0.34656, 0.42078, 0.43156],
       "min_count": 1, "label": "slot00-open"},
      {"class": "mousebite", "roi": [0.36469, 0.45766, 0.44469, 0.52516],
       "min_count": 1, "label": "slot01-mousebite"}
    ],
    "match_distance": 0.12,
    "min_score": 0.25,
    "report_extra": false
  }
}
```

一个装配位一条。`class` 必须是模型 `classes` 里的一个；`roi` 是这台摄像头画面下
归一化到 0–1 的 `[x1, y1, x2, y2]`；`min_count` 是这个位置期望几件；`label` 是操作工
在 `missing[]` 里看到的名字。`match_distance` 是仍算匹配的最大归一化中心距，
`min_score` 在匹配前丢掉低分检测，`report_extra` 决定所有期望 ROI 之外的检测是否报为
`extra`（配合 `ng_on_extra` 就能让它判掉一块板）。

`dimension` 段挂在看得到标定物的那一路上：

```json
"dimension": {
  "calibration": {"detect": "aruco", "aruco_dict": "DICT_4X4_50", "aruco_id": 7,
                  "ref_object_width_mm": 25.0,
                  "roi": [0.020695, 0.320312, 0.245305, 0.679688]},
  "measurements": [
    {"name": "gauge-block", "roi": [0.401906, 0.2375, 0.894094, 0.7625],
     "nominal_width_mm": 60.0, "nominal_height_mm": 40.0, "tolerance_mm": 1.0}
  ]
}
```

`calibration.roi` 框住标定物、算出 `mm_per_pixel`；每项测量各有自己的 ROI、
名义尺寸与公差。`ref_object_width_mm` 填你用卡尺量到的宽度，不是你让打印机打的宽度。

哪些原因能判掉一块板是可配的：`rules.ng_on_defect`、`ng_on_missing`、
`ng_on_extra`、`ng_on_dimension` 四个开关各自独立。

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

HR 0–7 与表面质检契约 v1 逐位相同，既有读这几个寄存器的 PLC 程序不用改。
`HR 10 = 0` 不代表"量到 0 mm"——先读 HR 11。写侧在同一把锁里先写完寄存器再翻线圈。

MQTT，`<工位名>/inspection/<流编号>/results`，schema `2.0.0`：

```json
{"type": "assembly_inspection_result", "version": "2.0.0",
 "stream_id": "line1-pcb", "frame_id": 10423, "verdict": "NG",
 "verdict_reasons": ["missing", "dimension_out_of_tolerance"],
 "defect_count": 0,
 "assembly": {"enabled": true, "expected_count": 3, "matched_count": 2,
              "missing_count": 1, "extra_count": 1,
              "missing": [{"label": "C7-cap", "class_name": "copper",
                           "roi": [0.62, 0.10, 0.78, 0.28],
                           "min_count": 1, "expected": 1, "found": 0}]},
 "dimension": {"enabled": true, "calibrated": true, "mm_per_pixel": 0.052083,
               "out_of_tolerance_count": 1,
               "measurements": [{"name": "board_edge", "status": "oversize",
                                 "status_code": 2, "measured_long_mm": 60.42,
                                 "nominal_long_mm": 60.0, "tolerance_mm": 0.3,
                                 "deviation_mm": 0.42}]}}
```

两段永远存在，模块在该路上关闭时为 `enabled: false`，消费方不需要判断字段是否存在。
在 v2 里，`verdict = NG` 不再蕴含 `defect_count > 0`。

#### 下一步

- 把示例期望清单换成你自己的装配位，并用你自己的图像重新训练模型——
  随包权重找的是 PCB 铜箔缺陷，不是你的零件。
- 有了带凭据的 broker 之后把 `mqtt.host` 指过去；随包的 mosquitto 按设计就是
  本机匿名的。
- 加摄像头就往 `sources[]` 里追加，每一路各带自己的 `assembly` 或 `dimension` 段。
  在 reComputer J30 系列（J3011，Orin Nano 8GB）上实测的最后一个稳定点是 8 路 × 10 fps，
  而且那次测试关掉了 MQTT 与 Modbus——带上完整 I/O 路径要按更少的路数规划。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 面板打不开 | 确认这台电脑能访问 8080 端口；容器用 host 网络，通常是主机防火墙挡住了 |
| 面板能开但预览是黑的 | 源还没连上；先看 `/healthz` 里 `frames_processed` 是否在涨，再看容器日志里的摄像头地址 |
| 线圈与寄存器对不上 | 原子性只在写侧成立；读侧分两次 Modbus 请求时可能落在两次判定之间——测试中在约 20 判定/秒时观察到过。先读寄存器、把线圈当触发信号 |
| 一开线全是 NG | 期望清单还是随包示例。先按你的工位重建它，再谈结论 |
| 每条事件里 `dimension.enabled` 都是 false | 那一路没有 `dimension` 段；在随包配置里标定摄像头是另一路源 |

## 步骤 4: 用 SAM2 生成期望件清单与 ROI（可选） {#annotate_sam2_jetson type=manual required=false config=devices/annotate_with_sam2.yaml}

可选。在工作站或 spark 上跑上游的半自动标注工具（`tools/annotation/`，SAM2 辅助），
把你自己的图像变成 `assembly.expected[]` 模板和一个带版本号的
`roi_profile_sha256`，不用手写 ROI。这一步没有任何东西跑在质检设备本身上。

### 前置条件

- 一台装有上游 `edge-inspection-assembly` 仓库的工作站或 spark，SAM2 后端需要
  GPU（`--backend otsu` 不需要，但效果是更弱的基线）。
- 你自己的工位图像与一份 COCO 风格的类别表，或者愿意先手工标几个类。

## 套餐: 摄像头 + reComputer R2000（Hailo-8） {#hailo}

同一套运行时、INT8 模型、更低功耗。HEF 在设备外编译、部署时下载，板子上没有构建步骤。
同款 Hailo-8 平台实测：硬件推理 106.75 FPS，全链路 43.92 FPS，
mAP50 0.9858（对比 CPU 基线）。以上为参考值，reComputer 整机复测后更新。
这条路径的多路容量不在该轮范围内，多路扫描只在 Orin 上跑过。

| 设备 | 用途 |
|--------|---------|
| reComputer R2000 + Hailo-8（M.2） | 加速器上做检测，CPU 上做缺件比对与尺寸测量，Modbus TCP server、MQTT broker 与 Web 面板 |
| 摄像头 | 提供检测工位的视频；任意 RTSP 或 ONVIF 摄像头均可，USB 摄像头或录制文件同样可用 |

**重要说明。** 这是一个 demo 包，不是经过认证的计量或安全产品；尺寸模块不能替代
经过校准的量具，随包模型训练在 DeepPCB 裸板缺陷数据集上而不是装配图像上。
上面引用的 Hailo-8 数字是同款加速器平台的实测参考值，
按它做规划之前请在自己的整机上复测一次。
同样的三个弱点仍然适用——画面坐标 ROI、标定平面敏感、多路共享一份 Modbus 寄存器。

## 步骤 1: 部署质检运行时 {#deploy_hailo_assembly type=docker_deploy required=true config=devices/hailo_assembly.yaml}

校验 Hailo 运行环境，上传 compose 工程与配置，下载并校验 HEF，然后启动运行时与
MQTT broker。

### 前置条件

下面有三条一旦不满足就会以很难定位的方式在后面炸掉，所以部署会先检查它们：

- **Python minor 版本必须一致。** compose 把宿主的 `hailo_platform` 挂进容器，
  里面的 `_pyhailort.cpython-3XX-*.so` 只能被同一 minor 的解释器 import。
  比一下宿主的 `python3 --version` 与 `docker run --rm <镜像> python3 -V`。
- **HailoRT 必须是 4.21.x**，且驱动、用户态库、Python 绑定三者同版本——
  HEF 是 Dataflow Compiler 3.31.0 编的，对应 HailoRT 4.21.0。两个包都要
  hold（`apt-mark hold hailort hailort-pcie-driver`）；只 hold 驱动会被升级
  把用户态库偷换掉。
- **`hailo_pci` 要带 `force_desc_page_size=4096`。** Pi 5 内核 PAGE_SIZE 是 16 KB，
  Hailo-8 的最大描述符页是 4 KB。不加它时 `VDevice()` 与
  `hailortcli fw-control identify` 都能过，偏偏在 `configure(hef)` 那一步崩。
- 设备能拉到运行镜像 `sensecraft-missionpack.seeed.cn/solution/edge-inspection-assembly-rpi-hailo:0.1.0-dev`。
  该镜像 2026-09-07 按 linux/arm64 构建并推送，digest
  `sha256:695aa8011186595764e0cbb680c2cad6b88d6c0fe54e075ad6e19eae3d33f944`，
  镜像内 python3 为 3.11.2，与 Pi OS bookworm 一致。registry 不可达时，
  在板子上构建、从导出的 tar 里 load，或者设 `INSPECTION_IMAGE`。
- 磁盘至少 4 GB 可用，`/dev/hailo0` 存在，1883、502、8080 端口空闲。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| `No /dev/hailo0` | 加速卡没插好或驱动没加载；看 `lspci` 与 `dmesg` 里的 PCIe 链路 |
| `libhailort.so.4.21.0 not found` | 这份 HEF 的 ABI 锁在 HailoRT 4.21.x。装对版本（驱动 / 库 / 绑定三者），不要改挂载路径绕过去 |
| 容器里 `import hailo_platform` 失败 | 宿主与镜像的 Python minor 不一致；换匹配的基础镜像重建，或者在镜像里装 HailoRT 而不是挂宿主的 |
| identify 正常但 `configure(hef)` 崩 | `/etc/modprobe.d/` 里缺 `force_desc_page_size=4096`；加上并重启 |
| `Image ... is not on this device` | 拉取步骤连不上镜像仓库或找不到该 tag；检查设备能否访问 `sensecraft-missionpack.seeed.cn`，或从上游仓库构建该 tag 后在板子上 load |
| HEF 校验和不符 | 这个文件不是本方案评测用的那一份；删掉让该步骤重新获取 |
| 摄像头没有画面 | 先用 VLC 测 RTSP 地址 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="reComputer R2000" config=devices/hailo_assembly.yaml default=true}

从这台电脑通过 SSH 部署到网络上的 reComputer R2000。

### 部署目标 {#hailo_local type=local device=hailo device_name="reComputer R2000" config=devices/hailo_assembly.yaml}

部署到本应用所在的这台机器。只有当这台机器就是 reComputer R2000 时才适用。

## 步骤 2: 建立尺寸标定 {#calibrate_dimension_hailo type=manual required=false config=devices/calibrate_dimension.yaml}

与 Jetson 套餐相同，只换一处：自检在
`sensecraft-missionpack.seeed.cn/solution/edge-inspection-assembly-rpi-hailo:0.1.0-dev` 里跑。
只做缺件比对的工位可以跳过这一步。

### 前置条件

- 一个与被测面**同平面**的标定物：ArUco 标记（示例是 `DICT_4X4_50`、id 7、
  宽 25 mm）或任意已知宽度的参考物，印出来的尺寸用卡尺确认过。
- 一件合格品，用来核对结果。
- 运行时已部署，自检才能在它的镜像里跑。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| `check_aruco.py` 非零退出 | 这套 OpenCV 没有 `aruco` 模块；换 `opencv-contrib-python-headless` 重建。钉死的 `opencv-python-headless==4.10.0.84` 是自带的——ArUco 从 OpenCV 4.7 起就在主仓库的 `objdetect` 模块里，不需要 contrib |
| 报 `status: uncalibrated` | 没检出标定物——检查 `calibration.roi`、`aruco_dict` 与 `aruco_id` |
| 报 `status: not_found` | 测量 ROI 里没有足够大的轮廓；通常是对比度不够或窗口画错 |
| 测量结果稳定偏差百分之几 | 标定物与被测面不共面，或它的实际宽度与 `ref_object_width_mm` 不一致 |
| 名义尺寸的件全判 NG | `tolerance_mm` 比本工位自身的测量误差还紧 |

## 步骤 3: 查看判定结果 {#preview_assembly_hailo type=web_dashboard required=false config=devices/preview_assembly.yaml}

打开运行时自带的 8080 端口面板——与 Jetson 套餐是同一个页面，由同一份代码提供。

### 部署完成

工位已经跑在 Hailo-8 上。它每帧发一条 MQTT 事件，持续更新 Modbus 寄存器与线圈，
并在本地提供面板。

#### 快速验证

1. 打开 `http://<pi-ip>:8080/healthz`，确认 `frames_processed` 在增长、
   `mqtt_rejected` 保持 0。
2. 订阅结果：
   `mosquitto_sub -h <pi-ip> -t '<工位名>/inspection/#' -C 5`。
   每条事件里都要有 `assembly` 段与 `dimension` 段，以及 `verdict_reasons`。
3. 从工装上拿走一个期望件。`missing_count` 上升，`verdict_reasons` 里出现
   `missing`，即使 `defect_count` 为 0，`verdict` 也变成 `NG`。
4. 用 Modbus 客户端连 502 端口、unit 1 看线圈翻转，确认 HR 8 跟着你刚制造的
   缺件数走。
5. 把这块板的实际表现记下来——你那个分辨率下的帧率，以及面板里的
   `inference_ms_avg`。这个套餐的上板数字以你自己这一次的实测为准。

#### 配置期望件清单

与 Jetson 套餐相同：`assembly` 与 `dimension` 放在 `config/config.json` 的
`sources[]` 下逐路配置，因为 ROI 是画面坐标。一个装配位一条 `expected[]`，
带 `class`、`roi`（归一化到 0–1 的 `[x1, y1, x2, y2]`）、`min_count` 与 `label`；
`match_distance`、`min_score`、`report_extra` 控制匹配行为。`dimension` 段带
`calibration`（`detect: aruco`、`aruco_dict`、`aruco_id`、`ref_object_width_mm`、
`roi`）与 `measurements[]`（`roi`、`nominal_width_mm`、`nominal_height_mm`、
`tolerance_mm`）。`rules.ng_on_defect`、`ng_on_missing`、`ng_on_extra`、
`ng_on_dimension` 决定哪些原因能判掉一块板。与 Jetson 配置唯一不同的是 `model` 段：
`.hef` 路径与 `accelerator: hailo`。

#### 读取输出

两个套餐的寄存器表与 MQTT schema 完全相同：

| 寄存器 | 含义 |
|---|---|
| Coil 0 / Coil 1 | NG / OK，互斥 |
| HR 0 / HR 1 | 主缺陷类别 ID / 缺陷数 |
| HR 2–5 | 主缺陷框 cx、cy、w、h，归一化 ×10000 |
| HR 6–7 | 心跳，Unix 秒的 uint32 高 / 低字 |
| HR 8 / HR 9 | 缺件数 / 多余件数 |
| HR 10 | 主测量值，毫米 ×100（长边） |
| HR 11 | 公差判定码：0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated |

`HR 10 = 0` 不代表"量到 0 mm"——先读 HR 11。MQTT 在
`<工位名>/inspection/<流编号>/results` 上发 schema `2.0.0`，`assembly` 与
`dimension` 两段永远存在，`verdict = NG` 不再蕴含 `defect_count > 0`。

#### 下一步

- 把示例期望清单换成你自己的装配位，并用你自己的图像重新训练。
- 把 `mqtt.host` 指到带凭据的 broker；随包的 mosquitto 是本机匿名的。
- 加路数之前先测一路。介绍页上的多路数字来自 Jetson 套餐，不能搬到这块板上。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 面板打不开 | 确认 8080 端口可达；host 网络下通常是主机防火墙 |
| 面板能开但预览是黑的 | 源还没连上；先看 `/healthz` 里 `frames_processed` 是否在涨，再看容器日志 |
| 线圈与寄存器对不上 | 原子性只在写侧成立；读侧分两次 Modbus 请求时可能落在两次判定之间。先读寄存器、把线圈当触发信号 |
| 帧率远低于 Jetson 的数字 | 属预期——那些数字来自 reComputer J30 系列（Orin Nano 8GB）上的 TensorRT engine。测这块板自己的数并用它 |
| 一开线全是 NG | 期望清单还是随包示例；先按你的工位重建它 |

## 步骤 4: 用 SAM2 生成期望件清单与 ROI（可选） {#annotate_sam2_hailo type=manual required=false config=devices/annotate_with_sam2.yaml}

可选，与 Jetson 套餐相同。在工作站或 spark 上跑上游的半自动标注工具——这一步
没有任何东西跑在树莓派上。

### 前置条件

- 一台装有上游 `edge-inspection-assembly` 仓库的工作站或 spark，SAM2 后端需要
  GPU（`--backend otsu` 不需要，但效果是更弱的基线）。
- 你自己的工位图像与一份 COCO 风格的类别表，或者愿意先手工标几个类。

## Preset: reCamera Pro {#recamera_pro}

相机与质检节点在同一个壳里。检测、OK/NG 判定、Modbus TCP 与 MQTT 全部跑在相机
上，判定链路里没有主机、没有网络跳数。检测器用 INT8 跑在相机的 RV1126B NPU 上。

在这台设备上、停掉相机自带应用后，用 DeepPCB 验证集 205 张实测：mAP50 0.9870
（fp32 CPU 参考 0.9876）、mAP50-95 0.8000（参考 0.8213）；冻结阈值 0.35 下精确率
0.9299、召回率 0.9741，与 CPU 参考在这批图上的总数相同，但漏掉的 30 个框不是同
一批（鼠咬 7 → 8、毛刺 2 → 1）。推理 p50 30.9 ms、p95 34.5 ms。同一模型的 fp16
版本一并发布：mAP50-95 0.8221、p50 110.3 ms。

这些数字有两条限制。INT8 用的 64 张校准图取自同一份验证集，所以 INT8 这一列相对
未见过的数据偏乐观。数字来自在设备上回放验证集图片，不是把相机对着板子拍——
经这台相机自己镜头与取图链路的精度，请在自己的产线上测。

| 设备 | 作用 |
|------|------|
| reCamera Pro（RV1126B） | 取图、NPU 上的检测、OK/NG 判定、Modbus TCP 服务、MQTT 发布与本机状态面板 |

**注意.** 这是 demo 包，不是经认证的计量或安全产品。随包模型训练于 DeepPCB 裸板
缺陷数据集，不是装配图像。本预设不开缺件比对与尺寸测量：这两项都要按工位标
ROI，通用表单承载不了——Orin 与 Hailo 两个预设覆盖它们。相机同一时刻只跑一个
应用中心的应用，激活本应用会停掉此前在跑的那个。

## Step 1: 在 reCamera Pro 上部署质检节点 {#deploy_recamera_pro_assembly type=recamera_pro_app required=true config=devices/recamera_pro_assembly.yaml}

节点以应用中心的应用 `inspection-assembly` 分发。先在相机 Web 控制台的应用中心
装上它，这一步再点名它、套用你的设置并把它设为活动应用。模型不在包里：应用中心
单独把它下发到 `/userdata/local/models/inspection-assembly/`。

你需要 Web 控制台的管理员凭据，以及 `/userdata` 上约 20 MB 空间。没有要编译的
东西，也没有要手工拷贝的文件。

填一个设备名称；想让判定同时上 broker 就再填 broker 地址。留空判定依然经 Modbus
TCP 出设备。填了 broker，每处理一帧就有一条记录到达
`inspection/<设备名称>/results`——QoS 0，broker 连着时每帧发一次，是「每帧发一
次」而不是「每帧必达」——内含判定与判定依据、缺陷数、每个框的类别与分数、
推理耗时与两个模型哈希——与本方案在 Orin、Hailo 上发的是同一个事件形状，发送前过
契约校验。

### PLC 读到的内容

Modbus TCP 端口 502、从站 1：线圈 0 是 NG、线圈 1 是 OK，保持寄存器 0–11 承载
类别、缺陷数、主框、心跳，以及缺件与尺寸计数。写线圈之前寄存器已经写完，PLC 看到
线圈时数据已经就位。

### 故障排查

| 问题 | 处理 |
|------|------|
| 应用中心里没有这个应用 | 需要先把它发布到这台相机的 catalog。这一步只点名已安装的应用，不负责安装 |
| 激活它把另一个应用停了 | 正常——应用中心同一时刻只跑一个应用 |
| broker 上收不到事件，但面板显示在处理帧 | broker 地址或凭据不对；判定仍在 Modbus 上。看状态面板的 `mqtt.last_error` |
| Modbus 502 上什么都没有 | 确认本应用是活动应用，且相机上没有别的进程占着 502 |
| 帧率远低于 Orin 的数字 | 正常——那些数字来自带 TensorRT engine 的 reComputer J30 系列（Orin Nano 8GB）。用这台相机自己的数字 |

## Step 2: 确认判定真的出了设备 {#verify_recamera_pro_assembly type=manual required=true verify=true config=devices/verify_recamera_pro_assembly.yaml}

应用的状态面板只绑相机本机回环，所以这里要做的检查就是 PLC 会做的那一个：读
Modbus TCP。

1. 把相机对准工位，让板子在画面里
2. 在网络上任意一台机器读端口 502、从站 1 的线圈 0/1 与保持寄存器 0–11
3. 一秒后再读一次

两次读之间 HR 6/7 的心跳在递增、且线圈 0 与线圈 1 恰有一个为 1，这个节点就是通
的。画面里是有缺陷的板时，线圈 0 为 1、HR 1 是缺陷数；是合格板时线圈 1 为 1、
HR 1 为 0。

填了 broker 的话，订阅 `inspection/<设备名称>/results` 会看到同一个判定，每处理
一帧一条 JSON 记录。

### 故障排查

| 问题 | 处理 |
|------|------|
| 502 连接被拒 | 本应用不是活动应用，或相机上有别的进程占着这个端口 |
| 心跳不递增 | 没有帧进来。应用读的是相机自带 `rkipc` 出的 RTSP 子码流，`rkipc` 停了就没有画面 |
| 两个线圈都读到 0 | 还没写过判定——第一帧尚未处理完。再读一次 |
