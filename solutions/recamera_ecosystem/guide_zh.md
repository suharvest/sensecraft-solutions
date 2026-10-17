## 套餐: 目标检测与环境感知 {#object_detection}

体验边缘视觉的基础能力——通用目标检测（YOLO）与天气分类。通过实时 WebRTC 画面观察检测框与置信度变化，直观了解边缘端 INT8 模型的高效推理。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `yolo-detector`（80 类常见物体检测）或 `weather-classifier`（天气识别）。
- **体验任务：** 
  1. 将手机、水杯或手伸入镜头，观察 AI 在 50ms 内画出检测框和类别标签；
  2. 缓慢移动物体或遮挡一部分，观察置信度数字变化，理解视觉模型对遮挡的鲁棒性。

## 步骤 1: 升级 reCamera 控制台（SG2002） {#obj_deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.5 版控制台，已经是这个版本会自动跳过。若使用 reCamera Pro 请直接进入步骤 4。

### 前置条件

1. 用 USB 连接摄像头（地址 `192.168.42.1`），或让它和这台电脑处于同一网络（用路由器上显示的 IP）。
2. 用户名 `recamera`，默认密码 `recamera`（较早的机器是 `recamera.2`）。
3. 新设备需要先打开 SSH：USB 连接后等约两分钟，打开 `http://192.168.42.1/#/security` 登录，打开 SSH 开关。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连不上 | USB 用 `192.168.42.1`；走网络到路由器里查 IP |
| 密码不对 | 默认是 `recamera`，较早固件的机器是 `recamera.2` |
| 安装失败 | 重启摄像头后重新执行这一步 |
| Node-RED 用不了了 | 控制台接管了摄像头，可在控制台的系统设置里切回 |
| 想恢复原来的面板 | 按住 **User** 键再插电，红灯停止闪烁并常亮后松开，摄像头恢复出厂设置 |

---

## 步骤 2: 安装目标检测应用（SG2002） {#obj_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择 **通用目标检测 (yolo-detector)** 或 **天气识别 (weather-classifier)**，点**部署**。

### 前置条件

1. 这台电脑能访问互联网；摄像头不需要联网（由电脑代下载应用包与模型文件）。
2. 地址和密码沿用上一步。
3. 应用连同模型约几十至上百 MB，部署页会显示传输进度。

### 部署完成

摄像头正在运行目标检测应用。应用支持 ONVIF，NVR 或视频管理平台可自动发现并拉流。

### 故障排查

