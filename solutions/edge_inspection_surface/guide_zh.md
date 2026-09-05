## 套餐: IP 摄像头 + reComputer J（Orin） {#orin}

有实测的那条路径。Jetson Orin 拉取相机的 RTSP 流，用 TensorRT FP16 跑
YOLOX-Tiny，再把判定发到 Modbus TCP 与 MQTT 上。engine 在部署过程中于设备上
构建——TensorRT engine 与那块 GPU 架构和那个 TensorRT 版本绑定，无法预先打包分发。

| 设备 | 用途 |
|--------|---------|
| reComputer J40 / J30 | 推理、OK/NG 规则、Modbus TCP 服务端、MQTT 发布、预览页 |
| IP 摄像头 | 提供 RTSP 视频；任意对着钢带或工件取景的 RTSP 相机 |
| PLC 或产线控制器 | 可选的 Modbus TCP 主站，读取判定 |

**重要：** 内部验证用。模型训练自 NEU-DET 的转载版，许可未核实——
在许可确认之前不得用于对外 demo、客户现场展示或商业物料。
实测精度是 290 张验证图上 mAP50 0.7577、部署阈值 0.35 下召回 0.6969，
每个数字都是单次未复现的实测。已知弱点：crazing 是最弱的一类，AP50 只有 0.3603，
调阈值救不回来；帧级误报无法测量，因为数据集里每张图都带缺陷；
所有数字都来自合成视频，不是真实相机。

## 步骤 1: 部署表面质检 {#deploy_jetson_inspection type=docker_deploy required=true config=devices/jetson_inspection.yaml}

在 Jetson 上部署检测器并构建它的 TensorRT engine。预留约 10 分钟；
仅 engine 构建一项在 Orin NX 上实测 291 s。

### 前置条件

1. Jetson 运行 JetPack 6.x，且 NVIDIA container runtime 可用。
2. 至少 10 GB 空闲磁盘——ONNX 模型、构建出的 engine 与容器镜像都在设备上。
3. 相机的 RTSP 地址（含用户名密码），例如
   `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`。
   先用 VLC 测一遍。
4. **容器镜像尚未发布。** compose 文件写的是
   `sensecraft-missionpack.seeed.cn/solution/edge-inspection-jetson:0.1.1-dev`，
   但这个 tag 上什么都没推。请用上游仓库的
   `platforms/jetson/Dockerfile.slim` 在设备上构建后改这个 tag，
   或者部署前把 `INSPECTION_IMAGE` 指向你本地的 tag。
5. **ONNX 模型同样没有上传 CDN**，原因同为许可未结清。部署步骤会尝试下载
   `yolox_tiny_neu6.onnx` 并校验 sha256
   `4eb5e4ff6144810e919f2a63ad8f7dcd1c1ac5309d207b1d9ff832ba6cd63aba`。
   在许可确认之前，请手工把该文件放到设备的
   `~/edge-inspection-surface/jetson_inspection/models/yolox_tiny_neu6.onnx`；
   两种方式都会做校验。
6. 部署前先定好判定阈值。0.35 是冻结值；方案页给出了 0.25 与 0.45 的代价对照。
7. **选一个检测器 track。** `config/config.json` 里的 `model.track`
   （部署输入项 **检测器 Track**）可选 `yolox`（默认，也是唯一在这块板上
   实测过的 track——291 s engine 构建、本页所有 Jetson 时延数字都是它的）、
   `dfine` 或 `rtdetrv2`。两个 DETR track 在 CPU-only 对比里（单种子——见
   方案页"检测器选型"一节）mAP50 持平或略好、等精度下召回更高，但还没有
   在 Orin 上构建过 engine 或计过时；选它们会像 `yolox` 一样重新构建
   TensorRT engine，只是没有事先的耗时预期。两个 track 都沿用同一个
   0.35 冻结阈值，而这个阈值是按 `yolox` 的分数分布标定的，不是它们的。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| engine 构建报 `Static model does not take explicit shapes` | 本模型导出的是静态 batch-1 ONNX，因此不能给 trtexec 传 `--minShapes/--optShapes/--maxShapes`。部署步骤已经不传；如果你用上游的 `build_engine.sh` 手工构建，设 `TRT_STATIC_SHAPE=true` |
