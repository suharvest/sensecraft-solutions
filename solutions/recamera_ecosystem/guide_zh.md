## 套餐: 目标检测与环境感知 {#object_detection}

体验边缘视觉的基础能力——通用目标检测（YOLO）与天气分类。通过实时 WebRTC 画面观察检测框与置信度变化，直观了解边缘端 INT8 模型的高效推理。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `yolo-detector`（80 类常见物体检测）或 `weather-classifier`（天气识别）。
- **体验任务：** 
  1. 将手机、水杯或手伸入镜头，观察 AI 在 50ms 内画出检测框和类别标签；
  2. 缓慢移动物体或遮挡一部分，观察置信度数字变化，理解视觉模型对遮挡的鲁棒性。

## 步骤 1: 升级 reCamera 控制台（SG2002） {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

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

## 步骤 3: 打开控制台查看（SG2002） {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 1 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

---

## 步骤 4: 检查并更新固件（reCamera Pro） {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

仅 reCamera Pro 用户需要执行。摄像头页面上已有应用中心则直接跳过。

### 前置条件

1. 打开摄像头的页面，已有**应用中心**就跳过这一步。
2. 在设备管理中填入摄像头地址与 ADB 端口 5555，点**检查更新设备**。
3. 更新走网络上的 ADB 5555 端口，只插 USB 不够。
4. 更新时摄像头会重启，需要几分钟，中途不要断电。同一页的**恢复出厂设置**可以回滚。

### 故障排查

| 现象 | 处理 |
|------|------|
| 测试连接失败 | 检查地址，以及这台电脑能否访问 5555 端口 |
| 点了检查更新设备没反应 | 摄像头可能已是最新，到它的页面上找应用中心 |
| 之后应用中心还是没出现 | 等摄像头重启完成后刷新页面 |

---

## 步骤 5: 打开应用中心（reCamera Pro） {#open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

仅 reCamera Pro 用户需要执行。打开应用中心，安装并启动对应应用。

### 前置条件

1. 用摄像头控制面板的账号密码登录（不是 SSH 账号）。
2. 在左侧打开**应用中心**，选择对应应用安装并点击**启动**。
3. 在左侧**实时预览**页查看画面和检测结果。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 应用中心是空的，或提示要登录 | 先登录控制面板，再重新打开这个标签页 |
| 加载目录失败 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`；自建目录时在安装对话框里修改目录地址 |
| 应用在列表里但启动不了 | 模型缺失，重新安装该应用 |

---

## 步骤 6: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 7、8 步填它的地址。

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
2. MQTT broker 在同一台设备的 1883 端口，第 7、8 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 7、8 步直接填它 |

---

## 步骤 7: 把 reCamera 接入 Home Assistant（可选） {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 6 步部署的，或你自己的）。
3. 摄像头控制台「集成 → Home Assistant」填入 broker 地址与 1883 端口。

### 部署完成

检测实体出现在 Home Assistant 里。如果实体显示不可用，到摄像头控制台确认应用正在运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 实体出现了但一直不可用 | 确认控制台里应用正在运行 |

---

## 步骤 8: 把 reCamera Pro 接入 Home Assistant（可选） {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

在应用的配置里填入 broker 地址，实体会自动出现在 Home Assistant。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 6 步部署的，或你自己的）。
3. 摄像头上有应用在运行。

### 部署完成

检测结果已出现在 Home Assistant 里。这份配置只属于当前应用：以后装的其他应用 MQTT 输出默认关闭，需要在它的「配置」里再做一遍。

### 故障排查

| 现象 | 处理 |
|------|------|
| 「配置」里没有「结果输出」分组 | 这个应用不支持 MQTT 输出，结果只留在设备上 |
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 保存被拒绝 | Broker 地址不能为空；「主题(base)」不能为空，不能含 `+` `#` 或空格 |
| 保存了，但 Home Assistant 里什么都没有 | 「输出模式」选 **Home Assistant**，并确认 Home Assistant 的 MQTT 集成连的是同一个 broker 和端口 |
| 实体出现了但一直不可用 | 摄像头上没有应用在运行，到应用中心启动一个 |

