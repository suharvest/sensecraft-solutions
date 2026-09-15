## 套餐: 云端或 OpenAI 兼容模型 {#cloud_llm}

语音在设备本地运行，对话回复由 Qwen API 或你填写的 OpenAI 兼容接口生成。默认是阿里云百炼北京地域、模型 qwen3.5-flash，换供应商时替换接口地址、Key 和模型 ID。

- **麦克风：** 需要 reSpeaker XVF3800 USB 麦克风阵列（普通 USB 麦克风会回声、误打断）。
- **网络：** 每轮对话都要联网。
- **API Key：** 部署时填写 API Key 和模型 ID，模型需支持流式 Chat Completions。

**可选唤醒词：** 在部署表单选择“唤醒词后响应”，输入简短的中文或英文唤醒词，识别成功后会播放一声提示音；默认是“持续监听”。

## 步骤 1: 部署云端对话终端 {#deploy_cloud type=docker_deploy required=true config=devices/cloud_rk3576.yaml}

部署后，可以在设备播放回答时随时开口打断。

### 部署目标 {#cloud_rk3576 type=remote device=rk3576 device_name="RK3576" config=devices/cloud_rk3576.yaml default=true}

在 RK3576 上运行语音，连接云端或局域网模型。需要至少 12 GB 可用磁盘。

### 接线

1. 接入 reSpeaker XVF3800 和音箱
2. 填写 SSH 信息和模型接口设置

### 部署完成

提一个问题；回答开始播放后 1 秒内再次开口，当前回答应立即停止。

### 故障排查

| 现象 | 处理 |
|------|------|
| 返回 401 | 确认 API Key 属于接口所在地域 |
| 能识别但不说话 | 查看 agent 日志中的大模型请求错误，确认模型支持流式输出 |
| 拔插麦克风后没有声音 | 确认运行的是新版 Agent 镜像 |

### 部署目标 {#cloud_local type=local device=jetson config=devices/cloud_jetson.yaml}

部署到本机。本机须为已安装 JetPack 6.2、Docker 和 NVIDIA Container Toolkit 的 Jetson Orin，需要至少 15 GB 可用磁盘。

### 接线

1. 将 reSpeaker XVF3800 和音箱接到本机
2. 填写模型接口设置和助手人设
3. 开始部署并等待语音模型预热

### 部署完成

提一个问题，在回答播放时再次开口，确认能立即打断。

### 故障排查

| 现象 | 处理 |
|------|------|
| 本机不支持部署 | 本机不是 JetPack 6.2 的 Jetson Orin 时，改选远程部署 |
| 缺少 NVIDIA runtime | 安装 NVIDIA Container Toolkit 后重启 Docker |

### 部署目标 {#cloud_rk3588 type=remote device=rk3588 device_name="RK3588" config=devices/cloud_rk3588.yaml}

在 RK3588 上运行语音，连接云端或局域网模型。需要至少 12 GB 可用磁盘。

### 接线

1. 接入 reSpeaker XVF3800 和音箱
2. 填写 SSH 信息和模型接口设置
3. 开始部署并等待语音模型就绪

### 部署完成

连续对话两轮，在第三轮回答播放时打断，面板状态应从 speaking 切到 barged-in / listening。

### 故障排查

| 现象 | 处理 |
|------|------|
| 回复不断重复 | 确认使用的是 reSpeaker XVF3800，降低音箱音量后复测 |
| 打断后仍有余音 | 不要使用会缓存数秒音频的外部播放器 |

### 部署目标 {#cloud_jetson type=remote device=jetson device_name="Jetson Orin" config=devices/cloud_jetson.yaml}

在 Orin Nano 或 Orin NX 上运行语音，连接云端或局域网模型。需要至少 15 GB 可用磁盘。

### 接线

1. 接入 reSpeaker XVF3800 和音箱
2. 选择 Orin Nano 或 Orin NX 语音配置
3. 填写 SSH 信息和模型接口设置

### 部署完成

