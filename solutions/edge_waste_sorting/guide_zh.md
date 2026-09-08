## 套餐: 摄像头 + reComputer J30 / J40（Orin） {#orin}

唯一有模型文件的套餐。TensorRT engine 在部署过程中于设备上构建，因为 engine
绑定具体 GPU 架构与 TensorRT 版本，无法预编分发。它也是唯一提供开放词汇 track
的套餐，这是可选项，在基线跑起来之后再加。

| 设备 | 用途 |
|---|---|
| reComputer J40 / J30（Jetson Orin） | 用 TensorRT 运行分类器，提供网页与触发端点，发布 MQTT |
| USB 或 IP 摄像头 | 俯视投放区——一次拍一件 |
| 实体按钮（可选） | 一个触发源；接线与 GPIO 读取是本包之外的集成工作 |
| 继电器、翻盖或指示灯（可选） | 由 actuator 回调驱动，回调带四分类结果、不绑引脚 |

**重要提示。** 这不是合规或监管用的分类系统。中国四分类映射是本项目维护的
一张表，不是主管部门的认定结果，各城市口径本来就有差异。这里的任何输出都不应
作为收费、处罚或合规判定的唯一依据。

已知弱点：

- **一图一件。** 没有检测器。一帧里两件物品只得到一个答案，
  且它描述哪一件是未定义的。
- **`textile` 从未被训练或测试过。** 两个数据集都没有布料类目。
  模型一次都没有预测过它。
- **`hazardous`（有害垃圾）永远不会发出。** 没有物料类映射到它。
- **域偏移。** 两个数据集都是单件干净物品的照片，不是真实垃圾桶。湿的、压扁的、
  堆叠的、装袋的垃圾上精度会掉——请采一批自己现场的数据重测。
- **方案页上的 Jetson 精度/一致率数字（top-1 0.8755，与 CPU golden 一致率
  0.9991，1060 张子集）来自另一个独立构建的 engine。** 同为 FP16
  engine——同一份 ONNX、同一精度，但不是本部署步骤产出的那个二进制。
  先在 reComputer J40 系列（Orin NX）上测得，在 reComputer J30 系列
  （Orin Nano 8GB）上复测逐位一致。部署 engine 自身的构建耗时
  （68 秒）与端到端 pipeline（4.122 ms）/ inference（3.533 ms）时延——取自一条
  实测的 MQTT 事件——是在部署二进制上实测的。

## 步骤 1: 部署垃圾分类 {#deploy_jetson_waste type=docker_deploy required=true config=devices/jetson_waste.yaml}

上传 compose 栈、下载 ONNX、在设备上构建 TensorRT engine、写入视频源与触发
配置，然后连同本地 MQTT broker 一起启动分类器。首次启动需要等待 engine
构建：基线（EfficientNet-Lite0）engine 在 reComputer J40 系列（Orin NX）上耗时
68 秒。

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
| `edge-waste-mosquitto` 一直重启，报 `Address in use` | 设备上另一个项目的 broker 已用 `network_mode: host` 占住 1883（例如这台设备之前跑过 edge_inspection_surface）。把 `config/mosquitto.conf` 和 `config/config.json` 里的 `mqtt.port` 都改成空闲端口（如 18831），再 `docker compose up -d --force-recreate mosquitto`。 |

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
| 物品在画面里很小 | 重新对准。方案页数字都取自物品占满取景的画面。 |

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
- 考虑下面的可选步骤：开放词汇 track 用于开放集拒识与加类。
- 采集现场集。从这两个数据集到真实垃圾桶的域偏移，是整个方案里最大的一项风险。

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

## 套餐: 摄像头 + reComputer R2000（Hailo-8） {#pi_hailo}

把一台装了 Hailo-8 的 Pi 5（对应出货形态是 reComputer R2000 系列）准备好、
验证三道只能在设备上检查的 ABI 关卡，然后下载 EfficientNet-Lite0（m1c）的
HEF。出货的这枚 HEF 已在 Hailo-8 真机上跑完 val 全集 7417 张：物料 top-1
0.8889、中国四分类 0.9507、与 fp32 CPU 一致率 0.9581、p50 3.166 ms、
p95 3.249 ms（纯推理）。这份容器的从零部署也在同一台真机上单独做过验证：
一次 `/healthz`、`/trigger` 与 MQTT 触发拿到的分类结果与该图的真值一致；
另外用 `infer_shard.py` 直接对同一份 val 集的 1060 张子集跑了一遍——用的
是同一枚 HEF，但不经过部署容器的 HTTP/MQTT 路径——测得一致率 0.9425、
对真值准确率 0.8453、p50 3.167 ms，与全集数字量级一致。

