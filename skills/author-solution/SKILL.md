---
name: author-solution
description: 从原始资料创作一个符合 spec 的一键部署 IoT 方案。基于 Wiki/文档/Git 仓库复现方案，提炼最简路径，输出符合公开契约（spec/CONTRACT.md）的 solution.yaml / guide.md / description.md，并用离线工具 solutionctl 校验。适用于：从资料创建新方案、提炼最简部署路径、校验方案合规性。
argument-hint: "<资料来源URL或路径> [solution_id]"
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, WebFetch, WebSearch
---

# Author Solution Skill

从原始资料（Wiki / 文档 / Git 仓库）创作一个符合 SenseCraft 方案契约的一键部署方案。

## 调用方式

```
/author-solution https://wiki.seeedstudio.com/xxx smart_factory
/author-solution ./raw_materials/ my_solution
/author-solution https://github.com/xxx/xxx       # 自动生成 solution_id
```

`$ARGUMENTS` 包含：资料来源（URL 或本地路径）+ 可选的 solution_id。**如果用户指定了某个 preset，只复现该 preset。**

所有 device YAML 字段、guide.md Step/Target 语法、`docker_deploy` 派生规则等**机器可读契约**以 **`spec/CONTRACT.md`** 为唯一权威来源（配套 `spec/*.json` schema）。本 skill 只讲创作流程；遇到字段细节一律查 CONTRACT。

---

## 核心理念

- **目标用户**：解决方案商（无开发能力）
- **最小工作单元**：**preset**（而非整个 solution）
- **最简路径**：去掉所有非必要步骤，让用户用最少操作完成部署
- **预配置优先**：能提前配好的全部预配好，用户只需做「连接」和「点击」
- **部署 + 验证完整闭环**：部署完不算完，要让用户立刻看到效果

**每个 preset 必须至少有一个 verify 步骤**（让用户立刻看到结果）。`solutionctl validate` 强制检查 verify step 存在。solution 类用 `type=web_dashboard`；technical 类用交互式 verify（`image_predict` / `text_chat` / `voice_chat` / `http_debug` 等）。可用的 verify/step 类型见 `spec/CONTRACT.md`「Deployer capabilities」表。

---

## 整体流程

```
资料 → 阅读分析 → 手动部署（第一轮）→ 整理配置文件 → 校验（solutionctl）→ 输出文档
                          ↑                                    |
                          └─────── 修复配置文件 ←──────────────┘
```

第一轮手动部署是为了理解方案、发现问题、积累经验。
之后用生成的配置文件走 `solutionctl validate`，验证配置文件符合契约。

---

## Phase 1: 资料收集与分析

**Step 1**：读取/抓取原始资料
- URL → WebFetch
- 本地路径 → 读取所有相关文件
- Git 仓库 → clone 并分析 README、docs、docker-compose 等

**Step 2**：提取关键信息，生成结构化摘要

```
## 方案概述
- 名称 / 解决什么问题 / 核心硬件 / 核心软件

## 部署步骤（原始）
1. ...

## 简化方案
- 合并/删除的步骤 / 预配置的内容 / 暴露的配置项

## 方案类型判定（solution / technical）
```

### 方案类型判定（必须做）

- **完整方案 (solution)**：打通多个技术模块形成业务闭环，有用户能直接使用的看板/管理界面（Grafana / Frigate / Node-RED Dashboard 等）
- **技术演示 (technical)**：单一 AI 能力或数据处理管道，主要价值在于输出数据/接口供其他系统集成

| 特征 | → solution | → technical |
|------|-----------|------------|
| 有面向用户的看板/仪表盘 | ✓ | |
| 端到端业务闭环 | ✓ | |
| 主要是单一 AI 能力 / 数据管道 | | ✓ |
| 主要价值在输出数据/接口 | | ✓ |
| 组合了多个独立功能模块 | ✓ | |

**注意**：有 Frigate 看板、Grafana 仪表盘的就是完整方案，不要因为「用了 AI 检测」就标 technical。

类型差异要点：
- technical 需声明输出接口（每个 interface 至少有 port/endpoint/topic/path/url 之一）
- 无论哪种类型，需要外部输入（摄像头/传感器）就声明输入要求
- 字段名以 `spec/solution.schema.json` 为准

