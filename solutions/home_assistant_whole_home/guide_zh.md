# 部署指南

> **草稿 / 禁用。** 语音镜像、语言资源许可、设备清单和真机验收门槛完成前
> 只能用于审查。

## 套餐：RK3588 单机（草稿）{#rk_single_box}

## 步骤 1：部署 HA 与 RK 语音 {#rk_deploy type=docker_deploy required=true config=devices/rk_voice.yaml}

填写获准的语音镜像 digest。ZBT-2 的 `/dev/serial/by-id/...` 路径可选，留空可在
接入加密狗之前先安装。compose
同时挂载已审查的 HA package 与句式文件；使用本草案前须在目标主机完成安装。

### Target {#rk_local type=local device=rk3588 device_name="RK3588" config=devices/rk_voice.yaml}

在这台 RK3588 上运行 Docker。

### Target {#rk_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk_voice.yaml default=true}

通过 SSH 连接这台 RK3588。

## 步骤 2：验证 Home Assistant {#rk_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

打开面板，在 ZHA 中配对 ZBT-2，添加 HomeKit Bridge，并使用 Voice PE 执行本地
语音指令。此 verify 步骤不代表已经通过验收。

## 套餐：树莓派 + Jetson 语音（草稿）{#rpi_jetson}

设备实测（树莓派 5 运行本包 compose 部署的 HA 2026.9.3，语音端点在 Jetson Orin NX，
经 Wyoming 接入）：5 条语音指令（中文、英文，“打开/关闭客厅灯”）全部改变了 HA 实体
状态，均由内置意图代理在本地处理。音频结束后 STT 最终结果 0.11–0.95 s（中位数
0.12 s）。输入为 TTS 合成语音推流到 Assist 管道，不是麦克风；实体为虚拟演示灯。
未验证：HomeKit 配对、Aqara/ZHA（ZBT-2）、Voice PE、ESPHome、实体麦克风/扬声器、
离线运行、日语。

## 步骤 1：部署 Home Assistant Container {#rpi_deploy type=docker_deploy required=true config=devices/ha_rpi.yaml}

使用 64 位 Raspberry Pi OS，树莓派的 8123 端口必须空闲。ZBT-2 设备路径可选：留空
可在接入加密狗之前先安装 Home Assistant，接入后填写 `/dev/serial/by-id/...` 路径
重新部署。

### Target {#rpi_local type=local device=arm64_linux device_name="ARM64 Linux 主机（如树莓派 5）" config=devices/ha_rpi.yaml}

在这台树莓派上运行 Docker。

### Target {#rpi_remote type=remote device=arm64_linux device_name="ARM64 Linux 主机（如树莓派 5）" config=devices/ha_rpi.yaml default=true}

通过 SSH 连接这台树莓派。

## 步骤 2：部署 Jetson 语音服务 {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

运行一个 OpenVoiceStream 服务（Qwen3-ASR + Matcha TTS，配置 `jetson-edgellm-v091-matcha`，
镜像 `nrd6-ovs-jetson:20261008`）同时提供 ASR 和 TTS，端口为 `voice_port`（默认 8623）；
另有 Home Assistant 连接的 Wyoming 适配层（`wyoming-slv-adapter:20261008`，STT 10300 /
TTS 10200）。首次启动时服务把模型下载到 `jetson-models` 卷（至少 30 GB 可用磁盘）。
这与上文 2026-10-08 Orin NX 实测的布局相同（同一镜像、同一配置）；本 compose 文件本身
2026-10-08 未在设备上运行——当时 Orin NX 没有可用磁盘。尚无完成许可核实的可分发语音 artifact。

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_voice.yaml}

在这台 Jetson 上运行 Docker。

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_voice.yaml default=true}

通过 SSH 连接这台 Jetson。

## 步骤 3：验证 Home Assistant {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

打开 HA，完成同样的 ZHA、HomeKit 和本地语音检查。
