## 套餐: reCamera 2002 {#recamera}

一台设备把事情做完：摄像头看着房间，在设备本地判断有没有人摔倒，并通过 MQTT 把
事件发出去。

| 设备 | 作用 |
|--------|---------|
| reCamera 2002 | 姿态估计、时序跌倒判定、RTSP 与 MQTT，全部本地完成 |

**重要提示：** 这是一个辅助告警，不是经过认证的医疗或人身安全系统。在未
被读过的 27 段 Subject 4 测试集上，准确率 74.1%、跌倒召回 83.3%；在一个独立外部
数据集上召回为 58.8%。远景、遮挡、低光以及看起来像跌倒的地面动作仍是弱项。

## 步骤 1: 更新 reCamera 控制台 {#update_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.5 控制台，它负责管理相机应用。已经是该版本会自动跳过。

### 前置条件

1. 用 USB 连接 reCamera，或让它和这台电脑处于同一网络。
2. USB 连接的地址是 `192.168.42.1`；走 Wi-Fi 时用路由器上显示的 IP。
3. 默认密码是 `recamera`（较早期的设备用 `recamera.2`）。
4. 如果控制台已经是 0.5.5，不会重装——版本会在动任何东西之前先检查，该步骤会直接标记为跳过。
5. 相机应用画廊里的跌倒检测开关由控制台提供，视觉应用之间的切换也由它负责，所以下一步之前它必须是新版本。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 连不上 | 确认设备已开启 SSH，IP 和密码填写正确 |
| 装完后控制台页面打不开 | 等待 30 秒让它重启，然后重新加载 `http://<摄像头 IP>/` |
| 密码被拒绝 | 试试 `recamera.2`，出厂固件较早的设备用这个密码 |

---

## 步骤 2: 安装跌倒检测 {#deploy_recamera_fall type=recamera_cpp required=true config=devices/recamera_fall.yaml}

安装姿态模型和跌倒检测应用，并在相机上启动它。

### 接线

![机位示意：2–3 m 的侧向或斜角机位可用；垂直俯拍、远景和被遮挡的机位不可用。](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/camera-placement-be3fb598.svg)

1. 把摄像头固定安装，让它能完整、开阔地看到要覆盖的区域。
2. 在可能发生跌倒的路径上，保证整个人体——尤其是肩部和髋部——始终可见。
3. 优先用侧向或斜角俯视地面区域的机位，不要垂直向下拍。
4. 对着通行区域，不要主要对着床或健身区域——除非你单独验证过，那里的日常地面动作会被当成跌倒。
5. 它检测的是倒地这个过程，不是倒地后的结果：如果启动时人已经躺着，它会报告姿态但不会产生事件。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 服务启动后立刻退出 | 还有别的相机应用在占用摄像头；同一时间只能有一个程序占用，重启设备后重试 |
| 装完后 Node-RED 不工作了 | 属于预期——安装会把摄像头从 Node-RED 和其他视觉应用手里接管过来 |
| 跌倒漏报 | 拉大视野、改善照明，保证倒地前后肩部和髋部都可见 |
| 做俯卧撑触发告警 | 这是已知的类跌倒动作，换个机位或在下游加人工确认 |
| 收不到 MQTT 消息 | 确认电脑能访问 1883 端口，主题为 `recamera/fall-detection/results` |

---

## 步骤 3: 查看跌倒状态 {#preview_recamera_fall type=preview required=false config=devices/preview_recamera_fall.yaml}

点击 **连接**，实时看到骨架、当前状态和事件编号。

### 部署完成

设备已经可以进入有人值守的现场试运行。告警和诊断数据发往
`recamera/fall-detection/results`，Home Assistant 自动发现会暴露跌倒状态、事件
编号和有人存在。

#### 快速验证

1. 点击 **连接**，等待视频出现。
2. 走进画面——骨架应当跟随你移动，状态卡显示 `NORMAL`。
3. 有意识地躺到地面上。大约两秒内状态卡应当变红，并显示一个新的事件编号。

#### 下一步

