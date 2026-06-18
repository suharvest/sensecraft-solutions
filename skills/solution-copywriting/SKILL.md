---
name: optimize-solution
description: 优化 IoT 解决方案文案。检查并改进 solutions/ 目录下的介绍页和部署页文案，确保非技术用户能理解。使用场景：优化文案、检查术语、修复文案问题。
argument-hint: "<solution_id> [修改方向]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Solution Copywriting Skill

## 调用方式

```
/optimize-solution smart_warehouse                    # 全面检查
/optimize-solution smart_warehouse 介绍页术语太专业    # 指定修改方向
/optimize-solution smart_warehouse 部署步骤不清晰
/optimize-solution smart_warehouse 添加故障排查表格
```

## 参数说明

- `$0` = solution_id（必填）
- `$1...` = 修改方向（可选，自然语言描述）

## 执行流程

**Step 1**: 读取方案文件
- `solutions/$0/solution.yaml`
- `solutions/$0/description.md` + `solutions/$0/description_zh.md`
- `solutions/$0/guide.md` + `solutions/$0/guide_zh.md`

**如果指定了修改方向 (`$1`)**: 优先按用户指定方向修改，跳过无关检查项。

**Step 2**: 介绍页检查（对照下方「一、介绍页文案标准」）
- [ ] 有「这个方案能帮你做什么」段落？
- [ ] 有「核心价值」表格？
- [ ] 有「适用场景」示例？
- [ ] 有「使用须知」限制说明？
- [ ] 专业术语已替换？
- [ ] 设备名称具体、不泛指？
- [ ] 设备描述只写功能、不贴产品定位标签？
- [ ] 技术工具名已转为用户价值描述？

**根据 solution_type 的额外检查**：

如果 `solution_type: technical`（技术演示）：
- [ ] 首屏先讲「能接到什么系统、解决什么能力缺口」，不是先贴端口/API 表？
- [ ] 有「部署后你会得到什么」或等价段落？（把接口翻译成用户能理解的产物）
- [ ] 有接口段落？（说明产出什么数据、什么协议、什么格式；如前端已自动展示 `output_interfaces`，正文只做通俗解释）
- [ ] curl/代码示例放在部署完成、接口详情或 guide.md 中，不要放在介绍页首屏？
- [ ] 核心价值聚焦在「能力」而非「业务流程」？
- [ ] 没有过度包装成完整业务方案？

如果 `solution_type: solution`（完整方案）：
- [ ] 有用户操作界面/仪表板的描述或截图？
- [ ] 适用场景描述的是完整业务流程（而非单一技术能力）？
- [ ] 有「部署效果」段落让用户预知部署后能看到什么？

**Step 3**: 部署页检查（对照下方「三、部署页文案标准」）
- [ ] 每个步骤有 `### 接线` / `### Wiring` 子节？
- [ ] 每个步骤有 `### 故障排查` / `### Troubleshooting` 子节？
- [ ] 中英文步骤 ID（`{#...}` 部分）完全一致？
- [ ] **中文关键词严格使用规范写法**？（`### 部署目标:` 不是 `### 目标:`，`### 故障排查` 不是 `### 排错`——完整对照表见 `docs/guide-heading-keywords.md`）
- [ ] 成功页内容完整？
- [ ] **尖括号占位符已正确处理**？裸文本中 `<device-ip>` → `\<device-ip\>`；backtick 内和 fenced code block 内**不要转义**（反斜杠会原样显示）

**Step 4**: 输出改进报告
- 按 P0/P1/P2 分类问题
- 提供修改建议或直接修改

---

## 概述

本 Skill 用于创建或优化 `solutions/` 目录下的解决方案文案，确保：
- 非技术用户能在 30 秒内理解方案价值
- 部署步骤清晰可执行，不卡壳、不出错
- 用词通俗易懂，避免专业术语

---

## 一、介绍页文案标准

### 目标
帮助非技术用户在 30 秒内理解：**这个方案解决什么问题？对我有什么好处？**

### 文件位置

使用**分离格式**（每种语言独立文件）：

```
solutions/[id]/
├── description.md      # 英文介绍页
└── description_zh.md   # 中文介绍页
```

### 结构模板（必须包含以下 4 个部分）

```markdown
## 这个方案能帮你做什么

[用 1-2 句话，用通俗语言描述痛点和解决方案]

示例：
- ✓ "仓库管理系统功能强大，但上手成本高——要培训、要记菜单。这个方案把复杂操作变成说话，开口就会用。"
- ✗ "本方案通过集成视觉识别模块实现多模态人机交互能力增强。"

## 核心价值

用 3-4 个要点说明好处，每个要点：
- 用「动词 + 具体结果」的格式
- 附带可量化的指标或具体场景

| 好处 | 具体说明 |
|------|---------|
| 零学习成本 | 不用培训、不用记菜单，开口说话就能操作系统 |
| 数据实时准确 | 直接查询数据库，库存数据实时更新 |
| 数据安全可控 | 支持纯本地部署，数据不出厂区 |

## 适用场景

列出 3-4 个具体应用场景，每个场景包含：
- **场景名称**：一句话描述
- **使用示例**：具体的操作或对话

| 场景 | 怎么用 |
|------|--------|
| 收货入库 | 说"入库 5 台 Watcher"，系统自动登记 |
| 叉车作业 | 司机说"A3 货架还有多少货"，语音播报，不用下车 |

## 使用须知

按以下顺序组织内容：

### 核心硬件设备（必需，显示在架构图之前）

| 设备 | 说明 | 必需 |
|------|------|------|
| SenseCAP Watcher | AI 语音助手 | ✓ 必选 |
| reComputer R1100/R2000 | 边缘网关（两款均支持） | ✓ 必选 |
| NVIDIA AGX Orin | 本地 AI 计算 | 边缘方案需要 |

### 网络要求（必需，显示在架构图之前）

- Watcher 需连接 2.4GHz WiFi（不支持 5GHz）
- 云方案需要互联网，边缘方案可断网运行
```

