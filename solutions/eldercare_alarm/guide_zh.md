## 套餐: IP 摄像头 + reComputer J（Orin） {#orin}

所有东西放在一台 Jetson 上：EdgeFallKit 检测器、告警服务、MQTT broker 与确认页面。
代价是部署时间——首次运行要在设备上构建 TensorRT 引擎，需要好几分钟，这也是这个套餐的超时
预算是一小时而不是几分钟的原因。

| 设备 | 用途 |
|---|---|
| reComputer J30 / J40（Orin） | 运行检测器、告警服务、broker 与确认页面 |
| IP 摄像头 | 提供检测器观察的 RTSP 画面 |

**重要提示**

本系统不是医疗器械，也不是经过认证的紧急响应产品。它不用于诊断、治疗，也不替代护理人员的
判断。告警只是提示，处置责任在人。

已知弱点，在这里比准确率那张表更值得先看：跌倒必须发生在画面里才可能被看见，检测器启动时
已经躺在地上的人只会被报成一个姿态而不产生事件。远景、家具重度遮挡、低光都会降低检出。
区域是画面上的归一化矩形，重新对准摄像头会在无声无息中让它们失效。而 `no_motion` 告警在
睡眠时段一定会触发，除非区域排除床位或超时长于一次午睡。

开始之前还有一件事：告警服务镜像尚未发布，见下面的前置条件。

## 步骤 1: 部署告警栈 {#deploy_orin_alarm type=docker_deploy required=true config=devices/orin_alarm.yaml}

填好设备、摄像头、区域与超时。这一步会上传 compose 栈、下载并校验姿态模型、构建 TensorRT
引擎、按你填的值写好两个配置文件，然后一直等到真的收到一条检测器消息、并且告警 API 能应答，
才报成功。

### 前置条件

- JetPack 6.x，且 Docker 已配置 NVIDIA container runtime。若
  `docker info | grep -i nvidia` 没有输出，执行
  `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`。
- 已安装 TensorRT 开发包——这一步需要 `/usr/src/tensorrt/bin/trtexec`。
- 至少 10 GB 可用空间。
- 摄像头的 RTSP 地址，先用 VLC 测通。
- **`eldercare-alarm-arm64:0.1.0` 镜像还不在 registry 里。** 在设备上或在能推送的机器上，
  从上游项目构建并打成 compose 文件期望的 tag：
  `docker build -f docker/Dockerfile -t sensecraft-missionpack.seeed.cn/solution/eldercare-alarm-arm64:0.1.0 .`
  没有它，`eldercare-alarm` 服务拉不到镜像，部署会失败。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `This target is not a NVIDIA Jetson` | 地址指到了别的机器。核对 IP 与 SSH 用户名。 |
| `trtexec not found` | 从 JetPack SDK 组件里安装 TensorRT 开发包。 |
| 引擎构建超时 | YOLO11m 比 YOLO11s 慢不少。重跑一次部署——ONNX 文件与时序缓存都保留着，第二次快得多。 |
| `eldercare-alarm-arm64` 报 `pull access denied` | 在该镜像构建或推送之前属预期现象，见前置条件。 |
| 验证阶段报 `No detector result` | 检测器没看到摄像头。先在 Jetson 上用 VLC 测 RTSP 地址，再看 `docker logs eldercare_alarm_orin-fall-detection-1`。 |
| 验证阶段卡在告警 API | `docker logs eldercare_alarm_orin-eldercare-alarm-1` 会指出它拒绝的配置项。生成的文件是部署目录下的 `config/eldercare.yaml`。 |
| 现场无事时始终没有告警 | 这是预期——超时就是为此存在的。要验证链路，把无人超时改成 1 分钟、重新部署，然后离开房间。 |

### 部署目标 {#orin_remote type=remote device=orin device_name="reComputer J" config=devices/orin_alarm.yaml default=true}

通过 SSH 部署到网络上的 Jetson。这是常规做法：应用跑在你的笔记本上，栈装到设备上。

### 部署目标 {#orin_local type=local device=orin device_name="reComputer J" config=devices/orin_alarm.yaml}

直接在 Jetson 上部署，适用于应用就跑在将要承载告警服务的这台机器上的情况。

