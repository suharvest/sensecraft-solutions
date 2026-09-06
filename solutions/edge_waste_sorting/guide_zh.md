## 套餐: 摄像头 + reComputer J（Orin） {#orin}

唯一有模型文件的套餐。TensorRT engine 在部署过程中于设备上构建，因为 engine
绑定具体 GPU 架构与 TensorRT 版本，无法预编分发。它也是唯一提供开放词汇 track
与 VLM 兜底的套餐，两者都是可选项，都在基线跑起来之后再加。

| 设备 | 用途 |
|---|---|
| reComputer J40 / J30（Jetson Orin） | 用 TensorRT 运行分类器，提供网页与触发端点，发布 MQTT |
| USB 或 IP 摄像头 | 俯视投放区——一次拍一件 |
| 实体按钮（可选） | 一个触发源；接线与 GPIO 读取是本包之外的集成工作 |
| 继电器、翻盖或指示灯（可选） | 由 actuator 回调驱动，回调带四分类结果、不绑引脚 |

**重要提示。** 这不是合规或监管用的分类系统。中国四分类映射是本项目维护的
一张表，不是主管部门的认定结果，各城市口径本来就有差异。这里的任何输出都不应
作为收费、处罚或合规判定的唯一依据。

已知弱点，全部要么实测过、要么明确标为未测：

- **一图一件。** 没有检测器。一帧里两件物品只得到一个答案，
  且它描述哪一件是未定义的。
- **`textile` 从未被训练或测试过。** 两个数据集都没有布料类目。
  模型一次都没有预测过它。
- **`hazardous`（有害垃圾）永远不会发出。** 没有物料类映射到它。
- **域偏移未测。** 两个数据集都是单件干净物品的照片，不是真实垃圾桶。
  没有现场集，因此没有「湿的、压扁的、堆叠的、装袋的垃圾上掉多少精度」的数字。
  预期会掉。
- **本页没有任何内容在硬件上跑过。** 每一个数字都来自 Apple M4 CPU 上的
  onnxruntime。

## 步骤 1: 部署垃圾分类 {#deploy_jetson_waste type=docker_deploy required=true config=devices/jetson_waste.yaml}

上传 compose 栈、下载 ONNX、在设备上构建 TensorRT engine、写入视频源与触发
配置，然后连同本地 MQTT broker 一起启动分类器。

### 前置条件

- 一台跑 JetPack 6.x、已配好 NVIDIA container runtime 的 Jetson Orin。
  该步骤在动手之前会先检查 `/etc/nv_tegra_release`、`trtexec` 与主机的
  `tensorrt` python 包。
- 至少 10 GB 可用空间。基线 ONNX 6 MB；开放词汇视觉塔 372 MB，
  它的 engine 还更大。
- 设备能访问到相机。用 USB 相机时还要在
  `assets/jetson/docker-compose.yml` 里把对应的 `/dev/videoN` 那行取消注释——
  否则容器里看不到视频节点。不要整个挂载 `/dev`；runc 无法重建 `/dev/pts` 的
  inode。
- **模型文件不在任何 CDN 上。** 步骤里的下载地址只是目标位置，
  什么都还没上传。请事先把 `efficientnet_lite0_waste8.onnx` 拷到设备的
  `~/edge-waste-sorting/jetson_waste/models/`；无论走哪条路，
  sha256 校验（`e9f9e847de6899ad4341d8f6084823e7c70307e84ac4d0da4bc4911b5b767391`）
  都照做。这是当前基线（EfficientNet-Lite0，m1c）——MobileNetV3-Small
  （m1b）已被取代，因为它在每一条测过的边缘链路上都出现 INT8 塌缩，
  详见方案页。
- **容器镜像尚未 push。** 在设备上从上游仓库构建，然后要么把它 retag 成
  compose 文件里的名字，要么把 `WASTE_IMAGE` 设成你的本地 tag。

