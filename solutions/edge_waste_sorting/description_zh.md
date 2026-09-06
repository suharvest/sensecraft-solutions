# 投放点垃圾分类

触发拍一张，拿回这件东西是什么材质、该进中国生活垃圾四分类里的哪一档，
通过 MQTT 一条消息发出去。

**基线分类器是 EfficientNet-Lite0（m1c），不是 MobileNetV3-Small。**
原基线（MobileNetV3-Small，"m1b"）在三条实测过的边缘链路上（Hailo emulator、
RK3576、RK3588）都出现 INT8 量化塌缩；EfficientNet-Lite0 不塌缩，现已成为
出货基线。下面大多数精度数字仍来自 Apple M4 CPU 上的 onnxruntime，但 Hailo-8
与 RK3588 两节带有真实 INT8 数字：RK3588 数字来自真实的 Radxa ROCK 5T 设备，
Hailo-8 数字只来自 DFC emulator——**本页任何地方都没有用过 Hailo-8 真机。**
目前也没有任何套餐声明 `verified: [hardware]`。

## 这个方案做什么

一次触发——按钮、HTTP 调用，或画面里的移动——让设备拍一张图，把图里的物品
分到八个物料类别之一，由这个类别查表得到中国四分类，然后发一条 MQTT 消息，
带上类别、四分类、带置信度的 top3，以及所存图片的引用。图片字节不出设备；
payload 里只有路径或对象存储 URI。同时一个异步回调收到四分类结果，
翻盖、继电器或指示灯可以据此动作。

## 你会得到什么

- **一个头出两层答案。** 模型预测八个物料类别——paper、cardboard、glass、
  metal、plastic、textile、organic、residual。中国四分类（可回收物 / 厨余垃圾 /
  有害垃圾 / 其他垃圾）是它上面的一张查表，不是第二个头，所以各地口径变化
  是改表而不是重训。
- **触发即拍，不是视频流。** 按钮、HTTP 或移动侦测，800 ms 去抖；
  前一次未完成时到达的触发会被合并而不是排队。也有连续模式，限速运行，
  且要连续三帧 top-1 相同才发布。
- **契约是被检查的，不只是写在文档里。** 每条 payload 发布前都过一遍事件
  schema 校验，包括 JSON Schema 表达不了的两条：`category` 必须等于
  `top3[0]`，`confidence` 必须等于 `top3[0].confidence`。不合格的计数并丢弃。
- **一条可选的开放词汇 track。** SigLIP 2 视觉塔对常量文本原型打分，
  部署时用 `model.track: open_vocab` 选择。它不重训就能加类别，
  同一份图像嵌入既能用中文也能用英文回答，还能给出"这不在我的词表里"的
  分数——这些是闭集头结构上做不到的。代价是慢 40 倍。
- **不绑引脚的执行机构接口。** 运行时回调时带上一个类别；这个类别送到哪里
  是集成工作，正因如此同一份构建才能跑在排针不同的板子上。

## 适合接到哪里

- 家用与社区投放点：在投放的那一刻拍下单件物品，告诉居民该进哪个桶。
- 分拣工位：操作员逐件展示物品，需要一个第二意见外加一条 MQTT 上的审计记录。
- 带电动翻盖或分道指示灯的垃圾桶：由四分类结果经 GPIO 回调驱动。

不在范围内：传送带分拣的机械联动，以及路面散落垃圾检测。后者是二期，
需要检测器而不是分类器——本模型假设一图一件。

## 实际效果如何

**这不是合规或监管用的分类系统。** 四分类映射是本项目维护的一张表，
不是主管部门的认定结果，各城市口径本来就有差异。这里的任何输出都不应作为
收费、处罚或合规判定的唯一依据。

两个分类器在**同一份 split**、同一批图片、同样 224² 输入、同样后处理、
同一台 Apple M4 CPU 上测过。

### 实测边界——基线分类器（EfficientNet-Lite0，m1c）

