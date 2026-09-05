> ⚠️ **DeepPCB 是裸板（铜箔层）缺陷数据集，许可为 MIT。**
> 本 demo 的**缺件 / 尺寸逻辑用它做链路验证**——证明"检测 → 缺件比对 → 尺寸测量
> → 规则合并 → MQTT/Modbus 输出"这条链跑得通、契约对得上。DeepPCB 的六类缺陷
> （open/short/mousebite/spur/copper/pin-hole）**不等同于装配缺件**，
> 训出来的模型不是"缺件检测器"。真实的装配缺件场景需要自采数据
> （真实 PCBA 或装配件 + 卡尺实测值）。

## 方案做什么

一台摄像头盯住一个检测工位。每一帧先过检测器，再过两个业务模块和一次规则合并：

- **缺件比对**——模板期望件清单（`class` + `ROI` + 匹配距离）与检测结果比对；
  清单里有、画面里没有的记为 `missing`，清单外找到的可按需报为 `extra`。
- **尺寸测量**——同平面的标定物给出 `mm_per_pixel`；测量 ROI 内目标的最小外接
  矩形换算成毫米，与名义尺寸 ± 公差比较。
- **判定合并**——`defect`、`missing`、`extra`、`dimension_out_of_tolerance`
  任一成立即判 NG，四条可以逐条关闭。

判定同时落到两处：给 PLC 的 Modbus TCP 保持寄存器与线圈，以及给 MES 或历史库的
每帧一条 MQTT JSON 事件。寄存器永远先于线圈写入，所以按线圈动作的消费方读到的
寄存器就是同一次判定的数据。

## 你会得到什么

- **带证据的缺件判定。** 事件里给出 `expected_count` / `matched_count` /
  `missing_count`，并逐条列出缺失项的标签与 ROI，操作工看到的是哪个工位空了，
  而不只是"这块板不合格"。
- **写明误差预算的尺寸判定。** 测量结果的可信度取决于标定，因此 payload 里带着
  `mm_per_pixel`、`calibrated` 和每项测量的状态（`ok` / `undersize` /
  `oversize` / `not_found` / `uncalibrated`），而不是只给一个数。
- **对 PLC 兼容的寄存器表。** HR 0–7 与表面质检契约 v1 逐位相同，既有读 HR 0–7
  的 PLC 程序不用改；HR 8–11 是追加的缺件数、多余件数、测量毫米值 ×100 与
  公差判定码。
- **逐路配置。** ROI 是画面坐标，所以 `assembly` 与 `dimension` 按摄像头逐路配置
  （`sources[].assembly` / `sources[].dimension`），不是全局一套。
- **发布路径上的契约校验。** 每条 MQTT payload 在发出前都按 v2 schema 校验一次，
  不只是在测试里校验。

## 适用场景

- PCBA 与小型装配工位，固定机位能看全每个装配位。
- 需要按图纸公差确认零件尺寸的来料或出货检验。
- PLC 已经在消费 OK/NG 线圈、又想拿到原因码但不想新增协议的产线。
- 希望判定进 MQTT 做追溯、同时由 PLC 继续驱动剔除机构的现场。

## 实测边界

**这是一个 demo 包，不是经过认证的计量或安全产品。** 尺寸模块量的是像素、按标定物
换算，精度取决于你的光学、照明与工装，不能替代验收环节里经过校准的量具。下面的
检测数字来自本页顶部说明的 DeepPCB 数据集，那是裸板缺陷数据集——它们证明的是链路
跑得通，不是这个模型能在你的装配件上找缺件。

| 指标 | 数值 | 条件 | 来源 |
|---|---|---|---|
| 检测 mAP50 | **0.9876** | DeepPCB6 val 205 图 / 1158 框 / 6 类；YOLOX-Tiny 640²，TensorRT fp16；冻结阈值 0.35 下 P 0.9284 / R 0.9741，FP 87 / FN 30，205 帧整帧漏检 0 | 本项目 M4 实测，2026-09-05，设备 `orin-nano`（Orin NX 16GB 工程参考套件，JetPack 6.2 / TRT 10.3）。单次实测，未经非原作者复现 |
| 推理吞吐 | **95.06 FPS**（`detect()` P50 10.52 ms） | 同设备同 engine，单路，60 帧预解码上计时 500 次；其中 engine execute 约 6.3 ms，差出的部分是 letterbox + CPU NMS | 同一次 M4 实测 |
| 端到端时延 capture → Modbus 线圈 | **P50 10.92 ms / P99 11.18 ms** | 单路 10 fps 产线节拍，3000 个样本，丢帧 0，Modbus writes 3000。去掉节流（89 FPS）时同一条路径 P50 42.9 ms | 同一次 M4 实测 |
| 多路容量 | **稳定 8 路 / 下降 12 路 / 失败 24 路** | 每路 640² / 10 fps，每级跑 5 min，整轮跑了两遍；该测试期间关掉了 MQTT 与 Modbus，实际部署带上下游 I/O 后路数会更低 | 同一次 M4 实测 |
| 缺件真值闭环 | **模板帧 6 / 6 匹配，换板后 6 / 6 缺失** | 期望件清单由一张 val 图的真值框生成（ROI = GT 框 ×1.6，6 条）；在那一帧上 `missing_count` = 0，换成别的板 6 条全部落空，`verdict_reasons` 里 `missing` 与 `defect` 并列出现 | 本项目 M2 实测，2026-09-05，同一台设备 |
| 尺寸误差（ArUco 标定） | **最差相对误差 0.65%**（预算 1%） | 合成 ArUco 场景，mm/px +0.40%，长边 60 → 60.241 mm（+0.40%），短边 40 → 40.261 mm（+0.65%）；公差 ±1.0 mm，判 `ok`。未压缩 PNG 与 mp4v 编码后数值一致 | 同一次 M2 实测 |
| Hailo INT8（HEF）精度 | **mAP50 0.9924，三条路径完全一致** | 20 张 val 图 / 118 个标注框；CPU onnxruntime、Hailo emulator `SDK_NATIVE`、emulator `SDK_QUANTIZED`（optimization level 1 + Bias Correction）给出相同的 mAP50 / P / R / FP / FN。逐框比对：CPU ↔ native 120/120 匹配，CPU ↔ quantized 119/120 | 本项目 M3a 实测，2026-09-05，跑在 x86 上的 Hailo Dataflow Compiler emulator 里——**未上板** |
| Raspberry Pi 5 + Hailo-8 上板吞吐与时延 | **未实测** | 运行镜像已交叉构建出 arm64、HEF 在 emulator 里能加载，但没有在板子上跑过 | 待实测——在拿到数据之前不要在这里填数字 |
| 72 h soak | **打包时仍在进行中** | 单路、300 s 视频循环、10 fps；起跑基线：RSS 256–259 MiB，丢帧 0，tj 61–62 °C，重启 0 | 同一次 M4 实测；`boundary.soak.yaml` 的三档在跑完前为 null |

