## 套餐: reCamera 2002 {#recamera}

一台 reCamera 2002 在设备本地判断有没有人摔倒，并通过 MQTT 发出事件。

**重要提示：** 这是辅助告警，不是经过认证的医疗或人身安全系统。远景、遮挡、低光以及看起来像跌倒的地面动作仍是弱项。

## 步骤 1: 更新 reCamera 控制台 {#update_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.5 控制台，它负责管理相机应用。已经是该版本会自动跳过。

### 前置条件

1. 用 USB 连接 reCamera，或让它和这台电脑处于同一网络。
2. USB 连接的地址是 `192.168.42.1`；走 Wi-Fi 时用路由器上显示的 IP。
3. 默认密码是 `recamera`（较早期的设备用 `recamera.2`）。
4. 下一步安装跌倒检测需要该版本控制台。

### 故障排查

| 现象 | 处理 |
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

| 现象 | 处理 |
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

告警发往 `recamera/fall-detection/results`，Home Assistant 自动发现会生成跌倒状态、事件编号和有人存在实体。

#### 快速验证

1. 点击 **连接**，等待视频出现。
2. 走进画面——骨架应当跟随你移动，状态卡显示 `NORMAL`。
3. 有意识地躺到地面上。大约两秒内状态卡应当变红，并显示一个新的事件编号。

#### 下一步

- 把摄像头接入 Home Assistant——只要 broker 是共享的，实体会自动出现。
- 在启用任何通知流程之前，用有代表性的跌倒动作和日常动作做一次现场验收测试。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 叠加层比视频先出现 | MQTT 比 RTSP 连得快，等几秒即可 |
| 人贴近地面时骨架消失 | 重新构图；落地后的短暂遮挡可以容忍，长时间遮挡无法判定 |
| 完全没有叠加层 | 确认 1883 端口可达，且主题填写一致 |

---

## 步骤 4: 安装告警面板（可选） {#panel_host_recamera type=docker_deploy required=false config=devices/panel_host.yaml}

跳过这一步部署即告完成：摄像头照旧发 MQTT 事件，其余什么都不变。

做这一步，则在另一台主机上安装告警面板：站点总览、在实时画面上画识别区域、每个区域的无人超时与静止超时、值班人确认或驳回告警、审计记录，以及不含视频的 webhook。

### 前置条件

面板装在与摄像头同网段的另一台机器上，不需要 AI 算力：reComputer R1000 系列，或已有的一台 Linux 机器。

- 摄像头同网段的一台 x86_64 或 arm64 Linux 主机，装好 Docker 与 compose 插件
  （`docker compose version` 必须能跑通），并可 SSH 登录。
- 摄像头实际发布的主题。开始前先在那台主机上确认：
  `mosquitto_sub -h <摄像头或 broker 地址> -t '#' -v`。reCamera 2002 发布在 `<设备名>/fall-detection/results`，单流，无流编号后缀。
- 该主机的 8080 与 1883 端口空闲，或在表单里填别的端口。

### 故障排查

| 现象 | 处理 |
|---|---|
| 部署停在「Port 8080 is already in use」 | 在表单里换一个面板端口，或停掉提示里指出的那个服务。 |
| 结尾出现「no message on ... within 20 s」告警 | 面板已起来但没收到检测结果。用 `mosquitto_sub -t '#' -v` 重新核对主题，并确认摄像头发布到的是这里填的 broker 地址。 |
| 告警列表一直为空，无人告警从不触发 | 画面里没人时摄像头也要发消息，这个超时才有输入。跌倒告警不受影响。 |
| `eldercare-alarm-*` 报 `pull access denied` | 检查主机能否访问镜像仓库。 |

### 部署目标 {#panel_host_recamera_remote type=remote device_name="告警面板主机" config=devices/panel_host.yaml default=true}

通过 SSH 部署到面板主机。

## 步骤 5: 打开告警面板 {#panel_open_recamera type=web_dashboard required=false config=devices/panel_console.yaml}

只有装了面板才需要这一步。

### 部署完成

#### 快速验证

