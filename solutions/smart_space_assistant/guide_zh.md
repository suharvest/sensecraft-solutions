## 套餐: 语音对话与智能体接入 {#voice_agent}

用最少的硬件（一台 SenseCAP Watcher 和一根 USB-C 线）开箱体验流式语音对话：将 Watcher 连入网络并接入 SenseCraft AI 云平台，配置智能体角色，通过 MCP 协议联动工作站，直接开始自然语言对话。

- **设备：** SenseCAP Watcher，USB-C 数据线；可选一台工位电脑或边缘主机（如 reComputer R1100）。
- **网络：** 2.4 GHz WiFi。
- **账号：** [SenseCraft AI 平台账号](https://sensecraft.seeed.cc/ai/)（免费注册）或 [小智 App](https://github.com/78/xiaozhi-esp32)。

## 步骤 1: 烧录小智固件 {#voice_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

将小智语音主控固件写入 Watcher 以启用语音交互。

### 接线与烧录

![连接设备](gallery/watcher.svg)

1. 用 USB-C 数据线将 Watcher 连接到电脑
2. 串口通常会自动选好；如果没选上，Windows 选名字里带 **SERIAL-B** 的 COM 口，macOS / Linux 选编号较大的那个（如 `...53` / `ttyACM1`）
3. 点击烧录按钮完成固件写入

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到串口 | 换一条 USB-C 数据线（确保支持数据传输，非仅充电线）或换个 USB 口 |
| 选错串口（烧录无反应或立刻失败） | 列表里换另一个 CH342 串口再试 |
| 烧录卡住或失败 | 按住 BOOT 键，按一下 RESET 键，松开 BOOT 键，重新点击烧录 |

---

## 步骤 2: Watcher 配网与获取 6 位绑定码 {#voice_network type=manual required=true}

1. 打开 Watcher 电源，长按滚轮按钮开机
2. 手机连接 Watcher 发出的热点（Watcher-XXXX），在弹出的配网页中选择 2.4 GHz WiFi 并输入密码
3. 连接成功后 Watcher 自动重启，屏幕上会显示专属的 **6 位设备绑定码**

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 看不到 Watcher-XXXX 热点或配网失败 | Watcher 仅支持 2.4 GHz Wi-Fi；请使用 2.4 GHz 网络并重新通过手机热点配网。 |
| 屏幕上没有 6 位绑定码 | 绑定码在 Watcher 联网并重启后显示，请等待重启完成。 |

---

## 步骤 3: 绑定 SenseCraft AI 并开启语音对话 {#voice_agent_setup type=manual required=true verify=true}

1. 浏览器登录 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/device/local/37/)
2. 在模型列表中找到「SenseCAP Watcher」，选择「Watcher Agent」并点击「Bind Device」
3. 输入 Watcher 屏幕上的 6 位验证码完成硬件绑定
4. 点击「Create」新建专属智能体（如工位助手、迎宾接待或仓管员），按需设定 System Prompt 与交互音色
5. 对 Watcher 说出唤醒词「小智小智」或直接开始对话，即可体验低延迟流式语音问答
6. （可选联动工作站）在 Agent 页面底部获取「MCP Setting」端点，填入仓管系统或本地服务，Watcher 即可通过 MCP 工具直接读写业务数据

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 绑定码被拒绝 | 在“模型 -> SenseCAP Watcher -> Watcher Agent -> 绑定设备”中输入 Watcher 屏幕当前显示的 6 位码。 |
| 唤醒词无响应 | 清晰说出“小智小智”，或直接说话；确认 Watcher 已连接 2.4 GHz Wi-Fi。 |
| 找不到 MCP 接入点 | 打开智能体设置并向下滚动到“MCP 设置”。 |

---

## 套餐: 视觉主动唤醒与参数配置 {#vision_wake}

在语音对话的基础上，让 Watcher 拥有“眼睛”：开启视觉主动唤醒，摄像头看到人出现在面前时主动开口打招呼并进入对话；通过语音随时讲解与调节视觉感知核心参数。

### 前提条件

- SenseCAP Watcher 已刷入小智固件、连入 2.4 GHz WiFi 并完成 SenseCraft AI / 小智平台 6 位码绑定（可先完成「套餐: 语音对话与智能体接入」）。语音主动唤醒与参数配置需要设备具备活跃的语音对话能力。

## 步骤 1: 开启人脸检测并体验主动打招呼 {#vision_wake_intro type=manual required=true verify=true}

开启人脸检测，走到 Watcher 面前触发主动问候。

### 接线