| 设备 | 用途 |
|---|---|
| reComputer R2000 系列（Hailo-8，PCIe M.2） | 在 NPU 上运行分类器 |
| USB 或 IP 摄像头 | 俯视投放区——一次拍一件 |
| 实体按钮（可选） | 一个触发源；接线与 GPIO 读取是本包之外的集成工作 |
| 继电器、翻盖或指示灯（可选） | 由 actuator 回调驱动，回调带四分类结果、不绑引脚 |

**重要提示。** 这不是合规或监管用的分类系统。中国四分类映射是本项目维护的
一张表，不是主管部门的认定结果，各城市口径本来就有差异。这里的任何输出都不应
作为收费、处罚或合规判定的唯一依据。

已知弱点：

- **台架是 Pi 5 + M.2 模块，不是 reComputer R2000 整机。** 加速器与
  HailoRT 相同，外壳、散热与供电不同——长时间满载的表现请在你要出货的整机上实测。
  开放词汇视觉塔的 INT8 量化仍然在 `hailo optimize` 处失败。如果你自己
  训练并量化 MobileNetV3-Small，先验证它的 INT8——它在同一条编译链路上塌缩过
  （详见方案页）。
- **一图一件。** 没有检测器。
- **`textile` 从未被训练或测试过**，`hazardous` 永远不会发出。
- **域偏移。** val 全集 7417 张与部署验证用的 1060 张子集
  都是公开数据集里单件物品的照片，不是现场投放点的图像——请采一批现场数据重测。

## 步骤 1: 在 reComputer RK3588 上部署分类器 {#deploy_recomputer_rk3588_waste type=manual required=true config=devices/recomputer_rk3588_waste.yaml}

放在相机旁边的独立主机，适合一台主机带多个投放点、或者相机本身换不掉的场合。
分类器用 INT8 跑在 RK3588 的 NPU 上。

开始之前你需要：能 SSH 登录板子、几百 MB 空闲空间，以及一个已经构建好的模型，
或者一台装了 `rknn-toolkit2` 2.3.2 的 x86_64 Linux 主机用来转换——转换跑不了
在板子上。下面四个子步骤依次是核对模型、装 RKNN Lite 运行时、准备一帧输入、
跑起来。

有一点跳过就会卡住：Python 绑定的版本必须和板子上已有的 `librknnrt` 一致，
对不上时只会在 `init_runtime` 处抛一个光秃秃的 `RKNN_ERR_FAIL`，没有别的线索。

在 RK3588 硬件上实测 val 全集 7417 张：INT8（calib256+mmse）物料 top-1
0.8881、与 fp32 CPU 基线的一致率 0.9893、p50 2.728 ms、p95 3.417 ms，纯
推理。fp16 物料 top-1 0.8882、一致率 0.9988、p50 5.575 ms、p95 9.904 ms——
INT8 比 fp16 快 51%，准确率没有实质差异。

以上为 RK3588 开发板的实测参考值，不是 reComputer 整机；reComputer 整机
复测后更新。

## 步骤 1: 在 reCamera Pro 上部署分类器 {#deploy_recamera_pro_waste type=recamera_pro_app required=true config=devices/recamera_pro_waste.yaml}

分类器用 INT8 跑在相机自己的 NPU 上——分类路径上没有主机、没有加速卡，
也没有一跳网络。

它以应用中心的应用形式分发，应用 ID 是 `waste-sorting`。先在相机 Web 控制台的
应用中心里装上它，本步骤再指定它、下发你填的设置并把它设为当前应用。应用中心
同一时间只跑一个应用，所以激活它会停掉之前在跑的那个。模型不在应用包里，
由应用中心单独下发到 `/userdata/local/models/waste-sorting/`。

你需要 Web 控制台的管理员凭据，以及 `/userdata` 上约 10 MB 空闲。没有要编译的
东西，也没有要手工拷贝的文件。

填一个设备名称；如果要把事件发到别处，再填一个 broker 地址。broker 留空，结果就
在相机上看；填了 broker，每一次分类都会以一条 JSON 记录发到
`waste/<设备名称>/results`，记录里有 top-3 及各自置信度、物料类与中国四分类、
推理耗时和两个模型哈希——与本方案在其它平台上发出的是同一个形状。

