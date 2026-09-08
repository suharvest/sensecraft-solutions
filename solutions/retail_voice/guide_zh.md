## 套餐: 设备本地转写 {#local_transcribe}

门店里一台盒子做完全部：采集、语音活动检测、转写、标点恢复和可选的声纹。转写结果以 JSON 文件写进这台盒子自己磁盘上的目录。没有云端账号，不上传，也没有数据库。

| 设备 | 作用 |
|--------|---------|
| reComputer RK3576 | SenseVoice 跑在 6 TOPS NPU 上，采集客户端跑在 CPU 上。这块板上的实测：3.0 s 音频热态约 780 ms 转写完成（RTF 0.26），标点与声纹全部加载常驻 1.71 GiB |
| reRouter CM4 | 更便宜的纯 CPU 选择。Paraformer 流式 ASR 跑在 4 个 Cortex-A72 核上，没有加速器，也不做语音合成 |
| reSpeaker XVF3800 | 4 麦阵列——回声消除、波束成形、噪声抑制在自带 DSP 上完成 |

**重要提示。** 这不是经过认证的转写产品，也不是合规控制手段。它产出的是方案页所记录质量的文本，不具备法律效力。在门店录音涉及的告知与同意义务，由你自行承担。

有两条已知弱点直接决定站点能不能用：稳态背景噪声**高于 70 dB** 时阵列的噪声抑制失效；说话人**超出约 3 m** 就落在波束成形的有效覆盖之外。换更快的板子解决不了其中任何一条。

**CM4 上的 ASR 速度与准确率尚未实测。** 上游 bench 矩阵里 CM4 的 `asr_zh_en` 行仍是 TBD。批量铺开这块板之前先做试点。

## 步骤 1: 烧录 OpenWrt 固件 {#firmware type=manual required=false}

仅 reRouter CM4 需要，RK3576 跳过。把系统写进 reRouter，然后接入网络。如果你的 reRouter 是 2025 年 11 月之后购买的，**跳过这一步**——出厂固件已经正确。

### 前置条件