1. 确认视觉检测模式：对 Watcher 说出“开启人脸检测”或“把视觉模式设为 1”（`self.vision.mode: 1`），Watcher 确认进入端侧人脸检测模式。
2. 将已配网的 Watcher 放置在桌面或工位正对人脸的高度（距离约 0.5 ~ 1.5 米）。
3. 走到 Watcher 面前并停留：
   - 摄像头检测到有人出现并停留超过持续确认时间（默认 3 秒）时，Watcher 屏幕切换为灵动表情，主动开口向你打招呼（如“你好呀，看到你了！”），直接进入对话监听状态，无需呼唤唤醒词。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 没有主动问候 | 确认视觉模式 1 已开启（说“开启人脸检测”），并在距离约 0.5-1.5 米处停留超过持续确认时间（默认 3 秒）。 |
| 一次对话后不再问候 | 对话结束后有冷却间隔；等待其结束，或在下一步缩短该间隔。 |

---

## 步骤 2: 语音讲解与微调检测参数 {#vision_wake_params type=manual required=true}

在对话中，试着询问 Watcher 它的视觉参数，Watcher 会调用内部工具并为你讲解与设置：

| 对 Watcher 说 | 效果 |
|---|---|
| "查询视觉参数" | 汇报当前阈值、持续时间与冷却间隔 |
| "把检测阈值调到 80" | `threshold`，0-100，越高误报越少 |
| "把持续时间改成 2 秒" | `duration`，0-60 秒，停留满该时长才确认 |
| "把冷却时间设为 10 秒" | `interval`，0-60 秒，对话后再次唤醒前的等待 |
| "切换到人脸检测模式" / "关闭主动唤醒" | `mode`：0=关闭，1=人脸检测，2=人脸识别，3=熟人免打扰 |

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 参数值不被接受 | 取值范围：`threshold` 0-100，`duration` 0-60 秒，`interval` 0-60 秒，`mode` 0-3。 |
| 误触发问候过多 | 提高 `threshold` 或 `duration`，或增大 `interval`。 |

---

## 套餐: 端侧人脸识别与迎宾 {#face_recognition}

在能感知“有人”的基础上，进一步识别“具体是谁”：启用 Himax WE2 独立视觉 NPU 运行 SCRFD + MobileFaceNet 双模型，端侧离线识别人脸、直呼其名，并在本地 NVS 存储最多 20 人的人脸特征库。

### 前提条件

- SenseCAP Watcher 与电脑通过 USB-C 数据线连接。
- Watcher 已刷入小智固件、连入 2.4 GHz WiFi 并完成 SenseCraft AI / 小智平台绑定（可先完成「套餐: 语音对话与智能体接入」）。直呼其名迎宾需要设备具备活跃的语音对话能力。

## 步骤 1: 烧录 Himax WE2 人脸模型 {#face_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

Watcher 内部由 ESP32-S3（主控兼语音）和 Himax WE2（视觉 AI NPU）组成：
1. 切换到 SERIAL-A 串口（macOS/Linux 选编号较小的那个，如 `...51` / `ttyACM0`）。
2. 点击烧录，将人脸检测（SCRFD 500M）与特征提取（MobileFaceNet 128D）固件写入 Himax WE2 芯片。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 找不到串口 | 使用数据线并选择编号较小的端口（SERIAL-A，如 `ttyACM0`）；SERIAL-B 是步骤 2 使用的 ESP32-S3 串口。 |
| 烧录失败 | 重新插拔 USB-C 数据线后再次烧录。 |

---

## 步骤 2: 连接 ESP32 主控串口 {#face_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

人脸特征数据库存储在 ESP32-S3 的本地 NVS 分区中：
1. 切换到 SERIAL-B 串口（即 ESP32-S3 对应的串口）。
2. 若在第一阶段已烧录固件，在此处选中串口即可直接通信；若未烧录，点击烧录小智固件。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 找不到串口 | 选择 SERIAL-B 端口（ESP32-S3），不要选步骤 1 使用的 Himax 端口。 |
| 人脸库不可用 | 人脸库存储在 ESP32-S3 的 NVS 中；若之前未烧录小智固件，请先在本步骤烧录。 |

---

## 步骤 3: 录入人脸特征库 {#face_enroll type=serial_camera config=devices/face_enroll.yaml required=true}

通过 USB 连接电脑，在本地人脸数据库管理面板录入家人或同事的人脸：

1. 点击**连接**启动摄像头实时预览（读取 Himax 端口）
2. 点击**人脸数据库**面板中的**注册**（通过 ESP32 端口读写 NVS）
3. 输入姓名（例如“张三”）
4. 正对摄像头保持充足光线，点击**开始采集**，保持约 5 秒完成 128 维特征向量提取与写入
5. 注册成功后，该人脸记录保存在 Watcher 本地 NVS 存储中（最多 20 人）

---

## 步骤 4: 切换到人脸识别模式并体验迎宾 {#face_demo type=manual required=true}