## 步骤 2: 打开确认页面 {#verify_orin_alarm type=web_dashboard required=false config=devices/confirm_ui.yaml}

填 Jetson 的地址与 8080 端口，页面会在浏览器里打开。

### 部署完成

检测器在发布，告警服务在消费，而这个控制台就是人对结果做处置的地方。

#### 快速验证

1. 页面能打开并显示告警列表。现场无事时列表为空是正确结果——说明服务已起来并能应答。
2. 在 Jetson 上订阅检测器，确认消息在流动：
   `docker exec eldercare_alarm_orin-mosquitto-1 mosquitto_sub -h 127.0.0.1 -t '#' -v -C 5`。
3. 强制造一条告警：在设备上改 `config/eldercare.yaml`，把该区域的
   `no_person_timeout_sec` 改成 60，执行 `docker compose restart eldercare-alarm`，
   让区域空置一分钟，刷新页面。验证完把原值改回去。
4. 在页面上确认这条告警。若配了 webhook，检查接收端收到一次 POST，负载里有操作者名字、
   且不含任何媒体。

#### 下一步

- 若一台摄像头覆盖多个区域，把那个覆盖整幅画面的区域拆成按房间的矩形，并把每个区域绑到
  对应的流编号上。
- 把 `notifiers` 指向真正应该接收告警的系统，并保留幂等键请求头——重试之所以安全就靠它。
- 设备能被局域网以外访问之前，先给 broker 加上账号密码与 TLS。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 页面打不开 | 8080 端口可能被 Jetson 上别的东西占了。看 `docker compose ps` 与容器日志。 |
| 页面能开但列表永远为空 | 要么还没有任何东西超时，要么订阅主题与检测器实际发布的不一致。把 `config/eldercare.yaml` 里的 `mqtt.subscriptions` 与实时的 `mosquitto_sub -t '#' -v` 对一下。 |
| 有告警但 webhook 没收到 | 看这条告警的状态。`escalated` 表示送达超期；重试仍每 30 s 进行，状态刻意保持 `escalated`。 |
| 房间里明明有人却报了 `no_person` | 人在区域矩形之外，或者被遮挡了。对着实时画面重新核对区域。 |

## 套餐: IP 摄像头 + reComputer R（Hailo） {#hailo}

同一套栈跑在 Hailo-8 加速器上。检测器热路径为原生 C++，姿态模型是预编译好的 HEF，
因此不需要在设备上构建引擎，部署耗时是几分钟而不是几十分钟。

| 设备 | 用途 |
|---|---|
| 带 Hailo-8 的 reComputer R | 运行检测器、告警服务、broker 与确认页面 |
| IP 摄像头 | 提供检测器观察的 RTSP 画面 |

**重要提示**

本系统不是医疗器械，也不是经过认证的紧急响应产品。它不用于诊断、治疗，也不替代护理人员的
判断。告警只是提示，处置责任在人。

同样的弱点在这里都成立：跌倒必须发生在画面里，启动时已躺在地上的人不会产生事件，远景、遮挡
与低光都会降低检出，摄像头一动区域就会无声失效，`no_motion` 在睡眠时段会触发，除非区域或
超时已经把这一点考虑进去。

此外这个套餐与 HailoRT 4.21 存在 ABI 绑定——GStreamer 插件、用户库与内核驱动必须都是这个
版本。以及同上：告警服务镜像尚未发布。

## 步骤 1: 部署告警栈 {#deploy_hailo_alarm type=docker_deploy required=true config=devices/hailo_alarm.yaml}

表单与 Orin 套餐一样。这一步会检查加速器、下载并校验 HEF、写入检测器环境变量与告警配置，
并在报成功之前验证真的收到了一条检测器消息、且告警 API 能应答。

### 前置条件

- Raspberry Pi OS 或 Ubuntu，装好 Docker 与 HailoRT 4.21 全套：`/dev/hailo0` 存在、
  `/usr/lib/libhailort.so.4.21.0` 存在、HailoRT GStreamer 插件在
  `/usr/lib/aarch64-linux-gnu/gstreamer-1.0/libgsthailo.so`。
