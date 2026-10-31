## 套餐: 目标检测与环境感知 {#object_detection}

体验边缘视觉的基础能力——通用目标检测（YOLO）与天气分类。通过实时 WebRTC 画面观察检测框与置信度变化，直观了解边缘端 INT8 模型的高效推理。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `yolo-detector`（80 类常见物体检测）或 `weather-classifier`（天气识别）。
- **体验任务：** 
  1. 将手机、水杯或手伸入镜头，观察 AI 在 50ms 内画出检测框和类别标签；
  2. 缓慢移动物体或遮挡一部分，观察置信度数字变化，理解视觉模型对遮挡的鲁棒性。

## 步骤 1: 升级 reCamera 控制台 (SG2002) {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.6 版本的控制台。如果已是 0.5.6 版本将自动跳过。若使用 reCamera Pro，请直接跳到步骤 2。

### 前置条件

1. 通过 USB（地址 `192.168.42.1`）连接摄像头，或将其置于同一局域网下。
2. 用户名为 `recamera`，默认密码为 `recamera`（旧固件可能为 `recamera.2`）。
3. 全新出厂设备请先访问 `http://192.168.42.1/#/security` 开启 SSH。

### 故障排查

| 现象 | 解决方法 |
|---|---|
| 连接失败 | 通过 USB 连接使用 `192.168.42.1`；局域网连接请查看路由器 DHCP 列表 |
| 密码错误 | 默认密码为 `recamera`（旧固件可能为 `recamera.2`） |
| 安装失败 | 重启摄像头后重新运行本步骤 |
| 无法使用 Node-RED | 控制台接管了摄像头；可在控制台系统设置中切换回 Node-RED |
| 恢复出厂设置 | 通电开机时按住 **User** 键，直到红色 LED 常亮 |

---

## 步骤 2: 安装目标检测应用 {#obj_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择要运行的应用并部署到摄像头。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 无法连接相机 | USB 连接使用 `192.168.42.1`；否则使用路由器上显示的 IP。reCamera Pro 通过 HTTPS 443 端口访问。 |
| 登录被拒绝 | reCamera（SG2002）：`recamera` / `recamera`（早期固件为 `recamera.2`）。reCamera Pro：Web 控制台账号，默认用户 `admin`。 |
| 部署后应用未启动 | 在控制台 Apps 页面（SG2002）或 App Center（Pro）查看应用状态；文件缺失时重新部署。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/recamera_console_app.yaml default=true}

在应用下拉框中选择 **通用目标检测 (yolo-detector)** 或 **天气识别 (weather-classifier)**，点击**部署**。

### 前置条件

1. 这台电脑能访问互联网；摄像头不需要联网（由电脑代下载应用包与模型文件）。
2. 用 USB 连接摄像头（地址 `192.168.42.1`），或让它和电脑处于同一局域网（使用路由器上分配的 IP）。
3. 摄像头账号密码默认 `recamera` / `recamera`（较早固件为 `recamera.2`）。
4. 控制台版本需为 0.5.5 或更高；若为旧版本请在控制台系统设置中升级。

### 部署完成

摄像头正在运行目标检测应用。应用支持 ONVIF 与 RTSP，视频管理平台可自动发现并拉流。

### 故障排查

| 现象 | 处理 |
|------|------|
| 下拉框是空的或很短 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`，解决网络后点刷新 |
| 登录被拒 | 用摄像头的账号密码，默认 `recamera` / `recamera`（较早的机器是 `recamera.2`） |
| 控制台不回应 | 摄像头可能还在重启，等一分钟再部署 |
| 提示 busy | 控制台正在处理另一个应用操作，完成后再试 |
| 装了但起不来 | 在控制台「应用」页查看状态；文件缺失就重新部署这一步 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_yolo.yaml}

在 reCamera Pro 上自动激活并配置通用目标检测应用 (`yolo-detector`)。

### 前置条件

1. 摄像头与这台电脑处于同一局域网或通过 USB 连接（默认 `192.168.42.1`）。
2. 填写摄像头 Web 控制面板的管理员账号与密码（默认 `admin`）。
3. 摄像头应用中心已下载该应用。若尚未安装，先在控制面板的「应用中心」中安装。

### 部署完成

应用已在 reCamera Pro 上成功激活并运行，开始进行实时目标检测。

### 故障排查

| 现象 | 处理 |
|------|------|
| 登录失败 | 确认使用 Web 控制面板账号密码（非 SSH 密码），默认用户为 admin |
| 应用未安装 | 若提示未安装，先在摄像头应用中心目录中点击安装该应用 |
| 连接超时 | 确认摄像头 IP 正确，且 HTTPS (443) 端口可达 |

---

## 步骤 3: 打开控制台查看 {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制面板，查看实时推理画面与检测结果。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 页面无法打开 | SG2002 控制台：`http://<camera-ip>/`。reCamera Pro：443 端口的 HTTPS 控制面板，出现自签名证书警告属正常现象。 |
| 实时画面为黑屏或无法加载 | 当前没有运行中的应用。返回步骤 2 部署或激活应用。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/console_dashboard.yaml default=true}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 2 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_apps.yaml}

