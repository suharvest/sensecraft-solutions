> **内部验证用，许可确认前不得公开演示。** 模型训练自 NEU-DET 的转载版：
> Roboflow 页面标 CC BY 4.0，但原始 NEU-DET 出处未见正式许可声明。
> 在拿到明确许可回复或替换为许可清晰的数据集之前，由它派生的一切——权重、
> ONNX、HEF、评测截图、检测叠加图——都不得用于对外 demo、客户现场展示
> 或商业物料。本页因此只放一张示意图，不放检测输出样例：
> 本包里不入库任何数据集派生图像。

## 这个方案做什么

把一台固定相机对着钢带或工件。设备逐帧判断表面有没有缺陷，并同时用两条路
把 OK/NG 判定交给产线：一个 PLC 可以直接锁的 Modbus TCP 线圈，
以及一条带上该帧全部检测框的 MQTT 消息。

识别六类缺陷：crazing、inclusion、patches、pitted_surface、rolled-in_scale、
scratches。检测、OK/NG 规则与两路输出全部在设备本地完成，图像不出设备。

## 你会得到什么

**一个 PLC 可以直接动作的判定。** 线圈 0 是 NG，线圈 1 是 OK，二者始终互斥。
每次判定先原子更新保持寄存器、再写线圈，所以 PLC 看到线圈翻转的那一刻，
寄存器 0-7 里已经是同一帧的类别、缺陷数、主缺陷框和心跳。

**一帧一条 MQTT，不是一框一条。** 判定、判定理由、缺陷数与该帧内所有检测框
放在同一条消息里。框是归一化的 `[cx, cy, w, h]`，`slot` 是帧内按分数降序的下标
——这条流水线不做跟踪，`slot` 在帧之间没有任何稳定语义。每条消息在发布路径上
都过一遍契约 schema 校验，不合格的计数并丢弃，不发出去。

**设备自带一个调试页面。** 画了检测框的 MJPEG 预览、含推理耗时与 capture→coil
时延以及 MQTT / Modbus 计数的健康接口，还有最近的判定记录。

**跨加速器只有一份解码与后处理实现。** YOLOX 解码与逐类 NMS 是同一份 numpy 实现，
backend 只负责预处理、调用加速器、把原始张量交出来。下面那些跨后端的比对之所以
有意义，就是因为两边不是各写一份后处理。

## 适合接到哪里

- **带钢与卷板表面检测**——产线上方一个固定机位，判定接到已有的剔除或打标工位。
- **给 PLC 驱动的老产线做改造**——Modbus 寄存器表就是全部对接面，
  产线上不需要任何一方会说 MQTT 或 HTTP。
- **正式部署前的数据采集**——MQTT 流里逐帧带着框与分数，
  可以先把产线录下来重新标注，再决定阈值定在哪。

## 实际效果如何

以下是在一个公开数据集上的工程基准，**不构成任何安全或质量认证依据**，
而且该数据集的许可未结清。下面每一个数字都是原作者的单次实测，
未经他人复现；所有 boundary 文件的 `reproduced_by` 都是 `null`。

**测试方法**

- 数据集 NEU6，按源组做 70/15/15 切分——同一缺陷类别下相邻编号视为同一条钢带，
  任何源组不跨集合出现。
- 精度跑在完整的 290 张验证集上（706 个标注框）。推理用 0.01 的低分阈值只跑一次，
  mAP50 与冻结阈值下的 P/R/FP/FN 都出自这一次，因此阈值扫描是事后过滤，
  不是三次独立测试。
- 吞吐、时延与多路容量都在部署镜像里跑，挂载方式与 compose 文件一致，
  测的就是实际发布的那套 ABI。
- 输入是 290 张不同验证图拼成的合成视频，640x640 / 10 FPS。帧间没有时间连续性，
  解码成本也与真实 H.264 码流不同。
- 验证集每张图都带缺陷，所以帧级误报（干净帧被判 NG）在这个数据集上根本测不到，
  只能测漏检。

