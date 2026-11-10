## 套餐: reCamera + reBot B601-DM {#default}

在 reCamera 上安装 reBot 遥控应用，在这台电脑上安装 AI 智能体服务（MCP），然后打开控制台移动机械臂，并用 ArUco 标记完成手眼标定。

| 设备 | 用途 |
|------|------|
| 装 B4 CAN 底板的 reCamera（SG2002） | 运行机械臂程序、网页控制台和摄像头视觉（同一个应用：rebot-teleop） |
| reBot B601-DM 机械臂 | 接在 B4 底板的 CAN 口 |
| 这台电脑 | 执行部署，运行 AI 智能体服务 |

**部署完成后你可以：**
- 在手机、平板或电脑浏览器打开 `http://<摄像头>:8765` 遥控机械臂
- 同一个应用里提供摄像头画面、YOLO 目标检测和 ArUco 标记识别
- 通过 MCP 服务让这台电脑上的 AI 智能体读取状态、查看摄像头画面并移动机械臂
- 用 ArUco 标记做手眼标定

**前提条件：** 装 B4 CAN 底板的 reCamera（不支持 reCamera Pro）· 机械臂电源 · 部署时这台电脑能联网 · 标定需要打印 4x4_50 字典的 ArUco 标记（默认边长 5 cm）

## 步骤 1: 在摄像头上安装 reBot 遥控 {#install_teleop type=recamera_console_app required=true config=devices/rebot_teleop.yaml}

安装 rebot-teleop 应用：机械臂控制、网页控制台和摄像头视觉。

### 前置条件

1. 摄像头通过 USB 连接（`192.168.42.1`），或与这台电脑在同一网络。
2. 登录账号为 `recamera` / `recamera`（早期固件为 `recamera.2`）。
3. 摄像头仍处于出厂 Node-RED 模式时，部署会提示先安装 reCamera 控制台。确认后会接着安装应用。

### 接线

1. 关闭机械臂电源和摄像头。
2. 把机械臂的 CAN 线接到 B4 底板的 J2：5 脚 `CAN_H`（红线），6 脚 `CAN_L`（黑线）。
3. J2 的 1/2 脚接 12–24 V 直流电源，3/4 脚接地；摄像头和机械臂电源共地。
4. 上电，等摄像头启动约一分钟，然后点击**部署**。

### 部署完成

rebot-teleop 成为当前运行的应用。它运行 `armd`（控制台地址 `http://<摄像头>:8765`）和 `rebot-vision`（视频 `ws://<摄像头>:8001/`，按需运行 YOLO 和 ArUco）。摄像头还会开出 Wi-Fi 热点 `reCamera-Arm-Teleop`（默认密码 `12345678`，摄像头地址 `192.168.16.1`），供手机连接。在控制台里使能之前，机械臂不上力矩。

应用已包含摄像头视觉，不需要再装其他摄像头应用。在 reCamera 控制台里启用其他应用会停止 rebot-teleop。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 提示 "missing hardware capability: can" | 摄像头没有 B4 CAN 底板，或 `can0` 没有启动。检查底板后重启摄像头 |
| 提示 "'rebot-teleop' is not in the catalog" | 这台电脑访问不了 `sensecraft-statics.seeed.cc`，或应用目录比本方案旧。检查网络后重新部署 |
| 登录被拒绝 | 使用摄像头账号：`recamera` / `recamera`（或 `recamera.2`） |
| 存储空间不足 | 在控制台的应用页面卸载不用的应用 |
| 用过控制台后机械臂控制台打不开 | 启用了其他应用。在控制台的应用页面重新启用 rebot-teleop |

---

## 步骤 2: 在这台电脑上安装 AI 智能体服务 {#install_mcp type=script required=true config=devices/mcp_server.yaml}

