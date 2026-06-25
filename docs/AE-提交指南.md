# AE 指南:把你的项目变成「一键部署方案」

这份文档教你把一个**已经能跑起来的项目**（比如一套 Docker 服务、一个固件、一个 reCamera 流程）变成 SenseCraft App 里**用户点一下就能部署**的方案，并提交上线。

> 不需要你懂很多代码。难的部分交给 AI 助手（Claude Code / Codex）+ 现成的 skill 做，你主要负责**提供信息**和**自己验证**。

---

## 全流程一张图

```
准备材料 →  ① 转化（AI 生成方案）→  ② 自己验证（本地校验 + App 预览）
                                              ↓
        上线（App 里能看到） ← ④ 合并(维护者) ← ③ 提交 PR（CI 自动检查）
```

四步：**转化 → 自验 → 提交 → 上线**。下面逐步讲。

---

## 开始前：准备工作（一次性）

1. **装好 SenseCraft App**（用来预览和测试部署）。按平台下载安装包（链接始终指向最新版）：
   - macOS（Apple Silicon）：<https://appcenter.seeed.xyz/SenseCraft.Solution/SenseCraft.Solution_aarch64.dmg>
   - Windows（x64）：<https://appcenter.seeed.xyz/SenseCraft.Solution/SenseCraft.Solution_x64-setup.exe>
   - Linux（arm64）：<https://appcenter.seeed.xyz/SenseCraft.Solution/SenseCraft.Solution_arm64.deb>
   > 「导入方案预览」需 ≥ 0.6.1（上面是最新版，已包含）。
2. **装 git 和 uv**（uv 是 Python 工具）：
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. **把方案仓库克隆下来**：
   ```bash
   git clone https://github.com/suharvest/sensecraft-solutions.git
   cd sensecraft-solutions
   uv sync
   ```
4. **打开 AI 助手**（Claude Code）。clone 下来后它会**自动认到本仓库的 skill**——转化、文案、校验、部署都有现成 skill 帮你。

---

## 你需要准备哪些信息（最重要）

转化之前，把下面这些**先想清楚、准备好**。AI 助手会问你这些，准备越全，生成越准：

| 信息 | 说明 | 例子 |
|---|---|---|
| **这个项目是干嘛的** | 一句话价值 + 给谁用 | 「语音操控库存管理，仓库员工说一句就能入库」 |
| **用什么硬件** | 跑在哪些设备上 | reComputer R1125、SenseCAP Watcher |
| **怎么部署** | 部署方式 | Docker Compose / 烧固件 / reCamera 流程 |
| **部署素材** | 能让它跑起来的文件 | `docker-compose.yml`、固件 `.bin`、`flow.json` |
| **部署步骤** | 你当初是怎么一步步装好的 | 「①起后端服务 ②连 Watcher ③打开看板」 |
| **怎么验证成功** | 用户怎么知道装好了 | 「打开 `localhost:3000` 看到看板有数据」 |
| **图文素材** | 封面图、截图、Demo（可选但强烈建议） | 产品图、效果截图、演示 gif |
| **中英文文案** | 介绍页 + 部署指南，**中英都要** | 自己写或让 AI 帮你润色 |

> 💡 最关键的是**「部署素材 + 部署步骤」**——这是把你的项目变成一键部署的核心。其余文案/图片 AI 能帮很多。

---

## 第 ① 步：转化（AI 帮你生成方案）

在 AI 助手里说：

> **「用 author-solution skill，把这个项目转成一个 solution。资料在这里：<贴你的 wiki 链接 / 文档路径>」**

AI 会按规范生成一个方案目录（在 `solutions/<你的方案名>/`），长这样：

```
solutions/你的方案/
├── solution.yaml          # 方案配置（硬件、套餐、中英文名）
├── description.md / _zh    # 介绍页文案（英 / 中）
├── guide.md / _zh          # 部署指南 + 步骤（英 / 中）
├── devices/                # 每个步骤对应的设备配置
├── docker/                 # compose 文件等部署产物
└── gallery/                # 封面 / 截图 / Demo
```

转化过程中 AI 会问你上一节那些信息——**照实回答**即可。文案不满意可以让它用 `solution-copywriting` skill 再润色。

> ⚠️ 二进制大文件（固件 `.bin`、模型、`.deb`）**不要直接放仓库**——传到 CDN，方案里用链接引用。AI 会按规范处理；不确定就问它。

---

## 第 ② 步：自己验证（提交前必做）

### 2.1 本地校验（检查写得对不对）