### 介绍页内容渲染顺序

前端会将介绍页内容分成三部分渲染：

```
┌─────────────────────────────────────────┐
│  这个方案能帮你做什么                      │
│  核心价值                                 │
│  适用场景                                 │  ← 主描述块
├─────────────────────────────────────────┤
│  使用须知（独立 section，带 info 图标）    │
│    ├─ 核心硬件设备                        │
│    ├─ 网络要求                            │
│    └─ 输入要求（来自 YAML input_requirements，
│         作为 H3 子小节自动插入）            │
├─────────────────────────────────────────┤
│  部署说明（Preset 卡片，带层级图标）        │
│  设备选择器                               │
│  架构图                                   │
├─────────────────────────────────────────┤
│  方案对比（H2 "## 方案对比" 抽取的内容）     │  ← preset 卡片和架构图之后
└─────────────────────────────────────────┘
```

**分割规则**（前端自动抽取以下两个 H2 section，从原位置移除后渲染到指定位置）：
- `## 使用须知` / `## Usage Notes` → 渲染为独立区块，放到主描述下方
- `## 方案对比` / `## Deployment Comparison` → 渲染到 preset 卡片和架构图之后
- YAML 的 `input_requirements` 会作为 H3 "输入要求" 自动追加到使用须知区块末尾

**方案对比规范**：
- 所有包含多个 preset 的方案，`description.md` 必须有一个 `## 方案对比` section
- 该 section 承载：
  1. preset 之间的核心差异表格（网络要求、设备组合、适用场景）
  2. 可选功能 / 扩展能力（作为 H3 子章节）
- 内部可以用任意 markdown（表格 + H3 子章节）

**作者注意**：`## 使用须知` 必须使用 H2（`##`），不能用 H3。否则不会被抽出。

### 技术演示（technical）的介绍页结构

当 `solution.yaml` 中 `solution_type: technical` 时，介绍页**不使用**上述四段式结构，改用以下模板：

```markdown
## 这个能力做什么

[1-2 句话，先说明它给用户的系统补上什么能力，再说明输入什么、输出什么。避免首段出现 3 个以上专业缩写。]

示例：
- ✓ "把摄像头画面实时转换成深度图，告诉你画面中每个物体离镜头多远。"
- ✗ "基于 Depth Anything V3 模型的单目深度估计解决方案。"

## 部署后你会得到什么

[用 3-4 个 bullet，把接口翻译成用户能理解的能力产物。]

示例：
- 一个本地听写服务：你的程序把音频发进去，拿到识别文字。
- 一个本地播报服务：你的程序把文字发进去，拿到可播放语音。
- 标准接口：可以接到机器人、网页应用、信息亭或工控系统里。

## 适合接到哪些系统

列出 2-4 个具体的集成场景，重点是「和什么系统搭配」以及「搭配后完成什么动作」：
- 接入安防系统做距离判断
- 配合机械臂做深度感知抓取
- 作为机器人避障模块

## 给程序对接的接口

| 接口类型 | 说明 | 端口/路径 | 数据格式 |
|---------|------|----------|---------|
| RTSP 视频流 | AI 处理后的深度图视频 | :8554/depth | 视频帧 |
| REST API | 单张深度图 | :8080/api/depth | PNG 图片 |

> 此表必须与 solution.yaml 中的 `output_interfaces` 一致。若前端已经自动渲染接口卡片，正文可以只保留通俗摘要，避免重复堆端口。

## 技术规格

| 指标 | 数值 |
|------|------|
| 推理延迟 | < 50ms |
| 分辨率 | 640x480 |
| 支持硬件 | Jetson Orin NX / AGX Orin |
```

**技术演示写作顺序原则**：
- 先用非技术语言解释能力产物，再给接口细节。
- 不要把 curl 命令放在介绍页前半段；它会让页面像 API 文档。需要快速测试时放到 guide.md 的「部署完成」或接口详情中。
- `ASR/TTS/RTSP/MQTT/ONNX/TensorRT/RKNN` 等术语可以出现在接口表或技术规格里，但首屏必须有通俗翻译。
- 表格列名优先写「能力 / 怎么连接 / 返回什么」，再补端口和协议。

---

## 二、术语通俗化对照表

编写文案时，**必须**将专业术语替换为通俗表达：

