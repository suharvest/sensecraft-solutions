# 部署生产工位工时与物料监测

## 套餐: Jetson 本地部署 {#jetson_local}

准备 Orin NX 8GB/16GB 或 Orin Nano 8GB，系统须为 Ubuntu 22.04、L4T 36.4.3、5.15.148-tegra 内核。安装 JetPack NVIDIA Container Toolkit 和 Docker Compose v2。SSH 用户应可直接使用 Docker，并可写入自己的主目录。首次部署至少预留 18GB 用于下载、解压和恢复点，数据集另计。升级前先停止训练。

部署使用本方案自带的发布钩子；旧版引擎会在切换服务之前被拦截。

## 步骤 1: 部署应用 {#jetson_worktime type=docker_deploy config=devices/jetson_deploy.yaml}

上传发布文件、拉取固定镜像、执行真实 CUDA 与 GPU NMS 检查，然后启动网页与训练服务。尚未配置摄像头不影响部署。

### 部署目标 {#jetson_remote type=remote device=jetson device_name="Jetson Orin" config=devices/jetson_deploy.yaml default=true}

填写目标设备地址、SSH 用户及密码或密钥。选择空闲网页端口（默认 8088），编码方式保留自动，然后开始部署。

### 接线

将 Jetson 接通电源并接入局域网，观看网页的浏览器需要直接访问它。媒体端口使用 8189 TCP/UDP、8554 TCP、8889 TCP、9997 TCP，如被其他程序占用，可统一修改媒体端口偏移。局域网防火墙需放行网页端口和 WebRTC 端口。

### 部署完成

开始部署后，引擎上传发布文件、准备固定候选镜像、核对镜像层，并执行真实 CUDA 矩阵运算与 GPU NMS。初始化服务补齐缺失配置及公开模型，网页与训练服务分别启动。就绪检查要求数据库、媒体服务、GPU 检查与训练心跳正常；尚未配置摄像头不影响部署成功。

目标 Jetson 无网络时，先在可联网电脑使用应用现有的离线准备/导出流程，架构选择 ARM64，再将包含镜像归档的完整离线包导入部署工具后离线部署。只复制 Compose 文件不足以离线运行。维护者也可在验证过的 Jetson 执行 `assets/docker/scripts/package.py export --output /绝对输出路径` 生成完整归档。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 切换服务后部署失败 | 失败钩子会自动恢复原配置、数据库和服务；等待恢复完成后再重试 |
| 部署期间 SSH 断开 | 设备看护进程会在 15 分钟内执行恢复；请等待恢复完成后重试，部署期间不要删除 `release-state/` |
| 担心已有数据被覆盖 | 持久化文件位于目标设备 `~/.sensecraft/deployments/jetson_worktime/persistent/`（实际以引擎显示的部署目录为准）；请定期备份整个目录并保护配置文件 |
| 恢复用镜像被清理 | 成功发布后将恢复用镜像固定为本地内容 ID，最多保留两份发布恢复点；请勿清理恢复使用的镜像 |

方案 ID 为 `workstation_monitoring`；内部设备／步骤 ID 和 Compose 项目名称沿用 `jetson_worktime`，以继续使用原部署目录和已有数据。名称与运行标识的对应关系见[运维说明](docs/operations.md#solution-naming)。手动恢复、诊断和验证边界见[运维说明](docs/operations.md)与[验证记录](docs/validation.md)。

## 步骤 2: 打开监测看板 {#verify_dashboard type=web_dashboard required=false config=devices/dashboard.yaml}

在部署完成的 Jetson 上打开看板。地址自动带入步骤 1 的主机与网页端口（默认 8088），确认页面可访问后完成摄像头配置。

### 部署完成

1. 打开部署完成页显示的 Jetson 地址。在设置中添加 RTSP 摄像头或选择 USB V4L2 设备，测试连接后保存。摄像头凭据仅保存在目标设备的持久化配置中，请勿填入方案 YAML。
2. 绘制工位、座位及物料区域后再开启统计；隐私模式默认开启。
3. 官方基础模型已预置。8GB 设备建议从 YOLO11n、batch 1 开始；需要时在模型页上传兼容的 YOLO `.pt` 模型。

Nano 自动选择较低预览规格的软件 H.264，NX 默认使用 NVIDIA 硬件 H.264。运行中接入 USB 摄像头后可刷新设备列表（通过宿主机 video 用户组访问）。升级前先完成或暂停训练；服务重启后未完成任务会标记为已中断，可在训练页从最新完整检查点继续。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| 页面无法打开 | 等待步骤 1 部署完成后刷新；确认浏览器可直接访问 Jetson 网页端口且防火墙已放行 |
| 无摄像头画面 | 重新测试 RTSP 地址或刷新 USB 设备列表；宿主用户需具备 video 组权限 |
| Nano 预览卡顿 | 在步骤 1 选择软件 H.264 后重新部署，保留较低预览规格 |
| 硬件编码不可用 | 选择软件 H.264 后重新部署；宿主多媒体驱动需符合本方案 L4T 基线 |
| 重启后训练中断 | 在训练页从最新完整检查点继续 |