打开 reCamera Pro 控制面板，在实时预览中查看推理结果与流媒体画面。

### 前置条件

1. 用摄像头控制面板的账号密码登录（默认 admin）。
2. 在左侧打开**实时预览**页查看实时画面和 AI 检测结果。

### 部署完成

控制面板已打开，可以在实时预览中查看检测框与置信度。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 画面未加载 | 确认上一步的应用已成功激活运行 |

---

## 步骤 4: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 或 1883 端口被占用 | 停掉现有的 Home Assistant 或 Mosquitto，或跳过这一步直接用现有的 |
| Docker 起不来 | 打开 Docker Desktop 应用 |
| 容器反复重启 | 确认至少有 2 GB 可用内存 |

### 部署目标 {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

部署到局域网内的远程边缘主机（如 reComputer）。

### 前置条件

1. 目标设备 SSH 可达，已安装并启动 Docker。
2. 在下面填入它的 IP 地址、用户名和密码。

### 部署完成

1. 打开 **http://<设备 IP>:8123**，按向导创建管理员账号。
2. MQTT broker 在同一台设备的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 5 步直接填它 |

---

## 步骤 5: 在 Home Assistant 里查看结果（可选） {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看摄像头的实时画面与检测实体。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 检测实体缺失或不可用 | 相机与 Home Assistant 必须使用步骤 4 中的同一个 MQTT broker（端口 1883），且相机上的应用处于运行状态。 |
| 卡片中没有视频 | SG2002 在 Picture glance 卡片中使用控制台视频。reCamera Pro 需在 Stream Settings 中启用 RTSP，并以 TCP 传输方式将该 URL 添加为 Generic Camera。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/ha_dashboard.yaml default=true}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现，再添加视频流卡片。

### 前置条件

1. **在 Home Assistant 中添加 MQTT 集成**：进入「设置 → 设备与服务 → 添加集成」，选择 MQTT。Broker 填第 4 步部署的那台机器的地址，端口 1883，用户名密码留空。如果已经配好 MQTT 则跳过。
2. **在摄像头上填写 broker 地址**：在摄像头控制台里打开「集成 → Home Assistant」，填入第 4 步的 MQTT Broker 地址和端口 1883，先点「测试连接」，再点「保存」。
3. **查看实体**：在 Home Assistant「设置 → 设备与服务 → MQTT」找到摄像头实体。
4. **添加卡片**：在仪表盘添加 Picture glance 卡片，将检测实体叠加在实时画面上。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体会自动更新。

### 故障排查

| 现象 | 处理 |
|------|------|
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 实体出现了但一直不可用 | 确认控制台里应用正在运行 |
| 卡片上有画面，但没有检测图标 | 确认摄像头控制台的 Home Assistant 集成配置无误，且实体状态正常 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/ha_dashboard_pro.yaml}

把 reCamera Pro 的 RTSP 视频流与 MQTT 检测实体添加到 Home Assistant 仪表盘卡片。

### 前置条件

1. **在 Home Assistant 中添加 MQTT 集成**：进入「设置 → 设备与服务 → 添加集成」，选择 MQTT。Broker 填第 4 步部署的那台机器的地址，端口 1883，用户名密码留空。如果已经配好 MQTT 则跳过。
2. **配置摄像头 MQTT**：如果部署时已填写 MQTT 服务器地址，设备会自动连接。否则在摄像头应用中心点当前应用的「配置」，在「结果输出」里勾选 MQTT，输出模式选择 Home Assistant，并填入 broker 地址和端口 1883。
3. **查看实体**：「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，确认检测实体存在。
4. **打开 RTSP**：在摄像头控制面板「画面设置 → 推流设置」开启 RTSP，复制视频流地址。
5. **添加视频**：在 Home Assistant「设置 → 设备与服务 → 添加集成」选 Generic Camera，粘贴 RTSP 地址（传输协议选 TCP）。
6. **添加卡片**：在仪表盘添加 Picture glance 卡片，Camera Entity 选 Generic Camera，Entities 添加检测实体。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP |
| 实体显示 unknown | 摄像头前画面发生变化后才会有数据上报 |

