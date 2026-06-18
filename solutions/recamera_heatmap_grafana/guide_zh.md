## 套餐: 传统摄像头改造 {#jetson}

手上有 IP 摄像头？加一台 AI 盒子（NVIDIA Jetson），让传统摄像头变成智能热力图传感器，不用换设备。

| 设备 | 用途 |
|------|------|
| NVIDIA Jetson（Orin 系列） | 运行 YOLO11 检测 + Grafana + InfluxDB |
| IP 摄像头（RTSP） | 任何支持 RTSP 输出的摄像头 |

**部署后能做什么：**
- GPU 加速 YOLO11 检测，约 18 FPS
- 支持多个 RTSP 摄像头
- 共用 Grafana 看板和热力图

**前提条件：** NVIDIA Jetson（JetPack 6.x） · Docker（含 NVIDIA runtime） · RTSP IP 摄像头在同一网络

## 步骤 1: 部署到 Jetson {#jetson_deploy type=docker_deploy required=true config=devices/jetson_deploy.yaml}

通过 SSH 将完整系统（YOLO 检测器 + InfluxDB + Grafana + MQTT）部署到 Jetson。

### 部署目标 {#local type=local config=devices/jetson_deploy.yaml default=true}

直接在本机 Jetson（运行 SenseCraft Solution 的这台设备）上部署。首次 TensorRT 引擎编译需要 2-5 分钟。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml}

通过 SSH 部署到另一台 Jetson。首次 TensorRT 引擎编译需要 2-5 分钟。

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 连接超时 | 检查网络，用 `ping` 验证 Jetson IP |
| NVIDIA 运行时错误 | 在 Jetson 上运行 `nvidia-smi` 确认 GPU 可用 |
| 没有视频画面 | 用 `ffprobe rtsp://...` 验证 RTSP 地址 |
| 首次启动慢 | TensorRT 引擎编译（仅一次，2-5 分钟） |

---

## 步骤 2: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Grafana 面板已经运行（登录账号 `admin` / `admin`）。点击下方按钮在浏览器中打开。带检测框的原始 MJPEG 视频流也可以在 `http://<jetson-ip>:5001` 访问，方便嵌入到其他系统。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 看板没有数据 | 等待 1-2 分钟，数据点正在生成 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

### 部署完成

Jetson 热力图系统已运行！

**访问地址：**
- **数据看板**：http://\<jetson-ip\>:3000 — Grafana 图表和趋势
- **实时检测**：http://\<jetson-ip\>:5001 — YOLO 检测 + 热力图叠加

---

## 套餐: AI 摄像头直连 {#recamera}

加一台电脑跑看板，保存历史数据，随时回看人流变化。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，识别人并发送位置数据 |
| 电脑 或 reComputer R1100 | 运行 Grafana 看板 + InfluxDB |

**部署完成后你可以：**
- 用图表看一天、一周的人流变化
- 自定义看板布局
- 导出数据做分析

**前提条件：** Docker 已安装 · 所有设备在同一网络

## 步骤 1: 启动数据看板 {#backend type=docker_deploy required=true config=devices/backend_deploy.yaml}

在你的电脑（或专用服务器）上启动数据存储和图表显示服务。

### 部署目标 {#backend_local type=local config=devices/backend_deploy.yaml default=true}

### 接线

![接线图](gallery/architecture.svg)

确保 Docker Desktop 已安装并运行，至少 2GB 可用磁盘空间。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 关闭占用 8086 或 3000 端口的程序 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 启动后自动停止 | 确保电脑有至少 4GB 内存 |

### 部署目标 {#backend_remote type=remote config=devices/backend_deploy.yaml}

### 接线

![接线图](gallery/architecture.svg)

| 字段 | 示例 |
|------|------|
| 设备 IP | 192.168.1.100 或 reComputer-R110x.local |
| 用户名 | recomputer |
| 密码 | 12345678 |

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping 测试 |
| SSH 认证失败 | 确认用户名密码正确 |

---

## 步骤 2: 让摄像头发送数据 {#recamera type=recamera_nodered required=true config=devices/recamera.yaml}

告诉 reCamera 把人流数据发到哪里。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入 reCamera IP 和看板服务器 IP（来自步骤 1）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 看不到数据 | 确认步骤 1 已完成，reCamera 和服务器在同一网络 |

---

## 步骤 3: 把热力图映射到平面图（可选） {#heatmap type=manual required=false}

默认热力图显示的是摄像头视角。如果想把热力图显示在你店铺的平面图上，用内置的校准工具即可。

### 操作步骤

1. 浏览器打开 **http://\<服务器IP\>:8080**
2. 点击右上角的 **齿轮图标**，打开校准设置
3. 左侧上传一张**摄像头截图**，右侧上传你的**店铺平面图**
4. 在摄像头截图上点 **4 个参考点**，再在平面图上点对应的 **4 个位置**
5. 点击**保存**，校准立即生效

**提示：** 选择间距大的明显标志物作为参考点，比如柱子、门口、墙角。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 热力图位置不准 | 重新打开设置，点重置，用更好的参考点重新校准 |
| 清除浏览器数据后校准丢失 | 重新打开设置再校准一次，校准数据保存在浏览器中 |

### 什么时候可以跳过

如果只想看摄像头视角的热力图，不需要映射到平面图，可以跳过。

## 步骤 4: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Grafana 面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

### 部署完成

热力图看板已就绪！

**访问服务：**
- **数据看板**：http://\<服务器IP\>:3000 — 用 `admin` / `admin` 登录，查看人流趋势图表
- **实时热力图**：http://\<服务器IP\>:8080 — 实时热力图叠加（点齿轮图标可校准平面图）

两个服务在步骤 1 部署时就已自动启动。

**遇到问题？**
- 看不到数据？检查摄像头是否已连接（步骤 2）
- 打不开页面？运行 `docker ps` 检查服务是否在运行
