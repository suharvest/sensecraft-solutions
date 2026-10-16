## 套餐: Jetson 上的语音抓取 {#default}

部署一套语音控制的抓取机械臂：说 **"Hey Jarvis, grab the water bottle"**，reBot B601-DM 用腕部 RGB-D 相机找到目标并抓起来。唤醒词、语音识别、大模型、目标检测、抓取规划、臂控与语音回复全部在 Jetson 本地运行，无在线 API。

| 设备 | 用途 |
|--------|---------|
| reBot B601-DM | 六自由度机械臂，平行夹爪（最大开口 0.100 m）—— USB 串口 |
| Orbbec Gemini 2 | 腕装 RGB-D 相机（眼在手）—— USB 3.0 |
| reComputer J40 系列 | Jetson Orin NX 16GB，运行全部服务 |
| reSpeaker USB 麦克风 + 音箱 | 远场语音输入，TTS 回复输出 |

**你将获得：**
- 语音指挥抓取纸盒、直立（不透明）瓶子、香蕉、水杯、橙子
- 可识别物体列表通过配置修改，无需重新训练
- 实时面板：腕部相机画面 + 机械臂状态（`:8776`）
- 笛卡尔观测 API（`:8775/observation`），供其他方案集成

**开始之前（硬件清单）：**
1. 机械臂上电并连接 —— `ls /dev/ttyACM*` 能看到（通常 `/dev/ttyACM0`）
2. Gemini 2 接 **USB 3.0** 口（蓝色接口 —— USB 2 带宽不够，深度流异常）
3. reSpeaker 麦克风 + 音箱已接好；记下桌面用户 uid（`id -u`，通常 `1000`）
4. Docker + NVIDIA runtime（JetPack 6 标配）；磁盘剩余 ≥10 GB
5. 首次启动需联网，下载约 1.4 GB 容器镜像和约 8.5 GB 模型

> **中国大陆网络**：Step 1 的 *HuggingFace 端点* 请填 `https://hf-mirror.com` —— LLM 引擎、语音模型、抓取检测模型都从这里下载。

## 步骤 1: 部署整套服务 {#rebot_stack type=docker_deploy required=true config=devices/rebot_stack.yaml}

把语音、LLM、臂控和库存服务一次部署到 Jetson。

### 服务内容

部署后启动 `rebot-arm`（机械臂控制）、`seeed-voice`（语音识别与合成）和 `edge-llm`（大模型）三个服务，并自动下载抓取检测模型。

### 故障排查

| 现象 | 处理 |
|---|---|
| 抓取检测速度慢 | TensorRT engine 加载失败时会自动改用 ONNX Runtime，检测结果一致但更慢。`docker logs voice-rebot-arm` 第一行显示实际使用的版本。 |
| SSH 连接失败 | 检查 Jetson IP、SSH 用户名/密码，并确认 `22` 端口可以访问。 |
| 找不到机械臂串口 | 在 Jetson 上确认 `ls /dev/ttyACM*` 的结果，并更新机械臂串口字段。 |
| 首次启动时 `edge-llm` 长时间 unhealthy | TensorRT 引擎仍在下载或预热；可查看 `docker logs edge-llm`。 |

### 部署目标 {#rebot_stack_remote type=remote device=jetson device_name="Jetson" config=devices/rebot_stack.yaml default=true}

通过 SSH 部署到 Jetson。填写 Jetson IP 和 SSH 凭据，然后继续配置机械臂串口、音频用户 ID 和 HuggingFace 端点。

### 部署目标 {#rebot_stack_local type=local device=jetson device_name="Jetson（本机）" config=devices/rebot_stack.yaml}

直接部署到当前机器，仅在 app 或 CLI 运行在 Jetson 本机上时使用。填写机械臂串口、音频用户 ID 和 HuggingFace 端点。

首次启动需要下载并预热 LLM 引擎，慢速网络下 `edge-llm` 可能 10 分钟后才变 healthy，可看 `docker logs edge-llm`。

## 步骤 2: 打开面板 {#verify_dashboard type=web_dashboard verify=true required=true config=devices/verify_dashboard.yaml}

打开面板，确认实时相机画面、机械臂状态和语音链路正常。

### 部署完成