等待语音服务预热后完成两轮对话，并在回答播放时开口验证打断。

### 故障排查

| 现象 | 处理 |
|------|------|
| CUDA 初始化失败 | 核对 JetPack 6.2、TensorRT 10.3 和容器 runtime |
| Orin Nano 内存不足 | 使用 `jetson-qwen3asr-matcha` 配置，不要在 Nano 上启动本地 4B 模型 |

### 部署目标 {#cloud_rpi5 type=remote device=rpi5 device_name="reComputer Industrial R20 series" config=devices/cloud_rpi5.yaml}

在 reComputer Industrial R20 系列上用 CPU 运行语音，连接云端或局域网模型。需要至少 10 GB 可用磁盘，**仅支持英文**，选择其他语言会在服务启动前终止部署。

### 接线

1. 接入 reSpeaker XVF3800 和音箱
2. 填写 SSH 信息和模型接口设置
3. 对话语言保持英文

### 部署完成

用英文提问；回答开始播放后 1 秒内再次开口，当前回答应立即停止。

### 故障排查

| 现象 | 处理 |
|------|------|
| 部署报 "not supported" 终止 | 改选英文 |
| 回复偏慢 | 关闭其他负载，或改用带 NPU 的板卡 |
| 拔插麦克风后没有声音 | 确认运行的是新版 Agent 镜像 |

## 步骤 2: 验证对话与打断 {#verify_cloud type=web_dashboard required=true config=devices/dashboard_cloud.yaml}

在面板里观察 listening、thinking、speaking 和 barged-in 状态。

### 部署完成

连续三轮对话正常，且播放期间说“等一下”能立即停止当前回答，即通过。

### 故障排查

| 现象 | 处理 |
|------|------|
| 状态变化但没有声音 | 检查默认播放设备是否为音箱 |
| 房间噪声频繁打断 | 先确认使用的是 reSpeaker XVF3800，再小幅提高客户端 VAD threshold，不要关闭麦克风 |

## 步骤 3: 验证所选语言 {#voice_chat_cloud type=web_dashboard required=true config=devices/voice_chat_cloud.yaml}

确认识别和语音回复使用的是部署时选择的语言。

### 部署完成

#### 验收清单

1. `curl -fsS http://<设备IP>:8621/health` 返回成功。
2. 提一个问题，几秒内开始播放语音回复。
3. 回答开始播放后 1 秒内再次开口，当前回答立即停止。
4. 两到三轮对话的转写和语音回复都是所选语言。
5. 在设备上执行 `docker compose -p conversational_voice_ai -f ~/conversational_voice_ai/assets/docker/docker-compose.<target>.yml logs --since 10m | grep -i error`，无输出（`<target>` 为 `rk3576`、`rk3588`、`jetson` 或 `rpi5`）。

### 故障排查

| 现象 | 处理 |
|------|------|
| 回复语言不对 | 检查助手人设提示词 |
| 部署没有启动 | 所选语言该板不支持，改选支持的语言 |
| 转写语言正确但语音不对 | 上报语言与板卡型号，不要自行修改语音配置 |

## 套餐: 全本地对话 {#local_llm}

语音识别、合成和对话模型都在设备上运行。

- **麦克风：** 需要 reSpeaker XVF3800 USB 麦克风阵列（普通 USB 麦克风会回声、误打断）。
- **网络：** 只在首次部署拉取镜像和模型时联网，之后可断网运行；不需要 API Key。

## 步骤 1: 部署全本地语音 AI {#deploy_local type=docker_deploy required=true config=devices/local_orin_nx.yaml}

部署语音服务、本地模型服务和双工 agent。

### 部署目标 {#local_orin_nx type=remote device=orin_nx device_name="Orin NX" config=devices/local_orin_nx.yaml default=true}

在 Orin NX 16GB 上运行 Qwen3-ASR、Matcha-TTS 和 Qwen3.5-4B。需要 JetPack 6.2 和至少 25 GB 可用磁盘。

