# 部署指南

> **草稿 / 禁用。** 语音镜像、语言资源许可、设备清单和真机验收门槛完成前
> 只能用于审查。

## 套餐：RK3588 单机（草稿）{#rk_single_box}

## 步骤 1：部署 HA 与 RK 语音 {#rk_deploy type=docker_deploy required=true config=devices/rk_voice.yaml}

填写获准的语音镜像 digest 和 ZBT-2 实际 `/dev/serial/by-id/...` 路径。compose
同时挂载已审查的 HA package 与句式文件；使用本草案前须在目标主机完成安装。

### Target {#rk_local type=local device=rk3588 device_name="RK3588" config=devices/rk_voice.yaml}

在这台 RK3588 上运行 Docker。

### Target {#rk_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk_voice.yaml default=true}

通过 SSH 连接这台 RK3588。

## 步骤 2：验证 Home Assistant {#rk_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

打开面板，在 ZHA 中配对 ZBT-2，添加 HomeKit Bridge，并使用 Voice PE 执行本地
语音指令。此 verify 步骤不代表已经通过验收。

## 套餐：树莓派 + Jetson 语音（草稿）{#rpi_jetson}

## 步骤 1：部署 Home Assistant Container {#rpi_deploy type=docker_deploy required=true config=devices/ha_rpi.yaml}

使用 64 位 Raspberry Pi OS，并填写真实 ZBT-2 设备路径。

### Target {#rpi_local type=local device=rpi device_name="Raspberry Pi" config=devices/ha_rpi.yaml}

在这台树莓派上运行 Docker。

### Target {#rpi_remote type=remote device=rpi device_name="Raspberry Pi" config=devices/ha_rpi.yaml default=true}

通过 SSH 连接这台树莓派。

## 步骤 2：部署 Jetson 语音服务 {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

填写获准的 ASR/TTS 镜像和 digest。当前没有已验证的 TTS E2E，也没有完成许可
核实的可分发语音 artifact。

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_voice.yaml}

在这台 Jetson 上运行 Docker。

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_voice.yaml default=true}

通过 SSH 连接这台 Jetson。

## 步骤 3：验证 Home Assistant {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

打开 HA，完成同样的 ZHA、HomeKit 和本地语音检查。