| engine 构建失败或中途停下 | 确认 `/usr/src/tensorrt/bin/trtexec` 存在、磁盘有 10 GB 空闲。重试前删掉残留的 `.part`——没建完的 engine 不会被移到位，但残留文件会挡住重建 |
| 容器里 `numpy.core.multiarray failed to import`，或 cv2 导入失败 | 有人把宿主机的 python 包顶到了镜像自带的前面。只能挂 `/usr/lib/python3.10/dist-packages/tensorrt` 这一个包——整挂 `dist-packages` 会让宿主机的 numpy 2.x 和坏掉的 cv2 盖住镜像里钉死的 numpy 1.26.4 |
| `docker compose` 去读 `._docker-compose.yml` 报错，或配置加载器读到了 `._config.json` | 从 macOS 上传素材时带进了 AppleDouble 附属文件。部署步骤会删掉上传目录里的 `._*` 与 `.DS_Store`；如果是手工拷贝的，在 compose 目录里跑 `find . -name '._*' -delete` |
| 相机没有画面 | 用 VLC 测 RTSP 地址。路径或用户名密码写错是最常见的失败原因 |
| ONNX 的 sha256 对不上 | 下载被截断，或者文件是另一版构建。删掉重下或拷贝正确的文件；不要去改期望哈希 |
| 部署连不上 SSH | 确认 SSH 可达、用户名正确——Seeed 镜像常用 `recomputer`、`nvidia` 或 `ubuntu` |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_inspection.yaml default=true}

从这台电脑通过 SSH 部署到 Jetson。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson Orin" config=devices/jetson_inspection.yaml}

如果你就在这台 Jetson 上操作，直接在本机运行。

---

## 步骤 2: 查看实时检测画面 {#preview_orin_inspection type=web_dashboard required=false config=devices/preview_inspection.yaml}

打开设备自带的页面，看实时画面上画出的检测框，以及下面的健康计数。

### 部署完成

设备已在运行并发布结果。结果发到 MQTT 1883 端口的
`<设备名>/inspection/<流编号>/results`，判定同时在 Modbus TCP 502 端口、
unit 1 的线圈 0 与 1 上。

#### 快速验证

1. 打开 `http://<设备 IP>:8080/`，确认 MJPEG 预览在动。
2. 看 `http://<设备 IP>:8080/healthz`——`inference_time_ms` 应该是几毫秒，
   10 FPS 下 `frames_dropped` 应为 0，`mqtt.rejected` 应为 0。
   `rejected` 非零表示 payload 没通过契约校验，被丢弃而不是发出去了。
3. 把一件有缺陷的样品放到相机前，看是否出现带类别名与分数的检测框。
4. 从另一台机器订阅主题：
   `mosquitto_sub -h <设备 IP> -t '<设备名>/inspection/#' -v`。

#### MQTT 消息

一帧一条，带上该帧内所有检测框：

```json
{
  "type": "surface_inspection_result",
  "version": "1.0.0",
  "device": "orin-nx",
  "stream_id": "line1-cam1",
  "frame_id": 10423,
  "verdict": "NG",
  "verdict_reason": "2 defect(s) >= min_defects=1",
  "defect_count": 2,
  "primary_class_id": 1,
  "coordinate_space": "normalized_center_wh",
  "inference_time_ms": 6.4,
  "pipeline_ms": 21.8,
  "detections": [
    {"slot": 0, "class_id": 1, "class_name": "inclusion", "score": 0.87,
     "bbox": [0.4125, 0.5312, 0.1094, 0.2031]}
  ]
}
```

