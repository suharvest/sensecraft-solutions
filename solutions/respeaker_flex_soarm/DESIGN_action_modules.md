# Action Modules — verify panel runtime interaction layer

> 设计文档。目标：在 robot_inspect verify panel 下加一层通用「动作模块」，让用户能在浏览器里录制机械臂动作并立即生效。审核稿，未实现。

---

## 1. 用户故事

**录制一个名为 `high_five` 的多帧动作**：

1. App 设备管理页 → 已部署的 voice-arm 卡片 → 点 **[运行/检查]** → 打开 verify panel
2. 上半显示实时关节角度（schema-driven gauge）
3. 下半「动作录制」模块：
    a. 点 [💪 关扭矩] → 远端容器切扭矩，臂变软可手动转动
    b. 输入动作名 `high_five`
    c. 摆臂第 1 帧 → 点 [👁 观测→添加] → 表格新增 1 行（6 关节角 + delay 0.4s）
    d. 摆第 2 帧 → 重复 → 表格累积
    e. 不满意某帧 → 🗑 删除
    f. 想调节奏 → 改单元格 delay
    g. 全部录完 → 点 [✅ 完成保存]
4. 容器接收完整序列 → 双写（in-memory ACTION_MAP + actions.yaml）→ 不重启
5. UI toast「已保存」 + 表格清空，可立即开始下一个录制
6. 旁边的 [🎤 测试动作] 按钮可不走语音直接 POST 触发执行
7. 用户说「Hey Jarvis, high five」→ 新动作生效

---

## 2. 架构总览

```
┌───────────── SenseCraft App (browser) ─────────────┐
│                                                    │
│  设备管理 / 卡片 [运行/检查] ────────┐              │
│                                     ▼              │
│  ┌─ verify panel (robot_inspect) ─────────────┐    │
│  │ 上半: 实时关节角 gauge                       │    │
│  │ 下半 action_modules:                         │    │
│  │   • device_command (扭矩开关)                │    │
│  │   • sequence_recorder (录制 wizard)          │    │
│  │   • <>详细数据 raw JSON                      │    │
│  └─────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
         │                    │                   │
         │ GET /observation   │ POST /torque/*    │ POST /actions
         │ (轮询)              │ (按钮)            │ (完成保存)
         ▼                    ▼                   ▼
┌─────────────────────── voice-arm 容器 ────────────────┐
│  pipeline.py + FastAPI                                │
│  • /observation         ← 已有                         │
│  • /torque/{on,off}     ← 新                           │
│  • /actions             ← 新                           │
│                                                       │
│  状态自管：                                            │
│  • _latest_obs (cache, 主循环写)                      │
│  • ACTION_MAP (内存动作库)                            │
│  • actions.yaml (持久化，启动时加载)                  │
│  • 锁: actions_lock 保证写盘与读取一致                │
└───────────────────────────────────────────────────────┘
```

**所有权分配**：
- **容器自管运行时状态**（ACTION_MAP、扭矩状态、actions.yaml 写盘）。状态属于容器内部，不暴露给平台部署期参数。
- **平台无状态反代**（observation / torque / actions 三个 endpoint 通过白名单反代到容器）
- **浏览器维护录制草稿**（未提交的序列只在浏览器内存里，关闭页面即丢；这就是"二阶段提交"的草稿态）

---

## 3. 容器侧 API（voice-arm）

### `GET /observation` （已有，不变）
返回当前关节角度 flat dict。

### `POST /torque/off` / `POST /torque/on` （新）
- 切换扭矩使能寄存器
- 返回 `{"ok": true, "torque": "off"|"on", "since_ts": <epoch_ms>}`
- `since_ts` 用于「最近 ON ≥ 500ms 防抖」（**容器侧记录**，前端不可信）

#### 关扭矩状态下 `/observation` 的行为（不依赖 P0 实测）

主循环**始终**用 `bus.sync_read("Present_Position")` 写 in-memory `_latest_obs` cache（带 monotonic timestamp `_latest_obs_ts`）。