**technical 文案边界（必须执行）**：
- 技术演示不是 API 文档。介绍页首屏先讲「这个能力能接到什么系统、补上什么能力」，再讲端口/协议。
- 正文必须把接口翻译成人能理解的产物，例如「本地听写服务」「可播放音频流」「识别结果 JSON」，不要只写 ASR/TTS/RTSP/RKNN。
- curl/代码示例不要放在介绍页前半段；放到 guide.md 的部署完成、接口详情或验证步骤里。
- 如果前端已经根据输出接口自动展示接口卡片，description 里不要重复堆完整 API 表，只保留通俗解释或简化表。

**Step 3**：向用户确认简化方案 + **修改边界**：
- 默认只改部署产物（docker-compose.yml、flow.json、device YAML），不改应用源码
- 用户可能允许改 docker-compose 中的环境变量、端口映射等

---

## Phase 2: 手动部署（第一轮）

亲手走通全流程，理解每一步实际发生了什么。

**Step 4**：准备目标设备的连接信息（IP / SSH 用户名密码 / 串口等）。

**Step 5**：逐步执行简化后的部署，直接在目标设备上操作：

```bash
# Docker
ssh user@device "cd /opt/myapp && docker compose up -d"
# 固件
esptool.py --chip esp32s3 write_flash 0x10000 firmware.bin
# reCamera
scp package.deb recamera@192.168.42.1:/tmp/ && ssh recamera@192.168.42.1 "opkg install /tmp/package.deb"
```

每一步记录：实际执行的命令和输出、遇到的问题、用户需要填的值（→ `user_inputs`）、可合并/自动化的步骤（→ `actions`）。

**Step 6**：验证最终结果，Web 界面截图录屏留证。

**Step 7**：记录部署笔记，作为下一步生成配置文件的输入。

### Phase 2.5: HuggingFace 资源下载规范

需要从 HuggingFace 拉模型/权重时，**不要在镜像里装 `huggingface_hub`**（库 + 依赖体积大，会让镜像膨胀几百 MB）。改用宿主机 curl 下载，模型 bind-mount 进容器：

- 下载脚本里不要硬编码 `huggingface.co`，用环境变量 `HF_ENDPOINT` / `HF_ENDPOINT_HOST` 控制 endpoint，受限网络下可切换镜像
- 验收：下载脚本的 curl/wget 命令里不出现硬编码 `huggingface.co`（注释里写没关系）

---

## Phase 3: 整理配置文件

**Step 8**：生成 solution 目录结构（**扁平结构，不要用 intro/、deploy/sections/ 等老结构**）

```
solutions/<solution_id>/
├── solution.yaml
├── description.md / description_zh.md
├── guide.md / guide_zh.md
├── gallery/
├── devices/               # 设备配置 YAML
└── assets/                # 部署产物（compose、flow.json 等）
```

**Step 9**：编写设备配置 YAML

device YAML 的字段、各部署类型（`docker_local` / `docker_remote` / `esp32_usb` / `recamera_cpp` / ...）的必填字段，全部以 **`spec/CONTRACT.md`** 的「Device schema fields」和「Deployer capabilities」表为准（schema 文件：`spec/device.schema.json`）。关键映射：

| 手动部署中做了什么 | 配置文件中怎么写 |
|---|---|
| `docker compose up`（本地） | `type: docker_local`，`docker.compose_file` |
| SSH 到远程跑 docker | `type: docker_remote`，`docker_remote.compose_file` |
| 同一方案既支持本地又支持远程 | guide.md 里写 `type=docker_deploy`（见 Step 10），由引擎派生 local/remote 两个视图 |
| `esptool.py write_flash` | `type: esp32_usb`，`firmware.flash_config` |
| `opkg install xxx.deb` | `type: recamera_cpp`，`binary` |
| 手动跑的 shell 命令 | `actions.before` / `actions.after` |
| 用户需要填的值 | `user_inputs` 列表 |

