## 套餐: reCamera {#recamera}

在 reCamera 的控制台里安装目标检测、文字识别、人脸分析、跌倒检测或客流统计应用，在浏览器里切换，并可把结果通过 MQTT 发到 Home Assistant。

- **设备：** reCamera；第 4 到 6 步接入 Home Assistant 时，另需一台电脑或 reComputer R1100。
- **网络：** 安装应用时，这台电脑需要联网。
- **限制：** 同一时间只运行一个应用。切换应用会停掉前一个及其 RTSP 和 MQTT 输出，不会卸载。

## 步骤 1: 升级 reCamera 控制台 {#deploy_console type=recamera_cpp required=true config=devices/recamera_console.yaml}

安装 0.5.5 版控制台，已经是这个版本会自动跳过。

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

## 步骤 2: 选择并安装应用 {#install_app type=recamera_console_app required=true config=devices/recamera_console_app.yaml}

从下拉框里选一个应用，点**部署**，自动完成下载、安装和启用。

### 前置条件

1. 这台电脑能访问互联网；摄像头不需要联网。
2. 地址和密码沿用上一步。
3. 应用连同模型可能有几百 MB，部署页会显示进度。

### 部署完成

摄像头正在运行你选的应用。应用支持 ONVIF，NVR 或视频管理平台可以自动发现这台摄像头并拉流。

第 4 到 6 步可选，用于把结果接入 Home Assistant。

### 故障排查

| 现象 | 处理 |
|------|------|
| 下拉框是空的或很短 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`，解决网络后点刷新 |
| 登录被拒 | 用摄像头的账号密码，默认 `recamera` / `recamera`（较早的机器是 `recamera.2`）。连续失败会锁定 60 秒 |
| 控制台不回应 | 摄像头可能还在重启，等一分钟再部署 |
| 提示 busy | 控制台正在处理另一个应用操作，完成后再试 |
| 存储空间不足 | 先到控制台卸载用不到的应用 |
| 装了但起不来 | 在控制台「应用」页查看状态；文件缺失就重新部署这一步 |
| 开启隐私打码后摄像头起不来 | 拔掉电源再插上，软件重启无效 |

---

## 步骤 3: 打开控制台查看 {#open_console type=web_dashboard required=true config=devices/console_dashboard.yaml}

打开摄像头的控制台，查看应用的检测结果。

### 前置条件

1. 用第 1 步的摄像头账号密码登录。
2. 在**应用**页点当前应用的**调试**，查看实时画面和检测结果。
3. 换应用在**应用**页切换，**从云端安装**里有目录中的其他应用。

### 部署完成

控制台地址 `http://<摄像头 IP>/`，可以安装和切换应用、查看实时画面、修改网络、隐私和系统设置。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 等一分钟让摄像头重启完成，再刷新 |
| 登录被拒 | 用摄像头的账号密码，默认 `recamera` / `recamera` |
| 实时画面是黑的 | 没有应用在运行，回上一步部署一个应用 |

---

## 步骤 4: 部署 Home Assistant {#deploy_ha type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local type=local config=devices/homeassistant_deploy.yaml default=true}

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

### 前置条件

1. 目标设备 SSH 可达，已安装并启动 Docker。
2. 在下面填入它的 IP 地址、用户名和密码。

### 部署完成

1. 打开 **http://\<设备 IP\>:8123**，按向导创建管理员账号。
2. MQTT broker 在同一台设备的 1883 端口，第 5 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 5 步直接填它 |

---

## 步骤 5: 把摄像头接入 Home Assistant {#connect_ha type=manual required=false config=devices/connect_ha_recamera.yaml}

让 Home Assistant 和摄像头连同一个 broker，实体会自动出现。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 4 步部署的，或你自己的）。
3. 摄像头上有应用在运行。

### 部署完成

检测结果通过 MQTT 自动发现出现在 Home Assistant 里；换应用后实体集合会跟着变。自动发现不含视频，画面在第 6 步单独添加。

### 故障排查

| 现象 | 处理 |
|------|------|
| 摄像头上「测试连接」失败 | broker 地址填 broker 所在机器的 IP，不要填 `localhost` |
| 保存了，但 Home Assistant 里什么都没有 | 确认 Home Assistant 的 MQTT 集成连的是同一个 broker 和端口，然后在控制台里重启当前应用 |
| 实体出现了但一直不可用 | 摄像头上没有应用在运行，到控制台启用一个 |
| 换应用之后实体消失了 | 正常，每个应用发布自己的一套实体 |

---

## 步骤 6: 在 Home Assistant 里查看结果 {#ha_dashboard type=web_dashboard required=false config=devices/ha_dashboard.yaml}