`slot` 是帧内按分数降序的下标。这条流水线不做跟踪，`slot` 跨帧没有任何意义。
无缺陷时 `primary_class_id` 取 `-1`——注意 Modbus 寄存器在同样情况下取 `0`，
因为保持寄存器是无符号 16 位，塞不下 `-1`。

#### 下一步

- 把 Modbus 线圈接到剔除或打标工位，然后做步骤 3。
- 把 MES 或历史库指向 MQTT 主题。设备只发布，自己从不写时序数据库。
- 加相机之前先压测。Orin NX 上的容量实测是稳定 8 路，
  用的是合成的 640x640 视频源，而且那次测量没有发 MQTT、没有写 Modbus。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 页面打不开 | 8080 端口跑在 host 网络上。确认容器已起（`docker ps`），并确认 8080 没有被别的服务占用 |
| 预览在动但从来不出框 | 要么画面里没有缺陷，要么阈值定高了。改任何东西之前先看 `/events` 里最近的判定 |
| `frames_dropped` 一直涨 | 源送帧比流水线消费快。RTSP 源按设计丢最旧的帧；调低配置的 FPS，或者减少路数 |
| `mqtt.rejected` 非零 | payload 在发布路径上没通过契约校验。看容器日志——通常意味着后端改动改变了 payload 的形状 |

---

## 步骤 3: 核对 Modbus 输出 {#plc_check type=manual required=false verify=true config=devices/plc_check.yaml}

确认 Modbus 主站看到的就是 PLC 将要据以动作的内容。只用 MQTT 的现场可以跳过这一步。

### 前置条件

1. 一台同网段、能做 Modbus TCP 主站的机器。
2. 设备 IP，以及部署时填的从站号（下面的寄存器表按 unit 1 写）。

### 部署完成

寄存器表，502 端口上的 unit 1：

| 地址 | 含义 |
|---|---|
| Coil 0 | NG，与线圈 1 互斥 |
| Coil 1 | OK，与线圈 0 互斥 |
| HR 0 | 主缺陷类别 ID——本帧最高分的那个框；OK 时为 0 |
| HR 1 | 缺陷数 |
| HR 2 | 主缺陷框 cx，归一化 x10000 |
| HR 3 | 主缺陷框 cy，归一化 x10000 |
| HR 4 | 主缺陷框 w，归一化 x10000 |
| HR 5 | 主缺陷框 h，归一化 x10000 |
| HR 6 | 心跳 Unix 秒，uint32 高字 |
| HR 7 | 心跳 Unix 秒，uint32 低字 |

#### 快速验证

1. 按 unit 1、端口 502 轮询，读线圈 0-1 与 HR 0-7。上游仓库自带的脚本可以直接做：
   `python evaluation/read_modbus.py --host <设备 IP> --port 502 --unit 1`。
2. 让有缺陷的样品经过相机时连续采样，观察线圈对翻转。
   Orin NX 上的核对以 20 Hz 采样抓到两次翻转。
3. 确认同一次采样里两个线圈绝不同时为 1。一旦读到 `(1,1)` 就停下来——
   PLC 无论锁哪一个线圈，都会对一个不存在的判定动作。
4. 在一帧 NG 上确认 HR 2-5 落在 0-10000 内，解码后与 MQTT 消息里的框一致。
   在一帧 OK 上确认 HR 0-5 全为 0。
5. 确认没有新判定时 HR 6-7 仍按自己的间隔递增——心跳独立于判定路径，
   只用 Modbus 的集成方靠它区分「没有缺陷」和「检测器挂了」。

#### 下一步