> **`docker_deploy` 派生规则**（一个 device YAML 写成 `type: docker_deploy`，引擎在加载时拆成 `docker_local` + `docker_remote` 两个视图）的完整规则见 `spec/CONTRACT.md`「docker_deploy view 派生规则」。要点：`remote_path` 必填且无 `solution_id` 兜底；`remote_overrides.actions` 是整体替换不是合并。

**Step 10**：编写 guide.md

每个 `## Step` 对应一个部署动作。Step / Target / Mode 的完整语法、`{#id ...}` 属性块解析规则见 **`spec/CONTRACT.md`**「guide.md Step/Target 语法」和「guide.md heading keywords」。标准格式：

```markdown
## Step 1: Deploy Services {#backend type=docker_deploy required=true config=devices/docker.yaml}

One-line description.

### Target {#local type=local config=devices/docker.yaml default=true}

### Target {#rk3576 type=remote device_name="RK3576" config=devices/docker_remote.yaml}

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Docker not found | Install Docker Desktop |
```

> **Target 命名规范**：
>
> **Target 标题不写名字** — 写成 `### Target {#id ...}`，冒号和名字都省略。前端会根据 `type=` + `device_name=` 自动从 i18n 决定显示名：
>
> | markdown | 用户看到（中文） | 用户看到（英文） |
> |---|---|---|
> | `type=local` | 在这台电脑上部署 | Deploy on This Machine |
> | `type=remote`（无 device_name） | 部署到另一台设备 | Deploy to Another Device |
> | `type=remote device_name="Jetson"` | 部署到 Jetson | Deploy to Jetson |
>
> **禁止写"本地/远程/Local/Remote"** 等方向词作为 Target 名。
>
> **`device_name=` 只写芯片/产品名**，不带括号备注 — ❌ `"RK3576 (reComputer / ROCK 5T)"` → ✓ `"RK3576"`。
>
> **Target ID 命名**：
> - `type` 是部署类型识别依据（local / remote），不是 ID
> - 本地部署 ID 可叫 `local` 或加前缀（`backend_local`）
> - 远程部署 ID 用具体设备/服务名（如 `rk3576`），不要笼统叫 `remote`

> **多个 docker_deploy 步部署到同一台机器** —— 用 `target_inherit_from=<upstream_step_id>` 让下游步自动跟随上游的 local/remote 选择。只继承 method（local/remote），不绑死 target id。同一 preset 内才能继承；引用的 step 必须在自己之前、且自己有 targets。

> **verify 步要复用上游 deploy 的 host** —— 在 verify 步的 device YAML 里写 `inherit_host_from: <step_id>` 显式声明（`inherit_host_from` 是 device schema 顶层字段，见 CONTRACT）。端点模板用 `{{deploy.host}}`。多 deploy 步的方案必须显式写，自动 fallback 会选错。

> **`### Wiring` 段严格限定为接线说明**，不要塞 Docker 安装、API key 获取等非接线内容。

> **guide.md 里 H2 只能是 `## Preset:` 或 `## Step N:`（必带 `{#id}`）** —— 其他任何顶层 `## ...`（如 `## Quick Verification` / `## API Reference` / `## Next Steps`）都是孤儿 H2，校验会拦。
>
> - 部署完成后的总结/验证/链接 → 写成 `### Deployment Complete`，放在该 preset **最后一个 step 的所有 `### Target` 之前**。
> - 附录小节（验证、API 表、下一步等）→ 写成 `#### XXX`（H4），嵌在 `### Deployment Complete` 下面。
> - 前置条件 / 系统要求 / 介绍性文字 → 放进 `description.md`，guide.md 只讲怎么部署。

```markdown
## Step 3: Open Dashboard {#dashboard type=web_dashboard ...}

### Deployment Complete

Your service is now running.

#### Quick Verification
1. Open http://...

#### Next Steps
- [Documentation](https://...)

### Target {#local type=local ...}
```

**Step 11**：编写 solution.yaml + description

字段以 `spec/solution.schema.json` 和 `spec/CONTRACT.md`「Solution schema fields」为准。关键点：
- 方案类型（solution / technical）必须明确
- technical 类需声明输出接口（含路由标识 port/endpoint/topic/path/url）
- 需要外部输入的方案声明输入要求
- `device_ref` 必须能在 `intro.device_catalog` 中找到
- 设备图片用稳定 CDN 域名