**主循环异常处理（必须）**：
```python
while running:
    try:
        obs = bus.sync_read("Present_Position")
        with state_lock:
            _latest_obs = obs
            _latest_obs_ts = time.monotonic_ns()
    except (BusTimeout, ProtocolError, OSError) as e:
        log.warning(f"sync_read failed: {e}")
        # 不更新 cache_ts；不抛出；下一次循环继续重试
    time.sleep(0.2)  # 5Hz
```
**主循环绝对不能让单次 sync_read 异常打挂自己**。失败时保留 last good cache，让 fallback 链有数据可返回。

**`/observation` fallback 链**：
1. 尝试 `bus.sync_read("Present_Position")`（同样 try/except）
   - 成功：返回结果 + 顺便刷新 `_latest_obs` cache
2. 失败：
   - `now - _latest_obs_ts < OBS_CACHE_MAX_AGE_MS`（默认 2000，env `OBS_CACHE_MAX_AGE_MS` 可配）：返回 cache + header `X-Observation-Source: cache`
   - 超过上限：返回 503 `{"error": "stale_observation"}`

**配置项**：`OBS_CACHE_MAX_AGE_MS` 通过 docker-compose env 暴露，默认 2000。用户摆姿态时间长可调大（如 5000）；演示场景调小（如 500）让响应更及时。

**P0 实测目标**：验证 ① 扭矩 off 时 sync_read 是抛硬异常还是返回旧值还是超时；② cache 5Hz 主循环刷新延迟是否 ≤200ms。**实测结果不影响设计**——主循环 try/except + cache fallback 在所有情况下都成立。

### `POST /actions` （新）
**Request**：
```json
{
  "name": "high_five",
  "frames": [
    {"joints": {"shoulder_pan": 20, "shoulder_lift": 87, ...}, "delay": 0.4},
    {"joints": {"shoulder_pan": -20, ...}, "delay": 0.4},
    {"joints": {"shoulder_pan": 0, ...}, "delay": 0.4}
  ]
}
```

**逻辑**：
1. 校验 `name` 符合 `^[a-z][a-z0-9_]*$`（**容器内强制校验**，不依赖前端）
2. 校验 frames 非空、不超过 50 帧、每帧 joints 包含所有 6 个关节、delay 在 [0.05, 5.0]
3. **加锁 `actions_lock`**（**写盘成功才更新内存**）：
   - 读 `/opt/seeed/voice_arm/config/actions.yaml` → 反序列化为 dict
   - 在 dict 副本里 `sequences[name] = ...`
   - 写到 `actions.yaml.tmp`（`yaml.dump`）
   - `os.replace(tmp, actions.yaml)` 原子替换
   - **仅在 replace 成功后** `ACTION_MAP[name] = sequence`
   - 如果 replace 失败 → 内存维持原状 + raise 500
4. 返回 `{"ok": true, "name": "high_five", "frames_count": 3}`

**所有性质**：先文件后内存。如果文件写盘失败，内存绝不更新；下次重启时也只会加载已落盘的版本。避免「内存生效但文件未落盘」的不一致窗口。

**读路径并发**：`actions_lock` **同时保护写路径和读路径**：
- 主循环用 `ACTION_MAP[name]` 查找动作前先 `with actions_lock:` 取一份引用（dict copy 或 read-only view），然后释放锁再执行动作
- `GET /actions` / `GET /actions/etag` 进入 lock 读 ACTION_MAP 快照 + 算 etag
- `POST /actions` 在 lock 内完成「读文件 → 写 tmp → replace → 更新 ACTION_MAP → 重算 etag」全流程
- 不允许任何代码绕过锁直读 ACTION_MAP

**冲突处理**：name 已存在 → 默认覆盖（返回 `{"replaced": true}` 让前端可提示）。要"防覆盖"的话前端先 GET 一次 actions 列表查重，UI 上做确认。

### `POST /actions/{name}/test` （新）
立即执行一次指定动作（不经语音/LLM），方便录完直接测。

**前置条件**（容器侧强制）：
- 扭矩必须为 ON（关扭矩时电机无力，执行无意义且可能 LeRobot 报错）→ 否则返回 409 `{"error": "torque_off"}`
- 不能并发：上次测试还没执行完 → 返回 409 `{"error": "busy"}`
- name 必须在 ACTION_MAP 中存在 → 否则 404

