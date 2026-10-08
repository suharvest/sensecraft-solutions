# 部署指南

> **草稿。** compose 是可审查契约；没有已发布默认值的输入会
> fail closed。

## 套餐：Clip + 边缘算力盒子（草稿）{#clip_edge_box}

在部署步骤里选择主机：Jetson、RK3588 或 RK3576。Clip 同步始终走 BLE；Wi-Fi 同步
为可选项，需要专用主机网卡。每个部署目标写明了其真机验收状态。

## 步骤 1：部署本地转写栈 {#deploy_stack type=docker_deploy required=true config=devices/jetson_stack.yaml}

clip-pt 镜像默认使用 2026-10-08 发布的镜像；Jetson 上的 OVS 镜像和 ASR 模型包也已发布。
请提供 RK 主机上的 SLV 镜像和已预载的 ASR 模型根目录、Mosquitto 镜像引用，并基于审查过的 `assets/config/config.example.yaml` 准备配置。手动配对
Clip，并保持单一主机绑定。

compose 栈会启动 clip-pt、独立的 SenseVoice 与 Whisper SLV 服务和 Mosquitto。LLM 使用用户在共享配置中填写的 OpenAI 兼容端点（`base_url`、`model_name`、`api_key`、`timeout_s`）；
`base_url` 可填写根地址或 `/v1`。端点可以是云端、RK1828 或 Jetson 服务，本方案不启动本地 LLM runtime。
LLM 复用语音 RD 的 `base_url`、`model_name`、`api_key` 字段，由用户在应用配置中填写；本包不写入真实密钥。
云端端点需要网络；可达的 RK1828 或 Jetson 端点可支持本地断网链路。Mosquitto 使用包内的本机匿名 broker 配置。

上传前，把所有 `REPLACE_WITH_*` 替换为实际 Clip 广播名称、BLE MAC 地址和本地标签，
不能保留示例占位符。使用 Wi-Fi 同步时，把 `sync.wifi_iface` 改为专用网卡的实际接口名；
没有专用网卡时设置 `sync.wifi_enabled: false`，Clip 只走 BLE 同步。请在本机生成 API key，
并将输出的 64 个十六进制字符填入 `api.key`；包内示例保持空值，未配置时会 fail closed：

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

**RK3576 / RK3588。** 复制的 profile 分别在 8621 选择 `rk.asr`、在 8622 选择
`rk.whisper`，并关闭 artifact 下载；请按 profile 声明的路径提供两个模型根目录（RK3576
使用 base10 Whisper RKNN 文件，RK3588 使用 base20）。SLV 镜像、profile 和模型根目录
必须与所选 RK runtime 匹配。共享示例为 Jetson 启用了 `pipeline.require_gpu_diarization`；
RK3576/RK3588 部署必须将其设为 `false`：当前严格契约只接受 Jetson CUDA CAM++ 元数据，
本文不宣称存在匹配的 RKNN speaker backend。设为 `false` 时保留现有 legacy CPU/空结果行为。

**Jetson。** Jetson 语音后端使用已发布的 `nrd6-ovs-jetson:20261008` 镜像（按 digest 固定）；
CUDA runtime 由宿主机提供。

两个 SLV 服务要求 Jetson runtime ABI：JetPack 6.2、TensorRT 10.3.0 和
Python 3.10。部署会在 Compose 启动前检查主机 TensorRT binding 和库，然后以只读方式挂载
binding、`/usr/src/tensorrt`、`/usr/local/cuda/lib64`、NVIDIA 库及 ARM64 系统库。
镜像加载路径固定到这些挂载；路径缺失或 TensorRT 版本不符时 fail closed，不提供 CPU fallback。
这项要求与下方按设备生成的模型 plan 分开，模型仍必须匹配目标 Jetson。

请提供两个部署输入：编辑后的 Clip 配置和获准的 Mosquitto 镜像。`clip-pt` 和 OVS
镜像默认使用 2026-10-08 发布的镜像（按 digest 固定），部署时把 `clip-orin-nx-r1` ASR
模型包（校验 SHA-256）下载到 Jetson 的 `/opt/clip-private-transcription/models`；
其中的 plan 按 Orin NX 构建。这些目录是
Jetson 上的路径，不是 App 所在电脑的路径，也不会上传。
模型包解包后的目录与 profile 使用的准确文件名一致：

```text
/opt/models/clip-asr/
├── sensevoice-trt/
│   ├── sense-voice-encoder.scaled.fixed.onnx
│   ├── am.mvn
│   ├── embedding.npy
│   ├── chn_jpn_yue_eng_ko_spectok.bpe.model
│   └── sensevoice.plan
├── whisper/
│   ├── encoder/jetson/enc_base_30s_bf16.plan
│   ├── mel_80_filters.txt
│   └── vocab_en.txt
├── plans/
│   ├── prefill_fp16.plan
│   └── step_fp16.plan
└── speaker/
    └── campplus.plan
```

该目录以只读方式挂载到 `/models`。Whisper BF16 encoder plan 和 TensorRT decoder
plans 必须匹配选定 Jetson 型号及其 runtime；NX 上验证的 plan 只适用于对应设备，
不能宣称可跨 Jetson 复用。包内 profile 会显式挂载；SenseVoice 和 Whisper 两个服务
分别监听主机 8621、8622，并各自使用一个串行 GPU 执行上下文。

