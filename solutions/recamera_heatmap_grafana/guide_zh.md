## 套餐: AI 摄像头直连 {#recamera}

reCamera 在本地识别人并通过 MQTT 发出结果，一台电脑或 reComputer R1100 运行看板，保存历史数据。

- **设备：** reCamera；一台电脑或 reComputer R1100 运行看板。
- **软件：** 看板所在机器已安装 Docker，至少 2 GB 可用磁盘。
- **网络：** 所有设备在同一网络。

## 步骤 1: 启动数据看板 {#backend type=docker_deploy required=true config=devices/backend_deploy.yaml}

启动 MQTT broker、数据库、Grafana 看板和视频网关，所有摄像头都往这里发数据。部署时会自动发现同一网段的 ONVIF 摄像头；后端与摄像头不在同一网段时，在部署表单里手填摄像头地址。

### 部署目标 {#backend_local type=local config=devices/backend_deploy.yaml default=true}

### 接线

![接线图](gallery/architecture.svg)

确认 Docker Desktop 已启动。

### 故障排查

| 现象 | 处理 |
|------|------|
| 端口被占用 | 释放 8086、3000、8080 和 1883 端口 |
| Docker 不可用 | 启动 Docker Desktop |
| 磁盘空间不足 | 至少保留 2 GB 可用空间 |

### 部署目标 {#backend_remote type=remote config=devices/backend_deploy.yaml}

### 接线

![接线图](gallery/architecture.svg)

| 字段 | 示例 |
|------|------|
| 设备 IP | 192.168.1.100 或 reComputer-R110x.local |
| 用户名 | recomputer |
| 密码 | 设备当前 SSH 密码（出厂默认 12345678，建议修改） |

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网线，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |

---

## 步骤 2: 让摄像头发送数据 {#recamera type=recamera_cpp required=true config=devices/recamera_cpp.yaml}

在 reCamera 上安装零售分析应用，设置数据发往哪个 broker。应用输出驻足状态（浏览 / 驻足 / 需要帮助）和进出店计数。

### 接线

1. USB 连接时 IP 为 `192.168.42.1`；网线或 WiFi 连接时在路由器管理页面查 IP
2. 输入 reCamera IP、MQTT 服务器 IP（步骤 1 那台机器），以及安装点名称和摄像头编号
3. 同一门店的多台摄像头用同一个安装点名称、不同的摄像头编号，看板据此区分设备

这一步会停用 Node-RED 自启动，两者不能同时运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 看不到数据 | 确认步骤 1 已完成，reCamera 和服务器在同一网络 |
| 装完启动失败，日志里有 `device_init` 断言 | 重启摄像头 |

---

## 步骤 3: 把热力图映射到平面图（可选） {#heatmap type=manual required=false}

热力图默认显示摄像头视角，用内置校准工具可以显示在店铺平面图上。

### 操作步骤

1. 浏览器打开 **http://\<服务器IP\>:8080**
2. 点击右上角的 **齿轮图标**，打开校准设置
3. 在**校准哪台摄像头**里选中要校准的那台（选"全部"则作为所有未单独校准摄像头的默认值）
4. 左侧上传一张**摄像头截图**，右侧上传**店铺平面图**
5. 在摄像头截图上点 **4 个参考点**，再在平面图上点对应的 **4 个位置**，参考点选柱子、门口、墙角等间距大的标志物
6. 点击**保存**，校准立即生效

多台摄像头各自校准后，人流叠加在同一张平面图上；页面左上角的下拉框可以只看某一台。

### 故障排查

| 现象 | 处理 |
|------|------|
| 热力图位置不准 | 打开设置，点重置，换参考点重新校准 |
| 换了浏览器后校准还在 | 正常，校准保存在服务器上 |

### 什么时候可以跳过

只看摄像头视角的热力图时可以跳过。

## 步骤 4: 打开面板 {#dashboard_recamera type=web_dashboard required=true config=devices/dashboard.yaml}

点击下方按钮打开 Grafana 面板。