**name 防 path traversal**：URL 路径里的 `name` 在容器侧二次校验 regex（不依赖前端），避免 `..%2F` 之类绕过

返回 `{"ok": true, "duration_ms": N}`

### `GET /actions` （新，**必需**）
返回当前所有动作清单，供前端做查重 / 列表显示。

```json
{
  "etag": "sha256:abc123...",
  "actions": [
    {"name": "home", "frames": 1},
    {"name": "high_five", "frames": 3}
  ]
}
```

前端在用户输入动作名时实时查重，重名提示「该名字已存在，保存将覆盖」。

### `GET /actions/etag` （新，**必需**，轻量端点）

只返回当前 actions.yaml 内容的指纹，给前端冲突检测用（5s 轮询走这里，不拉全量动作列表，省带宽）：

```json
{"etag": "sha256:abc123..."}
```

**etag 生成方式**：
- 算法：`hashlib.sha256(ACTIONS_YAML 文件 bytes).hexdigest()[:16]`
- 在 `actions_lock` 内每次 POST /actions 成功后重算并缓存 `_etag_cache`，附带当时的 `(size, mtime_ns)` 元组
- 容器重启 → 加载文件时计算并 cache
- 外部进程（Configure 模态 SSH 写）改了文件 → 容器没感知，cache 跟实际不一致

**双因子失效检测**：每次 `GET /actions/etag` 走以下流程：
1. `st = os.stat(ACTIONS_YAML)`
2. 比对 `(st.st_size, st.st_mtime_ns)` 跟 `_etag_cache.stat_tuple`
3. 任一不同 → 重新读文件算 hash + 更新 cache（含新 stat_tuple）
4. 全部相同 → 返回 cached etag

**为什么不光用 mtime**：1s 内多次写 / `touch` 同 ns / 文件系统 mtime 精度 → mtime 不变但内容变；size 跟 mtime 同时不变的概率极低（只有同 ns 写出完全相同 size 的不同内容才会假命中，实际工程可忽略）。

### `POST /actions` 返回值扩展

成功响应包含新 etag：
```json
{"ok": true, "name": "high_five", "frames_count": 3, "etag": "sha256:def456...", "replaced": false}
```

**乐观并发控制**（前端传 If-Match）：
- 前端发起 POST 时带 header `If-Match: <开始录制时拿到的 etag>`
- 容器对比当前 etag，不匹配 → 412 Precondition Failed + 返回当前 etag + actions 列表，前端弹"远端已被修改"对话框
- 前端可选「覆盖保存」（不带 If-Match 重试）或「丢弃当前草稿」

---

## 4. actions.yaml schema 统一

**取消 `poses` / `sequences` 二分**，全用 sequences 表示。单帧姿态 = 1 帧序列。

```yaml
sequences:
  home:
    - joints: {shoulder_pan: 0, shoulder_lift: 0, ...}
      delay: 1.5
  high_five:
    - joints: {shoulder_pan: 20, ...}
      delay: 0.4
    - joints: {shoulder_pan: -20, ...}
      delay: 0.4
    - joints: {shoulder_pan: 0, ...}
      delay: 0.4
```

**迁移**：scaffolding 生成的 default actions.yaml 里 poses → 转成单帧 sequence。robot_arm.py 取消 pose / sequence 分支，统一按 sequence 处理。

---

## 5. 平台侧通用 action_modules

### 5.1 device YAML 声明

```yaml
# devices/verify_arm.yaml
type: robot_inspect
endpoint: "http://{{deploy.host}}:8765/observation"
schema_endpoint: "http://{{deploy.host}}:8765/observation/schema"
poll_hz: 5

action_modules:
  - id: torque
    type: device_command
    label_i18n: { en: "Torque", zh: "扭矩" }
    buttons:
      - label_i18n: { en: "Disable Torque", zh: "关扭矩" }
        endpoint: "http://{{deploy.host}}:8765/torque/off"
      - label_i18n: { en: "Enable Torque", zh: "开扭矩" }
        endpoint: "http://{{deploy.host}}:8765/torque/on"

  - id: record
    type: sequence_recorder
    label_i18n: { en: "Record Action", zh: "动作录制" }
    observation_endpoint: "http://{{deploy.host}}:8765/observation"
    list_endpoint: "http://{{deploy.host}}:8765/actions"      # 查现有
    save_endpoint:  "http://{{deploy.host}}:8765/actions"      # POST 保存
    test_endpoint:  "http://{{deploy.host}}:8765/actions/{name}/test"
    name_pattern: "^[a-z][a-z0-9_]*$"
    default_delay: 0.4
    delay_range: [0.05, 5.0]
```