| 专业术语 | 通俗替代 |
|---------|---------|
| ASR 语音识别 | 听懂你说的话 |
| TTS 语音合成 | 说话给你听 |
| 推理/Inference | 分析判断 |
| 边缘计算 | 本地处理（不需要联网） |
| API 调用 | 连接到你的系统 |
| Docker 容器 | 一键部署包 |
| MQTT 消息 | 数据传输 |
| 隐私模糊处理 | 自动打码保护隐私 |
| 热力图 | 人流分布图 |
| OPC-UA | 工业设备通讯 |
| LLM/大语言模型 | AI 对话能力 |
| 多模态 | 能看能听能说 |
| 向量数据库 | 记忆存储 |
| RAG | 根据资料回答问题 |
| MCP 协议 | 设备连接方式 |
| 串口/Serial | USB 连接 |
| 固件/Firmware | 设备内部程序 |
| 烧录 | 写入程序 |
| 部署 Ollama / 部署 XX 工具 | 利用本地算力运行本地模型（强调隐私/本地化价值，而非技术实现） |
| 电脑 / Computer / 任何机器 | 具体产品名（如 reComputer R1100、reComputer Jetson），方案面向特定产品线时不要泛指 |
| 边缘网关 / 边缘 AI 计算机 | 直接写设备做什么（如"运行 XX 服务"），不要贴产品定位标签 |

---

## 三、部署页文案标准

### 目标
让非技术用户按步骤操作，**不卡壳、不出错、不迷路**。

### 文件结构

使用**分离格式**（每种语言独立文件）：

```
solutions/[id]/
├── solution.yaml       # 方案配置（介绍页元数据 + preset 定义）
├── description.md      # 英文介绍页
├── description_zh.md   # 中文介绍页
├── guide.md            # 英文部署页（含所有步骤 + 成功页）
├── guide_zh.md         # 中文部署页（含所有步骤 + 成功页）
├── gallery/            # 图片资源
│   ├── cover.png
│   └── ...
└── devices/            # 设备配置文件
    ├── docker.yaml
    └── ...
```

> **重要**：部署步骤的所有内容（标题、描述、接线、故障排除）都在 `guide.md` / `guide_zh.md` 中定义，不再使用 `deploy/sections/` 目录。

### guide.md 模板（英文）

```markdown
## Preset: Cloud Solution {#cloud_mode}

Use [SenseCraft](https://sensecraft.seeed.cc/ai/) cloud services for AI capabilities. Simplest deployment - just set up the system and connect devices to the platform.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant for receiving commands |
| Computer | Runs Docker services |

**What you'll get:**
- Voice-controlled operations
- Real-time web dashboard
- Works out of the box

**Requirements:** Internet connection · [SenseCraft account](https://sensecraft.seeed.cc/ai/) (free)

## Step 1: Deploy Backend {#backend type=docker_deploy required=true config=devices/docker.yaml}

Deploy the backend services.

### Target: Local Deployment {#backend_local type=local config=devices/docker.yaml default=true}

![Wiring](gallery/architecture.png)

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Deployment Complete

1. Open **http://localhost:8080** in your browser
2. Create your admin account

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8080 busy | Stop other services using this port |
| Docker not found | Install Docker Desktop |

### Target: Remote Deployment {#backend_remote type=remote config=devices/docker_remote.yaml}

![Wiring](gallery/architecture.png)

1. Connect target device to network
2. Enter IP address and SSH credentials
3. Click Deploy to install on remote device

### Deployment Complete

1. Open **http://\<device-ip\>:8080** in your browser
2. Create your admin account

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Check IP address and credentials |
| Timeout | Ensure target device is online |

---

## Step 2: Configure Platform {#platform type=manual required=true}

### Wiring

![Platform Setup](gallery/platform.png)

1. Open web interface at http://localhost:8080
2. Register admin account
3. Configure API settings

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page not loading | Wait 30 seconds for services to start |
| Registration failed | Check network connection |

---

## Preset: Edge Computing {#edge_mode}

## Step 1: Deploy Backend {#backend type=docker_deploy required=true config=devices/docker.yaml}

... (steps for this preset)

---

# Deployment Complete

Congratulations! All components deployed successfully.

## Initial Setup

1. Open http://localhost:8080
2. Register admin account

## Quick Verification

- Test voice commands
- Verify web interface

## Next Steps

- [View Documentation](https://wiki.seeedstudio.com/...)
- [Report Issues](https://github.com/...)
```

### guide_zh.md 模板（中文）

```markdown
## 套餐: 云方案 {#cloud_mode}

使用 [SenseCraft](https://sensecraft.seeed.cc/ai/) 云服务提供 AI 能力。最简单的部署方式——只需部署系统，将设备连接到平台即可。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | 语音助手，接收语音指令 |
| 电脑 | 运行 Docker 服务 |

**部署完成后你可以：**
- 语音操控系统
- 网页实时查看数据
- 开箱即用，无需额外配置

**前提条件：** 需要联网 · [SenseCraft 账号](https://sensecraft.seeed.cc/ai/)（免费注册）

## 步骤 1: 部署后端 {#backend type=docker_deploy required=true config=devices/docker.yaml}

部署后端服务。

### 部署目标: 本机部署 {#backend_local config=devices/docker.yaml default=true}

![接线图](gallery/architecture.png)

1. 确保 Docker 已安装并运行
2. 点击部署按钮启动服务

### 部署完成

1. 在浏览器打开 **http://localhost:8080**
2. 注册管理员账号

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 端口 8080 被占用 | 停止占用该端口的其他服务 |
| 找不到 Docker | 安装 Docker Desktop |

### 部署目标: 远程部署 {#backend_remote config=devices/docker_remote.yaml}

![接线图](gallery/architecture.png)

1. 将目标设备连接到网络
2. 输入 IP 地址和 SSH 凭据
3. 点击部署安装到远程设备

### 部署完成

1. 在浏览器打开 **http://\<设备IP\>:8080**
2. 注册管理员账号

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| SSH 连接失败 | 检查 IP 地址和凭据 |
| 连接超时 | 确保目标设备在线 |

---

## 步骤 2: 配置平台 {#platform type=manual required=true}

### 接线

![平台设置](gallery/platform.png)

1. 访问 http://localhost:8080
2. 注册管理员账号
3. 配置 API 设置

### 故障排除

| 问题 | 解决方法 |
|------|----------|
| 页面无法加载 | 等待 30 秒让服务启动 |
| 注册失败 | 检查网络连接 |

---

## 套餐: 边缘计算 {#edge_mode}

## 步骤 1: 部署后端 {#backend type=docker_deploy required=true config=devices/docker.yaml}

... (此套餐的步骤)

---

# 部署完成

恭喜！所有组件已部署成功。

## 初始设置

1. 访问 http://localhost:8080
2. 注册管理员账号

## 快速验证

- 测试语音命令
- 验证 Web 界面

## 后续步骤

- [查看文档](https://wiki.seeedstudio.com/...)
- [报告问题](https://github.com/...)
```