这块硬件上实测 1060 张验证图：物料八类 top-1 0.8764、中国四分类 top-1 0.9566、
与 fp32 CPU 基线的一致率 0.9906、p50 6.380 ms、p95 7.014 ms——纯推理，
不含取图与预处理，且相机自带应用在跑。

INT8 与 fp16 的对比是在这块硬件上另一轮测的，两者都在相机自带应用停止的条件下：
p50 分别为 5.824 ms 与 16.956 ms，即 INT8 快 2.9 倍。INT8、fp16 与主机 fp32
三者在这 1060 张图上的 top-1 相差不到 0.2 pp。

## 步骤 1: 在 reCamera 上部署分类器 {#deploy_recamera_waste type=recamera_cpp required=true config=devices/recamera_waste.yaml}

安装 `.deb` 并把 BF16 模型放到 `/userdata/local/models/`。整个分类器跑在
相机自己的 SG2002 TPU 上——分类路径上没有主机、没有加速卡，也没有一跳网络。

开始之前你需要：相机能通过 USB 或网络访问、`recamera` 用户的 SSH 密码，
以及 `/userdata` 上约 10 MB 空闲。

### 接线

1. 用 USB-C 连接 reCamera，或确认它在你的网络里可达
2. 填入它的 IP 地址（USB 默认给的是 `192.168.42.1`）与 `recamera` 用户的
   SSH 密码
3. 部署

### 落到设备上的内容

| 路径 | 内容 |
|------|------|
| `/usr/local/bin/waste-sorting` | 应用本体 |
| `/etc/init.d/K92waste-sorting` | 它的 init 脚本，停在 K 状态 |
| `/userdata/local/models/efficientnet_lite0_waste8_cv181x_bf16.cvimodel` | 模型，8.3 MB |
| `/etc/waste-sorting.conf` | 数据流 ID、MQTT 目标、置信度阈值与去抖帧数，取自下方字段 |

init 脚本刻意停在 K 状态（`K92`，不是 `S92`）：同一时刻只能有一个应用占用
摄像头，起哪个由控制台决定。

这张图没有 INT8 cvimodel——TPU-MLIR 1.7 对它跑不完校准——所以这里发的是
BF16 模型，这台相机上不存在 INT8 的精度或时延数字。

这块硬件上实测 1060 张验证图，走的是同样的离线预处理（中心裁剪，不经过
相机取图路径）：物料八类 top-1 0.8792、中国四分类 top-1 0.9566、与 fp32
CPU 基线的一致率 0.9915、p50 24.276 ms、p95 24.323 ms（纯推理，不含取图与
预处理），峰值常驻内存 11.6 MB。经相机自身取图与裁剪后的端到端精度请在自己现场实测。

### 故障排查

| 问题 | 解决办法 |
|------|----------|
| 应用一启动就退出 | 模型没加载成功。确认 `/userdata/local/models/efficientnet_lite0_waste8_cv181x_bf16.cvimodel` 存在且 sha256 与设备配置里的一致——文件缺失或不完整会让应用在碰摄像头之前就退出。 |
| 停掉另一个画廊应用后，`start` 连续两次失败 | VPSS 组是驱动侧资源，进程级的"摄像头是否空闲"检查覆盖不到它。重启相机即可恢复。 |

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
- **HEF 由部署器下发。** 步骤 1 从 CDN 拉
  `efficientnet_lite0_waste8_u8_t2.hef`，用 sha256
  `c514a4636dea5d9b3d0fb93f2d4a3dbe15ca907228122e3ed42bc894fce391d1`
  校验后才使用。设备需要能访问 `sensecraft-statics.seeed.cc` 的 HTTPS，
  不需要手工拷贝。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `No /dev/hailo0` | 卡没插好，或者 `hailo_pci` 没加载。`lspci \| grep -i hailo` 与 `dmesg \| grep -i hailo`。 |