- 锁线圈，不要锁寄存器：寄存器先被原子更新，线圈翻转时它们已经描述的是那一帧。
- 对心跳停更报警。这是只用 Modbus 的集成方在检测器停止时唯一能拿到的信号。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 502 端口连接被拒 | 配置里关掉了 Modbus，或者容器没起来。检查设备上 `config/config.json` 里的 `modbus.enabled` |
| MQTT 有检测结果但寄存器全 0 | 你读的从站号与部署时写入的不是同一个，或者正好读在一帧 OK 上 |
| 数值看着合理但框对不上 | HR 2-5 是归一化 x10000 的中心点与宽高，不是像素。除以 10000 再乘画面尺寸 |
| 接了多路相机却只有一组寄存器 | 这是设计如此——契约只定义了一组寄存器，多路时最后一次判定生效。要按路独立寄存器得先改契约 |

---

## 步骤 4: 启用无监督异常检测（可选） {#enable_anomaly_jetson type=manual required=false verify=true config=devices/enable_anomaly.yaml}

可选。在检测器旁边跑一个第二模型（EfficientAD-S，只用无缺陷图训练），
让一帧即便是检测器从未学过命名的缺陷类型，也能被标成"跟 OK 参考集不像"。
它不进判定路径——跳过这一步，介绍页上的每一个数字都照样成立。

### 前置条件

- 运行时已部署（步骤 1），改配置加重启容器就够。
- EfficientAD-S 的 ONNX 已拷到设备上——它还没上 CDN，与检测器同一个许可
  确认关卡。见该步骤第一个子步骤。
- 如果你打算把 `anomaly_score` 用在"看看机制能不能跑通"之外的地方，
  需要用真实检测相机采集你自己的 OK 样本。随包评测的 OK 集是 DeepPCB
  的模板扫描图，不是这台相机拍的——在拿它标定 `anomaly.threshold` 之前，
  先看方案页"无监督异常检测"一节。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| MQTT 事件里从来不出现 `anomaly_score` | 确认 `anomaly.enabled: true` 已保存且容器已重启；检查容器日志里 `anomaly.path` 对应的模型加载是否报错 |
| 不管样品是什么，`anomaly_score` 都稳定在同一个值附近 | 大概率是 `anomaly.threshold` 直接抄了本方案自己的评测——那个阈值是在 DeepPCB 图上标定的，不是你相机的 OK 图。先用自己的 OK 集重新标定 |
| 把单一的 `anomaly_score` 当成"这帧异常"来判，结果不稳定 | 这是已知限制，不是 bug——随包评测的图像级 AUROC 是 0.52（接近随机）。用像素/区域级信号（`heatmap_ref` 加分数），不要用单一帧级门限 |

## 步骤 5: 启用 VLM 解释（可选） {#enable_vlm_jetson type=manual required=false verify=true config=devices/enable_vlm_explanation.yaml}

可选。让运行时指向外部共享 VLM 服务（`edge-vision-vlm`，通常跑在另一台
Orin 上），让低置信度或只有异常分数的帧在旁路 MQTT 主题上拿到一段人话
解释。这条路径不进帧循环、不改变判定——跳过这一步，介绍页上的每一个数字
都照样成立。

### 前置条件

- 已经跑起来、且这台设备能访问到的 `edge-vision-vlm` 实例——本方案不部署
  也不打包这个服务。
- 运行时已部署（步骤 1），改配置加重启容器就够。
- 要用 `anomaly` 触发条件，得先启用步骤 4——否则只有 `low_confidence`
  生效。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 停掉 VLM 服务后拿到 HTTP 502 而不是连接错误 | 这是透明代理拦截了 VLM 地址，不是 VLM 自己的错误码。测试前先把 VLM 主机加进设备的 `no_proxy`——见该步骤第二个子步骤 |
| 一直收不到解释事件 | 确认 `vlm.enabled: true` 已保存且容器已重启；在容器里 `curl <base_url>/healthz` 检查；没收到事件本身是一个已定义的降级状态，不是崩溃 |
| 收到了解释事件但主 results 事件没了 | 不应该发生——两者互相独立。这应该按 VLM 客户端的 bug 处理，而不是触发条件配置的问题 |

