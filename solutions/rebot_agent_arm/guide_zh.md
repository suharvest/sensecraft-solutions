## 套餐: reCamera + reBot B601-DM {#default}

在 reCamera 上安装机械臂程序，可选在这台电脑上安装 AI 智能体服务、在摄像头上安装摄像头应用，最后在控制台里检查遥控并完成手眼标定。

| 设备 | 用途 |
|------|------|
| 装 B4 CAN 底板的 reCamera（SG2002） | 运行机械臂程序、网页控制台和摄像头应用 |
| reBot B601-DM 机械臂 | 接在 B4 底板的 CAN 口 |
| 这台电脑 | 执行部署；可选运行 AI 智能体服务 |

**部署完成后你可以：**
- 在手机、平板或电脑浏览器打开 `http://<摄像头>:8765` 遥控机械臂
- 通过 MCP 服务让这台电脑上的 AI 智能体读取状态并移动机械臂
- 用 ArUco 标记做手眼标定，或在视频上看到目标检测框

**前提条件：** 装 B4 CAN 底板的 reCamera（不支持 reCamera Pro）· 机械臂电源 · 部署时这台电脑能联网 · 标定需要打印 4x4_50 字典的 ArUco 标记

## 步骤 1: 安装 reBot 机械臂遥控 {#install_teleop type=recamera_console_app required=true config=devices/rebot_teleop.yaml}

在摄像头上安装机械臂程序和网页控制台。

### 前置条件

1. 摄像头通过 USB 连接（`192.168.42.1`），或与这台电脑在同一网络。
2. 登录账号为 `recamera` / `recamera`（早期固件为 `recamera.2`）。
3. 摄像头仍处于出厂 Node-RED 模式时，部署会提示先安装 reCamera 控制台。确认后会接着安装应用。

### 接线

1. 关闭机械臂电源和摄像头。
2. 把机械臂的 CAN 线接到 B4 底板 J2：5 脚 `CAN_H`（红线），6 脚 `CAN_L`（黑线）。
3. J2 的 1/2 脚接 12–24 V 直流，3/4 脚接地；摄像头和机械臂电源共地。
4. 上电，等约一分钟摄像头启动完成，再点击 **部署**。

### 部署完成

机械臂程序已运行，控制台地址是 `http://<摄像头>:8765`。摄像头同时开出 Wi-Fi 热点 `reCamera-Arm-Teleop`（默认密码 `12345678`，摄像头地址 `192.168.16.1`）供手机连接。在控制台里使能之前，机械臂不上力矩。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示 "missing hardware capability: can" | 摄像头没有 B4 CAN 底板，或 `can0` 没有起来。检查底板后重启摄像头 |
| 提示 "'rebot-teleop' is not in the catalog" | 这台电脑访问不到 `sensecraft-statics.seeed.cc`，或云端目录还没有这个应用。检查网络后重新部署 |
| 登录被拒绝 | 使用摄像头账号：`recamera` / `recamera`（或 `recamera.2`） |
| 存储空间不足 | 在控制台「应用」页卸载不用的应用 |

---

## 步骤 2: 在这台电脑上安装 AI 智能体服务（可选） {#install_mcp type=script required=false config=devices/mcp_server.yaml}

在这台电脑上安装 `rebot-mcp`，让 AI 智能体可以操控机械臂。

### 前置条件

