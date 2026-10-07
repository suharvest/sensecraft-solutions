# 部署指南

> **草稿 / 禁用。** compose 只是可审查契约；获准的本地镜像和真机证据齐备前
> 会 fail closed。

## 套餐：RK3576 + Clip BLE（草稿）{#rk3576_ble}

## 步骤 1：部署本地转写栈 {#rk3576_deploy type=docker_deploy required=true config=devices/rk3576_stack.yaml}

提供获准的本地 clip-pt、SLV 和 Mosquitto 镜像引用、已预载的 SenseVoice 与 Whisper 模型根目录，
并基于审查过的
`assets/config/config.example.yaml` 准备配置。手动配对 Clip，
并保持单一主机绑定。

compose 栈会启动 clip-pt、独立的 SenseVoice 与 Whisper SLV 服务和 Mosquitto。LLM 使用用户在共享配置中填写的 OpenAI 兼容端点（`base_url`、`model_name`、`api_key`、`timeout_s`）；
`base_url` 可填写根地址或 `/v1`。端点可以是云端、RK1828 或 Jetson 服务，本方案不启动本地 LLM runtime。
复制的 profile 分别在 8621 选择 `rk.asr`、在 8622 选择 `rk.whisper`，并关闭 artifact
下载；请按 profile 声明的路径提供两个模型根目录。云端 LLM 复用语音 RD 的 `base_url`、`model_name`、`api_key` 字段，由用户在应用配置中填写；本包不写入真实密钥。
Mosquitto 使用包内的本机匿名 broker 配置。SLV 镜像、profile 和模型根目录
必须与 RK3576 runtime 匹配；本方案没有该组合的 RK3576 实机验证证据。

上传前，把所有 `REPLACE_WITH_*` 替换为实际 Clip 广播名称、BLE MAC 地址和本地标签。
Wi-Fi 套餐还要把 `sync.wifi_iface` 改为主机的实际接口名。请在本机生成 API key，
并将输出的 64 个十六进制字符填入 `api.key`；包内示例保持空值，未配置时会 fail closed：

共享示例为 Jetson 套餐启用了 `pipeline.require_gpu_diarization`。RK3576/RK3588
部署必须将其设为 `false`：当前严格契约只接受 Jetson CUDA CAM++ 元数据，本文不宣称
存在匹配的 RKNN speaker backend。设为 `false` 时保留现有 legacy CPU/空结果行为。

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Target {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml}

在这台 RK3576 上运行 Docker。

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml default=true}

通过 SSH 连接这台 RK3576。

## 步骤 2：验证 API {#rk3576_verify type=http_debug required=true config=devices/verify_clip.yaml}

要求 `/healthz` 返回 HTTP 200，再执行受控同步并检查转写 schema。此项不代表
真机验收通过。

## 套餐：RK3588 + Clip Wi-Fi（草稿）{#rk3588_wifi}

## 步骤 1：部署本地转写栈 {#rk3588_deploy type=docker_deploy required=true config=devices/rk3588_stack.yaml}

提供获准的本地 clip-pt、SLV 和 Mosquitto 镜像引用、已预载的 SenseVoice 与 Whisper 模型根目录，
并基于示例准备配置。Wi-Fi 同步需要专用网卡，并在主机配置中填写实际接口名。`devices[]` 中的 Clip 名称和
BLE MAC 必须与实物一致，不能保留示例占位符。

compose 栈会启动 clip-pt、独立的 SenseVoice 与 Whisper SLV 服务和 Mosquitto。LLM 使用用户在共享配置中填写的 OpenAI 兼容端点（`base_url`、`model_name`、`api_key`、`timeout_s`）；
`base_url` 可填写根地址或 `/v1`。端点可以是云端、RK1828 或 Jetson 服务，本方案不启动本地 LLM runtime。
复制的 profile 分别在 8621 选择 `rk.asr`、在 8622 选择 `rk.whisper`，并关闭 artifact
下载；请按 profile 声明的路径提供两个模型根目录。LLM 使用用户配置的 OpenAI 兼容端点，复用语音 RD 的 `base_url`、`model_name`、`api_key` 字段；
用户在应用配置中填写，密钥不写入本包。云端端点需要网络；可达的 RK1828 或 Jetson 端点可支持本地断网链路。SLV 镜像、profile 和模型根目录必须与 RK3588 runtime 匹配；本方案没有该
组合的 RK3588 实机部署证据。

请基于 `assets/config/config.example.yaml` 准备配置：将 Clip 名称、BLE MAC、本地标签和
`sync.wifi_iface` 替换为实际值，然后把本机生成的 64 个十六进制字符填入 `api.key`：

RK3588 套餐请将 `pipeline.require_gpu_diarization: false`。当前严格响应契约只覆盖
Jetson CUDA CAM++，不宣称存在 RKNN speaker backend；默认 legacy 行为仍可用。

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Target {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_stack.yaml}

在这台 RK3588 上运行 Docker。

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_stack.yaml default=true}

通过 SSH 连接这台 RK3588。

## 步骤 2：验证 API {#rk3588_verify type=http_debug required=true config=devices/verify_clip.yaml}

真机门开启后再执行 API、MQTT、续传和断网检查。

## 套餐：Jetson + Clip Wi-Fi（草稿）{#jetson_wifi}

## 步骤 1：部署本地转写栈 {#jetson_deploy type=docker_deploy required=true config=devices/jetson_stack.yaml}

Jetson 语音后端和 CUDA runtime 需要获准 artifact；这里不暗示存在 registry
digest。

两个 SLV 服务要求 Jetson runtime ABI：JetPack 6.2、TensorRT 10.3.0 和
Python 3.10。部署会在 Compose 启动前检查主机 TensorRT binding 和库，然后以只读方式挂载
binding、`/usr/src/tensorrt`、`/usr/local/cuda/lib64`、NVIDIA 库及 ARM64 系统库。
镜像加载路径固定到这些挂载；路径缺失或 TensorRT 版本不符时 fail closed，不提供 CPU fallback。
这项要求与下方按设备生成的模型 plan 分开，模型仍必须匹配目标 Jetson。

请提供五个部署输入：获准的本地 `clip-pt` 镜像、获准的私有 OVS 镜像、编辑后的
Clip 配置、选定 Jetson 上已有的绝对 ASR 模型包目录（例如 `/opt/models/clip-asr`）、
获准的 Mosquitto 镜像。这些目录是
Jetson 上的路径，不是 App 所在电脑的路径，也不会上传。
部署前请按当前 profile 使用的准确文件名准备目录：

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

请基于 `assets/config/config.example.yaml` 准备配置：将 Clip 名称、BLE MAC、本地标签和
`sync.wifi_iface` 替换为实际值，然后把本机生成的 64 个十六进制字符填入 `api.key`：

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_stack.yaml}

在这台 Jetson 上运行 Docker。

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_stack.yaml default=true}

通过 SSH 连接这台 Jetson。

## 步骤 2：验证 API {#jetson_verify type=http_debug required=true config=devices/verify_clip.yaml}

检查 Clip `/healthz`、8621 的 SenseVoice `/health`、8622 的 Whisper `/health`、
以及 1883 上的 Mosquitto broker；按共享配置中的 `base_url`、`model_name`、`api_key`、`timeout_s` 验证已配置的 LLM 端点，再用真实 Clip 硬件执行 M10 测试矩阵。本方案不提供或实测验证
云端服务商、模型、密钥、Mosquitto 镜像或 GPU speaker-embedding artifact。示例配置仍保持 summary、MQTT 和 diarization 开启；
容器健康检查不能代表离线、摘要、MQTT、diarization 或 Clip 真机验收已完成。