---

## 套餐: IP 摄像头 + Raspberry Pi 5（Hailo-8） {#pi_hailo}

更便宜、也未经验证的那条路径。INT8 HEF 已编译，量化损失在编译器 emulator 上
量过，运行时镜像也能交叉构建成 arm64——但这里没有一样东西在树莓派上跑过。
设备上有三道 ABI 关卡要先过，容器才起得来。

| 设备 | 用途 |
|--------|---------|
| Raspberry Pi 5 + Hailo-8 | 推理、OK/NG 规则、Modbus TCP 服务端、MQTT 发布、预览页 |
| IP 摄像头 | 提供 RTSP 视频；任意对着钢带或工件取景的 RTSP 相机 |
| PLC 或产线控制器 | 可选的 Modbus TCP 主站，读取判定 |

**重要：** 内部验证用，与另一个套餐同样的许可限制。**此外，本套餐没有任何一项
经过上板验证。** 这块板卡的精度、吞吐、时延数字都不存在。已知的只有编译器
emulator 在 20 张验证图上的结果：部署的 level-1 INT8 版本 mAP50 0.7266，
CPU 浮点基准是 0.7228，整帧漏检 2 帧对 0 帧。那个样本只有 45 个框，不是结论。
crazing 弱、误报无法测量这两条在这里同样成立。

## 步骤 1: 在 Hailo 上部署表面质检 {#deploy_hailo_inspection type=docker_deploy required=true config=devices/hailo_inspection.yaml}

部署检测器与预编译好的 HEF。没有设备端编译，所以比 Jetson 那条路快——
前提是三道 ABI 关卡都过得去。

### 前置条件

1. **HailoRT 必须是 4.21.x，而且两个包都要 hold。** HEF 是用 Dataflow Compiler
   3.31.0 / HailoRT 4.21.0 编的。驱动、用户态库、python 绑定三者必须同一版本：
   `hailortcli --version` 应报 4.21.x，`apt-mark showhold` 里必须同时有
   `hailort` 与 `hailort-pcie-driver` 两行。只 hold 驱动的话，
   apt 会把用户态库偷偷升上去，HEF 就对不上了。
2. **`hailo_pci` 必须带 `force_desc_page_size=4096` 加载。** 树莓派 5 的内核
   PAGE_SIZE 是 16 KB，Hailo-8 的 max_desc_page_size 是 4 KB。不加这个参数时
   `VDevice()` 和 `hailortcli fw-control identify` 都能过，
   偏偏在 `configure(hef)` 那一步崩：
   `echo 'options hailo_pci force_desc_page_size=4096' | sudo tee /etc/modprobe.d/hailo.conf`
   然后重启。
3. **宿主机与容器的 Python minor 版本必须一致。** 宿主的 `hailo_platform`
   绑定会被挂进容器，而 `_pyhailort.cpython-3XX-*.so` 只能被同一 minor 的
   解释器 import。Pi OS bookworm 是 3.11，默认镜像基座与之对应；
   trixie 是 3.13，需要换基座重新构建镜像。
4. 至少 4 GB 空闲磁盘。实测新增占用约 452 MB——运行镜像约 443 MB、
   8.9 MB 的 HEF，加上配置。
5. **容器镜像尚未发布。** compose 文件写的是
   `sensecraft-missionpack.seeed.cn/solution/edge-inspection-rpi-hailo:0.1.0-dev`，
   但这个 tag 上什么都没推。请用上游仓库的 `platforms/rpi-hailo/Dockerfile`
   构建后设 `INSPECTION_IMAGE`，或者把本地构建改成这个 tag。