### 格式规范

#### Preset 头格式

```
## Preset: Name {#preset_id}
## 套餐: 名称 {#preset_id}
```

- `#preset_id` - Preset ID（必需，小写+下划线）
- 必须与 solution.yaml 中 `intro.presets[].id` 一致

#### Preset 全局说明（推荐）

在 Preset 标题后、第一个步骤之前的内容会作为该预设的全局说明，显示在部署页的预设选择器下方。

**标准格式**：

```markdown
## Preset: Cloud Solution {#cloud_mode}

Use [SenseCraft](https://sensecraft.seeed.cc/ai/) cloud services for AI capabilities. Simplest deployment - just set up the system and connect Watcher to the platform.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant for receiving commands |
| reComputer R1100 | Runs the management system |

**What you'll get:**
- Voice-controlled operations
- Real-time web dashboard
- Works out of the box

**Requirements:** Internet connection · [SenseCraft account](https://sensecraft.seeed.cc/ai/) (free registration)

## Step 1: Deploy Backend {#backend ...}
```

**中文版本**：

```markdown
## 套餐: 云方案 {#cloud_mode}

使用 [SenseCraft](https://sensecraft.seeed.cc/ai/) 云服务提供 AI 能力。最简单的部署方式——只需部署系统，将 Watcher 连接到 SenseCraft 平台即可。

| 设备 | 用途 |
|------|------|
| SenseCAP Watcher | 语音助手，接收语音指令 |
| reComputer R1100 | 运行管理系统 |

**部署完成后你可以：**
- 语音操控系统
- 网页实时查看数据
- 开箱即用，无需额外配置

**前提条件：** 需要联网 · [SenseCraft 账号](https://sensecraft.seeed.cc/ai/)（免费注册）

## 步骤 1: 部署后端 {#backend ...}
```

**格式要点**：

| 元素 | 英文 | 中文 | 说明 |
|------|------|------|------|
| 设备表格 | `\| Device \| Purpose \|` | `\| 设备 \| 用途 \|` | 列出该预设所需的设备 |
| 能力列表 | `**What you'll get:**` | `**部署完成后你可以：**` | 3-4 个要点说明部署后能做什么 |
| 前提条件 | `**Requirements:**` | `**前提条件：**` | 用 · 分隔多个条件，支持链接 |

**用途**：
- 介绍该预设的特点和适用场景
- 用表格展示所需设备（避免用列表）
- 说明部署后能实现什么（用 bullet list）
- 一行说明前提条件，支持添加链接（如 SenseCraft、小智 App）

**样式说明**：
- CSS 使用浅色背景（`bg-gray-50/50`）+ 虚线边框（`border-dashed`）
- 与步骤卡片形成视觉层次区分
- 文字使用次要颜色（`text-secondary`），不抢夺步骤的注意力

#### 步骤头格式

```
## Step N: Title {#step_id type=xxx required=true config=devices/xxx.yaml}
## 步骤 N: 标题 {#step_id type=xxx required=true config=devices/xxx.yaml}
```

参数说明：
- `#step_id` - 步骤 ID（必需，小写+下划线）
- `type` - 部署类型（必需）
- `required` - 是否必需（默认 true）
- `config` - 设备配置文件路径（可选）

**有效类型**：
| 类型 | 说明 |
|------|------|
| `manual` | 手动步骤（仅显示说明） |
| `docker_deploy` | Docker 部署（支持 local/remote targets） |
| `docker_local` | 本机 Docker 部署 |
| `docker_remote` | 远程 Docker 部署 |
| `esp32_usb` | ESP32 USB 烧录 |
| `himax_usb` | Himax 芯片烧录 |
| `script` | 脚本执行 |
| `preview` | 预览功能 |
| `recamera_cpp` | reCamera C++ 应用 |
| `recamera_nodered` | reCamera Node-RED |
| `ha_integration` | Home Assistant 集成部署 |
| `ssh_deb` | SSH + Debian 包部署 |

**Docker 部署方式详解**

- **`docker_local`**: 在目标设备本地执行部署。用户需要在目标设备上（或通过本地连接如 USB Serial）直接执行部署命令。适用于设备有控制台、SSH 本地连接、或用户在设备现场操作的场景。
  - 示例：在 Jetson 连接键盘/鼠标，或通过 USB Serial 终端本地执行 `docker-compose up`。

