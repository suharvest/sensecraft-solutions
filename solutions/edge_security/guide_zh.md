## 套餐: Jetson 单机部署 {#jetson_hub}

一台 Jetson Orin 跑完整套：MQTT broker、带告警工作台的汇聚 hub，以及人体检测走
TensorRT、视频解码走 NVDEC 的检测器。不需要第二台机器——hub 不解码视频、不做推理，
实测在同时还跑着检测器的 RK3588 板卡上占单核 3.7%、RSS 52.8 MB。

Orin NX 16GB、JetPack 6.1、TensorRT 10.3.0、1280x720 实测：流水线内推理 p50
4.13 ms，整条流水线 p50 7.24 ms，CPU 占单核 8.5–12.5%，解码确认走 NVDEC。

TensorRT 引擎在部署过程中于你的设备上构建，约需五到六分钟（实测 361 s）。这只发生
一次，重新部署会复用磁盘上已有的引擎。

## 步骤 1: 部署安防服务栈 {#deploy_edge_security_jetson_hub type=docker_deploy required=true config=devices/jetson_hub_stack.yaml}

填入这台机器的地址和摄像头 RTSP 地址，先构建引擎，再安装并启动三个容器。

### 前置条件

- 一台 JetPack 6.x 的 Jetson Orin。本套餐仅支持 Jetson：检测器加载 TensorRT 引擎，
  且拒绝退回 CPU 解码；换成别的机器，部署步骤会带说明直接停下。
- 板卡上装有 TensorRT——`libnvinfer.so.10`、`tensorrt` Python 包，以及
  `/usr/src/tensorrt/bin/trtexec`。三者都随 JetPack 提供，部署步骤会逐个按名检查。
- Docker 已注册 nvidia 容器运行时。正是它把 libcuda、L4T 的 GStreamer 插件和
  `/dev/v4l2-nvdec` 挂进容器。若缺失：`sudo apt-get install -y
  nvidia-container-toolkit && sudo nvidia-ctk runtime configure --runtime=docker
  && sudo systemctl restart docker`。
- 装有 Docker 及 compose 插件。若只有独立版 `docker-compose`，部署步骤会自动补上插件。
- 摄像头的 RTSP 地址，须为 H.264，先用 VLC 测通。路径或用户名密码写错是最常见的
  失败原因，现象和部署失败完全一样。
- 8090（工作台）、1883（broker）、8099（摄像头预览）三个端口空闲。
- 约 6 GB 空闲磁盘，用于镜像、引擎和告警数据库。

### 检查内容

- 引擎构建步骤结束时会打印 `Engine written:` 和一串 sha256。这一步要五到六分钟，
  中途不要打断。
- 最后一步会打印 hub 的 `/api/health` 返回，`mqtt_connected` 必须为 true。
- 最后一步还会打印检测器的 `/debug/decode`。看到 `"decode": "hw"` 且
  `"decoder_factory": "nvv4l2decoder"`，才算确认 NVDEC 真的在流水线里。
- 若是首次启动，还有一步会从 hub 打印出管理员登录信息。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 部署停在「This preset is Jetson-only」 | 目标机器不是 JetPack 系统。改用 RK3588 套餐，或换一台 Jetson。 |
| 部署停在「The nvidia container runtime is not registered」 | 安装 `nvidia-container-toolkit`，执行 `nvidia-ctk runtime configure --runtime=docker`，重启 Docker 后重新部署。 |
| 引擎构建失败或没有产物 | 读失败位置上方的 trtexec 输出。通常是磁盘不够——构建需要约 1.7 GB 内存，产物是一个 9 MB 的引擎。 |
| 检测器日志里出现 `deserialize_cuda_engine returned None` | 磁盘上的引擎是别的 TensorRT 版本或别的机器构建的。删掉 `models/yolov8n_fp16.orin.engine` 再部署一次，该步骤会重建。 |
| 检测器因硬解不可用退出 | `/dev/v4l2-nvdec` 没有进到容器里。确认 `runtime: nvidia` 生效：`docker inspect edge_security-detector-1 --format '{{.HostConfig.Runtime}}'`。 |
| 8090 无响应 | 执行 `docker compose logs hub`，通常是端口被占用。 |
| detector 容器反复重启 | 执行 `docker compose logs detector`，通常是 RTSP 地址不通；在同一台机器上用 VLC 验证。 |
| 工作台里看不到设备 | 检测器每 30 秒上报一次状态，等一个周期；再确认 `config/detector.yaml` 里的 `mqtt_host` 是 `mosquitto`。 |
| 一个人站着不动却连续报警两次 | 检测器跟不上视频流，跟踪目标被回收后换了新的 track id，等于又"进"了一次区域。本套餐下一路 720p 摄像头在 200 ms 的帧周期里只花 7.24 ms，所以先怀疑摄像头或网络，再怀疑检测器。 |

