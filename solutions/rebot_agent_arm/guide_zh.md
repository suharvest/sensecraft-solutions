## 套餐: reCamera + reBot B601-DM：真机遥操与 AI 控制 {#default}

在 reCamera 上安装 `rebot-teleop`，通过网页控制台遥控机械臂与完成标定，并按需在这台电脑安装 `rebot-mcp` 接入 AI 智能体控制。

**前提条件：** 装 B4 CAN 底板的 reCamera（不支持 reCamera Pro）· reBot B601-DM 机械臂与 12–24 V 直流电源（共地）· 本机可联网 · 标定需打印 4x4_50 ArUco 标记（5 cm）

## 步骤 1: 在摄像头上安装 reBot 遥控 {#install_teleop type=recamera_console_app required=true config=devices/rebot_teleop.yaml}

将 `rebot-teleop` 部署到 reCamera（USB 连接为 `192.168.42.1`，或与电脑处于同一局域网；默认账号 `recamera` / `recamera`，早期固件为 `recamera.2`）。若摄像头处于出厂 Node-RED 模式，按提示先确认安装 reCamera 控制台即可。

### 接线

1. 关闭机械臂电源与摄像头电源。
2. 将机械臂 CAN 线接到 B4 底板 J2：5 脚 `CAN_H`（红线），6 脚 `CAN_L`（黑线）。
3. J2 的 1/2 脚接 12–24 V 直流电源，3/4 脚接 GND（摄像头与机械臂电源共地）。
4. 上电后等待约 1 分钟启动，然后点击**部署**。

### 部署完成

`rebot-teleop` 会运行 `armd`（`http://<摄像头>:8765`）、视觉服务以及 Wi-Fi 热点 `reCamera-Arm-Teleop`（默认密码 `12345678`，地址 `192.168.16.1`）。使能前机械臂不上力矩；在控制台启用其他应用会停止 `rebot-teleop`。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 提示 `"missing hardware capability: can"` | 检查 B4 CAN 底板是否插牢并重启摄像头 |
| 登录被拒绝 | 使用账号 `recamera` / `recamera`（早期固件为 `recamera.2`） |
| 用过控制台后机械臂页面打不开 | 启用了其他应用，在控制台的应用页面重新启用 `rebot-teleop` |

---

## 步骤 2: 打开控制台进行遥操与标定 {#open_cockpit type=web_dashboard required=true config=devices/cockpit.yaml}

### 操作检查清单

1. 在手机、平板或电脑打开 `http://<host>:8765`，确认实时视频、CAN 状态与 7 关节遥测正常刷新。
2. 按住力矩开关使能机械臂，测试虚拟摇杆点动或笛卡尔 XYZ/RPY 移动。
3. 将常用工位（如 `scan`、`bin_a`、`bin_b`）保存为命名位姿。
4. *(可选)* ArUco 手眼标定：桌面平放单个 5 cm `4x4_50` 标记 → 打开**手眼标定**选**相机在夹爪上** → 采集 5–9 个不同角度 → 点击**求解标定**并**导出配置**。

真机运动时请始终确保有人在物理断电开关旁监护。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 页面打不开 | 检查 IP（USB 为 `192.168.42.1`，热点为 `192.168.16.1`）并确认 `rebot-teleop` 运行中 |
| 没有画面 | 等待几秒让 `rebot-vision` 自动重启，或在控制台重启 `rebot-teleop` |
| 机械臂无法使能 | 检查 12–24 V 机械臂供电与 J2 CAN 接线 |
| 残差偏大 / 进入观察者模式 | 采集时保持标记与机械臂静止并剔除异常帧；观察者模式说明其他端持有控制权 |

---

## 步骤 3: 在这台电脑上安装 AI 智能体服务 {#install_mcp type=script required=false config=devices/mcp_server.yaml}

可选步骤：在本机安装 `rebot-mcp`（自动继承步骤 1 的设备 IP），让 AI 智能体通过 24 个 MCP 工具读取画面状态并控制机械臂。

- **连接客户端**：已安装 Claude Code 时会自动注册 `rebot`（可用 `claude mcp list` 查看）；Claude Desktop、Cursor 或 Windsurf 请复制步骤日志末尾的 `mcpServers` JSON 到配置文件后重启客户端。
- **测试指令**：*"先调用 `describe_safety` 和 `get_state`，拍一张照片告诉我摄像头看到了什么。"*
- **安全规则**：让 AI 移动机械臂前必须先在控制台释放控制权；已锁存的故障与急停只能人工在网页控制台解除。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| `LEASE_BUSY` | 在网页控制台释放控制权或关闭控制台标签页 |
| `ESTOP_ACTIVE` 或 `FAULT_ACTIVE` | 检查机械臂周围环境后，人工在网页控制台解除故障 |
| Claude Code 中看不到 `rebot` | 运行 `claude mcp list`，缺失时重新执行本步骤 |

---

## 套餐: 虚拟沙盒编排与策略训练（免硬件） {#virtual_training}

免硬件在浏览器 3D MuJoCo 沙盒中测试任务，并在本地准备与校验可用于套餐 3 的 ONNX 策略包。

**前提条件：** 支持 WebGL/WASM 的现代浏览器 · 本机可联网