### 故障排查
| 现象 | 处理 |
|------|------|
| 页面无法加载 | 确认步骤 1 部署成功，在服务器上执行 `docker ps` 查看服务 |
| 主机/端口错误 | 部署到远程设备时，把地址换成设备 IP |
| 看不到数据 | 确认步骤 2 已完成，MQTT 服务器 IP 填的是步骤 1 那台机器 |

### 部署完成

- **数据看板**：http://\<服务器IP\>:3000，用 `admin` / `admin` 登录，查看人流趋势
- **实时热力图**：http://\<服务器IP\>:8080（点齿轮图标校准平面图）
- **视频网关**：http://\<服务器IP\>:1984，查看发现的摄像头和画面

---

## 套餐: reCamera Pro {#recamera_pro}

reCamera Pro 在本地做检测、跟踪、驻足状态和进出店计数，一台电脑或 reComputer R1100 运行看板。

- **设备：** reCamera Pro；一台电脑或 reComputer R1100 运行看板。
- **应用：** reCamera Pro 的应用中心里已安装 `retail-vision` 应用，本方案不提供该应用的安装包。
- **软件：** 看板所在机器已安装 Docker，至少 2 GB 可用磁盘。
- **网络：** 所有设备在同一网络。

## 步骤 1: 启动数据看板 {#backend_pro type=docker_deploy required=true config=devices/backend_deploy.yaml}

启动 MQTT broker、数据库、Grafana 看板和视频网关，已经部署过就跳过。部署时会自动发现同一网段的 ONVIF 摄像头；后端与摄像头不在同一网段时，在部署表单里手填摄像头地址。

### 部署目标 {#backend_pro_local type=local config=devices/backend_deploy.yaml default=true}

### 部署目标 {#backend_pro_remote type=remote config=devices/backend_deploy.yaml}

### 故障排查

| 现象 | 处理 |
|------|------|
| 端口被占用 | 释放 8086、3000、8080 和 1883 端口 |
| Docker 不可用 | 本机部署：启动 Docker Desktop；远程部署：确认设备上 Docker 服务在运行 |
| 磁盘空间不足 | 至少保留 2 GB 可用空间 |

## 步骤 2: 配置摄像头 {#recamera_pro_app type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

填入设备 Web 控制台账号（不是 SSH 账号）、安装点名称，以及步骤 1 那台机器的 MQTT 地址。MQTT 地址留空时，结果只在摄像头页面上显示，不上报看板。

### 故障排查

| 现象 | 处理 |
|------|------|
| 提示应用中心里没有 retail-vision | 先在设备的应用中心安装该应用，再重跑这一步 |
| 看板没有数据 | 确认 MQTT 地址填的是步骤 1 那台机器，且两者在同一网络 |
| 看板上 Avg Dwell 一直是空的 | 正常，Pro 的应用不输出人均驻足时长，其他指标不受影响 |

## 步骤 3: 打开面板 {#dashboard_pro type=web_dashboard required=true config=devices/dashboard.yaml}

点击下方按钮打开 Grafana 面板，登录账号 `admin` / `admin`。

### 部署完成

- **数据看板**：http://\<服务器IP\>:3000
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984，查看发现的摄像头和画面

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面无法加载 | 确认步骤 1 部署成功，在服务器上执行 `docker ps` 查看服务 |
| 主机/端口错误 | 部署到远程设备时，把地址换成设备 IP |

---

## 套餐: IP 摄像头 + 瑞芯微 NPU {#rk}

保留现有 IP 摄像头，用 reComputer RK3588 或 RK3576 在本地跑人流检测。

- **设备：** reComputer RK3588 或 RK3576；支持 RTSP 输出的 IP 摄像头。看板可以和检测器在同一块板卡上，也可以在另一台电脑上。
- **软件：** 看板所在机器已安装 Docker，至少 2 GB 可用磁盘。
- **网络：** 摄像头和板卡在同一网络。

## 步骤 1: 启动数据看板 {#backend_rk type=docker_deploy required=true config=devices/backend_deploy.yaml}