### 部署目标 {#jetson_hub_host type=remote device_name="reComputer J" config=devices/jetson_hub_stack.yaml default=true}

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_jetson_hub type=web_dashboard required=true config=devices/jetson_hub_dashboard.yaml}

登录、画一条边界，走过去看第一条告警。

### 部署完成

broker、hub 和一个检测器已经在你选的机器上运行。

#### 首次登录

1. 工作台地址是 `http://<机器地址>:8090`。
2. 用户名 `admin`。没有固定默认密码：hub 首次启动会生成一个随机密码，写入
   `/data/initial-password.txt` 并打进日志，上面的部署步骤也会打印。输出被截断的话，
   在机器上执行 `docker exec <hub 容器> cat /data/initial-password.txt` 取回——第一行
   用户名，第二行密码。首次登录后 hub 会强制改密，新密码用 bcrypt 哈希存储。
3. 打开**设备**页。检测器应显示为在线，解码方式为 `hw`——本套餐走 NVDEC 硬解，
   检测器拒绝退回 CPU 解码，显示别的值就说明它没跑起来。

#### 画第一条规则

1. 打开**规则**页。编辑器会取一帧检测器的实时画面作为底图，画在哪就是哪。
2. 画一个多边形作为禁区，或画一条线作为越线规则。越线规则可以限定方向：
   `forward`、`backward` 或 `any`。
3. 区域还可以设滞留时长，人在区域内停留超过这个时间，会在入侵告警之外再出一条
   滞留告警。
4. 保存后走进该区域，告警会在一秒内出现在**工作台**页，并附带 hub 向检测器索取的
   现场快照。

#### 处理告警列表

每条告警可以标记为已确认或误报，最近一次操作有撤销条，还有批量模式用于清积压。
筛选后的列表可以导出 CSV。界面提供中英文两种语言。

#### 对外输出的内容

| 主题 | 内容 |
|---|---|
| `sensecraft/security/<device_id>/detections/<stream_id>` | 逐帧人体检测框，带跟踪编号 |
| `sensecraft/security/<device_id>/status` | retained 的在线状态，以及实际使用的解码器 |
| `sensecraft/security/<device_id>/events/<stream_id>` | hub 的判定结果，带 `origin: hub` 标记 |

NVR、PLC 网关或你自己的告警服务可以订阅事件主题，不必轮询接口——但**本套餐里 1883 绑在
loopback 上**，别的机器连不到，需要你有意打开。两步都要做：把 compose 文件里 mosquitto 的
端口映射从 `127.0.0.1:1883:1883` 改成 `1883:1883`，并在 `config/mosquitto.conf` 里加
`password_file`、在 `config/detector.yaml` 里配上对应凭据。只开端口不加密码文件，等于在你的
网络上放了一个任何东西都能往里发伪造告警的匿名 broker。

#### 增加第二路摄像头

一个检测器容器对应一路摄像头。第二路摄像头需要第二个检测器——可以在这台机器上再起
一个容器，给它另一套 `device_id`、`stream_id` 和 `preview_port`，也可以用 RK3588
套餐上一块独立板卡。

在 Orin NX 16GB 上，多进程这条路实测可以撑到八路：每多一个检测器进程占 208 MB 统一
内存，八路 1080p 15 fps 是 120 次推理/秒，对实测 236 次/秒的 GPU 上限约 51%。四个
进程各以 5 fps 推理时互不干扰（p50 4.02–4.07 ms，与单进程独跑一致）。这份预算里有
两项是外推而非实测，正式按八路摄像头交付前应当核实：1080p 15 fps 下每路的 CPU 占用，
以及 NVDEC 的并发会话容量。

端到端（含 hub 与规则）实测过的最大规模仍是两路并发。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 登录页能打开但密码不对 | 从 hub 日志里读生成的密码：`docker compose logs hub \| grep -i admin`。 |
| 规则编辑器只有灰底、没有画面 | 浏览器访问不到检测器的预览地址。确认 `config/detector.yaml` 里的 `preview_advertise_host` 填的是机器的局域网地址，不是 `127.0.0.1`。 |
| 告警没有快照缩略图 | 告警触发时 hub 会向检测器索取快照，超过 200 KB 的快照会被拒绝。查看检测器日志。 |
| 越线时不报警 | 越线判定需要同一跟踪目标在相邻两帧之间跨到线的另一侧。先确认这个人确实被跟踪上了——设备页会显示检测速率。 |