把画面和检测结果放到同一张卡片上。

### 前置条件

1. **查看实体。** 「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，记下要放到仪表盘上的实体。
2. **添加视频。** 「设置 → 设备与服务 → 添加集成」，选 **Generic Camera**：
   - Stream Source URL：`rtsp://<摄像头 IP>:8554/live0`（控制台「集成」页可复制）
   - RTSP transport protocol：选 **TCP**
   - Verify SSL certificate 不要勾
3. **搭卡片。** 「设置 → 仪表盘」→ 打开仪表盘 → 点铅笔编辑 → **添加卡片** → **Picture glance**（图片一览）。Camera Entity 选刚加的 Generic Camera，再把检测实体加进 Entities 列表。
4. **分开显示（可选）。** 用 **Entities**（实体）卡片按行列出数值，用 **History**（历史）卡片看变化。
5. **自动化（可选）。** 「设置 → 自动化与场景 → 创建自动化」，触发器选**实体 → 状态**，指向某个检测实体。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体会变，Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP |
| 画面是黑的，或者放几秒就卡住 | 关掉控制台的实时画面和所有 VLC 窗口 |
| 卡片上有画面，但没有检测图标 | 先在「设置 → 设备与服务 → MQTT」里确认实体存在，再加到卡片上 |
| 实体显示 `unknown` | 摄像头前发生变化后才会有值 |
| Picture glance 不接受某个实体 | 添加具体实体，不要添加设备 |

---

## 套餐: reCamera Pro {#recamera_pro}

在 reCamera Pro 的应用中心安装应用，并可把结果通过 MQTT 发到 Home Assistant。

- **设备：** reCamera Pro；第 3 到 5 步接入 Home Assistant 时，另需一台电脑或 reComputer R1100。
- **网络：** 摄像头和这台电脑在同一网络，安装应用时这台电脑需要联网。
- **限制：** 摄像头不自带 MQTT broker，第 4 步填入 broker 地址前结果只留在设备上；broker 地址按应用分别配置。同一时间只运行一个推理应用。

## 步骤 1: 检查并更新固件 {#firmware_pro type=manual required=false config=devices/recamera_pro_firmware.yaml}

摄像头页面上还没有应用中心时才需要做，只做一次。

