> ⚠️ **DeepPCB 是裸板（铜箔层）缺陷数据集，许可为 MIT。**
> 本 demo 的**缺件 / 尺寸逻辑用它做链路验证**——证明"检测 → 缺件比对 → 尺寸测量
> → 规则合并 → MQTT/Modbus 输出"这条链跑得通、契约对得上。DeepPCB 的六类缺陷
> （open/short/mousebite/spur/copper/pin-hole）**不等同于装配缺件**，
> 训出来的模型不是"缺件检测器"。真实的装配缺件场景需要自采数据
> （真实 PCBA 或装配件 + 卡尺实测值）。

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
- **写明误差预算的尺寸判定。** 测量结果的可信度取决于标定，因此 payload 里带着
  「mm_per_pixel」、「calibrated」 和每项测量的状态（「ok」 / 「undersize」 /
  「oversize」 / 「not_found」 / 「uncalibrated」），而不是只给一个数。
- **对 PLC 兼容的寄存器表。** HR 0–7 与表面质检契约 v1 逐位相同，既有读 HR 0–7
  的 PLC 程序不用改；HR 8–11 是追加的缺件数、多余件数、测量毫米值 ×100 与
  公差判定码。
- **逐路配置。** ROI 是画面坐标，所以 「assembly」 与 「dimension」 按摄像头逐路配置
  （「sources[].assembly」 / 「sources[].dimension」），不是全局一套。
- **发布路径上的契约校验。** 每条 MQTT payload 在发出前都按 v2 schema 校验一次，
  不只是在测试里校验。

## 适用场景

- PCBA 与小型装配工位，固定机位能看全每个装配位。
- 需要按图纸公差确认零件尺寸的来料或出货检验。
- PLC 已经在消费 OK/NG 线圈、又想拿到原因码但不想新增协议的产线。
- 希望判定进 MQTT 做追溯、同时由 PLC 继续驱动剔除机构的现场。

## 实测边界

**这是一个 demo 包，不是经过认证的计量或安全产品。** 尺寸模块量的是像素、按标定物
换算，精度取决于你的光学、照明与工装，不能替代验收环节里经过校准的量具。

| 产线能得到什么 | 典型值 | 设备 |
|---|---|---|
| 拍到画面到判定落在 Modbus 线圈 | **P50 10.92 ms / P99 11.18 ms** | reComputer J30 系列（J3011，Orin Nano 8GB） |
| 缺陷检出精度（mAP50） | **0.9876** | reComputer J30 系列 |
| 10 fps 产线节拍下一台主机接几路 | **8 路**（12 路下降、24 路失败） | reComputer J30 系列 |
| 缺件闭环 | 模板帧 **6 / 6** 匹配，换板后 **6 / 6** 报缺失 | reComputer J30 系列 |
| 尺寸相对标定物的误差 | 最差 **0.65%**，预算 1% | reComputer J30 系列 |

口径：DeepPCB6 val 205 图 / 1158 框 / 6 类，YOLOX-Tiny 640² TensorRT fp16，冻结阈值 0.35；
端到端在 10 fps 产线节拍下取 3000 个样本，丢帧 0；路数扫描期间关掉了 Modbus 与 MQTT，
实际部署带上两者后路数会更低。2026-09-05 实测，设备为 reComputer J30 系列（J3011，Orin Nano 8GB；JetPack
6.2 / TRT 10.3）——`/proc/device-tree/model` 一度误读为 Orin NX 工程参考套件，
2026-09-08 用 device-tree compatible（nvidia,p3767-0003）核实后更正。

2026-09-08 复核：同一个 engine 在同一台 reComputer J30 系列（J3011）
整机上已连续运行 67 小时，CPU 与 TensorRT 的框一致率 0.9992，取图到线圈
P50 11.45 ms，67 小时全程 0 丢帧。

另外两台主机跑同一个检测器、精度相当：选配 Hailo-8 的 reComputer R2000 系列端到端
P50 11.89 ms / P99 16.08 ms、mAP50 0.9858（2026-09-06）；一体机 reCamera Pro
mAP50 0.9870、单次推理 P50 30.9 ms（RKNN INT8，2026-09-08）。reCamera Pro 的 INT8
校准图取自同一份验证集，因此那一列相对未见过的数据偏乐观。

精度数字来自 DeepPCB，它比真实装配场景容易——人造 PCB 缺陷边界清晰——而且它不是缺件
检测器。上线前请用自己的板子重训。这是参考设计，不是经过认证的检测产品。

## 输出接口