- 电脑上装好 **rpiboot**，否则 eMMC 根本不会被识别
  - **Windows：** 运行 [rpiboot 安装包](https://github.com/raspberrypi/usbboot/raw/master/win32/rpiboot_setup.exe)
  - **Mac/Linux：** `git clone --depth=1 https://github.com/raspberrypi/usbboot && cd usbboot && make`
- 一根 USB-C **数据**线，两根网线

### 接线

![启动模式](gallery/boot-mode.png)

| 设备 | 连接 | 说明 |
|--------|------------|-------|
| reRouter CM4 | 拆开外壳露出板子 | 需要接启动跳线 |
| USB-C 线 | reRouter 接电脑 | 用于烧录 eMMC |
| 电脑 | 已装 rpiboot | 否则 eMMC 不会枚举 |

1. 拆下外壳，把 **Boot** 和 **GND** 用跳线短接进入启动模式
2. 接上 USB-C 线并运行 **rpiboot**——eMMC 会挂载成一个 U 盘
3. 下载固件。用下面这两个版本，LAN 地址才是 `192.168.49.1`：[国际版](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/OpenWRT-24.10.3-RPi-4-Factory.img.gz) · [中文版](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/OpenWRT-24.10.3-RPi-4-Factory-Chinese.img.gz)
4. 用 [Raspberry Pi Imager](https://www.raspberrypi.com/software/)（选 "Use custom"）或 [balenaEtcher](https://etcher.balena.io/) 写入
5. 拔掉跳线，装回外壳，接好线缆上电

![WAN 与 LAN](gallery/wan_lan.png)

**LAN** 口接电脑，**WAN** 口接路由器。1–2 分钟后 `http://192.168.49.1` 可以打开；用户 `root`，密码为空。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| `192.168.49.1` 打不开 | 网线插在 WAN 口了，或者固件不是上面链接的版本、用了别的地址 |
| rpiboot 认不到设备 | Boot-GND 跳线没接好，或者 USB-C 线只能充电 |
| 烧录中途失败 | 重新格式化目标存储再写一次 |
| 登录被拒 | 密码为空——什么都不填直接提交 |

---

## 步骤 2: 部署本地语音栈 {#deploy_local type=docker_deploy required=true config=devices/local_rk3576.yaml}

启动两个容器：8621 端口上的 OpenVoiceStream 语音服务，8090 端口上的采集客户端。没有别的。没有配置任何云端地址，也不需要填任何凭据。

部署过程会询问识别语种、输出目录、麦克风声卡编号，以及是否开启声纹标注和标点恢复。RK3576 目标上两者默认开启，上面那组实测数字本来就是两者都开的结果；CM4 目标上两者默认关闭，因为它们各自都要在 4GB 板子上常驻一个模型。

### 前置条件

- 板子**仅在本次部署时**需要联网。RK3576 上是镜像加约 825 MB 模型产物（502 MB SenseVoice RKNN、294 MB CT-Transformer、28 MB CAM++），2.5 MB/s 的链路上约 7 分钟；CM4 上是两个镜像加 CPU 模型集。之后这台盒子不需要上行链路。
- RK3576 至少 6GB 空闲，CM4 至少 4GB。
- 8621 和 8090 端口空闲。
- 仅 RK3576：RKNPU 驱动已绑定。部署会检查 `/sys/bus/platform/drivers/RKNPU`；在 Seeed 厂商内核上 `/dev/rknpu` 不存在**不是**故障。

### 接线

| 设备 | 连接 | 说明 |
|--------|------------|-------|
| reSpeaker XVF3800 | USB 接边缘设备 | 必须用 USB-A 主机口。reComputer 的 Type-C 是双角色口，可能处于 device 模式，那样什么都不会枚举。用 `lsusb` 确认，应显示 `2886:001a` |
| 边缘设备 | 网线接路由器 | 只在拉镜像和模型时需要。reRouter 上是 WAN 口 |
| 电脑 | 同一网段 | 用于 SSH 部署。reRouter 上接它的 LAN 口 |

部署前先记下 ALSA 声卡编号：SSH 进去运行 `arecord -l`，阵列显示为 **ArrayUAC10**，`card` 后面的数字就是部署时要填的值。

### 部署目标: reComputer RK3576 {#local_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576" config=devices/local_rk3576.yaml default=true}

通过 SSH 部署。板子的地址来自 DHCP，默认用户是 `recomputer`。语音服务后端固定为 RKNN。

### 部署目标: reRouter CM4 {#local_cm4_remote type=remote device=rerouter device_name="reRouter CM4" config=devices/local_rerouter.yaml}

通过 SSH 部署到 reRouter。默认地址 `192.168.49.1`，用户 `root`，出厂镜像密码为空。CPU 识别，没有加速器。

已退役的 smart_retail_voice_ai 建议在 reRouter 上部署完重启一次设备。这里不需要：部署执行的 `/dev/snd` `chmod` 立即生效。它也不持久——设备节点在开机时重建——所以重启后如果采集不工作，重新执行一次 `chmod -R 666 /dev/snd/*`。任何一次重启后，等服务起来约两分钟再打开客户端页面。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| reRouter 上 SSH 拒绝连接 | 网线插在 WAN 口了，或者地址不是 `192.168.49.1` |
| reRouter 上认证失败 | 出厂 OpenWrt 镜像 root 无密码——密码栏留空 |
| 预检报 "RKNPU driver not bound" | 这块板不是 RK3576，或者内核没有 NPU 驱动。原因不是缺 `/dev/rknpu`——检查读的是 `/sys/bus/platform/drivers/RKNPU` |
| 拉镜像超时 | 设备到镜像仓库不通。先在设备上 `ping` 通了再重试 |
| `speech` 好几分钟一直 unhealthy | 首次启动下载模型集时的正常现象。用 `docker logs -f openvoicestream` 跟踪 |
| 模型下载卡住 | 把模型下载源在 HF 镜像和 huggingface.co 之间切换后重新部署 |
| `voice-client` 起不来，提示镜像找不到 | `c4-local` tag 尚未发布。请从 sensecraft-voice-client 的 `feature/c4-harden` 分支构建并打上该 tag，或设置 `VOICE_CLIENT_IMAGE`。真机核实（2026-09-06，RK3576 `cat-remote`，该设备本地已缓存 `sensecraft-voice-client:ovs-20260901b`）：这个 tag 同样支持 `vad=none` 本地 VAD、`asr_cache`、`speaker_embedding`，把 `VOICE_CLIENT_IMAGE` 指向它可以直接顶替、不用重新构建——但这个 tag 没有发布到任何 registry，只确认在那一台设备上存在 |
| `lsusb` 里看不到 reSpeaker | 换到 USB-A 主机口。`dmesg \| tail` 出现 `xhci-hcd` 总线注销，说明双角色控制器切到了 device 模式 |
| CM4 上内存不足 | 把声纹和标点都设为关闭——它们各自要在 4GB 里常驻一个模型 |
| RK3576 上容器因内存压力被杀 | `mem_limit` 是按 3.82 GiB 的板子设的 3000m。如果这块板还跑别的负载，先关标点 |
| 每次重启都重新下载模型 | 命名卷被删了。特别是 `rk-sensevoice-rknn` 里存着 502 MB 的产物，没有它每次重建都会重下。另外 `rk-asr-models` 是个通用卷名，同一台设备上其他基于 OVS 的 RK3576 方案也会用到它（在 `cat-remote` 上实测发现与 `conversational_voice_ai` 部署共用）——它是跨方案共享的，不是本方案专属，对这套 compose 执行 `docker compose down -v` 会连带删掉那个方案缓存的模型 |

---

## 步骤 3: 检查本地转写结果 {#verify_local type=manual verify=true required=true config=devices/verify_asr.yaml}

对着阵列说一句话，然后确认设备上出现了文件。

### 验证

1. 站在 reSpeaker 约 3 m 以内，用选定的语种说一句完整的话
2. 说完静默两秒左右——本地 VAD 需要 0.7 s 静音才会结束这一句
3. 在设备上运行 `ls -lt <输出目录>/cache/asr/ | head`，应看到一个带当前时间戳的新 `.json` 文件
4. `cat` 打开它：`text` 字段就是你说的内容；开启标点时带标点，开启声纹时还会有 `speaker` 字段
5. 在门店局域网内打开 `http://<设备IP>:8090/`，同一句话会出现在实时视图里

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 没有文件生成，网页也是空的 | 在设备上运行 `arecord -l`。看不到 ArrayUAC10 说明阵列接在非主机 USB 口上（reComputer 上就是 Type-C 那个）；能看到但编号和你填的不一致，就用正确编号重新部署 |
| RK3576 上 `backend` 不是 `rk:sensevoice_rknn` | NPU 路径没加载。确认 profile 传进了容器：`docker exec openvoicestream env \| grep OVS_PROFILE` |
| `curl -F "file=@sample.wav" http://<设备IP>:8621/asr` 返回的文字正确，但没有文件写出 | 识别器没问题，音频通路有问题——检查声卡编号和 `docker logs sensecraft-voice-client` |
| 转写是一整行没有断句的文字 | 标点恢复关着。如果板子内存够就开启它 |
| 每句开头的字被吃掉 | CM4 上是本地 VAD 切早了：客户端配置里 `speechPadSeconds` 默认 0.5 s，不要拿几条录音去精调它。RK3576 上说明服务端 VAD 开着了——本套餐要求 `OVS_VAD_BACKEND=none`、由客户端本地断句，服务端 VAD 每个切点大约丢一个音节 |
| 房间很吵、识别很差 | 测一下背景噪声。高于约 70 dB 时阵列分不出说话人，改配置不改变这一点 |
| 刚重启完 `:8090` 打不开 | 等服务起来约两分钟再刷新 |
| 客户端页面上的录音按钮点了没反应 | 语音服务还在加载模型。`curl http://<设备IP>:8621/readyz` 返回就绪即可 |
| CPU 满载、转写落后于说话 | CM4：先关标点，再关声纹。那块板子按设计一次只跑一路识别 |

### 部署完成

门店盒子现在在本地转写了。

#### 快速验证

1. `docker ps`——`openvoicestream` 和 `sensecraft-voice-client` 都是 `Up`
2. `curl http://<设备IP>:8621/readyz` 返回就绪状态；RK3576 上 `curl -F "file=@sample.wav" http://<设备IP>:8621/asr` 的返回里还应带 `"backend":"rk:sensevoice_rknn"`
3. `<输出目录>/cache/asr/` 下存在带你那句话的 `.json` 文件
4. 拔掉网线，再说一句，确认仍然有新文件生成——这就是"只在本地"这句话的实测

#### 下一步

- 给 `<输出目录>` 定一个保留期并落实。那个目录没有任何轮转机制
- 如果不需要音频，把客户端配置里的 `voice.output` 改成 `stream`，只写文字
- 想要稳定的声纹标签而不是自动生成的编号，就在客户端页面上把常驻人员注册一遍
- 在真正的收银台位置再做一次噪声和距离检查，然后再铺更多站点
- 如果站点之后需要跨门店查询、导出或硬删除接口，那是「服务端栈」套餐——同样的硬件，前面加一个数据库和一层服务

---

## 套餐: 服务端栈 {#cloud_stack}

一台主机跑完整链路：语音识别、声纹、入库前脱敏的服务、MySQL、MinIO，以及带导出和硬删除的管理后台。它是一台机器上的一次部署——compose 是一个整体，自带数据库和对象存储，之后没有东西需要往上加。

所以音频从哪来这件事，是**在步骤 1 里选部署目标时一次性决定的**，不是第二次部署：

- **来自你已有的手机 App**——选「栈主机」目标。这套栈对外提供 ASR 端点供 App 指向，本机不跑采集客户端。接着做步骤 2 把端点交给 App。
- **来自本机上的麦克风阵列**——选 reComputer RK3576 或 reRouter CM4 的采集目标。同一套栈，外加一个绑定到阵列的采集客户端。

**两者可以同时用。** ASR 端点在四个目标上都是开着的，所以选了麦克风目标之后，再让 App 指向同一台栈主机是可以的——那需要**两件事都做**：选麦克风目标，再完成步骤 2。只用阵列就不必做步骤 2。

不会出现两条都没选的情况：步骤 1 是必选的，而每个目标至少带来一条采集路径。也不会出现两套数据库，因为自始至终只有一次部署。

| 设备 | 用途 |
|--------|---------|
| 栈主机（reComputer RK3576，或其他 arm64 Linux 主机） | ASR、voice-service、MySQL、MinIO、管理后台 |
| 手机 App（你的，不在本包内） | 采集音频并上传到 ASR 端点 |
| reSpeaker XVF3800 + reComputer RK3576 或 reRouter CM4 | App 之外的采集端选择 |

**重要：** 这不是合规认证。脱敏只覆盖文本——音频在保留期内是未脱敏的，但被删除流程覆盖。脱敏在 114 条金标准集上的成绩是 precision 0.98 / recall 0.95，也就是会漏；低置信实体是标记复核而不是遮蔽。说话人识别默认是关的：声纹容器的镜像已发布，两个麦克风采集目标会在部署时尽力自动拉取它需要的模型
（约 564MB）；栈主机（App 采集）目标没有这一步，仍要手动放好——见步骤 2 的前置条件。不管哪种方式，模型没就位、`voiceprint` profile 没启动之前，`speaker.identified`
恒为 false。

## 步骤 1: 部署语音服务端栈 {#deploy_stack type=docker_deploy required=true config=devices/cloud_stack.yaml}

拉取冻结镜像，在设备上写 `.env` 与服务配置，启动 MySQL、MinIO、ASR 后端、
voice-service 与管理后台。

### 前置条件

1. 一台装了 Docker、SSH 可达、至少 20 GB 可用空间的 arm64 Linux 主机。
2. 开始前先生成四个密钥——各执行一次 `openssl rand -hex 32`——分别用于
   JWT key、operator 令牌、admin 令牌、MinIO 私有密钥。
3. 现在就定下保留期。原音频默认 24 小时，部署表单还提供 6 小时与 1 小时；
   之后再改要编辑设备上的 `config/voice-service.yaml` 并重启 voice-service。
4. 首次部署要拉好几 GB 镜像，其中大部分是语音容器。网络慢的话，
   部署里耗时最长的是这一段，不是启动。
5. 主机必须是 arm64。冻结镜像没有 amd64 变体，随包的 ASR 镜像是 RK3576 NPU 构建。
6. 所有镜像（voice-service、voice-web、ASR/声纹镜像、MySQL、MinIO）都已发布，
   compose 文件里按 digest 固定。例外是声纹容器的模型——它的镜像已发布，
   但模型文件只在两个采集端（麦克风）目标上自动拉取；栈主机目标不会（见下文）。

### 接线

仅两个麦克风采集目标需要。App 采集目标上没有阵列要接，这一节不适用。

1. 部署之前先把 reSpeaker XVF3800 插到盒子的 USB 口上。
2. 执行 `cat /proc/asound/cards` 记下声卡编号——它要填进 ALSA 声卡编号字段。通常是 1，接了别的音频设备就会变。
3. 把阵列放在对话发生的位置：收银台或服务台，距离约 1 米。波束成形解决的是方向问题，不是距离问题。
4. 不要放在会传导盒子风扇振动的台面上。
5. 不要再接第二个麦克风。链路是单路采集的，多一块声卡只会让声卡编号变得不确定。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| `up -d` 停在 ASR 镜像上 | 镜像很大、registry 可能慢；重跑部署，已拉到的层会续上 |
| voice-service 一直不健康 | `docker logs c4-voice-service`——常见原因是 `config/voice-service.yaml` 里还留着 `CHANGE_ME_` 占位符，或 `.env` 与配置文件里的 MySQL 口令不一致 |
| 所有 API 调用都 401 | 你发的令牌不在 `VOICE_API_TOKENS` 里；格式是 `name:role:token`，逗号分隔 |
| 返回的是 403 而不是 401 | 凭据有效但角色档位不够——删除与导出需要 admin |
| 别的机器连不上 MySQL | 有意为之：MySQL 与 MinIO 只绑 127.0.0.1。要远程连走 SSH 隧道 |
| 8080 上的 `/ws` 连不上 | 声纹容器在 `voiceprint` profile 里默认不启动；如果你开了这个 profile，检查模型是否放好——见步骤 2 的前置条件 |
| 声纹容器报 `tokens.txt does not exist` 退出 | reRouter CM4 / reComputer RK3576 采集端目标的部署现在会自动把模型下到 `/data-iot/respeaker/models`（`before` 阶段的一步，尽力而为——失败只告警不中断部署）。先查那一步日志里有没有 `MISSING`，常见原因是设备连不上 `hf-mirror.com`。手工补下：`cd /data-iot/respeaker && HF_ENDPOINT=https://hf-mirror.com` 加上同样的下载循环（见 `devices/collector_rerouter.yaml`），或去上游 `sensecraft-asr-service` 仓库跑 `download_models.sh`，把产物拷到 `/data-iot/respeaker/models` |
| 莫名出现云端分析容器 | 它只在 `--profile cloud-analytics` 时启动；如果在跑，说明有人开了它，文本正在离开这台主机 |
| 麦克风采集目标：voice-client 反复重启 | ALSA 声卡编号不对；在设备上 `cat /proc/asound/cards`，用正确的编号重新部署 |
| 麦克风采集目标：容器在跑但没有转写 | `docker logs c4-voice-client`——看它是否连上了 8621 的 ASR 后端，以及令牌是不是 operator 那条 |
| `/data-iot/respeaker` 权限不足 | 部署会建这些目录；如果它们此前已存在且属主是 root，执行 `chmod -R 0775 /data-iot/respeaker` |
| reRouter CM4 目标要换 ASR 镜像 | `OVS_ASR_IMAGE` 现在默认是 `rpi-20260721` 的 arm64 CPU 构建（按 digest 固定）；要跑别的构建时才在部署输入里覆盖 |
| CM4 上全都在跑但转写是空的 | CM4 这条路径本包未验证。这个目标的 `ovs-asr` 内存上限已调低到 3000m/3600m（`.env` 里的 `OVS_ASR_MEM_LIMIT`/`OVS_ASR_MEMSWAP_LIMIT`，默认值原本按 8 GB 的板子写的是 7500m），但这个数值同样没有在 CM4 上实测——查 `docker logs c4-ovs-asr` 有没有被 OOM kill，主机有余量的话再调高 |

### 部署目标: {#stack_remote type=remote device=stack_host device_name="栈主机（App 采集）" config=devices/cloud_stack.yaml default=true}

音频来自你的 App。通过 SSH 部署到网络上的一台主机；这套栈对外提供 ASR 端点，本机不跑采集客户端。接着做步骤 2。

### 部署目标: {#stack_local type=local device=stack_host device_name="栈主机（App 采集）" config=devices/cloud_stack.yaml}

同样是 App 采集的那套栈，部署到本机，适用于栈就跑在你操作的这台机器上。同一份 compose、同样的输入，不需要 SSH 凭据。

### 部署目标: {#collector_rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576（麦克风采集）" config=devices/collector_rk3576.yaml}

音频来自本机上的麦克风阵列。同一套栈，外加绑定到阵列的采集客户端，走 NPU 路径——ASR 后端是 RK3576 构建，不需要额外输入。只用阵列的话步骤 2 不必做；还要同时接 App 就接着做步骤 2。

### 部署目标: {#collector_rerouter_remote type=remote device=rerouter device_name="reRouter CM4（麦克风采集）" config=devices/collector_rerouter.yaml}

同一套栈加采集客户端，走 CPU 路径。它那份 compose 变体把 ASR 镜像作为必填输入，因为本包没有为 CM4 固定镜像。未在真实硬件上验证。只用阵列的话步骤 2 不必做；还要同时接 App 就接着做步骤 2。

---

## 步骤 2: 在手机 App 里配置 ASR 端点 {#asr_endpoint type=manual required=false config=devices/asr_endpoint.yaml}

仅当有 App 上传音频时需要——不论步骤 1 选的是「栈主机」目标，还是已经选了麦克风采集目标又想再接一个 App。把端点和 operator 令牌交给 App，然后自己连一次确认端点会应答。只用麦克风阵列就跳过这一步。

### 前置条件

1. 先让 App 侧告诉你三件事：它的 ASR 客户端拼出来的 WebSocket 路径与查询参数格式、
   它怎么传凭据（自定义头、`Authorization: Bearer`，还是查询参数）、
   它上传的音频格式。App 配置页里有本页没有对应项的字段，按 App 配置页的说明填写。
2. 本端点这三条凭据通道都收，音频要求原始 PCM 二进制帧：16 kHz、单声道、
   有符号 16 位小端，单条消息不超过 2 MiB。不是这个格式就要在 App 侧转换。
3. 端点地址是 `ws://<栈主机>:8080/ws?token=<operator 令牌>`。
   交出去的是 operator 令牌，绝不是 admin 令牌。
4. 连上之后服务端会先发
   `{"type":"connection","message":"WebSocket connected, ready for audio","session_id":"..."}`；
   采集过程中发 `{"type":"vad","status":"speech_detected"|"silence",...}`，
   每句话一条 `{"type":"final","text":...,"speaker":{...}}`。
5. 出了局域网就在前面终结 TLS，交给 App 的换成 `wss://`——令牌是走查询参数的。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 还没升级连接就以 HTTP 401 断开 | 令牌没带或不对——鉴权发生在 WebSocket 升级之前，这是设计如此 |
| 返回的是 HTTP 403 | 令牌有效，但是 viewer 档；`/ws` 要 operator |
| 连上了但永远等不到 `final` | 音频不是 16 kHz 单声道 16 位 PCM，或者 App 发的是编码格式（带 WAV 头、Opus、AAC）——本端点收的是原始采样 |
| 静音约 20 s 后连接断开 | 读超时；客户端要持续发帧或重连 |
| 帧因过大被拒 | 单条消息上限 2 MiB——发小一点，链路按 4 KB 左右调过 |
| `speaker.identified` 恒为 false | 声纹容器没跑时属预期 |

---

## 步骤 3: 打开管理后台 {#admin_web type=web_dashboard required=false config=devices/admin_web.yaml}

打开 `http://<栈主机>:3000/`——录音、关键词、设备、导出与删除都在这里。

### 前置条件

1. 第一个账号用 admin API 令牌创建：
   `curl -X POST -H "X-API-Token: <admin 令牌>" -H "Content-Type: application/json" -d '{"username":"ops","password":"<口令>"}' http://<栈主机>:8081/api/v1/users/register`。
2. 这个账号建出来是 **viewer**——能读，不能删除或导出。用改角色接口把它提到
   admin（调用本身也要 admin 凭据）：
   `curl -X PATCH -H "X-API-Token: <admin 令牌>" -H "Content-Type: application/json" -d '{"role":"admin"}' http://<栈主机>:8081/api/v1/users/<id>/role`。
   `<id>` 用同一个 admin 令牌调 `GET /api/v1/users?username=ops` 查，然后重新
   登录拿带新角色的令牌。服务本身不允许把最后一个 admin 降级（返回
   409），所以这条路径不会把账号锁在角色接口外面。
3. 后台展示的全部是脱敏之后的内容。任何地方都看不到原文，因为它从来没被存过。
4. 用采集端时，它注册的设备会出现在「设备」里，按 MAC 标识。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 登录返回服务端错误 | `jwt_key` 还是占位符——签不出登录令牌，服务选择报错而不是回一个空 token |
| 登录成功但删除、导出按钮 403 | 账号是 viewer；按上面的办法用改角色接口提权 |
| 后台能打开但列表为空 | 还没有任何上报，或者浏览器指向的主机与 App、采集端上报的不是同一台 |
| 后台里没有任何设备 | 采集端还没上报过——说一句话再刷新 |
| 后台能访问但 API 不通 | voice-web 在 3000、voice-service 在 8081，主机上两个端口都要放开 |

---

## 步骤 4: 验收转写与删除 {#verify_stack type=manual required=true verify=true config=devices/verify_stack.yaml}

说一句话，确认落库的是脱敏后的内容，删掉它，再证明删干净了。

### 前置条件

1. 说一句带电话号码的话：「我叫张伟，手机号是 13812345678」——通过 App，
   或对着采集端的麦克风阵列，说完停下；语音段是靠静音结束的。
2. 看最新一条——号码必须显示为 `[[PHONE]]`、姓名显示为 `[[NAME]]`，
   且 `pii_masked_count` 大于 0。
3. 用 admin 令牌调 `POST /api/v1/privacy/erase` 删掉它。返回里必须是
   `"status": "complete"`、`"residue_count": 0`，且没有 `failed_steps`。
   级联步骤失败时接口仍返回 HTTP 200——判断这次删除算不算数看的是 `status`。
   `status: partial` 表示有东西没删掉（MinIO 对象、声纹、或墓碑），
   此时 `residue_count` 会把它们一并计入，不会是 0。
4. 用采集端时，确认本地音频目录 `/data-iot/respeaker/recordings` 里已经没有
   被删会话的文件——这是三处存储里的第三处。
5. 把 `assets/tools/delete_proof.sh` 拷进 `sensecraft-voice-service` 仓库再跑
   （脚本往上找到第一个 `go.mod` 作为仓库根，放 `tools/` 或 `assets/tools/` 都行；
   也可以显式指定 `REPO_ROOT=`）。
   它自己起 MySQL 与 MinIO（容器名前缀 `c4-proof-`，不碰既有编排），
   造数据、删一个主体、再核三处。通过条件是 `RESIDUE_COUNT=0` 且 `RESIDUE_DB_REPORTED=0`。
6. 这个脚本证明的是代码路径，不是你现场的数据。两项检查都要做。

### 故障排查

| 问题 | 解决办法 |
|-------|----------|
| 用采集端时完全没有转写 | 先查 ALSA 声卡编号，再看 `docker logs c4-ovs-asr` 的模型加载 |
| 有转写但被截断 | 服务端 VAD 按静音切段，单段最长 10 s |
| 数据库里能看到原始手机号 | 脱敏被关了——检查 `config/voice-service.yaml` 里的 `privacy.redaction_enabled`，然后停下来重查已入库的全部内容 |
| 有个姓名没被遮蔽 | 金标准集上的 recall 是 0.95；低置信实体是标记而不是遮蔽。先看 `pii_review_count` 再判定是 bug |
| 残留数不为 0 | 数据库之外有东西没删掉——MinIO 对象或声纹。读 `failed_steps` 与 `errors`，按删除失败处理 |
| `status` 是 `partial` | 至少有一个级联步骤失败。`voiceprint_delete` 是声纹服务不可达，`object_delete` 是 MinIO，`tombstone_write` 是删了但没留下凭证。修掉原因后重跑 erase，该接口是幂等的 |
| 删除成功但声纹还在 | 声纹服务没跑（未开 `voiceprint` profile）时属预期——级联没有可调用的对象，此时响应会给出 `status: partial` 与非零残留，而不是一个干净的 0 |
| 行已脱敏但删除后音频文件还在盘上 | 读删除返回里的 `errors` 字段——对象删除失败就是删除失败，不是部分成功 |
| 24 小时后音频仍然在 | 保留期由服务配置执行；确认 `config/voice-service.yaml` 里的 `raw_audio_retention_hours` 与你选的一致 |
| `voiceprint_delete` 报 `connection refused` | `config/voice-service.yaml` 的 `asr.base_url` 必须写 compose 服务名 `http://asr-voiceprint:8080`，不能写 `127.0.0.1`——voice-service 在自己的网络命名空间里，`127.0.0.1` 指的是它自己 |
| 一口气念出的手机号没被遮蔽 | ASR 把它转写成中文数字词（「幺三八幺二三四五六七八」）而不是阿拉伯数字。`cn_mobile_spoken` 规则覆盖 11 位手机号形态；这样念出的身份证号、座机号仍未覆盖——见方案描述里的「已知限制」 |
| `delete_proof.sh` 报 `go.mod file not found` | 脚本不在 `sensecraft-voice-service` 检出目录里。拷进去，或用 `REPO_ROOT=/path/to/sensecraft-voice-service` 运行 |
| `delete_proof.sh` 连不上 Go 模块代理 | 它默认传 `GOPROXY=https://goproxy.cn,direct`；网络有别的要求就覆盖 `GOPROXY` |

### 部署完成

栈已经在跑，并且有一个主体走完了上报、脱敏、删除、证明删干净的全过程。
文本上报与查询在 `http://<栈主机>:8081/api/v1/recordings`，
删除与导出在 `/api/v1/privacy/*`，后台在 3000 端口。

#### 快速验证

1. 栈主机上 `docker ps` 能看到 `c4-mysql`、`c4-minio`、`c4-ovs-asr`、
   `c4-voice-service`、`c4-voice-web` 都在跑；部署了采集端时还有 `c4-voice-client`。
2. `curl -sf http://<栈主机>:8081/healthz` 正常返回；麦克风采集目标上 `curl -sf http://<栈主机>:8621/health` 也正常返回——那是采集客户端喂的那个识别器。
3. 不带令牌的请求返回 401；用 viewer 令牌调删除接口返回 403。
4. 最新一条录音里是占位符，不是原始个人信息。
5. 删除接口返回 `status: complete` 且残留数为 0（`partial` 加非零残留
   表示这次删除没有被证明）；用采集端时，盘上的音频文件也已消失。

#### 后续步骤

1. 任何内容离开局域网之前，先在 ASR 端点前面加 TLS 终结。
2. 在真实硬件上跑边界测试——并发、连续时长、WER、落库时延目前都没测，
   所以现在不能用这套部署给出任何容量结论。
3. 声纹镜像已发布；采集端目标（reComputer RK3576 / reRouter CM4）的部署
   现在会自动把它的模型（SenseVoice ASR、标点、声纹、VAD，共约 564MB）
   下载到 `/data-iot/respeaker/models`——这一步是尽力而为，设备连不上镜像
   只会告警，不会中断部署。启动 `asr-voiceprint` 之前先看这一步的日志；
   服务端栈（Stack Host / 手机 App 采集）目标没有这一步，模型仍要手工拷进去。
   然后用 `docker compose --profile voiceprint up -d asr-voiceprint` 起它——
   不放模型会以 `tokens.txt does not exist` 报错退出——再在有声纹的情况下
   重跑一次删除检查。
4. 和现场隐私告知的负责人一起定保留期；24 小时是默认值，不是建议值。
5. CM4 上先把 CPU 版 ASR 路径端到端验一遍。它的 `ovs-asr` 内存上限现在
   可以通过 `OVS_ASR_MEM_LIMIT`/`OVS_ASR_MEMSWAP_LIMIT` 配置，该目标默认
   3000m/3600m，但这个数值是比照另一块 RK3576 板子的实测抄来的，
   没有在 CM4 上实测——确认它扛得住之后再把这个目标当作可用。
6. admin 令牌不要留在设备上；它是给跑删除与导出的运维用的。
