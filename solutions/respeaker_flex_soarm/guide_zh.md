## 套餐: 语音控制你的 SO-ARM {#default}

一步部署语音控制机械臂：Jetson 上的一个 Docker 容器同时承载唤醒、语音识别、LLM 推理、TTS 回复和 SO-ARM 控制。

| 设备 | 用途 |
|------|------|
| SO-ARM101 从动机械臂 | 六自由度机械臂，通过 USB 串口接收 `send_action` |
| reComputer Super J4012 | Jetson Orin NX 16GB，跑语音 + 机械臂容器 |
| reSpeaker Flex XVF3800 | 4 麦阵列，远场语音采集 |
| 音箱 | 输出助手的语音回复 |

**你将获得：**
- 一只能用自然语言指挥的机械臂
- 唤醒词激活（"Hey Jarvis"），只在被叫到时听
- 完全本地的 AI 栈：Paraformer 语音识别 + Qwen3-4B-AWQ 推理 + Matcha 语音合成，全部跑在 Jetson GPU
- 命名姿态库 + 手势序列库，YAML 可编辑，不用重构镜像
- `GET /observation` 提供实时关节状态供其他方案集成

**前置条件：** SO-ARM101 · Jetson Orin NX 16GB · reSpeaker Flex XVF3800 · 音箱 · 首次启动需联网（拉镜像 + 预热引擎）

> 首次部署需 5-10 分钟，用来拉取约 10 GB 镜像并预热 Qwen3 TensorRT 引擎；之后每次启动都是秒级。

## 步骤 1: 机械臂初始化（仅首次） {#arm_prep type=manual required=false}

全新的 SO-ARM 套件先按上游 Wiki 做完 3 件事，容器才能正确驱动。这条臂之前做过就跳过本步。

### 接线

在 Jetson（或任意能 USB 接到机械臂的 Linux 主机）上按上游教程依次完成下面 3 件事。每一项都有完整步骤 + 配图。