分类器 track 在这里选。`baseline` 是默认项，除非你已经读过方案页的
「分类器选型」一节，否则它就是正确选择：EfficientNet-Lite0 在这套分类法上
top-1 比开放词汇 track 更高（同一份 val 上 0.8877 对 0.8501），CPU 上大约
快 4-5 倍（目前还没有它在 Jetson TensorRT 上的实测数字）。`open_vocab` 用
top-1 换来更好的校准、开放集拒识、中英文都能回答，以及不重训就能加类。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `This target is not a NVIDIA Jetson` | 主机上没有 `/etc/nv_tegra_release`。你部署到了错误的机器上。 |
| `trtexec not found` | 装 TensorRT dev 包——JetPack 上是 `sudo apt install tensorrt`。 |
| `WARNING: nvidia runtime missing` | 执行 `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`，然后重新部署。 |
| Engine 构建报 `Static model does not take explicit shapes` | 有人加了 `--minShapes`/`--optShapes`/`--maxShapes`。两个 ONNX 都是静态 batch-1 导出，去掉这些参数。 |
| ONNX 的 sha256 对不上 | 你拿到的是另一个文件。不要继续——engine、事件里的 `onnx_sha256` 与方案页上每一个数字，指的都是那份有校验和的文件。 |
| 找不到 `docker compose` | 该步骤会安装或建链接。仍然失败就手工装 `docker-compose-plugin`。 |
| Compose 解析 `._docker-compose.yml` 失败 | AppleDouble 附属文件从 Mac 带过来了。该步骤会删掉它们；手工上传的话，自己跑一遍同样的 `find … -name '._*' -delete`。 |
| 容器起来了但没有相机 | compose 文件里的 `/dev/videoN` 那行还注释着。 |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_waste.yaml default=true}

从本机通过 SSH 部署到 Orin。这是常规路径：填设备 IP、SSH 凭据、相机地址与 track。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson Orin" config=devices/jetson_waste.yaml}

直接在 Orin 上运行部署，适用于你已经在设备上作业、不想再绕一层 SSH 的情况。

## 步骤 2: 查看实时分类画面 {#preview_orin_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

打开运行时自带的页面：实时画面、一个触发按钮、最近若干次分类及其 top3 与
四分类，还有健康接口。在验证步骤之前用它把相机对好。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 页面打不开 | 在设备上 `docker ps`——`waste` 容器应当在跑。看 `docker logs edge-waste-app`。 |
| 页面能开但预览是黑的 | 视频源写错或不可达。USB 相机检查 `/dev/videoN` 有没有挂进容器；RTSP 先用 VLC 测地址。 |
| 预览正常但 `/events` 一直空 | 还没有任何触发。`on_demand` 模式下运行时只在触发时分类——这是设计，不是故障。 |
| 物品在画面里很小 | 重新对准。方案页上没有任何数字是在物品很小的取景下测的。 |

## 步骤 3: 接好触发并确认一次分类 {#trigger_setup_orin type=manual required=true verify=true config=devices/trigger_setup.yaml}

端到端验证：把一件物品放到相机下、触发一次，看着恰好一条符合契约的事件到达
MQTT。

### 前置条件

- 步骤 1 已完成且容器在跑。
- 同网络的某台机器上有 `mosquitto_sub`，或者直接用 broker 容器：
  `docker exec edge-waste-mosquitto mosquitto_sub …`。
- 一件属于有训练数据的类别的物品——除了 textile 都行。

### 部署完成

栈已经在跑，并且端到端验证过一次分类。

#### 快速验证

1. 打开 `http://<设备IP>:8080/`，确认实时画面里是投放区，
   单件物品在画面里占到有意义的比例。
2. 订阅：`mosquitto_sub -h <设备IP> -t '<设备名>/waste/+/results' -v`。
3. 触发一次：`curl -X POST http://<设备IP>:8080/trigger`。
4. 确认恰好到达一条消息，且 `category` 与 `top3[0]` 一致、
   `confidence` 与 `top3[0].confidence` 一致。运行时会拒掉不一致的 payload，
   所以能看到这条消息本身就说明两条都成立。
