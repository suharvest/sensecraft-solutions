## 这个能力做什么

通过 SSH 一键把 GPT OSS 20B 大模型部署到 NVIDIA Jetson 设备上。部署完成后，容器自动启动 `llama-server`，在 `8080` 端口提供兼容 OpenAI 格式的 HTTP 推理服务。

## 输出接口

| 接口类型 | 说明 | 端口/路径 | 数据格式 |
|---------|------|----------|---------|
| HTTP API | 兼容 OpenAI 的对话补全接口 | :8080/v1/chat/completions | JSON |

部署完成后，打开浏览器访问：

`http://<jetson-ip>:8080`

## 适用集成场景

- 作为本地 AI 对话后端，接入聊天机器人或语音助手
- 配合 OpenClaw 网关，同时对接微信、Telegram 等多个聊天平台
- 为边缘设备提供离线大模型推理能力，无需云端 API

## 使用须知

**硬件要求**：
- Jetson Orin NX 16GB 或更高配置（20B 模型需要约 12-15GB 显存）
- reComputer J4012 已验证可用，其他 Jetson Orin 机型需确认显存充足

**调用方式**：
- API 地址：`http://<jetson-ip>:8080/v1/chat/completions`
- 兼容 OpenAI 格式，可直接用现有 SDK 调用
- Python 示例：`import openai; openai.api_base = "http://<jetson-ip>:8080/v1"`

**首次请求延迟**：
- 部署完成后首次调用可能需要等待 2-5 分钟（模型加载预热）
- 可访问 `http://<jetson-ip>:8080/v1/models` 检查服务是否就绪
- 预热完成后，后续请求响应较快（通常 1-3 秒）

**Token 与上下文**：
- 默认上下文窗口约 2048 tokens，可在部署时调整
- 如需更大上下文，可在配置中调高 `Llama Context` 参数（会占用更多显存）
- 单次请求建议控制在 1000 tokens 以内，避免显存溢出

## 技术规格

| 指标 | 数值 |
|------|------|
| 模型 | GPT OSS 20B |
| 推理框架 | llama.cpp (llama-server) |
| 支持硬件 | reComputer J4012 (Jetson Orin NX 16GB) |
| 服务端口 | 8080 |
| API 格式 | OpenAI 兼容 |