---

## 步骤 9: 在 Home Assistant 里查看 reCamera 结果（可选） {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看 reCamera (SG2002) 的视频流与检测实体。

### 前置条件

1. **查看实体。** 在 Home Assistant「设置 → 设备与服务 → MQTT」找到摄像头实体。
2. **添加卡片。** 在仪表盘添加 Picture glance 卡片，将检测实体叠加在实时画面上。

### 故障排查

| 现象 | 处理 |
|------|------|
| 卡片上有画面，但没有检测图标 | 确认摄像头控制台的 Home Assistant 集成配置无误，且实体状态正常 |
| 实体显示 unknown | 镜头前发生画面变化后才会有数据上报 |

---

## 步骤 10: 在 Home Assistant 里查看 reCamera Pro 结果（可选） {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

把画面和检测结果放到同一张卡片上。

### 前置条件

1. **查看实体。** 「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，记下要放到仪表盘上的实体。
2. **打开 RTSP。** 在摄像头上：**画面设置 → 推流设置**，协议选 RTSP 并开启，复制显示的视频流地址。需要认证时在同一页设置用户名和密码。
3. **添加视频。** 在 Home Assistant 里：「设置 → 设备与服务 → 添加集成」，选 **Generic Camera**，粘贴地址，RTSP transport protocol 选 **TCP**。开了认证时地址写成 `rtsp://用户名:密码@…`。
4. **搭卡片。** 「设置 → 仪表盘」→ 打开仪表盘 → 点铅笔编辑 → **添加卡片** → **Picture glance**（图片一览）。Camera Entity 选 Generic Camera，再把检测实体加进 Entities 列表。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体换成新应用发布的那套，Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP。设了凭据时写进地址 |
| 画面是黑的，或者放几秒就卡住 | 关掉摄像头的实时预览和所有 VLC 窗口 |
| 卡片上有画面，但没有检测图标 | 确认当前应用配过 MQTT（步骤 8），且实体在「设置 → 设备与服务 → MQTT」里存在 |
| 实体显示 `unknown` | 摄像头前发生变化后才会有值 |

---

## 套餐: 人体姿态与行为分析 {#human_behavior}

进阶体验人体拓扑关键点与时序动作识别。学习人脸关键点（Facemesh）、骨骼姿态、端侧隐私保护打码脱敏，以及基于时序状态机的动作分析。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `face-analysis`（人脸分析与打码脱敏）、`facemesh-reader`（困倦检测）、`fall-detection`（跌倒报警）、`fitness-trainer`（健身动作计数）。
- **体验任务：** 
  1. 对着镜头闭眼 3 秒或假装打哈欠，观察系统如何通过人脸 468 关键点触发困倦提醒；
  2. 开启隐私打码模式，观察 WebRTC 画面中人脸如何在端侧被自动高斯模糊，原始人脸不出设备。

## 步骤 1: 升级 reCamera 控制台（SG2002） {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

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

## 步骤 2: 安装人体行为应用（SG2002） {#human_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择 **人脸分析 (face-analysis)**、**困倦检测 (facemesh-reader)**、**跌倒检测 (fall-detection)** 或 **健身教练 (fitness-trainer)** 并部署。

### 前置条件

1. 这台电脑能访问互联网，摄像头不需要联网。
2. 若体验人脸打码隐私保护，可在安装后进入控制台开启 Privacy Blur。

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

---

## 步骤 3: 打开控制台查看（SG2002） {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 1 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

---

## 步骤 4: 检查并更新固件（reCamera Pro） {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

仅 reCamera Pro 用户需要执行。摄像头页面上已有应用中心则直接跳过。

### 前置条件

