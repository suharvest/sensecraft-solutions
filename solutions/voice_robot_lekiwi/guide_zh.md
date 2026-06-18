## 套餐: 语音控制你的 LeKiwi {#default}

打造一个能听懂自然语言指令的语音控制机器人——只需说话就能让它前进、后退、横移、转向。

| 设备 | 用途 |
|------|------|
| LeKiwi 套件 | 三轮 Kiwi-drive 底盘，含 3 个 STS3215 智能舵机 |
| XIAO ESP32S3 | 电机控制器——接收树莓派发来的串口指令 |
| 树莓派 5 | 语音 AI 大脑——运行唤醒词检测、语音识别、LLM 推理和语音合成 |
| reSpeaker Flex XVF3800 | 4 麦克风阵列，实现远场语音采集 |

**你将获得：**
- 一台能用自然语言解放双手控制的机器人
- 唤醒词激活（"Hey Jarvis"）——机器人只在被呼叫时响应
- Groq AI 驱动：Whisper（语音识别）+ Llama 3（推理决策）+ Orpheus（语音回复）
- Kiwi-drive 全向移动 + 紧急停止

**需要准备：** LeKiwi 套件 · XIAO ESP32S3 · 树莓派 5 · reSpeaker Flex XVF3800 · 音箱 · Groq API 密钥（免费） · 树莓派能上网

## 步骤 1: 组装硬件 {#hardware type=manual required=true}

在部署任何软件之前，需要先完成机器人的物理组装。

### 接线