启动 MQTT broker、数据库、Grafana 看板和视频网关，已经部署过就跳过。部署时会自动发现同一网段的 ONVIF 摄像头；后端与摄像头不在同一网段时，在部署表单里手填摄像头地址。

### 部署目标 {#backend_rk_local type=local config=devices/backend_deploy.yaml default=true}

### 部署目标 {#backend_rk_remote type=remote config=devices/backend_deploy.yaml}

### 故障排查

| 现象 | 处理 |
|------|------|
| 端口被占用 | 释放 8086、3000、8080 和 1883 端口 |
| Docker 不可用 | 本机部署：启动 Docker Desktop；远程部署：确认设备上 Docker 服务在运行 |
| 磁盘空间不足 | 至少保留 2 GB 可用空间 |

## 步骤 2: 部署检测器 {#rk_detector type=docker_deploy required=true config=devices/rk_deploy.yaml}

通过 SSH 把检测器部署到板卡。板卡型号要选对，选错模型无法加载。看板在同一块板卡上时，MQTT 地址保持 `127.0.0.1`。

### 部署目标 {#rk_remote type=remote config=devices/rk_deploy.yaml default=true}

板卡须已安装 Docker 和 NPU 驱动（`/usr/lib/librknnrt.so` 存在）。

### 故障排查

| 现象 | 处理 |
|------|------|
| 容器起不来，报 librknnrt 相关错误 | 板卡上缺 NPU 驱动，确认 `/usr/lib/librknnrt.so` 存在 |
| 看板没数据 | 用 `ffprobe rtsp://...` 确认摄像头地址能通，检查 MQTT 地址 |
| 帧率明显偏低、CPU 占满 | 硬件解码未生效，确认板卡上的 MPP 库完整 |

## 步骤 3: 打开面板 {#dashboard_rk type=web_dashboard required=true config=devices/dashboard.yaml}

### 部署完成

- **数据看板**：http://\<服务器IP\>:3000，用 `admin` / `admin` 登录
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984，查看发现的摄像头和画面

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面无法加载 | 确认步骤 1 部署成功，在服务器上执行 `docker ps` 查看服务 |
| 主机/端口错误 | 部署到远程设备时，把地址换成设备 IP |

---

## 套餐: IP 摄像头 + reComputer Industrial R20（Hailo） {#hailo}

保留现有 IP 摄像头，用带 Hailo-8 加速卡的 reComputer Industrial R20 在本地跑人流检测。

- **设备：** reComputer Industrial R20 系列（带 Hailo-8）；支持 RTSP 输出的 IP 摄像头。看板可以和检测器在同一块板卡上，也可以在另一台电脑上。
- **软件：** 看板所在机器已安装 Docker，至少 2 GB 可用磁盘。
- **网络：** 摄像头和板卡在同一网络。
- **限制：** 一块 Hailo-8 同时只能运行一个应用。板上已有其他 Hailo 应用在运行时，检测器无法启动。

## 步骤 1: 启动数据看板 {#backend_hailo type=docker_deploy required=true config=devices/backend_deploy.yaml}

启动 MQTT broker、数据库、Grafana 看板和视频网关，已经部署过就跳过。部署时会自动发现同一网段的 ONVIF 摄像头；后端与摄像头不在同一网段时，在部署表单里手填摄像头地址。

### 部署目标 {#backend_hailo_local type=local config=devices/backend_deploy.yaml default=true}

### 部署目标 {#backend_hailo_remote type=remote config=devices/backend_deploy.yaml}

### 故障排查

| 现象 | 处理 |
|------|------|
| 端口被占用 | 释放 8086、3000、8080 和 1883 端口 |
| Docker 不可用 | 本机部署：启动 Docker Desktop；远程部署：确认设备上 Docker 服务在运行 |
| 磁盘空间不足 | 至少保留 2 GB 可用空间 |

## 步骤 2: 部署检测器 {#hailo_detector type=docker_deploy required=true config=devices/hailo_deploy.yaml}

通过 SSH 把检测器部署到板卡。部署前会检查 Hailo 运行时版本，不匹配时停止并显示板上实际的版本。