---

## 套餐: 人体姿态与行为分析 {#human_behavior}

进阶体验人体拓扑关键点与时序动作识别。学习人脸关键点（Facemesh）、骨骼姿态、端侧隐私保护打码脱敏，以及基于时序状态机的动作分析。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `face-analysis`（人脸分析与打码脱敏）、`facemesh-reader`（困倦检测）、`fall-detection`（跌倒报警）、`fitness-trainer`（健身动作计数）。
- **体验任务：** 
  1. 对着镜头闭眼 3 秒或假装打哈欠，观察系统如何通过人脸 468 关键点触发困倦提醒；
  2. 开启隐私打码模式，观察 WebRTC 画面中人脸如何在端侧被自动高斯模糊，原始人脸不出设备。

## 步骤 1: 升级 reCamera 控制台 (SG2002) {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.6 版本的控制台。如果已是 0.5.6 版本将自动跳过。若使用 reCamera Pro，请直接跳到步骤 2。

### 前置条件

1. 通过 USB（地址 `192.168.42.1`）连接摄像头，或将其置于同一局域网下。
2. 用户名为 `recamera`，默认密码为 `recamera`（旧固件可能为 `recamera.2`）。
3. 全新出厂设备请先访问 `http://192.168.42.1/#/security` 开启 SSH。

### 故障排查

| 现象 | 解决方法 |
|---|---|
| 连接失败 | 通过 USB 连接使用 `192.168.42.1`；局域网连接请查看路由器 DHCP 列表 |
| 密码错误 | 默认密码为 `recamera`（旧固件可能为 `recamera.2`） |
| 安装失败 | 重启摄像头后重新运行本步骤 |
| 无法使用 Node-RED | 控制台接管了摄像头；可在控制台系统设置中切换回 Node-RED |
| 恢复出厂设置 | 通电开机时按住 **User** 键，直到红色 LED 常亮 |

---

## 步骤 2: 安装人体行为应用 {#human_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择要运行的人体行为分析应用并部署到摄像头。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 无法连接相机 | USB 连接使用 `192.168.42.1`；否则使用路由器上显示的 IP。reCamera Pro 通过 HTTPS 443 端口访问。 |
| 登录被拒绝 | reCamera（SG2002）：`recamera` / `recamera`（早期固件为 `recamera.2`）。reCamera Pro：Web 控制台账号，默认用户 `admin`。 |
| 部署后应用未启动 | 在控制台 Apps 页面（SG2002）或 App Center（Pro）查看应用状态；文件缺失时重新部署。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/recamera_console_app.yaml default=true}

在应用下拉框中选择 **人脸分析 (face-analysis)**、**跌倒检测 (fall-detection)**、**困倦检测 (facemesh-reader)** 或 **健身教练 (fitness-trainer)**，点击**部署**。

### 前置条件

1. 这台电脑能访问互联网；摄像头不需要联网（由电脑代下载应用包与模型文件）。
2. 用 USB 连接摄像头（地址 `192.168.42.1`），或让它和电脑处于同一局域网。
3. 摄像头账号密码默认 `recamera` / `recamera`（较早固件为 `recamera.2`）。
4. 控制台版本需为 0.5.5 或更高。

### 部署完成

摄像头正在运行人体行为分析应用。

### 故障排查

| 现象 | 处理 |
|------|------|
| 下拉框是空的或很短 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`，解决网络后点刷新 |
| 登录被拒 | 用摄像头的账号密码，默认 `recamera` / `recamera`（较早的机器是 `recamera.2`） |
| 控制台不回应 | 摄像头可能还在重启，等一分钟再部署 |
| 提示 busy | 控制台正在处理另一个应用操作，完成后再试 |
| 装了但起不来 | 在控制台「应用」页查看状态；文件缺失就重新部署这一步 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_fall.yaml}

在 reCamera Pro 上自动激活并配置跌倒检测应用 (`fall-detection`)。

### 前置条件

1. 摄像头与这台电脑处于同一局域网或通过 USB 连接（默认 `192.168.42.1`）。
2. 填写摄像头 Web 控制面板的管理员账号与密码（默认 `admin`）。
3. 摄像头应用中心已下载该应用。若尚未安装，先在控制面板的「应用中心」中安装。

### 部署完成

跌倒检测应用已在 reCamera Pro 上成功激活并运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| 登录失败 | 确认使用 Web 控制面板账号密码（非 SSH 密码），默认用户为 admin |
| 应用未安装 | 若提示未安装，先在摄像头应用中心目录中点击安装该应用 |
| 连接超时 | 确认摄像头 IP 正确，且 HTTPS (443) 端口可达 |

---

## 步骤 3: 打开控制台查看 {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制面板，查看实时推理画面与检测结果。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 页面无法打开 | SG2002 控制台：`http://<camera-ip>/`。reCamera Pro：443 端口的 HTTPS 控制面板，出现自签名证书警告属正常现象。 |
| 实时画面为黑屏或无法加载 | 当前没有运行中的应用。返回步骤 2 部署或激活应用。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/console_dashboard.yaml default=true}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 2 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_apps.yaml}

