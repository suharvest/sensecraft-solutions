# Clip 本地私有转写

> **草稿 / 禁用。** M7/M8 软件门和本地 wheel 已有，但 Clip/BLE/Wi-Fi 或主机
> 真机验收尚未通过。SLV artifact、模型许可和可分发的 clip-pt 镜像尚未
> 提供。

预期流程在本地同步录音，通过本地服务完成说话人分离与 ASR，并通过带认证的
> HTTP API 和 MQTT 提供转写结果。LLM 请求复用配置中的 OpenAI 兼容端点字段
>（`base_url`、`model_name`、`api_key`、`timeout_s`）。端点可以是云端服务，也可以是用户
> 管理的 RK1828/Jetson 服务；本方案不部署 LLM runtime。录音在本地处理和保存；选择云端摘要时，转写文本会发送到所配置的端点。使用本地 RK1828 或 Jetson 端点时可保留现场处理。本方案不宣称 Voice
> PE、BLE、AP、MT7921 或断网 E2E 已通过。