## 套餐: RK3588 单机部署 {#rk3588}

一块 RK3588 板卡跑完整套：MQTT broker、带告警工作台的汇聚 hub，以及人体检测走 NPU、
视频解码走板载硬解的检测器。不需要第二台机器——hub 不解码视频、不做推理，实测在承载
在同时还跑着检测器的 RK3588 板卡上占单核 3.7%、RSS 52.8 MB。

该板卡实测（int8 模型，1280x720）：流水线内推理 p50 41.9 ms，NPU 核心占用 8%，
CPU 占单核 21%，解码确认走硬件。

## 步骤 1: 部署安防服务栈 {#deploy_edge_security_rk3588 type=docker_deploy required=true config=devices/rk3588_detector.yaml}

填入板卡地址和摄像头地址，在板卡上安装并启动三个容器。

### 前置条件

- 板卡已安装 `rknpu2` 运行时，即存在 `/usr/lib/librknnrt.so`。
- 板卡的 `python3` 能 import `rknn_toolkit_lite2`。部署步骤会把它复制进容器，
  找不到就提前失败。
- 存在 Rockchip 硬解节点 `/dev/mpp_service`。检测器在只能用 CPU 解码时会拒绝启动，
  而不是悄悄降级。
- 摄像头输出 H.264。硬解路径是按 H.264 构建的。
- 板卡上 8090（工作台）、1883（broker）、8099（摄像头预览）三个端口空闲。
- 约 6 GB 空闲磁盘，用于两个镜像、板卡依赖库和告警数据库。

### 检查内容

- 这一步会打印 hub 的 `/api/health` 返回；若是首次启动，还会打印管理员登录信息。
- 随后会打印运行中检测器的 `/debug/decode`，即 GStreamer 实际创建的元件。
  期望结果是 `"decode": "hw"` 且 `"decoder_factory": "mppvideodec"`。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 部署停在 "rknnlite is not importable" | 在板卡上安装：`pip3 install rknn_toolkit_lite2`。它是 wheel 包，经常装进部署步骤看不到的 venv。 |
| 检测器报解码器错误后退出 | MPP 插件没准备好。看板卡上 compose 文件旁边的 `gstmpp/` 目录，若为空，安装 `gstreamer1.0-rockchip1` 和 `gstreamer1.0-plugins-bad`。 |
| 部署报成功，但检测器表现得像旧版本 | 板卡上已存在同名镜像时部署会跳过拉取，所以重新发布同一个 tag 不会到达拉过一次的板卡。先看板上实际是哪个：`docker image inspect <image> -f '{{.Id}}'`，和 registry 对一下，重新部署前先 `docker pull`。 |
| 模型加载报版本不匹配 | 文件名里的版本不是二进制里的版本。用 `strings /usr/lib/librknnrt.so \| grep 'librknnrt version'` 读真实版本；随镜像发布的模型按 2.3.2 构建。 |
| 每次启动都打印 `W Query dynamic range failed` | 无害。静态 shape 模型在这个运行时上就是这么打印的。 |
| 检测器在跑，但 hub 里看不到它 | broker 就在同一套栈里，`config/detector.yaml` 里的 `mqtt_host` 应为 `mosquitto`。检测器每 30 s 上报一次状态，先等一个周期再下结论。 |
| 8090 无响应 | 执行 `docker compose logs hub`，通常是板卡上端口被占用。 |

### 部署目标 {#rk3588_board type=remote device_name="RK3588" config=devices/rk3588_detector.yaml default=true}

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_rk3588 type=web_dashboard required=true config=devices/rk3588_dashboard.yaml}

在板卡本机上打开工作台，确认解码方式为硬解。

### 部署完成

板卡正在做人体检测，并在本机判定规则。工作台地址是 `http://<板卡地址>:8090`。

#### 快速验证

1. 用户名 `admin`，密码用部署步骤打印出来的那个——hub 首次启动生成随机密码，没有固定
   默认值。它也在 hub 容器里的 `/data/initial-password.txt`。按提示设置新密码。