- **`docker_remote`**: 从远程机器（如用户的 Mac/Windows）通过网络（SSH）连接到目标设备后执行部署。适用于用户与目标设备在不同网络、或需要远程管理的场景。
  - 示例：从 Mac 通过 SSH 连接到局域网内的 Jetson，然后在 Jetson 上执行部署命令。

**规则**：所有支持 Docker 部署的方案都应同时提供 `docker_local` 和 `docker_remote` 两种方式，让用户灵活选择。

#### 详细数据（Data Channels）

验证步骤（preview、voice_demo、http_debug）会自动生成「详细数据」面板，展示连接信息（MQTT broker/topic、WebSocket URL、curl 命令等），帮用户调试和二次集成。

如果方案对外提供了自定义 API 或数据流，可以在设备 YAML 中显式声明 `data_channels`，支持 4 种类型：`mqtt`、`websocket`、`http`、`http_stream`。URL 中可以使用 `{{host}}` 等模板变量，用户在页面上填完值后点刷新按钮自动替换。

> 详细格式参考 `/solution-validation` skill 中的「详细数据」章节。

#### 步骤描述（自动提取为副标题）

步骤标题下方的**第一段纯文本**会自动显示为卡片的副标题（header 区域）。

**推荐写法**：用一句话说清这步做什么

```markdown
## Step 1: Deploy Backend {#backend type=docker_deploy ...}

Deploy the data storage and chart display services on your computer.

### Target: Local Deployment {#backend_local ...}
```

**注意**：
- 图片行（`![...](...)` ）、列表、表格会被跳过
- 如果步骤标题下方直接是 `### 接线` 等子节，则不显示副标题
- 副标题应简洁（1 句话），详细说明放在内容区

#### Target 头格式（用于 docker_deploy 类型）

```
### Target: Name {#target_id type=local config=devices/xxx.yaml default=true}
### 部署目标: 名称 {#target_id type=remote config=devices/xxx.yaml default=true}
```

参数说明：
- `#target_id` - Target ID（必需，小写+下划线）
- `type` - 部署类型：`local`（本机部署）或 `remote`（远程部署）（必需）
- `config` - 设备配置文件路径（可选）
- `default` - 是否为默认选项（可选，true/false）

> ⚠️ **Target 内容结构规则**：Target 标题下方只允许**一行简短描述**（会显示在选择卡片上）。表格、列表、图片等详细内容**必须放在 `### Wiring` / `### 接线` 子节中**。否则这些内容会被当作 `description` 字段，以原始 markdown 文本显示在选择卡片上，导致排版混乱。
>
> ✓ 正确：
> ```markdown
> ### Target: Local {#local type=local ...}
>
> Deploy on your local computer.
>
> ### Wiring
> | Device | Connection |
> |--------|------------|
> | ... | ... |
> 1. Step one
> 2. Step two
> ```
>
> ✗ 错误（表格会显示为原始 markdown 文本）：
> ```markdown
> ### Target: Local {#local type=local ...}
>
> Deploy on your local computer.
>
> | Device | Connection |
> |--------|------------|
> | ... | ... |
> ```

#### 子节识别规则

| 英文标题 | 中文标题 | 用途 | 渲染位置 |
|---------|---------|------|---------|
| `### Wiring` | `### 接线` | 接线说明 | 部署按钮上方（图片+步骤） |
| `### Deployment Complete` | `### 部署完成` | 部署后操作指引 | 部署按钮下方（绿色背景） |
| `### Troubleshooting` | `### 故障排查` 或 `### 故障排除` | 故障排查 | 部署按钮下方（始终可见） |
| `### Target: ...` | `### 部署目标: ...` | 部署目标选项 | Target 选择器 |
| 其他 H3 | - | 作为描述的一部分 | 步骤主体内容 |

> ⚠️ **重要**：中文故障排查标题必须使用 `### 故障排查` 或 `### 故障排除`（解析器同时支持两种写法）。如果使用其他写法（如 `### 故障排除方法`），将不会被正确识别，导致内容被当作普通描述显示。

#### 接线子节格式

```markdown
### 接线

![接线图](gallery/wiring.png)

1. 用 USB-C 线连接设备到电脑
2. 选择串口
3. 点击部署按钮
```

解析器自动提取：
- `wiring.image` - 从 `![](path)` 提取图片路径
- `wiring.steps` - 从有序列表提取步骤

#### 故障排查子节格式

```markdown
### 故障排查

| 问题 | 解决方法 |
|------|----------|
| 找不到串口 | 换一条 USB 线或换个 USB 口 |
| 烧录失败 | 重新插拔设备再试 |
```

**格式要求**：
- **必须使用表格格式**，包含「问题」和「解决方法」两列
- **标题必须精确匹配**：中文使用 `### 故障排查` 或 `### 故障排除`，英文使用 `### Troubleshooting`
- 标题后不要添加额外文字（如 ~~`### 故障排查指南`~~），否则解析器无法识别

#### 成功页格式

使用 `# Deployment Complete` / `# 部署完成` 标记成功页开始：

```markdown
# 部署完成

恭喜！所有组件已部署成功。

## 初始设置

1. 访问 http://localhost:8080
2. 注册管理员账号

## 快速验证

- 测试语音命令
- 验证 Web 界面
```

### 页面布局