- 总览页会列出你填的那个房间，带摄像头数与区域数。
- 现场无事时告警列表为空即为正常——说明服务已经起来并能应答。
- 要端到端验证接收链路，在主机上把该区域的无人超时临时改成 1 分钟
  （改 `config/alarm-panel.yaml`，再执行 `docker compose restart alarm-panel`），
  让该区域空置，确认出现一条告警。验证完把原值改回去。

#### 下一步

- 在实时画面上把识别区域画出来，替换部署时创建的那个覆盖整幅画面的矩形。
- 之前留空的话，把 webhook 指向你自己的告警系统。
- 语音确认默认关闭，需要一个 OpenVoiceStream 实例，以及接在这台主机上的 USB 麦克风与扬声器，见步骤 6。

### 故障排查

| 现象 | 处理 |
|---|---|
| 页面打不开 | 核对面板端口与部署步骤里填的一致，并确认主机防火墙放行。 |
| 出现登录页 | 部署设置了 `ELDERCARE_API_TOKEN`。输入该口令与操作者姓名——姓名会写进确认/驳回回执。 |
| 某个房间显示「未知 + 断流」 | 面板主机连不上那台摄像头，检查网络；卡片上的「最近一帧」是最后收到画面的时间。 |

## 步骤 6: 语音确认（可选） {#voice_checkin_recamera type=manual required=false verify=true config=devices/voice_checkin.yaml}

可选，默认关闭。跌倒告警触发后，服务出声询问住户是否安好，并按回答处置；关闭后告警链路不变。

回答如何影响告警：

| 回答 | 结果 |
|---|---|
| 求救（"救命"、"help"、"我起不来"） | 立即确认，跳过剩余的人工窗口 |
| 完全没有回答 | 立即确认 |
| 听不明白 | 立即确认 |
| "我没事" | 默认 `on_ok: needs_review`——告警保持原有时序，只打上待复核标记。要直接结案就设 `on_ok: dismiss` |

### 前置条件

同一局域网内有一个 OpenVoiceStream 实例，USB 麦克风与扬声器接在运行它的那台机器上，不接在摄像头上。

### 部署完成

同一句话里同时有求救词和安全词时按求救处理。

**隐私：** 音频不落盘。审计保存判定结果、置信度、耗时与转写文本；把 `store_transcript` 设为 `false` 则不存转写文本。通知不含快照和视频。

#### 快速验证

1. `curl -sf http://<ovs 地址>:8621/readyz` 返回 200。
2. 站在可能跌倒的位置能听清合成出来的提示音。

### 故障排查

| 现象 | 处理 |
|---|---|
| 每条告警都是 `no_answer` | 要么提示音听不见，要么没有采到音。先查扬声器，再在告警主机上跑 `arecord -l`。 |
| 每条告警都是 `unclear` | ASR 返回的文本没命中词表。在控制台里看转写内容，把住户实际的说法加进 `ok_keywords` / `help_keywords`。 |
| 告警自己结案了 | `on_ok` 被设成了 `dismiss`。除非确实有人在复核这些驳回，否则改回 `needs_review`。 |
| 服务起来了但从不出声 | 确认告警主机的音频设备已接入容器，在 `docker compose logs eldercare-alarm` 里查看 TTS 或播放报错。 |

## 套餐: reCamera Pro {#recamera_pro}

一台 reCamera Pro 在设备本地做多人跟踪和跌倒判定，并通过 MQTT 发出事件。

**重要提示：** 这是辅助告警，不是经过认证的医疗或人身安全系统。远景、遮挡、弱光以及类似跌倒的地面活动仍是弱项。

检测器通过设备自带的应用中心分发，本套餐**配置已安装的应用并把它设为运行中的应用**。设备上还没有时，先在应用中心安装。

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

这两个主题不含骨架数据；带骨架的实时画面在设备控制台页面上，由本步骤打开。

### 故障排查