| 指标 | 数值 | 条件 | 来源 |
|---|---|---|---|
| 物料八类 top-1 | 0.8877 | val，7417 张；onnxruntime 1.25.1 CPU；ONNX `e9f9e847…`，13,477,056 B | 本项目 `evaluation/runs/2026-09-06-m1c-cpu` |
| 物料 top-5 | 0.9833 | 同上 | 同上 |
| 中国四分类 top-1 | 0.9500 | 同上；在八类 argmax 之上查表得到 | 同上 |
| macro-F1（有样本的 7 类） | 0.8511 | 不含 `textile`——零样本 | 同上 |
| 物料八类 top-1，held-out test | 0.8802 | test，7290 张，与 m1b 同一份 split | 同上 |
| 推理时延（单图，CPU） | mean 16.796 ms / p50 14.724 ms / p95 28.718 ms | 仅 `session.run`，Apple M4 CPU，batch 1 | 同上 |
| 置信度低于 0.5 的图 | 318 张（4.3%） | val | 同上 |
| ORT PTQ INT8 与 fp32 一致率（200 张 val） | 0.965 | per_channel + MinMax，未塌缩 | `evaluation/runs/2026-09-06-m1c-int8-diag-quick` |

**为什么换基线。** MobileNetV3-Small（m1b）在同一份 split 上 top-1 略高
（val 0.8792 对 Lite0 0.8877——其实 Lite0 **高 0.85 个百分点**，不是更差），
但它的 INT8 量化图在每一条测过的边缘链路上都塌缩：Hailo emulator top-1
0.15、RK3576 一致率 0.10、RK3588 一致率 0.22，同一批链路上 fp16 一致率都在
0.98 左右（`2026-09-06-m1b-hef`、`2026-09-06-rk3576-cat`、
`2026-09-06-rk3588-radxa`）。ORT PTQ 复现了同样的塌缩，排除了「厂商编译器
特有 bug」这个可能。EfficientNet-Lite0（无 SE 分支、无 hard-swish）在同一批
INT8 流水线上不塌缩——见下方 Hailo-8 与 RK3588 两节。代价只在 CPU 上：
平均推理时延从 1.886 ms 涨到 16.796 ms（**CPU 上约慢 9 倍**），因为 Lite0
（13.5 MB ONNX）FLOPs 比 MobileNetV3-Small（6.1 MB）更高。在真正测过的边缘
NPU 上（Hailo-8 emulator、RK3588），Lite0 的时延与 MobileNetV3-Small 相近甚至
更快——CPU 上的这 9 倍代价不会带到下面的 NPU 数字里。

**两个 top-1 必须一起报。** 四分类（0.9500）比物料层（0.8877）高得多，
是因为 glass↔metal↔plastic 的混淆被吸收掉了——三者都映射到可回收物。
只报四分类那个数字会高估模型对材质的认知。

### MobileNetV3-Small（m1b）——已被取代，保留作 INT8 塌缩对照

同一份 split、同一批图、同一台 CPU。这个模型不再是出货基线；留在本页是
因为它的 INT8 失败是换基线的原因，它的 fp16 数字仍是有效对照。

| 指标 | 数值 | 条件 | 来源 |
|---|---|---|---|
| 物料八类 top-1 | 0.8792 | val，7417 张；ONNX `51c7c0ed…` | 本项目 `evaluation/runs/2026-09-06-m1b-cpu` |
| 物料 top-5 | 0.9854 | 同上 | 同上 |
| 中国四分类 top-1 | 0.9519 | 同上 | 同上 |
| macro-F1（有样本的 7 类） | 0.8292 | 不含 `textile` | 同上 |
| 物料八类 top-1，held-out test | 0.8807 | test，7290 张 | 本项目 `evaluation/runs/2026-09-05-w1-cpu` 基线列 |
| 推理时延（单图，CPU） | mean 1.886 ms / p50 1.769 ms / p95 2.276 ms | 仅 `session.run`，Apple M4 CPU，batch 1 | `evaluation/runs/2026-09-06-m1b-cpu` |
| 置信度低于 0.5 的图 | 335 张（4.5%） | val | 同上 |
| **INT8 塌缩——Hailo-8 emulator** | top-1 0.15，与 CPU/native 一致率 0.115（200 张 val） | 同一批 200 张图 fp16 一致率 1.000 | `evaluation/runs/2026-09-06-m1b-hef` |
| **INT8 塌缩——RK3576（cat-remote，真机）** | 与 CPU golden 一致率 0.10 | 同一台设备 fp16 一致率 0.98 | `evaluation/runs/2026-09-06-rk3576-cat` |
| **INT8 塌缩——RK3588（radxa，真机）** | 与 CPU golden 一致率 0.22 | 同一台设备 fp16 一致率 0.98 | `evaluation/runs/2026-09-06-rk3588-radxa` |