- 把摄像头接入 Home Assistant——只要 broker 是共享的，实体会自动出现。
- 在启用任何通知流程之前，用有代表性的跌倒动作和日常动作做一次现场验收测试。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 叠加层比视频先出现 | MQTT 比 RTSP 连得快，等几秒即可 |
| 人贴近地面时骨架消失 | 重新构图；落地后的短暂遮挡可以容忍，长时间遮挡无法判定 |
| 完全没有叠加层 | 确认 1883 端口可达，且主题填写一致 |

---

## 套餐: reCamera Pro {#recamera_pro}

一台设备搞定全部，硬件比 2002 更新：摄像头看住房间，在设备本地判断有没有人摔倒，然后
把事件通过 MQTT 发出去。

| 设备 | 作用 |
|--------|------|
| reCamera Pro | 姿态估计、多人跟踪、时序跌倒判定与 MQTT，全部本地完成 |

**重要提示：** 这是辅助告警，不是经过认证的医疗或人身安全系统。远景、遮挡、弱光以及
类似跌倒的地面活动仍是薄弱场景。

检测器随设备自己的应用中心分发，不随本方案下发，所以这个套餐做的是**配置已安装的应用
并把它设为运行中的应用**。如果你的设备上还没有，请先在应用中心安装——部署步骤会提示你，
并列出设备上已装的应用。

## 步骤 1: 更新摄像头固件 {#firmware_recamera_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

只需做一次，而且只在摄像头还没有应用中心时才需要。

![设备管理 → 嵌入式 → reCamera Pro，展开后可填写地址与 ADB 端口](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/recamera-pro-firmware-update-a9539b3d.gif)

### 检查内容

- 先打开摄像头页面——如果已经能看到**应用中心**且里面有 Fall Detection，这一步就不用做，直接跳过。
- 在本应用里：**设备管理 → 嵌入式 → reCamera Pro**，填写摄像头地址，然后点**检查更新设备**。
- 它通过 **ADB 5555 端口**连接摄像头，不是 SSH，所以摄像头必须在网络上，仅用 USB 连接不够。
- 更新过程会重启摄像头，需要几分钟，中途不要断电。
- 它会保留出厂文件备份，同一页的**恢复出厂设置**可以回滚。

### 故障排查

| 现象 | 处理 |
|------|------|
| 测试连接失败 | 检查地址，以及这台电脑能否访问摄像头的 5555 端口 |
| 点了检查更新设备没反应 | 可能已经是最新——去摄像头页面看有没有应用中心 |
| 更新后仍没有应用中心 | 刷新页面，摄像头重启后需要一点时间 |

## 步骤 2: 配置跌倒检测 {#deploy_recamera_pro_fall type=recamera_pro_app required=true config=devices/recamera_pro_fall.yaml}

把应用指向你的 MQTT 服务器，并将其设为运行中的应用。

### 检查内容

- 设备**同一时刻只运行一个应用**，激活这个会停掉当前正在运行的那个。
- **MQTT 是可选的。** broker 地址留空就在设备自带页面看结果；填了才会把事件转发到 Home Assistant。这台摄像头不自带 broker，和 2002 不同。
- 凭据是**网页控制台**的账号密码，不是 SSH。

### 故障排查

| 现象 | 处理 |
|------|------|
| 提示应用未安装 | 先在设备的应用中心安装 Fall Detection，再重新执行本步 |
| 登录被拒 | 连续失败会按 IP 递增锁定，重试前先在控制台确认密码 |
| MQTT 收不到消息 | 确认 broker 地址**从摄像头**可达，而不只是从你的电脑可达。如果留空了，结果只出现在设备页面，这是预期行为 |

### 部署目标 {#recamera_pro_device type=remote device_name="reCamera Pro" config=devices/recamera_pro_fall.yaml}

## 步骤 3: 查看跌倒状态 {#verify_recamera_pro_fall type=web_dashboard required=false config=devices/verify_recamera_pro_fall.yaml}

打开设备控制台，让人在摄像头前走动，观察实时画面。

### 部署完成

摄像头现在会把跌倒事件发到你的 broker。

#### 发出的内容

| 主题 | 内容 |
|---|---|
| `<设备名>/fall-detection/summary` | `person_count`、`fallen_count` |
| `<设备名>/fall-detection/fall` | 状态跃迁时的 `fall_event` |

