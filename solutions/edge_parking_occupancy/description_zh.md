# 边缘多摄像头停车位占用检测

> **草稿。** SlotsApp 运行镜像和各部署目标的 vehicle640 模型包已发布（2026-10-08），
> 部署时自动获取；每个部署目标写明了其验收状态。这里不打包 broker 凭据或宿主机专有库。

SlotsApp 采样一路或多路 RTSP，通过原生 `slot_coverage` 分析器处理配置的车位
> 多边形，并向外部 MQTT broker 发布保留的车位状态。HTTP 编辑页和 `/healthz`
> 是预期应用契约的一部分。

当前方案记录 Jetson 与 RK3576/RK3588 暂存契约，各部署目标的实测结果见部署指南。投入
生产前，在自己的摄像头和车场上测量多路承载能力、车位准确率和断流恢复。

## RK3576 与 RK3588 部署目标

套餐中的 RK3576 与 RK3588 部署目标记录 reComputer RK3576 和 RK3588 的原生 RKNN SlotsApp 部署。部署
前，将随包提供的 `assets/config/slots-rk3576.json` 或 `slots-rk3588.json` 复制到宿主机
并编辑：site/device ID 不超过 32 个字符，MQTT client ID 和 topic root 唯一，两个 MQTT
映射一致，填写 RTSP 地址/编码、固定 vehicle640 模型路径/SHA、映射到 stream ID 的车位
多边形和已存在的状态路径。每个 RK 部署目标还需要本地构建镜像、可写数据目录、DRM 设备以及
用户提供的 RKNN/RGA/MPP 宿主机路径。转换 artifact 已记录 SHA，本包不会内置或自动下载，
部署前需放到宿主机上。默认流编码为 H.264；每路流可通过 `options.codec` 选择 H.265。
车位消息使用 `<site>/parking/<camera>/slots`，其中 `<camera>` 是配置的 stream ID。
原生健康服务绑定 `0.0.0.0:8099`；远程 `/healthz` 检查使用 RK 主机可达地址。