**根因未完全证实。** 排除 SE 分支的数值链路并不能修复塌缩，ORT PTQ 独立于
任何厂商编译器复现了同样的塌缩——这是全网退化，不是局部算子问题。训练
recipe 里确实存在一个具体缺陷：`AdamW(model.parameters(),
weight_decay=1e-4)` 把 weight decay 施加到了 BatchNorm 的 gamma/bias 上，
m1b checkpoint 里 34 个 `BatchNorm2d` 层中有 4 个 `running_var`/`|gamma|`
退化到 float32 反规格化量级，位置恰好落在 INT8 精度断崖处。
EfficientNet-Lite0 用同样的 weight decay 设置，也有同类型的权重离群
（`|w|` 最大 35.70 对 m1b 的 52.35，只降了 32%），却**没有**塌缩——离群幅度
的降幅不足以单独解释一致率从 0.115 跳到 0.89 以上这个量级的改善。更可能的
读法是 SE 门控 + hard-swish 结构本身对 INT8 更敏感，weight-decay 缺陷是
背景因素、放大了这种敏感性而非单独致因。这个判断没有做消融实验（例如给
m1b 加 no-decay 参数组重训）验证。

### 实测边界——开放词汇 track（SigLIP 2 ViT-B/16）

同一份 split、同一批图、同样后处理、同一台机器。

| 指标 | 数值 | 条件 | 来源 |
|---|---|---|---|
| 物料八类 top-1 | 0.8501 | val，7417 张；英文 prompt 集 `waste8-en/v1`，模板 `t02`，16-shot α=0.8，温度 0.0075 | 本项目 `evaluation/runs/2026-09-05-w1-cpu` |
| 物料 top-5 | 0.9987 | 同上 | 同上 |
| 中国四分类 top-1 | 0.9393 | 同上；走层级路径（先八类再映射） | 同上 |
| macro-F1（7 类） | 0.7460 | 同上 | 同上 |
| ECE（15 桶） | 0.0221 | 同上 | 同上 |
| 开放集 AUROC | 0.7538 | 有样本的 7 个类的均值，留一类当未知，分数 = `1 - max softmax` | 同上 |
| 跨语言一致率（中/英同图） | 物料 0.8698 / 四分类 0.9143 | 一份视觉嵌入配三套原型——这个数字里没有预处理或采样噪声 | 同上 |
| 物料八类 top-1，held-out test | 0.8620 | test，7290 张；模板/α/温度从未在它上面搜过 | 同上 |
| 推理时延（单图） | p50 66.93 ms / p95 91.62 ms | Apple M4 CPU，batch 1，仅视觉塔 | 同上 |

### 基线 vs 开放词汇，同 split

| 指标 | 基线（MobileNetV3-Small） | 开放词汇（SigLIP2-B/16） |
|---|---:|---:|
| 物料八类 top-1，val | **0.8792** | 0.8501 |
| 物料八类 top-1，test | **0.8807** | 0.8620 |
| 中国四分类 top-1，val | **0.9519** | 0.9393 |
| macro-F1，val | **0.8292** | 0.7460 |
| ECE（15 桶），val | 0.0308 | **0.0221** |
| 开放集 AUROC | 做不了——闭集头拿掉一类等于重训 | **0.7538** |
| 跨语言一致率 | 没有文本侧 | **0.8698 / 0.9143** |
| 零样本加类 | 需要重训 | **改 prompt 即可** |
| CPU p50 时延 | **1.57 ms** | 66.93 ms |

两列取自同一批 val/test 文件、同样的 224² 输入、同一条 softmax / top-k /
映射代码路径。基线一列是为这次对比在这份 split 上重算的，
它的 val top-1 与独立的 m1b 报告逐位一致。