| 现象 | 处理 |
|------|------|
| 下拉框是空的或很短 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`，解决网络后点刷新 |
| 登录被拒 | 用摄像头的账号密码，默认 `recamera` / `recamera`（较早的机器是 `recamera.2`） |
| 控制台不回应 | 摄像头可能还在重启，等一分钟再部署 |
| 提示 busy | 控制台正在处理另一个应用操作，完成后再试 |
| 装了但起不来 | 在控制台「应用」页查看状态；文件缺失就重新部署这一步 |

---

## 步骤 3: 打开控制台查看（SG2002） {#obj_open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 1 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。
3. 尝试在镜头前晃动水杯或手机，观察置信度与 FPS。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

---

## 步骤 4: 检查并更新固件（reCamera Pro） {#obj_firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

仅 reCamera Pro 用户需要执行。摄像头页面上已有应用中心则直接跳过。

### 前置条件

1. 打开摄像头的页面，已有**应用中心**就跳过这一步。
2. 在设备管理中填入摄像头地址与 ADB 端口 5555，点**检查更新设备**。

---

## 步骤 5: 启动目标检测（reCamera Pro） {#obj_open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

打开 reCamera Pro 应用中心，安装并启动目标检测应用。

### 前置条件

1. 用摄像头控制面板的账号密码登录。
2. 在左侧打开**应用中心**，选择目标检测应用并点击**启动**。
3. 在左侧**实时预览**页查看画面和检测结果。

---

## 步骤 6: 部署 Home Assistant（可选） {#obj_deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。已有可跳过。

### 部署目标 {#obj_ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 部署目标 {#obj_ha_remote type=remote config=devices/homeassistant_deploy.yaml}

部署到局域网内的远程边缘主机（如 reComputer）。

---

## 步骤 7: 把摄像头接入 Home Assistant（可选） {#obj_connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 摄像头控制台「集成 → Home Assistant」填入 broker 地址与 1883 端口。

---

## 步骤 8: 在 Home Assistant 里查看结果（可选） {#obj_ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看目标检测的视频流与实体卡片。

---

## 套餐: 人体姿态与行为分析 {#human_behavior}

进阶体验人体拓扑关键点与时序动作识别。学习人脸关键点（Facemesh）、骨骼姿态、端侧隐私保护打码脱敏，以及基于时序状态机的动作分析。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `face-analysis`（人脸分析与打码脱敏）、`facemesh-reader`（困倦检测）、`fall-detection`（跌倒报警）、`fitness-trainer`（健身动作计数）。
- **体验任务：** 
  1. 对着镜头闭眼 3 秒或假装打哈欠，观察系统如何通过人脸 468 关键点触发困倦提醒；
  2. 开启隐私打码模式，观察 WebRTC 画面中人脸如何在端侧被自动高斯模糊，原始人脸不出设备。

## 步骤 1: 升级 reCamera 控制台（SG2002） {#human_deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.5 版控制台，已经是这个版本会自动跳过。若使用 reCamera Pro 请直接进入步骤 4。

### 前置条件

1. 用 USB 连接摄像头（地址 `192.168.42.1`），或通过局域网 IP 连接。
2. 用户名 `recamera`，默认密码 `recamera`。

---

## 步骤 2: 安装人体行为应用（SG2002） {#human_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择 **人脸分析 (face-analysis)**、**困倦检测 (facemesh-reader)**、**跌倒检测 (fall-detection)** 或 **健身教练 (fitness-trainer)** 并部署。

### 前置条件

1. 这台电脑能访问互联网，摄像头不需要联网。
2. 若体验人脸打码隐私保护，可在安装后进入控制台开启 Privacy Blur。

---

## 步骤 3: 打开控制台查看（SG2002） {#human_open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开控制台的调试面板，观察人脸特征点、姿态骨骼线或动作计数变化。

---

## 步骤 4: 检查并更新固件（reCamera Pro） {#human_firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

仅 reCamera Pro 用户需要执行。已有应用中心则直接跳过。

---

## 步骤 5: 启动人体行为应用（reCamera Pro） {#human_open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

打开 reCamera Pro 应用中心，启动对应的人体或人脸分析应用。

---

## 步骤 6: 部署 Home Assistant（可选） {#human_deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和 MQTT broker。已有可跳过。

### 部署目标 {#human_ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

本地部署 Home Assistant。

### 部署目标 {#human_ha_remote type=remote config=devices/homeassistant_deploy.yaml}

远程部署 Home Assistant。

---

## 步骤 7: 把摄像头接入 Home Assistant（可选） {#human_connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

配置 MQTT 转发，将人脸状态、困倦告警或跌倒事件自动接入 Home Assistant。

---

## 步骤 8: 在 Home Assistant 里查看结果（可选） {#human_ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在仪表盘添加 Picture glance 卡片，将跌倒告警或人脸属性实体叠在视频流上。

---

## 套餐: 文字与符号识别 {#text_reading}

学习端侧两阶段视觉流水线（文本定位 + OCR 字符识别）与二维码密集解码。了解复杂文字检测算法如何部署在低功耗边缘端。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `ppocr-reader`（中英文 OCR 文字识别）或 `qrcode-reader`（二维码识别）。
- **体验任务：** 
  1. 拿名片、工牌或外卖包装盒置于摄像头前 15~25 cm 处，观察印刷文字如何秒级被捕获并切片转为 JSON 字符串；
  2. 拿手机展示二维码给镜头，看画面中多个二维码同时解析。

## 步骤 1: 升级 reCamera 控制台（SG2002） {#text_deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.5 版控制台，已经是这个版本会自动跳过。若使用 reCamera Pro 请直接进入步骤 4。

### 前置条件

1. 用 USB 连接摄像头（地址 `192.168.42.1`）。
2. 用户名 `recamera`，默认密码 `recamera`。

---

## 步骤 2: 安装文字识读应用（SG2002） {#text_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择 **OCR 文字识别 (ppocr-reader)** 或 **二维码识别 (qrcode-reader)** 并部署。

### 前置条件

1. 电脑能访问互联网，摄像头不需要联网。
2. PP-OCR 模型内嵌中英文常用字库。

---

## 步骤 3: 打开控制台查看（SG2002） {#text_open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开控制台，把待识别的文本或条码置于镜头前，查看实时识别的文本行与置信度。

---

## 步骤 4: 检查并更新固件（reCamera Pro） {#text_firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

仅 reCamera Pro 用户需要执行。已有应用中心则直接跳过。

---

## 步骤 5: 启动文字识读应用（reCamera Pro） {#text_open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

打开 reCamera Pro 应用中心，启动 OCR 或二维码识别应用。

---

## 步骤 6: 部署 Home Assistant（可选） {#text_deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和 MQTT broker。已有可跳过。

### 部署目标 {#text_ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

本地部署 Home Assistant。

### 部署目标 {#text_ha_remote type=remote config=devices/homeassistant_deploy.yaml}

远程部署 Home Assistant。

---

## 步骤 7: 把摄像头接入 Home Assistant（可选） {#text_connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

配置 MQTT 转发，将识别出的文字文本或条码内容推送至 Home Assistant。

---

## 步骤 8: 在 Home Assistant 里查看结果（可选） {#text_ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在仪表盘添加文本传感器卡片，实时显示扫描读取到的文字内容。

---

## 套餐: 空间感知与客流分析 {#spatial_retail}

体验从 2D 图像脑补 3D 相对深度的单目深度估计，以及多目标追踪（ByteTrack）与虚拟绊线结合的实际商业客流统计应用。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `depth-estimation`（单目深度估计）或 `retail-vision`（零售客流统计）。
- **体验任务：** 
  1. 在单目深度估计模式下，将手部由远及近推向摄像头，观察画面像素如何从冷色（远）渐变为暖红色（近）；
  2. 在零售客流模式下，划定一条虚拟绊线，体验人员进出穿过时的自动累加计数与驻留状态捕获。

## 步骤 1: 升级 reCamera 控制台（SG2002） {#spatial_deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.5 版控制台，已经是这个版本会自动跳过。若使用 reCamera Pro 请直接进入步骤 4。

### 前置条件

1. 用 USB 连接摄像头（地址 `192.168.42.1`）。
2. 用户名 `recamera`，默认密码 `recamera`。

---

## 步骤 2: 安装空间与客流应用（SG2002） {#spatial_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择 **单目深度估计 (depth-estimation)** 或 **零售人流分析 (retail-vision)** 并部署。

### 前置条件

1. 电脑能访问互联网，摄像头不需要联网。
2. 零售客流应用包含目标跟踪与绊线计数逻辑。

---

## 步骤 3: 打开控制台查看（SG2002） {#spatial_open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开控制台，查看实时深度热力图（近红远蓝）或客流计数越线画面。

---

## 步骤 4: 检查并更新固件（reCamera Pro） {#spatial_firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

仅 reCamera Pro 用户需要执行。已有应用中心则直接跳过。

---

## 步骤 5: 启动空间与客流应用（reCamera Pro） {#spatial_open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

打开 reCamera Pro 应用中心，启动深度估计或客流分析应用。

---

## 步骤 6: 部署 Home Assistant（可选） {#spatial_deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和 MQTT broker。已有可跳过。

### 部署目标 {#spatial_ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

本地部署 Home Assistant。

### 部署目标 {#spatial_ha_remote type=remote config=devices/homeassistant_deploy.yaml}

远程部署 Home Assistant。

---

## 步骤 7: 把摄像头接入 Home Assistant（可选） {#spatial_connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

配置 MQTT 转发，将进出客流人数或方位接近度网格发布到 Home Assistant。

---

## 步骤 8: 在 Home Assistant 里查看结果（可选） {#spatial_ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在仪表盘添加计数实体与历史曲线卡片，实时呈现客流动线数据。