```
┌─────────────────────────────────────────┐
│  [Preset 选择器: 云方案 | 边缘计算]       │  ← 多个 preset 时显示
├─────────────────────────────────────────┤
│  步骤 1: 部署后端                        │  ← 步骤卡片
│  ├─ [Target 选择: 本机 | 远程]           │  ← docker_deploy 时显示
│  ├─ 接线图 + 步骤列表                    │  ← ### 接线 子节
│  ├─ [ 🚀 开始部署 ]                     │  ← 系统自动渲染
│  ├─ 部署后操作指引（绿色背景）            │  ← ### 部署完成 子节
│  └─ 故障排除表格                        │  ← ### 故障排除 子节
├─────────────────────────────────────────┤
│  步骤 2: 配置平台                        │
│  └─ ...                                 │
└─────────────────────────────────────────┘
```

### 中英文结构一致性要求

**必须保证中英文文件的结构完全一致**：

1. **Preset ID 一致**：`{#cloud_mode}` 在两个文件中必须相同
2. **步骤 ID 一致**：`{#backend}` 在两个文件中必须相同
3. **Target ID 一致**：`{#backend_local}` 在两个文件中必须相同
4. **步骤数量一致**：每个 preset 下的步骤数量必须相同
5. **type/required/config 一致**：元数据参数必须相同

解析器会校验结构一致性，不一致时会报告错误。

---

## 四、solution.yaml 配置（简化版）

> **重要变化**：从 v2.0 开始，部署步骤的所有内容从 `guide.md` / `guide_zh.md` 自动解析，YAML 中只需定义介绍页元数据和 preset 基本信息。

```yaml
version: "1.0"
id: solution_id
name: Solution Name
name_zh: 方案名称

intro:
  summary: One-line description
  summary_zh: 一句话描述
  description_file: description.md      # 英文介绍页（根目录）
  cover_image: gallery/cover.png
  category: voice_ai
  tags: [voice, ai, watcher]

  gallery:
    - type: image
      src: gallery/demo.png
      caption: Demo screenshot
      caption_zh: 演示截图

  # 设备目录（用于介绍页展示购买链接）
  device_catalog:
    sensecap_watcher:
      name: SenseCAP Watcher
      name_zh: SenseCAP Watcher
      image: gallery/watcher.png
      product_url: https://www.seeedstudio.com/sensecap-watcher
      description: AI voice assistant
      description_zh: AI 语音助手

  # Preset 定义（用于介绍页展示方案选项）
  presets:
    - id: cloud_mode                    # 必须与 guide.md 中的 {#cloud_mode} 一致
      name: Cloud Solution
      name_zh: 云方案
      badge: Recommended
      badge_zh: 推荐
      description: Quick setup with cloud services
      description_zh: 使用云服务快速部署
      device_groups:                    # 用于介绍页展示所需设备
        - id: watcher
          name: Voice Assistant
          name_zh: 语音助手
          type: single
          required: true
          options:
            - device_ref: sensecap_watcher
          default: sensecap_watcher
      # ⚠️ 不需要 devices[] - 步骤从 guide.md 解析
      # ⚠️ 不需要 section - 内容从 guide.md 解析

  stats:
    difficulty: beginner    # beginner | intermediate | advanced
    estimated_time: 30min

  links:
    wiki: https://wiki.seeedstudio.com/...
    github: https://github.com/...

deployment:
  guide_file: guide.md                  # 英文部署页（根目录）
  selection_mode: sequential
  # ⚠️ 不需要 devices[] - 从 guide.md 解析
  # ⚠️ 不需要 order[] - 从 guide.md 解析
  # ⚠️ 不需要 post_deployment.success_message_file - 从 guide.md 末尾解析
```

### YAML 与 guide.md 职责划分

| 数据 | YAML | guide.md | 说明 |
|------|------|----------|------|
| **介绍页** ||||
| Preset ID/名称/描述 | ✅ | ❌ | 用于介绍页展示 |
| 所需设备 (device_groups) | ✅ | ❌ | 购买链接展示 |
| 封面/图库/标签 | ✅ | ❌ | 介绍页元数据 |
| **部署页（100% 从 guide.md）** ||||
| Preset 结构 | ❌ | ✅ | 从 `## Preset: ... {#id}` 解析 |
| 步骤 ID/type/config | ❌ | ✅ | 从 `## Step ... {#id type=X}` 解析 |
| 步骤内容/接线/故障排除 | ❌ | ✅ | Markdown 内容 |
| Target 选项 | ❌ | ✅ | 从 `### Target: ... {#id}` 解析 |
| 成功消息 | ❌ | ✅ | `# Deployment Complete` 区域 |

---

## 五、质量检查清单

### 介绍页检查

- [ ] **30 秒测试**：非技术人员能否在 30 秒内说出"这是干什么的"
- [ ] **价值明确**：每个核心价值都有具体数字或场景支撑
- [ ] **场景具体**：每个场景都有真实的使用示例
- [ ] **限制透明**：明确告知用户硬件要求和能力边界
- [ ] **无专业术语**：或专业术语都有通俗解释
- [ ] **设备不泛指**：面向特定产品线时，用具体产品名（如 reComputer Jetson / reComputer R），不要写"电脑"、"任何机器"等泛称
- [ ] **设备描述只写功能**：不要贴产品定位标签（如"边缘网关"、"边缘 AI 计算机"），只写设备在方案中做什么（如"运行 XX 服务"、"GPU 加速本地模型"）
- [ ] **技术工具名转为用户价值**：不要直接提技术工具名（如"部署 Ollama"），改为面向用户的说法（如"利用本地算力运行本地模型"），突出隐私/本地化等用户关心的价值
- [ ] **内容顺序正确**：核心硬件 → 网络要求 → 部署方案对比（如有）→ 可选功能（如有）
- [ ] **设备支持说明**：如有多型号支持（如 R1100/R2000），需注明"两款均支持"

