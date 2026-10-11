---
name: solution-cli
description: 方案内容作者用的 solutionctl CLI——离线校验方案（validate）、查看每个 preset 的步骤与产物（steps）、打包给 App 预览（export）。给 Agent 部署方案不要用它，改用 sensecraft skill（sensecraft-engine 命令行引擎，不启动 Python 进程）。
allowed-tools: Read, Bash
---

# solution-cli — 方案作者用的 solutionctl

`solutionctl` 是 `packages/solutionctl/` 里的命令行工具，分两类命令：

| 类别 | 命令 | 需要什么 |
|---|---|---|
| **作者离线工具**（本 skill 的主要用途） | `validate`、`steps`、`export` | 只要本仓库 clone，不需要引擎、不需要 App |
| 需要 Python 引擎的命令 | `meta`、`solution list/show`、`deploy-info`、`deploy`、`manage`、`stage` | 定位并启动 `provisioning-station`（桌面 App 的 Python 后端），见文末附录 |

## 部署方案：用 sensecraft skill，不用 solutionctl

Agent 给用户部署方案、处理部署失败、处理验证步骤（`verify_required`）时，加载
`skills/sensecraft/SKILL.md`。它只用 `sensecraft-engine` 命令行引擎：

```bash
curl -fsSL https://sensecraft-statics.seeed.cc/engine/install.sh | sh -s -- --with-content
sensecraft-engine content pull
sensecraft-engine solution list --json
sensecraft-engine deploy-info <solution_id> --preset <preset>
sensecraft-engine deploy --params body.json --yes --detach
sensecraft-engine status <deployment_id> --json
sensecraft-engine logs <deployment_id> --since <N>
```

`solutionctl deploy` / `manage` / `stage` 会启动 Python 后端，不在 Agent 部署路径上。

## 作者离线工具（不需要引擎）

从仓库 clone 内运行：`uv run --package sensecraft-solutionctl solutionctl <...>`
（已全局安装时直接 `solutionctl`）。

```bash
# 校验一个方案目录是否符合 spec 契约（CI 对每个方案跑同一条命令）
solutionctl validate solutions/<id> --spec-dir spec --check-urls

# 每个 preset 的步骤：guide 标题与它指向的 devices/*.yaml 产物合在一起显示
#（固件来源与校验和、compose 文件、烧录参数等），发布前核对用
solutionctl steps solutions/<id> [--lang en|zh]

# 打包成 App 可导入的 zip（本地预览，见 preview-solution-content skill）
solutionctl export <id> [--output-dir dist]
```

`validate` 失败时按输出逐条修改再跑，直到通过。

## 附录：需要 Python 引擎的命令（作者调试用，会启动 Python 后端）

以下命令通过子进程调用 `provisioning-station`（桌面 App 的 Python 后端）。定位顺序：

1. 环境变量 `$SENSECRAFT_ENGINE_BIN`
2. `~/.sensecraft/engine.json` 握手文件（App 首次启动写入）
3. 平台原生查找（macOS `mdfind` / Windows 注册表 / Linux `dpkg`）

定位失败时 `solutionctl` 会提示装 App，或 `export SENSECRAFT_ENGINE_BIN=<引擎绝对路径>`。
作者用它们在本机验证改过的方案能否部署；给用户部署请用 sensecraft skill。

### 命令速查

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

#### 部署三步法（deploy-info → 填 → deploy）

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
# 列出已部署的 app（起 headless 服务）
solutionctl manage list-apps
```

### 去没网的现场部署：`stage`

先在有网的地方把方案要用的东西下到本机，到现场再部署。单位是**步骤 × 目标设备**：
可以只备某一步，也可以给同一步备多个型号。

```bash
# 1. 看这个套餐每一步需要什么、能不能完全离线、本机已经有哪些
solutionctl stage plan <solution_id> --preset <preset>

# 2. 下到本机（--target 只备指定步骤；--arch 用于推不出架构的目标）
solutionctl stage prepare <solution_id> --preset <preset> \
    --target <step>=<target> --arch <step>=aarch64 --params '{"board":"rk3588"}'

# 3. 看本机备了什么、占多少（--check 顺带报哪些有更新）
solutionctl stage list --check

# 4. 带到另一台电脑
solutionctl stage export kit.tar
solutionctl stage import kit.tar          # 在现场那台执行

# 5. 腾空间
solutionctl stage delete --entry <solution>/<preset>/<step>[/<target>[/<arch>]]
```

现场部署时在连接里传 `force_offline`，引擎会在**连接设备之前**核对离线包，缺件就直接
停下并说明缺什么：

```bash
solutionctl deploy <solution_id> --preset <preset> --device <step> \
    --connection '{"<step>":{"host":"<ip>","username":"<user>","password":"<REDACTED>",
                   "target":"<target>","target_type":"remote","force_offline":true}}' --yes
```

**退出码**：`0` = 清单里的东西都在本机；`1` = 有缺的；`2` = 清单推不出来（比如目标没写
设备类型、架构需要用 `--arch` 指定）。加 `--require-full` 后，方案未声明"服务启动后不再
联网下载"时也会失败（`3`）——目前还没有方案声明，所以默认不开。

**能离线到什么程度取决于方案**：镜像启动后自己去拉模型这类内容，清单推导不出来，
`plan` 会标成 `partial` 并写明现场仍需联网的是什么。

#### 凭据红线（必须遵守）

- **绝不编造凭据**。SSH 主机 / 用户名 / 密码一律向用户索取。
- 日志、示例、回显里**把密码 redact 成 `<REDACTED>`**，永远不要明文打印。

### deploy 输出怎么读

`solutionctl deploy` **内部已经加了 `--json`**——你**不要**再自己传 `--json`（会 exit 2）。
默认输出是**收敛过的**人类可读流：只渲染生命周期骨架
（`device_started` / `pre_check_*` / `device_completed` / `deployment_completed`）+ 错误日志，
docker 拉层进度和 httpx 轮询噪声被过滤掉。需要全量看用 `--verbose`。
流的结尾会打印一个结构化的**结果 dict**（`status` + 每个设备的 `steps`）。进程**退出码**：
`0 = 成功`，`非零 = 失败`。判断真成功：`status: completed/success` 且 `docker ps` 显示容器
`(healthy)`。容器明明 `(healthy)` 但报失败 → 多半是 healthcheck 配置 bug（如探了个返回 401 的鉴权端点），
**不是**部署失败。

### 能力边界（诚实写清）

CLI **一把梭覆盖**：方案发现（`solution list`）、部署信息（`deploy-info`）、部署（`deploy`）、
离线校验（`validate`）、引擎元数据（`meta`）、离线预备（`stage`）。

**设备管理那一大块**——启停 / 更新 / OTA / 恢复出厂 / docker 操作（详见 `AGENTS.md` **Part E**）——
目前 CLI **只有 `manage list-apps`**，其余全部走 **`serve --headless` + REST 端点**。
`solutionctl manage` 内部就是起这个 headless server，所以任何 REST 端点都够得着；
完整端点表见 `AGENTS.md` **Part D / Part E**。

> 简言之：**部署 / 校验 / 发现 / meta 用 CLI；细粒度设备运维走 REST。**