拔掉 USB 数据线让 Watcher 独立运行，然后切换到识别模式。

### 接线


1. **开启人脸识别**：对 Watcher 说“开启人脸识别”或“把视觉模式设为 2”（`self.vision.mode: 2`）。
2. **熟人迎宾**：已录入人员走到 Watcher 前，Himax 端侧提取特征并在本地比对，Watcher 自动识别并直呼其名问候（例如“张三，你好！”）。
3. **陌生人提醒**：未录入人员出现时，触发陌生人提醒。
4. **语音管理命令**：
   - "你认识谁"：列出当前本地人脸库中录入的所有人员名字。
   - "你能认出我吗"：现场拍一张照提取特征并汇报当前匹配姓名与相似度。
   - "打开熟人模式"：开启免打扰（`mode: 3`），熟人经过不再逐个问候，仅在陌生人出现时发声提醒。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| Watcher 没有叫出名字 | 确认识别模式 2 已开启（说“开启人脸识别”），且该人员已在步骤 3 中录入。 |
| 熟人没有被问候 | 熟人模式（`mode: 3`）会对熟人静音；说“开启人脸识别”可恢复模式 2。 |

---

## 套餐: 8 寸触控大屏智能体 {#d1001_touch_agent}

使用搭载 ESP32-P4 芯片与 8 寸电容触摸屏的 reTerminal D1001 部署桌面语音智能体。支持屏幕触控配网、端侧摄像头主动视觉唤醒打招呼，以及局域网 HTTP 卡片推送。

- **设备：** reTerminal D1001，USB-C 数据线，Type-C 供电电源（建议 5V/3A）。
- **网络：** 2.4 GHz WiFi。
- **账号：** [小智官方控制台](https://xiaozhi.me) 或 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/)（免费注册）。

## 步骤 1: 烧录 D1001 固件 {#d1001_flash type=esp32_usb required=true config=devices/d1001_esp32.yaml}

将小智语音与端侧视觉固件写入 reTerminal D1001。

### 接线与烧录

1. 用 USB-C 数据线将 reTerminal D1001 连接到电脑的原生 USB 接口
2. 串口自动识别（ESP32-P4 原生 USB-Serial-JTAG，macOS 显示为 `/dev/cu.usbmodem*`，Linux 显示为 `/dev/ttyACM*`，Windows 显示为 USB JTAG/serial 端口）
3. 点击烧录按钮完成固件多分区写入

### 故障排查

| 现象 | 处理 |
|------|------|
| 找不到串口 | 换用支持数据传输的 USB-C 数据线，直连电脑 USB 接口（避免使用拓展坞） |
| 烧录中断或失败 | 拔下 USB-C 数据线，重新插入后再次点击烧录 |

---

## 步骤 2: 触控配网与设备绑定 {#d1001_touch_setup type=manual required=true verify=true}

在触控屏上配置 Wi-Fi，绑定设备，并测试主动问候与卡片推送。

### 接线

1. **大屏触控配网**：烧录完成后设备自动重启。首次开机未配网时系统会自动弹出 Wi-Fi 列表，或可点击屏幕左上角网络图标进入；选择 2.4 GHz Wi-Fi 后，在屏幕软键盘输入密码连接。
2. **平台接入与绑定**：配网成功后，屏幕上显示专属的 **6 位设备绑定码**。登录[小智官方控制台](https://xiaozhi.me)或 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/)，在设备管理中输入屏幕上显示的 6 位验证码完成绑定，即可开始语音对话。
3. **视觉主动问候与卡片推送**：
   - **Mode 1 端侧视觉主动打招呼**：在设备空闲状态下，板载摄像头通过本地 esp-dl 人脸检测模型感知有人出现，自动触发语音主动打招呼；具备冷却时间防止短时间内重复打扰。

### 故障排查

| 问题 | 解决方法 |
|---|---|
| 没有显示 Wi-Fi 列表 | 点击屏幕左上角的网络图标；仅可使用 2.4 GHz 网络。 |
| 没有显示 6 位绑定码 | 设备联网后才会显示绑定码；请在小智控制台或 SenseCraft AI 平台的设备管理中输入。 |
| 卡片推送请求失败 | 使用屏幕左上角显示的 IP 与 8080 端口，并从同一局域网内的电脑发送请求。 |

### 部署完成

**局域网卡片推送**：设备连接 Wi-Fi 后，屏幕左上角可查看局域网 IP（例如 `192.168.x.x`）。支持在同局域网下通过 8080 端口推送卡片，最小可执行验证命令：
```bash
curl -X POST http://<设备IP>:8080/panel/markdown \
  -H "Content-Type: application/json" \
  -d '{"text":"# 你好，D1001\n已连接到局域网！"}'
```