5. 确认 `image_ref` 里是路径或 URI，没有图片字节。
6. 在 800 ms 内触发两次，确认仍然只收到一条消息——
   那是去抖把第二次合并进了正在处理的请求。

#### MQTT 消息

```json
{
  "type": "waste_sorting_result",
  "version": "1.0.0",
  "taxonomy_version": "material8/china4-v1",
  "device": "orin-nx",
  "stream_id": "bin1-cam1",
  "frame_id": 4207,
  "timestamp": 1757030400123,
  "trigger": "button",
  "inference_time_ms": 3.7,
  "pipeline_ms": 42.5,
  "category": {
    "class_id": 4,
    "class_name": "plastic",
    "china_category": "recyclable",
    "china_category_zh": "可回收物"
  },
  "confidence": 0.913,
  "top3": [
    {"rank": 0, "class_id": 4, "class_name": "plastic", "confidence": 0.913, "china_category": "recyclable"},
    {"rank": 1, "class_id": 2, "class_name": "glass", "confidence": 0.052, "china_category": "recyclable"},
    {"rank": 2, "class_id": 7, "class_name": "residual", "confidence": 0.021, "china_category": "residual"}
  ],
  "image_ref": {
    "kind": "local",
    "uri": "/var/lib/edge-waste-sorting/captures/2026-09-05/bin1-cam1-4207.jpg"
  },
  "model": {
    "name": "efficientnet_lite0_waste8",
    "backbone": "efficientnet_lite0",
    "input": "images:1x3x224x224",
    "onnx_sha256": "e9f9e847de6899ad4341d8f6084823e7c70307e84ac4d0da4bc4911b5b767391",
    "accelerator": "tensorrt"
  }
}
```

`stream_id` 放在 payload 里是刻意的。从那里读它——主题模板是运行时配置，
消费者不得解析主题。

#### 下一步

- 有翻盖或指示灯就绑上 actuator 回调：设
  `"actuator": {"enabled": true, "min_confidence": 0.5}` 并提供集成代码。
  运行时不绑任何引脚。
- 离开工作台之前把 MQTT 指向带凭据的 broker。随包的 broker 允许匿名连接，
  只适合本地调试。
- 考虑下面的可选步骤：开放词汇 track 用于开放集拒识与加类，
  VLM 兜底用于给歧义物品一个第二意见。
- 采集现场集。从这两个数据集到真实垃圾桶的域偏移，
  是整个方案里最大的一项未测风险。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 一条消息都没有 | 看 `/healthz`——触发计数不动就说明触发源没配上。检查 `config/config.json` 里的 `trigger.sources`。 |
| 按一次按钮出两条消息 | 去抖时间对这个抖动的开关来说太短。调高 `trigger.debounce_ms`；低于约 300 ms 时抖动的按钮会触发两次。 |
| 类别总是 `residual` | 置信度落到了 `rules.min_confidence` 以下，所以发的是兜底类别而不是 argmax。检查光照、取景，以及这件东西是不是根本不在八类里。 |
| 玻璃与塑料上自信地判错 | 实测混淆矩阵里最大的一格就是玻璃对塑料——透明瓶子在形状与高光上高度重叠。四分类结果仍然是对的，因为两者都映射到可回收物。 |
| 什么都判成 `organic` | `organic` 占训练数据的 48.9%，模型会把不确定的样本往它那边推。改善取景与光照有帮助，真正的解法是重新平衡后重训。 |
| 布料物品被判成别的 | 属预期。`textile` 零训练样本，模型从未预测过它。 |
| 物品根本不是生活垃圾 | 基线没有办法说「不在我的词表里」。那正是下面开放词汇步骤补上的能力。 |

## 步骤 4: 切换到开放词汇分类（可选） {#enable_open_vocab_orin type=manual required=false verify=true config=devices/enable_open_vocab.yaml}

把闭集头换成对文本原型打分的 SigLIP 2 视觉塔。先读方案页的「分类器选型」一节：
这是 top-1 的下降，也是校准、开放集拒识、跨语言回答与不重训加类能力的上升。

### 前置条件

- 步骤 1 已经用 `model_track: baseline` 跑通并验证过。
  不要同时调试两处改动。
