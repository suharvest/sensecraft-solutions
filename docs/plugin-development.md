# 插件开发指南：给方案补一个全新的能力 / Plugin Development

> 适用对象：在写方案（`author-solution`）时发现**内置的 verify/deploy 类型都不合适**、需要一个**全新交互形态**的开发者。
>
> 先确认你真的走到这一步了 —— 90% 的「没有合适类型」其实用兜底就能解决，**别急着写插件**。决策顺序见
> [`skills/author-solution/SKILL.md`](../skills/author-solution/SKILL.md) 的「选择 verify 验证方式 + 能力不够怎么拓展」一节：
>
> 1. 通用兜底：`http_debug`（任意 HTTP 接口）/ `web_dashboard`（任意 URL）
> 2. 自定义校验：设备 YAML 的 `actions.before/after` 跑 `run:` 脚本
> 3. 标记任意步：`{#id type=... verify=true}`
> 4. **以上都不够、确实需要一个全新的交互式类型** → 才是本文档要讲的「插件」
>
> 还不够、或者你想把这个类型**收编成官方内置类型**？走
> [能力需求 issue](#5-不写插件向维护者提需求) 这条路。

---

## 0. 边界先说清楚

本仓库（`sensecraft-solutions`）是 **内容 + 契约 + 工具** 层，Apache-2.0。**配置引擎本身（deployer 运行时、设备通信、桌面 App、`plugin_manager`）是闭源的**，不在本仓库。

因此本文档只能、也只需要讲清楚 **公开契约这一侧**：
- 插件清单 `plugin.json` 的字段（由 [`spec/plugin.schema.json`](../spec/plugin.schema.json) 定义，**这是公开的**）。
- 方案侧怎么接线（`requires_plugins:` + 命名空间 `type=` + `verify=true`）。
- `solutionctl validate` 对插件类型的行为。
- catalog 限制。

至于 **deployer 后端类怎么实现**（`BaseDeployer` 子类、`category` / `ui_traits`、前端 renderer 的宿主 API），那些 API 活在闭源引擎仓库里。本文给出 manifest 契约和接线方式；后端实现细节请向维护者要引擎侧 SDK 文档，或走 [issue](#5-不写插件向维护者提需求)。

---

## 1. 插件清单 `plugin.json`

一个插件是一个目录，根部放 `plugin.json`。**必填**字段只有三个：`id` / `name` / `version`。

最小可用清单（贡献一个**全新 verify 类型**）：

```json
{
  "id": "myplugin",
  "name": "My Custom Verify",
  "name_zh": "我的自定义验证",
  "version": "1.0.0",
  "min_app_version": "1.4.0",
  "contributes": {
    "deployers": [
      {
        "type": "robot_arm",
        "module": "backend.deployer:RobotArmVerifyDeployer",
        "category": "verify",
        "renderer": "robot_arm_panel"
      }
    ]
  }
}
```

字段对应 [`spec/plugin.schema.json`](../spec/plugin.schema.json)：

| 字段 | 说明 |
|---|---|
| `contributes.deployers[].type` | **裸**类型名（如 `robot_arm`）。注册时引擎会自动加上命名空间，变成 `myplugin/robot_arm`。 |
| `contributes.deployers[].module` | 可导入的 deployer 类，如 `backend.deployer:RobotArmVerifyDeployer`。必须继承引擎的 `BaseDeployer` 并暴露 `category` / `ui_traits`（引擎侧 API）。 |
| `contributes.deployers[].category` | `deploy` 或 `verify`。`verify` = 后端 no-op + 前端交互式 renderer。 |
| `contributes.deployers[].renderer` | 可选。前端 renderer 名；不写则回退到通用 auto UI（够用就别写）。 |
| `backend.module` / `backend.websocket` | 可选。后端路由模块 / 是否暴露 WebSocket。 |
| `frontend.entry` / `css` / `i18n` / `type` | 可选。前端入口、样式、多语言、挂载模式（如 `overlay`）。 |
| `permissions` | 申请的能力，如 `["network", "websocket"]`。 |
| `settings.schema[]` | 声明式设置表单字段。 |

完整字段以 [`spec/plugin.schema.json`](../spec/plugin.schema.json) 为准（schema 是 `additionalProperties: true`，引擎可能消费更多键）。

---

## 2. 在方案里使用插件类型

假设你已经有了上面的 `myplugin`，现在在 `solution.yaml` 里用它的 `robot_arm` verify 步。

**两件事必须做：**

### 2.1 声明依赖（最小 lockfile）

在 `solution.yaml` **顶层**加 `requires_plugins:`，把方案依赖的插件钉死：

```yaml
requires_plugins:
  - {id: myplugin, version: 1.0.0}
```

### 2.2 用命名空间 `type=` + 标 `verify=true`

verify 步在 `guide.md` 里这样写（命名空间 `<plugin-id>/<type>`，并显式标 `verify=true`）：

```markdown
{#check-arm type=myplugin/robot_arm verify=true}
连接机械臂，观察实时关节状态面板。
```

- **命名空间**：必须写成 `myplugin/robot_arm`，一眼看出来源，不和内置/其他插件撞名。
- **`verify=true` 必须显式标**：`validate` 是离线的、不知道插件类型的 `category`，所以插件做的 verify 步必须自己标 `verify=true`，才会被算作「该 preset 的 verify 步」。

---

## 3. validate 行为

`solutionctl validate` 对插件类型的处理：

| 情况 | 行为 |
|---|---|
| 命名空间插件类型（含 `/`，如 `myplugin/robot_arm`） | **WARN 不 ERROR**。能离线自检通过，但会提示来源 + 是否漏了 `requires_plugins`。 |
| 真未知类型（**没有** `/`，如 `robot_armm`） | **ERROR**。没有 `/` 的未知类型被当成拼写错误，不是插件。 |

所以：插件类型一定要带 `/`，否则会被当错别字拦下。

---

## 4. catalog 限制（重要）

> **带插件类型的方案不进公开 catalog。**

在该类型被「收编」成官方内置类型之前，带插件 `type=` 的方案**只能在装了对应插件的本地 / 私有环境部署**，**不收进公开仓库**。

「原型（插件） → 毕业（官方内置类型）」的昇格管线**仍在设计中**。如果你的插件类型足够通用、值得变成官方类型，走下面的 issue 路径告诉维护者。

---

## 5. 不写插件，向维护者提需求

如果你不想自己写插件，或者你希望这个类型直接成为**官方内置类型**（这样方案能进公开 catalog），请提一个能力需求 issue：

👉 **[New capability request](https://github.com/suharvest/sensecraft-solutions/issues/new?template=new-capability-request.md)**

模板会引导你说清楚：你部署的是什么、用户需要怎么交互、为什么现有 fallback（`http_debug` / `web_dashboard` / `actions`）不够。说得越具体，维护者越快能判断该做成内置类型还是给你插件 SDK。

---

## 相关文档

- [`skills/author-solution/SKILL.md`](../skills/author-solution/SKILL.md) — 写方案的完整流程 + 能力拓展决策树
- [`spec/plugin.schema.json`](../spec/plugin.schema.json) — `plugin.json` 字段权威定义
- [`spec/CONTRACT.md`](../spec/CONTRACT.md) — 内置 deployer 能力表（「Deployer capabilities」）
- [`docs/AE-提交指南.md`](AE-提交指南.md) — 非开发者 / AE 的手把手指南