远端部署时填写 Step 1 使用的同一个 Jetson IP；本机部署时填写 `localhost`。面板地址是 `http://<jetson>:8776`。

- 相机画面在刷新：感知链路正常
- 状态 JSON 有值：串口链路正常

然后做端到端语音测试，对麦克风说：

> **"Hey Jarvis, wave"**

机械臂挥手、音箱播报确认，说明语音 + LLM + 臂控已全部打通。抓取还差最后一步：标定。

### 故障排查

| 现象 | 处理 |
|---|---|
| 没有相机画面 | Gemini 2 插在 USB 2 口，或相机被其他进程占用 —— 换 USB 3.0 口并重启 `rebot-arm` 容器 |
| 完全没有语音响应 | `docker logs voice-rebot-arm \| grep -i wake`；确认音频用户 ID 与 `id -u` 一致 |
| `edge-llm` 长时间 unhealthy | 引擎还在下载/预热 —— 首次启动属正常 |
| 磁盘被 `tegra-xusb: buffer overrun` 内核日志慢慢填满 | JetPack 驱动日志，不影响运行，但几周内可占用数 GB。过滤这些行：`echo ':msg, contains, "buffer overrun event for slot" stop' \| sudo tee /etc/rsyslog.d/30-tegra-xusb-spam.conf && sudo systemctl restart rsyslog` |

## 步骤 3: 手眼标定 —— 解锁抓取 {#handeye type=manual required=false}

使用抓取指令前，先完成一次性的手眼标定。

### 前置条件

每台设备需要单独标定。`/opt/rebot-models/hand_eye.npz` 生成之前，抓取指令能检测到物体但不会动臂。一次性，约 30 分钟：

1. 下载并打印[官方 ArUco 标定板 PDF](https://raw.githubusercontent.com/Seeed-Projects/reBot-DevArm-Grasp/main/aruco100x100.pdf)（DICT_4X4_50，ID 0，标称 100 mm），并**用尺子实测打印出来的黑色外框边长**——打印机会缩放。边长填错 1 mm 对应约 1 cm 抓取偏差。
2. 把标定板平贴在机械臂正前方约 65 cm 的桌面上。
3. 按[仓库 RUNBOOK §3.2](https://github.com/suharvest/openvoicestream/blob/main/agent/ovs_agent/apps/voice_rebot_arm/RUNBOOK.md) 执行采集 + 求解 —— 机械臂在板上方扫过约 16 个位姿后求解变换（目标平均误差 < 5 mm）。
4. 把生成的 `hand_eye.npz` 复制到 `/opt/rebot-models/`，重启 `rebot-arm` 容器。

### 第一次抓取

把一个小纸盒（每个面都小于 9.5 cm）放在机械臂正前方约 25–30 cm、大致居中的位置，说：

> **"Hey Jarvis, grab the box"**

机械臂会扫描、播报找到的目标、抓取、抬起并带回。然后可以试水杯、香蕉、橙子，再试直立的不透明瓶子。

**已验证的摆放**：正前方或中线左右适度偏移。**请用不透明物体**，深度相机看不到透明瓶子。

### 故障排查

| 现象 | 处理 |
|---|---|
| 偶尔提示找不到目标 | 某些角度下检测置信度偏低 —— 重复指令；把物体往中间挪。英文播报可能是 "I couldn't find the ..." |
| 播报物体太大、夹不住 | 所有可见面都超过 0.100 m 开口 —— 属预期行为，换小物体或把窄面转向机械臂。英文播报可能是 "too big for me to grip" |
| 第一次失败，重试就好 | 偶发情况，重试即可 |
| 抓取偏差几厘米 | 重新标定 —— 并重新实测打印标记边长（见上面第 1 条） |
| 机械臂关节报错（`status_code=12`） | 启动时会自动清除这个锁存故障；若容器重启后仍持续报错，再给机械臂断电重启 |
| 机械臂断电重启后不响应指令 | 执行 `docker restart voice-rebot-arm`，串口编号变化也能自动识别。 |
| 检测速度慢 | 已回退到 ONNX Runtime。先看 `docker logs voice-rebot-arm` 第一行，再看 `docker logs voice-rebot-arm-model-init-1` 里的原因 |
| 重启后又重新下载好几 GB | 不要用 `docker compose down -v`（会删除模型数据），改用 `down` 或 `restart` |