1. 打开摄像头的页面，已有**应用中心**就跳过这一步。
2. 在设备管理中填入摄像头地址与 ADB 端口 5555，点**检查更新设备**。
3. 更新走网络上的 ADB 5555 端口，只插 USB 不够。
4. 更新时摄像头会重启，需要几分钟，中途不要断电。同一页的**恢复出厂设置**可以回滚。

### 故障排查

| 现象 | 处理 |
|------|------|
| 测试连接失败 | 检查地址，以及这台电脑能否访问 5555 端口 |
| 点了检查更新设备没反应 | 摄像头可能已是最新，到它的页面上找应用中心 |
| 之后应用中心还是没出现 | 等摄像头重启完成后刷新页面 |

---

## 步骤 5: 打开应用中心（reCamera Pro） {#open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

仅 reCamera Pro 用户需要执行。打开应用中心，安装并启动对应应用。

### 前置条件

1. 用摄像头控制面板的账号密码登录（不是 SSH 账号）。
2. 在左侧打开**应用中心**，选择对应应用安装并点击**启动**。
3. 在左侧**实时预览**页查看画面和检测结果。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 应用中心是空的，或提示要登录 | 先登录控制面板，再重新打开这个标签页 |
| 加载目录失败 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`；自建目录时在安装对话框里修改目录地址 |
| 应用在列表里但启动不了 | 模型缺失，重新安装该应用 |

---

## 步骤 6: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 7、8 步填它的地址。

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
2. MQTT broker 在同一台设备的 1883 端口，第 7、8 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 7、8 步直接填它 |

---

## 步骤 7: 把 reCamera 接入 Home Assistant（可选） {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 6 步部署的，或你自己的）。
3. 摄像头控制台「集成 → Home Assistant」填入 broker 地址与 1883 端口。

### 部署完成

检测实体出现在 Home Assistant 里。如果实体显示不可用，到摄像头控制台确认应用正在运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 实体出现了但一直不可用 | 确认控制台里应用正在运行 |

---

## 步骤 8: 把 reCamera Pro 接入 Home Assistant（可选） {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

在应用的配置里填入 broker 地址，实体会自动出现在 Home Assistant。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 6 步部署的，或你自己的）。
3. 摄像头上有应用在运行。

### 部署完成

检测结果已出现在 Home Assistant 里。这份配置只属于当前应用：以后装的其他应用 MQTT 输出默认关闭，需要在它的「配置」里再做一遍。

### 故障排查

| 现象 | 处理 |
|------|------|
| 「配置」里没有「结果输出」分组 | 这个应用不支持 MQTT 输出，结果只留在设备上 |
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 保存被拒绝 | Broker 地址不能为空；「主题(base)」不能为空，不能含 `+` `#` 或空格 |
| 保存了，但 Home Assistant 里什么都没有 | 「输出模式」选 **Home Assistant**，并确认 Home Assistant 的 MQTT 集成连的是同一个 broker 和端口 |
| 实体出现了但一直不可用 | 摄像头上没有应用在运行，到应用中心启动一个 |

---

## 步骤 9: 在 Home Assistant 里查看 reCamera 结果（可选） {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看 reCamera (SG2002) 的视频流与检测实体。

### 前置条件

1. **查看实体。** 在 Home Assistant「设置 → 设备与服务 → MQTT」找到摄像头实体。
2. **添加卡片。** 在仪表盘添加 Picture glance 卡片，将检测实体叠加在实时画面上。

### 故障排查

| 现象 | 处理 |
|------|------|
| 卡片上有画面，但没有检测图标 | 确认摄像头控制台的 Home Assistant 集成配置无误，且实体状态正常 |
| 实体显示 unknown | 镜头前发生画面变化后才会有数据上报 |

---

## 步骤 10: 在 Home Assistant 里查看 reCamera Pro 结果（可选） {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

把画面和检测结果放到同一张卡片上。

### 前置条件