2. 在工作台打开**设备**页，能看到你刚才命名的这块板卡。
3. 解码列应显示 `hw`。这个值不是从配置文件读的，而是检测器从实时流水线协商到的
   GStreamer caps 上读出来的。
4. 打开**规则**页，选中这台设备和这一路流，画一个区域或一条线。底图就是这块板卡的
   真实画面。

#### 关于模型

板卡使用 int8 模型。相对 fp16，在 COCO person 上 AP@.5:.95 掉 0.52、小目标掉 0.61；
换来的是推理从 72.3 ms 降到 41.9 ms、NPU 负载从 26% 降到 8%。两者在端到端规则断言上
表现一致。int8 的失效形态是多出低置信度框，而不是漏人，所以先调高 `conf_threshold`，
再考虑换回 fp16。

小目标那个结论是在 COCO 上得到的。如果要部署到广角俯拍、人只有 30 m 远的场地，
先用该场地的实拍素材重新测一遍精度。

#### 下一步

- 每增加一块板卡就重复一次这个套餐。每块板卡自成一套，各自维护自己的告警列表。每台
  检测器要取不同的名字，主题以它为键。
- 如果希望多块板卡共用一份告警列表，在一台独立的常开机器上部署「共享 Hub」套餐，
  再把每块板卡 `config/detector.yaml` 里的 `mqtt_host` 改成那台机器的地址。这是可选
  扩展，不是必须项。
- 单个 hub 上实测过的最大规模是两路并发。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 设备页显示解码为 `sw` | 检测器默认拒绝 CPU 解码，出现 `sw` 说明 `require_hw_decode` 被人为关掉了。把它打开，再去查 MPP 为什么不可用。 |
| 一个人站着不动却重复报警 | 检测器跟不上视频流，跟踪器在不断发新的 track id。用设备页的检测速率和摄像头帧率对一下。 |
| 这台设备的规则底图是灰的 | `preview_advertise_host` 要填板卡的局域网地址，hub 才能从 8099 端口取到画面。 |

## 套餐: Hailo 单机部署 {#hailo}

一块带 Hailo-8 的板卡跑完整套：MQTT broker、带告警工作台的汇聚 hub，以及人体检测走
加速器的检测器。不需要第二台机器。

Raspberry Pi 5 + Hailo-8 实测（1280x720）：流水线内推理 p50 7.7 ms、p95 8.4 ms，
全管线 p50 9.5 ms，CPU 占单核 8.7-13.0%，常驻内存 127-131 MB，测量时板卡上另有
十个无关容器在跑。

**视频解码在 CPU 上,这是设计如此,不是故障。** Raspberry Pi 5 没有 H.264 硬解——
VideoCore VII 只解 HEVC——所以检测器上报 `decode: "sw"`、`fallback_active` 为
false，上面那个 CPU 数字里同时包含了解码和推理。加第二路摄像头前先把这部分算进去。

## 步骤 1: 部署安防服务栈 {#deploy_edge_security_hailo type=docker_deploy required=true config=devices/hailo_detector.yaml}

填入板卡地址和摄像头地址，在板卡上安装并启动三个容器。

### 前置条件

- Hailo PCIe 驱动已加载（存在 `/dev/hailo0`），且安装了版本匹配的 `hailort` 包
  （存在 `/usr/lib/libhailort.so`）。驱动与用户库必须同版本，容器挂载的是板卡自己
  那一份。
- **加速器没有被别的程序占用。** HailoRT 同一时刻只把设备交给一个进程，除非板上
  每一个使用方都改走它的多进程服务（默认关闭）。部署步骤会检查，被占用时直接停下。
- 家目录下有 HailoRT 的 Python wheel（`hailort-*-cp311-*_aarch64.whl`）。
  Raspberry Pi OS 现在是 Python 3.13，而 Hailo 发的是 cp311 wheel，所以板卡自己的
  site-packages 里没有可 import 的包可拷；部署步骤改为解包 wheel 给容器里的 3.11 用。
- 一路 RTSP 摄像头。
- 板卡上 8090（工作台）、1883（broker）、8099（画面预览）端口空闲。
- 约 4 GB 可用磁盘，用于两个镜像、暂存的依赖包和告警数据库。

### 检查内容

- 该步骤会打印 hub 的 `/api/health` 响应；若是首次启动，还会打印管理员登录信息。
- 随后确认检测器确实在工作：`/preview.jpg` 返回 200 且是完整 JPEG，容器处于 running、
  重启次数不再增长。三项都要看——`/healthz` 只要预览服务绑定就返回 200，所以容器可以在
  推理每帧都崩的情况下报 healthy；而崩溃退避期里，重启计数也会暂时不动。任一项不成立，
  该步骤会让部署失败。