6. **HEF 也没有上传 CDN**，原因同为许可未结清。部署步骤会尝试下载并校验
   默认 level-1 版本的 sha256
   `02201b733a3009a5e72cebf49b9b314bd09d63dafa9cf4b9f359251ff49c0565`
   （level-0 是
   `9638f2b210b49b10b44658d2e970b2822e0fac7d36ec8831f08ad4d0a10dac8f`）。
   在那之前请手工把文件放到
   `~/edge-inspection-surface/hailo_inspection/models/yolox_tiny_neu6_o1.hef`；
   两种方式都会做校验。
7. 相机的 RTSP 地址，先用 VLC 测过。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 部署停在 "libhailort.so.4.21.0 not found" | 设备上是另一个版本的 HailoRT。本部署被 ABI 锁死；要么装 4.21.x，要么按设备上的版本重编 HEF。只改挂载路径没有用 |
| 部署停在 `force_desc_page_size` 检查 | 加上 modprobe 参数再重启。树莓派 5 上这不是可选项——不加的话容器能起来，然后死在 `configure(hef)` 里 |
| 容器因为提到 `_pyhailort` 的 python import 错误退出 | 宿主与容器的 Python minor 不一致。用与宿主匹配的基座重建镜像（宿主是 3.13 就用 `--build-arg RUNTIME_IMAGE=...trixie-slim`） |
| 日志里出现 `AssembleError` | HEF 的九个输出张量与期望布局对不上。输出是按特征图边长与通道数归位的，不按名字，所以这说明用的不是本方案期望的那份 HEF。拿 sha256 与 `assets/models/hef_o1.manifest.json` 核对 |
| `docker compose` 去读 `._docker-compose.yml` 报错 | 从 macOS 上传时带进了 AppleDouble 附属文件。部署步骤会删掉上传目录里的 `._*` 与 `.DS_Store`；手工拷贝的话跑 `find . -name '._*' -delete` |
| 能出框但召回明显低于方案页 | 这条路径上属预期——level-0 版本在 emulator 子集上比 CPU 基准掉了 0.03 mAP50。确认你跑的是默认的 level-1 HEF |
| 相机没有画面 | 用 VLC 测 RTSP 地址。路径或用户名密码写错是最常见的失败原因 |
| 想在这块板上跑 `dfine` 或 `rtdetrv2` 检测器 track | 不支持——Hailo Dataflow Compiler 3.31.0 的解析器对两者都拒绝（可变形注意力算子 `GridSample`/`GatherElements`/`TopK` 在 Hailo-8 上没有实现；见方案页"检测器选型"一节）。这个套餐只提供 `yolox` |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="Raspberry Pi 5" config=devices/hailo_inspection.yaml default=true}

从这台电脑通过 SSH 部署到树莓派。

### 部署目标 {#hailo_local type=local device=hailo device_name="Raspberry Pi 5" config=devices/hailo_inspection.yaml}

如果你就在这台树莓派上操作，直接在本机运行。

---

## 步骤 2: 查看实时检测画面 {#preview_hailo_inspection type=web_dashboard required=false config=devices/preview_inspection.yaml}

打开设备自带的页面，看实时画面上画出的检测框，以及下面的健康计数。

### 部署完成

设备已在运行并发布结果。结果发到 MQTT 1883 端口的
`<设备名>/inspection/<流编号>/results`，判定同时在 Modbus TCP 502 端口、
unit 1 的线圈 0 与 1 上。

#### 快速验证

1. 打开 `http://<设备 IP>:8080/`，确认 MJPEG 预览在动。
2. 看 `http://<设备 IP>:8080/healthz`——`inference_time_ms` 应该是几毫秒，
   10 FPS 下 `frames_dropped` 应为 0，`mqtt.rejected` 应为 0。
   `rejected` 非零表示 payload 没通过契约校验，被丢弃而不是发出去了。
3. 把一件有缺陷的样品放到相机前，看是否出现带类别名与分数的检测框。
4. 从另一台机器订阅主题：
   `mosquitto_sub -h <设备 IP> -t '<设备名>/inspection/#' -v`。

#### MQTT 消息