1. **[找 USB 端口](https://wiki.seeedstudio.com/lerobot_so100m_new/#find-the-usb-ports)** —— 跑 `lerobot-find-port` 确认机械臂在哪个 `/dev/ttyACM*`
2. **[分配舵机 ID](https://wiki.seeedstudio.com/lerobot_so100m_new/#configure-the-motors)** —— 出厂舵机都是 ID 1，按提示一颗一颗接，自动烧成 1–6
3. **[校准](https://wiki.seeedstudio.com/lerobot_so100m_new/#calibrate)** —— 摆到中位 + 扫各关节全行程，让数值归一化到 -100..100（身体关节）/ 0..100（夹爪）

校准文件会落在 `~/.cache/huggingface/lerobot/calibration/robots/so_follower/<arm_id>.json`。注意 `<arm_id>` 要跟步骤 2 里的 `ARM_ID` 保持一致。

### 故障排查

| 问题 | 解决办法 |
|------|----------|
| 命令动作时只有夹爪抖一下 | 舵机 ID 没分配，按上面表里的 Configure the Motors 重做 |
| `/observation` 返回的不是 -100..100 而是 1500、2048 | 没做校准，按 Calibrate 重做。不做的话演示能跑但数值不是归一化的 |
| 中位严重漂移、`Magnitude exceeds 2047` 之类的报错 | 跑 [Seeed_RoboController](https://github.com/Seeed-Projects/Seeed_RoboController) 的中位校准工具，再重做 Calibrate |
| 校准是在别的机器上做的 | 把 `~/.cache/huggingface/lerobot/calibration` 挂进容器（`-v` 同路径），让容器运行时能读到 JSON |

## 步骤 2: 部署语音机械臂容器 {#voice_arm type=docker_deploy required=true config=devices/voice_brain.yaml}

把语音 + 机械臂容器部署到 Jetson。容器首次启动时会探测 SO-ARM 串口和麦克风，没有用户配置就拷贝默认的 `actions.yaml` / `prompt.yaml`，然后启动语音 pipeline 和 8765 端口上的观测 HTTP 服务。

### 故障排查

| 问题 | 解决办法 |
|------|----------|
| Docker 没装 | JetPack 6.x 默认带 Docker，`docker --version` 确认 |
| 容器秒退 | `docker logs voice-arm` —— 通常是 `seeed-voice` 或 `edge-llm` 还没健康检查通过。首次启动等 5-10 分钟让 Qwen3 引擎预热完成再重试 |
| 唤醒词不响应 | 部署**之前**先把 reSpeaker 插上；`docker logs voice-arm` 看自动选中的麦克风 |
| 机械臂不动 | 确认 SO-ARM USB-C 已连接（通常是 `/dev/ttyACM0`）；容器会扫描 `/dev/ttyACM*`，日志里有最终绑定的端口 |
| TTS / STT 报错 | `docker logs seeed-voice` —— 首次启动模型下载可能尚未完成 |
| LLM 无响应 | `docker logs edge-llm` —— 首次启动会下载 Qwen3 TensorRT 引擎（约 5 GB）并跑一次预热推理才会变 healthy |

### 部署目标 {#local type=local config=devices/voice_brain.yaml}

### 部署目标 {#jetson type=remote config=devices/voice_brain.yaml default=true}

## 步骤 3: 验证机械臂状态 {#verify_arm type=robot_inspect verify=true required=true config=devices/verify_arm.yaml}

实时查看 SO-ARM 的关节状态，并在线给它教新的手势。面板会以 5Hz 轮询 `GET /observation`，展开"详细数据"可以看到完整 JSON。下方的动作录制器可以在运行时给手势库加新条目 —— 不用重构镜像。

### 默认支持的语音指令

开箱即用，机械臂已经认识下面这些手势。先说唤醒词 **"Hey Jarvis"**，再说指令即可（说法不用一字不差 —— LLM 按意图匹配，不是关键词匹配）。这些指令之后都可以改、删、加（见下方「教它新手势」）。

| 手势 | 可以这么说 |
|------|-----------|
| 回原位 / 复位 | "回到原位"、"复位" |
| 准备抓取 | "准备抓取"、"摆到抓取位" |
| 张开夹爪 | "张开"、"松开" |
| 闭合夹爪 | "闭合"、"抓紧" |
| 抬头 | "抬头"、"向上看" |
| 低头 | "低头"、"向下看" |
| 挥手 | "打招呼"、"挥手" |
| 点头（表示"是"） | "点头"、"同意" |
| 摇头（表示"否"） | "摇头"、"不行" |

### 验证

1. 机械臂静止时确认六个 `*.pos` 字段都是有限数字（不是 `NaN` 也不是 "—"）
2. 说一句 **"Hey Jarvis, wave hello"** —— 值应该跟随机械臂动作变化
3. （可选）试一下动作录制器：
   - 点 **关扭矩**，这样可以徒手摆动机械臂
   - 摆好姿势，起一个动作名（例如 `high_five`），在 **触发短语** 里写一句话说明这个动作**什么时候**该触发（例如：「当用户说 'high five'、'击个掌' 时触发」）。这句话会作为 LLM 工具描述使用 —— **留空的话语音模型永远不会调用这个新动作**
   - 点 **观测 → 添加** 把当前姿态快照成一帧。如果是多步手势就继续添加帧
   - 点 **开扭矩**，再点 **测试动作** 验证播放效果，确认后点 **完成保存** 落盘
   - 说 "Hey Jarvis, high five" —— 模型下次请求时会拿到新工具并触发

### 故障排查

| 问题 | 解决办法 |
|------|----------|
| 面板显示降级提示 | 容器还没起，或者 8765 端口不可达。确认 Step 1 完成并且 Jetson IP 可达 |
| 字段全是 `NaN` | SO-ARM 串口没绑定。拔插 USB 重启容器 |
| 机械臂动了但数值不变 | 容器接到了错误的设备。`docker logs voice-arm` 查实际绑定端口 |

### 部署完成

你的 SO-ARM 现在能用语音控制了，试试说「Hey Jarvis，挥个手」。

#### 教它新动作

想加新手势，去**第 2 步「实时状态」面板**右下的**动作录制器**：

1. **先点「关扭矩」**（在录制器上方的"扭矩"行）—— 扭矩开着的时候硬掰会扭坏舵机
2. 手动把机械臂摆成姿态 → 点「观测→添加」记录一帧
3. 摆下一帧再加一帧，起个名字、写一句**触发短语**（比如「击个掌」）
4. 点「完成保存」—— 容器自动重建（约半分钟），期间唤醒词不响应
5. 想试试录的动作，点「测试动作」会自动开扭矩并执行

下次说出那句触发短语，机械臂就会做这个动作。

#### 改默认动作 / 改对话风格

去**设备管理 → 软件大脑 → ⚙ 配置**，能看到两个可编辑的配置：

- **动作库** —— 已学会的所有手势。改一改让动作幅度更大 / 更小，或删掉用不到的。
- **对话规则** —— 系统提示词，决定它回话的语气和习惯（比如让它说更短、更礼貌、用方言）。

保存后大约半分钟生效，期间唤醒词不响应。

#### 让其他系统读机械臂状态

同一局域网下，任何程序都能拉到实时关节数据，做数字孪生、动作录制、远程监控之类：

```bash
curl http://<jetson-ip>:8765/observation
# {"shoulder_pan.pos":0.12, ..., "gripper.pos":0.1}
```

#### 后续

- 硬件搭建细节看 [SO-ARM Wiki](https://wiki.seeedstudio.com/respeaker_flex_soarm/)
- 出问题先 `docker logs voice-arm` 看日志
- 唤醒词容易误触发或难触发，去设备配置里调灵敏度（`WAKEWORD_THRESHOLD`）和冷却时间（`WAKEWORD_COOLDOWN`）