### 实测边界——Jetson Orin NX

板卡：Jetson Orin NX 16GB（Seeed reComputer Super J4012），L4T R36.4.3 /
JetPack 6.2，TensorRT 10.3.0.30，功耗模式 MAXN_SUPER（只读未改），
镜像 `edge-inspection-jetson:0.1.0-dev`，仓库 commit `670e433`。
YOLOX-Tiny 640x640 FP16。

| 指标 | 数值 | 条件 | 来源 |
|---|---|---|---|
| mAP50 | 0.7577 | 290 张验证图 / 706 框，TensorRT FP16，0.01 阈值单次推理 | 本次实测，`boundary.accuracy.yaml` 稳定档 |
| 冻结阈值 0.35 下的精确率 / 召回率 | P 0.7652 / R 0.6969 | 同一次推理事后过滤；TP 492 / FP 151 / FN 214；290 帧里 7 帧整帧无输出 | 本次实测，`boundary.accuracy.yaml` 稳定档 |
| 阈值 0.6 下的召回率 | R 0.5807 | 同一次推理；FN 由 214 升到 296，整帧漏检由 7 帧升到 39 帧（13.4%）；精确率升到 0.865 | 本次实测，`boundary.accuracy.yaml` 下降档 |
| 阈值 0.9 下的召回率 | R 0.0241 | 同一次推理；290 帧里 273 帧整帧无输出（94%）；crazing 与 rolled-in_scale 召回归零 | 本次实测，`boundary.accuracy.yaml` 失败档 |
| 推理调用 P50 | 8.797 ms（113.7 FPS） | 60 帧预解码循环上跑 500 次 `detect()`，含 letterbox、execute 与 CPU NMS。P95 9.097 / P99 9.223 ms | 本次实测，`boundary.throughput.yaml` |
| 单纯 engine execute | 约 5.6 ms（约 178 FPS） | 运行时自己的 `inference_time_ms` 字段，只含 execute——差出的约 3.2 ms 是 letterbox 与 CPU 侧 NMS | 本次实测，`boundary.throughput.yaml` |
| 产线节拍下的全链路 | 9.999 FPS，丢帧 0 | 单路按配置的 10 FPS 节流；含采集、推理、判定、Modbus、MQTT 与契约校验 | 本次实测，`boundary.throughput.yaml` 稳定档 |
| 去掉节流的全链路 | 76.5-104.3 FPS | 去掉源节流；两个数字的差别在样本长度（300 帧按 wall clock 算 vs 3000 帧 app 侧统计） | 本次实测，`boundary.throughput.yaml` 下降档 |
| capture→Modbus 线圈 P50 / P95 / P99 | 9.298 / 9.441 / 9.549 ms | 单路 10 FPS，3000 个样本，max 9.926 ms，无一超过 20 ms；两端时间戳都由运行时自己打 | 本次实测，`boundary.e2e_latency.yaml` 稳定档 |
| 满速下 capture→Modbus 线圈 P50 / P95 / P99 | 35.90 / 39.75 / 40.36 ms | 同样 3000 个样本，跑在 104 FPS；多出的约 26 ms 是帧在深度 2 的队列里排队，不是推理变慢（均值仍 5.35 ms） | 本次实测，`boundary.e2e_latency.yaml` 下降档 |
| 并行路数——稳定 | 8 路 x 10 FPS | 每级 5 min；每路 9.989 FPS，丢帧 0.02%，P95 72.3 ms。判据写在脚本里，不是事后解读 | 本次实测，`boundary.multistream.yaml` 稳定档 |
| 并行路数——下降 | 12 路 x 10 FPS | 每路 9.306 FPS，丢帧 6.83%，P95 104.0 ms。从这里往上总吞吐锁死在 110-112 FPS：到顶的是单线程推理 | 本次实测，`boundary.multistream.yaml` 下降档 |
| 并行路数——失败 | 24 路 x 10 FPS | 每路 4.593 FPS，丢帧 53.95%。进程不崩——过半输入被静默丢弃，产线上等于漏检 | 本次实测，`boundary.multistream.yaml` 失败档 |
| 72 h soak | 暂无 | 2026-09-05T06:22:47Z 起跑，预计 2026-09-08T06:22Z 结束。起跑基线：RSS 250.5 MiB、CPU 10.9%、9.96 FPS、丢帧 0、tj 62.1-62.7 C | 进行中，`boundary.soak.yaml` 三档全 null |