```bash
uv run --package sensecraft-solutionctl solutionctl validate solutions/你的方案 --check-urls
```

它会检查：字段对不对、引用的文件在不在、中英文齐不齐、**链接有没有失效**、能不能部署起来等。**有红色报错就让 AI 帮你修，改到全绿**。

### 2.2 在 App 里预览（看长啥样）

让 AI 助手用 **`preview-solution-content` skill** 把你的方案导进**本机已装的 App** 预览（不影响别人，只在你电脑上看）：

> **「用 preview-solution-content skill，把 `solutions/你的方案` 导进 App 让我看看」**

然后在 App 里：
- 方案列表能看到你的方案 ✅
- 点进去，介绍页**图片正常、文案通顺、中英文都对** ✅
- 部署页**步骤清晰、套餐选项正常** ✅

### 2.3 真测一次部署（强烈建议）

按部署页的步骤**真在设备上部署一次**，确认能成功、效果对。这是唯一能确认「真能用」的方法。
> 自动化只能保证「能装起来」，**结果对不对（识别准不准、语音灵不灵）只能你亲自测**。

---

## 第 ③ 步：提交（PR）

自验通过后提交。让 AI 助手帮你走 git（它会做）：

> **「帮我把 `solutions/你的方案` 提交成一个 PR 到这个仓库」**

或手动：
```bash
git checkout -b add-你的方案
git add solutions/你的方案
git commit -s -m "feat(solutions): 你的方案"
git push   # 然后在 GitHub 上开 Pull Request
```

提交后，**CI 会自动检查**（你不用管，等结果）：
- `guard` —— 边界检查
- `validate` —— 就是 2.1 那套（含死链检查）
- `docker-smoke` —— 如果是 Docker 方案、能在 CI 起服务

**全绿才能合并**。红了点进去看哪条挂了，让 AI 帮你修、再推。

---

## 第 ④ 步：上线（最终显示出来）

1. **维护者 review + 合并**你的 PR（会人工看渲染效果 + 该硬件验证的硬件验证）。
2. 合并后，维护者把方案同步进引擎并**推 OTA**。
3. **用户的 App 下次启动就会自动更新**，看到你的方案——无需重装 App。

---

## ✅ 自己验证「整个流程成功了」的检查清单

| 阶段 | 怎么确认成功 |
|---|---|
| 转化 | `solutions/你的方案/` 目录生成,有 solution.yaml + 中英文 guide/description |
| 本地校验 | `solutionctl validate ... --check-urls` **全绿无报错** |
| App 预览 | App 里能看到方案，图片/文案/中英文都正常，部署页步骤清晰 |
| 真机部署 | 按步骤在真设备上**部署成功 + 效果对** |
| 提交 | PR 的 CI **guard / validate / docker-smoke 全绿** |
| 上线 | 合并后，App 更新能看到你的方案、能一键部署 |

**六项全打勾 = 成功。**

---

## 常见问题

- **校验报「referenced file not found」** → 你引用了不存在的文件，让 AI 检查路径。
- **校验报死链（4xx）** → 引用的图片/链接失效了，换成有效的。
- **每个套餐必须有「验证步骤」** → 让用户立刻看到效果。solution 类用看板(web_dashboard)，技术类用交互式验证（拍照预测 / 语音对话等）。AI 会提醒你。
- **内置验证方式不够用怎么办** → 大多数情况能兜底：服务有接口就用「任意接口调试器」(`http_debug`)，只是要打开个页面就用「打开网址」(`web_dashboard`)。要做自定义检查（比如部署前/后跑个健康检查脚本），可以让 AI 在设备配置里加 `actions` 脚本。实在需要全新的交互形态，[提一个能力需求 issue](https://github.com/suharvest/sensecraft-solutions/issues/new?template=new-capability-request.md)（开发者可用插件原型化，见 `docs/plugin-development.md`）。细节让 AI 看 `skills/author-solution`。
- **二进制大文件怎么办** → 不放仓库，传 CDN 用链接引用（参考 `solution-assets`，或直接问维护者）。
- **不会写中英文文案** → 让 AI 用 `solution-copywriting` skill 帮你写/润色。
- **不会用 git / 开 PR** → 直接让 AI 助手帮你做，或把方案目录给维护者代提。

---

> 需要从命令行/CI 部署（不开 App）→ 看 `skills/solution-cli`。完整字段规范 → 看 `spec/CONTRACT.md`。写新方案的完整流程 → `skills/author-solution`。