| 现象 | 处理 |
|------|----------|
| 摄像头页面打不开 | 固件有 HTTPS 开关，80 端口会重定向到 443。跟随跳转，或直接用 `https://` 地址打开 |
| 实时画面正常但 broker 收不到跌倒事件 | 检查上一步填的 broker 地址和端口；summary 主题要检测到人之后才会出现 |
| 应用中心里有 Fall Detection 但启动不了 | 缺 AI 模型。在摄像头的应用中心里重新安装一次——安装时会连模型一起下载 |
| 贴近地面时漏检 | 调整摄像头取景；倒地后的短暂遮挡可以容忍，长时间遮挡无法判定 |

### 部署目标 {#recamera_pro_verify type=remote device_name="reCamera Pro" config=devices/verify_recamera_pro_fall.yaml}

## 步骤 4: 安装告警面板（可选） {#panel_host_recamera_pro type=docker_deploy required=false config=devices/panel_host.yaml}

跳过这一步部署即告完成：摄像头照旧发 MQTT 事件，其余什么都不变。

做这一步，则在另一台主机上安装告警面板：站点总览、在实时画面上画识别区域、每个区域的无人超时与静止超时、值班人确认或驳回告警、审计记录，以及不含视频的 webhook。

### 前置条件

面板装在与摄像头同网段的另一台机器上，不需要 AI 算力：reComputer R1000 系列，或已有的一台 Linux 机器。

- 摄像头同网段的一台 x86_64 或 arm64 Linux 主机，装好 Docker 与 compose 插件
  （`docker compose version` 必须能跑通），并可 SSH 登录。
- 摄像头实际发布的主题。开始前先在那台主机上确认：
  `mosquitto_sub -h <摄像头或 broker 地址> -t '#' -v`。reCamera Pro 发布在 `<base>/fall-detection/state`；表单里「摄像头型号」要选 reCamera Pro，才会用 Pro 适配器。
- 该主机的 8080 与 1883 端口空闲，或在表单里填别的端口。

### 故障排查

| 现象 | 处理 |
|---|---|
| 部署停在「Port 8080 is already in use」 | 在表单里换一个面板端口，或停掉提示里指出的那个服务。 |
| 结尾出现「no message on ... within 20 s」告警 | 面板已起来但没收到检测结果。用 `mosquitto_sub -t '#' -v` 重新核对主题，并确认摄像头发布到的是这里填的 broker 地址。 |
| 告警列表一直为空，无人告警从不触发 | 画面里没人时摄像头也要发消息，这个超时才有输入。跌倒告警不受影响。 |
| `eldercare-alarm-*` 报 `pull access denied` | 检查主机能否访问镜像仓库。 |

### 部署目标 {#panel_host_recamera_pro_remote type=remote device_name="告警面板主机" config=devices/panel_host.yaml default=true}

通过 SSH 部署到面板主机。

## 步骤 5: 打开告警面板 {#panel_open_recamera_pro type=web_dashboard required=false config=devices/panel_console.yaml}

只有装了面板才需要这一步。

### 部署完成

#### 快速验证

- 总览页会列出你填的那个房间，带摄像头数与区域数。
- 现场无事时告警列表为空即为正常——说明服务已经起来并能应答。
- 要端到端验证接收链路，在主机上把该区域的无人超时临时改成 1 分钟
  （改 `config/alarm-panel.yaml`，再执行 `docker compose restart alarm-panel`），
  让该区域空置，确认出现一条告警。验证完把原值改回去。

#### 下一步

- 在实时画面上把识别区域画出来，替换部署时创建的那个覆盖整幅画面的矩形。
- 之前留空的话，把 webhook 指向你自己的告警系统。
- 语音确认默认关闭，需要一个 OpenVoiceStream 实例，以及接在这台主机上的 USB 麦克风与扬声器，见步骤 6。

### 故障排查

| 现象 | 处理 |
|---|---|
| 页面打不开 | 核对面板端口与部署步骤里填的一致，并确认主机防火墙放行。 |
| 出现登录页 | 部署设置了 `ELDERCARE_API_TOKEN`。输入该口令与操作者姓名——姓名会写进确认/驳回回执。 |
| 某个房间显示「未知 + 断流」 | 面板主机连不上那台摄像头，检查网络；卡片上的「最近一帧」是最后收到画面的时间。 |