示例还要求获准的离线 CAM++ plan 位于 `/models/speaker/campplus.plan`。
`OVS_SPEAKER_EMB_BACKEND=jetson_trt` 是严格选择：plan 缺失、不兼容或运行失败时返回
错误，不改用 CPU speaker 模型。GPU 证明只覆盖 CAM++ 神经前向；VAD、fbank 和聚类仍在
CPU 上执行。

compose 契约关闭模型下载。两个 ASR-only 服务使用同一私有 OVS 镜像启动，并要求两个
检查都通过：`/readyz` 必须接受请求（后端就绪、会话容量和 GPU watchdog 状态），随后
`/health` 返回 `{"asr": true}`，且 `asr_backend` 分别为 `sensevoice_trt` 或
`whisper-tensorrt`。会话容量满时 `/readyz` 可能短暂 not ready；该 healthcheck 本身
不会主动重启容器。

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_stack.yaml default=true}

预编译的 TensorRT plan 只适用于 Jetson Orin NX（P3767-0000 / P3767-0001）、L4T R36.4（JetPack 6.2）、TensorRT 10.3；在其他模组或 JetPack 版本上，部署步骤会直接停止。

通过 SSH 连接这台 Jetson。2026-10-08 在 Orin NX 上，现已发布为
`clip-private-transcription:20261008` 的 clip-pt 构建用测试 compose（改用其他端口）跑通
HTTP 上传链路（上传、GPU 说话人分离、SenseVoice/Whisper TensorRT ASR、LLM 摘要、经
HTTP 与 MQTT 输出转写）。本目标的 compose 文件 2026-10-08 也在 Orin NX 上用已发布镜像运行过
（关闭摘要；因主机端口与磁盘已被占用，改用端口 8641/8642/18883 和 tmpfs 数据目录，模型只读绑定挂载）：
6.3 s 的 LibriSpeech 上传 1.2 s 完成，34 s 双人 FLEURS 日语上传 2.2 s 完成，识别出 2 位说话人。
英文样本只转写出第二句（说话人分离步骤丢掉了第一句）。Clip BLE/Wi-Fi 同步需要 Clip 实物，当天没有可用的 Clip。

### 部署目标 {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_stack.yaml}

预编译的 TensorRT plan 只适用于 Jetson Orin NX（P3767-0000 / P3767-0001）、L4T R36.4（JetPack 6.2）、TensorRT 10.3；在其他模组或 JetPack 版本上，部署步骤会直接停止。

在这台 Jetson 上运行 Docker。与 SSH 目标使用同一 compose 文件：该 compose 与已发布镜像
2026-10-08 已在 Orin NX 上跑通 HTTP 上传链路（见 SSH 目标）。Clip BLE/Wi-Fi 同步需要 Clip 实物。

### 部署目标 {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_stack.yaml}

通过 SSH 连接这台 RK3588。整包验收受阻：2026-10-08 在 Rock 5T 上无法满足 15 GB 磁盘
预检。用重建的 clip-pt 镜像直接经 Compose 启动时，HTTP 上传链路（SenseVoice RKNN
ASR、CPU CAM++ 说话人分离、RK1828 LLM 摘要、转写与 MQTT）通过；Whisper 服务健康但
没有任务使用。Clip BLE/Wi-Fi 同步需要 Clip 实物。

### 部署目标 {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_stack.yaml}

在这台 RK3588 上运行 Docker。整包验收受阻：HTTP 上传链路仅在使用重建 clip-pt 镜像时
于 Rock 5T 上通过；Clip BLE/Wi-Fi 同步需要 Clip 实物。

### 部署目标 {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml}

通过 SSH 连接这台 RK3576。验收受阻：2026-10-08 的测试板无法满足 15 GB 磁盘预检，缺少
SLV RK 模型根目录，且在已有服务旁的空闲内存不足以同时运行 SenseVoice 与 Whisper。
Clip BLE 同步需要 Clip 实物。

### 部署目标 {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml}

在这台 RK3576 上运行 Docker。验收受阻：RK3576 测试板的磁盘预检与空闲内存不足，整包栈
无法端到端运行。

## 步骤 2：验证 API {#verify_stack type=http_debug required=true config=devices/verify_clip.yaml}

要求 8631 上 clip-pt `/healthz` 返回 HTTP 200，再检查 8621 的 SenseVoice、8622 的
Whisper（Jetson 为 `/health`，RK 为 `/readyz`）以及 1883 上的 Mosquitto broker；按共享
配置中的 `base_url`、`model_name`、`api_key`、`timeout_s` 验证已配置的 LLM 端点，再执行
受控同步并检查转写 schema。M10 测试矩阵中的 API、MQTT、续传和断网检查须在真机门开启后
用真实 Clip 硬件执行。本方案不提供或实测验证云端服务商、模型、密钥、Mosquitto 镜像或
GPU speaker-embedding artifact。示例配置仍保持 summary、MQTT 和 diarization 开启；
容器健康检查不能代表离线、摘要、MQTT、diarization 或 Clip 真机验收已完成。