1. **查看实体。** 「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，记下要放到仪表盘上的实体。
2. **打开 RTSP。** 在摄像头上：**画面设置 → 推流设置**，协议选 RTSP 并开启，复制显示的视频流地址。需要认证时在同一页设置用户名和密码。
3. **添加视频。** 在 Home Assistant 里：「设置 → 设备与服务 → 添加集成」，选 **Generic Camera**，粘贴地址，RTSP transport protocol 选 **TCP**。开了认证时地址写成 `rtsp://用户名:密码@…`。
4. **搭卡片。** 「设置 → 仪表盘」→ 打开仪表盘 → 点铅笔编辑 → **添加卡片** → **Picture glance**（图片一览）。Camera Entity 选 Generic Camera，再把检测实体加进 Entities 列表。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体换成新应用发布的那套，Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP。设了凭据时写进地址 |
| 画面是黑的，或者放几秒就卡住 | 关掉摄像头的实时预览和所有 VLC 窗口 |
| 卡片上有画面，但没有检测图标 | 确认当前应用配过 MQTT（步骤 8），且实体在「设置 → 设备与服务 → MQTT」里存在 |
| 实体显示 `unknown` | 摄像头前发生变化后才会有值 |

---

## 套餐: 文字与符号识别 {#text_reading}

学习端侧两阶段视觉流水线（文本定位 + OCR 字符识别）与二维码密集解码。了解复杂文字检测算法如何部署在低功耗边缘端。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `ppocr-reader`（中英文 OCR 文字识别）或 `qrcode-reader`（二维码识别）。
- **体验任务：** 
  1. 拿名片、工牌或外卖包装盒置于摄像头前 15~25 cm 处，观察印刷文字如何秒级被捕获并切片转为 JSON 字符串；
  2. 拿手机展示二维码给镜头，看画面中多个二维码同时解析。

## 步骤 1: 升级 reCamera 控制台（SG2002） {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

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

## 步骤 2: 安装文字识读应用（SG2002） {#text_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择 **OCR 文字识别 (ppocr-reader)** 或 **二维码识别 (qrcode-reader)** 并部署。

### 前置条件

1. 电脑能访问互联网，摄像头不需要联网。
2. PP-OCR 模型内嵌中英文常用字库。

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

---

## 步骤 3: 打开控制台查看（SG2002） {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 1 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

---

## 步骤 4: 检查并更新固件（reCamera Pro） {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

仅 reCamera Pro 用户需要执行。摄像头页面上已有应用中心则直接跳过。

### 前置条件

1. 打开摄像头的页面，已有**应用中心**就跳过这一步。
2. 在设备管理中填入摄像头地址与 ADB 端口 5555，点**检查更新设备**。
3. 更新走网络上的 ADB 5555 端口，只插 USB 不够。
4. 更新时摄像头会重启，需要几分钟，中途不要断电。同一页的**恢复出厂设置**可以回滚。

### 故障排查

| 现象 | 处理 |
|------|------|
| 测试连接失败 | 检查地址，以及这台电脑能否访问 5555 端口 |
| 点了检查更新设备没反应 | 摄像头可能已是最新，到它的页面上找应用中心 |
| 之后应用中心还是没出现 | 等摄像头重启完成后刷新页面 |

---

## 步骤 5: 打开应用中心（reCamera Pro） {#open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

仅 reCamera Pro 用户需要执行。打开应用中心，安装并启动对应应用。

### 前置条件

