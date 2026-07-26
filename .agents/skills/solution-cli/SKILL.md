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

> **从仓库 clone 内跑命令即可**，`solutionctl` 会自动把 `PS_SOLUTIONS_DIR` 指向这个
> clone 的 `solutions/`（cwd 在 repo 根下任意位置都行），无需 `--solutions-dir`；同时
> best-effort 把 `PS_DEVICES_DIR` 指向已装桌面 App 的 `devices/` 目录（含 `device_class` 的方案需要）。
> 命令行不用加 `uv run` 前缀的话直接 `solutionctl`；在 clone 里用
> `uv run --package sensecraft-solutionctl solutionctl <...>`。

```bash
# 看引擎能力 / 契约元数据（版本、支持的 deployer 类型等）
solutionctl meta

# 发现方案：列出所有方案 ID
solutionctl solution list
```

### 部署三步法（deploy-info → 填 → deploy）

**别凭空猜 preset 名，也别啃 `solution show` 的原始 JSON。** 走 `deploy-info`：

```bash
# 1. 看这个方案怎么部署：有哪些 preset、每步要填什么、local/remote 怎么选
solutionctl deploy-info <solution_id> [--preset <p>] [--lang en|zh]
#   → JSON 输出：
#     presets            : 每个 preset 的 id + name（按用户意图选一个，再 --preset 收窄）
#     steps              : 每步的 device_id / type / 必填参数；
#                          has_targets=true 的步骤（如 docker_deploy）提供 local vs remote 两种 target
#                            local  = 部署到本机 Docker（免 SSH）
#                            remote = SSH 部署到边缘设备
#     request_template   : 每个 device 预填好的连接骨架，<REQUIRED: ...> 是用户必须补的空

# 2. 从 request_template 拷出来，填好空，组成 --connection（嵌套 dict）
#    本机 Docker（免 SSH）：选 local target，零凭据
#      {"<device_id>":{"target":"<...>_local","target_type":"local"}}
#    远程 SSH：选 remote target，补 host/username/password/port
#      {"<device_id>":{"target":"<...>_remote","target_type":"remote","host":"...","username":"...","password":"<REDACTED>","port":22}}

# 3. 部署（一次性，跑完即退）—— 注意：不要自己加 --json！
solutionctl deploy <solution_id> \
    --preset <preset_id> \
    --device <device_id> \
    --connection '<填好的 JSON>' \
    --yes
#   device_id 必须和 deploy-info 里的一致；--device 省略 = 部署该 preset 的全部步骤（CI 场景）
#   --verbose 看完整事件流（docker 拉层 + 轮询）；默认只渲染生命周期骨架 + 错误日志
#   --replace-existing 同名容器已存在时自动停掉重建（默认会报错让用户确认）
```

**可复制的本机 Docker 实例**（已实跑验证）：

```bash
# 从 sensecraft-solutions clone 内
uv run --package sensecraft-solutionctl solutionctl deploy-info smart_warehouse --preset sensecraft_cloud

uv run --package sensecraft-solutionctl solutionctl deploy smart_warehouse \
  --preset sensecraft_cloud --device warehouse \
  --connection '{"warehouse":{"target":"warehouse_local","target_type":"local","auto_replace_containers":true}}' \
  --yes

docker ps --filter name=mcp_warehouse        # → Up X seconds (healthy)
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:2125/healthz   # → 200
```

```bash
# 离线校验一个方案目录是否合规（不需引擎）
solutionctl validate <solution_path> --spec-dir spec --check-urls

# 列出已部署的 app
solutionctl manage list-apps
```

### 凭据红线（必须遵守）

- **绝不编造凭据**。SSH 主机 / 用户名 / 密码一律向用户索取。
- 日志、示例、回显里**把密码 redact 成 `<REDACTED>`**，永远不要明文打印。

## deploy 输出怎么读

`solutionctl deploy` **内部已经加了 `--json`**——你**不要**再自己传 `--json`（会 exit 2）。
默认输出是**收敛过的**人类可读流：只渲染生命周期骨架
（`device_started` / `pre_check_*` / `device_completed` / `deployment_completed`）+ 错误日志，
docker 拉层进度和 httpx 轮询噪声被过滤掉。需要全量看用 `--verbose`。
流的结尾会打印一个结构化的**结果 dict**（`status` + 每个设备的 `steps`）。进程**退出码**：
`0 = 成功`，`非零 = 失败`。判断真成功：`status: completed/success` 且 `docker ps` 显示容器
`(healthy)`。容器明明 `(healthy)` 但报失败 → 多半是 healthcheck 配置 bug（如探了个返回 401 的鉴权端点），
**不是**部署失败。

## 能力边界（诚实写清）

CLI **一把梭覆盖**：方案发现（`solution list`）、部署信息（`deploy-info`）、部署（`deploy`）、
离线校验（`validate`）、引擎元数据（`meta`）。

**设备管理那一大块**——启停 / 更新 / OTA / 恢复出厂 / docker 操作（详见 `AGENTS.md` **Part E**）——
目前 CLI **只有 `manage list-apps`**，其余全部走 **`serve --headless` + REST 端点**。
`solutionctl manage` 内部就是起这个 headless server，所以任何 REST 端点都够得着；
完整端点表见 `AGENTS.md` **Part D / Part E**。

> 简言之：**部署 / 校验 / 发现 / meta 用 CLI；细粒度设备运维走 REST。**