## 步骤 6: 语音确认（可选） {#voice_checkin_recamera_pro type=manual required=false verify=true config=devices/voice_checkin.yaml}

可选，默认关闭。跌倒告警触发后，服务出声询问住户是否安好，并按回答处置；关闭后告警链路不变。

回答如何影响告警：

| 回答 | 结果 |
|---|---|
| 求救（"救命"、"help"、"我起不来"） | 立即确认，跳过剩余的人工窗口 |
| 完全没有回答 | 立即确认 |
| 听不明白 | 立即确认 |
| "我没事" | 默认 `on_ok: needs_review`——告警保持原有时序，只打上待复核标记。要直接结案就设 `on_ok: dismiss` |

### 前置条件

同一局域网内有一个 OpenVoiceStream 实例，USB 麦克风与扬声器接在运行它的那台机器上，不接在摄像头上。

### 部署完成

同一句话里同时有求救词和安全词时按求救处理。

**隐私：** 音频不落盘。审计保存判定结果、置信度、耗时与转写文本；把 `store_transcript` 设为 `false` 则不存转写文本。通知不含快照和视频。

#### 快速验证

1. `curl -sf http://<ovs 地址>:8621/readyz` 返回 200。
2. 站在可能跌倒的位置能听清合成出来的提示音。

### 故障排查

| 现象 | 处理 |
|---|---|
| 每条告警都是 `no_answer` | 要么提示音听不见，要么没有采到音。先查扬声器，再在告警主机上跑 `arecord -l`。 |
| 每条告警都是 `unclear` | ASR 返回的文本没命中词表。在控制台里看转写内容，把住户实际的说法加进 `ok_keywords` / `help_keywords`。 |
| 告警自己结案了 | `on_ok` 被设成了 `dismiss`。除非确实有人在复核这些驳回，否则改回 `needs_review`。 |
| 服务起来了但从不出声 | 确认告警主机的音频设备已接入容器，在 `docker compose logs eldercare-alarm` 里查看 TTS 或播放报错。 |

## 套餐: IP 摄像头 + reComputer J30 / J40 {#jetson}

reComputer J30 / J40 拉取现有 IP 摄像头的 RTSP 流，对每一路里的多个人独立跟踪并判定跌倒。

- **摄像头：** 支持 ONVIF 或 RTSP 的 IP 摄像头。

**重要提示：** 这是辅助告警，不是经过认证的医疗或人身安全系统。远景和遮挡会降低召回。

## 步骤 1: 部署跌倒检测 {#deploy_jetson_fall type=docker_deploy required=true config=devices/jetson_fall.yaml}

在 Jetson 上部署检测器并构建推理引擎，预计需要 10–20 分钟。

### 前置条件

1. Jetson 运行 JetPack 6.x，且 NVIDIA 容器运行时可用。
2. 至少 10 GB 空闲磁盘。
3. 准备好 IP 摄像头的 RTSP 地址，需要认证的话要带上用户名密码，例如
   `rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101`。
4. 首次部署大部分时间用于在设备上构建推理引擎，之后的部署会复用。
5. 按板子选姿态模型：Orin Nano 用 **YOLO11s**，Orin NX 用 **YOLO11m**。

### 故障排查

| 现象 | 处理 |
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

结果发往 `recamera/fall-detection/results/<流编号>`，一路摄像头一个主题。

#### 快速验证

1. 点击 **连接**，等待摄像头画面出现。
2. 走进画面——应当有一个框跟随你，标注着跟踪编号和 `NORMAL`。
3. 有意识地躺下。框应当变红，状态卡显示一个新的事件编号。

#### 增加更多摄像头

检测器可以同时处理多路视频。在设备上的配置文件里往 `streams` 列表中添加，然后重启
容器即可；每一路各自维护跟踪状态，并有自己的 MQTT 主题。

#### 下一步