1. 用摄像头控制面板的账号密码登录（不是 SSH 账号）。
2. 在左侧打开**应用中心**，选择对应应用安装并点击**启动**。
3. 在左侧**实时预览**页查看画面和检测结果。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 应用中心是空的，或提示要登录 | 先登录控制面板，再重新打开这个标签页 |
| 加载目录失败 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`；自建目录时在安装对话框里修改目录地址 |
| 应用在列表里但启动不了 | 模型缺失，重新安装该应用 |

---

## 步骤 6: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 7、8 步填它的地址。

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
2. MQTT broker 在同一台设备的 1883 端口，第 7、8 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 7、8 步直接填它 |

---

## 步骤 7: 把 reCamera 接入 Home Assistant（可选） {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 6 步部署的，或你自己的）。
3. 摄像头控制台「集成 → Home Assistant」填入 broker 地址与 1883 端口。

### 部署完成

检测实体出现在 Home Assistant 里。如果实体显示不可用，到摄像头控制台确认应用正在运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 实体出现了但一直不可用 | 确认控制台里应用正在运行 |

---

## 步骤 8: 把 reCamera Pro 接入 Home Assistant（可选） {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

在应用的配置里填入 broker 地址，实体会自动出现在 Home Assistant。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 6 步部署的，或你自己的）。
3. 摄像头上有应用在运行。

### 部署完成

检测结果已出现在 Home Assistant 里。这份配置只属于当前应用：以后装的其他应用 MQTT 输出默认关闭，需要在它的「配置」里再做一遍。

### 故障排查

| 现象 | 处理 |
|------|------|
| 「配置」里没有「结果输出」分组 | 这个应用不支持 MQTT 输出，结果只留在设备上 |
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 保存被拒绝 | Broker 地址不能为空；「主题(base)」不能为空，不能含 `+` `#` 或空格 |
| 保存了，但 Home Assistant 里什么都没有 | 「输出模式」选 **Home Assistant**，并确认 Home Assistant 的 MQTT 集成连的是同一个 broker 和端口 |
| 实体出现了但一直不可用 | 摄像头上没有应用在运行，到应用中心启动一个 |

---

## 步骤 9: 在 Home Assistant 里查看 reCamera 结果（可选） {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看 reCamera (SG2002) 的视频流与检测实体。

### 前置条件

1. **查看实体。** 在 Home Assistant「设置 → 设备与服务 → MQTT」找到摄像头实体。
2. **添加卡片。** 在仪表盘添加 Picture glance 卡片，将检测实体叠加在实时画面上。

### 故障排查

| 现象 | 处理 |
|------|------|
| 卡片上有画面，但没有检测图标 | 确认摄像头控制台的 Home Assistant 集成配置无误，且实体状态正常 |
| 实体显示 unknown | 镜头前发生画面变化后才会有数据上报 |

---

## 步骤 10: 在 Home Assistant 里查看 reCamera Pro 结果（可选） {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

把画面和检测结果放到同一张卡片上。

### 前置条件

1. **查看实体。** 「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，记下要放到仪表盘上的实体。
2. **打开 RTSP。** 在摄像头上：**画面设置 → 推流设置**，协议选 RTSP 并开启，复制显示的视频流地址。需要认证时在同一页设置用户名和密码。
3. **添加视频。** 在 Home Assistant 里：「设置 → 设备与服务 → 添加集成」，选 **Generic Camera**，粘贴地址，RTSP transport protocol 选 **TCP**。开了认证时地址写成 `rtsp://用户名:密码@…`。
4. **搭卡片。** 「设置 → 仪表盘」→ 打开仪表盘 → 点铅笔编辑 → **添加卡片** → **Picture glance**（图片一览）。Camera Entity 选 Generic Camera，再把检测实体加进 Entities 列表。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体换成新应用发布的那套，Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP。设了凭据时写进地址 |
| 画面是黑的，或者放几秒就卡住 | 关掉摄像头的实时预览和所有 VLC 窗口 |
| 卡片上有画面，但没有检测图标 | 确认当前应用配过 MQTT（步骤 8），且实体在「设置 → 设备与服务 → MQTT」里存在 |
| 实体显示 `unknown` | 摄像头前发生变化后才会有值 |

---

## 套餐: 商业客流与动线分析 {#spatial_retail}

体验多目标追踪（ByteTrack）与虚拟绊线结合的商业客流统计应用，学习端侧如何在无服务器依赖下实现过线人数统计与停留时长分析。