- 在已有占用之外，还要 372 MB 放视觉塔 ONNX，外加它的 engine 的空间。
- 原型库与它的 meta 文件——校验和在
  `assets/models/SHA256SUMS.open_vocab`。和 ONNX 一样，CDN 上什么都没上传；
  手工拷到设备上并用 `sha256sum -c` 校验。
- 仅限 Orin。Hailo 套餐提供不了这条：SigLIP 2 的 INT8 量化目前在
  `hailo optimize` 处失败，而且没有任何 HEF。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| Engine 构建比基线久得多 | 属预期。这个 ViT-B/16 从未在任何板卡上构建过 engine，没有参照时间。不要过早杀掉它。 |
| Engine 构建报 `Static model does not take explicit shapes` | 去掉 `--minShapes`/`--optShapes`/`--maxShapes`；导出是静态 batch-1。 |
| 时延比之前高很多 | 属预期：CPU 上 p50 66.93 ms 对 1.57 ms。如果不能接受，这条 track 就不适合你的形态——它的落点是加速器或蒸馏出的小模型。 |
| 置信度看上去整体变了 | 改 `temperature` 会改变置信度分布，也就改变了 `min_confidence` 的含义。0.0075 是标定值；改了就重调阈值。 |
| 换成中文四分类原型库之后四分类精度下降 | 走层级路径。直接预测四分类是 0.8478，八类再映射上去是 0.9393。 |
| 未知物体仍然拿到自信的材质标签 | 看留一法的数字：`residual` 的 AUROC 只有 0.5795，接近随机。开放集拒识在物料类上远好于这个兜底档。 |

## 步骤 5: 启用 VLM 低置信 / 歧义兜底（可选） {#enable_vlm_fallback_orin type=manual required=false verify=true config=devices/enable_vlm_fallback.yaml}

把分类器拿不准的物品送到外部 VLM 服务，并把它的回答作为一条独立的
`waste_fallback` 事件发出去。这是 additive 的：它不进分类路径、不改变主事件的
category，方案页上的每一个数字在它关闭时都成立。

### 前置条件

- 一个可达的 `edge-vision-vlm` 实例。本方案不打包也不启动这个服务——
  通常它跑在另一台 Orin 主机上。
- 步骤 3 已验证通过，这样加第二条流之前你知道主流是健康的。
- `vlm.trigger.min_confidence` 不得低于 `rules.min_confidence`；
  兜底门限低于改判门限会被配置校验拒掉。
- 清楚哪些验证过、哪些没有：接线是对着真实服务、生成后端换成 stub 验证的
  （5 帧、5 条有效主事件、2 条兜底事件、0 条被拒）。
  真实模型的时延，以及 VLM 是不是真的更常判对，待在 Orin 上验证。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 从来收不到兜底事件 | 看 `/healthz` 里的 VLM 计数。静默降级是设计如此——VLM 慢、不可达或熔断打开时不发事件，也不打扰主流。 |
| 运行时报 HTTP 502 而不是连接错误 | 透明代理接管了这个地址，连 `127.0.0.1` 也一样。设 `no_proxy=127.0.0.1,localhost,<vlm主机>`，或者干脆不给容器任何代理变量。httpx 认 `HTTP_PROXY`，而代理返回的 502 会与真正的后端错误记成同一类——行为一样，归因误导。 |
| `ambiguous` 闸门从不触发 | 看可达区间：softmax 下门限为 `g` 时，被接受一侧的差至少是 `2g−1`。`g=0.6` 时 margin 小于 0.2 永远不会触发。 |
| 两条闸门都成立却只报 `low_confidence` | 设计如此——报更强的那条理由。 |
| VLM 给的类别与分类器不同 | 属预期，而且它不回填主事件。两个都记下来复盘；兜底目前的证据还不足以支持自动照做。 |
| 启用 VLM 之后翻盖反应变慢 | `vlm.apply_fallback_to_gpio` 必须保持 false。翻盖不能去等一个 P50 以秒计的调用。 |