### Hailo-8——基线已编译并在 DFC emulator 上完成 INT8 核实，没有 Hailo-8 真机

| 路径 | 状态 |
|---|---|
| 基线 EfficientNet-Lite0（m1c） → HEF | **一次编译成功，不需要任何修复。** `hailo optimize` 与 `compiler` 第一次尝试就都 exit 0——Lite0 没有 SE 分支，从架构上就不会撞上 m1b 那个需要 model-script 修复的 avgpool shift 问题。200 张 val 图上（DFC 3.31.0 / HailoRT 4.21.0 emulator）：INT8 与 CPU/native 一致率 **0.890**，对真值准确率 **0.755**（native/CPU 同批图是 0.795）——掉 4 个百分点，不是塌缩。与 CPU 余弦相似度 mean 0.948、min 0.441。**这些数字全部来自编译机（wsl2-local）上的 x86 emulator，没有用过 Hailo-8 PCIe 卡。** `evaluation/runs/2026-09-06-m1c-hef` |
| 基线 MobileNetV3-Small（m1b） → HEF | 编译成功，但 INT8 塌缩：emulator 一致率 0.115，对真值准确率 0.150（接近 7 类随机基线）。因此被 Lite0 取代——见上方对照表。`evaluation/runs/2026-09-06-m1b-hef` |
| SigLIP 2 视觉塔 → HEF | 不受 m1c 这轮工作影响。`hailo parser` 端到端通过，无 unsupported op。`hailo optimize`（INT8 PTQ，256 张校准图，optimization_level=1）**失败**，在 `ne_activation_mul_and_add78` 层报 `NegativeSlopeExponentNonFixable`——"Desired shift is 16.0, but op has only 8 data bits"。没有 optimized HAR，没跑 compiler，没有 HEF。 |

**「0.89 一致率」支持什么、不支持什么。** 支持：EfficientNet-Lite0 在同一条
编译链路、同一份校准集上，INT8 量化没有出现 MobileNetV3-Small 那种模式坍缩，
且 `hailo optimize` 不需要任何 SE 分支的绕过修复就能跑通。不支持：这份 HEF
能在真实 Hailo-8 上正确分类垃圾——本项目的评测链路里没有出现过 Hailo-8
硬件，板级时延、发热与精度全部未测。校准集也只有 256 张，低于 DFC 文档
通常建议的约 1024 张门槛，且是原样复用 m1b 轮次的抽样，没有为 Lite0
重新采样。

### RK3588（Radxa ROCK 5T）——真机实测，基线 INT8 现已可用

设备侧实测，真机而非 emulator。在 wsl2-local 上用 rknn-toolkit2 2.3.2 转换，
在 Radxa ROCK 5T 上跑，librknnrt **2.3.2**（软链名字写的是 2.3.0，
以库内版本为准），50 张 val 图，`core_mask=AUTO`，per-channel 量化。

| 模型 / 精度 | 时延 p50 / p95（mean） | 与 CPU golden 的一致率 | 对真值准确率 | 条件 |
|---|---|---|---|---|
| **EfficientNet-Lite0（m1c），fp16** | 7.906 ms / 8.129 ms（7.041 ms） | 1.00 | 0.78 | ONNX sha `e9f9e847…`，50 张 val 图 |
| EfficientNet-Lite0（m1c），int8 calib64+normal | 3.780 ms / 3.984 ms（3.807 ms） | 0.90 | 0.72 | 63 张校准图，`normal` 算法 |
| EfficientNet-Lite0（m1c），int8 calib64+mmse | 3.785 ms / 3.981 ms（3.808 ms） | 0.98 | 0.78 | 63 张校准图，`mmse` 算法 |
| EfficientNet-Lite0（m1c），int8 calib256+normal | 3.766 ms / 3.920 ms（3.500 ms） | 0.90 | 0.72 | 252 张校准图，`normal` 算法 |
| **EfficientNet-Lite0（m1c），int8 calib256+mmse**——推荐 | 3.803 ms / 4.003 ms（3.834 ms） | **1.00** | **0.78** | 252 张校准图，`mmse` 算法；与 fp16 一致率、准确率完全打平，**快 52%** |
| MobileNetV3-Small（m1b，已淘汰），fp16 | 4.44 ms / 6.32 ms | 0.98 | — | ONNX sha `aa181dd5…`，仅作对照 |
| MobileNetV3-Small（m1b，已淘汰），int8 | 4.70 ms / 11.04 ms | **0.22——塌缩** | — | 64 张校准图，仅作对照 |

