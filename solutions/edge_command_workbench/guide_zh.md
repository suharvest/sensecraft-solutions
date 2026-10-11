## 套餐: 远程 RK3576 {#rk3576_remote}

通过 SSH 将本地命令工作台部署到一台 RK3576 Linux 设备。本套餐只面向 RK3576，不包含 Jetson 或 RK3588。

## 步骤 1: 部署工作台 {#deploy type=docker_remote required=true config=devices/rk3576_remote.yaml}

部署过程会准备固定版本的应用归档、RKNN 模型和 tokenizer，然后在目标设备的 18768 端口启动单容器 Web 工作台。目标设备需要已有 Docker 和 RKNN 运行时库。

### 部署目标 {#rk3576 type=remote device_name="RK3576" config=devices/rk3576_remote.yaml default=true}

部署文件放在目标设备的 `/home/<username>/edge-command-workbench`。流程会跳过 Docker 安装和 Docker 镜像拉取；只有在目标设备没有精确的本地镜像标签时才加载镜像归档。部署前请保留至少 4GB 磁盘空间，安装 Docker 和 `/usr/lib/librknnrt.so`，并提供已测试的 RK3576 NPU DRM 节点 `/dev/dri/card1` 与 `/dev/dri/renderD129`。

填写目标设备 IP 或主机名、SSH 用户名和 SSH 密码。已有兼容本地语音服务的地址为可选项，不需要语音时留空，然后点击 **部署**。

### 接线

1. 给 RK3576 上电，并接入运行 SenseCraft Solution 的电脑所在网络。
2. 接好设备网络接口，部署期间保持物理连接稳定。

### 部署完成

打开 `http://<device-ip>:18768` 验证页面。页面由已部署的应用提供。浏览器在 localhost 或本地网络打开时可使用 HTTP；可选语音服务要使用浏览器麦克风时，需要 HTTPS 或 localhost。

#### 可选语音服务

只有目标设备已有兼容的本地语音服务时才填写 `VOICE_SERVICE_URL`；本方案不会自动安装语音服务。

### 故障排查

| 现象 | 处理 |
|------|------|
| 缺少镜像归档或 tokenizer 校验值 | 在构建归档后补齐发布 manifest 的校验值；脚本会在启动 Docker 前停止。 |
| 加载后没有目标镜像标签 | 确认归档是 RK3576 arm64 构建，并包含 `edge-command-workbench:rk3576-0.1.0`。 |
| RKNN 库报错 | 检查目标设备的 `/usr/lib/librknnrt.so`，并保留 compose 中的只读挂载。 |
| 18768 端口被占用 | 检查占用服务的归属，停止后再重试。 |
| 工作台无法打开 | 检查目标设备 IP，并确认 `docker compose ps` 显示工作台容器为 healthy。 |

## 步骤 2: 打开工作台 {#verify type=web_dashboard required=true config=devices/dashboard.yaml}

打开已部署的 Web 工作台并提交带候选命令的请求。页面能加载且返回 JSON 决策响应时，表示容器、模型挂载、tokenizer 挂载和 RKNN 后端可访问。

### 部署完成

#### HTTP 检查

打开 `http://<device-ip>:18768/api/health`，确认服务健康。主要决策接口是 18768 端口上的 `POST /api/decide`。

### 故障排查

| 现象 | 处理 |
|------|------|
| 健康检查尚未就绪 | 等待模型加载，然后查看 `docker logs edge-command-workbench`。 |
| 语音按钮不可用 | 保持语音关闭，或填写已有兼容的 `VOICE_SERVICE_URL`；本套餐不会安装 ASR。 |

## 套餐: RK3576 Kev RKLLM {#rk3576_rkllm_remote}

此套餐在 cat-remote RK3576 上部署已测试的 Kev RKLLM 路径。engine 导出容量为 8192 tokens，但该设备上的部署 guard 和 metadata 将请求限制为 2048 tokens，因为 8K 配置触发了全局 OOM。运行时、engine、head、tokenizer 和 metadata 均作为固定版本外部产物记录。

## 步骤 1: 部署 Kev 工作台 {#deploy_rk3576_rkllm type=docker_remote required=true config=devices/rk3576_rkllm_remote.yaml}