## 套餐: 摄像头 + Raspberry Pi 5（Hailo-8） {#pi_hailo}

把一台装了 Hailo-8 的 Pi 5 准备好、验证三道只能在设备上检查的 ABI 关卡，
然后下载 EfficientNet-Lite0（m1c）的 HEF。该 HEF 编译顺利，并在 DFC
emulator 上完成了 INT8 核实（与 CPU/native 在 200 张 val 图上一致率
0.89）——**目前还没有 Hailo-8 真机跑过它**。选这个套餐是为了拿到这个分类器
第一次真机上板的结果；把 emulator 数字当作编译期健全性检查，不是硬件验证。

| 设备 | 用途 |
|---|---|
| Raspberry Pi 5 + Hailo-8（PCIe M.2） | 本应在 NPU 上运行分类器——HEF 还不存在 |
| USB 或 IP 摄像头 | 俯视投放区——一次拍一件 |
| 实体按钮（可选） | 一个触发源；接线与 GPIO 读取是本包之外的集成工作 |
| 继电器、翻盖或指示灯（可选） | 由 actuator 回调驱动，回调带四分类结果、不绑引脚 |

**重要提示。** 这不是合规或监管用的分类系统。中国四分类映射是本项目维护的
一张表，不是主管部门的认定结果，各城市口径本来就有差异。这里的任何输出都不应
作为收费、处罚或合规判定的唯一依据。

已知弱点，全部要么实测过、要么明确标为未测：

- **HEF 只在 emulator 上验证过，不是硬件验证。** 基线（EfficientNet-Lite0，
  m1c）在 DFC emulator 上编译顺利、没有 INT8 塌缩（一致率 0.89），但没有
  Hailo-8 真机跑过它。开放词汇视觉塔的 INT8 量化仍然在 `hailo optimize`
  处失败。如果你自己训练并量化 MobileNetV3-Small，不要假设它的 INT8 也能像
  这个基线一样跑通——它在同一条编译链路上塌缩过（详见方案页）。
- **一图一件。** 没有检测器。
- **`textile` 从未被训练或测试过**，`hazardous` 永远不会发出。
- **域偏移未测**，而且方案页上所有 CPU 精度数字都是 FP32——
  真实 Hailo-8 硬件上的 INT8 置信度分布还没有测过。
- **这里没有任何东西在树莓派上跑过。**

## 步骤 1: 在 Hailo 上部署垃圾分类 {#deploy_hailo_waste type=docker_deploy required=true config=devices/hailo_waste.yaml}

上传 compose 栈、检查三道 Hailo ABI 关卡，然后下载并校验 EfficientNet-Lite0
的 HEF。

### 前置条件

- 装了 Docker 的 Raspberry Pi OS、PCIe M.2 槽里的 Hailo-8，
  以及存在的 `/dev/hailo0`。
- 已安装 HailoRT 4.21.x，且 `hailort` 与 `hailort-pcie-driver` 两个包
  在 apt 里都被 hold。只 hold 驱动会让 apt 在 HEF 脚下悄悄升级用户态库。
- `/etc/modprobe.d/` 里有 `options hailo_pci force_desc_page_size=4096`，
  然后重启过。Pi 5 内核 PAGE_SIZE 是 16 KB，Hailo-8 的最大描述符页是 4 KB；
  没有这条时 `VDevice()` 与 `hailortcli fw-control identify` 都会成功，
  故障只在 `configure(hef)` 时才暴露。
- 至少 4 GB 可用空间。
- **容器镜像尚未 push。** 在设备上从上游仓库构建，然后要么把它 retag 成
  compose 文件里的名字，要么把 `WASTE_IMAGE` 设成你的本地 tag。
- **HEF 还没上传到任何 CDN。** 步骤里的下载地址只是目标位置；上传落地前
  请手工把 `efficientnet_lite0_waste8.hef` 拷到设备上。sha256 校验
  （`3d7d92e974dc0bfbab5376dda32fc746dcf7511fc6bd1351bf93d4df593f2a00`）
  无论走哪条路都照做。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `No /dev/hailo0` | 卡没插好，或者 `hailo_pci` 没加载。`lspci \| grep -i hailo` 与 `dmesg \| grep -i hailo`。 |
