## 套餐: 套餐 0 · 云端版 {#trial}

只需一台 Watcher，无需购买主机。库存数据和语音服务全部托管在 Seeed 云端，开箱即可体验完整的语音仓管功能。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | 语音助手，接收语音指令 |

**部署完成后你可以：**
- 语音操控库存（说"入库 10 箱苹果"就能录入）
- 网页实时查看库存数据

**前提条件：** 需要联网 · SenseCraft 账号（免费注册）

**注意：** 按月订阅制，数据托管在 Seeed 云端，不支持人脸识别，不支持对接 ERP / WMS

## 步骤 1: 配置 Watcher 设备 {#sensecraft type=manual required=true}

![Agent 配置](gallery/configure_agent.gif)

将 Watcher 连接到 SenseCraft 云平台：

1. 打开 Watcher 电源，按住右上角滚轮按钮 5 秒后松开开机
2. 手机搜索名为"Watcher-XXXX"的 WiFi 热点并连接
3. 连接后浏览器会自动弹出配网页面（如未弹出，手动访问 http://192.168.42.1）
4. 等待约 5 秒完成 WiFi 扫描，从列表中选择 2.4GHz 网络，输入密码，点击"连接"
5. 连接成功后设备自动重启，重启后屏幕显示 6 位验证码
6. 登录 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/device/local/37/)，点击模型里的「SenseCraft Watcher」选择「Watcher Agent」→「Bind Device」，输入 6 位验证码完成绑定
7. 点击「Create」新建一个 Agent，点击 Agent 卡片上的 ⚙ 设置图标，在「角色模板」中选择「库存管理员」，按需调整名称和语言后保存

### 故障排除

| 问题 | 解决方法 |
|------|--------|
| 手机搜不到热点 | 确保手机 WiFi 已开启，靠近 Watcher 重试 |
| 配网失败 | Watcher 仅支持 2.4GHz WiFi，检查路由器是否开启 2.4GHz 频段 |
| 找不到 Watcher Agent | 确认已登录 SenseCraft 账号，刷新页面 |

---

## 步骤 2: 配置仓库系统 {#cloud_warehouse_config type=manual required=true}

![配置演示](gallery/setup_warehous.gif)

仓管系统由 Seeed 云端托管，无需自行部署。打开云端仓库管理系统完成初始配置：