容器选择 `DECISION_BACKEND=rkllm` 和 `MODEL_ID=kev`。请准备包含 `model.rkllm`、`kev_head.npz`、`tokenizer/tokenizer.json` 以及固定版本运行时 `runtime/librkllmrt.so` 的模型目录。只有使用固定版本 RKLLM 1.3.1 头文件构建时，镜像才包含 C helper。

### 部署目标 {#rk3576_rkllm type=remote device_name="RK3576" config=devices/rk3576_rkllm_remote.yaml default=true}

填写 SSH 信息。RKLLM 首次准备至少需要 3GB 可用空间（实测新鲜产物峰值约 1.94GB，并保留 1GB 余量）。可选的 `MODEL_SERVICES_JSON` 可将其他模型系列映射到已有 HTTP 服务；当前容器只在本地加载 Kev。`VOICE_SERVICE_URL` 仅连接已有兼容语音服务，不会安装 ASR。

### 部署完成

打开 `http://<设备 IP>:18768`。验证要求 `/api/health` 返回 `model_ready: true`、`backend: "rkllm"` 和 `model_id: "kev"`。

## 步骤 2: 打开 Kev 工作台 {#verify_rk3576_rkllm type=web_dashboard required=true config=devices/dashboard_rk3576_rkllm.yaml}

健康检查确认 Kev 模型就绪后，提交带候选命令的请求。

## 套餐: RK3588 Kev RKLLM {#rk3588_rkllm_remote}

此套餐在 Radxa RK3588 上部署已测试的 8K Kev 产物契约，已验证部署上下文为 8192 tokens；结果只适用于已测试设备，不推断其他可用内存不同的板卡。

## 步骤 1: 部署 Kev 工作台 {#deploy_rk3588_rkllm type=docker_remote required=true config=devices/rk3588_rkllm_remote.yaml}

为目标设备提供固定版本 engine、FP32 Q/K head、tokenizer、metadata 和 RKLLM 运行时目录。服务启动时不会下载模型权重。

### 部署目标 {#rk3588_rkllm type=remote device_name="RK3588" config=devices/rk3588_rkllm_remote.yaml default=true}

可通过部署字段配置可选远程模型配置和已有语音服务。

### 部署完成

打开 `http://<设备 IP>:18768`，确认健康接口报告模型就绪后再发送决策请求。

## 步骤 2: 打开 Kev 工作台 {#verify_rk3588_rkllm type=web_dashboard required=true config=devices/dashboard_rk3588_rkllm.yaml}

健康检查确认 Kev 模型就绪后，提交带候选命令的请求。

### 已发布产物记录

RKLLM 0.3.1 ef82 镜像已发布到 Hugging Face revision [`db0545065d4da3598d009407fc3bd0c7632ca199`](https://huggingface.co/harvestsu/laya-multilingual-rknn-tensorrt/commit/db0545065d4da3598d009407fc3bd0c7632ca199)，沿用路径前缀 `releases/edge-workbench-0.3.0`。当前 active inventory 包含新镜像、原有 2 个模型和 13 个共享产物；旧 d870 镜像保留为历史记录。新版本证据见 [`assets/evidence/hf-release-0.3.1-20261011.json`](assets/evidence/hf-release-0.3.1-20261011.json)。

记录的镜像检查返回 HTTP 308 并跳转到 Hugging Face 源站；证据不宣称已完成镜像原生大文件下载。

### RK3588 镜像 bootstrap 证据

Radxa 上按固定 revision fresh bootstrap 完成了 14 项 RK3588 目标文件校验。目标设备已有精确镜像标签和 config，因此跳过 Docker load，现有容器保持运行。原始 bootstrap 日志和校验摘要见 [`assets/evidence/radxa-rk3588-bootstrap-20261011.log`](assets/evidence/radxa-rk3588-bootstrap-20261011.log) 与 [`assets/evidence/radxa-rk3588-bootstrap-20261011.json`](assets/evidence/radxa-rk3588-bootstrap-20261011.json)。Radxa 镜像请求返回 mirror HTTP 302 并转到签名 CAS bridge；Spark 的独立 308-to-origin 行为已单独记录，不推广到所有设备。
