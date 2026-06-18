## 套餐: 零售人流热力图 {#simple}

只用一台 reCamera，在网页上直接看零售场景的人流热力图——顾客在哪里停留、哪些区域被冷落，一目了然。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，识别并追踪画面中的人，生成人流热力图 |

**部署完成后你可以：**
- 看到叠加人流热力图的实时视频（热力图在网页端实时生成，按人体位置累积）
- 直观看出货架前、过道里哪些位置人多、哪些被冷落
- 隐私保护（人脸自动打码）

**前提条件：** 新设备需先开启 SSH——用 USB 连接电脑，等设备开机（约 2 分钟），访问 [192.168.42.1/#/security](http://192.168.42.1/#/security)，输入初始账号 `recamera` / `recamera`，打开 SSH 开关

## 步骤 1: 让摄像头能识别人 {#deploy_detector type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

给 reCamera 安装人员识别程序，让它能在画面中找到人。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入用户名 `recamera`，默认密码 `recamera`（若已修改请用新密码）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 密码错误 | 初始密码 `recamera`，若改过请用新密码 |
| 安装失败 | 重启摄像头再试一次 |

---

## 步骤 2: 查看实时人流热力图 {#preview type=preview required=false config=devices/preview.yaml}

点击 **连接** 查看带人流热力图叠加的实时视频。

**提示：** 热力图按行人位置随时间累积，等几分钟人流分布会更清晰。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 黑屏 | 等 10 秒让视频流加载；检查摄像头 IP 是否正确 |
| 没有热力图叠加 | 等几分钟让数据积累；确认步骤 1 已完成 |

### 部署完成

摄像头已就绪！点击上方 **连接** 查看实时人流热力图。

热力图按人体位置随时间累积——顾客停留越久、经过越多的区域会越亮，可用于识别零售门店中的"热区"和"冷区"。

---

## 套餐: Home Assistant 集成 {#ha_integration}

将 reCamera 接入 Home Assistant，统一管理智能家居设备。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，支持 YOLO 识别 + RTSP 视频流 |
| 电脑 或 reComputer R1100 | 运行 Home Assistant |

**部署完成后你可以：**
- 在 HA 面板中查看实时 RTSP 视频流
- 看到 AI 识别计数传感器，包含各类别明细（人、车等）
- 在 reCamera 上使用 FlowFuse Dashboard 进行本地调试

**前提条件：** Docker 已安装 · 所有设备在同一局域网

---

## 步骤 1: 部署 Home Assistant {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant。如果你已有 HA，可以跳过这一步。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

### 接线

1. 确保 Docker Desktop 已安装并运行
2. 至少 2GB 可用磁盘空间

### 部署完成

1. 在浏览器打开 **http://localhost:8123**
2. 按照引导向导创建管理员账号
3. 请记住用户名和密码——步骤 3 需要用到

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 端口 8123 被占用 | 关闭占用 8123 端口的程序，或修改 docker-compose.yml 中的端口 |
| Docker 启动不了 | 打开 Docker Desktop 应用 |
| 容器反复重启 | 确保电脑有至少 2GB 可用内存 |

### 部署目标 {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

### 接线

1. 将目标设备连接到网络
2. 在下方输入 IP 地址、用户名和密码

### 部署完成

1. 在浏览器打开 **http://\<设备IP\>:8123**
2. 按照引导向导创建管理员账号
3. 请记住用户名和密码——步骤 3 需要用到

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping 测试 |
| SSH 认证失败 | 确认用户名密码正确 |

---

## 步骤 2: 部署 AI 识别流程 {#deploy_flow type=recamera_nodered required=true config=devices/recamera.yaml}

给 reCamera 安装 YOLO 识别 + RTSP 视频流程序。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入用户名 `recamera`，默认密码 `recamera`（若已修改请用新密码）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 密码错误 | 初始密码 `recamera`，若改过请用新密码 |
| 安装失败 | 重启摄像头再试一次 |

---

## 步骤 3: 在 Home Assistant 中添加 reCamera {#configure_ha type=ha_integration required=true config=devices/homeassistant_existing.yaml}

安装 reCamera 集成并连接到 Home Assistant。

### 接线

1. 输入 Home Assistant 的 **IP 地址**（如 `192.168.1.100`）
2. 输入 HA 设置时创建的**登录用户名和密码**
3. 输入 **reCamera 的 IP 地址** — USB 连接用 `192.168.42.1`，或路由器中查到的 WiFi IP
4. **HA OS 用户**：SSH 相关字段留空 — 系统会自动安装配置 SSH
5. **Docker HA 用户**：还需要填写**宿主机**的 SSH 用户名和密码（不是 HA 的登录密码）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| HA 登录失败 | 这里填的是 HA 网页登录的用户名密码，不是 SSH 的。请确认是否正确 |
| 重启时间很长 | HA OS 会重启整个系统，可能需要 30-90 秒，请耐心等待 |
| SSH 插件安装失败 | HA OS 需要联网才能下载 SSH 插件，检查网络连接 |
| 文件复制失败 | HA OS 检查磁盘空间；Docker 确认 SSH 凭据是**宿主机**的 |
| 添加后显示 `setup_retry` | HA 无法访问 reCamera — 确保两者在同一局域网 |
| 摄像头缩略图空白，但直播正常 | 已知问题：ffmpeg 截图可能超时，面板中的实时画面不受影响 |
| 传感器显示 0 | 摄像头视野内没有可识别物体时属正常；可访问 http://\<reCamera IP\>:1880/data 验证 |

## 步骤 4: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Home Assistant 面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

### 部署完成

reCamera 已成功接入 Home Assistant！

#### 快速验证

1. 打开 **http://\<服务器IP\>:8123**
2. 进入 **设置 → 设备与服务** — 应该能看到 **reCamera (你的IP)** 设备
3. 点击进入设备查看两个实体
4. 在面板中添加 **图片实体** 卡片来显示摄像头画面

#### 访问地址

- **Home Assistant**：http://\<服务器IP\>:8123 — 统一智能家居面板
- **FlowFuse Dashboard**：http://\<reCamera IP\>:1880/dashboard — reCamera 本地调试界面
- **识别数据 API**：http://\<reCamera IP\>:1880/data — 原始识别 JSON 数据

#### 后续玩法

- 用识别传感器创建**自动化**（例如检测到人时自动开灯）
- 在面板中用 **图片实体** 或 **图片概览** 卡片添加摄像头画面
- 设置**手机通知**，检测到特定物体时推送提醒

**遇到问题？**
- 看不到画面？检查 reCamera IP，确认步骤 2 已完成
- 没有识别数据？确保视野内有物体；访问 http://\<reCamera IP\>:1880 检查 Node-RED

---

## 套餐: OCR 文字识别 {#ocr_reader}

把 reCamera 对准任何文字——标牌、标签、仪表显示屏——识别出的字符实时显示在画面上。全部在摄像头上处理，不需要联网。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，识别画面中的文字 |

**部署完成后你可以：**
- 实时看到画面中被识别出的文字
- 支持印刷文字、标牌、标签、电子显示屏
- 全部在设备上处理——不需要联网，不需要额外设备

**前提条件：** 新设备需先开启 SSH——用 USB 连接电脑，等设备开机（约 2 分钟），访问 [192.168.42.1/#/security](http://192.168.42.1/#/security)，输入初始账号 `recamera` / `recamera`，打开 SSH 开关

## 步骤 1: 安装文字识别程序 {#deploy_ppocr type=recamera_cpp required=true config=devices/recamera_ppocr.yaml}

给 reCamera 安装文字识别程序，让它能读取画面中的文字。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入用户名 `recamera`，默认密码 `recamera`（若已修改请用新密码）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 密码错误 | 初始密码 `recamera`，若改过请用新密码 |
| 安装失败 | 重启摄像头再试一次 |

---

## 步骤 2: 查看 OCR 文字叠加 {#preview_ocr type=preview required=false config=devices/preview_ocr.yaml}

点击 **连接** 查看带文字识别叠加的实时视频。

**提示：** 将摄像头对准文字——标牌、标签、屏幕——效果最佳。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 黑屏 | 等 10 秒让视频流加载；检查摄像头 IP 是否正确 |
| 没有识别到文字 | 确保文字清晰可见且光线充足；确认步骤 1 已完成 |

### 部署完成

摄像头已就绪！点击上方 **连接** 查看实时 OCR 文字叠加。

将摄像头对准印刷文字——识别出的字符会显示在每个检测区域上方。

---

## 套餐: 人脸分析 {#face_analysis}

把 reCamera 对准人——实时检测人脸并分析年龄、性别、表情。全部在摄像头上处理，不需要联网。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，分析画面中的人脸 |

**部署完成后你可以：**
- 实时看到人脸框和分析标签
- 每张检测到的人脸都显示年龄、性别和表情
- 全部在设备上处理——不需要联网，不需要额外设备

**前提条件：** 新设备需先开启 SSH——用 USB 连接电脑，等设备开机（约 2 分钟），访问 [192.168.42.1/#/security](http://192.168.42.1/#/security)，输入初始账号 `recamera` / `recamera`，打开 SSH 开关

## 步骤 1: 安装人脸分析程序 {#deploy_face_analysis type=recamera_cpp required=true config=devices/recamera_face_analysis.yaml}

给 reCamera 安装人脸分析程序，让它能检测人脸并分析年龄、性别和表情。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入用户名 `recamera`，默认密码 `recamera`（若已修改请用新密码）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 密码错误 | 初始密码 `recamera`，若改过请用新密码 |
| 安装失败 | 重启摄像头再试一次 |

---

## 步骤 2: 查看人脸分析结果 {#preview_face_analysis type=preview required=false config=devices/preview_face_analysis.yaml}

点击 **连接** 查看带人脸分析叠加的实时视频。

**提示：** 将摄像头对准人——每张检测到的人脸都会显示年龄、性别和表情。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 黑屏 | 等 10 秒让视频流加载；检查摄像头 IP 是否正确 |
| 没有检测到人脸 | 确保人脸清晰可见且光线充足；确认步骤 1 已完成 |

### 部署完成

摄像头已就绪！点击上方 **连接** 查看实时人脸分析叠加。

每张检测到的人脸都会显示年龄、性别和表情——全部在设备上实时分析。

---

## 套餐: 困倦检测 {#facemesh_drowsiness}

把 reCamera 对准驾驶员——实时监测闭眼时长、哈欠频率和 PERCLOS 困倦指数。全部在摄像头上处理，不需要联网。

| 设备 | 用途 |
|------|------|
| reCamera | AI 摄像头，监测驾驶员警觉状态 |

**部署完成后你可以：**
- 实时看到人脸框和困倦检测指标
- 实时追踪 EAR（眼宽比）和 MAR（嘴宽比）
- PERCLOS 困倦评分和持续闭眼时长监控
- 哈欠检测，含 5 分钟频率统计
- 颜色编码的困倦状态：正常、疲劳、困倦、危险
- 全部在设备上处理——不需要联网，不需要额外设备

**前提条件：** 新设备需先开启 SSH——用 USB 连接电脑，等设备开机（约 2 分钟），访问 [192.168.42.1/#/security](http://192.168.42.1/#/security)，输入初始账号 `recamera` / `recamera`，打开 SSH 开关

## 步骤 1: 安装困倦检测程序 {#deploy_facemesh_drowsiness type=recamera_cpp required=true config=devices/recamera_facemesh_drowsiness.yaml}

给 reCamera 安装 FaceMesh 困倦检测程序，让它能追踪眼睛和嘴部的运动。

### 接线

1. USB 连接：IP 地址 `192.168.42.1`，即插即用
2. 网线/WiFi：在路由器管理页面查找 reCamera 的 IP
3. 输入用户名 `recamera`，默认密码 `recamera`（若已修改请用新密码）

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 连不上 | USB 连接用 `192.168.42.1`；网络连接去路由器查 IP |
| 密码错误 | 初始密码 `recamera`，若改过请用新密码 |
| 安装失败 | 重启摄像头再试一次 |

---

## 步骤 2: 查看困倦检测结果 {#preview_facemesh_drowsiness type=preview required=false config=devices/preview_facemesh_drowsiness.yaml}

点击 **连接** 查看带困倦检测叠加的实时视频。

**提示：** 将摄像头对准人脸——每张检测到的人脸都会显示 EAR、MAR 和困倦状态。

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 黑屏 | 等 10 秒让视频流加载；检查摄像头 IP 是否正确 |
| 没有检测到人脸 | 确保人脸清晰可见且光线充足；确认步骤 1 已完成 |

### 部署完成

摄像头已就绪！点击上方 **连接** 查看实时困倦检测叠加。

每张检测到的人脸都会显示 EAR/MAR 值和颜色编码的困倦状态——全部在设备上实时分析。