| 接口 | 位置 | 内容 |
|---|---|---|
| MQTT | 端口 1883，「<设备名>/inspection/<流编号>/results」 | 每帧一条 JSON 事件，schema 「2.0.0」：「verdict」、「verdict_reasons」、「detections[]」，以及 「assembly」 与 「dimension」 两段。两段永远存在，模块在该路上关闭时为 「enabled: false」 |
| Modbus TCP | 端口 502，unit 1 | Coil 0 = NG、Coil 1 = OK（互斥）。HR 0–7 同契约 v1（主缺陷类别、缺陷数、bbox ×10000、心跳）。HR 8 = 缺件数，HR 9 = 多余件数，HR 10 = 毫米 ×100，HR 11 = 公差判定码（0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated） |
| HTTP | 端口 8080，「/healthz」 「/events」 「/preview.mjpg」 | 健康计数、最近事件，以及带检测框与缺件 ROI 的 MJPEG 预览 |

「HR 10 = 0」 不代表"量到 0 mm"——必须先读 HR 11。另外在 v2 里，
「verdict = NG」 不再蕴含 「defect_count > 0」：只要有缺件或尺寸超差，一条就够。

## 可选：VLM 解释

运行时可以把一帧 NG 交给外部共享 VLM 服务（「edge-vision-vlm」）生成一段人话解释。
这是一条旁路，不是第二个判定者：它不进帧循环、不改变 「verdict」，服务关闭、变慢
或不可达时，OK/NG 输出与没有这条旁路完全一样。

- **触发条件。** 只在值得人看一眼的状态变化上才调用——「assembly.missing_count > 0」，
  或主缺陷置信度低于 「vlm.trigger.min_confidence」——每路按
  「vlm.trigger.min_interval_s」 限速，绝不是每帧调用一次。
- **旁路事件。** 有界、drop-oldest 队列的后台 worker 负责提交调用；
  「inspection/<流编号>/results」 上的主事件照常按原节奏发布，不管 VLM 有没有回应。
  回应了才会在 「inspection/<流编号>/explanations」 上再发一条，按同一个 「frame_id」
  对齐。
- **不阻塞主链路。** 客户端硬超时会放弃这次调用；连续失败达到阈值后熔断器会停调
  一段冷却期。这条链路上没有任何东西能拖住判定、Modbus 写入或 MQTT 发布。
- **时延不是可以按帧规划的数字。** 在共享服务自己的评测硬件——NVIDIA Spark GB10
  工作站，**不是本 demo 跑的这台 Orin**——上实测，Qwen3-VL-2B bf16 光生成阶段就是
  P50 ≈ 3.2 s / P95 ≈ 7.2 s（「max_tokens=320」）。这正是这次调用要离开热路径的原因；
  这套集成目前没有 Orin 上的实测时延。

设置 「vlm.enabled: true」 并把 「vlm.base_url」 指到一个可达的 「edge-vision-vlm」 实例
即可启用；完整步骤见部署指南，包括设备上需要的 「no_proxy」 设置。

## 半自动标注工具

上游仓库的 「tools/annotation/」 用 SAM2 把人工画的框变成像素级 mask，再把审核通过的
mask 变成一份装配 ROI profile——它不在边缘设备上跑，也不进帧循环，是构建
「assembly.expected[]」 模板用的离线工作站工具。

- **模型。** SAM 2.1 Hiera-Small（「facebookresearch/sam2」，代码与权重都是
  Apache-2.0），外加一个不需要 GPU 的纯 numpy Otsu-flood 后端，兼作对照基线。
- **省不掉什么。** 框还是人画的——点击数与人工标注一样，2 次/框。SAM2 加的是
  从这个框生成一份像素 mask，ROI-profile 步骤再把它扩成归一化的 「assembly」
  ROI（「roi_profile.py」，mask 外接框 ×1.6）。
- **提示点越多越差，不是越好。** 校准轮里只给框的策略胜过"框+中心点"与
  "框+中心点+背景点"——DeepPCB 的缺陷很小，多出来的前景/背景点会落在缺陷本体
  上或旁边，把 mask 往错的方向拉。工具默认就是只给框。
- **修订率是代理值，不是人工数字。** 本轮评测没有真人审核；9.33% 是
  「gt_box_iou < 0.5」 自动判定的结果（「review_by: auto:gt_box_iou>=0.5」），
  与真正的人工裁决分在不同字段，不会被混算成同一个数。
- **「roi_profile_sha256」。** 生成的 「assembly」 段带一个只对该段计算的 SHA-256
  （不含运行目录、时间戳、模型名），事件里就能断言现场跑的是哪一版 ROI；
  这个字段是 additive 可选的——手写 ROI 不带它或写 「null」 都可以。

具体数字、逐类拆分与提示点校准过程见上方实测边界表和部署指南里的可选标注步骤；
两者用的是同一次 DeepPCB6 val 跑测，与本 demo 检测精度共用同一个数据源。

## 套餐对比