打开 reCamera Pro 控制面板，在实时预览中查看推理结果与流媒体画面。

### 前置条件

1. 用摄像头控制面板的账号密码登录（默认 admin）。
2. 在左侧打开**实时预览**页查看实时画面和 AI 检测结果。

### 部署完成

控制面板已打开，可以在实时预览中查看检测框与置信度。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 画面未加载 | 确认上一步的应用已成功激活运行 |

---

## 步骤 4: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 或 1883 端口被占用 | 停掉现有的 Home Assistant 或 Mosquitto，或跳过这一步直接用现有的 |
| Docker 起不来 | 打开 Docker Desktop 应用 |
| 容器反复重启 | 确认至少有 2 GB 可用内存 |

### 部署目标 {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

部署到局域网内的远程边缘主机（如 reComputer）。

### 前置条件

1. 目标设备 SSH 可达，已安装并启动 Docker。
2. 在下面填入它的 IP 地址、用户名和密码。

### 部署完成

1. 打开 **http://<设备 IP>:8123**，按向导创建管理员账号。
2. MQTT broker 在同一台设备的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 5 步直接填它 |

---

## 步骤 5: 在 Home Assistant 里查看结果（可选） {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看摄像头的实时画面与检测实体。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 检测实体缺失或不可用 | 相机与 Home Assistant 必须使用步骤 4 中的同一个 MQTT broker（端口 1883），且相机上的应用处于运行状态。 |
| 卡片中没有视频 | SG2002 在 Picture glance 卡片中使用控制台视频。reCamera Pro 需在 Stream Settings 中启用 RTSP，并以 TCP 传输方式将该 URL 添加为 Generic Camera。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/ha_dashboard.yaml default=true}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现，再添加视频流卡片。

### 前置条件

1. **在 Home Assistant 中添加 MQTT 集成**：进入「设置 → 设备与服务 → 添加集成」，选择 MQTT。Broker 填第 4 步部署的那台机器的地址，端口 1883，用户名密码留空。如果已经配好 MQTT 则跳过。
2. **在摄像头上填写 broker 地址**：在摄像头控制台里打开「集成 → Home Assistant」，填入第 4 步的 MQTT Broker 地址和端口 1883，先点「测试连接」，再点「保存」。
3. **查看实体**：在 Home Assistant「设置 → 设备与服务 → MQTT」找到摄像头实体。
4. **添加卡片**：在仪表盘添加 Picture glance 卡片，将检测实体叠加在实时画面上。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体会自动更新。

### 故障排查

| 现象 | 处理 |
|------|------|
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 实体出现了但一直不可用 | 确认控制台里应用正在运行 |
| 卡片上有画面，但没有检测图标 | 确认摄像头控制台的 Home Assistant 集成配置无误，且实体状态正常 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/ha_dashboard_pro.yaml}

把 reCamera Pro 的 RTSP 视频流与 MQTT 检测实体添加到 Home Assistant 仪表盘卡片。

### 前置条件

1. **在 Home Assistant 中添加 MQTT 集成**：进入「设置 → 设备与服务 → 添加集成」，选择 MQTT。Broker 填第 4 步部署的那台机器的地址，端口 1883，用户名密码留空。如果已经配好 MQTT 则跳过。
2. **配置摄像头 MQTT**：如果部署时已填写 MQTT 服务器地址，设备会自动连接。否则在摄像头应用中心点当前应用的「配置」，在「结果输出」里勾选 MQTT，输出模式选择 Home Assistant，并填入 broker 地址和端口 1883。
3. **查看实体**：「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，确认检测实体存在。
4. **打开 RTSP**：在摄像头控制面板「画面设置 → 推流设置」开启 RTSP，复制视频流地址。
5. **添加视频**：在 Home Assistant「设置 → 设备与服务 → 添加集成」选 Generic Camera，粘贴 RTSP 地址（传输协议选 TCP）。
6. **添加卡片**：在仪表盘添加 Picture glance 卡片，Camera Entity 选 Generic Camera，Entities 添加检测实体。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP |
| 实体显示 unknown | 摄像头前画面发生变化后才会有数据上报 |