1. 这台电脑能联网。如果没有 [uv](https://docs.astral.sh/uv/)，本步骤会用官方安装脚本安装；uv 会自行下载 Python。
2. 填写智能体连接摄像头用的地址：USB 为 `192.168.42.1`，连机械臂热点时为 `192.168.16.1`。

### 部署完成

`rebot-mcp` 已作为 uv 工具安装。装有 Claude Code 命令行（`claude`）时，服务会以 `rebot` 为名注册到当前用户。Claude Desktop、Cursor 等其他客户端：部署日志会打印一段 `mcpServers` 配置，粘贴到客户端的 MCP 配置里即可。

智能体可以做的事（14 个工具）：读取机械臂状态、拍摄画面（原图或带检测框）、读取检测结果、移动到指定位姿或按偏移移动、开合夹爪、回零位、收臂、使能力矩、停止、急停、获取或释放控制权。

默认安全设置：
- 智能体不能解除急停或故障，需要人在控制台里解除（未开启 `--allow-clear-fault`）。
- 智能体不能从控制台手里抢控制权（未开启 `--allow-preempt`）。
- 摄像头上的 `armd` 强制执行工作空间边界、速度上限，以及控制端失去响应时自动收臂的看门狗。

手动安装：先运行 `uv tool install "rebot-companion[agent] @ https://github.com/Seeed-Solution/rebot-companion/archive/refs/heads/main.zip"`，再运行 `claude mcp add --scope user rebot -- rebot-mcp --armd http://192.168.42.1:8765 --camera-ws ws://192.168.42.1:8001/`。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| uv 安装失败 | 按 [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) 手动安装 uv，再重新部署本步骤 |
| 智能体返回 `LEASE_BUSY` | 控制权在控制台手里。在控制台释放，或关掉控制台后让智能体调用 `take_control` |
| 智能体返回 `CAMERA_UNAVAILABLE` | 没有运行摄像头应用，在步骤 3 安装 |
| Claude Code 里看不到 `rebot` | 运行 `claude mcp list` 查看；没有的话执行上面的手动命令 |

---

## 步骤 3: 安装摄像头应用（可选） {#install_camera_app type=recamera_console_app required=false config=devices/camera_app.yaml}

选择 ArUco 标记（手眼标定）或 YOLO（目标检测）。

### 前置条件

1. 已完成步骤 1。
2. 摄像头同一时间只运行一个摄像头应用。步骤 4 的手眼标定需要 ArUco 标记；YOLO 会在控制台画面上加检测框并支持点选抓取。

### 部署完成

启用摄像头应用会停掉机械臂程序：控制台同一时间只运行一个画廊应用，而此前处于启用状态的是机械臂应用。请重启一次摄像头：打开控制台 `http://<摄像头>/`，进入 **系统**，点击 **重启**。重启后机械臂程序和摄像头应用都会启动。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 本步骤之后控制台打不开 | 按上面的方法重启摄像头 |
| 下拉框只有两个应用 | 本方案只提供这两个；其他应用在控制台的「从云端安装」里 |
| 应用没有启动 | 在控制台「应用」页查看状态，重新部署 |

---

## 步骤 4: 检查遥控并标定 {#open_cockpit type=web_dashboard required=true config=devices/cockpit.yaml}

打开控制台，移动机械臂，完成手眼标定。

### 部署完成

#### 检查遥控

1. 在手机、平板或这台电脑上打开 `http://<摄像头>:8765`。
2. 状态面板显示 CAN 总线反馈正常，关节表在刷新。
3. 按住力矩开关使能机械臂，用关节按钮或摇杆把 J1 点动几度。
4. 运行了摄像头应用时，能看到夹爪摄像头的画面。

#### 手眼标定（ArUco 标记）

1. 打印 4x4_50 字典的 ArUco 标记，平整固定在桌面上。
2. 打开「手眼标定」，选择眼在手上（摄像头装在夹爪上）。
3. 移动机械臂，从不同角度让标记出现在画面里，采集 9 个以上位姿。画面里只保留一个标记。
4. 点击「求解」，查看给出的 RMSE，导出 JSON。rebot-companion 用 `HandEyeCalibration.load_result` 加载。

#### 检测框（YOLO）

1. 打开「检测」，画面上出现检测框和标签。
2. 点选抓取只在仿真中测试过；尝试时手放在急停按钮旁。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 检查地址（USB 为 `192.168.42.1`，热点为 `192.168.16.1`）；装过摄像头应用的话，重启摄像头 |
| 没有画面 | 没有运行摄像头应用，完成步骤 3 |
| 控制台处于观察模式 | 其他客户端（例如 AI 智能体）持有控制权；在控制台确认接管，或停止智能体 |
| 机械臂无法使能 | 检查机械臂电源和 J2 的 CAN 接线 |
| 显示急停或故障 | 检查机械臂后在控制台里解除 |