- 至少 6 GB 可用空间。
- 摄像头的 RTSP 地址，先用 VLC 测通。
- **`eldercare-alarm-arm64:0.1.0` 镜像还不在 registry 里。** 从上游项目构建并打成
  compose 文件期望的 tag：
  `docker build -f docker/Dockerfile -t sensecraft-missionpack.seeed.cn/solution/eldercare-alarm-arm64:0.1.0 .`

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `No /dev/hailo0` | 加速器没插好或驱动没加载。`hailortcli fw-control identify` 应该能返回。 |
| `libhailort.so.4.21.0 not found` | 装的是别的 HailoRT 小版本。插件、用户库与驱动要一起换，只改挂载没用。 |
| HEF 下载失败或校验不过 | 该地址是 Hailo Model Zoo v2.15 官方构建。重跑这一步，未完成的分片会续传。 |
| `eldercare-alarm-arm64` 报 `pull access denied` | 在该镜像构建或推送之前属预期现象，见前置条件。 |
| 验证阶段报 `No detector result` | 先看容器健康状态——这一步会打印出来。再从设备上核对 RTSP 地址，并看 `docker logs eldercare_alarm_hailo-fall-detection-1`。 |
| 验证阶段卡在告警 API | `docker logs eldercare_alarm_hailo-eldercare-alarm-1` 会指出它拒绝的配置项。 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="reComputer R" config=devices/hailo_alarm.yaml default=true}

通过 SSH 部署到网络上的设备。

### 部署目标 {#hailo_local type=local device=hailo device_name="reComputer R" config=devices/hailo_alarm.yaml}

直接在设备上部署，适用于应用就跑在这台机器上的情况。

## 步骤 2: 打开确认页面 {#verify_hailo_alarm type=web_dashboard required=false config=devices/confirm_ui.yaml}

填设备地址与 8080 端口，页面会在浏览器里打开。

### 部署完成

检测器在发布，告警服务在消费，而这个控制台就是人对结果做处置的地方。

#### 快速验证

1. 页面能打开并显示告警列表。现场无事时列表为空是正确结果。
2. 在设备上确认消息在流动：
   `docker exec eldercare_alarm_hailo-mosquitto-1 mosquitto_sub -h 127.0.0.1 -t '#' -v -C 5`。
3. 强制造一条告警：把 `config/eldercare.yaml` 里该区域的 `no_person_timeout_sec` 改成 60，
   执行 `docker compose restart eldercare-alarm`，让区域空置一分钟，刷新页面，再把原值改回去。
4. 在页面上确认这条告警，并检查 webhook 接收端收到一次 POST，负载里有操作者名字、
   且不含任何媒体。

#### 下一步

- 把覆盖整幅画面的区域拆成按房间的矩形，并把每个区域绑到对应的流编号上。
- 把 `notifiers` 指向真正应该接收告警的系统。
- 设备能被局域网以外访问之前，先给 broker 加上账号密码与 TLS。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 页面打不开 | 8080 端口可能被占。看 `docker compose ps` 与容器日志。 |
| 页面能开但列表永远为空 | 把 `config/eldercare.yaml` 里的 `mqtt.subscriptions` 与实时的 `mosquitto_sub -t '#' -v` 对一下。 |
| 有告警但 webhook 没收到 | `escalated` 表示送达超期；重试仍每 30 s 进行，状态刻意保持 `escalated`。 |
| 房间里明明有人却报了 `no_person` | 人在区域矩形之外，或者被遮挡了。对着实时画面重新核对区域。 |

## 套餐: reCamera + 告警网关 {#recamera}

摄像头本来就在自己做跌倒检测——2002 是原生进程，Pro 是应用中心里的应用——本方案不动它们。
告警服务放到旁边的网关机器上，由人工拉起：那台网关是现场手上现成的机器，而部署表单里没有
"任意 Linux 主机"这样一个设备类型可以寻址它。

| 设备 | 用途 |
|---|---|
| reCamera 2002 或 reCamera Pro | 做跌倒检测并发布事件流 |
| 网关主机（任意 x86_64 或 arm64 Linux 机器） | 运行告警服务、broker 与确认页面 |

**重要提示**

本系统不是医疗器械，也不是经过认证的紧急响应产品。它不用于诊断、治疗，也不替代护理人员的
判断。告警只是提示，处置责任在人。