---

## 套餐: 文字与符号识别 {#text_reading}

两阶段视觉流水线。通过 PP-OCR 实时识别包装、标签和屏幕上的中英文字符，或一次性解析画面的所有二维码。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `ppocr-reader`（中英文字符识别）或 `qrcode-reader`（二维码识别）。
- **体验任务：** 
  1. 将带有中英文字符的书本或包装纸放到镜头前，观察端侧 OCR 如何快速定位并识别文本内容；
  2. 测试不同光照与倾斜角度下的字符识别准确度。

## 步骤 1: 升级 reCamera 控制台 (SG2002) {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.6 版本的控制台。如果已是 0.5.6 版本将自动跳过。若使用 reCamera Pro，请直接跳到步骤 2。

### 前置条件

1. 通过 USB（地址 `192.168.42.1`）连接摄像头，或将其置于同一局域网下。
2. 用户名为 `recamera`，默认密码为 `recamera`（旧固件可能为 `recamera.2`）。
3. 全新出厂设备请先访问 `http://192.168.42.1/#/security` 开启 SSH。

### 故障排查

| 现象 | 解决方法 |
|---|---|
| 连接失败 | 通过 USB 连接使用 `192.168.42.1`；局域网连接请查看路由器 DHCP 列表 |
| 密码错误 | 默认密码为 `recamera`（旧固件可能为 `recamera.2`） |
| 安装失败 | 重启摄像头后重新运行本步骤 |
| 无法使用 Node-RED | 控制台接管了摄像头；可在控制台系统设置中切换回 Node-RED |
| 恢复出厂设置 | 通电开机时按住 **User** 键，直到红色 LED 常亮 |

---

## 步骤 2: 安装文字识读应用 {#text_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择要运行的文字或符号识别应用并部署到摄像头。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 无法连接相机 | USB 连接使用 `192.168.42.1`；否则使用路由器上显示的 IP。reCamera Pro 通过 HTTPS 443 端口访问。 |
| 登录被拒绝 | reCamera（SG2002）：`recamera` / `recamera`（早期固件为 `recamera.2`）。reCamera Pro：Web 控制台账号，默认用户 `admin`。 |
| 部署后应用未启动 | 在控制台 Apps 页面（SG2002）或 App Center（Pro）查看应用状态；文件缺失时重新部署。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/recamera_console_app.yaml default=true}

在应用下拉框中选择 **OCR 文字识别 (ppocr-reader)** 或 **二维码识别 (qrcode-reader)**，点击**部署**。

### 前置条件

1. 这台电脑能访问互联网；摄像头不需要联网（由电脑代下载应用包与模型文件）。
2. 用 USB 连接摄像头（地址 `192.168.42.1`），或让它和电脑处于同一局域网。
3. 摄像头账号密码默认 `recamera` / `recamera`（较早固件为 `recamera.2`）。
4. 控制台版本需为 0.5.5 或更高。

### 部署完成

摄像头正在运行文字与符号识别应用。

### 故障排查

| 现象 | 处理 |
|------|------|
| 下拉框是空的或很短 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`，解决网络后点刷新 |
| 登录被拒 | 用摄像头的账号密码，默认 `recamera` / `recamera`（较早的机器是 `recamera.2`） |
| 控制台不回应 | 摄像头可能还在重启，等一分钟再部署 |
| 提示 busy | 控制台正在处理另一个应用操作，完成后再试 |
| 装了但起不来 | 在控制台「应用」页查看状态；文件缺失就重新部署这一步 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_ocr.yaml}

在 reCamera Pro 上自动激活并配置文字识别应用 (`ocr`)。

### 前置条件

1. 摄像头与这台电脑处于同一局域网或通过 USB 连接（默认 `192.168.42.1`）。
2. 填写摄像头 Web 控制面板的管理员账号与密码（默认 `admin`）。
3. 摄像头应用中心已下载该应用。若尚未安装，先在控制面板的「应用中心」中安装。

### 部署完成

文字识别应用已在 reCamera Pro 上成功激活并运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| 登录失败 | 确认使用 Web 控制面板账号密码（非 SSH 密码），默认用户为 admin |
| 应用未安装 | 若提示未安装，先在摄像头应用中心目录中点击安装该应用 |
| 连接超时 | 确认摄像头 IP 正确，且 HTTPS (443) 端口可达 |

---

## 步骤 3: 打开控制台查看 {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制面板，查看实时推理画面与检测结果。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 页面无法打开 | SG2002 控制台：`http://<camera-ip>/`。reCamera Pro：443 端口的 HTTPS 控制面板，出现自签名证书警告属正常现象。 |
| 实时画面为黑屏或无法加载 | 当前没有运行中的应用。返回步骤 2 部署或激活应用。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/console_dashboard.yaml default=true}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 2 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_apps.yaml}

