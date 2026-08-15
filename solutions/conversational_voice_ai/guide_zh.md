## 套餐: 云端或 OpenAI 兼容模型 {#cloud_llm}

语音识别和合成仍在设备本地运行，对话文字发送到 Qwen API 或你填写的 OpenAI 兼容接口。默认地址是阿里云百炼北京地域，换供应商时只需要替换接口地址、Key 和模型 ID。

| 设备 | 用途 |
|------|------|
| RK3576 / RK3588 / Orin Nano / Orin NX | 运行本地语音链路和双工 agent |
| Qwen API 或兼容接口 | 生成对话回复 |

**前提条件：** 持续联网 · 有效 API Key · 模型支持流式 Chat Completions

## 步骤 1: 部署云端对话终端 {#deploy_cloud type=docker_deploy required=true config=devices/cloud_rk3576.yaml}

部署后，用户可以在设备说话期间随时打断正在播放的回答。

### 部署目标 {#cloud_rk3576 type=remote device=rk3576 device_name="RK3576" config=devices/cloud_rk3576.yaml default=true}

在 RK3576 上运行语音，连接云端或局域网模型。

### 接线

1. 接入 AEC 麦克风和音箱
2. 填写 SSH 信息、接口地址、API Key 和模型 ID
3. 默认 Qwen 配置使用当前低延迟的 `qwen3.5-flash` 模型

reSpeaker 可以在部署前接入，也可以在 Agent 已运行后热插拔。Agent 会按稳定的
USB 产品标识自动选择真实采集设备，忽略 HDMI/DP 虚拟输入；拔出后重新插入无需重启容器。

### 部署完成

对设备提问；它开始回答后，在 1 秒内再次开口，当前声音应立即停止并处理新问题。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 返回 401 | 检查 API Key 是否属于接口所在地域 |
| 能识别但不说话 | 查看 agent 日志中的 LLM 请求错误，并确认模型支持流式输出 |
| 热插拔后没有恢复 | 确认容器使用新版 Agent 镜像，且 Compose 包含动态 `/dev/snd` 映射和 `116:*` cgroup 规则 |

### 部署目标 {#cloud_local type=local device=jetson config=devices/cloud_jetson.yaml}

直接部署到正在运行 SenseCraft Solution 的本机。该本机目标要求设备是
Jetson Orin，并已安装 JetPack 6.2、Docker 和 NVIDIA Container Toolkit。

### 接线

1. 将 AEC 麦克风和音箱接到本机
2. 填写云端接口、API Key、模型 ID 和助手人设
3. 开始部署并等待语音模型预热

### 部署完成

提出一个问题，在回答播放时再次说话，确认能立即打断。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 本机不支持部署 | 如果当前机器不是 JetPack 6.2 的 Jetson Orin，请选择远程部署 |
| 缺少 NVIDIA runtime | 安装 NVIDIA Container Toolkit 后重启 Docker |

### 部署目标 {#cloud_rk3588 type=remote device=rk3588 device_name="RK3588" config=devices/cloud_rk3588.yaml}

在 RK3588 上运行语音，连接云端或局域网模型。

### 接线

1. 接入 AEC 麦克风和音箱
2. 填写 SSH 信息、接口地址、API Key 和模型 ID
3. 开始部署并等待语音模型就绪

### 部署完成

连续对话两轮，然后在第三轮回答播放时打断。面板状态应从 speaking 切到 barged-in/ listening。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 回复不断重复 | 检查麦克风是否真的输出 AEC 通道，降低音箱音量后复测 |
| 打断后仍有余音 | 查看 agent 是否记录播放队列清空；不要使用会缓存数秒音频的外部播放器 |

### 部署目标 {#cloud_jetson type=remote device=jetson device_name="Jetson Orin" config=devices/cloud_jetson.yaml}

在 Orin Nano 或 Orin NX 上运行语音，连接云端或局域网模型。

### 接线

1. 接入 AEC 麦克风和音箱
2. 选择 Orin Nano 或 Orin NX 语音配置
3. 填写 SSH 信息、接口地址、API Key 和模型 ID

### 部署完成

等待语音服务预热后完成两轮对话，并在回复播放期间开口验证打断。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| CUDA 初始化失败 | 核对 JetPack 6.2、TensorRT 10.3 和容器 runtime |
| Orin Nano 内存不足 | 使用 `jetson-qwen3asr-matcha`，不要在 Nano 上同时启动本地 4B 模型 |

## 步骤 2: 验证对话与打断 {#verify_cloud type=web_dashboard required=true config=devices/dashboard_cloud.yaml}