- 把告警系统指向 MQTT 主题，或把 broker 接入 Home Assistant 以获取自动发现实体。
- 增加路数前先在现场测一次实际帧率。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 有视频但没有叠加层 | 预览是单独读 MQTT 的，确认 Jetson 的 1883 端口可达 |
| 有叠加层但没有视频 | 预览直接从摄像头拉 RTSP，确认这台电脑也能访问摄像头 |
| 框在不同人之间跳变 | 调高跟踪器的 IoU 阈值，或调整机位减少人物重叠 |

---

## 步骤 3: 打开告警面板 {#panel_open_jetson type=web_dashboard required=false config=devices/panel_console.yaml}

告警面板已在步骤 1 与检测器一起部署在同一台设备上，默认端口 8080。面板提供站点总览、在实时画面上画识别区域、每个区域的无人超时与静止超时、按操作者记录的确认与驳回，以及不含视频的 webhook。

### 部署完成

#### 快速验证

- 总览页会列出你在部署表单里填的那个区域。
- 现场无事时告警列表为空即为正常——说明服务已经起来并能应答。
- 要端到端验证接收链路，在设备上把该区域的无人超时临时改成 1 分钟
  （改 `config/alarm-panel.yaml`，再执行 `docker compose restart alarm-panel`），
  让该区域空置，确认出现一条告警。验证完把原值改回去。

#### 下一步

- 在实时画面上把识别区域画出来，替换部署时创建的那个覆盖整幅画面的矩形。
- 之前留空的话，把 webhook 指向你自己的告警系统。
- 语音确认默认关闭，需要一个 OpenVoiceStream 实例，以及接在这台设备上的 USB 麦克风与扬声器，见步骤 4。

### 故障排查

| 现象 | 处理 |
|---|---|
| 页面打不开 | 核对告警面板端口与部署步骤里填的一致，并确认设备防火墙放行。 |
| 出现登录页 | 部署设置了 `ELDERCARE_API_TOKEN`。输入该口令与操作者姓名——姓名会写进确认/驳回回执。 |
| 跌倒能告警，无人告警从不触发 | 检测器配置里 `publish_empty_frames` 已经是 true，这个超时依赖它。如果你把 `config/config.json` 换成了设备自带的那份，需要把这个键重新设上。 |

## 步骤 4: 语音确认（可选） {#voice_checkin_jetson type=manual required=false verify=true config=devices/voice_checkin.yaml}

可选，默认关闭。跌倒告警触发后，服务出声询问住户是否安好，并按回答处置；关闭后告警链路不变。

回答如何影响告警：

| 回答 | 结果 |
|---|---|
| 求救（"救命"、"help"、"我起不来"） | 立即确认，跳过剩余的人工窗口 |
| 完全没有回答 | 立即确认 |
| 听不明白 | 立即确认 |
| "我没事" | 默认 `on_ok: needs_review`——告警保持原有时序，只打上待复核标记。要直接结案就设 `on_ok: dismiss` |

### 前置条件

同一局域网内有一个 OpenVoiceStream 实例，USB 麦克风与扬声器接在运行它的那台机器上，不接在摄像头上。

### 部署完成

同一句话里同时有求救词和安全词时按求救处理。

**隐私：** 音频不落盘。审计保存判定结果、置信度、耗时与转写文本；把 `store_transcript` 设为 `false` 则不存转写文本。通知不含快照和视频。

#### 快速验证

1. `curl -sf http://<ovs 地址>:8621/readyz` 返回 200。
2. 站在可能跌倒的位置能听清合成出来的提示音。

### 故障排查

| 现象 | 处理 |
|---|---|
| 每条告警都是 `no_answer` | 要么提示音听不见，要么没有采到音。先查扬声器，再在告警主机上跑 `arecord -l`。 |
| 每条告警都是 `unclear` | ASR 返回的文本没命中词表。在控制台里看转写内容，把住户实际的说法加进 `ok_keywords` / `help_keywords`。 |
| 告警自己结案了 | `on_ok` 被设成了 `dismiss`。除非确实有人在复核这些驳回，否则改回 `needs_review`。 |
| 服务起来了但从不出声 | 确认告警主机的音频设备已接入容器，在 `docker compose logs eldercare-alarm` 里查看 TTS 或播放报错。 |

