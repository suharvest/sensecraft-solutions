---
name: solution-cli
description: 教 AI agent 用 solutionctl CLI 调用引擎能力——发现方案、部署、校验、设备管理。当 agent 要在命令行 / CI / 无 GUI 环境部署或操作 SenseCraft 方案时加载。
allowed-tools: Read, Bash
---

# solution-cli — 用 solutionctl 在命令行驱动引擎

`solutionctl` 是 `packages/solutionctl/` 里的**瘦客户端**：它自己不含任何引擎代码，只负责定位
引擎二进制（`provisioning-station`）并通过子进程调用它。AI agent 加载本 skill 后，无需知道二进制
路径，就能在终端发现方案、部署、离线校验、查已部署 app。

## 何时用

- **headless / CI / 脚本化部署**：GitHub Actions、批量给多台设备部署、跑完即退。
- **没有桌面 App GUI** 的环境（纯命令行机器、远程 SSH）。
- 想**离线校验**一个方案目录是否符合 spec 契约（这一项不需要引擎，见下）。

不适用：内容编辑（改文案 → 用桌面 App 的编辑模式）、引擎/插件开发（在闭源引擎仓库）。

## 前提

- 已安装 **SenseCraft Solution App**，或本机有 `provisioning-station` 引擎二进制。
  `solutionctl` 按三级顺序自动定位，agent **不用关心路径**：
  1. 环境变量 `$SENSECRAFT_ENGINE_BIN`
  2. `~/.sensecraft/engine.json` 握手文件（App 首次启动写入）
  3. 平台原生查找（macOS `mdfind` / Windows 注册表 / Linux `dpkg`）
- 定位失败时 `solutionctl` 会给出清晰提示（装 App，或 `export SENSECRAFT_ENGINE_BIN=<引擎绝对路径>`）。
- **例外**：`solutionctl validate` 是**纯离线**的，不需要引擎二进制。

## 命令速查

```bash
# 看引擎能力 / 契约元数据（版本、支持的 deployer 类型等）
solutionctl meta

# 发现方案：先列再选 —— 别凭空猜 preset 名！
solutionctl solution list
solutionctl solution show <solution_id> [--lang en|zh]
#   → show 输出 JSON，含每个 preset 的 id / 步骤 / 关联 device YAML

# 部署（一次性，跑完即退）
solutionctl deploy <solution_id> \
    --preset <preset_id> \
    --device <device_id> \
    --connection '{"<device_id>":{"host":"...","username":"...","password":"<REDACTED>","port":22,"target":"...","target_type":"remote"}}' \
    --json
#   --connection 是嵌套 dict：{ device_id: {host, username, password, port, target, target_type, ...} }
#   device_id 必须和 `solution show` 里的一致；--device 省略 = 部署该 preset 的全部步骤（CI 场景）

# 离线校验一个方案目录是否合规（不需引擎）
solutionctl validate <solution_path> --spec-dir spec --check-urls

# 列出已部署的 app
solutionctl manage list-apps
```

### 凭据红线（必须遵守）

- **绝不编造凭据**。SSH 主机 / 用户名 / 密码一律向用户索取。
- 日志、示例、回显里**把密码 redact 成 `<REDACTED>`**，永远不要明文打印。

## `--json` 输出怎么读

`deploy --json` 输出 **NDJSON 事件流**：每行一个 JSON 对象，**逐行解析**（不要等全部读完再 parse）。
流的结尾会打印一个结构化的**结果 dict**（`status` + 每个设备的 `steps`）。进程**退出码**：
`0 = 成功`，`非零 = 失败`。判断真成功：`status: completed/success` 且远端 `docker ps` 显示容器
`(healthy)`。

## 能力边界（诚实写清）

CLI **一把梭覆盖**：方案发现（`solution list/show`）、部署（`deploy`）、离线校验（`validate`）、
引擎元数据（`meta`）。

**设备管理那一大块**——启停 / 更新 / OTA / 恢复出厂 / docker 操作（详见 `AGENTS.md` **Part E**）——
目前 CLI **只有 `manage list-apps`**，其余全部走 **`serve --headless` + REST 端点**。
`solutionctl manage` 内部就是起这个 headless server，所以任何 REST 端点都够得着；
完整端点表见 `AGENTS.md` **Part D / Part E**。

> 简言之：**部署 / 校验 / 发现 / meta 用 CLI；细粒度设备运维走 REST。**
