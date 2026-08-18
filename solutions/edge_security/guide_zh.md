## 套餐: Jetson 单机部署 {#jetson_hub}

一台 Jetson 跑完整套：MQTT broker、带告警工作台的汇聚 hub，以及一个看单路摄像头的
CPU 检测器。不需要第二台机器。

这里的检测器跑在 CPU 上的 ONNX Runtime，本项目还没有 TensorRT 检测路径，因此
Jetson 的 GPU 没有被使用——这块板子在这里的角色是一台核数够用的安静 arm64 机器。
一路 720p、15 fps 的摄像头大约要占 2.5 个核。

## 步骤 1: 部署安防服务栈 {#deploy_edge_security_jetson_hub type=docker_deploy required=true config=devices/jetson_hub_stack.yaml}

填入这台机器的地址和摄像头 RTSP 地址，安装并启动三个容器。

### 前置条件

- 目标机器上装有 Docker 及 compose 插件。若只有独立版 `docker-compose`，部署步骤
  会自动补上插件。
- 摄像头的 RTSP 地址，先用 VLC 测通。路径或用户名密码写错是最常见的失败原因，
  现象和部署失败完全一样。
- 8090（工作台）、1883（broker）、8099（摄像头预览）三个端口空闲。
- 约 5 GB 空闲磁盘，用于镜像和告警数据库。

### 检查内容

- 最后一步会打印 hub 的 `/api/health` 返回，`mqtt_connected` 必须为 true。
- 若是首次启动，同一步还会从 hub 日志里打印出管理员登录信息。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 8090 无响应 | 执行 `docker compose logs hub`，通常是端口被占用。 |
| detector 容器反复重启 | 执行 `docker compose logs detector`，通常是 RTSP 地址不通；在同一台机器上用 VLC 验证。 |
| 工作台里看不到设备 | 检测器每 30 秒上报一次状态，等一个周期；再确认 `config/detector.yaml` 里的 `mqtt_host` 是 `mosquitto`。 |
| 一个人站着不动却连续报警两次 | 检测器跟不上视频流，跟踪目标被回收后换了新的 track id，等于又"进"了一次区域。调大推理线程数，或把摄像头降到更低分辨率。 |

### 部署目标 {#jetson_hub_host type=remote device_name="reComputer J" config=devices/jetson_hub_stack.yaml default=true}

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_jetson_hub type=web_dashboard required=true config=devices/jetson_hub_dashboard.yaml}

登录、画一条边界，走过去看第一条告警。

### 部署完成

broker、hub 和一个检测器已经在你选的机器上运行。

#### 首次登录

1. 工作台地址是 `http://<机器地址>:8090`。
2. 用 `admin` / `admin` 登录。hub 会在首次登录时强制改密，新密码用 bcrypt 哈希存储。
3. 打开**设备**页。检测器应显示为在线，解码方式为 `sw`——这个套餐用 CPU 解码，
   `sw` 在这里是正确的。

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

把 NVR、PLC 网关或你自己的告警服务连到 1883 端口订阅事件主题，不必轮询接口。

#### 增加第二路摄像头

一个检测器容器对应一路摄像头。第二路摄像头需要第二个检测器——可以在这台机器上再起
一个容器并给它另一个 `device_id`，也可以用 RK3588 套餐上一块独立板卡。实测过的最大
规模是两路并发，超出部分属于未验证范围。

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
两路实时流时只占单核 1.4%、44.9 MB 内存。

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

1. 用 `admin` / `admin` 登录，按提示设置新密码。
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

## 套餐: 共享 Hub（可选扩展） {#hub_only}

这不是本方案的常规部署路径。Jetson 与 RK3588 两个套餐各自在一台机器上跑完 broker、
hub 和检测器，都不需要在这里装任何东西。

只有当你已经有多台检测设备在跑、希望它们共用一份告警列表时才用这个套餐。它在一台常开
机器上装 broker、规则引擎和告警工作台，本机不带检测器——hub 只根据检测器发来的 JSON
判定规则，实测在承载两路实时流时占 1.4% CPU、44.9 MB 内存。

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

## 步骤 2: 打开告警工作台 {#dashboard_edge_security_hub_only type=web_dashboard required=true config=devices/hub_dashboard.yaml}

登录并改密；在检测器接入之前，设备列表是空的。

### 部署完成

汇聚层已经运行，正在 1883 端口等待检测器接入。

#### 首次登录

1. 工作台地址是 `http://<机器地址>:8090`。
2. 用 `admin` / `admin` 登录，按提示设置新密码。
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

reCamera 和 Hailo 的探测节点尚未构建。报文契约已经公开，之后新增探测节点不需要改动
这台机器上的任何东西。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 检测器在线离线来回跳 | 每台检测器要有自己的名字。两台检测器共用一个身份会争抢同一个 retained 状态主题。 |
| 告警没有缩略图 | 告警触发时 hub 会向检测器索取快照。检测器答不上来时，告警仍然记录，只是没有图。 |
| 各站点时钟不一致导致排序混乱 | 滞留计时、冷却和排序一律用 hub 自己的时钟。设备时间戳只用于展示和取证，检测器时钟不准不会影响规则判定。 |
