> ⚠️ **随包模型训练在 DeepPCB（MIT 许可）上——那是裸板铜箔缺陷数据集，不是装配缺件数据。**
> 它用来验证"检测 → 缺件比对 → 尺寸测量 → 规则合并 → MQTT/Modbus 输出"这条链路和契约。
> 真实装配场景请用自采数据（真实 PCBA + 卡尺实测值）重训。

## 方案做什么

一台摄像头盯住一个检测工位。每一帧先过检测器，再过两个业务模块和一次规则合并：

- **缺件比对**——模板期望件清单（「class」 + 「ROI」 + 匹配距离）与检测结果比对；
  清单里有、画面里没有的记为 「missing」，清单外找到的可按需报为 「extra」。
- **尺寸测量**——同平面的标定物给出 「mm_per_pixel」；测量 ROI 内目标的最小外接
  矩形换算成毫米，与名义尺寸 ± 公差比较。
- **判定合并**——「defect」、「missing」、「extra」、「dimension_out_of_tolerance」
  任一成立即判 NG，四条可以逐条关闭。

判定同时落到两处：给 PLC 的 Modbus TCP 保持寄存器与线圈，以及给 MES 或历史库的
每帧一条 MQTT JSON 事件。寄存器永远先于线圈写入，所以按线圈动作的消费方读到的
寄存器就是同一次判定的数据。

## 你会得到什么

- **带证据的缺件判定。** 事件里给出 「expected_count」 / 「matched_count」 /
  「missing_count」，并逐条列出缺失项的标签与 ROI，操作工看到的是哪个工位空了，
  而不只是"这块板不合格"。
- **写明误差预算的尺寸判定。** payload 里带着 「mm_per_pixel」、「calibrated」
  和每项测量的状态（「ok」 / 「undersize」 / 「oversize」 / 「not_found」 /
  「uncalibrated」），而不是只给一个数。
- **对 PLC 兼容的寄存器表。** HR 0–7 与表面质检契约 v1 逐位相同，既有读 HR 0–7
  的 PLC 程序不用改；HR 8–11 是追加的缺件数、多余件数、测量毫米值 ×100 与
  公差判定码。
- **逐路配置。** ROI 是画面坐标，所以 「assembly」 与 「dimension」 按摄像头逐路配置
  （「sources[].assembly」 / 「sources[].dimension」），不是全局一套。
- **发布路径上的契约校验。** 每条 MQTT payload 在发出前都按 v2 schema 校验一次。

## 适用场景

- PCBA 与小型装配工位，固定机位能看全每个装配位。
- 需要按图纸公差确认零件尺寸的来料或出货检验。
- PLC 已经在消费 OK/NG 线圈、又想拿到原因码但不想新增协议的产线。
- 希望判定进 MQTT 做追溯、同时由 PLC 继续驱动剔除机构的现场。

## 实测边界

| 产线能得到什么 | 典型值 | 设备 |
|---|---|---|
| 拍到画面到判定落在 Modbus 线圈 | **P50 10.92 ms / P99 11.18 ms** | reComputer J30 系列（J3011，Orin Nano 8GB） |
| 缺陷检出精度（mAP50） | **0.9876** | reComputer J30 系列 |
| 10 fps 产线节拍下一台主机接几路 | **8 路**（12 路下降、24 路失败） | reComputer J30 系列 |
| 缺件闭环 | 模板帧 **6 / 6** 匹配，换板后 **6 / 6** 报缺失 | reComputer J30 系列 |
| 尺寸相对标定物的误差 | 最差 **0.65%**，预算 1% | reComputer J30 系列 |

口径：DeepPCB6 val 205 图 / 1158 框 / 6 类，YOLOX-Tiny 640² TensorRT fp16，冻结阈值
0.35；端到端在 10 fps 下取 3000 个样本，丢帧 0。同一台 J3011 整机连续运行 67 小时
后复核：CPU 与 TensorRT 框一致率 0.9992，全程 0 丢帧。

## 输出接口