### 部署页检查

- [ ] **Preset ID 一致**：YAML 中的 preset ID 与 guide.md 一致
- [ ] **中英文结构一致**：guide.md 和 guide_zh.md 的 preset/step/target ID 完全一致
- [ ] **接线说明完整**：每个需要硬件连接的步骤都有 `### 接线` 子节
- [ ] **故障排查完整**：每个步骤都有 `### 故障排查`（或 `### 故障排除`）子节（表格格式）
- [ ] **故障排查标题正确**：中文必须使用 `### 故障排查` 或 `### 故障排除`（不能有额外文字）
- [ ] **部署后指引**：需要用户后续操作的步骤（如 docker_deploy）有 `### 部署完成` 子节（如打开浏览器、创建账号）
- [ ] **成功页完整**：有 `# 部署完成` 区域，包含验证步骤
- [ ] **顺序合理**：先物理后软件，先准备后操作
- [ ] **详细数据面板**：对外提供 API 或数据流的步骤，检查部署页是否展示了连接详情（自动生成或通过 `data_channels` 显式配置），方便用户调试和二次集成

### 按方案类型的额外检查

**technical（技术演示）**：
- [ ] 首屏不是 API 文档：先讲用户能拿它接到什么系统，再讲端口/协议
- [ ] 有「部署后你会得到什么」或等价内容，把接口翻译为能力产物
- [ ] 输出接口明确：用户能知道部署后拿到什么数据、通过什么协议
- [ ] curl / 代码示例在部署完成、接口详情或 guide.md 中，不抢占介绍页首屏
- [ ] 不要过度包装成「方案」：技术演示的价值在于能力本身
- [ ] `output_interfaces` 与 description 中描述的接口一致
- [ ] 使用技术演示介绍页模板（能力 → 部署后得到什么 → 集成场景 → 接口 → 技术规格）

**solution（完整方案）**：
- [ ] 仪表板/UI 有截图或描述
- [ ] 业务流程完整：从部署到日常使用的链路都有说明
- [ ] 技术细节适度：用户关心「能做什么」而非「怎么实现」
- [ ] 使用完整方案介绍页模板（痛点 → 核心价值 → 适用场景 → 使用须知）

### 常见错误

| 错误 | 表现 | 修复方法 |
|------|------|----------|
| Preset ID 不一致 | 部署页无法加载 | 确保 YAML 和 guide.md 中的 ID 一致 |
| 缺少故障排查 | 用户遇到问题无指引 | 添加 `### 故障排查` + 表格 |
| 故障排查标题错误 | 中英文故障排查内容混杂显示 | 使用精确标题：`### 故障排查` 或 `### 故障排除`（中文），`### Troubleshooting`（英文） |
| 中英文 ID 不匹配 | 解析错误 | 检查两个文件的 `{#xxx}` 一致 |
| Target 无默认值 | 页面显示异常 | 添加 `default=true` 到一个 target |
| Target 内容未用子节包裹 | 选择卡片显示原始 markdown 文本 | 将表格/列表移到 `### Wiring` / `### 接线` 子节中 |
| 尖括号占位符未转义 | `<device-ip>` 等内容在页面上消失（被当作 HTML 标签） | **裸文本**：反斜杠转义 `\<device-ip\>`；**backtick/代码块内**：不转义（直接写 `<device-ip>`） |

---

## 六、常见文案问题及修复

### 高优先级问题（P0）

| 问题类型 | 表现 | 修复方法 |
|---------|------|---------|
| 术语堆砌 | 首段出现 3+ 专业术语 | 用「术语通俗化对照表」替换 |
| 价值模糊 | 无法 30 秒说清"干什么用" | 重写「这个方案能帮你做什么」段落 |
| 结构不一致 | 中英文步骤 ID 不匹配 | 对齐两个文件的 `{#xxx}` |
| 设备泛指 | 用"电脑"、"任何机器"代替具体产品名 | 替换为具体产品型号（如 reComputer R1100） |
| 技术工具名暴露 | 直接提"部署 Ollama"等工具名 | 改为用户价值描述（如"利用本地算力运行本地模型"） |
| 设备贴标签 | 用"边缘网关"等产品定位描述设备 | 只写功能（如"运行 XX 服务"） |
| 尖括号占位符未转义 | `<device-ip>`、`<jetson-ip>` 等被浏览器当 HTML 标签吞掉，页面内容显示为空 | **裸文本**中用反斜杠转义 `\<device-ip\>`；**backtick 内和代码块内不要转义**（反斜杠会原样显示） |
| 类型错配 | technical 方案用了业务场景写法，或 solution 方案缺少 UI/仪表板描述 | 按 `solution_type` 选择对应的介绍页模板 |

### 中优先级问题（P1）

| 问题类型 | 表现 | 修复方法 |
|---------|------|---------|
| 缺接线图 | 硬件连接方式不清晰 | 在 `### 接线` 子节添加图片和步骤 |
| 缺故障排查 | 部署失败后无指引 | 添加 `### 故障排查` 子节（表格格式） |
| 故障排查标题错误 | 中英文内容混杂显示 | 使用精确标题 `### 故障排查` 或 `### 故障排除` |
| 无默认 Target | 部署页显示异常 | 添加 `default=true` 到一个 target |
| technical 缺接口说明 | 技术演示没有说明输出什么数据、什么格式 | 添加「输出接口」段落，与 solution.yaml 中 `output_interfaces` 对齐 |