### 5.2 平台后端反代（POST 扩展，多层防护）

复用 `robot_inspect.py` 的 host+port 白名单，扩展支持 POST。**白名单不只是 host+port**，还要约束允许的 endpoint 集合 + 方法 + body。

新 endpoint：`POST /api/verify/robot_inspect/proxy`

**多层校验**（顺序）：
1. **host+port 白名单**（已有）：endpoint host 在 loopback/RFC1918/link-local + port ∈ [8765-8769]
2. **方法白名单**：method ∈ {GET, POST}，其他拒绝
3. **endpoint 路径白名单**：endpoint URL 必须匹配方案 device YAML `action_modules` 里声明过的 endpoint 字符串（精确字符串比对，不允许任意 path），不然 403
4. **body 大小限制**：payload 序列化后 ≤ 32KB（足够覆盖 50 帧序列 + 6 关节 + delay）
5. **Content-Type 限制**：仅允许 `application/json`
6. **超时**：上游 2s connect + 5s read
7. **响应大小限制**：256KB（同现有 robot_inspect）

**Endpoint 注册机制**：

- **存储**：solution_manager 维护一个 `dict[(solution_id, device_id, endpoint_url_template), 元数据]`
- **URL 形式**：allowlist 存**模板形式**（含 `{{deploy.host}}` 等），不存渲染后 URL
- **Lifecycle**：
  - 加载方案 → 注册（覆盖式，幂等）
  - 卸载方案 / 删除 device → 移除该 (solution_id, device_id) 下的全部条目
  - 平台服务重启 → 启动时全量扫描 `solutions/` 重建（同 SolutionManager 现有的方案加载流程，复用现成钩子）
  - 用户在 App 里改 device YAML（hot reload）→ 该 device 的 allowlist 条目先全删再全加
- **重启冷启间隙**：服务启动到 SolutionManager 加载完成之间 allowlist 为空 → 反代 403。FastAPI startup hook 里必须确保 SolutionManager 加载完成才接受流量（已是现状）

**反代请求 + 渲染流程（前端不可控 render_vars）**：

前端请求 body：
```json
{
  "solution_id": "respeaker_flex_soarm",
  "device_id": "voice_brain",
  "endpoint_template": "http://{{deploy.host}}:8765/actions",
  "method": "POST",
  "payload": {...}
}
```
**注意**：**前端不传 render_vars**。

后端反代流程：
1. 用 `(solution_id, device_id, endpoint_template)` 三元组查 allowlist → 不存在 → 403
2. 从**服务端 device state**（DockerDeviceManager 已部署应用记录里的 `host` / `port` 等）取出 render_vars —— 这些值是 deploy 时由平台决定/记录的，不接受前端覆盖
3. 用服务端 render_vars 渲染模板得到真实 URL
4. 校验真实 URL host+port 仍在 RFC1918/loopback + 端口白名单内（双重校验）
5. 执行 HTTP 请求

**SSRF 防御要点**：
- ✅ render_vars 由服务端从 device state 重建，前端不可覆盖
- ✅ 即使 endpoint_template 通过 allowlist，渲染后 URL 仍要走 host+port 白名单（防 device state 被污染的极端场景）
- ✅ 攻击面收窄到：要 SSRF 必须先污染 device state（部署流程级别的攻击，远高于 verify panel 调用门槛）

**Defense-in-depth**：容器侧必须独立做 schema 校验，因为平台反代不解析业务 payload，无法知道 `delay` 等业务字段是否合理。容器是最终防线。

### 5.3 平台前端

新增 `frontend/src/modules/verify-action-modules/`：
- `index.js` —— 总入口，根据 device YAML 的 `action_modules` 数组渲染
- `device-command.js` —— 按钮组件，POST 反代
- `sequence-recorder.js` —— 完整 wizard

