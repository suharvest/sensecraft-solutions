# respeaker_flex_soarm — Implementation Plan

> 一键部署版「SO-ARM 语音机械臂」方案。基于 Seeed Wiki [respeaker_flex_soarm](https://wiki.seeedstudio.com/respeaker_flex_soarm/) 改造，目标用户：AE / 方案商（无开发能力）。
>
> 设备到货前先把平台基础能力（P-1 SSH 安全 + `robot_inspect` HTTP poller + `yaml_file` 字段）做掉；设备到货后并行做镜像和方案接入。

---

## 1. 方案定位

- **solution_type**: `technical`（单一能力：语音控制机械臂；可被其他 solution 集成）
- **硬件**: reComputer Super J4012 (Jetson Orin NX) + reSpeaker Flex XVF3800 + SO-ARM101
- **核心链路**: 唤醒 → Groq Whisper → Groq LLaMA → 动作映射 → SO-ARM 电机 → Groq Orpheus TTS
- **明确放弃**：标定（另平台处理）、Solution Console、Web 姿态/Prompt 表单编辑器、`config_volume` 通用能力

---

## 2. 平台侧基础能力

### 2.0 P-1：远程 SSH config 写入的 shell 注入修复（前置必做，~1 天）

> **必须先于 `yaml_file` 完成**，因为 yaml_file 会把整段 YAML 文本作为字符串传到底层。当前 `docker_device_manager.py:1535-1546` 直接用字符串拼 `env_str` / `cd` / `docker compose` 命令，value 里任何 `$(...)` / 反引号 / `;` / 换行都会被 shell 执行。即使不上 yaml_file，现有 GROQ_API_KEY 这类字段也有理论注入面。

#### 改动范围
- `provisioning_station/services/docker_device_manager.py:1443-1575` 改用 paramiko `exec_command(stdin=...)` + base64 编码传递 value，或改 `shlex.quote()` 所有 value
- 所有 ssh 拼接命令的位置（grep `f".*ssh"` / `f".*compose"` 全部审一遍）
- 加 unit test：value 含 `$(rm -rf /)` / 反引号 / `;` / 换行时，落到设备上的 env / 文件内容必须**逐字一致**，不能被 shell 解释

#### 工作量：1 天（含审计 + 改动 + 测试）

---

### 2.1 `robot_inspect` verify 类型（B 方案 — HTTP poller，~1.5 天）

**架构关键点**：机械臂 serial port 由**主容器始终独占**。verify 不去抢 port，而是通过 HTTP 问主容器要数据。这样部署前 / 部署后**都能用**，且无 port 冲突。

```
┌─ 设备 ─────────────────────────────────┐
│  ┌─ 方案主容器 ───────────────────┐    │
│  │ 主循环持有 Robot 实例和 port    │    │
│  │ 每次读完往 in-memory cache 写   │    │
│  │                                │    │
│  │ FastAPI mini server（线程）：   │    │
│  │   GET /observation  → 读 cache │◄───┼── SenseCraft App
│  │   GET /observation/schema       │    │   verify 面板 5Hz fetch
│  └────────────────────────────────┘    │
└────────────────────────────────────────┘
```

**面板布局**（沿用现有 preview verify 风格）：
- 上半：schema 驱动 gauge / 数值条；状态栏显示连接 / 采样率 / 消息计数
- 下半：`<> 详细数据` 折叠手风琴，展开后显示完整 observation raw JSON（只读，自动随 poll 刷新）

**协议约定**（任何 robot 类方案 opt-in 接入）：
- `GET /observation` → 返回 flat dict `{field_name: number}`
- `GET /observation/schema` → 返回 `{field_name: {type: float|bool|array, label?: str, range?: [min, max]}}`

#### 后端
- 新增 `provisioning_station/routers/robot_inspect.py`
  - `GET /api/verify/robot/{session_id}/observation` — 反代到目标设备 endpoint
  - `GET /api/verify/robot/{session_id}/schema` — 同上
  - 不维护 Robot 实例、无 session 生命周期 —— 纯无状态 HTTP 反代
- 新增 device type `robot_inspect`，**3 处同步注册**：
  - [ ] `provisioning_station/models/device.py:40` — DeviceType enum
  - [ ] `provisioning_station/deployers/__init__.py:25` — deployer registry（即使不做实际 deploy，verify 类型也要登记）
  - [ ] `tests/unit/test_solution_spec_compliance.py:149` — verify 类型白名单

#### 前端
- 新增 `frontend/src/pages/deploy.js` 渲染分支：`type=robot_inspect` 时挂载 `RobotInspectPanel`
- 新增 `frontend/src/modules/robot-inspect-panel.js`：
  - HTTP poller 按 `poll_hz` 拉数据
  - schema 驱动渲染：float → 数值条；bool → 灯；array → 跳过
  - `<>详细数据` 手风琴复用 preview 页 CSS（`.preview-data-detail` 等）
  - i18n key 加在 `frontend/src/modules/i18n.js`

#### Solution 侧声明
```yaml
# devices/verify_arm.yaml
type: robot_inspect
endpoint: "http://{{deploy.host}}:{{deploy.observation_port}}/observation"
schema_endpoint: "http://{{deploy.host}}:{{deploy.observation_port}}/observation/schema"
poll_hz: 5
fallback_message: "无法连接到机械臂状态服务，请确认 voice_arm 容器已启动。"
```

> **端口约束（SSRF 防护）**：`observation_port` 必须在 `[8765, 8766, 8767, 8768, 8769]` 内 —— 后端 `_validate_endpoint` 白名单。新方案接入时 docker-compose 要在这 5 个端口内选一个暴露 observation HTTP server，否则反代直接返回 403。如需扩展，改 `provisioning_station/routers/robot_inspect.py` 里的 `ALLOWED_UPSTREAM_PORTS`。

#### 工作量
- 后端反代 router + DeviceType/registry/test 注册：0.5 天
- 前端 panel + i18n + 手风琴：0.7 天
- spec compliance 测试 + 错误降级 UX：0.3 天

---

### 2.2 `yaml_file` config 字段类型（~2 天）

**形态**：在现有「配置应用」模态（`frontend/src/pages/devices.js:1393-1406`）的字段渲染分支里增加一种新类型。`yaml_file` 字段渲染为折叠行（摘要 + ✏ 按钮），点 ✏ 就地展开嵌入式 **CodeMirror 6** 编辑器。

#### 后端（含事务回滚）
修改 `provisioning_station/services/docker_device_manager.py`：
- `getRemoteConfig` / `getLocalConfig`：遇到 `field.type=yaml_file` 时，**SSH 读** `remote_path` 文件内容塞进 `current_value`
- `updateConfig` 的事务流程：
  1. 服务端 `yaml.safe_load(new_content)` —— 失败直接 400 返回，不动设备
  2. SSH `cp file file.bak.{timestamp}` 备份（local 模式同理）
  3. SSH 写新内容（**base64 走 stdin，禁止字符串拼接**，依赖 P-1 已完成）
  4. `docker compose up -d <service>`
  5. 失败 → SSH `mv file.bak.{timestamp} file` + `docker compose up -d` 恢复，banner 报错给用户
  6. 成功 → 5 个最新的 .bak 之外的备份删掉
- 防护：
  - 拒绝写入 > 100KB
  - 拒绝路径含 `..` / 不在白名单根目录（`/opt/seeed/`）下
  - 并发写锁（同 solution_id 不允许并发 update）

#### 前端
修改 `frontend/src/pages/devices.js`：
- 1393-1406 渲染逻辑改 switch：`text/number/password → input`；`yaml_file → renderYamlFileField()`
- 新增 `renderYamlFileField()`：
  - 折叠态：`▸ {label}    {summary_text}   [✏]`，summary 用前端 yaml.parse 算出 keys 数量
  - 展开态：CodeMirror 6 实例，行号 + YAML 高亮 + 本地 yaml.parse 校验
  - 底部状态条：`✓ YAML 语法正确` / `✗ Line N: ...`
- 引入 CodeMirror 6（按需 import，~50KB gzip）
- 引入 `js-yaml`（前端校验用，~20KB gzip）
- 关闭模态前如有未保存改动 → `confirm()` 弹窗
- 保存按钮处理：所有字段（标量 + 文件）一次 POST；按字段类型分发处理；失败 banner 红色 + 编辑器内容保留

#### 工作量
- 后端文件读写 + 事务回滚 + 防护：0.8 天
- 前端 yaml_file 渲染 + CodeMirror + 校验：0.9 天
- 集成测试（重启失败回滚验证、注入字符防护验证）：0.3 天

---

### 平台侧小计：**~4.5 天**（P-1 1d + robot_inspect 1.5d + yaml_file 2d）

---

## 3. 方案侧 voice_arm

### Phase 0 — 设备到货验证（1-2 天，设备到货后开始）

- [ ] 加 reComputer J4012 到 fleet（标签 `jetson`, `orin-nx`, `voice_arm`）
- [ ] 在裸机上手动跑通 wiki 流程，确认能用
- [ ] **关键风险点 1**：reSpeaker XVF3800 USB 在 Docker 容器内可用
  - **已验证参考**：`solutions/voice_robot_lekiwi/assets/docker/docker-compose.yml`（`/dev/snd` + `device_cgroup_rules: 'c 166:* rmw'` + `group_add: "29"`）+ `Dockerfile`（`libportaudio2 alsa-utils portaudio19-dev`）—— 已在 Jetson 上验证过，**直接复用这套配置**
- [ ] 测 openwakeword 在 Orin NX 上的延迟，确认实时性

### Phase 1 — 镜像 + 代码改造（2 天）

- [ ] Fork voice_arm 代码到 `solutions/respeaker_flex_soarm/assets/voice_arm/`（不维护独立 repo）
- [ ] 魔改：
  - [ ] `robot_arm.py` 启动时 `yaml.safe_load("/opt/seeed/voice_arm/config/actions.yaml")`，不再硬编码 `ACTION_MAP`
  - [ ] `llm.py` 启动时读 `prompt.yaml`
  - [ ] `pipeline.py` 加 robot_inspect endpoint（**~30 行**）：
    ```python
    # 缓存最新 observation（主循环写）
    _latest_obs, _lock = {}, threading.Lock()
    # FastAPI 后台线程：GET /observation 读 cache，GET /schema 返 observation_features
    # uvicorn.run(host="0.0.0.0", port=8765, log_level="error")
    ```
  - [ ] 新增 `entrypoint.sh`：
    - 自动探测 `/dev/ttyACM*`，逐个 `lerobot.find_port` 验证识别 SO-ARM
    - 自动枚举 PyAudio 设备，filter `name contains "ReSpeaker|XVF"`
    - 写探测结果到 `runtime.env`
- [ ] 默认 `actions.yaml` + `prompt.yaml` 放在 `assets/default_config/`
- [ ] 构建 `seeed/lerobot-voice-arm:jetson-r36.x`
  - base: `nvcr.io/nvidia/l4t-jetpack:r36.x.x`
  - 装 lerobot[feetech] / openwakeword / groq / pyaudio / **fastapi + uvicorn**（~5MB）
  - apt 装 `libportaudio2 alsa-utils portaudio19-dev`（抄 lekiwi）
  - 预下载 "hey jarvis" wake word 模型
  - **不装 huggingface_hub**（按规范，模型走 `solutions/_shared/scripts/hf_download.sh`）
- [ ] `docker-compose.yml`（抄 lekiwi 模板）：
  - `devices: ['/dev/ttyACM0', '/dev/snd:/dev/snd']`
  - `device_cgroup_rules: ['c 166:* rmw']`
  - `group_add: ['29']`
  - `ports: ['8765:8765']`（robot_inspect endpoint）
  - bind mount `/opt/seeed/voice_arm/config` → 容器 `/opt/seeed/voice_arm/config`
  - 首次部署 entrypoint 检查 config 目录，没有就从镜像内默认值拷贝（**不覆盖已有**）

### Phase 2 — 方案接入（1 天）

- [ ] `solutions/respeaker_flex_soarm/solution.yaml`
  - `solution_type: technical`
  - `output_interfaces`：声明 WS / HTTP 接口（让其他 solution 可集成）
  - `input_requirements`：reSpeaker + SO-ARM101 + Groq API Key
  - `config_fields`：
    - `GROQ_API_KEY` (password, required)
    - `WAKEWORD_THRESHOLD` (number, default "0.5")
    - `WAKEWORD_COOLDOWN` (number, default "2")
    - `TTS_VOICE` (text, default "autumn")
    - `actions` (**yaml_file**, remote_path `/opt/seeed/voice_arm/config/actions.yaml`)
    - `prompt_rules` (**yaml_file**, remote_path `/opt/seeed/voice_arm/config/prompt.yaml`)
- [ ] `devices/jetson.yaml`（`type: docker_remote`）
- [ ] `devices/verify_voice.yaml`（`type: voice_chat`）
- [ ] `devices/verify_arm.yaml`（`type: robot_inspect`，HTTP endpoint 指向 `:8765`）
- [ ] `guide.md` / `guide_zh.md`：
  - Step 1: Deploy（`docker_remote`）
  - Step 2: Verify Voice（`voice_chat`）
  - Step 3: Verify Arm State（`robot_inspect` 看关节角度 + 详细数据手风琴）
  - `### Deployment Complete` 段落附「进阶：自定义动作」说明：进设备管理 → 配置 → 改 actions.yaml
- [ ] `description.md` / `_zh.md`（technical 风格 —— 能力 → 集成场景 → 接口）
  - **必须显式说明 Groq 免费 tier 限额**：Whisper 20 RPM / 2000 RPD，Orpheus 仅 **10 RPM / 100 RPD**，仅供个人演示；规模化部署需自费 paid tier
- [ ] `gallery/` cover 图（demo 视频截帧，臂在动 + 唤醒提示）

### Phase 3 — 验收与交付（0.5 天）

- [ ] 第二轮 API 部署跑通（`/deploy-solution respeaker_flex_soarm`）
- [ ] `pytest tests/unit/test_solution_spec_compliance.py tests/unit/test_solution_format.py tests/unit/test_solution_config_validation.py -k respeaker_flex_soarm` 全绿
- [ ] 录 Demo 视频（语音 → 臂动作 → TTS 回复完整链路）
- [ ] `/solution-copywriting respeaker_flex_soarm` 过一遍
- [ ] 在 App 里完整走一遍部署流程，截屏 Step 3 robot_inspect 面板有真实数据 + 手风琴展开
- [ ] 验证 yaml_file 配置流程：模态打开 → 改 actions.yaml 加新动作 → 保存 → 容器重启 → 语音触发新动作成功

### 方案侧小计：**~3.5 天**（不含 P0 设备验证）

---

## 4. 时间线（关键路径）

```
P-1 SSH 注入修复 (1d) ───┐
                         ├─→ yaml_file (2d) ─────┐
                         │                       ├─→ Phase 2 (1d) ─→ Phase 3 (0.5d)
平台 robot_inspect (1.5d) ──────────────────────┤
                                                 │
P0 设备验证 (1-2d) ─→ P1 镜像 (2d) ──────────────┘
```

P-1 必须先做（yaml_file 依赖）。其他可并行。**总日历时间 ~ 5-6 天**。

---

## 5. 风险与开放问题（codex 审核后更新）

| 风险 | 状态 | 缓解 |
|---|---|---|
| 远程 SSH config 写入 shell 注入 | 🔴 → 已规划 P-1 | 切 base64 stdin / shlex.quote，加 unit test |
| yaml_file 无事务回滚 | 🔴 → 已规划 | .bak 备份 + 服务端 yaml.safe_load 校验 + 失败自动 mv 恢复 |
| 平台 registry / spec 测试缺口 | 🔴 → 已规划 | 3 处注册清单写入 PLAN，作为 acceptance check |
| reSpeaker XVF3800 USB 音频 | ✅ 绿灯 | lekiwi 已验证可工作，直接复用 docker 配置 |
| Groq 免费 tier 限额（Orpheus 仅 100 RPD） | ⚪ obsolete | 已彻底切换为完全本地推理（seeed-local-voice + edge-llm-chat-service），Groq 依赖整体砍掉，不再有调用限额 |
| 首次启动需 5-10 分钟（拉镜像 + Qwen3 引擎预热 + 模型下载） | 🟡 | guide.md / description.md 在前置条件里显式说明；voice-arm `depends_on: service_healthy` 等到两个上游就绪再启动 |
| Orin NX 16GB 显存同时跑 seeed-voice + edge-llm + voice-arm | 🟡 | 预算：voice ~3GB + edge-llm 4B AWQ ~8GB + voice-arm <1GB，留 4GB 给系统；Jetson AGX 16GB 实测 OK，Orin NX 16GB 首次部署需现场验证 |
| openwakeword 在 Orin NX 延迟 | 🟡 | P0 实测，必要时调阈值 |
| robot_inspect endpoint 在设备未启动时返回什么 | 🟡 | 前端 `fallback_message` 显示「容器未启动」并停止轮询 |
| yaml_file 用户改坏 YAML 致容器起不来 | 🟡 | 服务端校验拦明显语法错；语义错通过事务回滚兜底 |
| 多 session / 多浏览器同时打开 verify | ✅ 绿灯 | B 方案无 session 概念，纯 HTTP 反代，N 个客户端无冲突 |

---

## 6. 后续可复用

- **`robot_inspect` HTTP poller**：任何「想让用户看实时状态」的方案（机器人、PLC、传感器…）只需暴露 `GET /observation` + `GET /observation/schema` 两个端点即可接入，**不限于 LeRobot 生态**
- **`yaml_file` 字段**：任何需要让用户改结构化配置的方案（heatmap 的 telegraf、grafana datasource、未来 voice_robot_lekiwi 的姿态库等）
- **P-1 SSH 安全修复**：所有用 `docker_device_manager` 的方案受益

---

## 7. 平台侧验收清单

robot_inspect verify：
- [ ] DeviceType enum 已加 `robot_inspect`
- [ ] deployer registry 已注册（即使是 no-op deployer）
- [ ] verify spec 白名单已加
- [ ] frontend renderer 已实现，i18n key 齐全
- [ ] endpoint 不通时前端有降级提示，不卡死
- [ ] 折叠手风琴样式与现有 preview 一致

yaml_file 字段：
- [ ] 服务端 yaml.safe_load 校验生效
- [ ] .bak 备份 + 失败回滚集成测试通过
- [ ] 注入字符（`$(...)` / `;` / 反引号 / 换行）写入后逐字一致
- [ ] 路径 traversal 防护测试通过
- [ ] 100KB 上限生效
- [ ] 并发写锁生效

P-1 SSH 修复：
- [ ] 现有所有 ssh 拼接位置审计完毕
- [ ] 注入字符 unit test 全绿
- [ ] 不破坏现有标量字段（GROQ_API_KEY 等）的功能
