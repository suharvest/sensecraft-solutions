# 部署指南

> **草稿 / 禁用。** 语音镜像、语言资源许可、设备清单和真机验收门槛完成前
> 只能用于审查。

## 套餐：树莓派 + Jetson 语音（草稿）{#rpi_jetson}

设备实测（ARM64 Linux 主机，Broadcom BCM2712、8GB，运行本包 compose 部署的 HA 2026.9.3，语音端点在 Jetson Orin NX，
经 Wyoming 接入）：5 条语音指令（中文、英文，“打开/关闭客厅灯”）全部改变了 HA 实体
状态，均由内置意图代理在本地处理。音频结束后 STT 最终结果 0.11–0.95 s（中位数
0.12 s）。输入为 TTS 合成语音推流到 Assist 管道，不是麦克风；实体为虚拟演示灯。
HomeKit 配对、Aqara/ZHA（ZBT-2）、Voice PE、ESPHome、实体麦克风/扬声器、离线运行
和日语指令不在这次实测范围内：交付前在自己的安装环境里测试需要用到的项。

## 步骤 1：部署 Home Assistant Container {#rpi_deploy type=docker_deploy required=true config=devices/ha_rpi.yaml}

使用 64 位 Raspberry Pi OS。Home Assistant 默认监听 8123 端口；若树莓派上 8123
已被占用（例如另一套 Home Assistant），首次安装前填写其他 Home Assistant 端口。ZBT-2 设备路径可选：留空
可在接入加密狗之前先安装 Home Assistant，接入后填写 `/dev/serial/by-id/...` 路径
重新部署。

### Target {#rpi_local type=local device=arm64_linux device_name="ARM64 Linux 主机（64 位系统，8GB 内存）" config=devices/ha_rpi.yaml}

在这台树莓派上运行 Docker。

### Target {#rpi_remote type=remote device=arm64_linux device_name="ARM64 Linux 主机（64 位系统，8GB 内存）" config=devices/ha_rpi.yaml default=true}

通过 SSH 连接这台树莓派。

## 步骤 2：部署 Jetson 语音服务 {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

运行一个 OpenVoiceStream 服务（Qwen3-ASR + Matcha TTS，配置 `jetson-edgellm-v091-matcha`，
镜像 `nrd6-ovs-jetson:20261008`）同时提供 ASR 和 TTS，端口为 `voice_port`（默认 8623）；
另有 Wyoming 适配层（`wyoming-slv-adapter:20261008`），Home Assistant 经 `wyoming_stt_port` /
`wyoming_tts_port`（默认 10300 / 10200）连接。首次启动时服务把模型下载到 `jetson-models` 卷
（至少 30 GB 可用磁盘）。2026-10-08 已在 Orin NX 上用本 compose 文件验证，所用 OVS 与适配层镜像的
config digest 与已发布的 20261008 镜像一致（语音服务 8633，Wyoming 经端口输入改为 10301 / 10201；
模型取自已有卷，关闭自动下载）：两个端口都应答 Wyoming `describe` 请求；TTS 输出回送 STT，
打开客厅灯、关闭卧室的灯和 "Turn on the living room light" 三句与原文一致（另带句末标点）；TTS 首段音频 0.05–0.12 s，音频结束后 0.38–0.58 s 出 STT 结果。
输入为合成语音，非麦克风。尚无完成许可核实的可分发语音 artifact。

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_voice.yaml}

在这台 Jetson 上运行 Docker。

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_voice.yaml default=true}

通过 SSH 连接这台 Jetson。

## 步骤 3：验证 Home Assistant {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

把 Home Assistant 接到 Jetson 语音服务，再做检查：

1. 在 Home Assistant 中进入 **设置 → 设备与服务 → 添加集成 → Wyoming Protocol**，主机填 Jetson 的
   IP 地址，端口填步骤 2 的 `wyoming_stt_port`（默认 10300）。
2. 再添加一个 **Wyoming Protocol** 集成，主机相同，端口填 `wyoming_tts_port`（默认 10200）。
3. 进入 **设置 → 语音助手**，打开 Assist 流水线，选择新加入的语音转文字和文字转语音服务。
4. 完成 ZHA、HomeKit 和本地语音检查。

之后若用其他端口重新部署步骤 2，已有的 Wyoming 集成仍指向旧端口：删除这两个集成后重新添加。