一帧一条，带上该帧内所有检测框：

```json
{
  "type": "surface_inspection_result",
  "version": "1.0.0",
  "device": "rpi-hailo",
  "stream_id": "line1-cam1",
  "frame_id": 10423,
  "verdict": "NG",
  "verdict_reason": "2 defect(s) >= min_defects=1",
  "defect_count": 2,
  "primary_class_id": 1,
  "coordinate_space": "normalized_center_wh",
  "inference_time_ms": 6.4,
  "pipeline_ms": 21.8,
  "detections": [
    {"slot": 0, "class_id": 1, "class_name": "inclusion", "score": 0.87,
     "bbox": [0.4125, 0.5312, 0.1094, 0.2031]}
  ]
}
```

`slot` 是帧内按分数降序的下标。这条流水线不做跟踪，`slot` 跨帧没有任何意义。
无缺陷时 `primary_class_id` 取 `-1`——注意 Modbus 寄存器在同样情况下取 `0`，
因为保持寄存器是无符号 16 位，塞不下 `-1`。

#### 下一步

- 把 Modbus 线圈接到剔除或打标工位，然后做步骤 3。
- 把 MES 或历史库指向 MQTT 主题。设备只发布，自己从不写时序数据库。
- 先把这块板测出来再信它。Hailo 这条路径上没有任何吞吐、时延或上板精度数字，
  `/healthz` 上的计数会是第一份真实数据。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 页面打不开 | 8080 端口跑在 host 网络上。确认容器已起（`docker ps`），并确认 8080 没有被别的服务占用 |
| 预览在动但从来不出框 | 要么画面里没有缺陷，要么阈值定高了。改任何东西之前先看 `/events` 里最近的判定 |
| `frames_dropped` 一直涨 | 源送帧比流水线消费快。RTSP 源按设计丢最旧的帧；调低配置的 FPS |
| `mqtt.rejected` 非零 | payload 在发布路径上没通过契约校验。看容器日志——通常意味着后端改动改变了 payload 的形状 |

---

## 步骤 3: 核对 Modbus 输出 {#plc_check_hailo type=manual required=false verify=true config=devices/plc_check.yaml}

确认 Modbus 主站看到的就是 PLC 将要据以动作的内容。只用 MQTT 的现场可以跳过这一步。

### 前置条件

1. 一台同网段、能做 Modbus TCP 主站的机器。
2. 设备 IP，以及部署时填的从站号（下面的寄存器表按 unit 1 写）。

### 部署完成

寄存器表，502 端口上的 unit 1：

| 地址 | 含义 |
|---|---|
| Coil 0 | NG，与线圈 1 互斥 |
| Coil 1 | OK，与线圈 0 互斥 |
| HR 0 | 主缺陷类别 ID——本帧最高分的那个框；OK 时为 0 |
| HR 1 | 缺陷数 |
| HR 2 | 主缺陷框 cx，归一化 x10000 |
| HR 3 | 主缺陷框 cy，归一化 x10000 |
| HR 4 | 主缺陷框 w，归一化 x10000 |
| HR 5 | 主缺陷框 h，归一化 x10000 |
| HR 6 | 心跳 Unix 秒，uint32 高字 |
| HR 7 | 心跳 Unix 秒，uint32 低字 |

#### 快速验证

1. 按 unit 1、端口 502 轮询，读线圈 0-1 与 HR 0-7。上游仓库自带的脚本可以直接做：
   `python evaluation/read_modbus.py --host <设备 IP> --port 502 --unit 1`。
2. 让有缺陷的样品经过相机时连续采样，观察线圈对翻转。
3. 确认同一次采样里两个线圈绝不同时为 1。一旦读到 `(1,1)` 就停下来——
   PLC 无论锁哪一个线圈，都会对一个不存在的判定动作。
4. 在一帧 NG 上确认 HR 2-5 落在 0-10000 内，解码后与 MQTT 消息里的框一致。
   在一帧 OK 上确认 HR 0-5 全为 0。