同一次推理的逐类 AP50——上面那个精度数字实际是从这里来的：

| 类别 | 标注框数 | AP50 | 0.35 下召回 |
|---|---:|---:|---:|
| scratches | 95 | 0.9685 | 0.9263 |
| pitted_surface | 70 | 0.9301 | 0.8857 |
| patches | 122 | 0.9065 | 0.8689 |
| inclusion | 184 | 0.7658 | 0.6902 |
| rolled-in_scale | 104 | 0.6149 | 0.5481 |
| crazing | 131 | 0.3603 | 0.3969 |

crazing 明显是最弱的一类，而且调阈值救不回来——这是模型能力上限，训练时就已经
看到。主要缺陷是 crazing 的产线需要重训模型，不是重调阈值。

FP16 engine 还与同一份 ONNX 的 CPU（onnxruntime）结果做过逐框比对：
643 对匹配，CPU 侧多 3 个框、TensorRT 侧一个不多，IoU 均值 0.9972（最小 0.8311），
分数差均值 0.0011，mAP50 差 0.0003。FP16 没有改变任何一帧的 OK/NG 判定。

### Hailo-8——harvest-pi 真机实测数字（2026-09-06）

Raspberry Pi 5 + Hailo-8 这条路径用的是 Dataflow Compiler 3.31.0 /
HailoRT 4.21.0 编出的 INT8 HEF（level-0，`optimization_level=0`）。2026-09-06
在 fleet `harvest-pi` 上（用户授权临时腾出这块板卡唯一的 Hailo-8，窗口约
15 分钟）拿到了真机数字：

| 指标 | 数值 | 条件 | 来源 |
|---|---:|---|---|
| 硬件推理 FPS（`hailortcli run`） | 106.75 FPS | 854 帧/8 秒，HW 延迟 8.47 ms，不含应用层前后处理 | `evaluation/runs/2026-09-06-rpi-hailo/results.md` 第 7.1 节 |
| mAP50 对比 CPU golden（290 张全 val） | Hailo 0.7091 / CPU 0.7574，差 -0.0483 | `evaluate_accuracy.py detect --backend hailo` + `compare` | 同上 第 7.2 节 |
| 逐框匹配率（IoU≥0.5） | 86.66%（523/684 对匹配框） | 同一次比对 | 同上 第 7.2 节 |
| 应用层推理 FPS | 91.49 FPS（p50 10.93 ms，p95 13.19 ms） | 只计 `detector.detect()`，裸机进程复用现成 Hailo Python venv | 同上 第 7.4 节 |
| 全链路吞吐 | 46.14 FPS | 真实 InspectionApp：判定+Modbus+MQTT+契约校验，源节流去掉 | 同上 第 7.4 节 |
| 10 FPS 产线节拍下端到端时延 | p50 11.61 ms，p95 14.99 ms，p99 16.63 ms | `e2e_latency.py`，采集入队到 Modbus 写完 | 同上 第 7.5 节 |
| MQTT 事件 | 抓 20 条，抽样 3 条全部过 `contracts/validate_payload.py`（mqtt-event v1） | `mosquitto_sub` 订阅设备上现成 broker | 同上 第 7.6 节 |
| 裸机进程 RSS | 约 126 MB | 本轮未走容器化测，Dockerfile/ABI 链路此前已单独验证过 | 同上 第 7.7 节 |