打开 reCamera Pro 控制面板，在实时预览中查看推理结果与流媒体画面。

### 前置条件

1. 用摄像头控制面板的账号密码登录（默认 admin）。
2. 在左侧打开**实时预览**页查看实时画面和 AI 检测结果。

### 部署完成

控制面板已打开，可以在实时预览中查看检测框与置信度。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 画面未加载 | 确认上一步的应用已成功激活运行 |

---

## 步骤 4: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 或 1883 端口被占用 | 停掉现有的 Home Assistant 或 Mosquitto，或跳过这一步直接用现有的 |
| Docker 起不来 | 打开 Docker Desktop 应用 |
| 容器反复重启 | 确认至少有 2 GB 可用内存 |

### 部署目标 {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

部署到局域网内的远程边缘主机（如 reComputer）。

### 前置条件

1. 目标设备 SSH 可达，已安装并启动 Docker。
2. 在下面填入它的 IP 地址、用户名和密码。

### 部署完成

1. 打开 **http://<设备 IP>:8123**，按向导创建管理员账号。
2. MQTT broker 在同一台设备的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 5 步直接填它 |

---

## 步骤 5: 在 Home Assistant 里查看结果（可选） {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看摄像头的实时画面与检测实体。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 检测实体缺失或不可用 | 相机与 Home Assistant 必须使用步骤 4 中的同一个 MQTT broker（端口 1883），且相机上的应用处于运行状态。 |
| 卡片中没有视频 | SG2002 在 Picture glance 卡片中使用控制台视频。reCamera Pro 需在 Stream Settings 中启用 RTSP，并以 TCP 传输方式将该 URL 添加为 Generic Camera。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/ha_dashboard.yaml default=true}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现，再添加视频流卡片。

### 前置条件

1. **在 Home Assistant 中添加 MQTT 集成**：进入「设置 → 设备与服务 → 添加集成」，选择 MQTT。Broker 填第 4 步部署的那台机器的地址，端口 1883，用户名密码留空。如果已经配好 MQTT 则跳过。
2. **在摄像头上填写 broker 地址**：在摄像头控制台里打开「集成 → Home Assistant」，填入第 4 步的 MQTT Broker 地址和端口 1883，先点「测试连接」，再点「保存」。
3. **查看实体**：在 Home Assistant「设置 → 设备与服务 → MQTT」找到摄像头实体。
4. **添加卡片**：在仪表盘添加 Picture glance 卡片，将检测实体叠加在实时画面上。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体会自动更新。

### 故障排查

| 现象 | 处理 |
|------|------|
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 实体出现了但一直不可用 | 确认控制台里应用正在运行 |
| 卡片上有画面，但没有检测图标 | 确认摄像头控制台的 Home Assistant 集成配置无误，且实体状态正常 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/ha_dashboard_pro.yaml}

把 reCamera Pro 的 RTSP 视频流与 MQTT 检测实体添加到 Home Assistant 仪表盘卡片。

### 前置条件

1. **在 Home Assistant 中添加 MQTT 集成**：进入「设置 → 设备与服务 → 添加集成」，选择 MQTT。Broker 填第 4 步部署的那台机器的地址，端口 1883，用户名密码留空。如果已经配好 MQTT 则跳过。
2. **配置摄像头 MQTT**：如果部署时已填写 MQTT 服务器地址，设备会自动连接。否则在摄像头应用中心点当前应用的「配置」，在「结果输出」里勾选 MQTT，输出模式选择 Home Assistant，并填入 broker 地址和端口 1883。
3. **查看实体**：「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，确认检测实体存在。
4. **打开 RTSP**：在摄像头控制面板「画面设置 → 推流设置」开启 RTSP，复制视频流地址。
5. **添加视频**：在 Home Assistant「设置 → 设备与服务 → 添加集成」选 Generic Camera，粘贴 RTSP 地址（传输协议选 TCP）。
6. **添加卡片**：在仪表盘添加 Picture glance 卡片，Camera Entity 选 Generic Camera，Entities 添加检测实体。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP |
| 实体显示 unknown | 摄像头前画面发生变化后才会有数据上报 |