**推荐配置：`calib256+mmse`。** 与 fp16 完全打平（一致率 1.00、准确率
0.78）的同时快 52%（RK3588 上 int8 真正吃到了 NPU 加速路径，塌缩的 m1b
int8 图从未吃到——m1b 的 int8 反而比自己的 fp16 更慢，4.70 ms 对 4.44 ms，
说明它的执行从未走进 INT8 加速通道）。四个 Lite0 INT8 变体全部落在
0.90–1.00 一致率区间，没有一个塌缩。`mmse` 转换耗时是默认 `normal` 算法的
40–90 倍（256 张校准下 17.3 分钟对 11.5 秒）——这是一次性转换成本，不是
运行时成本。m1b 塌缩的根因见上方对照表：PTQ 独立于 RK 编译器造成了全网退化，
训练 recipe 里对 BatchNorm 的 weight-decay 缺陷是一个疑似但未证实的助因。
`evaluation/runs/2026-09-06-m1c-rk3588-radxa`、
`evaluation/runs/2026-09-06-rk3588-radxa`（m1b 对照）

同一台设备上的 SigLIP 2 视觉塔，不受本轮 m1c 工作影响：

| 模型 / 精度 | 时延 p50 / p95 | 与 CPU golden 的一致率 | 条件 |
|---|---|---|---|
| SigLIP 2 视觉塔，**fp16** | 169.4 ms / 170.5 ms | embedding 余弦均值 **0.999617**，最小 0.998841 | ONNX sha `6f664af0…`，.rknn 191 MB |

注意 m1b 对照行的条件：这一轮用的 MobileNetV3 ONNX 是 sha256 `aa181dd5…`，
不是上面所有 m1b 精度数字所指的文件（`51c7c0ed…`）。这个 parity 结果说的是
运行时，不是精度，两者不能拼成一个精度结论。

### RK3576（EmbedFire LubanCat-3）——真机实测，只有 m1b，未用 m1c 复测

| 模型 / 精度 | 时延 p50 / p95 | 与 CPU golden 的一致率 | 条件 |
|---|---|---|---|
| MobileNetV3-Small（m1b），**fp16** | 9.49 ms / 12.49 ms | top-1 **98%**（49/50） | `evaluation/runs/2026-09-06-rk3576-cat` |
| MobileNetV3-Small（m1b），**int8** | 4.62 ms / 6.68 ms | top-1 **10%**（5/50）——**不可用，比随机猜还差** | train 的 64 张校准图 |
| SigLIP 2 视觉塔，**fp16** | 152.51 ms / 176.59 ms | embedding 余弦均值 **0.99965**，最小 0.99900 | 同一轮 |

**EfficientNet-Lite0（m1c）从未在 RK3576 上转换或跑过。** 这台设备上只有
上面的 m1b 数字；不要假设 RK3588 的 INT8 结果能直接搬过来——RK3576 与
RK3588 是不同代 NPU，同一份 MobileNetV3-Small 图在两者上的 INT8 表现本身
就不同（一致率 10% 对 22%），未测的情况下往哪个方向猜都是猜测。

### 平台支持

| 平台 | 状态 |
|---|---|
| Jetson Orin（TensorRT） | 部署包已发，基线换成 EfficientNet-Lite0 ONNX；从未在任何 Jetson 上构建过 engine |
| Raspberry Pi 5 + Hailo-8 | 部署包已发；基线 HEF 已编译并在 DFC emulator 上完成 INT8 核实（一致率 0.89）——**没有 Hailo-8 真机跑过它**。SigLIP2 视觉塔 INT8 量化仍失败 |
| RK3588 | **真机推理 parity 已验证，fp16 与 INT8 均有（基线，m1c）；部署包待补**——没有 compose、没有镜像、没有 preset。转换与运行时是通的，打包不存在 |
| RK3576 | 真机推理 parity 已验证，fp16 与 INT8——**只有 m1b（MobileNetV3-Small），未用当前 m1c 基线复测**；部署包待补 |
| CPU（onnxruntime） | 本页所有精度数字 |