六类里 crazing（AP50 0.3873）和 rolled-in_scale（AP50 0.4483）对 INT8 量化
损失最大，与下面 emulator 阶段的结论方向一致，不是上板才出现的新问题。
`compare` 输出里 matched_pairs/a_only/b_only 这类计数字段本轮清理设备前
没有单独落盘（mAP50 与分数差本身是完整数字），完整说明见
`evaluation/runs/2026-09-06-rpi-hailo/results.md` 第 7.2、7.9 节。

从同一份 ONNX 编了两版 HEF，在同样的 20 张验证图（45 个框）上比对——
这 20 张与校准集不重叠，且跨六类均匀分布：

| 路径 | mAP50 | 0.35 下 P | 0.35 下 R | 整帧漏检 | 条件 | 来源 |
|---|---:|---:|---:|---:|---|---|
| CPU onnxruntime（基准） | 0.7228 | 0.6429 | 0.6000 | 0 | 同一份 ONNX，同样 20 张图 | emulator 实测，`2026-09-05-m3-hef` |
| emulator，INT8 level-0 | 0.6927 | 0.7353 | 0.5556 | 3 | `optimization_level=0`，val 集 128 张校准图 | emulator 实测，`2026-09-05-m3-hef` §2 |
| emulator，INT8 level-1 | 0.7266 | 0.7179 | 0.6222 | 2 | `optimization_level=1`，train 集 1024 张校准图，启用 Bias Correction | emulator 实测，`2026-09-05-m3-hef` §6.5 |

level-1 是本方案部署的默认值。它把 level-0 掉得最多的两类补了回来——
inclusion 0.5415→0.6552，rolled-in_scale 0.4048→0.5108——代价是编译更久
（773 s→1180 s，全部涨在 optimize 步骤）。它的 mAP50 比 CPU 浮点基线高 0.0038，
在 20 张图、45 个框的样本量下这是采样噪声，不是「INT8 比浮点更准」的证据。

emulator 能证与不能证的：它用的是编译产物里的定点参数，因此能证明九张量输出的
拼接与 CPU 路径数值等价（42 个框全匹配，最小 IoU 0.9992），也能量出这个子集上的
INT8 损失。它与硬件不保证 bit-exact，它自己报的耗时是 x86 GPU 的耗时，
与 Hailo-8 无关。板上的全验证集精度仍然是欠账。

### 部署占用

| 项 | 数值 | 条件 | 来源 |
|---|---|---|---|
| 设备上构建 TensorRT engine | 291 s | Orin NX 16GB，JetPack 6.2，TRT 10.3，YOLOX-Tiny 640x640 FP16，静态 shape | 本次实测，`2026-09-05-m2-orin` §1 |
| Jetson 镜像 | 375 MB | `edge-inspection-jetson:0.1.0-dev`；宿主机 TensorRT 与 CUDA 挂载进来，不打进镜像 | 本次实测，`2026-09-05-m2-orin` |
| 树莓派新增占用 | 约 452 MB | 运行镜像磁盘占用约 443 MB + 8.9 MB HEF + 配置；2026-09-06 已在 harvest-pi 原生 arm64 构建通过（444 MB），同一块板上真实推理数字已测出（见 Hailo-8 一节） | 交叉构建实测 `2026-09-05-m3-hef` §3.1；原生构建 `2026-09-06-rpi-hailo` |

## 检测器选型：基线 vs 先进

YOLOX-Tiny 是默认值，也是唯一在 Jetson 上实测过、唯一在 Hailo 套餐上出货的
track。另外评测了两种 NMS-free 的 DETR 架构——D-FINE-S 与 RT-DETRv2-S，
都是 Apache-2.0，都是从各自 COCO-only 的 checkpoint 微调（不使用也不分发
Objects365 系权重）。`config/config.json` 里的 `model.track` 选择跑哪一个；
Jetson 部署步骤把它开放成一个 **检测器 Track** 选项。