- 之后在工作台的设备页能看到板卡在线、`"decode": "sw"`、`"fallback_active": false`。
  这个读数在该板卡上是正确的，不是降级：它没有 H.264 硬解，软解就是主路径。

### 故障排查

| 问题 | 解决办法 |
|------|----------|
| 部署停在「/dev/hailo0 is already held by」 | 有别的程序在用加速器，常见是另一个视觉容器。停掉它再重新部署。HailoRT 无法在进程间共享设备，除非所有使用方都走多进程服务。 |
| `hailortcli fw-control identify` 能通，就以为设备空闲 | 那不是这个检查。`fw-control identify` 开的是 control handle 而不是 VDevice，对完全被占用的设备照样成功。真正的判据是能否打开 VDevice，部署步骤用读 `/proc/*/fd` 来近似。 |
| 检测器报 `HAILO_OUT_OF_PHYSICAL_DEVICES(74)` 退出 | 同上，只是从容器内部看到的表现。 |
| 部署报成功，但检测器表现得像旧版本 | 板卡上已存在同名镜像时部署会跳过拉取，所以重新发布同一个 tag 不会到达拉过一次的板卡。先看板上实际是哪个：`docker image inspect <image> -f '{{.Id}}'`，和 registry 对一下，重新部署前先 `docker pull`。 |
| 部署停在「No hailort cp311 wheel found」 | 从 Hailo developer zone 下载与已装驱动同版本的 wheel，放在家目录下。它不在公开源上，这也是镜像不内置它的原因。 |
| 检测器打印完整结果后进程以 139 或 135 退出 | 已在发布镜像中修复。若你在跑更早的构建，原因是 teardown 先释放了设备、后析构它的 Python wrapper。 |
| 设备页显示 `decode: "sw"` | 该板卡上这是正确状态，不是降级。见上方说明。 |
| 检测器在跑但 hub 一直不列出它 | broker 在同一套栈里，`config/detector.yaml` 里的 `mqtt_host` 应为 `mosquitto`。检测器每 30 秒上报一次状态，等一个周期再下结论。 |
| hub 在 8090 上没响应 | `docker compose logs hub`。通常是板卡上该端口已被占用。 |

### 部署目标 {#hailo_board type=remote device_name="Hailo 板卡" config=devices/hailo_detector.yaml default=true}

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_hailo type=web_dashboard required=true config=devices/hailo_dashboard.yaml}

在板卡上打开工作台，画出第一条规则。

### 部署完成

板卡正在本地做人体检测和规则判定。工作台地址是 `http://<板卡地址>:8090`。

#### 首次登录

hub 首次启动会生成随机密码，并在首次登录时强制修改。部署步骤会打印出来；若输出被截断，
在板卡上执行 `docker exec edge_security_hailo-hub-1 cat /data/initial-password.txt`
取回——第一行是用户名，第二行是密码。

#### 画出第一条规则

打开 **Rules**，选中这块板卡的摄像头，在 hub 从检测器代理过来的实时画面上作图。
多边形是禁区，线段是越线，箭头指向规则判为 forward 的方向。规则按归一化坐标保存，
换分辨率仍然成立——但摄像头不能移动，因为边界是画在这个机位的画面上的。

#### 上报的内容

检测结果发到 `sensecraft/security/<device_id>/detections/<stream_id>`，hub 的判定结果
发到 `.../events/<stream_id>`，retained 的在线状态发到 `.../status`。检测框按**原始画面**
归一化，而不是模型看到的 letterbox 画面，所以订阅方不需要知道模型输入尺寸。

#### 增加第二路摄像头

加速器还有余量——检测器的吞吐远高于 5 fps 的源——但每加一路也会多一份 CPU 上的
H.264 软解，而软解正是这块板卡上最先耗尽的东西。先加一路，在设备页上观察检测器的
CPU 数字，有余量再加下一路。

### 故障排查

| 问题 | 解决办法 |
|------|----------|
| 规则编辑器里实时画面加载不出来 | 底图由 hub 从检测器的预览接口代理而来。检查 `config/detector.yaml` 里的 `preview_advertise_host` 是板卡的局域网地址，而不是 `127.0.0.1`。 |
| 告警到了但没有快照 | 检测器通过 MQTT 响应快照请求。如果 broker 重启过，等一个状态周期让检测器重连。 |