`sequence-recorder.js` 状态机：
```
[idle] ──── observe ───→ [draft_with_frames]
   ▲                            │
   │                            ├─ observe → [draft_with_frames] (++)
   │                            ├─ delete frame → [draft_with_frames] (--)
   │                            ├─ edit delay → [draft_with_frames]
   │                            ├─ test → POST /test (不影响草稿)
   │                            └─ complete → POST /actions → [idle] + toast
   │
   └─── clear ─────────────────┘
```

浏览器内 state（不持久化）：
```js
{
  name: "high_five",
  frames: [
    { joints: {shoulder_pan: 20.5, ...}, delay: 0.4 },
    ...
  ]
}
```

UI 关键交互：
- **观测**：fetch `/observation` → 添加一行到 frames，**不预览**
- **删除帧**：直接从 array 移除
- **改 delay**：inline edit（input type=number）
- **测试动作**：先临时 POST 草稿到 `/test_endpoint`（可选行为，需要容器有 ephemeral test 接口；如果没有就用 save_endpoint + test 两步）

### 5.4 已部署应用卡片「运行/检查」入口

`frontend/src/pages/devices.js` 设备卡片加 [运行/检查] 按钮（条件：该方案有 verify 类型为 robot_inspect 的 step）。

点了 → 打开一个 modal 直接挂载 robot_inspect verify panel（不走完整 deploy 流程）。复用 `RobotInspectPanel` 组件。

---

## 6. 工作量

| 任务 | 工作量 |
|---|---|
| 平台后端：POST 反代扩展 + 白名单 | 0.3d |
| 平台前端：action_modules 渲染框架 | 0.3d |
| 平台前端：device_command 模块 | 0.2d |
| 平台前端：sequence_recorder 模块（状态机 + 表格 + inline edit + i18n + etag 冲突检测） | 2.0d |
| 平台前端：「运行/检查」卡片入口 + modal 挂载 | 0.5d |
| voice-arm：`/torque/{on,off}` endpoint | 0.2d |
| voice-arm：`/actions` endpoint（含原子写 + 内存同步 + 锁 + If-Match 412） | 0.5d |
| voice-arm：`/actions/etag` endpoint + `_etag_cache` + mtime 失效逻辑 | 0.3d |
| voice-arm：`/actions/{name}/test` + `/actions/cancel` endpoint + cancel event + 防抖 ts | 0.3d |
| voice-arm：actions.yaml schema 统一（poses 合并进 sequences）+ robot_arm.py 改造 | 0.3d |
| 测试 — 容器侧（注入 + 并发 + 原子写 + name traversal） | 0.5d |
| 测试 — 平台侧（反代多层校验 + endpoint allowlist + size limit） | 0.3d |
| 测试 — 前端 E2E（录制完整流程 + etag 冲突 + 测试动作安全前置） | 0.5d |
| 文档 + spec compliance | 0.3d |
| **合计** | **~6.5d** |

比初版 5d 多 1.5d（两轮 codex review 累积）：sequence_recorder 加 etag + 取消按钮 +0.5d，etag endpoint 单独工时 +0.3d，cancel endpoint +0.1d，测试拆分按层独立排期 +0.8d，被时序压缩到 +1.5d。

---

## 7. 风险与边界

1. **录制中容器重启 / yaml_file 编辑器同时改 actions.yaml**：
   - 容器重启 → 重新加载 actions.yaml → in-memory ACTION_MAP 全量重建
   - 重启原因可能是：用户在 Configure 模态用 yaml_file 编辑器改了 actions.yaml + 保存（走 SSH 写 + docker compose up -d 路径）
   - 此时浏览器 verify panel 里的录制草稿基于**旧版** actions.yaml 状态，但容器已是新版 → 保存时可能覆盖用户在 Configure 改的内容
   - **三层缓解**：
     - **乐观锁**：保存时 POST 带 `If-Match: <开始录制时的 etag>`；容器对比当前 etag 不匹配 → 412 + 返回新 etag/列表，前端弹冲突对话框
     - **轮询提示**：录制中前端 `GET /actions/etag`（5s 一次）发现变化 → 顶部横幅「设备动作库已被外部修改」+ 按钮 [拷贝草稿 JSON] / [刷新基线]；不立即禁用 [完成保存]（用户可能仍想强制覆盖）
     - **草稿导出**：横幅有 [📋 拷贝草稿 JSON]，把当前 frames 序列复制到剪贴板，用户可以粘到记事本里救命，不至于辛苦 8 帧全废
   - **轮询清理**：sequence_recorder 组件 mount 时 `setInterval`，**unmount 时 `clearInterval`** —— 同 P-3 robot_inspect cleanup 模式。`renderer-registry.cleanupAll()` 调用时也要清。modal close / 路由切换 / verify panel 重渲都触发清理
   - localStorage 自动暂存：**不做**（草稿态生命周期清晰才好排错；用户可手动 [拷贝草稿 JSON] 救命）
