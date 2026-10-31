# 部署指南：水产螯虾打斗与行为识别方案

在 Seeed reCamera 边缘相机上一键部署澳洲淡水龙虾实时打斗检测、公母性别鉴别与蜕壳残食风险预警。

---

## 套餐：reCamera Pro {#recamera_pro}

在 reCamera Pro（RV1126B 3 TOPS NPU）上运行完整的端侧 4 级漏斗视觉流水线，支持 8 帧时序拼接验证与公母性别多帧投票。

## 步骤 1：部署螯虾行为监测应用 {#deploy_recamera_pro_crayfish type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

安装部署器会自动检查 reCamera Pro 上的 App Center，自动下载并部署官方固件离线包（`crayfish-fight-v0.1.2-core.tar.gz`），配置并激活推理应用。

### 前置条件

1. 使用网线将 reCamera Pro 连接到路由器，或通过 USB-C 数据线直连工作站。
2. 确保设备 IP 可访问（默认 HTTPS 443 端口，自签证书在本地地址直接信任即可）。
3. 选择所需的靠近判定系数。

### 部署与配置

输入 reCamera Pro 的网络地址与 Web 登录凭据（默认用户为 `admin`）。安装程序将自动检查并下发应用包（`crayfish-fight-v0.1.2-core.tar.gz`），写入所选参数并激活推理服务。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 登录被拒绝或连接被拒 | 本步骤使用 HTTPS 443 端口的 Web 控制台，账号为 `admin`。请核对设备 IP 与 Web 控制台密码。 |
| 步骤结束后应用未激活 | 部署器最多等待 90 秒完成激活。请确认电脑能下载应用包（`crayfish-fight-v0.1.2-core.tar.gz`），然后重新运行本步骤。 |
| 浏览器提示证书警告 | 相机在 443 端口使用自签名证书，继续访问即可。 |

---

## 步骤 2：验证推流 {#verify_stream_pro type=video_stream required=true verify=true}

验证摄像头画面实时推流与螯虾行为识别状态。

### 部署完成

- 打开浏览器访问 `https://<camera-ip>/`。
- 确认实时检测框、靠近交互触发与行为分类事件正常输出。

---

## 套餐：reCamera 2002 {#recamera_2002}

超紧凑型 RISC-V 边缘相机，运行 SG2002 原生 TPU BF16 模型，实现端侧目标检测与打斗粗筛报警。

## 步骤 1：部署螯虾检测器 {#deploy_recamera_2002_crayfish type=recamera_cpp required=true config=devices/recamera_2002.yaml}

安装原生 TPU 硬件加速模型 `crayfish_det_cv181x_bf16.cvimodel` 与 `crayfish_behavior_cv181x_bf16.cvimodel`，并启动 C++ 推理报警守护进程。

### 前置条件

1. 通过 USB 将 reCamera 2002 接入电脑，默认 IP 为 `192.168.42.1`。
2. 默认 SSH 凭据：用户名 `recamera`，密码 `recamera`。
3. 摄像头互斥保护：系统会自动接管并让出正在占用摄像头的后台视频流。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| SSH 连接失败 | USB 连接使用 `192.168.42.1`；Wi-Fi 或有线网络使用路由器上显示的 IP。SSH 用户名为 `recamera`。 |
| 密码被拒绝 | 尝试表单预填的 `recamera.1` 或 `recamera`；早期固件使用 `recamera.2`。 |
| 部署后没有画面或检测结果 | 同一时间只运行一个摄像头管线。重启相机后重新运行本步骤。 |

### 部署目标 {#recamera_2002_device type=remote device_name="reCamera 2002" config=devices/recamera_2002.yaml default=true}

通过 SSH 远程部署到 reCamera 2002 设备。

---

## 步骤 2：验证推流 {#verify_stream_2002 type=video_stream required=true verify=true}

验证摄像头视频流推流与现场检测状态。

### 部署完成

- 打开浏览器访问 `http://<camera-ip>/`。
- 确认实时视频流正常播放，并叠加螯虾检测边框与靠近报警信息。