### 低优先级问题（P2）

| 问题类型 | 表现 | 修复方法 |
|---------|------|---------|
| 场景抽象 | 只说功能，不说具体怎么用 | 添加对话示例或操作流程 |
| 限制不透明 | 不告知能力边界 | 补充「使用须知」段落 |

---

## 七、最佳范例

### 介绍页范例：smart_warehouse

**优点**：
1. 痛点陈述具体："上手成本高——要培训、要记菜单"
2. 解决方案直白："把复杂操作变成说话"
3. 使用示例是真实对话："说'入库 5 台 Watcher'"
4. 设备支持多型号并注明："R1100/R2000（两款均支持）"
5. 部署方案对比表格清晰，放在最后不干扰核心信息

查看参考：
- `solutions/smart_warehouse/description.md`
- `solutions/smart_warehouse/description_zh.md`

### 部署页范例：smart_warehouse

**优点**：
1. 多 preset 支持（SenseCraft 云方案/私有云/边缘计算）
2. preset 说明包含设备表格 + 功能列表 + 前提条件
3. docker_deploy 类型有 local/remote targets
4. 每个步骤有故障排除表格
5. 成功页有验证步骤

查看参考：
- `solutions/smart_warehouse/guide.md`
- `solutions/smart_warehouse/guide_zh.md`

---

## 八、使用方法

### 创建新方案

1. 创建目录结构：
   ```bash
   mkdir -p solutions/your_solution_id/{gallery,devices}
   ```

2. 创建必需文件：
   ```
   solutions/your_solution_id/
   ├── solution.yaml       # 方案配置
   ├── description.md      # 英文介绍页
   ├── description_zh.md   # 中文介绍页
   ├── guide.md            # 英文部署页
   ├── guide_zh.md         # 中文部署页
   ├── gallery/            # 图片资源
   └── devices/            # 设备配置文件
   ```

3. 按本规范编写内容

4. 使用检查清单自检

### 优化现有方案

1. 读取现有文案
2. 对照检查清单找出问题
3. 按规范修改
4. 重点检查：
   - 术语是否通俗化
   - 中英文结构是否一致
   - 是否有具体场景和示例
   - 每个步骤是否有 `### 故障排除` 子节

---

## 九、解析器行为说明

### 自动解析内容

解析器从 `guide.md` / `guide_zh.md` 自动提取：

1. **Preset**：从 `## Preset: Name {#id}` / `## 套餐: 名称 {#id}` 提取
2. **Step**：从 `## Step N: Title {#id type=xxx ...}` / `## 步骤 N: 标题 {#id ...}` 提取
3. **Target**：从 `### Target: Name {#id ...}` / `### 部署目标: 名称 {#id ...}` 提取
4. **Wiring**：从 `### Wiring` / `### 接线` 子节提取图片和步骤列表
5. **Troubleshoot**：从 `### Troubleshooting`（英文）/ `### 故障排查` 或 `### 故障排除`（中文）子节提取
6. **Post-Deploy**：从 `### Deployment Complete`（英文）/ `### 部署完成`（中文）子节提取（步骤级别，H3）
7. **Success**：从 `# Deployment Complete` / `# 部署完成` 之后的内容提取（全局级别，H1）

> ⚠️ **子节标题必须精确匹配**：解析器使用正则表达式匹配子节标题，标题后不能有额外文字。例如 `### 故障排查指南` 不会被识别，必须是 `### 故障排查`。

### 结构校验

解析器校验中英文文件结构一致性：

- Preset 数量和 ID 一致
- 每个 Preset 下的步骤数量和 ID 一致
- 每个步骤的 type/required/config 一致
- 每个步骤下的 Target 数量和 ID 一致

### 错误处理

| 错误类型 | 说明 | 解决方法 |
|---------|------|----------|
| `PRESET_ID_MISMATCH` | 中英文 Preset ID 不一致 | 对齐两个文件的 `{#xxx}` |
| `STEP_ID_MISMATCH` | 中英文步骤 ID 不一致 | 对齐两个文件的 `{#xxx}` |
| `STEP_TYPE_MISMATCH` | 中英文步骤 type 不一致 | 对齐两个文件的 `type=xxx` |
| `INVALID_STEP_TYPE` | 无效的步骤类型 | 使用有效类型（见上方列表） |
| `DUPLICATE_STEP_ID` | 步骤 ID 重复 | 使用唯一的步骤 ID |

### 常见渲染问题

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 中英文故障排查内容混杂 | 中文故障排查标题不匹配（如用了 `### 故障排查方法`） | 使用精确标题：`### 故障排查` 或 `### 故障排除` |
| 故障排查表格没有显示在正确位置 | 子节标题后有额外文字 | 确保标题精确匹配，不要添加额外文字 |
| 部署完成/成功页内容部分消失 | 尖括号占位符（如 `<jetson-ip>`、`<device-ip>`）被浏览器解析为 HTML 标签并吞掉 | **裸文本**中反斜杠转义 `\<jetson-ip\>`；**backtick 内和 fenced code block 内不要转义**（反斜杠会原样显示为 `\<jetson-ip\>`），直接写 `<jetson-ip>` 即可 |