| `libhailort.so.4.21.0 not found` | 本部署 ABI 锁在 HailoRT 4.21。装这个版本；驱动、库与 python 绑定不要混版本。 |
| `expected both hailort and hailort-pcie-driver on hold` | `sudo apt-mark hold hailort hailort-pcie-driver`。 |
| `hailo_pci is missing force_desc_page_size=4096` | `echo 'options hailo_pci force_desc_page_size=4096' \| sudo tee /etc/modprobe.d/hailo.conf && sudo reboot`。 |
| `No HEF for this solution` | CDN 上传还没落地。按步骤里给出的路径手工把 HEF 拷到设备上，校验上面的 sha256，再重跑这一步。 |
| `_pyhailort` 导入报错 | 主机的绑定被挂进容器，只能在同一个 Python 小版本下导入。Bookworm 是 3.11，trixie 是 3.13。 |
| 自己训的 MobileNetV3-Small 在 Hailo 上 INT8 表现很差 | 属预期——不要直接量化它。MobileNetV3-Small（m1b）在同一条编译链路上塌缩到接近随机水平（与 CPU/native 一致率 0.115）。EfficientNet-Lite0 正因为这个原因成为基线。 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="Raspberry Pi 5" config=devices/hailo_waste.yaml default=true}

从本机通过 SSH 部署到树莓派。这是常规路径。

### 部署目标 {#hailo_local type=local device=hailo device_name="Raspberry Pi 5" config=devices/hailo_waste.yaml}

直接在树莓派上运行部署，适用于你已经在设备上作业的情况。

## 步骤 2: 查看实时分类画面 {#preview_hailo_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

打开运行时自带的页面：实时画面、一个触发按钮、健康接口。如果步骤 1 没能
拿到 HEF（CDN 还没上传，也没有手工拷贝），实时画面照样能起来，但分类结果
起不来。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 页面打不开 | 在设备上 `docker ps`——`waste` 容器应当在跑。看 `docker logs edge-waste-app`。 |
| 页面能开但预览是黑的 | 视频源写错或不可达。USB 相机检查 `/dev/videoN` 有没有挂进容器；RTSP 先用 VLC 测地址。 |
| 预览正常但 `/events` 一直空 | 如果设备上没有 HEF，模型永远加载不上，所以什么都不会被分类——见步骤 1 的「No HEF for this solution」条目。 |
| 物品在画面里很小 | 重新对准。方案页上没有任何数字是在物品很小的取景下测的。 |

## 步骤 3: 接好触发并确认一次分类 {#trigger_setup_hailo type=manual required=true verify=true config=devices/trigger_setup.yaml}

端到端验证。如果步骤 1 已经把 HEF 放到了设备上，这一步会产出一次真实分类，
第一次跑在 Hailo-8 真机上——本项目自己的 emulator 数字不能替代这个结果。
如果 HEF 还缺，先把取景与订阅这两小步跑掉，除模型之外的部分就都确认过了。

### 前置条件

- 步骤 1 已尝试过，三道 ABI 关卡通过，容器在跑。
- 同网络的某台机器上有 `mosquitto_sub`，或者直接用 broker 容器：
  `docker exec edge-waste-mosquitto mosquitto_sub …`。
- 一件属于有训练数据的类别的物品——除了 textile 都行。

### 部署完成

板子已经准备好，栈也在跑。如果 HEF 已经放到设备上，分类跑在 Hailo-8 真机
上——这是本项目第一次真正验证这个数字，因为本项目自己没有 Hailo-8。
如果 HEF 还缺（CDN 上传待定），分类被它卡住；触发与 MQTT 链路仍然可以验证。

#### 快速验证

1. 打开 `http://<设备IP>:8080/`，确认实时画面里是投放区，
   单件物品在画面里占到有意义的比例。
