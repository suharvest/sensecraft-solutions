# 投放点垃圾分类

触发拍一张，拿回这件东西是什么材质、该进中国生活垃圾四分类里的哪一档，
通过 MQTT 一条消息发出去。

**基线分类器是 EfficientNet-Lite0（m1c），不是 MobileNetV3-Small。**
原基线（MobileNetV3-Small，"m1b"）在三条实测过的边缘链路上（Hailo 编译器自带的模拟器、
RK3576、RK3588）都出现 INT8 量化塌缩；EfficientNet-Lite0 不塌缩，现已成为
出货基线。下面大多数精度数字仍来自 Apple M4 CPU 上的 onnxruntime，但 Hailo-8
与 RK3588 两节带有真实 INT8 数字，两者都来自真机：RK3588 数字来自 RK3588
开发板，Hailo-8 数字来自台架单元 + Hailo-8 M.2 模块。
目前也没有任何套餐声明 硬件验证标记。

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

两个公开数据集上的工程基准，**不是合规或监管用的分类结果**。四分类映射是本项目维护的
一张表，不是主管部门的认定结果，各城市口径本就有差异。

| 投放点能得到什么 | 典型值 | 设备 |
|---|---|---|
| 物品进画面到出投放答案 | 每次触发 **4.122 ms** | reComputer J40 系列（J4012，Orin NX） |
| 四分类 top-1 | **0.9500** | 同一模型，各加速器一致 |
| 物料 top-1（8 类） | **0.8877** | 同上 |

**两个 top-1 要一起报**：四分类比物料高，是因为玻璃、金属、塑料之间的混淆被吸收掉了——
三者都映射到可回收物——所以只报四分类会高估模型对材质的判别力。

精度是模型属性，换加速器仍然成立：Hailo-8 构建在全量 7417 张验证集上物料 top-1 为
0.8889。

### 平台支持

- **Jetson Orin（TensorRT）**——已在 reComputer J40 系列（Orin NX）上完成部署。
- **reComputer R2000（Hailo-8）**——已有部署包；基线 HEF 已在真实 Hailo-8 上
  跑完全量验证集。
- **RK3588**——fp16 与 INT8 都能在真机上跑，但**没有部署包**：转换与运行时都跑通了，
  缺的是打包。
- **RK3576**——真机上跑过，但只覆盖已淘汰的骨干；没有部署包。

### 这些数字覆盖的范围

- **两个数据集都是单件物品的照片**：一个拍在纯色板上，一个是目标偏心、常被遮挡的检测集。
  两者都不是真实的垃圾桶——潮湿、压扁、堆叠、逆光与部分装袋的垃圾都在评测之外，所以
  **真实投放点上的精度会低于上面这些数字**，上线前应在自己现场的图像上复测一次。
- **`textile` 在两个数据集里都没有样本**，模型不会输出它，所有表在这一类上报的是 `n/a`
  而不是 0。
- **`hazardous`（有害垃圾）没有任何物料类别映射过去**，本包出货的模型也不会发出它。
- **`organic` 在数据里占比过高**，训练集与验证集都在 48% 上下，混淆矩阵显示模型会把
  拿不准的物品推向这一类。
- 两个数据集共用了部分原始照片；按来源批次、原始图像与感知哈希分组后合并了 430 组近重复，
  其中 183 组跨数据集，分组在切分时整组移动。

## 分类器选型：基线 vs 开放词汇

两条 track 都是真的，两条都发。选择不是「旧的 vs 新的」。

**这次对比之后基线模型换了：现在是 EfficientNet-Lite0（m1c），不是
MobileNetV3-Small（m1b）。** 下面的对比是针对旧基线测的，数字本身没变——
Lite0 在这份 split 上比 MobileNetV3-Small 略准（val 0.8877 对 0.8792），
所以「基线 vs 开放词汇」的精度差距没有缩小；但下面表格里「基线」列的具体
数字（0.8792/0.8501 等）指的是 MobileNetV3-Small，不是今天实际出货的模型。
40 倍时延差距也是 CPU-only 的旧数字——除数是 MobileNetV3-Small 的 CPU
时延（p50 1.57 ms），Lite0 自己的 CPU p50 是 14.7 ms，
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
0.06 GFLOPs 量级（Lite0 介于两者之间）。
**开放词汇在 CPU 上不构成实时方案。** 它的落点是
(a) 有 NPU / GPU 的形态，或 (b) 当教师蒸馏出小模型。

校准过程还有两条结论，直接决定这条 track 怎么部署：

- **走层级路径，不要直接预测四分类。** 英文八类预测再映射到四分类得
  0.9393；中文 prompt 直接预测四分类只有 0.8478。「可回收物」不是一个视觉
  概念，「玻璃瓶」是。
- **`residual` 的留一 AUROC 是 0.5795，接近随机。** 把「其他垃圾」从词表里
  拿掉，总有某个材质词能以高置信度接住那些东西。它是一个兜底定义，
  不是视觉概念。

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

**摄像头 + reComputer J30 / J40（Orin）**——唯一有模型文件的套餐。TensorRT engine
在部署过程中于设备上构建，因为 engine 绑定具体 GPU 架构与 TensorRT 版本，
无法预编分发。它也是唯一提供开放词汇 track 的套餐：SigLIP 2 视觉塔在 CPU 上
单图 67 ms，要能用就得有加速器，而 Orin 是本包手上的加速器。已在
reComputer J40 系列（Orin NX）上实测：基线 engine 构建 68 秒，部署容器端到端
pipeline 4.122 ms / inference 3.533 ms（每次触发）——部署状态见上方"平台支持"表。

**摄像头 + reComputer R2000 系列（Hailo-8）**——把板子准备好、验证三道 Hailo
ABI 关卡，下载 EfficientNet-Lite0 HEF。出货的这枚 HEF 已在 Hailo-8 真机上跑完
val 全集 7417 张（物料 top-1 0.8889、中国四分类 0.9507、与 fp32 CPU 一致率
0.9581、p50 3.166 ms）。部署容器本身也在同一台真机上单独做过验证：一次
`/healthz`、`/trigger` 与 MQTT 触发拿到的分类结果与该图的真值一致；另外用
`infer_shard.py` 直接对同一份 val 集的 1060 张子集跑了一遍——用的是同一枚
HEF，但不经过部署容器的 HTTP/MQTT 路径——测得一致率 0.9425、对真值准确率
0.8453、p50 3.167 ms，与上面的全集数字量级一致。
`evaluation/runs/2026-09-08-harvest-pi-acceptance`

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