---

## 套餐: 商业客流与动线分析 {#spatial_retail}

结合 ByteTrack 多目标追踪与虚拟绊线，统计出入客流人数，并实时识别驻足停留与求助状态。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `retail-vision`（商业客流与驻足分析）。
- **体验任务：** 
  1. 人员走过划定区域，观察出入计数值的增加；
  2. 在指定区域停留超过设定阈值，观察驻足停留事件触发。

## 步骤 1: 升级 reCamera 控制台 (SG2002) {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

安装 0.5.6 版本的控制台。如果已是 0.5.6 版本将自动跳过。若使用 reCamera Pro，请直接跳到步骤 2。

### 前置条件

1. 通过 USB（地址 `192.168.42.1`）连接摄像头，或将其置于同一局域网下。
2. 用户名为 `recamera`，默认密码为 `recamera`（旧固件可能为 `recamera.2`）。
3. 全新出厂设备请先访问 `http://192.168.42.1/#/security` 开启 SSH。

### 故障排查

| 现象 | 解决方法 |
|---|---|
| 连接失败 | 通过 USB 连接使用 `192.168.42.1`；局域网连接请查看路由器 DHCP 列表 |
| 密码错误 | 默认密码为 `recamera`（旧固件可能为 `recamera.2`） |
| 安装失败 | 重启摄像头后重新运行本步骤 |
| 无法使用 Node-RED | 控制台接管了摄像头；可在控制台系统设置中切换回 Node-RED |
| 恢复出厂设置 | 通电开机时按住 **User** 键，直到红色 LED 常亮 |

---

## 步骤 2: 安装商业客流应用 {#retail_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择要运行的客流分析应用并部署到摄像头。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 无法连接相机 | USB 连接使用 `192.168.42.1`；否则使用路由器上显示的 IP。reCamera Pro 通过 HTTPS 443 端口访问。 |
| 登录被拒绝 | reCamera（SG2002）：`recamera` / `recamera`（早期固件为 `recamera.2`）。reCamera Pro：Web 控制台账号，默认用户 `admin`。 |
| 部署后应用未启动 | 在控制台 Apps 页面（SG2002）或 App Center（Pro）查看应用状态；文件缺失时重新部署。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/recamera_console_app.yaml default=true}

在应用下拉框中选择 **零售人流分析 (retail-vision)**，点击**部署**。

### 前置条件

1. 这台电脑能访问互联网；摄像头不需要联网（由电脑代下载应用包与模型文件）。
2. 用 USB 连接摄像头（地址 `192.168.42.1`），或让它和电脑处于同一局域网。
3. 摄像头账号密码默认 `recamera` / `recamera`（较早固件为 `recamera.2`）。
4. 控制台版本需为 0.5.5 或更高。

### 部署完成

摄像头正在运行商业客流分析应用。

### 故障排查

| 现象 | 处理 |
|------|------|
| 下拉框是空的或很短 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`，解决网络后点刷新 |
| 登录被拒 | 用摄像头的账号密码，默认 `recamera` / `recamera`（较早的机器是 `recamera.2`） |
| 控制台不回应 | 摄像头可能还在重启，等一分钟再部署 |
| 提示 busy | 控制台正在处理另一个应用操作，完成后再试 |
| 装了但起不来 | 在控制台「应用」页查看状态；文件缺失就重新部署这一步 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_retail.yaml}

在 reCamera Pro 上自动激活并配置客流分析应用 (`retail-vision`)。

### 前置条件

1. 摄像头与这台电脑处于同一局域网或通过 USB 连接（默认 `192.168.42.1`）。
2. 填写摄像头 Web 控制面板的管理员账号与密码（默认 `admin`）。
3. 摄像头应用中心已下载该应用。若尚未安装，先在控制面板的「应用中心」中安装。

### 部署完成

客流分析应用已在 reCamera Pro 上成功激活并运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| 登录失败 | 确认使用 Web 控制面板账号密码（非 SSH 密码），默认用户为 admin |
| 应用未安装 | 若提示未安装，先在摄像头应用中心目录中点击安装该应用 |
| 连接超时 | 确认摄像头 IP 正确，且 HTTPS (443) 端口可达 |

---

## 步骤 3: 打开控制台查看 {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制面板，查看实时推理画面与检测结果。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 页面无法打开 | SG2002 控制台：`http://<camera-ip>/`。reCamera Pro：443 端口的 HTTPS 控制面板，出现自签名证书警告属正常现象。 |
| 实时画面为黑屏或无法加载 | 当前没有运行中的应用。返回步骤 2 部署或激活应用。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/console_dashboard.yaml default=true}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 2 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/recamera_pro_apps.yaml}