### 会改变对外表述的 caveat

- **`textile` 零训练样本、零评测样本。** 两个来源数据集都没有布料类目——
  GC3 v2 导出包里没有这个标签，与广为转述的二手描述相反。第八维 logit 仍在，
  ONNX 输出仍是 `1×8`，因为输出形状是契约的一部分，但它从未被训练或测试过。
  所有表格对这一类报 `n/a` 而不是 0。模型一次都没有预测过它。
- **`hazardous`（有害垃圾）没有任何物料类映射到它。** 它留在枚举里是为了
  schema 稳定，本轮构建永远不会发出这一档。
- **GC3 复用了 TrashNet 的原图，去重把它抓出来了。** 分组按来源批次 + 原图 +
  感知哈希（dhash 8×8，Hamming ≤ 3）并查集合成连通分量；430 次近重复合并，
  **其中 183 次跨两个数据集**——GC3 把相当一批 TrashNet 的照片重新标成了
  检测框。组整体同进同出，切分末尾断言任何组、任何相同 dhash 都不得跨集合。
  没有这一步，上面的数字就是泄漏而不是精度。
- **域偏移没有测。** 两个数据集都是单件物品的照片：TrashNet 是白色海报板背景、
  日光或室内光，GC3 是检测数据集、物体不居中且常有遮挡。哪一个都不是真实的
  垃圾桶——评测里没有湿的、压扁的、堆叠的、逆光的或部分装袋的垃圾。
  **没有采集过现场集，因此没有「真实桶里掉多少精度」的数字。** 预期会掉，
  掉多少未知。
- **`organic` 在数据里占绝对多数。** 训练集 48.9%、val 47.1%，因为 GC3 的
  `BIODEGRADABLE` 一个类就占了 74090 个原始框里的 45407 个。它的召回
  （0.9791）远高于其余任何类别（0.70–0.88），混淆矩阵显示模型把不确定的
  样本往它那边推。
- **`residual` 在 val 里只有 20 张。** 这一类的 precision 数字不该单独引用——
  开放词汇 track 在这一格的 0.2754 既是模型的问题，也同样是样本量的问题。

### 部署占用

| 项 | 大小 |
|---|---|
| 基线 ONNX（`efficientnet_lite0_waste8.onnx`，m1c，当前） | 13,477,056 B |
| 基线 ONNX（`mobilenetv3s_waste8.onnx`，m1b，已淘汰） | 6,118,606 B |
| SigLIP 2 视觉塔 ONNX（`siglip2_vision_224.onnx`） | 371,695,898 B |
| 原型库 + 校准报告 | 合计约 155 KB |

## 分类器选型：基线 vs 开放词汇

两条 track 都是真的，两条都发。选择不是「旧的 vs 新的」。

**这次对比之后基线模型换了：现在是 EfficientNet-Lite0（m1c），不是
MobileNetV3-Small（m1b）。** 下面的对比是针对旧基线测的，数字本身没变——
Lite0 在这份 split 上比 MobileNetV3-Small 略准（val 0.8877 对 0.8792），
所以「基线 vs 开放词汇」的精度差距没有缩小；但下面表格里「基线」列的具体
数字（0.8792/0.8501 等）指的是 MobileNetV3-Small，不是今天实际出货的模型。
40 倍时延差距也是 CPU-only 的旧数字——除数是 MobileNetV3-Small 的 CPU
时延（p50 1.57 ms），Lite0 自己的 CPU p50 是 14.7 ms（见上方基线表），
把倍数收窄到约 4–5 倍。换基线之后，两条 track 都没有针对 SigLIP2 重新测过。

**在这套分类法上基线更准。** 同 split、同批图：val 0.8792 对 0.8501，
test 0.8807 对 0.8620——闭集头在 val 上领先约 3 个百分点、test 上约 2 个。
这正是开放词汇 track 不赢的那个指标。