从 [rebot-companion](https://github.com/Seeed-Solution/rebot-companion) 安装 `rebot-mcp`，并接入 Claude Code 或 Claude Desktop。

### 前置条件

1. 这台电脑能联网。没有 [uv](https://docs.astral.sh/uv/) 时，这一步会用官方安装脚本装上；uv 会自己下载 Python。不需要 git。
2. 填写智能体连接摄像头用的地址：USB 为 `192.168.42.1`，连机械臂热点时为 `192.168.16.1`。

### 部署完成

`rebot-mcp` 已作为 uv 工具安装。服务跑在这台电脑上，通过网络连接机械臂；摄像头上不需要另外安装任何东西。

- **Claude Code**：如果装了 `claude` 命令行，服务会以 `rebot` 的名字注册到当前用户。用 `claude mcp list` 查看。
- **Claude Desktop**：把部署日志末尾打印的 `mcpServers` 配置复制到 `claude_desktop_config.json`（Claude Desktop：**Settings → Developer → Edit Config**），然后重启 Claude Desktop。Cursor、Windsurf 等使用 `mcpServers` 格式的客户端用同一段配置。

智能体可用的工具（14 个）：`get_state`、`snapshot`、`snapshot_annotated`、`detect`（pipelines 可选 `yolo`、`aruco` 或两者）、`move_to`、`move_relative`、`gripper`、`home`、`park`、`stop`、`e_stop`、`enable`、`take_control`、`release_control`。

默认安全设置：
- 智能体不能解除急停或故障，需要人在控制台里解除。只有服务以 `--allow-clear-fault` 启动时才会出现 `clear_fault` 工具。
- 智能体不能从控制台手里抢走控制权。只有加 `--allow-preempt` 才能强制接管。
- 摄像头上的 `armd` 会限制工作空间和速度，控制方停止响应时由控制权看门狗把机械臂收回停放位。

#### 手动安装

与 rebot-companion README 中的命令一致：

```bash
git clone https://github.com/Seeed-Solution/rebot-companion
cd rebot-companion
uv sync --extra agent
claude mcp add rebot -- uv run --directory /path/to/rebot-companion --extra agent rebot-mcp \
  --armd http://192.168.42.1:8765
```

Claude Desktop 在 `mcpServers` 里加入：

```json
{
  "mcpServers": {
    "rebot": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/rebot-companion", "--extra", "agent",
               "rebot-mcp", "--armd", "http://192.168.42.1:8765"]
    }
  }
}
```

视频流默认是 `ws://192.168.42.1:8001/`；摄像头用其他地址时，加上 `--camera-ws ws://<摄像头>:8001/`。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| uv 安装失败 | 按 [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) 手动安装 uv，然后重新部署这一步 |
| 智能体返回 `LEASE_BUSY` | 控制台持有控制权。在控制台里释放，或关闭控制台后让智能体调用 `take_control` |
| 智能体返回 `CAMERA_UNAVAILABLE` 或 `DETECTOR_UNAVAILABLE` | 摄像头上当前运行的不是 rebot-teleop。在控制台的应用页面启用它 |
| 智能体返回 `ESTOP_ACTIVE` 或 `FAULT_ACTIVE` | 检查机械臂后，在控制台里解除 |
| Claude Code 里没有 `rebot` | 运行 `claude mcp list`；没有的话执行上面的手动命令 |
| Claude Desktop 里看不到 `rebot` 工具 | 检查 JSON 格式正确、`command` 路径存在，然后重启 Claude Desktop |

---

## 步骤 3: 打开控制台并完成标定 {#open_cockpit type=web_dashboard required=true config=devices/cockpit.yaml}

打开控制台，移动机械臂，并用 ArUco 标记完成手眼标定。

### 部署完成

#### 检查遥控

1. 在手机、平板或这台电脑上打开 `http://<摄像头>:8765`。
2. 页面显示摄像头画面；专家模式下连接状态显示 CAN 反馈，关节表实时刷新。
3. 按住力矩开关使能机械臂，再用摇杆把 J1 点动几度。

#### 手眼标定（ArUco 标记）

1. 打印 4x4_50 字典的 ArUco 标记（默认边长 5 cm），平贴在桌面上。
2. 打开**手眼标定**，**相机安装方式**选**相机在夹爪上**。
3. 移动机械臂，从不同角度拍到标记并采集位姿：至少 5 个，建议 9 个。画面里只保留一个标记。
4. 点击**求解标定**，查看给出的 RMSE，再点击**导出配置**。rebot-companion 用 `HandEyeCalibration.load_result` 加载导出的 JSON。

#### 检测叠加

1. 打开识别，选择 YOLO、ArUco 或两者；画面上会画出检测框和标记。
2. 点选抓取只在仿真中测试过；尝试时手放在急停上。

#### 试试智能体

对 Claude 说："读取机械臂状态，拍一张照片，告诉我摄像头看到了什么。"需要智能体移动机械臂时，先关闭控制台或在控制台里释放控制权。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 检查地址（USB 为 `192.168.42.1`，热点为 `192.168.16.1`），并确认控制台里当前运行的是 rebot-teleop |
| 没有画面 | rebot-vision 会自动重启，等几秒。一直黑屏时，在控制台的应用页面重启 rebot-teleop |
| YOLO 显示不可用 | 摄像头上没有 YOLO11n 模型；应用使用设备上已有的模型。ArUco 和标定不受影响 |
| 控制台进入观察者模式 | 另一个客户端（例如 AI 智能体）持有控制权；在控制台确认接管，或停止智能体 |
| 机械臂无法使能 | 检查机械臂电源和 J2 上的 CAN 接线 |
| 显示急停或故障 | 检查机械臂后在控制台里解除 |
| 求解提示残差偏大 | 采集时保持标记固定、机械臂静止，删除标黄的位姿后重新求解 |