1. **组装底盘**——参考 [LeKiwi 组装教程](https://wiki.seeedstudio.com/lerobot_lekiwi/#assembly) 搭建框架并安装轮子/舵机。先不要把舵机总线接到 XIAO —— 步骤 2、3 会烧录配置固件并逐个设置舵机 ID。
2. **连接 reSpeaker Flex**——将 reSpeaker Flex 插入树莓派的 USB 口
3. **连接 XIAO ESP32S3**——用 USB-C 线将 XIAO 连接到树莓派
4. **连接音箱**——将音箱插入树莓派的音频口或 USB 口

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 舵机无响应 | 先完成步骤 2、3：烧录舵机 ID 配置固件，并用串口向导逐个设置 ID 1、2、3 |
| 舵机接线混淆 | 舵机 1 = 前轮，舵机 2 = 左后轮，舵机 3 = 右后轮 |
| USB 设备不识别 | 换一根 USB 线试试——有些线只能充电，不支持数据传输 |

## 步骤 2: 烧录舵机 ID 配置 {#esp32_id type=esp32_usb required=true config=devices/esp32_id_setter.yaml}

将舵机 ID 配置固件烧录到 XIAO ESP32。该固件通过下一步的串口控制台，逐个为 STS3215 舵机分配唯一 ID（1、2、3）。

### 接线

1. 用 USB-C 线将 XIAO ESP32 连接到电脑
2. 点击**部署**烧录固件
3. 继续步骤 3 配置舵机 ID

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 烧录失败 / 设备未识别 | 按住 XIAO 上的 BOOT 键，按一下 RESET，再松开 BOOT |

## 步骤 3: 配置舵机 ID {#servo_wizard type=serial_wizard required=true config=devices/servo_id_wizard.yaml}

使用串口控制台逐个为舵机分配 ID。固件会引导操作 —— 按提示逐个连接舵机并确认。

### 接线

1. 点击**连接**打开串口控制台
2. 按提示逐个将舵机连接到 XIAO 舵机总线：
   - **前轮** → ID 1
   - **左后轮** → ID 2
   - **右后轮** → ID 3
3. 使用**发送回车**按钮或在输入框输入内容后按 Enter 继续
4. 三个 ID 全部设置完毕后，断电，将所有舵机接回总线

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 未检测到舵机 | 检查舵机供电，点击**重新扫描**按钮重试 |
| 检测到多个舵机 | 每次只连接一个舵机到总线 |
| 串口无输出 | 拔插 XIAO USB 线后重新点击**连接** |

## 步骤 4: 烧录电机控制器 {#esp32 type=esp32_usb required=true config=devices/esp32.yaml}

烧录电机控制固件。该固件负责 Kiwi-drive 运动学计算，并监听来自树莓派的串口指令。

### 接线

1. 用 USB-C 线将 XIAO ESP32 连接到电脑
2. 点击**部署**烧录固件
3. 烧录完成后，将 XIAO 重新连接到树莓派，给舵机上电

### 验证

烧录后，XIAO 会启动并检测舵机 1、2、3。串口监视器（115200 波特率）会依次显示 `Servo 1 OK`、`Servo 2 OK`、`Servo 3 OK`，最后显示 `System ready!`。

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 烧录失败 / 设备未识别 | 按住 XIAO 上的 BOOT 键，按一下 RESET，再松开 BOOT |
| 检测到错误的串口 | 拔掉其他 USB 转串口设备后重试 |
| 启动时找不到舵机 | 检查舵机供电。如果 ID 没设对，重新执行步骤 2-3 |

## 步骤 5: 部署语音大脑 {#voice_brain type=docker_deploy required=true config=devices/voice_brain_deploy.yaml}

把语音 AI 容器部署到机器人的树莓派上（唤醒词 + 语音识别 + LLM + 语音合成全在一个镜像里）。

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| Docker 未安装 | 在树莓派上运行 `curl -fsSL https://get.docker.com \| sh` |
| 容器启动后立即退出 | `docker logs lekiwi-voice` 查日志，多半是 GROQ_API_KEY 没填 |
| 唤醒词不响应 | 确认部署前已插入 reSpeaker。容器会自动选择麦克风，可用 `docker logs lekiwi-voice` 查看实际选中的输入设备 |
| 机器人不动 | 确认 XIAO 已通过 USB-C 连接到树莓派，并且步骤 4 的电机控制固件正在运行。容器会自动选择 ESP32 串口 |
| TTS / STT 报错 | GROQ_API_KEY 无效、Groq 使用条款未接受，或树莓派无法访问 Groq |

### 部署目标 {#local type=local config=devices/voice_brain_deploy.yaml}

### 部署目标 {#raspberry_pi type=remote config=devices/voice_brain_deploy.yaml default=true}

## 步骤 6: 和机器人对话 {#test type=manual verify=true required=true}

一切就绪后，测试你的语音控制机器人。

### 验证

1. 站在距离机器人 1 米以内
2. 清晰地说出 **"Hey Jarvis"**——此时不会听到回复（机器人在等待你的指令）
3. 唤醒后说出指令，例如：
   - "前进"
   - "左转"
   - "向右横移"
   - "你能做什么？"
4. 机器人应该先语音回复，然后执行相应动作

### 故障排查

| 问题 | 解决方案 |
|------|----------|
| 唤醒词始终检测不到 | 距离麦克风 1 米以内清晰说话。查看 `docker logs lekiwi-voice`，确认自动选中的麦克风是 reSpeaker |
| 机器人移动方向不对 | 确认舵机 ID 1、2、3 设置正确，轮子角度正确 |
| 响应较慢 | Groq API 延迟。首次请求可能需 2-3 秒，后续会更快 |
| 容器反复重启 | 查看日志：`docker logs lekiwi-voice`。确认 GROQ_API_KEY 有效 |
### 部署完成

你的 LeKiwi 机器人现在可以用语音控制了。

#### 指令参考

| 短语 | 机器人动作 |
|------|-----------|
| "前进" / "往前走" | 向前移动 |
| "后退" / "往后退" | 向后移动 |
| "左转" / "向左转" | 左转 |
| "右转" / "向右转" | 右转 |
| "向左横移" / "左移" | 向左横移 |
| "向右横移" / "右移" | 向右横移 |
| "一直往前走" / "持续前进" | 连续移动（直到停止） |
| "停下" / "停止" / "紧急停止" | 紧急停止 |

#### 高级指令

机器人还能响应：
- "你能做什么？"——列出能力
- "加速" / "减速"——调整移动参数
- 闲聊对话——LLM 会自然对话并通过 TTS 回复

#### 下一步

- 在设备设置中调整移动距离/速度后重新部署
- 在设备设置中更换 TTS 语音（Autumn, Tara, Leah, Dan, Mia, Zac）
- 如果唤醒词难以触发，查看 `docker logs lekiwi-voice`，确认自动选中的麦克风是 reSpeaker
- [LeKiwi Voice GitHub](https://github.com/KasunThushara/Lekiwi-voice)