## 套餐: IP 摄像头 + reComputer RK3576 / RK3588 {#rk}

检测器跑在 reComputer RK3576 / RK3588 的 NPU 上，MQTT 输出与其他套餐一致。

- **摄像头：** 支持 ONVIF 或 RTSP 的 IP 摄像头。

**重要提示：** 这是辅助告警，不是经过认证的医疗或人身安全系统。

## 步骤 1: 部署跌倒检测 {#deploy_rk_fall type=docker_deploy required=true config=devices/rk3588_fall.yaml}

把检测器部署到你的瑞芯微板卡，预计需要 5 分钟左右。

### 前置条件

1. 板卡运行厂商系统镜像，NPU 驱动和 `librknnrt.so` 已就位，并且装有 Docker。
2. 至少 6 GB 空闲磁盘，用于运行时镜像和姿态模型。
3. 准备好 IP 摄像头的 RTSP 地址，需要认证的话带上用户名密码。
4. 选择与板卡一致的部署目标，RK3588 与 RK3576 的模型不通用。当前部署安装单路摄像头。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 提示找不到 `librknnrt.so` | 安装板卡的 `rknpu2` 运行时包 |
| 模型加载失败 | 模型必须与板卡匹配，选对板卡型号后重新执行这一步 |
| 收不到摄像头画面 | 先用 VLC 测试 RTSP 地址，绝大多数问题是路径或用户名密码写错 |
| 帧率偏低 | 其他 NPU 业务在抢占加速器，先看看板卡上还跑着什么 |

### 部署目标 {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_fall.yaml default=true}

### 部署目标 {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_fall.yaml}

### 部署目标 {#rk_local type=local device=rk3588 device_name="reComputer RK3576 / RK3588" config=devices/rk_auto_fall.yaml}

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
- 正式使用前做一次现场验收测试。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 有视频但没有叠加层 | 预览是单独读 MQTT 的，确认板卡的 1883 端口可达 |
| 骨架和人物错位 | 请向 Seeed 反馈 |
| 框在不同人之间跳变 | 调高跟踪器的 IoU 阈值，或调整机位减少人物重叠 |

---

## 步骤 3: 打开告警面板 {#panel_open_rk type=web_dashboard required=false config=devices/panel_console.yaml}

告警面板已在步骤 1 与检测器一起部署在同一台设备上，默认端口 8080。面板提供站点总览、在实时画面上画识别区域、每个区域的无人超时与静止超时、按操作者记录的确认与驳回，以及不含视频的 webhook。

### 部署完成

#### 快速验证

- 总览页会列出你在部署表单里填的那个区域。
- 现场无事时告警列表为空即为正常——说明服务已经起来并能应答。
- 要端到端验证接收链路，在设备上把该区域的无人超时临时改成 1 分钟
  （改 `config/alarm-panel.yaml`，再执行 `docker compose restart alarm-panel`），
  让该区域空置，确认出现一条告警。验证完把原值改回去。

#### 下一步

- 在实时画面上把识别区域画出来，替换部署时创建的那个覆盖整幅画面的矩形。
- 之前留空的话，把 webhook 指向你自己的告警系统。
- 语音确认默认关闭，需要一个 OpenVoiceStream 实例，以及接在这台设备上的 USB 麦克风与扬声器，见步骤 4。

### 故障排查

| 现象 | 处理 |
|---|---|
| 页面打不开 | 核对告警面板端口与部署步骤里填的一致，并确认设备防火墙放行。 |
| 出现登录页 | 部署设置了 `ELDERCARE_API_TOKEN`。输入该口令与操作者姓名——姓名会写进确认/驳回回执。 |
| 跌倒能告警，无人告警从不触发 | 这个超时要求画面里没人时检测器也发消息，确认画面无人时 MQTT 主题仍有消息。 |