2. **关扭矩状态用户离开页面忘记开**：臂保持软态可能下垂。**缓解**：modal 关闭时弹"扭矩仍未开启，确认离开？"
3. **同名覆盖**：默认覆盖。可选：前端先 GET 列表查重，发现重名时确认对话框
4. **并发录制**（两个浏览器同时调 `/actions`）：容器锁保证不竞态，但后写覆盖先写。**接受** —— 这是单用户场景，不做分布式锁
5. **delay 极端值**：[0.05, 5.0] 范围，超出拒绝。0.05 是 LeRobot 最小可分辨；5s 是合理上限
6. **frames 数量**：建议上限 50 帧（防止有人录小时级动作把 actions.yaml 撑爆）
7. **actions.yaml 大小**：复用 P-2 yaml_file 的 100KB 上限作为 sanity check
8. **「测试动作」副作用与安全前置**：用户在录制中点测试 → 臂会动，可能撞用户的手或臂仍处于关扭矩状态。
   - **强制前置条件**（前端按钮状态 + 容器二次校验）：
     - 扭矩必须为 ON（关扭矩态下按钮 disabled + tooltip「请先开扭矩」；容器 endpoint 409 兜底）
     - 距离上次扭矩 ON 至少 500ms 防抖。**容器侧维护 `_torque_on_since_ts`**（POST /torque/on 时记录 `time.monotonic_ns()`），test endpoint 检查 `now - since < 500ms` 则 409；前端按钮 disabled 是 UX 提示，**容器是 source of truth**
     - 二次确认对话框「即将执行 N 帧动作，确认机械臂周围无人？」
   - 测试按钮配色：橙色 warning，不是绿色 primary
   - 测试期间：
     - 禁用其他按钮（防并发）
     - 显示一个**红色取消按钮**「⏹ 紧急停止」，点了 POST `/actions/cancel` → 容器把所有未发的 frame 跳过 + send_action(home) 回安全位
     - 容器需要：`_running_test` flag + `_test_cancel_event` (asyncio.Event)；执行序列循环每帧前检查 cancel event
   - **测试中收到 POST /actions（保存新动作）**：默认 **409 busy**，前端弹「测试进行中，请先取消或等待」。强制 busy 而非排队，避免长测试阻塞保存
   - 409 兜底有意义：用户可绕过前端（curl 直接打 API）；浏览器 disabled 是 UX，容器 enforce 是安全

---

## 8. 不在本次范围

- 复杂时序编辑（拖拽重排帧、关键帧补间）—— v2 再说
- 视觉化关节预览（3D arm 渲染）—— v2 再说
- 录制时的回放（一边录一边在 web 端"虚拟臂"看效果）—— 远期
- 单帧 pose 单独 UI —— 全用 sequence 表示就够了
- 编辑现有动作（重新录制就是编辑，先不做精细 in-place edit）

---

## 9. 测试要点

平台后端：
- POST 反代白名单（非 8765-8769 拒绝）
- 注入字符通过 POST body 仍逐字一致（沿用 P-1 / P-2 测试模式）

容器侧：
- 原子写 + 中途崩溃 → actions.yaml 不会破损（用 tempfile + os.replace）
- 并发 POST /actions → lock 串行
- /actions 写完立即 GET /actions 能看到新动作（内存与文件同步）

前端：
- 草稿态 → 完成 → 清空 toast 闭环
- frames 列表 inline edit
- 录制中断（关 modal）确认对话框
- 同名覆盖 toast 提示
