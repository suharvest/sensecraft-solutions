# 全屋 Home Assistant 接入与本地语音

> **草稿。** Jetson 语音镜像和 Wyoming 适配层镜像已发布（2026-10-08）；RK 语音镜像和
> 具备分发许可的语言资源尚未发布，HomeKit、
> Aqara/ZHA、Voice PE 和断网语音尚未完成真机验收。这里不打包凭据或 Xiaomi
> Home 集成。

本方案记录使用 Home Assistant Container、HomeKit Bridge、通过 ZBT-2 的
ZHA 以及本地 Wyoming ASR/TTS 的部署契约。米家路径明确是用户自行安装的非
商业示例，不构成产品承诺。两个套餐使用已审查的 RK 与树莓派加 Jetson
compose；镜像 digest 为空时 fail closed。