上面这些数字有意不声称两件事。其一，精度是 DeepPCB 的，而 DeepPCB 比真实装配场景
容易——人造 PCB 缺陷边界清晰。其二，五份 boundary 文件的 `reproduced_by` 都是
null：作者单次实测，每项各一台设备。

## 输出接口

| 接口 | 位置 | 内容 |
|---|---|---|
| MQTT | 端口 1883，`<设备名>/inspection/<流编号>/results` | 每帧一条 JSON 事件，schema `2.0.0`：`verdict`、`verdict_reasons`、`detections[]`，以及 `assembly` 与 `dimension` 两段。两段永远存在，模块在该路上关闭时为 `enabled: false` |
| Modbus TCP | 端口 502，unit 1 | Coil 0 = NG、Coil 1 = OK（互斥）。HR 0–7 同契约 v1（主缺陷类别、缺陷数、bbox ×10000、心跳）。HR 8 = 缺件数，HR 9 = 多余件数，HR 10 = 毫米 ×100，HR 11 = 公差判定码（0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated） |
| HTTP | 端口 8080，`/healthz` `/events` `/preview.mjpg` | 健康计数、最近事件，以及带检测框与缺件 ROI 的 MJPEG 预览 |

`HR 10 = 0` 不代表"量到 0 mm"——必须先读 HR 11。另外在 v2 里，
`verdict = NG` 不再蕴含 `defect_count > 0`：只要有缺件或尺寸超差，一条就够。

## 套餐对比

**摄像头 + reComputer J（Orin）** 是本页所有实测数据的来源。首次部署时在设备上构建
TensorRT engine（约 5 分钟），engine 因此与该设备和该 TensorRT 版本绑定。想让上面
那组数字对你成立、或者一台机器要跑不止一两路摄像头时选它。

**摄像头 + Raspberry Pi 5（Hailo-8）** 用实测证据换功耗与成本。INT8 HEF 在设备外
编译、部署时下载，板子上没有构建步骤；精度已在 Hailo emulator 上与 CPU 基线核对，
但板子本身的吞吐、时延与路数没有实测过。这块板还有三道硬前提——容器与宿主 Python
minor 版本一致、驱动 / 用户态库 / Python 绑定三者都锁在 HailoRT 4.21.x、
`hailo_pci` 带 `force_desc_page_size=4096`——部署指南里逐条带着做。

## 使用须知

- **期望件 ROI 是画面坐标。** 摄像头一移动或重新对焦，整份期望清单就要重建。
  先固定机位再建模板，不要反过来。
- **随包的期望清单是示例，不是你的产品。** 它由一张 DeepPCB 图生成，用途是验证链路。
  在这个工位有意义之前，先把 `assembly.expected[]` 换成你自己的装配位。
- **尺寸模块是纯 CPU、单平面的。** 它量的是 ROI 内最小外接矩形，按同平面标定物换算；
  零件倾斜、标定物与被测面不等距、边缘对比度低，都会体现为误差、`not_found`
  或 `uncalibrated`。
- **线圈与寄存器"同属一次判定"只在写侧成立。** 运行时在同一把锁里先写完所有寄存器
  再写线圈。读侧如果分成两次 Modbus 请求，在高判定频率下可能落在两次判定之间——
  测试中在约 20 判定/秒时观察到过。真实产线节拍下这个窗口不成立；如果在意，
  先读寄存器、把线圈当触发信号。
- **多路共享一份寄存器。** Modbus 上是最新一次判定，不区分来自哪一路；
  逐路结果从 MQTT 取。
- **包里的 MQTT broker 是本机匿名的。** 它的作用是让部署开箱即用；
  生产环境应指向带凭据的 broker。

## 许可说明

运行时代码为 Apache-2.0。检测骨干是 **YOLOX**（Megvii-BaseDetection，Apache-2.0）
——不使用 Ultralytics 的任何代码或权重，因此没有 AGPL 传染义务。训练数据是
**DeepPCB，MIT 许可**，允许再分发与商用；署名随图片一起记在
`gallery/ATTRIBUTION.md`。随包模型训练在那份裸板缺陷数据集上——它因此是什么、
不是什么，见本页顶部的说明。