打开 reCamera Pro 控制面板，在实时预览中查看推理结果与流媒体画面。

### 前置条件

1. 用摄像头控制面板的账号密码登录（默认 admin）。
2. 在左侧打开**实时预览**页查看实时画面和 AI 检测结果。

### 部署完成

控制面板已打开，可以在实时预览中查看检测框与置信度。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 画面未加载 | 确认上一步的应用已成功激活运行 |

---

## 步骤 4: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 或 1883 端口被占用 | 停掉现有的 Home Assistant 或 Mosquitto，或跳过这一步直接用现有的 |
| Docker 起不来 | 打开 Docker Desktop 应用 |
| 容器反复重启 | 确认至少有 2 GB 可用内存 |

### 部署目标 {#ha_remote type=remote config=devices/homeassistant_deploy.yaml}

部署到局域网内的远程边缘主机（如 reComputer）。

### 前置条件

1. 目标设备 SSH 可达，已安装并启动 Docker。
2. 在下面填入它的 IP 地址、用户名和密码。

### 部署完成

1. 打开 **http://<设备 IP>:8123**，按向导创建管理员账号。
2. MQTT broker 在同一台设备的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 5 步直接填它 |

---

## 步骤 5: 在 Home Assistant 里查看结果（可选） {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看摄像头的实时画面与检测实体。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 检测实体缺失或不可用 | 相机与 Home Assistant 必须使用步骤 4 中的同一个 MQTT broker（端口 1883），且相机上的应用处于运行状态。 |
| 卡片中没有视频 | SG2002 在 Picture glance 卡片中使用控制台视频。reCamera Pro 需在 Stream Settings 中启用 RTSP，并以 TCP 传输方式将该 URL 添加为 Generic Camera。 |

### 模式: reCamera (SG2002) {#recamera_sg2002 config=devices/ha_dashboard.yaml default=true}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现，再添加视频流卡片。

### 前置条件

1. **在 Home Assistant 中添加 MQTT 集成**：进入「设置 → 设备与服务 → 添加集成」，选择 MQTT。Broker 填第 4 步部署的那台机器的地址，端口 1883，用户名密码留空。如果已经配好 MQTT 则跳过。
2. **在摄像头上填写 broker 地址**：在摄像头控制台里打开「集成 → Home Assistant」，填入第 4 步的 MQTT Broker 地址和端口 1883，先点「测试连接」，再点「保存」。
3. **查看实体**：在 Home Assistant「设置 → 设备与服务 → MQTT」找到摄像头实体。
4. **添加卡片**：在仪表盘添加 Picture glance 卡片，将检测实体叠加在实时画面上。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体会自动更新。

### 故障排查

| 现象 | 处理 |
|------|------|
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 实体出现了但一直不可用 | 确认控制台里应用正在运行 |
| 卡片上有画面，但没有检测图标 | 确认摄像头控制台的 Home Assistant 集成配置无误，且实体状态正常 |

### 模式: reCamera Pro (RV1126B) {#recamera_pro config=devices/ha_dashboard_pro.yaml}

把 reCamera Pro 的 RTSP 视频流与 MQTT 检测实体添加到 Home Assistant 仪表盘卡片。

### 前置条件

1. **在 Home Assistant 中添加 MQTT 集成**：进入「设置 → 设备与服务 → 添加集成」，选择 MQTT。Broker 填第 4 步部署的那台机器的地址，端口 1883，用户名密码留空。如果已经配好 MQTT 则跳过。
2. **配置摄像头 MQTT**：如果部署时已填写 MQTT 服务器地址，设备会自动连接。否则在摄像头应用中心点当前应用的「配置」，在「结果输出」里勾选 MQTT，输出模式选择 Home Assistant，并填入 broker 地址和端口 1883。
3. **查看实体**：「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，确认检测实体存在。
4. **打开 RTSP**：在摄像头控制面板「画面设置 → 推流设置」开启 RTSP，复制视频流地址。
5. **添加视频**：在 Home Assistant「设置 → 设备与服务 → 添加集成」选 Generic Camera，粘贴 RTSP 地址（传输协议选 TCP）。
6. **添加卡片**：在仪表盘添加 Picture glance 卡片，Camera Entity 选 Generic Camera，Entities 添加检测实体。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP |
| 实体显示 unknown | 摄像头前画面发生变化后才会有数据上报 |