1. 浏览器访问 [仓管系统](https://warehouse.seeed.cn/)
2. 点击右上角「登录」→「Watcher 设备用户可自助注册」
3. 对 Watcher 说「你的设备 ID 是什么」，Watcher 会回报一串 ID
4. 将设备 ID 填入注册页面，完成注册后登录
5. 进入系统后，点击左侧「库存列表」导入现有库存（[下载 Excel 模板](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx)）

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 检查网络连接，稍后重试 |
| 导入失败 | 检查 Excel 格式是否与模板一致 |
| 忘记管理员密码 | 进入「设备管理」删除此应用（勾选「删除数据」），然后重新初始化 |

---

## 步骤 3: 联动智能体 {#cloud_mcp_bridge type=manual required=true}

![MCP 端点](gallery/mcp-endpoint.png)

在仓库系统中添加智能体，让 Watcher 能够操作库存：

1. 浏览器访问 [仓管系统](https://warehouse.seeed.cn/)
2. 进入左侧「智能体配置」，点击「添加智能体」，填写名称
3. 登录 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/device/local/37/)，在 ⚙ 设置页下滑到最底部，点击「MCP Setting」→「获取 MCP 端点」→「复制端点地址」
4. 在 Endpoint 中粘贴端点地址
5. 点击「保存并启动」
6. 点击智能体卡片上的「MCP 接入点」，刷新状态显示 Connected 即连接成功

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 连接失败 | 检查端点地址是否完整复制，不要包含多余空格 |
| 状态一直显示 Disconnected | 确认 Watcher 已正确绑定到 SenseCraft 平台 |

---

## 步骤 4: 效果体验 {#demo type=manual verify=true required=true}

![语音入库演示](gallery/xiaozhi-stock-in.png)

试试这些语音指令——对话本身就是验证体验版是否就绪。说完后到 SenseCraft 平台 [sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/) 查看产生的库存记录。

| 说这句话 | Watcher 会做什么 |
|----------|------------------|
| "苹果还有多少？" | 查询苹果的库存数量 |
| "入库 10 箱苹果" | 添加 10 箱苹果到库存 |
| "出库 5 箱香蕉" | 从库存减少 5 箱香蕉 |
| "今天入库了什么？" | 列出今日入库记录 |

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| Watcher 没反应 | 确认智能体已连接（状态显示 Connected） |
| 库存没更新 | 刷新 SenseCraft 页面查看最新数据 |
| 看不到记录 | 确认 Watcher 已绑定 SenseCraft 账号 |

### 部署完成

SenseCraft 体验版已就绪！

**访问入口：**
- SenseCraft 平台：[sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/)

试着说「入库 10 箱苹果」测试语音库存管理。

---

## 套餐: 套餐一 · 基础版 {#sensecraft_cloud}

使用 [SenseCraft](https://sensecraft.seeed.cc/ai/) 云服务提供语音 AI 能力。最简单的部署方式——只需部署仓管系统，将 Watcher 连接到 SenseCraft 平台即可。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | 语音助手，接收语音指令 |
| reComputer R1125-10 | 运行仓库管理系统 |
| USB-C 数据线 | 烧录 Watcher 固件 |

**部署完成后你可以：**
- 语音操控库存（说"入库 10 箱苹果"就能录入）
- 网页实时查看库存数据
- 开箱即用，无需额外配置

❌ 不支持高精度人脸识别

**前提条件：** 需要联网 · [SenseCraft 账号](https://sensecraft.seeed.cc/ai/)（免费注册）

## 步骤 1: 更新小智固件 {#warehouse_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

将语音助手程序写入 Watcher 以启用语音交互。

### 接线

![连接设备](gallery/watcher_usb.png)

1. 用 USB-C 线连接 Watcher 到电脑
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-B** 的 COM 口，macOS / Linux 选编号较大的那个（如 `...53` / `ttyACM1`）
3. 点击烧录按钮

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到串口 | 换一条 USB 线或换个 USB 口 |
| 选错串口（烧录无反应或立刻失败） | 列表里换另一个 CH342 串口再试 |
| 收不到串口数据 | 按住 BOOT 按钮，按一下 RESET，松开 BOOT，然后重试 |
| 烧录失败 | 重新插拔设备再试 |

---

## 步骤 2: 更新视觉检测固件 {#warehouse_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

将视觉检测程序写入 Watcher 的 AI 芯片。

### 接线

![连接设备](gallery/watcher_usb.png)

1. 确保 Watcher 仍通过 USB-C 线连接到电脑（与上一步相同）
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-A** 的 COM 口，macOS / Linux 选编号较小的那个（如 `...51` / `ttyACM0`）—— 和上一步不是同一个口
3. 点击烧录按钮
4. 点击烧录后，按一下设备的重启按钮进入烧录模式

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 设备无响应 | 重新插拔 USB 线 |
| 烧录卡住或失败 | 按重启按钮重试 |
| 反复烧录失败 | 换一条 USB 线或换个 USB 口 |
| 烧录到 99% 失败或中途重启 | 关闭其他占用串口的程序，重新插拔 USB 后重试 |

---

## 步骤 3: 配置 Watcher 设备 {#watcher_setup type=manual required=true}

![Agent 配置](gallery/configure_agent.gif)

先通过 WiFi 配对 Watcher，绑定到 SenseCraft 云平台，再创建一个「库存管理员」智能体并复制其 MCP 端点地址（步骤 6 会用到）。

### 接线

1. 打开 Watcher 电源，按住右上角滚轮按钮 5 秒后松开开机
2. 手机搜索名为"Watcher-XXXX"的 WiFi 热点并连接
3. 连接后浏览器会自动弹出配网页面（如未弹出，手动访问 http://192.168.42.1）
4. 等待约 5 秒完成 WiFi 扫描，从列表中选择 2.4GHz 网络，输入密码，点击"连接"
5. 连接成功后设备自动重启，重启后屏幕显示 6 位验证码
6. 登录 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/device/local/37/)，点击模型里的「SenseCraft Watcher」选择「Watcher Agent」→「Bind Device」，输入 6 位验证码完成绑定
7. 点击「Create」新建一个 Agent，点击 Agent 卡片上的 ⚙ 设置图标，在「角色模板」中选择「库存管理员」，按需调整名称和语言后保存
8. 对 Watcher 说「开启人脸识别模式」，让设备切换到人脸识别检测
9. 在 ⚙ 设置页下滑到最底部，点击「MCP Setting」→「获取 MCP 端点」→「复制端点地址」

### 故障排除

| 问题 | 解决方法 |
|------|--------|
| 手机搜不到热点 | 确保手机 WiFi 已开启，靠近 Watcher 重试 |
| 配网失败 | Watcher 仅支持 2.4GHz WiFi，检查路由器是否开启 2.4GHz 频段 |
| 找不到 Watcher Agent | 确认已登录 SenseCraft 账号，刷新页面 |

---

## 步骤 4: 仓库管理系统 {#warehouse type=docker_deploy required=true config=devices/warehouse_deploy.yaml}

部署库存管理服务，支持语音操控和网页看板。

### 部署目标 {#warehouse_local type=local config=devices/warehouse_deploy.yaml}

在本机运行仓库管理服务。

### 接线

1. 确保本机 Docker 已安装并运行
2. 点击部署按钮启动服务

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 检查 2125 端口是否被其他服务使用 |
| Docker 未运行 | 启动 Docker Desktop 后重试 |

### 部署目标 {#warehouse_remote type=remote config=devices/warehouse_deploy.yaml default=true}

部署到 reComputer R1125-10 边缘计算设备。

### 接线

![接线图](gallery/R1100_connected.png)

1. 将 R1125-10 接上电源和网线，确保与电脑在同一网络
2. 输入 IP 地址 `reComputer-R110x.local`（或从路由器查询）
3. 输入用户名 `recomputer`，密码 `12345678`
4. 点击部署，等待安装完成

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping reComputer-R110x.local 测试 |
| SSH 认证失败 | 确认用户名密码正确，首次使用需接显示器完成初始设置 |

---

## 步骤 5: 配置仓库系统 {#warehouse_config type=manual required=true}

![配置演示](gallery/setup_warehous.gif)

部署完成后，打开仓库管理系统完成初始配置：

1. 浏览器访问 `http://服务器IP:2125`（本机部署用 `localhost`）
2. 首次访问会弹出「设置管理员」窗口，填写信息后点击确定
3. 进入系统后，点击左侧「库存列表」导入现有库存（[下载 Excel 模板](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx)）

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 等待 30 秒让服务启动完成 |
| 导入失败 | 检查 Excel 格式是否与模板一致 |
| 忘记管理员密码 | 进入「设备管理」删除此应用（勾选「删除数据」），然后重新部署 |

---

## 步骤 6: 联动智能体 {#mcp_bridge type=manual required=true}

![MCP 端点](gallery/mcp-endpoint.png)

在仓库系统中添加智能体，让 Watcher 能够操作库存：

1. 进入左侧「智能体配置」，点击「添加智能体」，填写名称
2. 在 Endpoint 中粘贴步骤 3 从 MCP Setting 复制的端点地址
3. 点击「保存并启动」
4. 点击智能体卡片上的「MCP 接入点」，刷新状态显示 Connected 即连接成功

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 连接失败 | 检查端点地址是否完整复制，不要包含多余空格 |
| 状态一直显示 Disconnected | 确认 Watcher 已正确绑定到 SenseCraft 平台 |

---

## 步骤 7: 效果体验 {#voice_demo_test type=manual required=false}

![语音入库演示](gallery/xiaozhi-stock-in.png)

试试这些语音指令：

| 说这句话 | Watcher 会做什么 |
|----------|------------------|
| "苹果还有多少？" | 查询苹果的库存数量 |
| "入库 10 箱苹果" | 添加 10 箱苹果到库存 |
| "出库 5 箱香蕉" | 从库存减少 5 箱香蕉 |
| "今天入库了什么？" | 列出今日入库记录 |

说完后可以在仓库网页界面查看库存变化。

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| Watcher 没反应 | 确认智能体已连接（状态显示 Connected） |
| 库存没更新 | 刷新网页查看最新数据 |

---

## 步骤 8: 测试人脸识别 {#face_test type=manual required=false}

在仓管系统中配置人脸识别并验证效果：

1. 浏览器访问 `http://服务器IP:2125`，进入「系统设置」→「人脸识别」
2. 按页面指引完成配置，录入需要识别的人员人脸
3. 确认已对 Watcher 说过「开启人脸识别模式」（见步骤 3）
4. 面对 Watcher 摄像头，识别成功后可在仓管系统中查看识别记录

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 识别不到人脸 | 确认视觉检测固件已烧录，且已对 Watcher 说「开启人脸识别模式」 |
| 识别结果不准 | 在「系统设置 → 人脸识别」重新录入光线充足、正面清晰的人脸照片 |

## 步骤 9: 打开面板 {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

仓库管理面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

### 部署完成

语音仓库管理系统已就绪！

**访问入口：**
- 仓库系统：http://\<服务器IP\>:2125
- SenseCraft 平台：[sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/)

试着说「入库 10 箱苹果」测试语音库存管理。

---

## 套餐: 套餐二A · 升级版（单点位）{#private_cloud}

在套餐一的基础上增加本地高精度人脸识别：语音 AI 使用 [SenseCraft](https://sensecraft.seeed.cc/ai/) 云服务，人脸识别在本地设备上推理，库存与人脸数据留在自己网络内。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | 语音助手，接收语音指令 |
| reComputer R2135-12（Hailo-8）或 Jetson 设备 | 运行仓管系统 + 人脸识别服务 |
| USB-C 数据线 | 烧录 Watcher 固件 |

**部署完成后你可以：**
- 语音操控库存，网页实时查看数据
- 高精度人脸识别，识别记录留在本地

✅ 支持高精度人脸识别（含活体检测），按设备型号自动选择 Hailo / TensorRT 推理镜像

**前提条件：** 需要联网 · [SenseCraft 账号](https://sensecraft.seeed.cc/ai/)（免费注册）

## 步骤 1: 更新小智固件 {#warehouse_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

将语音助手程序写入 Watcher 以启用语音交互。

### 接线

![连接设备](gallery/watcher_usb.png)

1. 用 USB-C 线连接 Watcher 到电脑
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-B** 的 COM 口，macOS / Linux 选编号较大的那个（如 `...53` / `ttyACM1`）
3. 点击烧录按钮

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到串口 | 换一条 USB 线或换个 USB 口 |
| 选错串口（烧录无反应或立刻失败） | 列表里换另一个 CH342 串口再试 |
| 收不到串口数据 | 按住 BOOT 按钮，按一下 RESET，松开 BOOT，然后重试 |
| 烧录失败 | 重新插拔设备再试 |

---

## 步骤 2: 更新视觉检测固件 {#warehouse_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

将视觉检测程序写入 Watcher 的 AI 芯片。

### 接线

![连接设备](gallery/watcher_usb.png)

1. 确保 Watcher 仍通过 USB-C 线连接到电脑（与上一步相同）
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-A** 的 COM 口，macOS / Linux 选编号较小的那个（如 `...51` / `ttyACM0`）—— 和上一步不是同一个口
3. 点击烧录按钮
4. 点击烧录后，按一下设备的重启按钮进入烧录模式

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 设备无响应 | 重新插拔 USB 线 |
| 烧录卡住或失败 | 按重启按钮重试 |
| 反复烧录失败 | 换一条 USB 线或换个 USB 口 |
| 烧录到 99% 失败或中途重启 | 关闭其他占用串口的程序，重新插拔 USB 后重试 |

---

## 步骤 3: 配置 Watcher 设备 {#watcher_config type=manual required=true}

![Agent 配置](gallery/configure_agent.gif)

将 Watcher 连接到 SenseCraft 云平台：

1. 打开 Watcher 电源，按住右上角滚轮按钮 5 秒后松开开机
2. 手机搜索名为"Watcher-XXXX"的 WiFi 热点并连接
3. 连接后浏览器会自动弹出配网页面（如未弹出，手动访问 http://192.168.42.1）
4. 等待约 5 秒完成 WiFi 扫描，从列表中选择 2.4GHz 网络，输入密码，点击"连接"
5. 连接成功后设备自动重启，重启后屏幕显示 6 位验证码
6. 登录 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/device/local/37/)，点击模型里的「SenseCraft Watcher」选择「Watcher Agent」→「Bind Device」，输入 6 位验证码完成绑定
7. 点击「Create」新建一个 Agent，点击 Agent 卡片上的 ⚙ 设置图标，在「角色模板」中选择「库存管理员」，按需调整名称和语言后保存
8. 对 Watcher 说「开启人脸识别模式」，让设备切换到人脸识别检测
9. 在 ⚙ 设置页下滑到最底部，点击「MCP Setting」→「获取 MCP 端点」→「复制端点地址」（步骤 6 联动智能体会用到）

### 故障排除

| 问题 | 解决方法 |
|------|--------|
| 手机搜不到热点 | 确保手机 WiFi 已开启，靠近 Watcher 重试 |
| 配网失败 | Watcher 仅支持 2.4GHz WiFi，检查路由器是否开启 2.4GHz 频段 |
| 找不到 Watcher Agent | 确认已登录 SenseCraft 账号，刷新页面 |

---

## 步骤 4: 仓库管理系统 {#warehouse_2a type=docker_deploy required=true config=devices/warehouse_face_hailo_deploy.yaml}

部署仓管系统和高精度人脸识别服务——同一台设备、一个 Compose 管两个容器。系统会探测设备型号并默认选中对应的人脸识别镜像（Hailo-8 加速卡用 Hailo 镜像，Jetson 用 TensorRT 镜像），也可手动切换。

### 部署目标 {#warehouse_2a_hailo_remote type=remote device=hailo device_name="Hailo-8" config=devices/warehouse_face_hailo_deploy.yaml default=true}

部署到带 Hailo-8 加速卡的设备（reComputer R2135-12 或 Raspberry Pi + Hailo-8）。

### 接线

![接线图](gallery/R1100_connected.png)

1. 将设备接上电源和网线，确保与电脑在同一网络
2. 输入设备 IP 地址（或从路由器查询）
3. 输入 SSH 用户名和密码
4. 点击部署，等待安装完成

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping 测试设备 IP |
| 人脸服务启动失败 | 确认设备已安装 Hailo 驱动（`ls /dev/hailo0` 应存在） |
| 人脸服务反复重启，日志报 `HAILO_INVALID_DRIVER_VERSION` | 宿主机驱动与容器用户态版本不一致。本方案镜像需要 HailoRT **4.21.0**（树莓派官方源的 `hailo-all` 只到 4.20.0）。查看版本：`modinfo -F version hailo_pci`；安装：`curl -sfL https://raw.githubusercontent.com/blakeblackshear/frigate/dev/docker/hailo8l/user_installation.sh \| sudo bash`，然后**重启设备** |

### 部署目标 {#warehouse_2a_jetson_remote type=remote device=jetson device_name="Jetson" config=devices/warehouse_face_jetson_deploy.yaml}

部署到 Jetson 设备（Orin 系列），人脸识别使用 TensorRT 推理。

### 接线

1. 将 Jetson 接上电源和网线，确保与电脑在同一网络
2. 输入设备 IP 地址和 SSH 凭据
3. 点击部署，等待安装完成

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping 测试设备 IP |
| 人脸服务启动失败 | 确认 JetPack 已安装（容器挂载宿主 CUDA/TensorRT），且模型引擎已就位 |

### 部署目标 {#warehouse_2a_hailo_local type=local device=hailo device_name="Hailo-8" config=devices/warehouse_face_hailo_deploy.yaml}

在本机（带 Hailo-8 的设备）直接运行。

### 接线

1. 确保本机 Docker 已安装并运行
2. 点击部署按钮启动服务

### 部署目标 {#warehouse_2a_jetson_local type=local device=jetson device_name="Jetson" config=devices/warehouse_face_jetson_deploy.yaml}

在本机（Jetson 设备）直接运行。

### 接线

1. 确保本机 Docker 已安装并运行
2. 点击部署按钮启动服务

---

## 步骤 5: 配置仓库系统 {#warehouse_config_private_cloud type=manual required=true}

![配置演示](gallery/setup_warehous.gif)

部署完成后，打开仓库管理系统完成初始配置：

1. 浏览器访问 `http://服务器IP:2125`（本机部署用 `localhost`）
2. 首次访问会弹出「设置管理员」窗口，填写信息后点击确定
3. 进入系统后，点击左侧「库存列表」导入现有库存（[下载 Excel 模板](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx)）

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 等待 30 秒让服务启动完成 |
| 导入失败 | 检查 Excel 格式是否与模板一致 |
| 忘记管理员密码 | 进入「设备管理」删除此应用（勾选「删除数据」），然后重新部署 |

---

## 步骤 6: 联动智能体 {#agent_config type=manual required=true}

![MCP 端点](gallery/mcp-endpoint.png)

在仓库系统中添加智能体，让 Watcher 能够操作库存：

1. 浏览器访问 `http://服务器IP:2125`（本机部署用 `localhost`）
2. 进入左侧「智能体配置」，点击「添加智能体」，填写名称
3. 在 Endpoint 中粘贴步骤 3 从 MCP Setting 复制的端点地址
4. 点击「保存并启动」
5. 点击智能体卡片上的「MCP 接入点」，刷新状态显示 Connected 即连接成功

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 连接失败 | 检查端点地址是否完整复制，不要包含多余空格 |
| 状态一直显示 Disconnected | 确认 Watcher 已正确绑定到 SenseCraft 平台 |

---

## 步骤 7: 效果体验 {#demo_private_cloud type=manual required=false}

![语音入库演示](gallery/xiaozhi-stock-in.png)

试试这些语音指令：

| 说这句话 | Watcher 会做什么 |
|----------|------------------|
| "苹果还有多少？" | 查询苹果的库存数量 |
| "入库 10 箱苹果" | 添加 10 箱苹果到库存 |
| "出库 5 箱香蕉" | 从库存减少 5 箱香蕉 |
| "今天入库了什么？" | 列出今日入库记录 |

说完后可以在仓库网页界面查看库存变化。

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| Watcher 没反应 | 确认智能体已连接（状态显示 Connected） |
| 库存没更新 | 刷新网页查看最新数据 |

## 步骤 8: 测试人脸识别 {#face_test_2a type=manual required=false}

在仓管系统中配置人脸识别并验证效果（本套餐为高精度识别，含活体检测）：

1. 浏览器访问 `http://服务器IP:2125`，进入「系统设置」→「人脸识别」
2. 按页面指引完成配置，录入需要识别的人员人脸
3. 确认已对 Watcher 说过「开启人脸识别模式」（见步骤 3）
4. 面对 Watcher 摄像头，识别成功后可在仓管系统中查看识别记录；用照片对着摄像头应被活体检测拒绝

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 识别不到人脸 | 确认视觉检测固件已烧录，且已对 Watcher 说「开启人脸识别模式」 |
| 人脸服务无响应 | 访问 `http://服务器IP:8001/health` 检查服务状态，确认部署步骤中 face-rec 容器已启动 |
| 识别结果不准 | 在「系统设置 → 人脸识别」重新录入光线充足、正面清晰的人脸照片 |

## 步骤 9: 打开面板 {#dashboard_private_cloud type=web_dashboard required=true config=devices/dashboard.yaml}

仓库管理面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

### 部署完成

私有云仓管系统已就绪！

**访问入口：**
- 仓库系统：http://\<服务器IP\>:2125
- 人脸识别服务：http://\<服务器IP\>:8001/health

库存与人脸数据留在自己网络内。试着说「苹果还有多少」测试。

---

## 套餐: 套餐二B · 升级版（多点位）{#private_cloud_multi}

自建语音 AI 服务器，调用云端 API（DeepSeek、OpenAI 等）处理语音。数据不经过第三方平台，只有 API 调用。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | 语音助手，接收语音指令 |
| reComputer R2135-12（Hailo-8） | 运行仓管系统 + 人脸识别 + 语音 AI 服务 |
| reComputer Super J4012 | 运行语音识别与合成（OpenVoiceStream），支持多路语音并发 |

**部署完成后你可以：**
- 完全掌控数据——库存信息留在自己网络内
- 自由选择 AI 模型（DeepSeek、GPT-4、通义千问等）
- 自定义语音助手的提示词和行为

✅ 支持人脸识别

**前提条件：** 需要联网 · 需要 LLM API 密钥

## 步骤 1: 更新小智固件 {#warehouse_esp32_2b type=esp32_usb required=true config=devices/watcher_esp32.yaml}

将语音助手程序写入 Watcher 以启用语音交互。本套餐的语音识别与合成由本地服务器处理，固件需要指向自建服务器（步骤 7 会做绑定）。

### 接线

![连接设备](gallery/watcher_usb.png)

1. 用 USB-C 线连接 Watcher 到电脑
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-B** 的 COM 口，macOS / Linux 选编号较大的那个（如 `...53` / `ttyACM1`）
3. 点击烧录按钮

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到串口 | 换一条 USB 线或换个 USB 口 |
| 选错串口（烧录无反应或立刻失败） | 列表里换另一个 CH342 串口再试 |
| 收不到串口数据 | 按住 BOOT 按钮，按一下 RESET，松开 BOOT，然后重试 |
| 烧录失败 | 重新插拔设备再试 |

---

## 步骤 2: 更新视觉检测固件 {#warehouse_himax_2b type=himax_usb required=true config=devices/watcher_himax.yaml}

将视觉检测程序写入 Watcher 的 AI 芯片，用于人脸识别和物体检测。

### 接线

![连接设备](gallery/watcher_usb.png)

1. 确保 Watcher 仍通过 USB-C 线连接到电脑（与上一步相同）
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-A** 的 COM 口，macOS / Linux 选编号较小的那个（如 `...51` / `ttyACM0`）—— 和上一步不是同一个口
3. 点击烧录按钮
4. 点击烧录后，按一下设备的重启按钮进入烧录模式

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 设备无响应 | 重新插拔 USB 线 |
| 烧录卡住或失败 | 按重启按钮重试 |
| 反复烧录失败 | 换一条 USB 线或换个 USB 口 |
| 烧录到 99% 失败或中途重启 | 关闭其他占用串口的程序，重新插拔 USB 后重试 |

---

## 步骤 3: 仓库管理系统 {#warehouse_2b type=docker_deploy required=true config=devices/warehouse_face_hailo_deploy.yaml}

部署库存管理服务，支持语音操控和网页看板。

### 部署目标 {#warehouse_2b_local type=local config=devices/warehouse_face_hailo_deploy.yaml}

在本机运行仓库管理服务。

### 接线

1. 确保本机 Docker 已安装并运行
2. 点击部署按钮启动服务

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 检查 2125 端口是否被其他服务使用 |
| Docker 未运行 | 启动 Docker Desktop 后重试 |

### 部署目标 {#warehouse_2b_remote type=remote config=devices/warehouse_face_hailo_deploy.yaml default=true}

部署到 reComputer R2135-12 边缘网关（带 Hailo-8，人脸识别需要它）。

### 接线

![接线图](gallery/R1100_connected.png)

1. 将 J4012 接上电源和网线，确保与电脑在同一网络
2. 从路由器查询 J4012 的 IP 地址，输入到地址栏
3. 输入用户名 `recomputer`，密码 `12345678`
4. 点击部署，等待安装完成

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，确认 IP 地址正确 |
| SSH 认证失败 | 确认用户名密码正确，首次使用需接显示器完成初始设置 |

---

## 步骤 4: 配置仓库系统 {#warehouse_config_private_cloud_multi type=manual required=true}

![配置演示](gallery/setup_warehous.gif)

部署完成后，打开仓库管理系统完成初始配置：

1. 浏览器访问 `http://服务器IP:2125`（本机部署用 `localhost`）
2. 首次访问会弹出「设置管理员」窗口，填写信息后点击确定
3. 进入系统后，点击左侧「库存列表」导入现有库存（[下载 Excel 模板](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx)）

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 等待 30 秒让服务启动完成 |
| 导入失败 | 检查 Excel 格式是否与模板一致 |
| 忘记管理员密码 | 进入「设备管理」删除此应用（勾选「删除数据」），然后重新部署 |

---

## 步骤 5: 语音服务 {#voice_stack_private_cloud_multi type=docker_deploy required=true config=devices/ovs_voice_deploy.yaml}

在 J4012 上部署 OpenVoiceStream，提供语音识别、语音合成与声纹能力。下一步在 R2135-12 上部署的语音 AI 服务会连接到它。

本套餐只在本地跑语音，大模型调用云端 API，所以不部署本地大模型。

### 部署目标 {#voice_stack_local type=local config=devices/ovs_voice_deploy.yaml}

直接在本机（运行 SenseCraft Solution 的这台设备）上部署，仅当本机就是 J4012 时适用。模型会自动下载，无需准备离线包。

### 部署目标 {#voice_stack_remote type=remote config=devices/ovs_voice_deploy.yaml default=true}

### 接线

1. 将 J4012 接上电源和网线
2. 若部署到另一台设备，输入其 IP 地址和 SSH 凭据
3. 点击部署，等待模型下载与服务启动

部署完成后服务监听 **8621**。**记下这台机器的局域网 IP，下一步填「语音服务地址」要用。**

> 即使语音服务与下一步装在同一台机器上，也**不能填 `127.0.0.1`** —— 该地址由容器读取，容器里的 `127.0.0.1` 指向容器自己，连不到宿主服务。

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 首次部署很久没反应 | 正常。首次启动要下载约 5GB 模型，走 hf-mirror 镜像站，视网络可能要十几分钟 |
| 磁盘空间不足 | 该步骤需要至少 15GB 可用空间 |
| 提示 NVIDIA runtime 不可用 | 确认已安装 nvidia-container-toolkit 并重启 Docker |
| 部署中止，提示容器名冲突 | 设备上已手工装过语音服务，或装了另一个套餐的语音步骤。两者抢同一个容器名和 8621 端口，不能共存。按提示 `docker rm -f` 掉原有容器再重试，数据卷不受影响 |
| 部署完但 8621 不通 | 模型仍在加载。`docker logs seeed-voice-v091` 查看进度，`curl localhost:8621/readyz` 返回 200 才算就绪 |

---

## 步骤 6: 语音 AI 服务 {#voice_service_private_cloud_multi type=docker_deploy required=true config=devices/xiaozhi_console_deploy.yaml}

![模型配置](gallery/console-tts-list.jpg)

本地模型会排在各列表最前面，无需翻页。

部署语音 AI 服务与智控台，为 Watcher 提供语音交互能力。部署时选择「**私有云方案**」，填写：

- **语音服务地址**：上一步部署 OpenVoiceStream 的 **J4012 局域网 IP**，端口 8621（不能填 `127.0.0.1`，该地址由容器读取）
- **LLM API 地址 / 模型名称 / 密钥**：云端大模型信息（如 DeepSeek、通义千问）

语音识别与合成在本地，只有大模型走云端。部署完成后会自动配好地址与 MCP 接入点。


### 部署目标 {#voice_local type=local config=devices/xiaozhi_console_deploy.yaml}

### 接线

1. 确保 Docker 已安装并运行
2. 点击部署按钮启动服务

### 部署目标 {#voice_remote type=remote config=devices/xiaozhi_console_deploy.yaml default=true}

### 接线

1. 输入 J4012 的 IP 地址和 SSH 凭据
2. 点击部署，等待安装完成

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 镜像拉取失败 | 检查网络连接，或配置 Docker 镜像加速 |
| 端口被占用 | 检查 18000、18002、18003、18004 端口是否被其他服务使用 |
| API 调用失败 | 检查 API 密钥是否正确，余额是否充足 |

---

## 步骤 7: 配置 Watcher 连接本地服务器 {#watcher_config_private_cloud_multi type=manual required=true}

把 Watcher 配上 WiFi，并让它连到刚部署的本地语音服务器。

> 语音识别与合成都在本地运行，Watcher **不需要**绑定 SenseCraft 云平台。

### 接线

1. 打开 Watcher 电源，按住右上角滚轮按钮 5 秒后松开开机
2. 手机搜索名为 `Watcher-XXXX` 的 WiFi 热点并连接
3. 连接后浏览器会自动弹出配网页面（如未弹出，手动访问 `http://192.168.42.1`）
4. **先别急着连 WiFi** —— 在页面顶部点击「**高级选项**」，在 OTA 地址栏填入：

   ```
   http://<J4012 的 IP>:18002/xiaozhi/ota/
   ```

   点击保存。这一步决定了设备连哪台服务器，漏了就会去连默认的公有服务器。
5. 回到配网页面，等待约 5 秒完成 WiFi 扫描，从列表中选择 **2.4GHz** 网络，输入密码，点击「连接」
6. 连接成功后设备自动重启
7. 用浏览器打开 `http://<J4012 的 IP>:18002/xiaozhi/ota/` 自检，显示「OTA 接口运行正常」即说明服务端就绪

> **启用人脸识别**：人脸识别服务已随步骤 3 的仓管系统一并部署（独立容器，
> 监听 8001）。配网完成后对 Watcher 说「**开启人脸识别模式**」，再到仓管系统
> 「系统设置 → 人脸识别」录入人员照片即可。不说这句话，Watcher 不会上送人脸帧。

### 故障排除

| 问题 | 解决方法 |
|------|--------|
| 手机搜不到热点 | 确保手机 WiFi 已开启，靠近 Watcher 重试 |
| 配网失败 | Watcher 仅支持 2.4GHz WiFi，检查路由器是否开启 2.4GHz 频段 |
| OTA 地址页面显示「运行不正常」 | 说明智控台里的 `server.websocket` 没配好。部署脚本会自动写入，若仍异常请登录智控台「参数管理」检查该项 |
| 设备重启后没反应 | 确认 OTA 地址填的是**服务器 IP**而不是 localhost，且设备与服务器在同一网络 |
| 想改回默认服务器 | 重新进入配网模式，在高级选项里清空 OTA 地址 |

---

## 步骤 8: 创建智能体并联动仓库 {#agent_config_private_cloud_multi type=manual required=true}

在智控台创建智能体，再把它的 MCP 接入点填进仓库系统，让语音能操作库存。
> **部署时填的地址如需改动**：在智控台「模型配置 → 语音合成 → OpenVoiceStream → 修改」
> 里改红框处的基础 URL。
>
> ![模型配置项](gallery/console-ovs-form-annotated.png)
>
> - 🔴 **基础 URL**：语音服务地址，格式 `http://<设备IP>:8621`
> - 🔵 **音色**：填好基础 URL 后展开即自动从设备拉取，无需手填
> - 🔵 **API Key**：仅当语音服务开启了 `OVS_API_KEYS` 时才需要填，否则留空


### 接线

**A. 登录智控台**

1. 浏览器访问 `http://<J4012 的 IP>:18002`
2. 用户名 `admin`，初始密码 `Seeed@2026`
3. ⚠️ **首次登录后请立即修改密码**（右上角账号菜单 → 修改密码）

   ![修改密码](gallery/console-change-password.jpg)

**B. 配置云端大模型**

4. 进入「模型配置 → 大语言模型」，找到部署时填写的模型，确认 API 地址、模型名称、密钥无误

**C. 创建智能体**

5. 点击「新建智能体」，角色模板选择「**仓库智能助手**」——该模板已预置仓库场景的提示词与本地语音模型
6. 保存后进入该智能体的「角色配置」页，把「主语言模型」切换成上一步配好的云端模型
7. 如需调整音色：点击「OVS Speaker」下拉，会实时从语音服务拉取可用音色

**D. 取 MCP 接入点地址**

8. 在角色配置页点击「**编辑功能**」按钮
9. 在弹窗中找到「MCP 接入点」，点击复制该智能体的专属地址

   > 每个智能体的地址不同（地址里的 token 是按智能体身份加密生成的），多点位部署时别复制混了。

**E. 填进仓库系统**

10. 浏览器访问 `http://<J4012 的 IP>:2125`
11. 进入左侧「智能体配置」，点击「添加智能体」，填写名称
12. 在 Endpoint 中粘贴刚才复制的接入点地址
13. 点击「保存并启动」
14. 点击智能体卡片上的「MCP 接入点」，刷新状态显示 **Connected** 即连接成功

> **多点位提示**：每台 Watcher 对应一个智能体，重复 C~E 即可。各智能体的 MCP 接入点地址互不相同。

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 打不开智控台 | 首次启动要跑数据库迁移，等 1~2 分钟后重试 |
| 忘记 admin 密码 | 重新部署语音 AI 服务并勾选清除数据，密码会恢复默认 |
| 角色模板里没有「仓库智能助手」 | 说明用的不是本方案的镜像，检查语音 AI 服务是否部署成功 |
| MCP 接入点是空的 | 智控台「参数管理」里检查 `server.mcp_endpoint`，部署脚本会自动填写 |
| 状态一直显示 Disconnected | 检查端点地址是否完整复制（含 token，不要有多余空格） |
| 大模型不响应 | 检查 API 密钥是否有效、账户是否欠费 |

---

## 步骤 9: 效果体验 {#demo_private_cloud_multi type=manual required=false}

![语音入库演示](gallery/xiaozhi-stock-in.png)

试试这些语音指令：

| 说这句话 | Watcher 会做什么 |
|----------|------------------|
| "苹果还有多少？" | 查询苹果的库存数量 |
| "入库 10 箱苹果" | 添加 10 箱苹果到库存 |
| "出库 5 箱香蕉" | 从库存减少 5 箱香蕉 |
| "今天入库了什么？" | 列出今日入库记录 |

说完后可以在仓库网页界面查看库存变化。

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| Watcher 没反应 | 确认智能体已连接（状态显示 Connected） |
| 库存没更新 | 刷新网页查看最新数据 |

## 步骤 10: 打开面板 {#dashboard_private_cloud_multi type=web_dashboard required=true config=devices/dashboard.yaml}

仓库管理面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

### 部署完成

私有云仓管系统已就绪！

**访问入口：**
- 仓库系统：http://\<服务器IP\>:2125
- 智控台：http://\<服务器IP\>:18002

数据留在自己网络内。试着说「苹果还有多少」测试。

---

## 套餐: 套餐三 · 顶配版 {#edge_computing}

所有服务本地运行，包括大语言模型和语音合成——完全不需要联网。适合断网环境或对数据合规要求严格的场景。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | 语音助手，接收语音指令 |
| reComputer R2135-12（Hailo-8） | 运行仓管系统 + 人脸识别 + 语音 AI 服务 |
| reComputer Robotics J5011 | 运行本地大模型，完全离线 |

**部署完成后你可以：**
- 100% 离线运行——没有网络也能用
- 数据完全不出厂区/办公区
- 本地大模型响应速度约 16 tok/s

✅ 支持人脸识别

**前提条件：** 需要 reComputer Robotics J5011 · 首次部署需要网络下载镜像

## 步骤 1: 更新小智固件 {#warehouse_esp32_t3 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

将语音助手程序写入 Watcher 以启用语音交互。本套餐的语音全部由本地服务器处理，固件需要指向自建服务器（步骤 7 会做绑定）。

### 接线

![连接设备](gallery/watcher_usb.png)

1. 用 USB-C 线连接 Watcher 到电脑
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-B** 的 COM 口，macOS / Linux 选编号较大的那个（如 `...53` / `ttyACM1`）
3. 点击烧录按钮

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到串口 | 换一条 USB 线或换个 USB 口 |
| 选错串口（烧录无反应或立刻失败） | 列表里换另一个 CH342 串口再试 |
| 收不到串口数据 | 按住 BOOT 按钮，按一下 RESET，松开 BOOT，然后重试 |
| 烧录失败 | 重新插拔设备再试 |

---

## 步骤 2: 更新视觉检测固件 {#warehouse_himax_t3 type=himax_usb required=true config=devices/watcher_himax.yaml}

将视觉检测程序写入 Watcher 的 AI 芯片，用于人脸识别和物体检测。

### 接线

![连接设备](gallery/watcher_usb.png)

1. 确保 Watcher 仍通过 USB-C 线连接到电脑（与上一步相同）
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-A** 的 COM 口，macOS / Linux 选编号较小的那个（如 `...51` / `ttyACM0`）—— 和上一步不是同一个口
3. 点击烧录按钮
4. 点击烧录后，按一下设备的重启按钮进入烧录模式

### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 设备无响应 | 重新插拔 USB 线 |
| 烧录卡住或失败 | 按重启按钮重试 |
| 反复烧录失败 | 换一条 USB 线或换个 USB 口 |
| 烧录到 99% 失败或中途重启 | 关闭其他占用串口的程序，重新插拔 USB 后重试 |

---

## 步骤 3: 仓库管理系统 {#warehouse_t3 type=docker_deploy required=true config=devices/warehouse_face_hailo_deploy.yaml}

部署库存管理服务，支持语音操控和网页看板。

### 部署目标 {#warehouse_t3_local type=local config=devices/warehouse_face_hailo_deploy.yaml}

在本机运行仓库管理服务。

### 接线

1. 确保本机 Docker 已安装并运行
2. 点击部署按钮启动服务

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 端口被占用 | 检查 2125 端口是否被其他服务使用 |
| Docker 未运行 | 启动 Docker Desktop 后重试 |

### 部署目标 {#warehouse_t3_remote type=remote config=devices/warehouse_face_hailo_deploy.yaml default=true}

部署到 reComputer R2135-12 边缘计算设备。

### 接线

![接线图](gallery/R1100_connected.png)

1. 将 R2135-12 接上电源和网线，确保与电脑在同一网络
2. 输入 IP 地址 `reComputer-R110x.local`（或从路由器查询）
3. 输入用户名 `recomputer`，密码 `12345678`
4. 点击部署，等待安装完成

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 连接超时 | 检查网线是否插好，用 ping reComputer-R110x.local 测试 |
| SSH 认证失败 | 确认用户名密码正确，首次使用需接显示器完成初始设置 |

---

## 步骤 4: 配置仓库系统 {#warehouse_config_edge_computing type=manual required=true}

![配置演示](gallery/setup_warehous.gif)

部署完成后，打开仓库管理系统完成初始配置：

1. 浏览器访问 `http://服务器IP:2125`（本机部署用 `localhost`）
2. 首次访问会弹出「设置管理员」窗口，填写信息后点击确定
3. 进入系统后，点击左侧「库存列表」导入现有库存（[下载 Excel 模板](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx)）

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 页面打不开 | 等待 30 秒让服务启动完成 |
| 导入失败 | 检查 Excel 格式是否与模板一致 |
| 忘记管理员密码 | 进入「设备管理」删除此应用（勾选「删除数据」），然后重新部署 |

---

## 步骤 5: 语音 AI 栈 {#jetson_ai type=docker_deploy required=true config=devices/ovs_jetson_deploy.yaml}

在 Jetson 上部署 OpenVoiceStream（语音识别 + 语音合成 + 声纹）和 EdgeLLM（对话大模型 Qwen3.5-4B）。下一步的语音服务会连接到这两个地址。

### 部署目标 {#jetson_ai_local type=local config=devices/ovs_jetson_deploy.yaml}

直接在本机 Jetson（运行 SenseCraft Solution 的这台设备）上部署。模型会自动下载，无需准备离线包。

### 部署目标 {#jetson_remote type=remote config=devices/ovs_jetson_deploy.yaml default=true}

### 接线

1. 将 Jetson（reComputer Robotics J5011）接上电源和网线
2. 输入 Jetson 的 IP 地址和 SSH 凭据
3. 点击部署，等待模型下载与服务启动

部署完成后会起两个容器：语音服务在 **8621**，大模型在 **8000**。**记下这台 Jetson 的 IP，下一步要填。**

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 确认 Jetson 已开机，检查 IP 地址是否正确 |
| 首次部署很久没反应 | 正常。首次启动要下载约 10GB 的模型与推理引擎，走 hf-mirror 镜像站，视网络可能要十几分钟 |
| 磁盘空间不足 | 该步骤需要至少 25GB 可用空间 |
| 提示 NVIDIA runtime 不可用 | 在 Jetson 上确认已安装 nvidia-container-toolkit 并重启 Docker |
| 部署中止，提示容器名冲突 | 设备上已手工装过语音服务（如用 openvoicestream 的 install.sh）。两者抢同一个容器名和 8621 端口，不能共存。按提示 `docker rm -f` 掉原有容器再重试，数据卷不受影响，模型无需重新下载 |

---
## 步骤 6: 语音 AI 服务 {#voice_service_edge_computing type=docker_deploy required=true config=devices/xiaozhi_console_deploy.yaml}

![模型配置](gallery/console-tts-list.jpg)

本地模型会排在各列表最前面，无需翻页。

在 R2135-12 上部署语音 AI 服务与智控台。部署时选择「**边缘计算方案**」，并填写两个地址：

- **语音服务地址**：上一步部署 OpenVoiceStream 的 Jetson 局域网 IP，端口 8621（不能填 `127.0.0.1`，该地址由容器读取）
- **本地 LLM 地址**：上一步记下的 Jetson 局域网 IP，端口 8000（与语音服务同机时可留空）

部署完成后会自动配好模型地址、设备接入地址和 MCP 接入点。


### 部署目标 {#voice_local type=local config=devices/xiaozhi_console_deploy.yaml}

### 接线

1. 确保 Docker 已安装并运行
2. 点击部署按钮启动服务

### 部署目标 {#voice_remote type=remote config=devices/xiaozhi_console_deploy.yaml default=true}

### 接线

1. 输入 R2135-12 的 IP 地址和 SSH 凭据
2. 点击部署，等待安装完成

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 无法连接 Jetson | 检查 R2135-12 和 Jetson 是否在同一网络 |
| 响应很慢 | 确认 Jetson 服务已启动，访问 `http://Jetson-IP:8000/v1/models` 检查 |

---

## 步骤 7: 配置 Watcher 连接本地服务器 {#watcher_config_edge_computing type=manual required=true}

把 Watcher 配上 WiFi，并让它连到刚部署的本地语音服务器（而不是云端）。

> 本套餐是纯局域网方案，Watcher **不需要**绑定 SenseCraft 云平台。

### 接线

1. 打开 Watcher 电源，按住右上角滚轮按钮 5 秒后松开开机
2. 手机搜索名为 `Watcher-XXXX` 的 WiFi 热点并连接
3. 连接后浏览器会自动弹出配网页面（如未弹出，手动访问 `http://192.168.42.1`）
4. **先别急着连 WiFi** —— 在页面顶部点击「**高级选项**」，在 OTA 地址栏填入上一步部署完成后显示的地址：

   ```
   http://<语音服务器IP>:18002/xiaozhi/ota/
   ```

   点击保存。这一步决定了设备连哪台服务器，漏了就会去连默认的公有服务器。
5. 回到配网页面，等待约 5 秒完成 WiFi 扫描，从列表中选择 **2.4GHz** 网络，输入密码，点击「连接」
6. 连接成功后设备自动重启
7. 用浏览器打开 `http://<语音服务器IP>:18002/xiaozhi/ota/` 自检，显示「OTA 接口运行正常」即说明服务端就绪

> **启用人脸识别**：人脸识别服务已随步骤 3 的仓管系统一并部署（独立容器，
> 监听 8001）。配网完成后对 Watcher 说「**开启人脸识别模式**」，再到仓管系统
> 「系统设置 → 人脸识别」录入人员照片即可。不说这句话，Watcher 不会上送人脸帧。

### 故障排除

| 问题 | 解决方法 |
|------|--------|
| 手机搜不到热点 | 确保手机 WiFi 已开启，靠近 Watcher 重试 |
| 配网失败 | Watcher 仅支持 2.4GHz WiFi，检查路由器是否开启 2.4GHz 频段 |
| OTA 地址页面显示「运行不正常」 | 说明智控台里的 `server.websocket` 没配好。部署脚本会自动写入，若仍异常请登录智控台「参数管理」检查该项 |
| 设备重启后没反应 | 确认 OTA 地址填的是**服务器 IP**而不是 localhost，且设备与服务器在同一网络 |
| 想改回默认服务器 | 重新进入配网模式，在高级选项里清空 OTA 地址 |

---

## 步骤 8: 创建智能体并联动仓库 {#agent_config_edge_computing type=manual required=true}

在智控台创建智能体，再把它的 MCP 接入点填进仓库系统，让语音能操作库存。
> **部署时填的地址如需改动**：在智控台「模型配置 → 语音合成 → OpenVoiceStream → 修改」
> 里改红框处的基础 URL。
>
> ![模型配置项](gallery/console-ovs-form-annotated.png)
>
> - 🔴 **基础 URL**：语音服务地址，格式 `http://<设备IP>:8621`
> - 🔵 **音色**：填好基础 URL 后展开即自动从设备拉取，无需手填
> - 🔵 **API Key**：仅当语音服务开启了 `OVS_API_KEYS` 时才需要填，否则留空


### 接线

**A. 登录智控台**

1. 浏览器访问 `http://<语音服务器IP>:18002`
2. 用户名 `admin`，初始密码 `Seeed@2026`
3. ⚠️ **首次登录后请立即修改密码**（右上角账号菜单 → 修改密码）

   ![修改密码](gallery/console-change-password.jpg)

**B. 创建智能体**

4. 点击「新建智能体」，角色模板选择「**仓库智能助手**」——该模板已预置仓库场景的提示词，并已选好本地的语音识别、语音合成、大语言模型
5. 保存后进入该智能体的「角色配置」页
6. 如需调整音色：点击「OVS Speaker」下拉，会实时从语音服务器拉取可用音色

**C. 取 MCP 接入点地址**

7. 在角色配置页点击「**编辑功能**」按钮
8. 在弹窗中找到「MCP 接入点」，点击复制该智能体的专属地址

   > 每个智能体的地址不同（地址里的 token 是按智能体身份加密生成的），别复制错。

**D. 填进仓库系统**

9. 浏览器访问 `http://<仓库服务器IP>:2125`
10. 进入左侧「智能体配置」，点击「添加智能体」，填写名称
11. 在 Endpoint 中粘贴刚才复制的接入点地址
12. 点击「保存并启动」
13. 点击智能体卡片上的「MCP 接入点」，刷新状态显示 **Connected** 即连接成功

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 打不开智控台 | 首次启动要跑数据库迁移，等 1~2 分钟后重试 |
| 忘记 admin 密码 | 重新部署语音 AI 服务并勾选清除数据，密码会恢复默认 |
| 角色模板里没有「仓库智能助手」 | 说明用的不是本方案的镜像，检查语音 AI 服务是否部署成功 |
| MCP 接入点是空的 | 智控台「参数管理」里检查 `server.mcp_endpoint`，部署脚本会自动填写 |
| 状态一直显示 Disconnected | 检查端点地址是否完整复制（含 token，不要有多余空格），并确认仓库系统与语音服务器网络互通 |
| 音色下拉拉不到内容 | 检查「模型配置 → 语音合成」里的地址是否指向真实的语音服务设备 |

---

## 步骤 9: 效果体验 {#demo_edge_computing type=manual required=false}

![语音入库演示](gallery/xiaozhi-stock-in.png)

试试这些语音指令：

| 说这句话 | Watcher 会做什么 |
|----------|------------------|
| "苹果还有多少？" | 查询苹果的库存数量 |
| "入库 10 箱苹果" | 添加 10 箱苹果到库存 |
| "出库 5 箱香蕉" | 从库存减少 5 箱香蕉 |
| "今天入库了什么？" | 列出今日入库记录 |

说完后可以在仓库网页界面查看库存变化。

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| Watcher 没反应 | 确认智能体已连接（状态显示 Connected） |
| 库存没更新 | 刷新网页查看最新数据 |

## 步骤 10: 打开面板 {#dashboard_edge_computing type=web_dashboard required=true config=devices/dashboard.yaml}

仓库管理面板已经运行。点击下方按钮在浏览器中打开。

### 故障排查
| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 请确认前一个部署步骤已经成功，服务运行正常 |
| 主机/端口错误 | 如果你部署到远程设备，请用实际的设备 IP 更新地址 |

### 部署完成

全离线仓管系统已就绪！

**访问入口：**
- 仓库系统：http://\<服务器IP\>:2125
- 智控台：http://\<服务器IP\>:18002
- 大模型接口：http://\<Jetson-IP\>:8000/v1/models

部署完成后 100% 离线运行，无需联网。