## 套餐: 共享 Hub（可选扩展） {#hub_only}

这不是本方案的常规部署路径。Jetson 与 RK3588 两个套餐各自在一台机器上跑完 broker、
hub 和检测器，都不需要在这里装任何东西。

只有当你已经有多台检测设备在跑、希望它们共用一份告警列表时才用这个套餐。它在一台常开
机器上装 broker、规则引擎和告警工作台，本机不带检测器——hub 只根据检测器发来的 JSON
判定规则，实测在同时还跑着检测器的 RK3588 板卡上占单核 3.7%、RSS 52.8 MB。

部署完之后，把每台检测器 `config/detector.yaml` 里的 `mqtt_host` 从 `mosquitto` 改成
这台机器的地址，再重启该检测器。

## 步骤 1: 部署 Hub {#deploy_edge_security_hub_only type=docker_deploy required=true config=devices/hub_stack.yaml}

填入这台机器的地址，安装并启动 broker 与 hub。

### 前置条件

- 一台常开的 arm64 或 x86_64 机器，装有 Docker。
- 8090 与 1883 端口空闲。任一被占用时部署步骤会给出提示。
- 约 3 GB 空闲磁盘。告警数据库和快照文件会随告警量增长。

### 检查内容

- 最后一步会打印 `/api/health`；若是首次启动，还会从 hub 日志里打印管理员登录信息。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 8090 无响应 | 执行 `docker compose logs hub`，通常是端口冲突。 |
| 检测器反复连上又掉线 | 两个 hub 进程用了同一个 MQTT client id 会互相踢下线并循环。`GET /api/health` 会给出正在使用的 id；一个 broker 只跑一个 hub。 |
| 只出了最初几条告警之后就不再出 | 看 `/api/health` 里的 `handler_errors`。这个数不为零且在涨，说明消息是在 hub 内部被丢掉的，而不是根本没到。 |

### 部署目标 {#hub_host_machine type=remote device_name="Hub Host" config=devices/hub_stack.yaml default=true}

### 部署目标 {#hub_local type=local config=devices/hub_stack.yaml}

在本机运行 Hub —— 也就是跑 SenseCraft Solution 的这台。Hub 与 broker 都是
不依赖加速器的普通容器，不用另配机器、也不用配 SSH。其他板子上的检测器
照样通过 MQTT 汇报。

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_hub_only type=web_dashboard required=true config=devices/hub_dashboard.yaml}

登录并改密；在检测器接入之前，设备列表是空的。

### 部署完成

汇聚层已经运行，正在 1883 端口等待检测器接入。

#### 首次登录

1. 工作台地址是 `http://<机器地址>:8090`。
2. 用户名 `admin`，密码用部署步骤打印出来的那个——hub 首次启动生成随机密码，没有固定
   默认值。它也在 hub 容器里的 `/data/initial-password.txt`。按提示设置新密码。
3. **设备**页是空的。在有检测器指向这台机器之前，这是正常状态。

#### 接入检测器

在每台检测设备上编辑 compose 文件旁边的 `config/detector.yaml`，把 `mqtt_host` 改成
这台机器的地址，再执行 `docker compose up -d detector`。那台设备上原有的 broker 留着
也无妨，只是不再有人订阅它。任何按公开契约发送报文的设备都能以同样方式接入——hub 消费的是报文契约，不是某个具体产品。
带跟踪编号的检测器由 hub 判规则；自己判规则的设备直接发成品事件，hub 只做记录，不再
重复判定。

#### 数据存放位置

告警数据库、快照文件和规则配置都在 compose 文件旁边的 `data/` 目录里。要备份的是这个
目录，不是容器。

#### 预留扩展

reCamera 的探测节点尚未构建。报文契约已经公开，之后新增探测节点不需要改动这台机器上的
任何东西。Jetson、RK3588 和 Hailo 的检测器目前都能汇入这里。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 检测器在线离线来回跳 | 每台检测器要有自己的名字。两台检测器共用一个身份会争抢同一个 retained 状态主题。 |
| 告警没有缩略图 | 告警触发时 hub 会向检测器索取快照。检测器答不上来时，告警仍然记录，只是没有图。 |
| 各站点时钟不一致导致排序混乱 | 滞留计时、冷却和排序一律用 hub 自己的时钟。设备时间戳只用于展示和取证，检测器时钟不准不会影响规则判定。 |
