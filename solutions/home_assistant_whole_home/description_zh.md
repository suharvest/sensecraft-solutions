# 全屋 Home Assistant 接入与本地语音

> **草稿。** Jetson 语音镜像和 Wyoming 适配层镜像已发布（2026-10-08）；具备分发许可的
> 语言资源尚未发布，RK3588 单机套餐在其语音镜像发布前不提供，HomeKit、
> Aqara/ZHA、Voice PE 和断网语音尚未完成真机验收。这里不打包凭据或 Xiaomi
> Home 集成。

本方案记录使用 Home Assistant Container、HomeKit Bridge、通过 ZBT-2 的
ZHA 以及本地 Wyoming ASR/TTS 的部署契约。米家路径明确是用户自行安装的非
商业示例，不构成产品承诺。本套餐在树莓派（或其他 ARM64 Linux 主机）上运行
Home Assistant，在 Jetson 上运行语音服务；镜像 digest 为空时 fail closed。
