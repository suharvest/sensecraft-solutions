## 套餐: 部署到 Jetson {#default}

在 reComputer Industrial（Jetson Orin）上运行 AI 加速的人员入侵检测，支持多摄像头、浏览器面板查看实时视频、配置安全规则，SQLite 事件持久化。

| 设备 | 用途 |
|------|------|
| reComputer Industrial（Jetson Orin NX / Nano） | 运行 AI 检测流程，提供 GPU 加速 |
| RTSP IP 摄像头 | 提供实时视频源（支持多摄像头） |

**部署完成后你能得到：**
- 浏览器中的实时标注视频流（检测框 + 区域 + 越线）—— 多摄像头自适应网格布局
- 可配置的禁区、围栏线、徘徊时长规则——每摄像头独立配置
- SQLite 事件持久化——重启不丢失，支持按日期筛选
- HTTP API 用于对接外部系统（`/api/stats`、`/api/events`、`/api/stream`）
- HDMI 全屏模式——按 **F** 键切换全屏显示

**前置条件：** Jetson 已装 JetPack 6.x · Docker + NVIDIA runtime · SSH 可访问 · 摄像头 RTSP 地址可用

**检测模型：** YOLO26n（默认，NMS-free，~268 QPS）· YOLOv8n · YOLOv5n —— TensorRT FP16 加速

## 步骤 1: 准备摄像头 {#init_camera type=manual required=false}

配置好你的 IP 摄像头并拿到 RTSP 地址。支持多摄像头同时接入。


1. 把 IP 摄像头和 Jetson 接到同一个网络（或 PoE 交换机）
2. 找到摄像头 IP——查看路由器 DHCP 列表，或用厂商的搜索工具
3. 登录摄像头 Web 后台，确认 RTSP 流已开启（一般默认开启）
4. 记下 RTSP 地址，下一步要填

> **常见 RTSP 地址格式：**
> - **海康：** `rtsp://admin:password@<ip>:554/Streaming/Channels/101`（主码流）或 `/102`（子码流）
> - **大华：** `rtsp://admin:password@<ip>:554/cam/realmonitor?channel=1&subtype=0`（主码流）或 `&subtype=1`（子码流）
> - **通用 ONVIF：** 用厂商 ONVIF 工具搜索流地址

**建议：** 先用 VLC 测一下（**媒体 → 打开网络串流 → 粘贴 URL**）。VLC 都打不开的话部署也跑不起来。

**多摄像头提示：** 部署完成后可以在 Web 面板中动态添加或移除摄像头。

### 故障排查

| 问题 | 解决办法 |
|------|--------|
| 进不去摄像头 Web | `ping <camera-ip>`，确认摄像头和电脑在同一网段 |
| VLC 拉不到 RTSP | 检查用户名密码。部分摄像头需要在设置里手动开启 RTSP |
| 不知道 RTSP 路径 | 试上面常见格式，或查摄像头说明书 |
| VLC 画面卡顿 / 花屏 | 改用子码流地址（分辨率 / 码率更低）—— 主码流可能超出网络承载 |

## 步骤 2: 部署工业安防服务 {#deploy type=docker_deploy required=true config=devices/deploy.yaml}

把检测服务装到 Jetson 上。部署器会拉取预构建镜像、把你的 RTSP 地址写入配置、启动容器。

### 部署目标 {#deploy_local type=local config=devices/deploy.yaml default=true}

直接在本机部署（仅限 SenseCraft 桌面 App 跑在 Jetson 设备上时可用）。

### 接线

1. 确认本机已装 Docker + NVIDIA runtime
2. 粘贴 步骤 1 中拿到的 **RTSP 地址**
3. 点 **部署**

> **说明：** 首次启动需要 1-2 分钟，系统在编译针对 Jetson 显卡优化的检测引擎。编译后会缓存，之后重启秒级完成。

### 部署完成

打开 **http://localhost:8080** 即可访问 Web 面板。你会看到：
- 主区域显示带标注的实时视频
- 默认有一个黄色禁区和一条品红色越线（可在浏览器中重新绘制）
- FPS、检测计数实时刷新

API 快速验证：

```bash
curl http://localhost:8080/api/stats
# 期望：返回包含当前 FPS、检测数、最近事件的 JSON

curl http://localhost:8080/api/events
# 期望：事件列表 JSON（首次部署为空）
```

### 故障排查

| 问题 | 解决办法 |
|------|--------|
| Docker 拉镜像很慢 | 镜像约 3-5 GB。国内建议先配置 Docker 镜像加速器 |
| 首次启动检测引擎构建失败 | 确认 JetPack 6.x 已装、`/usr/src/tensorrt` 存在。`docker logs industrial-security-demo` 看详情 |
| RTSP 打不开 | 在 Jetson 上 `ffprobe rtsp://...` 测试。确认摄像头和 Jetson 在同一网络 |
| 容器反复重启 | `docker logs industrial-security-demo` —— 最常见是 RTSP 地址错或摄像头不可达 |
| 面板视频空白 | 打开浏览器开发者工具 → 控制台 / 网络。MJPEG 流在 `/api/stream`，看是否能加载 |
| 找不到 GPU / nvidia 报错 | NVIDIA Container Runtime 没装：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |

### 部署目标 {#deploy_remote type=remote config=devices/deploy.yaml}

通过 SSH 部署到远程 Jetson。

### 接线

1. 确保 Jetson 已联网且 SSH 可达
2. 填入 Jetson IP、SSH 用户名、密码
   - reComputer Industrial 出厂默认：用户名 `nvidia` / 密码 `nvidia`（如已修改请按实际填）
3. 粘贴 步骤 1 中拿到的 **RTSP 地址**
4. 点 **部署** —— 系统会自动拉镜像、起服务

> **说明：** 首次启动需要 1-2 分钟，系统在编译针对 Jetson 显卡优化的检测引擎。编译后会缓存，之后重启秒级完成。

### 部署完成

打开 **http://\<jetson-ip\>:8080** 即可访问 Web 面板。你会看到：
- 主区域显示带标注的实时视频
- 默认有一个黄色禁区和一条品红色越线（可在浏览器中重新绘制）
- FPS、检测计数实时刷新

API 快速验证：

```bash
curl http://<jetson-ip>:8080/api/stats
# 期望：返回包含当前 FPS、检测数、最近事件的 JSON

curl http://<jetson-ip>:8080/api/events
# 期望：事件列表 JSON（首次部署为空）
```

### 故障排查

| 问题 | 解决办法 |
|------|--------|
| SSH 连接失败 | 先用电脑 `ssh user@ip` 试一下，确认 IP、用户名、密码正确 |
| Docker 拉镜像很慢 | 镜像约 3-5 GB。国内建议先配置 Docker 镜像加速器 |
| 首次启动检测引擎构建失败 | 确认 JetPack 6.x 已装、`/usr/src/tensorrt` 存在。`docker logs industrial-security-demo` 看详情 |
| RTSP 打不开 | 在 Jetson 上 `ffprobe rtsp://...` 测试。确认摄像头和 Jetson 在同一网络 |
| 容器反复重启 | `docker logs industrial-security-demo` —— 最常见是 RTSP 地址错或摄像头不可达 |
| 面板视频空白 | 打开浏览器开发者工具 → 控制台 / 网络。MJPEG 流在 `/api/stream`，看是否能加载 |
| 找不到 GPU / nvidia 报错 | NVIDIA Container Runtime 没装：`sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |

## 步骤 3: 配置安全规则 {#dashboard type=manual required=true}

在下一步打开面板后，根据现场情况调整安全规则：

- **重新绘制禁区** —— 在实时画面上点击多个点
- **移动越线** —— 移到你想报警的位置
- **调整徘徊时长阈值** —— 在禁区内停留多久才算
- **调节检测置信度** —— 越低越敏感，越高误报越少

修改保存后即时生效。

### 故障排查

| 问题 | 解决办法 |
|------|--------|
| 面板打不开 | 确认 Jetson 防火墙开放 8080：`sudo ufw status` |
| 视频画面卡死 | RTSP 中断了——检查摄像头，然后 `docker restart industrial-security-demo` |
| 事件不触发 | 置信度太高，或禁区没覆盖到实际行走路径。把置信度降到 0.25 再试 |
| 需要多个摄像头 | 已支持多摄像头——在 Web 面板的摄像头管理面板中动态添加摄像头 |

## 步骤 4: 打开面板 {#open_dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

工业安全面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |
### 部署完成

工业安防监控系统已经在边缘运行起来了。

#### 快速验证

1. 走进摄像头视野的禁区——约 1 秒内检测框应变红，事件日志中出现新事件
2. 越过围栏线——触发越线事件
3. 在禁区内站够徘徊时长——触发徘徊事件
4. 浏览器打开 `http://<jetson-ip>:8080/api/events`——能看到刚才触发的事件列表

#### API 参考

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | Web 面板 |
| `/api/stats` | GET | 实时 FPS、检测数、最近事件 |
| `/api/events` | GET | 事件历史（`?date=YYYYMMDD` 过滤） |
| `/api/config` | GET / POST | 读取或修改区域 / 线段 / 检测器阈值 |
| `/api/stream` | GET | 带标注的 MJPEG 视频流 |

#### 下一步

- 把 `/api/events` 接入现有的告警 / SCADA / 企微机器人
- 把事件汇总到 Loki / ELK 等中心化日志，做多站点监控
- 多摄像头场景：通过 Web 面板的摄像头管理添加多个摄像头，每个摄像头独立配置区域和规则
- [Industrial Security Demo on GitHub](https://github.com/Zhang-zu-hao/Industrial-security-demo)