5. 确认没有新判定时 HR 6-7 仍按自己的间隔递增——心跳独立于判定路径。

#### 下一步

- 锁线圈，不要锁寄存器：寄存器先被原子更新，线圈翻转时它们已经描述的是那一帧。
- 对心跳停更报警。这是只用 Modbus 的集成方在检测器停止时唯一能拿到的信号。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 502 端口连接被拒 | 配置里关掉了 Modbus，或者容器没起来。检查设备上 `config/config.json` 里的 `modbus.enabled` |
| MQTT 有检测结果但寄存器全 0 | 你读的从站号与部署时写入的不是同一个，或者正好读在一帧 OK 上 |
| 数值看着合理但框对不上 | HR 2-5 是归一化 x10000 的中心点与宽高，不是像素。除以 10000 再乘画面尺寸 |
| 接了多路相机却只有一组寄存器 | 这是设计如此——契约只定义了一组寄存器，多路时最后一次判定生效。要按路独立寄存器得先改契约 |

---

## 步骤 4: 启用无监督异常检测（可选） {#enable_anomaly_hailo type=manual required=false verify=true config=devices/enable_anomaly.yaml}

可选，与 Jetson 套餐相同。在 CPU 上跑 EfficientAD-S（`accelerator: "cpu"`——
这个模型目前没有 Hailo 后端），在检测器旁边跑，让一帧能被标成"跟 OK
参考集不像"。这条路径不进判定路径。

### 前置条件

- 运行时已部署（步骤 1），改配置加重启容器就够。
- EfficientAD-S 的 ONNX 已拷到设备上——它还没上 CDN。
- 在信任 `anomaly.threshold` 之前，先用真实检测相机采集你自己的 OK
  样本——随包评测的 OK 集是 DeepPCB 的模板扫描图，不是这台相机拍的。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| MQTT 事件里从来不出现 `anomaly_score` | 确认 `anomaly.enabled: true` 已保存且容器已重启；检查容器日志里 `anomaly.path` 对应的模型加载是否报错 |
| 不管样品是什么，`anomaly_score` 都稳定在同一个值附近 | 阈值大概率是抄了本方案自己的评测，在 DeepPCB 图上标定，不是你相机的 OK 图。用自己的 OK 集重新标定 |
| 把单一的 `anomaly_score` 当成"这帧异常"来判，结果不稳定 | 已知限制——随包评测的图像级 AUROC 是 0.52（接近随机）。用像素/区域级信号，不要用单一帧级门限 |

## 步骤 5: 启用 VLM 解释（可选） {#enable_vlm_hailo type=manual required=false verify=true config=devices/enable_vlm_explanation.yaml}

可选，与 Jetson 套餐相同。让运行时指向外部共享 VLM 服务（`edge-vision-vlm`，
通常跑在另一台 Orin 上——树莓派本身不跑它），让低置信度或只有异常分数的帧
在旁路 MQTT 主题上拿到一段人话解释。这条路径不进帧循环、不改变判定。

### 前置条件

- 已经跑起来、且这台树莓派能访问到的 `edge-vision-vlm` 实例——本方案不
  部署也不打包这个服务。
- 运行时已部署（步骤 1），改配置加重启容器就够。
- 要用 `anomaly` 触发条件，得先启用步骤 4。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 停掉 VLM 服务后拿到 HTTP 502 而不是连接错误 | 这是透明代理拦截了 VLM 地址，不是 VLM 自己的错误码。测试前先把 VLM 主机加进设备的 `no_proxy` |
| 一直收不到解释事件 | 确认 `vlm.enabled: true` 已保存且容器已重启；在容器里 `curl <base_url>/healthz` 检查；没收到事件本身是一个已定义的降级状态 |
| 收到了解释事件但主 results 事件没了 | 不应该发生——两者互相独立 |