| 检测器 | mAP50 | 冻结 0.35 下 P / R | 整帧漏检 | CPU `detect()` P50 / P95 / P99 (ms) |
|---|---:|---|---:|---|
| YOLOX-Tiny（默认） | 0.7574 | 0.7632 / 0.6983 | 7/290 | 30.2 / 35.7 / 52.7 |
| D-FINE-S | 0.7499 | 0.4956 / 0.8017 | **0/290** | 54.0 / 68.1 / 95.8 |
| RT-DETRv2-S | 0.7317 | 0.4575 / 0.7847 | 1/290 | 83.1 / 93.8 / 126.1 |

三者前提相同：同一份 290 张 NEU6 val 图（706 框）、同样的 640x640 静态
batch-1 输入、同一台机器（arm64 Mac，onnxruntime CPUExecutionProvider）、
每个 track 各 1 个种子、冻结阈值 0.35。来源：
`evaluation/runs/2026-09-06-a1-cpu/results.md`。

**mAP 接近，但冻结阈值不是跨架构的公平比较。** 0.35 是按 YOLOX 的
`obj x cls` 分数分布标定的，没有按架构分别重新标定——这也是上表 P/R
看起来不对称的原因（DETR 的 sigmoid decoder 分数分布不同）。改成按精度
对齐而不是按阈值对齐（P 约 0.81-0.87），D-FINE 的召回比 YOLOX 高
2-7 个点，整帧漏检从 YOLOX 的 38 帧降到 20 帧。**这是单种子的观察，
不是已确认的结论**——每个 track 目前只跑了 1 个种子，需要 3 个种子才能
定论。

**crazing 换架构也没有改善。** 三者的 AP50 都在 0.30-0.36（YOLOX 0.360、
D-FINE 0.302、RT-DETRv2 0.310）——与 Jetson 实测边界表里对 YOLOX 单独下的
结论一致：这是模型能力上限，不是换个检测头能解决的。

**Hailo-8 对两条 DETR track 都不支持——树莓派套餐继续用 YOLOX-Tiny。**
Hailo Dataflow Compiler 3.31.0 的解析器直接拒绝 RT-DETRv2-S（`GridSample`
×9、`GatherElements` ×3、`TopK` ×2 全部报不支持——可变形注意力算子在
Hailo-8 上没有实现），对 D-FINE-S 甚至在给出这份清单之前就崩了（解析器
自身的一个 `MatMul` 形状假设不成立，不是「支持/不支持」的判定）。
Hailo 部署步骤的 `detector_track` 选项因此不提供 `dfine`/`rtdetrv2`。

**RKNN 能转但未上板验证。** 两份 ONNX 都成功转成了 RK3576 的 `.rknn`
（FP16，不量化），但 18 处 `GridSample` 节点（每个模型各 9 处）走的是
自定义算子回退，没有对应的 NPU 实现——转换成功不代表这部分图在 NPU 上跑。
探针阶段没有可用的 RK3576 设备核实与 CPU 的输出一致性，所以这是**未验证**，
不是负面结论。

来源：`tracks/detector/PROVENANCE.md`（两个上游的许可与 commit 锁定）、
`evaluation/runs/2026-09-06-a1-probe/results.md`（Hailo/RKNN 探针）。

## 无监督异常检测（可选）

一个可选的第二模型（anomalib EfficientAD-S，Apache-2.0）可以与检测器并行
跑，只用无缺陷（"OK"）参考图训练，标出与参考集不像的帧——包括检测器
从未学过命名的缺陷**类型**。它从不替代检测器的判定：`anomaly_score` 是
MQTT 里附加的独立字段（`contracts/MQTT.md`），`anomaly_verdict` 从不与
顶层 `verdict` 合并。