![设备管理、嵌入式标签页，以及填写地址和 ADB 端口的 reCamera Pro 条目](https://files.seeedstudio.com/Solution/landpage_asset/fall-detection/recamera-pro-firmware-update-a9539b3d.gif)

### 前置条件

1. 打开摄像头的页面，已有**应用中心**就跳过这一步。
2. 在本应用里：**设备管理 → 嵌入式 → reCamera Pro**，填入摄像头地址，点**检查更新设备**。
3. 更新走网络上的 ADB 5555 端口，只插 USB 不够。
4. 更新时摄像头会重启，需要几分钟，中途不要断电。同一页的**恢复出厂设置**可以回滚。

### 故障排查

| 现象 | 处理 |
|------|------|
| 测试连接失败 | 检查地址，以及这台电脑能否访问 5555 端口 |
| 点了检查更新设备没反应 | 摄像头可能已是最新，到它的页面上找应用中心 |
| 之后应用中心还是没出现 | 等摄像头重启完成后刷新页面 |

---

## 步骤 2: 挑选并安装应用 {#open_appcenter_pro type=web_dashboard required=true config=devices/recamera_pro_apps.yaml}

打开应用中心，安装并启动一个应用。

### 前置条件

1. 用摄像头控制面板的账号密码登录（不是 SSH 账号）。
2. 在左侧打开**应用中心**，点 **+** 打开安装对话框，选择应用安装。
3. 应用需要运行时组件时，对话框会询问是否一并下载；取消则不安装该应用。
4. 在应用卡片上点**启动**。启动一个推理应用会停掉另一个。
5. 在左侧**实时预览**或**实时画面**页查看画面和检测结果。

### 部署完成

摄像头正在运行你选的应用。第 3 到 5 步可选，用于把结果接入 Home Assistant。

### 故障排查

| 现象 | 处理 |
|------|------|
| 页面打不开 | 地址用 `http://` 开头输入，让浏览器跟随跳转 |
| 证书告警 | 开启 HTTPS 时摄像头使用自签证书，继续访问即可 |
| 应用中心是空的，或提示要登录 | 先登录控制面板，再重新打开这个标签页 |
| 加载目录失败 | 这台电脑访问不了 `sensecraft-statics.seeed.cc`；自建目录时在安装对话框里修改目录地址 |
| 校验和不匹配，拒绝安装 | 重新加载目录再试一次 |
| 应用在列表里但启动不了 | 模型缺失，重新安装该应用 |
| 实时预览里没有检测结果 | 确认正在运行的是你装的应用 |

---

## 步骤 3: 部署 Home Assistant {#deploy_ha_pro type=docker_deploy required=false config=devices/homeassistant_deploy.yaml}

启动 Home Assistant 和一个 MQTT broker。两者都已在运行就跳过。

### 部署目标 {#ha_local_pro type=local config=devices/homeassistant_deploy.yaml default=true}

### 前置条件

1. 已安装并启动 Docker Desktop。
2. 至少 2 GB 可用磁盘。
3. 8123 和 1883 端口空闲。

### 部署完成

1. 打开 **http://localhost:8123**，按向导创建管理员账号。
2. MQTT broker 在这台机器的 1883 端口，第 4 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 8123 或 1883 端口被占用 | 停掉现有的 Home Assistant 或 Mosquitto，或跳过这一步直接用现有的 |
| Docker 起不来 | 打开 Docker Desktop 应用 |
| 容器反复重启 | 确认至少有 2 GB 可用内存 |

### 部署目标 {#ha_remote_pro type=remote config=devices/homeassistant_deploy.yaml}

### 前置条件

1. 目标设备 SSH 可达，已安装并启动 Docker。
2. 在下面填入它的 IP 地址、用户名和密码。

### 部署完成

1. 打开 **http://\<设备 IP\>:8123**，按向导创建管理员账号。
2. MQTT broker 在同一台设备的 1883 端口，第 4 步填它的地址。

### 故障排查

| 现象 | 处理 |
|------|------|
| 连接超时 | 检查网络，用 ping 测试 |
| SSH 认证失败 | 核对用户名和密码 |
| 目标机 1883 被占用 | 那里已有 broker，保留它，第 4 步直接填它 |

---

## 步骤 4: 把摄像头接入 Home Assistant {#connect_ha_pro type=manual required=false config=devices/connect_ha_recamera_pro.yaml}

在应用的配置里填入 broker 地址，实体会自动出现在 Home Assistant。

### 前置条件

1. Home Assistant 已运行并能登录。
2. 有一个摄像头可访问的 MQTT broker（第 3 步部署的，或你自己的）。
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
| 启动别的应用之后实体消失了 | 正常，每个应用发布自己的一套实体，没配过 MQTT 的应用不发布 |

---

## 步骤 5: 在 Home Assistant 里查看结果 {#ha_dashboard_pro type=web_dashboard required=false config=devices/ha_dashboard_pro.yaml}

把画面和检测结果放到同一张卡片上。

### 前置条件

1. **查看实体。** 「设置 → 设备与服务 → MQTT」，点进这台摄像头的设备，记下要放到仪表盘上的实体。
2. **打开 RTSP。** 在摄像头上：**画面设置 → 推流设置**，协议选 RTSP 并开启，复制显示的视频流地址。需要认证时在同一页设置用户名和密码。
3. **添加视频。** 在 Home Assistant 里：「设置 → 设备与服务 → 添加集成」，选 **Generic Camera**，粘贴地址，RTSP transport protocol 选 **TCP**。开了认证时地址写成 `rtsp://用户名:密码@…`。
4. **搭卡片。** 「设置 → 仪表盘」→ 打开仪表盘 → 点铅笔编辑 → **添加卡片** → **Picture glance**（图片一览）。Camera Entity 选 Generic Camera，再把检测实体加进 Entities 列表。
5. **分开显示（可选）。** 用 **Entities**（实体）卡片按行列出数值，用 **History**（历史）卡片看变化。
6. **自动化（可选）。** 「设置 → 自动化与场景 → 创建自动化」，触发器选**实体 → 状态**，指向某个检测实体。

### 部署完成

仪表盘上能看到摄像头画面和检测实体。换应用后 MQTT 实体换成新应用发布的那套，Generic Camera 画面不受影响。

### 故障排查

| 现象 | 处理 |
|------|------|
| 推流设置里没有视频流地址 | RTSP 未开启或选了别的协议；选 RTSP 会关闭 RTMP 和 ONVIF |
| Generic Camera 提示连不上 | 先用 VLC 测试这条地址；VLC 能播而 Home Assistant 不行时，把 RTSP transport 设为 TCP。设了凭据时写进地址 |
| 画面是黑的，或者放几秒就卡住 | 关掉摄像头的实时预览和所有 VLC 窗口 |
| 卡片上有画面，但没有检测图标 | 确认当前应用配过 MQTT（第 4 步），且实体在「设置 → 设备与服务 → MQTT」里存在 |
| 实体显示 `unknown` | 摄像头前发生变化后才会有值 |