与其他套餐不同，这里是**映射后的摘要**而非每帧完整文档——Home Assistant 需要的正是这些
字段，但其中不含骨架数据；带骨架的实时画面在控制台自己的页面上，由本步骤打开。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 摄像头页面打不开 | 固件有 HTTPS 开关，80 端口会重定向到 443。跟随跳转，或直接用 `https://` 地址打开 |
| 实时画面正常但 broker 收不到跌倒事件 | 检查上一步填的 broker 地址和端口；summary 主题要检测到人之后才会出现 |
| 应用中心里有 Fall Detection 但启动不了 | 缺 AI 模型。在摄像头的应用中心里重新安装一次——安装时会连模型一起下载 |
| 贴近地面时漏检 | 调整摄像头取景；倒地后的短暂遮挡可以容忍，长时间遮挡无法判定 |

### 部署目标 {#recamera_pro_verify type=remote device_name="reCamera Pro" config=devices/verify_recamera_pro_fall.yaml}

## 套餐: IP 摄像头 + reComputer J {#jetson}

保留你现有的摄像头。由 Jetson Orin 拉取它们的 RTSP 流，运行更大的姿态模型，并对
每一路里的多个人独立跟踪。

| 设备 | 作用 |
|--------|---------|
| reComputer J30 / J40 | 为每一路视频做姿态推理、跟踪、跌倒判定和 MQTT 输出 |
| IP 摄像头 | 提供 RTSP 视频，任何支持 ONVIF 或 RTSP 的摄像头都可以 |

**重要提示：** 这是一个辅助告警，不是经过认证的医疗或人身安全系统。在未
被读过的 27 段 Subject 4 测试集上，YOLO11m 配置的准确率为 85.2%、跌倒召回 100%；
在一个独立外部数据集上，部署版召回为 52.9%，瓶颈是远景和遮挡下的姿态覆盖率。

## 步骤 1: 部署跌倒检测 {#deploy_jetson_fall type=docker_deploy required=true config=devices/jetson_fall.yaml}

在 Jetson 上部署检测器并构建推理引擎，预计需要 10–20 分钟。

### 前置条件

1. Jetson 运行 JetPack 6.x，且 NVIDIA 容器运行时可用。
2. 至少 10 GB 空闲磁盘——姿态模型和构建出来的引擎都存在设备上。
3. 准备好 IP 摄像头的 RTSP 地址，需要认证的话要带上用户名密码，例如
   `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`。
4. 首次部署的时间大部分花在设备上构建推理引擎。TensorRT 引擎和 GPU 架构、TensorRT 版本严格绑定，无法预先打包分发。Orin Nano 实测：YOLO11s 耗时 461 秒。之后的部署会复用它。
5. 按板子选姿态模型——Orin Nano 用 **YOLO11s**，Orin NX 用 **YOLO11m**。方案介绍页表格里更准的一行是 YOLO11m；YOLO11s 给额外的摄像头路数留了更多余量。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 引擎构建失败 | 确认 `/usr/src/tensorrt/bin/trtexec` 存在，且磁盘有 10 GB 空闲 |
| 收不到摄像头画面 | 先用 VLC 测试 RTSP 地址，绝大多数问题是路径或用户名密码写错 |
| 容器反复重启 | 查看日志里的引擎路径；上次中断留下的半成品引擎必须删掉 |
| 部署时连不上 | 确认 SSH 可达且用户名正确——Seeed 镜像通常是 `recomputer` 或 `nvidia` |

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_fall.yaml default=true}

从这台电脑通过 SSH 部署到 Jetson。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_fall.yaml}

如果你就在 Jetson 上操作，直接在本机运行。

---

## 步骤 2: 查看跌倒状态 {#preview_jetson_fall type=preview required=false config=devices/preview_jetson_fall.yaml}

点击 **连接**，每个被跟踪的人都会有独立的框、编号和状态颜色。

### 部署完成

Jetson 已经可以进入有人值守的现场试运行。结果发往
`recamera/fall-detection/results/<流编号>`，一路摄像头一个主题，下游可以分开处理。

#### 快速验证

1. 点击 **连接**，等待摄像头画面出现。
2. 走进画面——应当有一个框跟随你，标注着跟踪编号和 `NORMAL`。
3. 有意识地躺下。框应当变红，状态卡显示一个新的事件编号。

#### 增加更多摄像头