### 部署目标 {#hailo_remote type=remote config=devices/hailo_deploy.yaml default=true}

板卡须已安装 Docker 和 HailoRT **4.21**（驱动、用户库、GStreamer 插件版本一致）。

### 故障排查

| 现象 | 处理 |
|------|------|
| 报 `HAILO_OUT_OF_PHYSICAL_DEVICES` | 加速卡被另一个应用占用，先停掉它 |
| 部署时提示 libhailort 版本不符 | 把板上的 HailoRT 换成 4.21，驱动和用户库一起换 |
| `/dev/hailo0` 不存在 | 加速卡没插好，或 `hailo_pci` 驱动没加载 |
| 看板没数据 | 用 `ffprobe rtsp://...` 确认摄像头地址能通，检查 MQTT 地址 |

## 步骤 3: 打开面板 {#dashboard_hailo type=web_dashboard required=true config=devices/dashboard.yaml}

### 部署完成

- **数据看板**：http://\<服务器IP\>:3000，用 `admin` / `admin` 登录
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984，查看发现的摄像头和画面

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面无法加载 | 确认步骤 1 部署成功，在服务器上执行 `docker ps` 查看服务 |
| 主机/端口错误 | 部署到远程设备时，把地址换成设备 IP |

## 套餐: 传统摄像头改造 {#jetson}

保留现有 IP 摄像头，用 NVIDIA Jetson 在本地跑人流检测。

- **设备：** NVIDIA Jetson（Orin 系列）；支持 RTSP 输出的 IP 摄像头。看板可以和检测器在同一台 Jetson 上，也可以在另一台电脑上。
- **软件：** 看板所在机器已安装 Docker，至少 2 GB 可用磁盘。
- **网络：** 摄像头和 Jetson 在同一网络。

## 步骤 1: 启动数据看板 {#backend_jetson type=docker_deploy required=true config=devices/backend_deploy.yaml}

启动 MQTT broker、数据库、Grafana 看板和视频网关，已经部署过就跳过。部署时会自动发现同一网段的 ONVIF 摄像头；后端与摄像头不在同一网段时，在部署表单里手填摄像头地址。

### 部署目标 {#backend_jetson_local type=local config=devices/backend_deploy.yaml default=true}

### 部署目标 {#backend_jetson_remote type=remote config=devices/backend_deploy.yaml}

### 故障排查

| 现象 | 处理 |
|------|------|
| 端口被占用 | 释放 8086、3000、8080 和 1883 端口 |
| Docker 不可用 | 本机部署：启动 Docker Desktop；远程部署：确认设备上 Docker 服务在运行 |
| 磁盘空间不足 | 至少保留 2 GB 可用空间 |

## 步骤 2: 部署检测器 {#jetson_deploy type=docker_deploy required=true config=devices/jetson_deploy.yaml}

通过 SSH 把检测器部署到 Jetson。首次部署会编译 TensorRT engine，需要 2-5 分钟，之后的部署直接复用。

### 部署目标 {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

Jetson 须为 JetPack 6.x，已安装 Docker 和 NVIDIA runtime。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 `ping` 验证 Jetson IP |
| NVIDIA 运行时错误 | 在 Jetson 上运行 `nvidia-smi` 确认 GPU 可用 |
| 没有数据 | 用 `ffprobe rtsp://...` 验证 RTSP 地址，检查 MQTT 地址 |
| 首次启动慢 | 正在编译 TensorRT engine，仅首次，2-5 分钟 |

## 步骤 3: 打开面板 {#dashboard_jetson type=web_dashboard required=true config=devices/dashboard.yaml}

### 部署完成

- **数据看板**：http://\<服务器IP\>:3000，用 `admin` / `admin` 登录
- **实时热力图**：http://\<服务器IP\>:8080
- **视频网关**：http://\<服务器IP\>:1984，查看发现的摄像头和画面

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面无法加载 | 确认步骤 1 部署成功，在服务器上执行 `docker ps` 查看服务 |
| 主机/端口错误 | 部署到远程设备时，把地址换成设备 IP |

---