## 步骤 4: 语音确认（可选） {#voice_checkin_rk type=manual required=false verify=true config=devices/voice_checkin.yaml}

可选，默认关闭。跌倒告警触发后，服务出声询问住户是否安好，并按回答处置；关闭后告警链路不变。

回答如何影响告警：

| 回答 | 结果 |
|---|---|
| 求救（"救命"、"help"、"我起不来"） | 立即确认，跳过剩余的人工窗口 |
| 完全没有回答 | 立即确认 |
| 听不明白 | 立即确认 |
| "我没事" | 默认 `on_ok: needs_review`——告警保持原有时序，只打上待复核标记。要直接结案就设 `on_ok: dismiss` |

### 前置条件

同一局域网内有一个 OpenVoiceStream 实例，USB 麦克风与扬声器接在运行它的那台机器上，不接在摄像头上。

### 部署完成

同一句话里同时有求救词和安全词时按求救处理。

**隐私：** 音频不落盘。审计保存判定结果、置信度、耗时与转写文本；把 `store_transcript` 设为 `false` 则不存转写文本。通知不含快照和视频。

#### 快速验证

1. `curl -sf http://<ovs 地址>:8621/readyz` 返回 200。
2. 站在可能跌倒的位置能听清合成出来的提示音。

### 故障排查

| 现象 | 处理 |
|---|---|
| 每条告警都是 `no_answer` | 要么提示音听不见，要么没有采到音。先查扬声器，再在告警主机上跑 `arecord -l`。 |
| 每条告警都是 `unclear` | ASR 返回的文本没命中词表。在控制台里看转写内容，把住户实际的说法加进 `ok_keywords` / `help_keywords`。 |
| 告警自己结案了 | `on_ok` 被设成了 `dismiss`。除非确实有人在复核这些驳回，否则改回 `needs_review`。 |
| 服务起来了但从不出声 | 确认告警主机的音频设备已接入容器，在 `docker compose logs eldercare-alarm` 里查看 TTS 或播放报错。 |

## 套餐: IP 摄像头 + reComputer R2000（Hailo） {#hailo}

检测器跑在带 Hailo-8 加速器的 reComputer R2000 上，MQTT 输出与其他套餐一致。

- **摄像头：** 支持 ONVIF 或 RTSP 的 IP 摄像头。

**重要提示：** 这是辅助告警，不是经过认证的医疗或人身安全系统。

## 步骤 1: 部署跌倒检测 {#deploy_hailo_fall type=docker_deploy required=true config=devices/hailo_fall.yaml}

把检测器部署到带 Hailo 的设备，预计需要 5 分钟左右。

### 前置条件

1. 设备上有 Hailo-8 加速器（`/dev/hailo0`），且安装 **HailoRT 4.21**（GStreamer 插件、用户态库和内核驱动同一版本）。
2. 装有 Docker，至少 4 GB 空闲磁盘。
3. 准备好 IP 摄像头的 RTSP 地址，需要认证的话带上用户名密码。
4. 姿态模型在部署过程中自动下载。
5. 先停掉其他占用 Hailo 加速器的应用。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 找不到 `/dev/hailo0` | 加速器没插好或驱动没加载，用 `hailortcli fw-control identify` 检查 |
| 找不到 `libhailort.so.4.21.0` | 安装 HailoRT 4.21，插件、库和驱动需同时为该版本 |
| 容器启动后退出 | 停掉占用加速器的其他进程 |
| 收不到摄像头画面 | 先用 VLC 测试 RTSP 地址，绝大多数问题是路径或用户名密码写错 |
| 部署在验证阶段停止 | 检查检测器日志中的 `HAILO_BATCH` 行、容器健康状态和配置主题上的 MQTT 结果 |

### 部署目标 {#hailo_remote type=remote device=hailo device_name="reComputer R2000" config=devices/hailo_fall.yaml default=true}

从这台电脑通过 SSH 部署到设备。

### 部署目标 {#hailo_local type=local device=hailo device_name="reComputer R2000" config=devices/hailo_fall.yaml}

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
- 正式使用前做一次现场验收测试。

### 故障排查