**摄像头 + reComputer J30 / J40（Orin）** 是 Jetson 这条路径。本页所有 Jetson
实测数据——精度、吞吐、时延、67 小时 soak——都来自 reComputer J30 系列
（J3011，Orin Nano 8GB）；本方案未单独给 J40 跑评测。首次部署时在设备上构建
TensorRT engine（在 J3011 上实测约 5 分钟），engine 因此与该设备和该 TensorRT
版本绑定。想让上面那组数字对你成立选 J3011；想要更多路摄像头的余量选
J40（本方案未单独给它跑评测）。

**摄像头 + reComputer R2000（Hailo-8）** 用功耗与成本换更小的板卡体积。
INT8 HEF 在设备外编译、部署时下载，板子上没有构建步骤。同款 Hailo-8 平台实测：硬件推理
106.75 FPS，全链路 43.92 FPS，mAP50 0.9858（对比 CPU golden 差 -0.0018）。
这些是参考值，reComputer 整机复测后更新。上面的多路扫描只在 Orin 上跑过。这块板还有三道硬前提——容器与宿主 Python minor 版本一致、驱动 /
用户态库 / Python 绑定三者都锁在 HailoRT 4.21.x、「hailo_pci」 带
「force_desc_page_size=4096」——部署指南里逐条带着做。

**reCamera Pro** 把整个节点放进相机里：取图、RV1126B NPU 上的 INT8 检测、
OK/NG 判定、Modbus TCP 服务与 MQTT 发布，判定链路里没有主机、没有网络跳数。
设备实测同一份 205 张 val：mAP50 0.9870，fp32 CPU 参考 0.9876；推理 P50 30.9 ms。
mAP50-95 是 0.8000，参考值 0.8213——这个差距来自高 IoU 下的框贴合度，在冻结阈值
0.35 下这一版与 CPU 参考在这批图上的精确率与召回率总数相同，但漏掉的 30 个框不是
同一批。两条限制：INT8 的 64 张校准图取自同一份验证集，因此 INT8 这一列相对未见过
的数据偏乐观；数字来自在设备上回放验证集图片，不是把相机对着板子拍。同一模型的 fp16 版本一并
发布（mAP50-95 0.8221、P50 110.3 ms），留给更看重框贴合度而不是帧率的工位。
这条路径不开缺件比对与尺寸测量：两者都要按工位标 ROI，本预设没有承载它们的地方。

## 使用须知

- **期望件 ROI 是画面坐标。** 摄像头一移动或重新对焦，整份期望清单就要重建。
  先固定机位再建模板，不要反过来。
- **随包的期望清单是示例，不是你的产品。** 它由一张 DeepPCB 图生成，只是一个样例。
  在这个工位有意义之前，先把 「assembly.expected[]」 换成你自己的装配位。
- **尺寸模块是纯 CPU、单平面的。** 它量的是 ROI 内最小外接矩形，按同平面标定物换算；
  零件倾斜、标定物与被测面不等距、边缘对比度低，都会体现为误差、「not_found」
  或 「uncalibrated」。
- **线圈与寄存器"同属一次判定"只在写侧成立。** 运行时在同一把锁里先写完所有寄存器
  再写线圈。读侧如果分成两次 Modbus 请求，在高判定频率下可能落在两次判定之间——
  测试中在约 20 判定/秒时观察到过。真实产线节拍下这个窗口不成立；如果在意，
  先读寄存器、把线圈当触发信号。
- **多路共享一份寄存器。** Modbus 上是最新一次判定，不区分来自哪一路；
  逐路结果从 MQTT 取。
- **包里的 MQTT broker 是本机匿名的。** 它的作用是让部署开箱即用；
  生产环境应指向带凭据的 broker。

## 数字的适用范围

- **Orin 侧数字**——检测精度、吞吐、端到端时延与多路容量：运行记录 M4，2026-09-05，主机 `orin-nano`。
- **缺件闭环与尺寸误差**——运行记录 M2，2026-09-05，同一台主机，用验证帧与合成场景。
- **Hailo INT8 精度**——运行记录 M3a，2026-09-05，在 x86 Hailo Dataflow Compiler 模拟器里，不是设备上。
- **Hailo-8 上板吞吐、时延与精度**——运行记录 M3b-pi-2，2026-09-06，fleet 主机 `harvest-pi`。
- **VLM 解释时延**——已公布数字来自 Spark GB10 工作站；请在自己的质检主机上实测。

## 许可说明

运行时代码为 Apache-2.0。检测骨干是 **YOLOX**（Megvii-BaseDetection，Apache-2.0）
——不使用 Ultralytics 的任何代码或权重，因此没有 AGPL 传染义务。训练数据是
**DeepPCB，MIT 许可**，允许再分发与商用；署名随图片一起记在
「gallery/ATTRIBUTION.md」。随包模型训练在那份裸板缺陷数据集上——它因此是什么、
不是什么，见本页顶部的说明。