在面板里观察 listening、thinking、speaking 和 barged-in 状态。

### 部署完成

连续三轮对话正常，且播放期间说“等一下”能立即停止当前回复，即代表核心体验通过。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 状态变化但没有声音 | 检查默认播放设备，避免 PortAudio 选到没有输出通道的声卡 |
| 房间噪声频繁打断 | 先确认 AEC 通道，再小幅提高客户端 VAD threshold，不要直接关闭麦克风 |

## 套餐: 全本地对话 {#local_llm}

语音和对话都留在设备上。当前交付提供两条已经有模型产物和运行时的组合：RK3588 + RK1828 运行 Qwen3-4B，或 Orin NX 16GB 运行 Qwen3.5-4B。

| 设备 | 本地模型 |
|------|----------|
| RK3588 + RK1828 / RM182X | Qwen3-4B，独立 PCIe NPU |
| Orin NX 16GB | Qwen3.5-4B，与 Qwen3-ASR + Matcha 同机 |

**前提条件：** 首次下载模型时联网 · RK1828 驱动/固件已经在宿主机初始化 · Orin NX 使用 JetPack 6.2

## 步骤 1: 部署全本地语音 AI {#deploy_local type=docker_deploy required=true config=devices/local_orin_nx.yaml}

部署语音服务、本地模型服务和常驻双工 agent。

### 部署目标 {#local_orin_nx type=remote device=orin_nx device_name="Orin NX" config=devices/local_orin_nx.yaml default=true}

在 Orin NX 16GB 上运行 Qwen3-ASR、Matcha-TTS 和 Qwen3.5-4B。

### 接线

1. 接入 AEC 麦克风和音箱
2. 确认设备是 Orin NX 16GB，并预留至少 25GB 磁盘空间
3. 填写 SSH 凭据并开始部署

### 部署完成

首次模型下载和预热可能需要十几分钟。两个健康检查通过后，完成对话和打断测试。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 模型加载时 OOM | 停止其他 GPU 容器；不要把该套餐部署到 Orin Nano 8GB |
| engine 校验失败 | 不要混用其他 TensorRT/JetPack 版本构建的 engine，保留锁定 revision |

### 部署目标 {#local_this_machine type=local device=orin_nx config=devices/local_orin_nx.yaml}

直接部署到本机。该目标要求本机是运行 JetPack 6.2 的 Orin NX 16GB，
并有足够内存同时运行语音服务和 Qwen3.5-4B。

### 接线

1. 接入 AEC 麦克风和音箱
2. 确认至少有 25GB 空闲磁盘，并停止其他 GPU 工作负载
3. 开始部署，等待本地 LLM 和语音服务健康

### 部署完成

完成预热后断开外网，确认对话仍可正常进行。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 本机不是 Orin NX 16GB | 选择远程部署，并在下拉框中选择正确设备 |
| 模型加载时内存不足 | 部署前停止其他 GPU 容器 |

### 部署目标 {#local_rk3588 type=remote device=rk3588_rk1828 device_name="RK3588 + RK1828" config=devices/local_rk3588_rk1828.yaml}

在 RK3588 上运行语音，并由 RK1828 加速卡运行 Qwen3-4B。

### 接线

1. 确认 RK1828 独立 12V 供电、驱动服务正常且设备节点存在
2. 接入 AEC 麦克风和音箱
3. 填写 SSH 凭据并开始部署

### 部署完成

检查 1828 和 8621 端口健康状态，再完成连续对话和打断测试。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| RK1828 无法加载模型 | 检查宿主机驱动、固件和独立供电；不要执行 `rknn-smi reset` |
| 另一模型已占用加速卡 | RK1828 单卡一次只驻留一个大模型，先停止其他 RK1828 推理服务 |

## 步骤 2: 验证本地对话与打断 {#verify_local type=web_dashboard required=true config=devices/dashboard_local.yaml}

断开外网后继续对话，确认音频和文本链路不依赖云端。

### 部署完成

在断网状态完成三轮对话，并在回答播放时成功打断，即代表全本地链路通过。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 断网后首次启动失败 | 首次运行所需镜像和模型还没有全部缓存，请联网完成一次启动 |
| 回复过长 | 保持语音助手提示词为一到两句口语化回答，避免长文本拖慢合成 |

# 部署完成

应用已持续监听麦克风。最终验收请在真实房间、真实音箱音量下完成：连续对话三轮，在每轮回复开始后 0.5–1 秒开口打断，并确认旧回复立即停止、打断内容没有丢失。