| 指标 | 数值 | 条件 | 来源 |
|---|---|---|---|
| 像素级 AUROC | **0.8752** | DeepPCB `pcb` OK/异常切分：205 张 OK val + 213 张 OK test + 213 张异常 test | `evaluation/runs/2026-09-05-a2-cpu/results.md` |
| 像素级 AUPRO（FPR ≤ 0.30） | **0.6494** | 同一次跑测，1177 个连通缺陷区域 | 同一次跑测 |
| 图像级 AUROC | **0.5201**（0.5 = 随机） | 同一次跑测——见下方 caveat | 同一次跑测 |
| 同源 OK 集对照：图像级 AUROC（NEU patch） | **0.7055** | 另一次 EfficientAD-S 训练/评测；OK 与缺陷 patch 裁自同一批 NEU 照片、同一次拍摄，仅裁剪位置不同；256×256 patch；数据集许可 UNRESOLVED，仅供内部方法验证 | `evaluation/runs/2026-09-06-a2-neu-cpu/results.md` |
| 未见缺陷召回，留一类（像素/区域级） | **0.225-0.955**，按类差异极大（open 0.955，spur 0.225） | 留出类完全不进标定；模型没见过这个标签 | 同一次跑测 §2 |
| 双路延迟开销（检测器 + EfficientAD，CPU 参考实现） | **+139 ms P95/帧** | queue=2、超时 500 ms（随包默认值）；120/120 帧成功汇合，丢帧 0 | 同一次跑测 §3 |

**像素/区域级判据可用，图像级不可用，且试过 12 种聚合方式都没救回来。**
把像素级热力图压成一个图像标量分数（max、top-k 均值、Otsu 前景 mask 内
max、高斯平滑后 max、连通域面积/最大连通域占比）——12 种方式的图像 AUROC
全部落在 0.495-0.530，都在随机水平的噪声带内。根因不是图像边缘的稀疏
噪声尖峰（去边处理没有带来可测的差异）；是 OK 集（扫描模板图）与异常集
（实拍图）之间弥漫全图的分数偏置，它以同样的方式污染任何对像素图做的
单标量汇总。像素/区域级指标之所以还有效，是因为它们只在同一张异常图
内部比较（框内 vs 框外），偏置在这个比较里被抵消；图像级指标比较的是
两张来自不同来源的图像，偏置抵消不掉。

**OK 参考集必须与被测图同源采集——上面这组数字用的那份不是。这不是推断，
是两组对照实验的结果：OK/异常不同源（本模型，DeepPCB 模板图 vs 实拍图）
图像级 AUROC 0.5201（随机水平）；OK/异常同源（另一次 EfficientAD-S
训练评测，NEU patch，OK 与异常 patch 裁自同一批照片、同一次拍摄）图像级
AUROC 回升到 0.7055——见上表"同源 OK 集对照"一行。** NEU6（本方案检测器
自己的训练数据）完全没有无缺陷图像：1799 张图里每一张都至少带一个标注
缺陷。上面的异常模型因此训练与评测在另一个 MIT 许可的数据集（DeepPCB）上，
它的 OK 图是扫描出来的板卡模板图，而异常图是另一块实体板卡的实拍照片——
这个模板 vs 实拍的差异正是上面说的那个弥漫偏置，不代表真实产线上同一台
相机拍出的 OK/异常图会长什么样。**同源对照的 0.7055 本身也不是产品指标**
——它来自 patch 级评测（256×256 裁剪，非整图）、数据集许可 UNRESOLVED
（仅供内部方法验证，不得用于对外 demo）、且只跑了一次未经复现，不能当成
"同源就能做到 0.7 AUROC"的产品承诺。**启用 `anomaly.enabled` 之前，先用
真实检测相机采集你自己的 OK 样本，并在这批图上重新标定
`anomaly.threshold`**——不要把上面的像素 AUROC 当成你产线图像上的承诺；
它证明的是机制能跑通，不是你数据集上的数字。

配置：`config/config.json` 里的 `anomaly.enabled`（默认 `false`）与
`anomaly.threshold`，在 schema 里是 additive 字段——关掉它，本页其余每一个
实测数字都照样成立。启用后，把 `anomaly_score` 和 `heatmap_ref` 当成
像素/区域级信号来读，不要当成帧级的正常/异常开关，上面的数字就是原因。