### 接线

1. 接入 reSpeaker XVF3800 和音箱
2. 确认设备是 Orin NX 16GB
3. 填写 SSH 凭据并开始部署

### 部署完成

首次下载模型和预热需要十几分钟。两个健康检查通过后，完成对话和打断测试。

### 故障排查

| 现象 | 处理 |
|------|------|
| 模型加载时 OOM | 停止其他 GPU 容器；不要部署到 Orin Nano 8GB |
| engine 校验失败 | 不要混用其他 TensorRT/JetPack 版本构建的 engine |

### 部署目标 {#local_this_machine type=local device=orin_nx config=devices/local_orin_nx.yaml}

部署到本机。本机须为运行 JetPack 6.2 的 Orin NX 16GB，需要至少 25 GB 可用磁盘。

### 接线

1. 接入 reSpeaker XVF3800 和音箱
2. 停止其他 GPU 任务
3. 开始部署，等待本地大模型和语音服务就绪

### 部署完成

预热完成后断开外网，确认对话仍正常。

### 故障排查

| 现象 | 处理 |
|------|------|
| 本机不是 Orin NX 16GB | 改选远程部署，并选择正确设备 |
| 模型加载时内存不足 | 部署前停止其他 GPU 容器 |

### 部署目标 {#local_rk3588 type=remote device=rk3588_rk1828 device_name="RK3588 + RK1828" config=devices/local_rk3588_rk1828.yaml}

在 RK3588 上运行语音，由 RK1828 / RM182X 加速卡运行 Qwen3-4B。需要至少 18 GB 可用磁盘，RK1828 驱动和固件已在宿主机初始化。

### 接线

1. 确认 RK1828 已接独立 12V 供电、驱动服务正常且设备节点存在
2. 接入 reSpeaker XVF3800 和音箱
3. 填写 SSH 凭据并开始部署

### 部署完成

确认 1828 和 8621 端口健康检查通过，再完成连续对话和打断测试。

### 故障排查

| 现象 | 处理 |
|------|------|
| RK1828 无法加载模型 | 检查宿主机驱动、固件和独立供电；不要执行 `rknn-smi reset` |
| 加速卡已被占用 | RK1828 一次只能运行一个大模型，先停止其他 RK1828 推理服务 |

## 步骤 2: 验证本地对话与打断 {#verify_local type=web_dashboard required=true config=devices/dashboard_local.yaml}

断开外网后继续对话，确认不依赖云端。

### 部署完成

在真实房间、真实音箱音量下断网完成三轮对话。每轮回答开始后 0.5–1 秒开口打断，旧回答应立即停止，打断的话不丢失。

### 故障排查

| 现象 | 处理 |
|------|------|
| 断网后首次启动失败 | 镜像和模型还没缓存完，先联网完成一次启动 |
| 回复过长 | 把提示词限制为一到两句口语化回答 |

## 步骤 3: 本地验证所选语言 {#voice_chat_local type=web_dashboard required=true config=devices/voice_chat_local.yaml}

确认识别和语音回复使用的是部署时选择的语言。

### 部署完成

#### 验收清单

1. `curl -fsS http://<设备IP>:8621/health` 返回成功。
2. 断开外网，提一个问题，几秒内开始播放语音回复。
3. 回答开始播放后 1 秒内再次开口，当前回答立即停止。
4. 两到三轮对话的转写和语音回复都是所选语言。
5. 在设备上执行 `docker compose -p conversational_voice_ai -f ~/conversational_voice_ai/assets/docker/docker-compose.<target>.yml logs --since 10m | grep -i error`，无输出（`<target>` 为 `orin-nx-local` 或 `rk3588-rk1828`）。

### 故障排查

| 现象 | 处理 |
|------|------|
| 回复语言不对 | 检查助手人设提示词 |
| 部署没有启动 | 所选语言该板不支持，改选支持的语言 |
| 转写语言正确但语音不对 | 上报语言与板卡型号，不要自行修改语音配置 |