| 接口 | 位置 | 内容 |
|---|---|---|
| MQTT | 端口 1883，「<设备名>/inspection/<流编号>/results」 | 每帧一条 JSON 事件，schema 「2.0.0」：「verdict」、「verdict_reasons」、「detections[]」，以及 「assembly」 与 「dimension」 两段。两段永远存在，模块在该路上关闭时为 「enabled: false」 |
| Modbus TCP | 端口 502，unit 1 | Coil 0 = NG、Coil 1 = OK（互斥）。HR 0–7 同契约 v1（主缺陷类别、缺陷数、bbox ×10000、心跳）。HR 8 = 缺件数，HR 9 = 多余件数，HR 10 = 毫米 ×100，HR 11 = 公差判定码（0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated） |
| HTTP | 端口 8080，「/healthz」 「/events」 「/preview.mjpg」 | 健康计数、最近事件，以及带检测框与缺件 ROI 的 MJPEG 预览 |

「HR 10 = 0」 不代表"量到 0 mm"——必须先读 HR 11。另外在 v2 里，
「verdict = NG」 不再蕴含 「defect_count > 0」：只要有缺件或尺寸超差，一条就够。

## 半自动标注工具

上游仓库的 「tools/annotation/」 是构建 「assembly.expected[]」 模板的离线工作站工具
（不在边缘设备上跑）：人工画框，SAM 2.1（Apache-2.0）把框变成像素 mask，再扩成归一化
ROI。生成的 「assembly」 段带 「roi_profile_sha256」，事件里能断言现场跑的是哪一版
ROI。用法见部署指南里的可选标注步骤。

## 套餐对比

**摄像头 + reComputer J30 / J40（Orin）** 是有完整实测的路径，本页数字来自 J3011
（Orin Nano 8GB）；J40 未单独跑评测，适合要更多路摄像头余量的场景。首次部署在设备上
构建 TensorRT engine（约 5 分钟），engine 与该设备和 TensorRT 版本绑定。

**摄像头 + reComputer R2000（Hailo-8）** 用功耗与成本换更小的板卡体积：同平台实测
mAP50 0.9858、端到端 P50 11.89 ms。INT8 HEF 在设备外编译、部署时下载。
有三道硬前提（Python minor 版本、HailoRT 4.21.x 三件套、「force_desc_page_size=4096」），
部署指南逐条带着做。

**reCamera Pro** 把整个节点放进相机里：取图、RV1126B NPU 上的 INT8 检测、OK/NG 判定、
Modbus TCP 与 MQTT，链路里没有主机。mAP50 0.9870、推理 P50 30.9 ms。另有 fp16 版本
（mAP50-95 更高、P50 110.3 ms）供更看重框贴合度的工位。这条路径不含缺件比对与尺寸测量。

## 使用须知

- **期望件 ROI 是画面坐标。** 摄像头一移动或重新对焦，整份期望清单就要重建。
  先固定机位再建模板，不要反过来。
- **随包的期望清单是示例，不是你的产品。** 上线前把 「assembly.expected[]」
  换成你自己的装配位。
- **尺寸模块是纯 CPU、单平面的。** 零件倾斜、标定物与被测面不等距、边缘对比度低，
  都会体现为误差、「not_found」 或 「uncalibrated」。
- **线圈与寄存器"同属一次判定"只在写侧成立。** 运行时先写寄存器再写线圈；
  读侧分两次 Modbus 请求，在高判定频率下可能落在两次判定之间。在意的话先读寄存器、
  把线圈当触发信号。
- **多路共享一份寄存器。** Modbus 上是最新一次判定，不区分来自哪一路；
  逐路结果从 MQTT 取。
- **包里的 MQTT broker 是本机匿名的。** 生产环境应指向带凭据的 broker。

## 许可说明

运行时代码 Apache-2.0；检测骨干 YOLOX（Apache-2.0），不含 Ultralytics 代码或权重，
无 AGPL 义务。训练数据 DeepPCB 为 MIT 许可，署名见 「gallery/ATTRIBUTION.md」。