来源：`tracks/anomaly/README.md`、`tracks/anomaly/PROVENANCE.md`
（anomalib `lib/v2.6.0`，Apache-2.0）、
`evaluation/runs/2026-09-05-a2-cpu/results.md`、
`evaluation/runs/2026-09-05-a2-aggregation/results.md`。

## 可选：VLM 解释

运行时可以把一帧交给外部共享 VLM 服务（`edge-vision-vlm`）生成一段人话
解释。这是一条旁路，不是第二个判定者：它不进帧循环、不改变 `verdict`，
服务关闭、变慢或不可达时，OK/NG 输出与没有这条旁路完全一样。

- **触发条件**（两条依据任一即可，有框优先）。`low_confidence`——主缺陷
  分数低于 `vlm.trigger.min_confidence`。`anomaly`——`anomaly_score`
  过了 `anomaly.threshold` 且**检测器一个框都没有**，此时没有这条旁路就
  完全没有机器可读的判定理由。每路按 `vlm.trigger.min_interval_s` 限速，
  绝不是每帧调用一次。
- **旁路事件。** 有界、drop-oldest 队列加独立 worker 线程提交调用；
  `inspection/<流编号>/results` 上的主事件照常按原节奏发布，不管 VLM
  有没有回应。回应了才会在 `inspection/<流编号>/explanations` 上再发
  一条，按同一个 `frame_id` 对齐。
- **不阻塞主链路。** 客户端硬超时会放弃这次调用；连续失败达到阈值后
  熔断器会停调一段冷却期，冷却期靠 `GET /healthz` 探活。
- **时延不是可以按帧规划的数字。** 在共享服务自己的评测硬件——NVIDIA
  Spark GB10 工作站，**不是这台设备**——上实测，Qwen3-VL-2B bf16 光生成
  阶段就是 P50 约 3.2 s / P95 约 7.2 s（`max_tokens=320`）。这正是这次
  调用要离开热路径的原因；这套集成目前没有 Orin 上的实测时延。

设置 `vlm.enabled: true` 并把 `vlm.base_url` 指到一个可达的
`edge-vision-vlm` 实例即可启用；完整步骤见部署指南，包括设备上需要的
`no_proxy` 设置。

来源：上游 `README.md` "VLM 解释" 一节、
`contracts/explanation-event.schema.json`、
`evaluation/runs/2026-09-06-mvlma-stub-localhost/results.md`
（Mac 上用 stub backend 做的接线联调，不是真实模型的时延实测）。

## 输出接口

| 输出 | 位置 | 内容 |
|---|---|---|
| 判定 | Modbus TCP 502 端口，unit 1，线圈 0-1 | 线圈 0 NG / 线圈 1 OK，互斥，在寄存器之后写 |
| 判定明细 | Modbus TCP 502 端口，unit 1，HR 0-7 | 类别 ID、缺陷数、主缺陷框 cx/cy/w/h 归一化 x10000、心跳 Unix 秒两个字 |
| 检测结果 | MQTT 1883 端口，主题 `<设备名>/inspection/<流编号>/results` | 一帧一条 JSON：判定、理由、缺陷数、每个框的类别、分数与归一化 bbox |
| 实时画面 | HTTP 8080 端口 `/preview.mjpg`、`/healthz`、`/events`、`/snapshot.jpg` | 带框的 MJPEG 预览、健康计数、最近判定 |

`<设备名>` 与 `<流编号>` 都在部署步骤里由你自己填。它们存在的意义是让多条产线
共用一个 broker、一台设备接多路相机。`stream_id` 同时也在 payload 里，
下游不必解析主题就知道消息来自哪一路。

## 部署方式对比