- **设备：** reCamera (SG2002) 或 reCamera Pro (RV1126B)；接入 Home Assistant 时另需一台电脑或 reComputer R1100。
- **推荐应用：** `retail-vision`（零售客流统计）。
- **体验任务：** 
  1. 在控制台或实时画面中划定一条虚拟绊线，在镜头前来回走动，观察进出计数器的实时累加；
  2. 在绊线一侧驻留数秒，观察端侧对停留驻足与求助状态的判定逻辑。

## 步骤 1: 升级 reCamera 控制台（SG2002） {#deploy_console type=recamera_cpp required=false config=devices/recamera_console.yaml}

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

## 步骤 2: 安装商业客流应用（SG2002） {#retail_install_app type=recamera_console_app required=false config=devices/recamera_console_app.yaml}

在下拉框中选择 **零售客流分析 (retail-vision)** 并部署。

### 前置条件

1. 电脑能访问互联网，摄像头不需要联网。
2. 零售客流应用包含 ByteTrack 目标追踪与虚拟绊线计数逻辑。

### 部署完成

摄像头正在运行商业客流与动线分析应用。

### 故障排查

| 现象 | 处理 |
|------|------|
| 下拉框是空的或很短 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`，解决网络后点刷新 |
| 登录被拒 | 用摄像头的账号密码，默认 `recamera` / `recamera`（较早的机器是 `recamera.2`） |
| 控制台不回应 | 摄像头可能还在重启，等一分钟再部署 |
| 提示 busy | 控制台正在处理另一个应用操作，完成后再试 |
| 装了但起不来 | 在控制台「应用」页查看状态；文件缺失就重新部署这一步 |

---

## 步骤 3: 打开控制台查看（SG2002） {#open_console type=web_dashboard required=false config=devices/console_dashboard.yaml}

打开摄像头的控制台，查看实时推理画面与检测结果。

### 前置条件

1. 用第 1 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测框。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以查看实时画面、修改检测阈值、网络与系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

---

## 步骤 4: 检查并更新固件（reCamera Pro） {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

仅 reCamera Pro 用户需要执行。摄像头页面上已有应用中心则直接跳过。

### 前置条件

1. 打开摄像头的页面，已有**应用中心**就跳过这一步。
2. 在设备管理中填入摄像头地址与 ADB 端口 5555，点**检查更新设备**。
3. 更新走网络上的 ADB 5555 端口，只插 USB 不够。
4. 更新时摄像头会重启，需要几分钟，中途不要断电。同一页的**恢复出厂设置**可以回滚。

### 故障排查

| 现象 | 处理 |
|------|------|
| 测试连接失败 | 检查地址，以及这台电脑能否访问 5555 端口 |
| 点了检查更新设备没反应 | 摄像头可能已是最新，到它的页面上找应用中心 |
| 之后应用中心还是没出现 | 等摄像头重启完成后刷新页面 |

---

## 步骤 5: 打开应用中心（reCamera Pro） {#open_appcenter_pro type=web_dashboard required=false config=devices/recamera_pro_apps.yaml}

仅 reCamera Pro 用户需要执行。打开应用中心，安装并启动对应应用。

### 前置条件

1. 用摄像头控制面板的账号密码登录（不是 SSH 账号）。
2. 在左侧打开**应用中心**，选择对应应用安装并点击**启动**。
3. 在左侧**实时预览**页查看画面和检测结果。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 应用中心是空的，或提示要登录 | 先登录控制面板，再重新打开这个标签页 |
| 加载目录失败 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`；自建目录时在安装对话框里修改目录地址 |
| 应用在列表里但启动不了 | 模型缺失，重新安装该应用 |

---

## 步骤 6: 部署 Home Assistant（可选） {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

在本地电脑上部署 Home Assistant。需要 Docker Desktop 运行且 8123/1883 端口可用。

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 7、8 步填它的地址。

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
2. MQTT broker 在同一台设备的 1883 端口，第 7、8 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 7、8 步直接填它 |

