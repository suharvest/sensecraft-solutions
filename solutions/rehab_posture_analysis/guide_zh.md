## 套餐：reCamera Pro {#recamera_pro}

在 reCamera Pro（RV1126B）上部署 33 关键点全身康复动作与姿态分析应用。
利用板载 RKNN INT8 NPU 硬件加速推理，并通过 Result Hub v2 WebSocket 实时输出 33 骨骼关键点矢量图元与 HUD 交互看板。

- **硬件：** reCamera Pro (RV1126B) 开机并通过网线或 USB 接入局域网。
- **模型：** 硬件加速 33 关键点 YOLO11n-Pose INT8 模型（`.rknn`）。
- **隐私保护：** 100% 纯端侧边缘运算。视频流不出摄像头本地，仅输出量化后的运动学指标与矢量骨骼。

## 步骤 1：部署康复姿态分析应用 {#deploy_rehab_pro type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

通过 reCamera Pro 原生应用中心（App Center）安装并激活康复动作分析应用。

### 准备工作

1. 使用网线将 reCamera Pro 连接到路由器，或通过 USB-C 数据线直连工作站。
2. 确保设备 IP 可访问（默认 HTTPS 443 端口，自签证书在本地地址直接信任即可）。
3. 选择初始评测的康复项目（深蹲/坐立、肩外展抬升、屈肘肌力或坐姿伸膝）。

### 部署与配置

输入 reCamera Pro 的网络地址与 Web 登录凭据（默认用户为 `admin`）。安装程序将自动检查并下发应用包（`rehab-posture-analysis-v0.1.0-core.tar.gz`），写入所选动作配置并激活推理服务。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 登录被拒绝或连接被拒 | 本步骤使用 HTTPS 443 端口的 Web 控制台，账号为 `admin`。请核对设备 IP 与 Web 控制台密码。 |
| 运行的康复动作不对 | 动作（深蹲、肩外展、肱二头肌弯举、坐姿伸膝）在本步骤中选择；选好目标动作后重新运行本步骤。 |
| 浏览器提示证书警告 | 相机在 443 端口使用自签名证书，继续访问即可。 |

---

## 步骤 2：查看康复分析看板 {#verify_rehab_pro type=web_dashboard required=true config=devices/verify_recamera_pro.yaml}

打开交互式 Result Hub v2 数据看板，实时查看骨架跟踪、关节活动度（ROM）与代偿动作告警。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 页面无法打开 | 访问 `https://<camera-ip>/#/apps/rehab-posture-analysis`，并确认步骤 1 已完成。接受自签名证书警告。 |
| 33 个关键点未全部跟踪 | 站立或就坐在距相机 2.0–3.5 m 处，使全身处于画面内。 |
| 没有出现代偿提示 | 确认步骤 1 中选择的动作与实际做的动作一致。 |

### 部署完成

- 在现代浏览器中打开 `https://<camera-ip>/#/apps/rehab-posture-analysis`。
- **患者就位验证：** 站在或坐在摄像头前方 2.0~3.5 米处。确认全身 33 处解剖骨架标志（肩、肘、腕、手掌、髋、膝、踝、足跟、足尖）均被彩色线条准确捕捉。
- **动作与计数验证：** 完成所选康复动作，观察次数计数（Reps）、关节角度仪表（ROM）以及动作质量实时评分（Score 0~100）。
- **代偿纠错验证：** 尝试做出轻微代偿动作（如深蹲时膝盖内扣或抬臂时耸肩），确认对应关节变红高亮闪烁，并显示纠错指导语。

---

## 套餐：reCamera 2002 {#recamera_2002}

在 reCamera 2002（SG2002 RISC-V 1GHz）上部署康复运动学分析服务。
在 CVI TPU 上运行 33 点 INT8 cvimodel，输出轻量级 Web 画布或视频裸流 OSD，不依赖 PC 主机算力。

- **硬件：** reCamera 2002（SG2002），通过 USB（默认 RNDIS `192.168.42.1`）或 Wi-Fi/以太网连接。
- **内存优化：** 针对 256MB DDR3 内存深度优化，零拷贝 TPU 推理。

## 步骤 1：部署 reCamera 2002 康复服务 {#deploy_rehab_2002 type=recamera_cpp required=true config=devices/recamera_2002.yaml}

下发 INT8 cvimodel 模型并启动康复姿态分析后台服务。

### 准备工作

1. 通过 USB 将 reCamera 2002 接入电脑，默认 IP 为 `192.168.42.1`。
2. 默认 SSH 凭据：用户名 `recamera`，密码 `recamera`。
3. 摄像头互斥保护：系统会自动接管并让出正在占用摄像头的后台视频流。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| SSH 连接失败 | USB 连接使用 `192.168.42.1`；Wi-Fi 或有线网络使用路由器上显示的 IP。SSH 用户名为 `recamera`。 |
| 密码被拒绝 | 尝试表单预填的 `recamera.1` 或 `recamera`。 |
| 部署后没有画面或指标 | 同一时间只运行一个摄像头管线。重启相机后重新运行本步骤。 |

### 部署目标 {#camera_2002 type=remote device_name="reCamera 2002" config=devices/recamera_2002.yaml default=true}

通过 SSH 远程部署到 reCamera 2002 设备。

---

## 步骤 2：验证视频流与 OSD 状态 {#verify_rehab_2002 type=web_dashboard required=true config=devices/verify_recamera_2002.yaml}

验证摄像头画面推流与康复运动学叠加层。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 页面无法打开 | 访问 `http://<camera-ip>/`（HTTP，不是 HTTPS），并确认步骤 1 已完成。 |
| 骨骼点或重复次数指标缺失 | 保持全身在画面内且光线充足。 |

### 部署完成

- 打开浏览器访问 `http://<camera-ip>/`。
- 确认视频画面正常流出，并实时叠加 33 骨骼关键点与次数/ROM 指标。