检测器可以同时处理多路视频。在设备上的配置文件里往 `streams` 列表中添加，然后重启
容器即可；每一路各自维护跟踪状态，并有自己的 MQTT 主题。

#### 下一步

- 把告警系统指向 MQTT 主题，或把 broker 接入 Home Assistant 以获取自动发现实体。
- 增加路数前先实测真实吞吐——公布的 FPS 数字只是推理内核部分，不含解码、跟踪和 MQTT。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 有视频但没有叠加层 | 预览是单独读 MQTT 的，确认 Jetson 的 1883 端口可达 |
| 有叠加层但没有视频 | 预览直接从摄像头拉 RTSP，确认这台电脑也能访问摄像头 |
| 框在不同人之间跳变 | 调高跟踪器的 IoU 阈值，或调整机位减少人物重叠 |

---

## 套餐: IP 摄像头 + reComputer RK {#rk}

把检测器跑在瑞芯微 NPU 板卡上。算法和 MQTT 输出与其他套餐一致，只是用板卡自带的
NPU 代替 GPU。

| 设备 | 作用 |
|--------|---------|
| reComputer RK3576 / RK3588 | 在 NPU 上做姿态推理、跟踪、跌倒判定和 MQTT 输出 |
| IP 摄像头 | 提供 RTSP 视频，任何支持 ONVIF 或 RTSP 的摄像头都可以 |

**重要提示：** 这是一个辅助告警，不是经过认证的医疗或人身安全系统。每块板卡都使用在自己姿态轨迹上训练并冻结的时序权重。准确率在方案介绍页按整体给出——
27 段测试集分不出平台差异，按板卡分别列数字会把没测出来的差别说成差别。

## 步骤 1: 部署跌倒检测 {#deploy_rk_fall type=docker_deploy required=true config=devices/rk3588_fall.yaml}

把检测器部署到你的瑞芯微板卡，预计需要 5 分钟左右。

### 前置条件

1. 板卡运行厂商系统镜像，NPU 驱动和 `librknnrt.so` 已就位，并且装有 Docker。
2. 至少 6 GB 空闲磁盘，用于运行时镜像和姿态模型。
3. 准备好 IP 摄像头的 RTSP 地址，需要认证的话带上用户名密码。
4. 选择与你板卡一致的部署目标。为 RK3588 编译的模型不能在 RK3576 上运行，反之亦然，部署目标决定下载哪个模型，不是摆设。
5. 实测吞吐（板卡上其他业务未停）：RK3588 单上下文空白帧 19.3 FPS，走 RTSP 端到端约 8.6 FPS；RK3576 真实测试图 15.2 FPS，端到端约 4.9 FPS。这些是受资源竞争影响的数字，不是板卡上限。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 提示找不到 `librknnrt.so` | 安装板卡的 `rknpu2` 运行时包；容器特意挂载宿主机的这份库 |
| 模型加载失败 | 模型必须与板卡匹配，选对板卡型号后重新执行这一步 |
| 收不到摄像头画面 | 先用 VLC 测试 RTSP 地址，绝大多数问题是路径或用户名密码写错 |
| 帧率偏低 | 其他 NPU 业务在抢占加速器，先看看板卡上还跑着什么 |

### 部署目标 {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_fall.yaml default=true}

### 部署目标 {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_fall.yaml}

### 部署目标 {#rk_local type=local device=rk3588 device_name="reComputer RK" config=devices/rk_auto_fall.yaml}

---

## 步骤 2: 查看跌倒状态 {#preview_rk_fall type=preview required=false config=devices/preview_rk_fall.yaml}

点击 **连接**，每个被跟踪的人都会有独立的框、编号和状态颜色。

### 部署完成

板卡正在向 `recamera/fall-detection/results/<流编号>` 发布结果，一路摄像头一个主题。

#### 快速验证

1. 点击 **连接**，等待摄像头画面出现。
2. 走进画面——应当有一个框跟随你，并标注跟踪编号。
3. 有意识地躺下。框应当变红，状态卡显示一个新的事件编号。

#### 下一步