## 步骤 1: 打开 reBot Cyclops 3D 虚拟沙盒 {#open_sandbox type=web_dashboard required=true config=devices/cyclops_sandbox.yaml}

1. 点击**在浏览器中打开**启动已配对的 3D 沙盒标签页（无需任何硬件）。
2. 在底部控制栏选择工具、视觉预设、运动参数与安全设置，点击**运行测试**观察物理仿真与诊断结果。
3. 保持该标签页开启，AI 助手（或 `solution-cli page`）即可与你同步调参、跑批量测试并导出配置。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 沙盒打开但未配对 | 从部署卡片重新打开，或运行 `solution-cli page pair` |
| 3D 画布空白或卡顿 | 开启浏览器硬件 WebGL 加速并关闭其他高负载 WebGL 标签页 |

---

## 步骤 2: 配置本地策略训练工作区 {#train_policy type=script required=true config=devices/policy_training.yaml}

1. 填写 `policy_id`（默认 `pcb_demo`）并部署，将在 `~/.sensecraft/rebot-policies/<policy_id>` 生成初始模板（已有的 `policy.json` 与 `model.onnx` 不会被覆盖）。
2. 将训练好的 `policy.json` + `model.onnx` 放入该目录（或用 `rebot-record` 采集示范数据；若只想先端到端跑通套餐 3，可直接使用初始模板）。
3. 进入套餐 3 前运行以下命令完成校验：
   ```bash
   rebot-scene validate ~/.sensecraft/rebot-policies/<policy_id>
   ```

### 故障排查

| 问题 | 解决方法 |
|---|---|
| `uv tool install` 失败 | 检查 GitHub/PyPI 网络连通性，或先手动安装 `uv` 后重试 |
| `rebot-scene validate` 失败 | 核对 `policy.json` 的输入输出名称与形状是否与 `model.onnx` 一致 |

---

## 套餐: 在 reBot armd 中加载与运行策略 {#armd_policy}

将校验通过的 ONNX 策略包（`policy.json` + `model.onnx`）上传至 `armd`，在浏览器 WASM 或本地仿真中预检，或在专人监护下驱动真机执行。

**前提条件：** `~/.sensecraft/rebot-policies/<policy_id>` 中的策略包（来自套餐 2）· reCamera 上已运行 `armd`，或本机已启动 `armd --follower sim`（`127.0.0.1`）

## 步骤 1: 在摄像头安装或确认 reBot 遥控 (armd) {#ensure_armd type=recamera_console_app required=false config=devices/rebot_teleop.yaml}

如果 reCamera 已安装 `rebot-teleop`，或本次连接本机 `armd --follower sim`（`127.0.0.1`），可直接跳过本步骤。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 目标是本地仿真器 | 跳过本步骤，并在步骤 2 将 `host` 设为 `127.0.0.1` |
| 缺少 `can0` 接口 | 检查 B4 CAN 底板是否插牢并重启摄像头 |

---

## 步骤 2: 上传并激活 ONNX 策略到 armd {#load_policy type=script required=true config=devices/armd_policy_loader.yaml}

填写 3 个参数（`host`：USB 为 `192.168.42.1`、热点为 `192.168.16.1`、本地仿真为 `127.0.0.1`；`policy_id`：默认 `pcb_demo`；`sandbox_mode`：`wasm` 浏览器预检、`sim` 实时仿真或 `upload_only`）并部署，自动上传并激活到 `armd`。

- **在本地仿真运行**（`armd --follower sim`）：
  ```bash
  rebot-policy --armd 127.0.0.1 --policy onnx:$HOME/.sensecraft/rebot-policies/<policy_id> --fps 30 --max-seconds 15
  ```
- **在真机运行**（先释放控制台控制权，并确认有人站在物理断电开关旁后再传入 `--i-am-at-the-arm`）：
  ```bash
  rebot-policy --armd <host> --policy onnx:$HOME/.sensecraft/rebot-policies/<policy_id> --fps 30 --max-seconds 15 --i-am-at-the-arm
  ```

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 8765 端口连接被拒绝 | 确认 reCamera 上的 `rebot-teleop`（或本地 `armd`）正在 `<host>:8765` 运行 |
| 上传时校验失败 | 执行 `rebot-scene validate ~/.sensecraft/rebot-policies/<policy_id>` 修正配置或模型 |
| `rebot-policy` 报 `LEASE_BUSY` | 先在网页控制台释放控制权或关闭控制台标签页 |

---

## 步骤 3: 打开策略控制台并监控安全状态 {#open_policy_cockpit type=web_dashboard required=true config=devices/cockpit_policy.yaml}

1. 打开 `http://<host>:8765/` 查看实时关节遥测、故障状态与软件急停按钮。
2. 若选择了 `wasm` 模式，打开 `http://<host>:8765/?sim=wasm` 运行浏览器仿真预检。
3. `rebot-policy` 运行期间控制台显示**观察者模式**属正常现象（策略端持有控制权），急停按钮仍可随时触发。真机运行时需确保物理断电开关触手可及。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| `?sim=wasm` 缺少运行资源 | 运行 `rebot-scene status --armd-url http://<host>:8765` 确认设备端 WASM 资源就绪 |
| 运行因 `FAULT_ACTIVE` 或 `FOLLOWING_ERROR` 停止 | 立即停止并检查周围干涉，然后在网页控制台解除故障 |
