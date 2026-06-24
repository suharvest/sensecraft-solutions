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
- 极少数纯硬件/纯云方案没有本地 dashboard 可指 → 在该 preset 上标 `verify_exempt: true` 豁免（CI 会接受）。

### 选择 verify 验证方式 + 能力不够怎么拓展

**(a) 怎么选** —— 看部署出来的东西是什么，对号入座：

| verify 类型 | 当部署的是… |
|---|---|
| `web_dashboard` | 一个网页 UI / 看板（Grafana、Web 应用）—— 本质是「打开这个 URL」 |
| `image_predict` | 视觉模型 —— 传一张图、看预测结果 |
| `text_chat` | LLM / 聊天 —— 输入 prompt、看回复 |
| `image_text_chat` | 视觉语言模型（VLM）—— 图 + 文字 prompt |
| `image_text_to_image` | 文生图 / 图生图 —— 输入提示词（或图），看生成的图 |
| `voice_chat` | 语音助手 —— 说话、听 ASR/TTS |
| `robot_inspect` | **机器人 / 机械臂** —— 实时观测面板，轮询机器人主容器的 `/observation` 端点显示关节/传感器状态 |
| `http_debug` | **其他任意 HTTP 接口** —— 发请求看响应的通用调试器（**通用兜底**） |
| 任意步加 `verify=true` | 把一个非标准步骤（如手动 demo）标成 verify 步 |

> 这张是常用速查；**权威完整清单**（含每个类型的配置字段）以 `spec/CONTRACT.md`「Deployer capabilities」表为准。

**(b) 没有合适类型怎么拓展**（按优先级，前 3 条都不改引擎就能做）：

1. **先用通用兜底**：服务暴露 HTTP API 但不是 chat/vision → 用 `http_debug`（任意请求/响应）；只是要打开个页面 → `web_dashboard`（任意 URL）。这俩能覆盖绝大多数「没有专门类型」的情况。
2. **自定义校验 / 健康检查**：在 device YAML 的 `actions.before` / `actions.after` 写 `run:` 脚本（设备上跑任意 shell，可 `sudo: true`）—— 做部署前预检、部署后健康检查。参考 `solutions/gpt_oss_20b/devices/jetson_deploy.yaml` 的 "Validate Jetson runtime"。**这是不改引擎就能拓展的主力。** 字段名（`actions` / `before` / `after` / `run` / `sudo`）以 `spec/device.schema.json` 为准。
3. **标记任意步**：`{#id type=... verify=true}` 把任意步骤当成 verify 步。
4. **以上都不满足**（需要一个全新的交互式 verify 类型 / 新 UI 控件）：这是**引擎（闭源）侧能力**，本仓库加不了 —— 向维护者提 issue 说明你要的交互形态。

> **关于插件**：App 还有一套**插件机制**（`spec/plugin.schema.json`，如内置的 AI 助手）——用户可自己做插件给 App 加**功能面板**（后端 router + 前端 overlay），无需改引擎。但插件目前**只能加 App 级功能面板，注册不了方案步骤里的 `type=`（deploy/verify 类型）**。「用插件原型化自定义 verify/deploy 类型、好的再收编成官方类型」这条流水线还在设计中。

**校验现在查得更全**：`solutionctl validate --check-urls` 会查 schema、引用文件存在、i18n 完整、重复 id、device-ref、**死链（404/410）**、compose/flow 可解析、EN/ZH 结构一致。本地提交前自己跑一遍即可和 CI 一致。
> 说明：`--check-urls` 把 401/403/408/429 当「资源在、只是挡爬虫/限流」放过（如 `files.seeedstudio.com` 套了 Cloudflare，对脚本返回 403 但浏览器/App 正常显示）——这些图片**可放心用**，只有 404/410 这种真死链才报错。

**诚实标注验证等级（可选但推荐）**：在 preset 上加 `verified:` 列表对用户透明——
- `deploy-smoke`：声明它能在 CI 里起得来。**前提**：该 preset 有一个 `type: docker_deploy` 的 device YAML 在 `docker:` 块里标了 `ci_smoke: true`（仅限轻量 x86 栈；GPU/Jetson/烧固件的别标，CI 起不来）。validate 会强制这个一致性，标了 deploy-smoke 却没 ci_smoke gate 会报错。
  > **注意**：`ci_smoke` 是校验器直接从 raw YAML 读取的键，**不在** Pydantic `DockerConfig` schema 里——照写就行，别因为 schema 里没有它就以为是多余字段而删掉。
- `hardware`：你（或维护者）在真设备上跑过。
- 结果对不对（模型准不准等）永远不自动验证，靠人。

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

> **verify 步要复用上游 deploy 的 host** —— 在 verify 步的 device YAML 里写 `inherit_host_from: <step_id>` 显式声明（`inherit_host_from` 是 device schema 顶层字段，见 CONTRACT）。
>
> **`<step_id>` 是上游那个 deploy `## Step` 的 id（guide.md 里 `{#...}` 的值），不是 device id、也不是 target id。** 端点模板用 `{{deploy.host}}`，引擎会替换成被继承步骤实际选定的 host。多 deploy 步的方案必须显式写，自动 fallback（"最近的 deploy 步"）会选错。
>
> 最小 `web_dashboard` verify device YAML：
>
> ```yaml
> version: "1.0"
> id: dashboard
> name: Open Dashboard
> type: web_dashboard
> inherit_host_from: web        # ← 上游 deploy 步的 STEP id（## Step {#web ...}）
> web_dashboard:
>   url: "http://{{deploy.host}}:8080"   # {{deploy.host}} = 继承到的 host
>   title: My Dashboard
>   description: 页面能加载出数据即代表部署成功。
> ```

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
- 设备/封面图片用稳定可达的源：方案自带本地图（`gallery/cover.png`，相对路径）或公共 CDN（`files.seeedstudio.com`、`media-cdn.seeedstudio.com`、`sensecraft-statics.seeed.cc` 都行）。`--check-urls` 只把 404/410 当死链；`files.seeedstudio.com` 的 Cloudflare 403 会被放过，可放心用。