2. 订阅：`mosquitto_sub -h <设备IP> -t '<设备名>/waste/+/results' -v`。
3. 触发一次：`curl -X POST http://<设备IP>:8080/trigger`。
4. 确认 `/healthz` 里的触发计数在动——模型跑不了时触发链路照样成立。
5. 确认没有结果事件到达，且容器日志报的是缺模型，而不是别的什么故障。
6. 把 HEF 放到设备上之后重跑这一步；从那时起检查项与 Orin 套餐相同。

#### MQTT 消息

```json
{
  "type": "waste_sorting_result",
  "version": "1.0.0",
  "taxonomy_version": "material8/china4-v1",
  "device": "pi5-hailo",
  "stream_id": "bin1-cam1",
  "frame_id": 4207,
  "timestamp": 1757030400123,
  "trigger": "button",
  "inference_time_ms": 3.7,
  "pipeline_ms": 42.5,
  "category": {
    "class_id": 4,
    "class_name": "plastic",
    "china_category": "recyclable",
    "china_category_zh": "可回收物"
  },
  "confidence": 0.913,
  "top3": [
    {"rank": 0, "class_id": 4, "class_name": "plastic", "confidence": 0.913, "china_category": "recyclable"},
    {"rank": 1, "class_id": 2, "class_name": "glass", "confidence": 0.052, "china_category": "recyclable"},
    {"rank": 2, "class_id": 7, "class_name": "residual", "confidence": 0.021, "china_category": "residual"}
  ],
  "image_ref": {
    "kind": "local",
    "uri": "/var/lib/edge-waste-sorting/captures/2026-09-05/bin1-cam1-4207.jpg"
  },
  "model": {
    "name": "efficientnet_lite0_waste8",
    "backbone": "efficientnet_lite0",
    "input": "images:1x3x224x224",
    "onnx_sha256": "e9f9e847de6899ad4341d8f6084823e7c70307e84ac4d0da4bc4911b5b767391",
    "accelerator": "hailo"
  }
}
```

payload 形状跨平台完全一致，只有 `model.accelerator` 不同。
`stream_id` 放在 payload 里是刻意的——从那里读它，不要解析主题。

#### 下一步

- 把你刚测到的真实 Hailo-8 精度与时延反馈回来——这是本项目第一次在真机上
  验证这份 HEF。拿它对照方案页上 DFC emulator 的 0.89 一致率 / 0.755
  准确率两个数字。
- 如果 CDN 上传还没落地、你是手工把 HEF 拷上去的，记下这一点——下次部署
  该下载步骤会失败。
- 保住你刚建立的 ABI 状态：两个 Hailo 包都 hold 着，
  `force_desc_page_size=4096` 保持在位。这份用 DFC 3.31.0 / HailoRT 4.21.0
  编出来的 HEF 需要的正是这一套。
- 离开工作台之前把 MQTT 指向带凭据的 broker。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 一条消息都没有 | 先确认设备上是不是真有 HEF（`ls` models 目录)——如果 CDN 上传还没落地，步骤 1 会在下载这一步失败。HEF 存在的话，去容器日志里找别的故障。 |
| 触发计数不动 | 触发源没配上。检查 `config/config.json` 里的 `trigger.sources`。 |
| 按一次按钮出两条消息 | 去抖时间对这个抖动的开关来说太短。调高 `trigger.debounce_ms`；低于约 300 ms 时抖动的按钮会触发两次。 |
| `configure(hef)` 崩溃 | `force_desc_page_size=4096` 没设，或者设完没重启。 |
| 置信度阈值的表现与 Orin 套餐不同 | 方案页上「4.3% 低于 0.5」是 CPU FP32 上的数字。这块板子的 INT8 置信度分布本来就是另一次独立测量——这是预期，不是 bug；但如果看到它坍缩到单一类别，拿它对照 emulator 的 0.89 一致率，真机上出现明显差距值得反馈。 |
| 想在这里用开放词汇或 VLM 兜底 | 这个套餐不提供。SigLIP 2 的 INT8 量化在 `hailo optimize` 处失败，而 VLM 兜底步骤仅限 Orin。 |