---

## 步骤 7: 把 reCamera 接入 Home Assistant（可选） {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

让 Home Assistant 和摄像头连同一个 broker，检测实体会自动出现。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 6 步部署的，或你自己的）。
3. 摄像头控制台「集成 → Home Assistant」填入 broker 地址与 1883 端口。

### 部署完成

检测实体出现在 Home Assistant 里。如果实体显示不可用，到摄像头控制台确认应用正在运行。

### 故障排查

| 现象 | 处理 |
|------|------|
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 实体出现了但一直不可用 | 确认控制台里应用正在运行 |

---

## 步骤 8: 把 reCamera Pro 接入 Home Assistant（可选） {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

在应用的配置里填入 broker 地址，实体会自动出现在 Home Assistant。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 6 步部署的，或你自己的）。
3. 摄像头上有应用在运行。

### 部署完成

检测结果已出现在 Home Assistant 里。这份配置只属于当前应用：以后装的其他应用 MQTT 输出默认关闭，需要在它的「配置」里再做一遍。

### 故障排查

| 现象 | 处理 |
|------|------|
| 「配置」里没有「结果输出」分组 | 这个应用不支持 MQTT 输出，结果只留在设备上 |
| broker 上收不到任何数据 | 确认 broker 地址不为空，且摄像头能访问到 |
| 保存被拒绝 | Broker 地址不能为空；「主题(base)」不能为空，不能含 `+` `#` 或空格 |
| 保存了，但 Home Assistant 里什么都没有 | 「输出模式」选 **Home Assistant**，并确认 Home Assistant 的 MQTT 集成连的是同一个 broker 和端口 |
| 实体出现了但一直不可用 | 摄像头上没有应用在运行，到应用中心启动一个 |

---

## 步骤 9: 在 Home Assistant 里查看 reCamera 结果（可选） {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

在 Home Assistant 仪表盘上查看 reCamera (SG2002) 的视频流与检测实体。

### 前置条件

1. **查看实体。** 在 Home Assistant「设置 → 设备与服务 → MQTT」找到摄像头实体。
2. **添加卡片。** 在仪表盘添加 Picture glance 卡片，将检测实体叠加在实时画面上。

### 故障排查

| 现象 | 处理 |
|------|------|
| 卡片上有画面，但没有检测图标 | 确认摄像头控制台的 Home Assistant 集成配置无误，且实体状态正常 |
| 实体显示 unknown | 镜头前发生画面变化后才会有数据上报 |

---

## 步骤 10: 在 Home Assistant 里查看 reCamera Pro 结果（可选） {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

把画面和检测结果放到同一张卡片上。

### 前置条件

1. **查看实体。** 「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，记下要放到仪表盘上的实体。
2. **打开 RTSP。** 在摄像头上：**画面设置 → 推流设置**，协议选 RTSP 并开启，复制显示的视频流地址。需要认证时在同一页设置用户名和密码。
3. **添加视频。** 在 Home Assistant 里：「设置 → 设备与服务 → 添加集成」，选 **Generic Camera**，粘贴地址，RTSP transport protocol 选 **TCP**。开了认证时地址写成 `rtsp://用户名:密码@…`。
4. **搭卡片。** 「设置 → 仪表盘」→ 打开仪表盘 → 点铅笔编辑 → **添加卡片** → **Picture glance**（图片一览）。Camera Entity 选 Generic Camera，再把检测实体加进 Entities 列表。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体换成新应用发布的那套，Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP。设了凭据时写进地址 |
| 画面是黑的，或者放几秒就卡住 | 关掉摄像头的实时预览和所有 VLC 窗口 |
| 卡片上有画面，但没有检测图标 | 确认当前应用配过 MQTT（步骤 8），且实体在「设置 → 设备与服务 → MQTT」里存在 |
| 实体显示 `unknown` | 摄像头前发生变化后才会有值 |

---