`description.md` 遵循 `skills/solution-copywriting` 规范。

---

## Phase 4: 校验

**Step 12**：用离线工具 `solutionctl` 校验方案符合公开契约：

```bash
uv run --package solutionctl solutionctl validate solutions/<solution_id> --spec-dir spec
```

`solutionctl validate` 离线检查：solution.yaml / device YAML 是否符合 `spec/*.json` schema、guide.md Step/Target 语法、每个 preset 是否有 verify step、孤儿 H2、target 命名等。**必须全绿**才算合格。

失败 → 修复循环（修改 device YAML / compose / flow.json / guide.md，**不改应用源码**），重跑直到通过。

---

## Phase 5: 输出文档与素材

**Step 13**：截图和封面图
- 优先复用 Wiki 原图
- 有 dashboard 的方案，用 dashboard 实拍截图当 cover，1280x720，必须有真实数据
- 录屏作为 Demo

**Step 14**：确保 description / guide 文件完整。所有文件存在、步骤定义齐全。

---

## Phase 6: 文案优化

**Step 15**：用 `skills/solution-copywriting` 做全维度检查（介绍页按类型选模板、technical 首屏可读性、部署页 Troubleshooting/Wiring 子节、中英文 ID 一致、术语通俗化）。审核改动（P0 必须修，P1 应该修，P2 视情况）。

---

## Phase 7: 交付前自检

**Step 16**：跑校验 —— 失败必须修复后再交付。

```bash
uv run --package solutionctl solutionctl validate solutions/<solution_id> --spec-dir spec
```

**人眼自检清单**（工具查不到的）：
- [ ] 打开 cover_image，画面有真实数据、无空 dashboard、无 loading 状态
- [ ] 每个 deploy step 都对得上一个 verify step（看 guide.md 步骤列表）
- [ ] `### Wiring` 段确实只放接线说明
- [ ] description 风格匹配类型（solution: 四段式 / technical: 能力产物 → 集成场景 → 接口详情）
- [ ] technical 首屏不是端口表或 curl；首段专业缩写不超过 2 个，并有通俗解释

---

## 输出清单

- [ ] `solution.yaml` — preset ID 与 guide.md 一致，方案类型已设置
- [ ] technical 类已声明输出接口（每个含 routing 字段）
- [ ] technical 介绍页先讲能力产物和集成场景，再讲接口
- [ ] 需要外部输入的方案已声明输入要求
- [ ] `description.md` + `_zh.md` — 类型对应风格
- [ ] `guide.md` + `_zh.md` — 中英文结构一致，每个 preset 至少 1 个 verify step
- [ ] `devices/` — 配置文件，`solutionctl validate` 通过
- [ ] `gallery/` — 封面图、步骤截图、Demo（cover 有真实数据）
- [ ] `assets/` — 部署产物
- [ ] 手动部署通过（Phase 2）
- [ ] `solutionctl validate solutions/<id> --spec-dir spec` 全绿（Phase 4 / Phase 7）
- [ ] 文案优化完成（Phase 6）

---

## 相关 skill / 契约

| 资源 | 内容 |
|---|---|
| `spec/CONTRACT.md` | 机器可读契约：device/solution schema 字段、guide.md Step/Target 语法、docker_deploy 派生规则、heading 关键字 |
| `spec/*.json` | solution / device / capabilities / plugin schema |
| `skills/solution-copywriting` | 文案优化规范（介绍页四段式、术语通俗化、质量检查） |
| `skills/prepare-docker-images` | 准备 Docker 镜像与 compose 文件 |
| `skills/prepare-recamera-nodered` | 准备 reCamera Node-RED flow |
| `skills/prepare-esp32-firmware` | 准备 ESP32 固件 |
| `skills/prepare-himax-firmware` | 准备 Himax WE2 固件与 AI 模型 |
| `skills/prepare-deb-package` | 准备 reCamera C++ deb 包 |
| `skills/integrate-jetson-solution` | 从结构化输入生成 Jetson docker_remote 方案 |