- 把告警系统指向 MQTT 主题，或把 broker 接入 Home Assistant。
- 正式使用前请自己做验收测试——冻结的那个数字测的是时序门限，不是自动化实际收到的告警。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 有视频但没有叠加层 | 预览是单独读 MQTT 的，确认板卡的 1883 端口可达 |
| 骨架和人物错位 | 请反馈——该运行时输出的是letterbox 模型空间坐标，预览会做还原 |
| 框在不同人之间跳变 | 调高跟踪器的 IoU 阈值，或调整机位减少人物重叠 |

---

## 套餐: IP 摄像头 + reComputer R（Hailo） {#hailo}

把检测器跑在 Hailo-8 加速器上。热路径是原生 C++，不含 Python，宿主 CPU 占用很低。

| 设备 | 作用 |
|--------|---------|
| 带 Hailo-8 的 reComputer R | 在 Hailo-8 上做姿态推理、跟踪、跌倒判定和 MQTT 输出 |
| IP 摄像头 | 提供 RTSP 视频，任何支持 ONVIF 或 RTSP 的摄像头都可以 |

**重要提示：** 这是一个辅助告警，不是经过认证的医疗或人身安全系统。Hailo 专属的时序权重已经冻结，在留出测试集上的姿态覆盖率为 92.02%。准确率在方案介绍页
按整体给出——27 段测试集分不出平台差异。

## 步骤 1: 部署跌倒检测 {#deploy_hailo_fall type=docker_deploy required=true config=devices/hailo_fall.yaml}

把检测器部署到带 Hailo 的设备，预计需要 5 分钟左右。

### 前置条件

1. 设备上有 Hailo-8 加速器（`/dev/hailo0`），且安装的是 **HailoRT 4.21**——GStreamer 插件、用户态库和内核驱动必须是同一个版本。
2. 装有 Docker，至少 4 GB 空闲磁盘。
3. 准备好 IP 摄像头的 RTSP 地址，需要认证的话带上用户名密码。
4. 姿态模型会在部署过程中从 Hailo 官方 Model Zoo 下载，并校验固定的摘要，不需要手工准备。
5. 不能有别的程序占用加速器——HailoRT 的上下文是独占的，先停掉其他 Hailo 应用。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 找不到 `/dev/hailo0` | 加速器没插好或驱动没加载，用 `hailortcli fw-control identify` 检查 |
| 找不到 `libhailort.so.4.21.0` | 本部署锁定 HailoRT 4.21；要升级就得同时换插件、库和驱动 |
| 容器启动后退出 | 有别的进程占着加速器，HailoRT 上下文是独占的 |
| 收不到摄像头画面 | 先用 VLC 测试 RTSP 地址，绝大多数问题是路径或用户名密码写错 |
| 部署在验证阶段停止 | 检查检测器日志中的 `HAILO_BATCH` 行、容器健康状态和配置主题上的 MQTT 结果 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="reComputer R" config=devices/hailo_fall.yaml default=true}

从这台电脑通过 SSH 部署到设备。

### 部署目标 {#hailo_local type=local device=hailo device_name="reComputer R" config=devices/hailo_fall.yaml}

如果你就在该设备上操作，直接在本机运行。

---

## 步骤 2: 查看跌倒状态 {#preview_hailo_fall type=preview required=false config=devices/preview_hailo_fall.yaml}

点击 **连接**，每个被跟踪的人都会有独立的框、编号和状态颜色。

### 部署完成

设备正在向 `recamera/fall-detection/results/<流编号>` 发布结果，一路摄像头一个主题。

#### 快速验证

1. 点击 **连接**，等待摄像头画面出现。
2. 走进画面——应当有一个框跟随你，并标注跟踪编号。
3. 有意识地躺下。框应当变红，状态卡显示一个新的事件编号。

#### 下一步

- 把告警系统指向 MQTT 主题，或把 broker 接入 Home Assistant。
- 正式使用前请自己做验收测试——冻结的那个数字测的是时序门限，不是自动化实际收到的告警。

### 故障排查

| 问题 | 处理方法 |
|-------|----------|
| 有视频但没有叠加层 | 预览是单独读 MQTT 的，确认设备的 1883 端口可达 |
| 有叠加层但没有视频 | 预览直接从摄像头拉 RTSP，确认这台电脑也能访问摄像头 |
| `inference_time_ms` 显示 0 | 属于预期——Hailo 的 GStreamer 元件在该探测点不暴露加速器调用耗时 |