**开放词汇赢的是闭集结构上做不到的那些事：**

- **校准。** val 上 ECE 0.0221 对 0.0308，test 上 0.0250 对 0.0345。
  它的置信度更有意义，而当一个阈值决定翻盖动不动时，这件事有具体后果。
- **开放集拒识。** 「这件东西不在我的词表里」的 AUROC 0.7538。
  闭集头根本给不出这个数字——从固定 softmax 头里拿掉一类就得重训。
- **跨语言回答。** 同一份视觉嵌入下，中英 prompt 在物料八类上一致率 0.8698，
  映射到四分类后 0.9143。基线没有文本侧。
- **不重训就加类。** 新类别是改 prompt 加重建原型，不是一次训练——
  这正是对 `textile` 没有数据这个问题的直接回答。

**对旧基线代价是 40 倍时延**（同一台 M4 CPU 上 p50 66.93 ms 对 1.57 ms），
**对当前基线约 4–5 倍**（66.93 ms 对 Lite0 自己的 CPU p50 约 14.7 ms）。
这不是实现差距——ViT-B/16 在 224² 上约 17.6 GFLOPs，MobileNetV3-Small 是
0.06 GFLOPs 量级（Lite0 的 FLOPs 比 MobileNetV3-Small 高，但没有单独测过）。
**开放词汇在 CPU 上不构成实时方案。** 它的落点是
(a) 有 NPU / GPU 的形态，或 (b) 当教师蒸馏出小模型。

校准过程还有两条结论，直接决定这条 track 怎么部署：

- **走层级路径，不要直接预测四分类。** 英文八类预测再映射到四分类得
  0.9393；中文 prompt 直接预测四分类只有 0.8478。「可回收物」不是一个视觉
  概念，「玻璃瓶」是。
- **`residual` 是开放词汇设置里最弱的一环。** 它的留一 AUROC 0.5795，
  接近随机：把「其他垃圾」从词表里拿掉，总有某个材质词能以高置信度接住那些
  东西。它是一个兜底定义，不是视觉概念。

## 输出接口

| 接口 | 位置 | 内容 |
|---|---|---|
| MQTT `waste/<stream-id>/results` | 端口 1883 | 一次分类一条 JSON：物料类别、中国四分类、置信度、top3、触发来源、图片引用、模型名与 ONNX sha256、分类法版本 |
| MQTT `waste/<stream-id>/fallback` | 端口 1883 | 可选的 `waste_fallback` 事件——VLM 对模糊物品的第二意见，按 frame_id 对齐。不改变主事件。 |
| HTTP `/trigger` | 端口 8080 | POST 触发一次拍照分类 |
| HTTP `/preview.mjpg`、`/healthz`、`/events` | 端口 8080 | 实时画面、计数与推理耗时、最近结果与它们的 top3 |
| GPIO 回调 | 进程内 | 带四分类结果的异步回调。不绑引脚——那是集成工作。 |

图片永远不进 payload。`image_ref.kind` 取值 `none` / `local` /
`object_store`；payload 里出现 base64 图像字节属于违反契约，发布前会被拒。

### `waste_fallback` 旁路

默认关闭。启用后，触发任一闸门的物品——top-1 低于
`vlm.trigger.min_confidence`，或 top-1 减 top-2 低于 `vlm.trigger.margin`——
会被送到外部 VLM 服务，它的回答作为一条独立事件发到 fallback 主题上。
**它永远不回填主事件。**

| 字段 | 内容 |
|---|---|
| `type` | 恒为 `waste_fallback` |
| `frame_id` | 与同一帧的 `waste_sorting_result` 事件对齐 |
| `trigger` | `low_confidence` 或 `ambiguous`。两条同时成立时报更强的那条（`low_confidence`）。 |
| `category` | VLM 给的类别，形状与主事件的 category 相同——一套解析器服务两条流 |
| `confidence` | VLM 自己的置信度。不能与分类器的 softmax 置信度比较。 |
| `rationale` | 一行理由。不做解析。 |
| `explanation` | 较长文本，只在 `vlm.explain_on_fallback` 打开时才有——每次兜底多一个调用 |
| `primary_confidence`、`primary_top3` | 分类器的原判，逐字复制，消费者据此能看到是什么触发了闸门 |
| `vlm_model`、`vlm_latency_ms`、`prompt_sha256` | 哪个模型、生成用了多久、哪份 prompt 模板产出的答案 |