| `libhailort.so.4.21.0 not found` | 本部署 ABI 锁在 HailoRT 4.21。装这个版本；驱动、库与 python 绑定不要混版本。 |
| `expected both hailort and hailort-pcie-driver on hold` | `sudo apt-mark hold hailort hailort-pcie-driver`。 |
| `hailo_pci is missing force_desc_page_size=4096` | `echo 'options hailo_pci force_desc_page_size=4096' \| sudo tee /etc/modprobe.d/hailo.conf && sudo reboot`。 |
| `No HEF for this solution` | 步骤 1 的下载或 sha256 校验没通过。重跑步骤 1；如果设备访问不了 `sensecraft-statics.seeed.cc`，在别处下好放到步骤里给出的路径，再按上面的 sha256 校验。 |
| `_pyhailort` 导入报错 | 主机的绑定被挂进容器，只能在同一个 Python 小版本下导入。Bookworm 是 3.11，trixie 是 3.13。 |
| 自己训的 MobileNetV3-Small 在 Hailo 上 INT8 表现很差 | 属预期——不要直接量化它。MobileNetV3-Small（m1b）在同一条编译链路上塌缩到接近随机水平（与 CPU/native 一致率 0.115）。EfficientNet-Lite0 正因为这个原因成为基线。 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="reComputer R2000 series" config=devices/hailo_waste.yaml default=true}

从本机通过 SSH 部署到树莓派。这是常规路径。

### 部署目标 {#hailo_local type=local device=hailo device_name="reComputer R2000 series" config=devices/hailo_waste.yaml}

直接在树莓派上运行部署，适用于你已经在设备上作业的情况。

## 步骤 2: 查看实时分类画面 {#preview_hailo_waste type=web_dashboard required=false config=devices/preview_waste.yaml}

打开运行时自带的页面：实时画面、一个触发按钮、健康接口。如果步骤 1 没能
拿到 HEF，实时画面照样能起来，但分类结果起不来。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 页面打不开 | 在设备上 `docker ps`——`waste` 容器应当在跑。看 `docker logs edge-waste-app`。 |
| 页面能开但预览是黑的 | 视频源写错或不可达。USB 相机检查 `/dev/videoN` 有没有挂进容器；RTSP 先用 VLC 测地址。 |
| 预览正常但 `/events` 一直空 | 如果设备上没有 HEF，模型永远加载不上，所以什么都不会被分类——见步骤 1 的「No HEF for this solution」条目。 |
| 物品在画面里很小 | 重新对准。方案页数字都取自物品占满取景的画面。 |

## 步骤 3: 接好触发并确认一次分类 {#trigger_setup_hailo type=manual required=true verify=true config=devices/trigger_setup.yaml}

端到端验证。如果步骤 1 已经把 HEF 放到了设备上，这一步会确认你自己的部署
拿到与步骤 1 里 val 全集 7417 张实测一致的结果。如果 HEF 还缺，先把取景与
订阅这两小步跑掉，除模型之外的部分就都确认过了。

### 前置条件

- 步骤 1 已尝试过，三道 ABI 关卡通过，容器在跑。
- 同网络的某台机器上有 `mosquitto_sub`，或者直接用 broker 容器：
  `docker exec edge-waste-mosquitto mosquitto_sub …`。
- 一件属于有训练数据的类别的物品——除了 textile 都行。

### 部署完成

板子已经准备好，栈也在跑，分类跑在 Hailo-8 上。如果步骤 1 没把 HEF 拿到
设备上，分类被它卡住；触发与 MQTT 链路仍然可以验证。

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

- 把你测到的精度与时延对照方案页上这份 HEF 的参照数据：val 全集 7417 张，
  物料八类 top-1 0.8889、中国四分类 0.9507、p50 3.166 ms。
- 保住你刚建立的 ABI 状态：两个 Hailo 包都 hold 着，
  `force_desc_page_size=4096` 保持在位。这份用 Hailo 编译器
  编出来的 HEF 需要的正是这一套。
- 离开工作台之前把 MQTT 指向带凭据的 broker。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 一条消息都没有 | 先确认设备上是不是真有 HEF（`ls` models 目录)。不在就是步骤 1 在下载这一步失败了。在的话，去容器日志里找别的故障。 |
| 触发计数不动 | 触发源没配上。检查 `config/config.json` 里的 `trigger.sources`。 |
| 按一次按钮出两条消息 | 去抖时间对这个抖动的开关来说太短。调高 `trigger.debounce_ms`；低于约 300 ms 时抖动的按钮会触发两次。 |
| `configure(hef)` 崩溃 | `force_desc_page_size=4096` 没设，或者设完没重启。 |
| 置信度阈值的表现与 Orin 套餐不同 | 方案页上「4.3% 低于 0.5」是 CPU FP32 上的数字。这块板子的 INT8 置信度分布是另一次独立测量。这份 HEF 在真机上的参照值是与 CPU 一致率 0.9581；如果看到预测坍缩到单一类别，反馈回来。 |
| 想在这里用开放词汇 track | 这个套餐不提供。SigLIP 2 的 INT8 量化在 `hailo optimize` 处失败。 |
