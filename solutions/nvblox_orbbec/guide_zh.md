## 套餐: Jetson NVBlox 部署 {#jetson_nvblox}

![NVBlox Orbbec 仓储场景动画演示](gallery/isaac_sim_nvblox_humans.gif)

通过 SSH 将 Orbbec Gemini2 与 Isaac ROS NVBlox 建图栈部署到 Jetson 设备。

| 设备 | 用途 |
|------|------|
| NVIDIA Jetson Orin | 运行主机侧 Orbbec ROS 2 驱动和长期运行的 NVBlox 容器 |

**本次部署会完成的内容**

- 可选地从 provisioning station 本机直接复制 `nvblox_images.tar`，这是通常最快的局域网传输路径
- 可选地从自定义镜像 URL 下载 `nvblox_images.tar`
- 使用内置 OneDrive 下载器拉取 `nvblox_images.tar`
- 在 Jetson 本地导入 Isaac ROS 基础镜像
- 准备 Jetson 主机侧 ROS 2 与 Orbbec 工作区
- 在 Jetson 上构建派生 NVBlox 运行时镜像与工作区
- 启动主机侧相机驱动与 Docker Compose 服务

**环境要求**

- Jetson Orin，Ubuntu 22.04，JetPack 6.x
- Orbbec Gemini2 已连接到 Jetson
- 可以通过 SSH 登录 Jetson
- Jetson 可以访问 apt、ROS 源和 GitHub
- 部署前 Jetson 至少需要 30GB 剩余磁盘空间
- 首次部署强烈建议预留 40GB 或更多空间，用于基础镜像 tar 缓存和工作区构建产物

## 步骤 1: 部署 NVBlox Orbbec {#deploy_nvblox_orbbec type=docker_deploy required=true config=devices/jetson_deploy.yaml}

将完整的 NVBlox Orbbec 栈部署到你的 Jetson。首次部署会比较重，因为会先准备主机环境和容器工作区，再由 Compose 启动最终服务。

点击 **Deploy** 前，请先确认 Jetson 根分区至少还有 30GB 可用空间；如果还需要在 Jetson 本地下载或保留基础镜像 tar，建议准备 40GB 以上，避免在部署中途因空间不足失败。


### 部署完成

NVBlox Orbbec 栈已经部署到你的 Jetson。

#### Validation Checklist

1. 部署页面中的 步骤 1 显示成功。
2. Compose 服务 `nvblox-orbbec` 保持运行。
3. 容器日志中出现 TF readiness 标记。
4. 容器日志中出现 runtime output probe 标记。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

通过 SSH 一键部署到 Jetson。

### 接线

1. 将 Orbbec Gemini2 相机连接到 Jetson。
2. 让 Jetson 与你的电脑处于同一网络。
3. 填写 Jetson 的 IP、SSH 用户名和密码。
4. 如果 provisioning station 所在主机上已经有 `nvblox_images.tar`，请填写 `本机基础镜像 tar 路径`，直接复制到 Jetson。
5. 如果你有更快的镜像源，也可以填写 `镜像直链`。
6. 点击 **Deploy**，并在整个部署过程中保持 Jetson 通电。

### 部署完成

1. 下载得到的基础镜像 tar 会缓存到 `~/nvblox_demo/downloads`。
2. Jetson 本地会存在 Isaac ROS 基础镜像。
3. 主机侧 Orbbec ROS 2 工作区会准备在 `~/nvblox_demo/ros2_ws`。
4. 容器侧工作区会准备在 `~/nvblox_demo/isaac_ros-dev`。
5. Jetson 上的 Compose 服务 `nvblox-orbbec` 会被启动。
6. 当前版本不提供预览页面，是否成功以容器日志中的运行就绪标记为准。

### 说明

- `tar + docker load` 只解决基础镜像来源，不会让整个流程完全离线。主机依赖安装和源码同步仍然需要联网。
- 通常最快的路径是 `本机基础镜像 tar 路径`，因为它会绕过 Jetson 到 SharePoint 的限速，直接走局域网/SSH 复制。
- 首次运行耗时较长，因为会在 Jetson 上安装 ROS 依赖、同步代码并构建工作区。
- 后续重复部署会复用受管 stamp 文件，只要已有准备状态仍然有效，就不会重复做全量准备。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| SSH 连接失败 | 检查 Jetson IP、用户名、密码以及 SSH 服务状态 |
| 运行时校验一开始就失败 | 确认目标设备是 Jetson Orin，系统为 Ubuntu 22.04 + JetPack 6.x |
| 运行时校验提示磁盘空间不足 | 清理 Jetson 根分区，至少保证剩余 30GB；首次部署建议预留 40GB 以上更稳妥 |
| Docker Compose 不可用 | 先安装 `docker compose` 或 `docker-compose` 后再重试 |
| 下载成功但镜像检查仍失败 | tar 中可能不包含预期 tag，请在 Jetson 上检查 `docker images` |
| 主机准备步骤失败 | 检查 Jetson 到 apt、ROS、GitHub 的网络连通性 |
| 主机相机步骤失败 | 重新连接 Gemini2，并确认设备会生成 `/dev/video*` |
| Compose 服务已运行但最终校验失败 | 在 Jetson 上执行 `cd ~/nvblox-orbbec/jetson && docker compose logs --tail=200` 查看日志 |


### 部署目标 {#jetson_local type=local config=devices/jetson_deploy.yaml}

将 NVBlox Orbbec 直接部署到本机。适用于已连接 Orbbec Gemini2 相机的 Jetson Orin 设备。

### 接线

1. 确保本机已安装 Docker 和 NVIDIA Container Toolkit。
2. 通过 USB 连接 Orbbec Gemini2 相机。
3. 点击 **Deploy** 开始本机部署。

> **注意：** 首次部署可能需要 10-15 分钟，期间会构建 Docker 镜像并安装 ROS 2 依赖。

### 部署完成

1. Compose 服务 `nvblox-orbbec` 正在本机运行。
2. Orbbec 相机驱动与 NVBlox 建图栈在容器内一起运行。
3. 是否成功以容器日志中的运行就绪标记为准。

### 故障排查

| 问题 | 处理方法 |
|------|----------|
| NVIDIA runtime 未找到 | 安装 NVIDIA Container Toolkit：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| 相机未检测到 | 检查 USB 连接：`lsusb | grep -i orbbec` |
| 容器持续重启 | 查看日志：`docker logs nvblox-orbbec` |
| Docker Compose 不可用 | 安装 `docker compose` 插件后重试 |