#### 最小可复制的 `solution.yaml` 骨架（solution 类型）

下面是一个**经 `solutionctl validate` 通过**的最小骨架（一个 `docker_deploy` 部署步 + 一个 `web_dashboard` verify 步）。复制后改 id/name/镜像即可。完整字段含义查 `spec/CONTRACT.md`。

```yaml
version: "1.0"
id: hello_dashboard
name: Hello Dashboard
name_i18n:
  zh: 你好看板

intro:
  summary: A minimal one-click web dashboard you can deploy and open.
  summary_i18n:
    zh: 一个可一键部署并打开的最小 Web 看板。
  description_file: description.md
  description_file_i18n:
    zh: description_zh.md
  cover_image: gallery/cover.png        # 本地相对路径，或公共 CDN URL 均可
  category: sensing
  solution_type: solution               # solution | technical
  tags: [demo, dashboard]

  device_catalog:                        # 介绍页展示的设备（device_ref 来源）
    server:
      name: Edge Server
      name_i18n:
        zh: 边缘服务器
      image: gallery/cover.png
      product_url: https://www.seeedstudio.com/reComputer-R1100-p-6253.html
      description: Runs the dashboard container
      description_i18n:
        zh: 运行看板容器

  presets:
    - id: default                        # 必须与 guide.md 的 {#default} 一致
      name: Default
      name_i18n:
        zh: 默认
      description: Deploy the dashboard on a server.
      description_i18n:
        zh: 在服务器上部署看板。
      verified:
        - deploy-smoke                   # 需配套 device YAML 的 docker.ci_smoke: true
      device_groups:                     # 介绍页展示所需设备，options[].device_ref 必须在 device_catalog 中
        - id: host
          name: Server
          name_i18n:
            zh: 服务器
          type: single
          required: true
          options:
            - device_ref: server
          default: server

  stats:
    difficulty: beginner
    estimated_time: 5min

deployment:                              # 部署步骤本身从 guide.md 解析，这里只给文件名
  guide_file: guide.md
  guide_file_i18n:
    zh: guide_zh.md
  selection_mode: sequential
```

配套的最小 `devices/web.yaml`（`docker_deploy` + ci_smoke）：

```yaml
version: "1.0"
id: web
name: Deploy Dashboard
type: docker_deploy
docker:
  ci_smoke: true                         # raw-YAML 键，不在 Pydantic schema 里（见 F2 说明）
  compose_file: ../assets/docker/docker-compose.yml
docker_remote:
  compose_file: ../assets/docker/docker-compose.yml
  remote_path: /opt/hello_dashboard      # remote_path 必填，无 solution_id 兜底
user_inputs:
  - id: host
    name: Server IP
    type: text
    default: "127.0.0.1"
    required: true
```

`web_dashboard` verify device YAML 见上方 Step 10 的 F4 范例；guide.md 见 Step 10 的 Step/Target 格式。

`description.md` 遵循 `skills/solution-copywriting` 规范。

---

## Phase 4: 校验

**Step 12**：用离线工具 `solutionctl` 校验方案符合公开契约。

在本仓库内（推荐，自动使用 workspace 里的 spec/ 和解析器）：

```bash
uv run --package sensecraft-solutionctl solutionctl validate solutions/<solution_id> --spec-dir spec
```

校验工具从本仓库内运行（clone-first，不依赖 PyPI 发布）。如果要在仓库外的位置校验某个 solution，指向本仓库的 `spec/` 即可：

```bash
uv run --package sensecraft-solutionctl solutionctl validate <solution_path> --spec-dir <repo>/spec
```

`solutionctl validate` **完全离线**（零引擎依赖），检查：
- **solution.yaml / device YAML** 是否符合 `spec/*.json` schema；
- **guide.md / guide_zh.md** Step/Target 语法与 `type=` 是否为合法 deployer 类型（来自 `spec/capabilities.json`）；
- **每个 preset 至少 1 个 verify step**（`web_dashboard` / `image_predict` / `text_chat` / `voice_chat` / `http_debug` 等，或 `verify=true` 标记的步骤）；
- **孤儿 H2**：每个 `##` 必须是 `## Preset:` / `## 套餐:` 或 `## Step N:` / `## 步骤 N:`，其它顶层 H2 报错；
- **target 命名**：`### Target` 名不得是方向词（Local / Remote / 本地 / 远程 / 本机 / 远端）；
- **中英文结构一致**：guide.md 与 guide_zh.md 的 preset / step / target ID 必须一一对应。

**必须全绿**才算合格。

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
uv run --package sensecraft-solutionctl solutionctl validate solutions/<solution_id> --spec-dir spec
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