**IP 摄像头 + reComputer J（Orin）** 是有实测的那条路径。上面表里每一个数字
都取自 Orin NX 16GB。TensorRT engine 在部署过程中于设备上构建——它与那块 GPU
架构和那个 TensorRT 版本绑定，不做分发。需要能拿出去对账的数字就选它。

**IP 摄像头 + Raspberry Pi 5（Hailo-8）** 是更便宜的那条。已经在真机
（harvest-pi，2026-09-06）跑出数字：硬件推理 106.75 FPS，全链路 46.14 FPS，
mAP50 0.7091（对比 CPU golden 0.7574，逐框匹配率 86.66%）。设备上仍有三道
ABI 关卡要先过（Python minor 版本、HailoRT 驱动/用户态/固件三件套、
`force_desc_page_size=4096`），部署步骤会逐个检查。

## 使用须知

- **阈值是一个业务决定，上面的扫描给它标了价。** 0.35 是部署值。
  抬到 0.6 换来精确率 0.765→0.865，代价是 290 帧里整帧漏检从 7 帧变成 39 帧。
  改之前先想清楚你的产线能吃哪一种错误。
- **误报没有测过。** 验证集每张图都带缺陷，所以这里没有任何数字说明干净钢带
  被判 NG 的频率。这个数字只能来自你自己的产线。
- **按当前配置一次部署一路相机。** 运行时支持多路，Orin NX 上实测稳定 8 路，
  但部署步骤只配置一路。其余的加进设备上的 `streams` 列表再重启容器。
- **多路共用同一组 Modbus 寄存器。** 契约只定义了一套线圈与寄存器，
  多路时最后一次判定生效。需要按路独立寄存器的产线要先改契约。
- **路数的天花板是单线程推理循环，不是 GPU。** 从 12 路起总吞吐锁死在约 110 FPS，
  而 engine 本身只要 5.3-5.6 ms（约 178 FPS）。加速器 context 不是线程安全的，
  推理是按设计串行的。
- **实测输入是合成视频，不是相机。** 290 张验证图按 640x640 / 10 FPS 拼成。
  真实相机的 H.264 解码方式不同，分辨率更高时解码占比还会上升。
  定路数之前先用你自己的视频源压测。
- **本包里的 MQTT broker 是给调试用的。** 它以 `allow_anonymous true` 运行。
  生产产线应当改指向带凭据的 broker。

## 许可说明

运行时代码是 Apache-2.0。默认检测骨干用 YOLOX（Megvii-BaseDetection），
同样是 Apache-2.0——这是刻意的选择，为的是避开 Ultralytics 权重带来的
AGPL 条款。本方案任何位置都没有使用 Ultralytics 的代码或权重。两个可选的
先进检测器 track 上游同样是 Apache-2.0（D-FINE，Peterande/D-FINE；
RT-DETRv2，lyuwenyu/RT-DETR），且只从各自 COCO 许可的 checkpoint 微调——
不下载也不分发 Objects365 系权重，因为上游自己声明那部分许可未确认
（`tracks/detector/PROVENANCE.md`）。可选的无监督异常检测模型
（anomalib EfficientAD-S）同样是 Apache-2.0，包括它的预训练 teacher 权重
（`tracks/anomaly/PROVENANCE.md`）；它的 OK/异常训练数据（DeepPCB）是
MIT 许可，与 NEU-DET 是两个不同的数据集。

**没结清的是训练数据。** 模型训练自 NEU-DET 的转载版。该转载版的 Roboflow
页面标 CC BY 4.0，但原始 NEU-DET 出处未见正式许可声明，从原作者到那个页面的
授权链条并未确立。由它派生的一切——checkpoint、ONNX、两份 HEF、TensorRT
engine、评测叠加图——在拿到明确许可回复或替换为条款清晰的数据集之前，
只限内部验证使用。本包不入库任何由该数据集派生的图像，所以这里唯一的插图
是为本方案单独画的示意图。在那之前不要把本方案用于对外 demo、
客户现场展示或商业物料。