其他套餐的弱点在这里同样成立——跌倒必须发生在画面里，遮挡、远景与低光都会降低检出，
摄像头一动区域就失效，`no_motion` 在睡眠时段会触发——此外还有一条是这条路径特有的：
reCamera 的事件流尚未在硬件上为本方案核实过。确切的主题，以及摄像头在无人时是否照样发布，
都要先在你自己的设备上查清楚，`no_person` 告警才谈得上可靠。

## 步骤 1: 搭建告警网关 {#deploy_recamera_alarm type=manual required=true config=devices/recamera_alarm.yaml}

五个子步骤：确认摄像头在发布、准备网关、改配置、启动服务、确认事件已被接收。
需要的东西都在本包的 `assets/recamera/` 里。

### 前置条件

- 摄像头上已经部署并运行着 Fall Detection。
- 同网段有一台装好 Docker 与 compose 插件的网关机器。
- **告警服务镜像尚未发布。** 按网关的架构从上游项目构建并打 tag，或把
  `ELDERCARE_ALARM_IMAGE` 指向你自己的 tag：
  `docker build -f docker/Dockerfile -t sensecraft-missionpack.seeed.cn/solution/eldercare-alarm-amd64:0.1.0 .`
- 网关上有 `mosquitto_sub`，用于在配置之前先读一下摄像头的主题。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| `mosquitto_sub -t '#'` 什么都没有 | 摄像头发到的是它自己的 broker，不是这一个。把 `mqtt.host` 指向摄像头的 broker，或者把摄像头改成发到网关。 |
| 主题和两个示例都对不上 | 以你实际看到的为准。2002 的主题映射到 `fall_result_v1`，Pro 的映射到 `recamera_pro_state`。不要靠主题形状猜。 |
| `eldercare-alarm` 反复重启 | `docker compose logs eldercare-alarm` 会指出它拒绝的配置项。 |
| 报 `pull access denied` | 在镜像构建或推送之前属预期现象，见前置条件。 |
| 跌倒能报但 `no_person` 从不触发 | 摄像头可能在无人时不发布。让画面里没人，盯着主题看——如果消息停了，那么在检测器被改成持续发布之前，这类告警在这台摄像头上就用不了。 |

## 步骤 2: 打开确认页面 {#verify_recamera_alarm type=web_dashboard required=false config=devices/confirm_ui.yaml}

填网关地址与 8080 端口，页面会在浏览器里打开。

### 部署完成

摄像头在发布，网关把事件流变成告警，而这个控制台就是人对它们做处置的地方。

#### 快速验证

1. 页面能打开并显示告警列表。现场无事时列表为空是正确结果。
2. 在网关上执行 `curl -s http://127.0.0.1:8080/api/alarms`，返回同一份列表——页面已在提供
   但浏览器访问不到时，这条命令能帮你分清是哪一头的问题。
3. 强制造一条告警：把 `config/eldercare.yaml` 里某区域的 `no_person_timeout_sec` 改成 60，
   执行 `docker compose restart eldercare-alarm`，让区域空置一分钟，刷新页面，再把原值改回去。
4. 在页面上确认这条告警，并检查 webhook 接收端收到一次 POST，负载里有操作者名字、
   且不含任何媒体。

#### 下一步

- 按区域各加一条，每条都有自己的矩形、流编号与超时。
- 若多台摄像头汇到同一个网关，把每个区域显式绑到它的流编号上——否则区域会接受所有流的帧。
- 网关能被局域网以外访问之前，先给 broker 加上账号密码与 TLS。

### 故障排查

| 问题 | 解决办法 |
|---|---|
| 页面打不开 | 看网关上的 `docker compose ps`，以及 8080 端口是否已被占用。 |
| 页面能开但列表永远为空 | 订阅主题对不上。把 `mqtt.subscriptions` 与实时的 `mosquitto_sub -t '#' -v` 对一下。 |
| 有告警但 webhook 没收到 | `escalated` 表示送达超期；重试仍每 30 s 进行，状态刻意保持 `escalated`。 |
| 各区域表现得像合成了一个 | `stream_ids` 为空表示接受任意流。多台摄像头汇入同一网关时，每个区域都要显式绑定。 |