**验证过的是接线，不是结果。** 这条路径对着真实的 edge-vision-vlm 应用端到端
跑过，只把生成后端换成 stub：5 帧、5 条通过契约校验的主事件、2 条兜底事件、
0 条被拒。请求校验、taxonomy 匹配与响应字段都是服务方的真代码，生成文本不是，
那一轮的 `vlm_latency_ms` 12.5 ms 是写死的常数。**真实模型的时延，以及 VLM 在
触发这些闸门的物品上是不是真的更常判对，待在 Orin 上用真服务验证。**
把兜底流当作可以记录的第二意见，不要当作可以照做的更正。

## 部署方式对比

**摄像头 + reComputer J（Orin）**——唯一有模型文件的套餐。TensorRT engine
在部署过程中于设备上构建，因为 engine 绑定具体 GPU 架构与 TensorRT 版本，
无法预编分发。它也是唯一提供开放词汇 track 的套餐：SigLIP 2 视觉塔在 CPU 上
单图 67 ms，要能用就得有加速器，而 Orin 是本包手上的加速器。
目前它上面什么都还没实测过。

**摄像头 + Raspberry Pi 5（Hailo-8）**——把板子准备好、验证三道 Hailo ABI
关卡，下载已编译并在 DFC emulator 上完成 INT8 核实（一致率 0.89）的
EfficientNet-Lite0 HEF。**没有 Hailo-8 真机跑过这份 HEF**——板级精度与
时延未测。选它是为了第一次在真实 Hailo-8 硅片上跑起一个真分类器；把
第一次上板结果当作真正的验证，而不是本页这个 emulator 数字。

## 使用须知

- **一图一件。** 没有检测器。一帧里两件物品只会得到一个答案，
  且它描述的是哪一件未定义。
- **相机与投放区就是全部输入。** 取景让物品在画面里过小会拉低分类效果，
  上面所有数字都不是在这种取景下测的。
- **连续模式下要连续三帧 top-1 相同才发布**，且该模式限速。
  触发模式没有这层平滑——一次拍摄就是一个答案。
- **随包的 MQTT broker 允许匿名连接。** 那是给本地调试用的。
  离开工作台的部署需要换成带凭据的 broker。
- **GPIO 回调默认没接任何东西。** `actuator.enabled` 默认 false；
  不提供绑定代码就打开它不会有任何变化。
- **`vlm.apply_fallback_to_gpio` 保持 false。** 翻盖不能去等一个 P50
  以秒计的调用。

## 许可说明

上游仓库的代码是 Apache-2.0。SigLIP 2 checkpoint
（`google/siglip2-base-patch16-224`，revision `75de2d55…`）是 Apache-2.0。

两个训练数据集都允许署名后再分发与二次创作，因此由它们得到的数字与模型
可以对外使用：

- **TrashNet——MIT License, Copyright (c) 2017 Gary Thung。** 经两处一手来源
  核实：仓库自身在 commit `6fa2b87` 上的 `LICENSE` 文件，以及官方 HuggingFace
  数据集卡片的 `license` 字段。注意上游项目自己的 SPEC 与调研报告都把它记成
  CC BY 4.0，那是错的，没有任何一手来源标 CC BY 4.0。
- **Garbage Classification 3 — Material Identification（Roboflow Universe）——
  CC BY 4.0**，导出包自带的 `README.dataset.txt` 里逐字写明。

对外物料使用的署名字符串：

```
TrashNet — Gary Thung and Mindy Yang, https://github.com/garythung/trashnet,
MIT License, Copyright (c) 2017 Gary Thung.
Garbage Classification 3 — Material Identification / Roboflow Universe,
https://universe.roboflow.com/material-identification/garbage-classification-3,
licensed CC BY 4.0.
```

本包不提交任何数据集派生的图像。`assets/models/` 只放校验和；
见 `gallery/ATTRIBUTION.md`。