| 现象 | 处理 |
|-------|----------|
| 有视频但没有叠加层 | 预览是单独读 MQTT 的，确认设备的 1883 端口可达 |
| 有叠加层但没有视频 | 预览直接从摄像头拉 RTSP，确认这台电脑也能访问摄像头 |
| `inference_time_ms` 显示 0 | 属于预期，Hailo 运行时不上报该值 |

## 步骤 3: 打开告警面板 {#panel_open_hailo type=web_dashboard required=false config=devices/panel_console.yaml}

告警面板已在步骤 1 与检测器一起部署在同一台设备上，默认端口 8080。面板提供站点总览、在实时画面上画识别区域、每个区域的无人超时与静止超时、按操作者记录的确认与驳回，以及不含视频的 webhook。

### 部署完成

#### 快速验证

- 总览页会列出你在部署表单里填的那个区域。
- 现场无事时告警列表为空即为正常——说明服务已经起来并能应答。
- 要端到端验证接收链路，在设备上把该区域的无人超时临时改成 1 分钟
  （改 `config/alarm-panel.yaml`，再执行 `docker compose restart alarm-panel`），
  让该区域空置，确认出现一条告警。验证完把原值改回去。

#### 下一步

- 在实时画面上把识别区域画出来，替换部署时创建的那个覆盖整幅画面的矩形。
- 之前留空的话，把 webhook 指向你自己的告警系统。
- 语音确认默认关闭，需要一个 OpenVoiceStream 实例，以及接在这台设备上的 USB 麦克风与扬声器，见步骤 4。

### 故障排查

| 现象 | 处理 |
|---|---|
| 页面打不开 | 核对告警面板端口与部署步骤里填的一致，并确认设备防火墙放行。 |
| 出现登录页 | 部署设置了 `ELDERCARE_API_TOKEN`。输入该口令与操作者姓名——姓名会写进确认/驳回回执。 |
| 跌倒能告警，无人告警从不触发 | 检查区域绑定的流编号是否与部署表单里的 Stream ID 一致。 |

## 步骤 4: 语音确认（可选） {#voice_checkin_hailo type=manual required=false verify=true config=devices/voice_checkin.yaml}

可选，默认关闭。跌倒告警触发后，服务出声询问住户是否安好，并按回答处置；关闭后告警链路不变。

回答如何影响告警：

| 回答 | 结果 |
|---|---|
| 求救（"救命"、"help"、"我起不来"） | 立即确认，跳过剩余的人工窗口 |
| 完全没有回答 | 立即确认 |
| 听不明白 | 立即确认 |
| "我没事" | 默认 `on_ok: needs_review`——告警保持原有时序，只打上待复核标记。要直接结案就设 `on_ok: dismiss` |

### 前置条件

同一局域网内有一个 OpenVoiceStream 实例，USB 麦克风与扬声器接在运行它的那台机器上，不接在摄像头上。

### 部署完成

同一句话里同时有求救词和安全词时按求救处理。

**隐私：** 音频不落盘。审计保存判定结果、置信度、耗时与转写文本；把 `store_transcript` 设为 `false` 则不存转写文本。通知不含快照和视频。

#### 快速验证

1. `curl -sf http://<ovs 地址>:8621/readyz` 返回 200。
2. 站在可能跌倒的位置能听清合成出来的提示音。

### 故障排查

| 现象 | 处理 |
|---|---|
| 每条告警都是 `no_answer` | 要么提示音听不见，要么没有采到音。先查扬声器，再在告警主机上跑 `arecord -l`。 |
| 每条告警都是 `unclear` | ASR 返回的文本没命中词表。在控制台里看转写内容，把住户实际的说法加进 `ok_keywords` / `help_keywords`。 |
| 告警自己结案了 | `on_ok` 被设成了 `dismiss`。除非确实有人在复核这些驳回，否则改回 `needs_review`。 |
| 服务起来了但从不出声 | 确认告警主机的音频设备已接入容器，在 `docker compose logs eldercare-alarm` 里查看 TTS 或播放报错。 |

