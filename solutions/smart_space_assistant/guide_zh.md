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

---

## 步骤 3: 绑定 SenseCraft AI 并开启语音对话 {#voice_agent_setup type=manual required=true}

1. 浏览器登录 [SenseCraft AI 平台](https://sensecraft.seeed.cc/ai/device/local/37/)
2. 在模型列表中找到「SenseCAP Watcher」，选择「Watcher Agent」并点击「Bind Device」
3. 输入 Watcher 屏幕上的 6 位验证码完成硬件绑定
4. 点击「Create」新建专属智能体（如工位助手、迎宾接待或仓管员），按需设定 System Prompt 与交互音色
5. 对 Watcher 说出唤醒词「小智小智」或直接开始对话，即可体验低延迟流式语音问答
6. （可选联动工作站）在 Agent 页面底部获取「MCP Setting」端点，填入仓管系统或本地服务，Watcher 即可通过 MCP 工具直接读写业务数据

---

## 套餐: 视觉主动唤醒与参数配置 {#vision_wake}

在语音对话的基础上，让 Watcher 拥有“眼睛”：开启视觉主动唤醒，摄像头看到人出现在面前时主动开口打招呼并进入对话；通过语音随时讲解与调节视觉感知核心参数。

- **设备：** SenseCAP Watcher，USB-C 数据线。
- **网络：** 2.4 GHz WiFi。

## 步骤 1: 体验主动打招呼 {#vision_wake_intro type=manual required=true}

1. 将已配网的 Watcher 放置在桌面或工位正对人脸的高度（距离约 0.5 ~ 1.5 米）。
2. 走到 Watcher 面前并停留：
   - 摄像头检测到有人出现并停留时，Watcher 屏幕切换为灵动表情，主动开口向你打招呼（如“你好呀，看到你了！”），直接进入对话监听状态，无需呼唤唤醒词。

---

## 步骤 2: 语音讲解与微调检测参数 {#vision_wake_params type=manual required=true}

在对话中，试着询问 Watcher 它的视觉参数，Watcher 会调用内部工具并为你讲解与设置：

| 对 Watcher 说 | 触发动作与效果 |
|---|---|
| "查询视觉参数" 或 "你的视觉参数怎么设置的" | Watcher 汇报当前置信度阈值、持续确认时间与冷却间隔 |
| "把检测阈值调到 80" | 提高置信度阈值（`threshold`，范围 0-100），要求更清晰的人脸才触发，有效减少误报 |
| "把持续时间改成 2 秒" | 调整持续检测时长（`duration`，范围 0-60 秒），人必须在视野内停留指定时长后才确认识别，防止走过路过误触发 |
| "把冷却时间设为 10 秒" | 调整唤醒冷却时间（`interval`，范围 0-60 秒），对话结束后等待指定秒数才允许下一次视觉唤醒，避免反复打扰 |
| "切换到人脸检测模式" / "关闭主动唤醒" | 切换视觉模式（`mode`）：0=关闭主动唤醒，1=人脸检测（只识别人在不在），2=人脸识别（报名字），3=熟人免打扰 |

---

## 套餐: 端侧人脸识别与迎宾 {#face_recognition}

在能感知“有人”的基础上，进一步识别“具体是谁”：启用 Himax WE2 独立视觉 NPU 运行 SCRFD + MobileFaceNet 双模型，端侧离线识别人脸、直呼其名，并在本地 NVS 存储最多 20 人的人脸特征库。

- **设备：** SenseCAP Watcher，USB-C 数据线。
- **网络：** 2.4 GHz WiFi。
- **隐私：** 人脸检测、对齐与特征提取全部在端侧芯片完成，不上传人脸照片到云端。

## 步骤 1: 烧录 Himax WE2 人脸模型 {#face_himax_flash type=himax_usb required=true config=devices/watcher_himax.yaml}

Watcher 内部由 ESP32-S3（主控兼语音）和 Himax WE2（视觉 AI NPU）组成：
1. 切换到 SERIAL-A 串口（macOS/Linux 选编号较小的那个，如 `...51` / `ttyACM0`）。
2. 点击烧录，将人脸检测（SCRFD 500M）与特征提取（MobileFaceNet 128D）固件写入 Himax WE2 芯片。

---

## 步骤 2: 录入人脸特征库 {#face_enroll type=serial_camera config=devices/face_enroll.yaml required=true}

通过 USB 连接电脑，在本地人脸数据库管理面板录入家人或同事的人脸：

1. 点击**连接**启动摄像头实时预览
2. 点击**人脸数据库**面板中的**注册**
3. 输入姓名（例如“张三”）
4. 正对摄像头保持充足光线，点击**开始采集**，保持约 5 秒完成 128 维特征向量提取与写入
5. 注册成功后，该人脸记录保存在 Watcher 本地 NVS 存储中（最多 20 人）

---

## 步骤 3: 体验熟人直呼其名与免打扰 {#face_demo type=manual required=true}

拔掉 USB 数据线，Watcher 独立运行：

1. **熟人迎宾**：已录入人员走到 Watcher 前，Watcher 自动识别并直呼其名问候（例如“张三，你好！”）。
2. **陌生人提醒**：未录入人员出现时，触发陌生人提醒。
3. **语音管理命令**：
   - "你认识谁"：列出当前本地人脸库中录入的所有人员名字。
   - "你能认出我吗"：现场拍一张照提取特征并汇报当前匹配姓名与相似度。
   - "打开熟人模式"：开启免打扰，熟人经过不再逐个问候，仅在陌生人出现时发声提醒。
