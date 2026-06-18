# voice-arm Perf Follow-up Plans

后续待办，已完成的 P1/P4/P7/response_mode/P9+P10 见 `/PROGRESS.md` 2026-05-27 条目。

---

## Plan A — 进一步性能优化（按 ROI 排序）

### A1. 历史 KV cache 跨轮复用（多轮场景最大红利）

**问题**：当前 `openvoicestream_agent/tools/runner.py:138-141` 在 `iter > 0` 时**强制关闭** `prefix_cache`：

```python
if iter_idx > 0:
    caller_extra["prefix_cache"] = False
```

注释解释："message list shape has changed (assistant_tool_calls + tool results appended)"。这是粗暴 workaround —— 实际上 history 前缀**仍然稳定**，每轮新增的只是末尾的 user / assistant_tool_calls / tool_result。完全可以增量复用。

**预期收益**：多轮对话每轮省 200-800ms（随历史长度增加）。voice-arm 场景对话长度通常 3-10 轮，累计可观。

**实施方向**：
1. **服务端**：edge-llm 已经有 `_build_prefix_formatted_request`（`tensorrt-edge-llm/experimental/server/api_server.py:763`）按 `messages[:-1]` 切 prefix。需要扩展支持任意 N，让 `messages[:-1]` 仍然命中"system + tools + history[0..N-1]"的累计前缀。
2. **客户端**：`runner.py` 取消 iter>0 强制关 prefix_cache；改为只关 final iteration（最后一次拿 tool_result 给 LLM 总结那次）的 prefix_cache，因为那次 messages 形态最不稳定。
3. **C++ runtime**：确认 `mSystemPromptKVCacheBase`（`cpp/runtime/llmInferenceSpecDecodeRuntime.cpp:2165-2235`）支持 token_ids 前缀**部分匹配**（radix tree），不只是全等。看代码 `std::equal` 那段是按 prefix 比较还是全等。

**风险**：
- Cache stale 时机：history 变化时 invalidate。当前 `_reregister_tools` 已经有 `session.cache_warmed = False` 模式可借鉴。
- 多轮中的 assistant_tool_calls JSON 序列化不稳定（field order、whitespace）可能导致 token_ids 不匹配。需要 canonical serialization。

**工程量**：~200 LOC（服务端 + 客户端协调）+ 完整测试。中等难度。

**验证**：跑一个 5 轮对话测试，对比每轮 TTFT。预期 turn 2-5 每轮省 100-300ms。

---

### A2. LLM round-2 max_tokens 硬限 + stop sequence

**问题**：tool 完成后的 LLM round 2 响应（"已挥手"）当前 max_tokens 没限制（服务端默认 2048）。模型经常多吐："已挥手。需要其他帮助吗？" 之类，15-20 tokens × 80ms = 多花 600-800ms。

**实施方向**：
- `openvoicestream_agent/tools/runner.py` round 2 调用处加 `max_tokens=16` + `stop=["。", "\n"]`
- 短句天然在第一个 `。` 截断，节省 decode 时间
- 或者在 `@tool(completion_max_tokens=16)` 元数据里 per-tool 配置

**风险**：太短截断自然语言（"已挥手" 本身只 3 token，但模型可能想说"动作完成"前还有 padding token）。

**工程量**：~30 LOC + 1 测试。

**预期收益**：100-500ms tail latency。

---

### A3. System prompt 压缩

**问题**：当前 `agent.yaml.tmpl:67-110` 的 system_prompt **2394 字符**，含 9 个 few-shot 示例（"挥手→wave"、"回首→没听清"等）。Few-shot 是为了让 Qwen3-4B-AWQ 严格按 trigger 词匹配，但 9 个可能冗余。

**实施方向**：
1. 把 few-shot 从 9 减到 3-4 个代表性的（正面 + 负面各 2）
2. 改成 ChainOfThought 风格规则描述，让模型抽象出"严格 trigger 匹配"原则，而不是列举所有 case
3. A/B 测试：用一组 query 集合（30-50 个）测压缩前后 tool selection 准确率，要求无显著下降

**预期收益**：50-300ms。Prefix 缩短直接减少 prefill token 数；prefix_cache 也更快命中。

**风险**：tool selection 准确率下降。**必须 A/B**。

**工程量**：1-2 天，重点在 A/B 测试 setup 和 query 集合构建。

---

### A4. ASR 流式 LLM 触发（更激进）

**思路**：现在等 `asr_final` 才启动 LLM。如果在 `asr_partial` 阶段（partial 稳定 200ms 不变化）就**提前**启动 LLM，最终 `asr_final` 跟 partial 一致则 LLM 已经在跑了；不一致就 cancel 重发。

**预期收益**：200-500ms（取决于用户说话节奏）。

**风险**：ASR 修正频繁的话浪费 LLM 算力 + 增加复杂度。需要 partial 稳定性度量。

**工程量**：~150 LOC + 复杂测试。**不建议优先做**，除非前面 A1-A3 都做完仍要继续压。

---

## Plan B — 上游 PR 机会（社区影响力）

来自 `/PROGRESS.md` 2026-05-27 的框架调研结论：现有 voice agent 框架（LiveKit、Pipecat）核心优化（preamble lifecycle、parallel function calling streaming、TRT-LLM first-class）都缺失。可以反哺。

### B1. LiveKit Agents — `on_tool_started` / `on_tool_completed` lifecycle hook

**为什么**：LiveKit Agents 的 `@function_tool` 装饰器目前只支持 tool body 同步调用，没有 lifecycle hook。我们的 `preamble_text` 机制（让 LLM 在 tool 派发瞬间说"好的"）正是这种 hook 的标准用例。

**实施**：
- Fork `livekit/agents`，给 `function_tool` 加 `preamble_text` / `completion_text` 字段
- 给 `AgentSession` 加 `on_tool_started(tool_name, args)` / `on_tool_completed(tool_name, result)` callback
- 提 PR 带我们 voice-arm 验证过的 53% 末段静默削减数据

**优先级**：高。LiveKit issue 区**无人做**这件事，是干净的 API 增量。Jetson + 机器人用户群体直接受益。

**工作量**：~3-5 天（含写测试 + 跑 LiveKit 现有 e2e）。

### B2. LiveKit Agents — TRT-LLM plugin

**为什么**：LiveKit 当前只有 `livekit-plugins-ollama`，TRT-LLM 完全空白（issue #403 之后无下文）。Jetson 用户跑 LiveKit 只能退化用 Ollama，性能差一截。

**实施**：
- 新建 `livekit-plugins-trtllm` 包
- 包装 edge-llm-chat-service 的 OpenAI-compat 接口（或者直接用 NVIDIA 官方 TRT-LLM serving）
- 暴露 `warmup()` 接口（依赖 LiveKit agent 框架接受 backend warmup hook，可能要先推 B1）

**优先级**：高。直接补全 LiveKit edge 生态。

**工作量**：~5-7 天（含 LiveKit plugin 模板适配 + 测试 + 文档）。

### B3. Pipecat — Fix parallel function calling streaming

**为什么**：Pipecat issue #424（parallel function calling 不工作）和 #2787（content + tool_calls 同 turn 处理）都还开着。我们的 P1（wrapper 流式 tool_call 增量解析）+ response_mode parallel 实际已经解决了这两个问题的等价版本。

**实施**：
- 把我们 `edge-llm-chat-service` 里 `_ToolCallStreamParser` 的思路适配到 Pipecat 的 frame-based pipeline
- 提 PR 修 #424，附上我们的实测数据

**优先级**：中。Pipecat 社区规模小于 LiveKit，但 fix 已有 issue 影响力会被作者注意到。

**工作量**：~3-4 天（含理解 Pipecat frame 模型 + 适配）。

---

## Plan C — 长期架构演进

### C1. ovs-agent 框架化抽象 + 公开化

如果决定**保持自研外壳**，可以把 ovs-agent 从内部库变成开源框架，定位是"边缘 LLM 优化的 voice agent 框架"。

**差异化卖点**（vs LiveKit）：
- TRT-LLM first-class
- preamble / response_mode 内建
- 中文 ASR/TTS 插件丰富
- Jetson / RPi 部署指南

**工作量**：3-6 个月。需要文档、CI、版本管理、社区运营。投入大，但占位独特细分。

### C2. 迁移到 LiveKit + 反哺优化作为 plugin

另一条路：放弃自研外壳，迁移到 LiveKit，把核心优化（preamble、prefix_cache 客户端协议、response_mode、TRT-LLM client）做成 LiveKit plugin。

**优点**：享受 LiveKit 社区 + 生态。
**缺点**：迁移成本 1-2 周；某些优化要塞进 LiveKit 抽象可能别扭。

**决策依据**：看团队人力 + 项目优先级。如果团队小、机器人是核心业务、不打算做框架社区运营 → C2 更现实。如果团队有 framework 经验、可以投人维护 → C1 影响力更大。

---

## 优先级建议

短期（1-2 周）：A1（KV 跨轮复用）+ A2（max_tokens 限制）
中期（1 个月）：B1（LiveKit lifecycle PR）+ B2（LiveKit TRT-LLM plugin）
长期（2-6 个月）：C1 或 C2 二选一

A3（prompt 压缩）和 A4（ASR partial trigger）按需做，不强求。
B3（Pipecat fix）有余力再做，社区影响小于 B1/B2。

---

## Plan D — 技术债（来自 codex 本轮 code review）

本轮 codex review 在三个必修 bug 之外抓出的中长期债务。每条带严重度（low/medium）和建议方向。**优先级排在 A/B/C 之后**，没有用户可感知影响，但会让后续维护越来越难。

1. **parallel dispatch 语义需要框架层文档化**（medium）
   `arm_plugin.py` 的 `dispatch_action` / `wait_completion` 拆分是 voice_arm 自己的约定，framework 层没有对应接口要求。建议在 `LLMBackend` / `Plugin` 接口文档或 docstring 里写清楚 "parallel mode tool MUST return within 200ms"，否则下一个写 parallel 工具的人会自己摸索。

2. **parallel 模式 timeout 名不副实**（low）
   `registry.py:57-63` 的 `timeout_s` 默认 10s/15s 是 wait_completion 的总超时，对 dispatch 部分没单独约束。建议加 `dispatch_timeout_ms`（默认 500ms）+ warning 日志监控 dispatch latency，超过即提示工具实现违反 parallel 契约。

3. **cache flag 组合矩阵缺文档**（low）
   `api_server.py:702-770` + `tools.py:799-805` + `edge_llm.py` 四个文件交叉管理 `prefix_cache` / `save_prefix_cache` / `save_system_prompt_kv_cache` flag，注释稀少，新人读这段代码很难拼出完整语义。建议在 `edge_llm.py:_build_extra_body` 加一段 flag matrix 说明。

4. **`session_max_input_tokens=7000` 是魔法数字**（low）
   硬编码假设 engine context ≥ 8K。建议从 `/v1/info` 或 `backend.warmup()` 返回值读取 engine 真实 `max_seq_len` 自动算 budget，省得换模型时手动调这个常数。

5. **测试覆盖盲区**（codex review Part C 提出，medium）
   - `backend.warmup()` 抛异常时 app 启动行为（fail-fast vs warn-and-continue 没测试）
   - parallel dispatch 串口锁竞争（A 动作未完 B 已 dispatch 的赛跑场景）
   - template 模式 `completion_text` 空字符串 ✅（本轮已修，回归测试已加 `test_response_mode_template_empty_completion_text_falls_back_to_await`）
   - trim budget ERROR 时 refuse-to-start vs warn-and-continue 行为差异
   - history 全 `tool` message 时 trim 行为

6. **`session._build_turns` corner case**（low）
   history 全为 `tool` message 时 trim 静默不处理（codex Part A bug 4）。触发条件罕见（要求所有用户回合都是 tool-only），归技术债。修起来要小心 trim 算法的 anchor 语义。

7. **partial warmup state 不一致**（low）
   `edge_llm.py:264` prefix cache 成功即把 `cache_warmed=True`，graph warmup 失败不回滚此标志。当前 fail-open 行为合理（部分热身好过完全没热身），但隐性：后续读 `cache_warmed` 的代码不知道 "已 warm 一半" 的可能。建议改成两个独立标志 `prefix_cache_warmed` + `graph_warmed`，或在日志里显式记 "partial warmup"。

---

**修法建议**：1/3/4 一起做（纯文档/常数，半天），5 单独排（写测试 1-2 天），2/6/7 等下次有相关代码改动再顺手做（不值得为它们专门起 PR）。

---

## Plan E — 开发体验 / 部署便利性

### E1. inject_user_text 远程开发体验（来自 codex review fix 后续）

**背景**：本轮 fix `adf096b` 把 debug_dashboard 默认绑 `127.0.0.1`，关闭了 LAN 暴露面的安全风险。但团队成员如果想远程验证机械臂动作（比如笔记本通过设备 SSH 上 Jetson），需要一种方式访问 dashboard。以下三个选项按安全度从高到低排序：

**选项 A：SSH 端口转发**（推荐，零代码改动）

```bash
ssh -L 18000:localhost:18000 seeed-orin-nx
# 浏览器/curl 访问 localhost:18000 即可走 SSH 隧道到设备的 dashboard
```

优点：不开任何额外端口；隧道随 SSH session 自动关；最安全。
缺点：每个开发者都得自己起隧道。

**选项 B：临时打开 LAN 绑定**

docker compose 加 env：

```yaml
environment:
  - OVS_DEBUG_DASHBOARD_BIND=0.0.0.0
```

注意：**仅在受信任 LAN（如机房内网）使用**；放公网或共享 WiFi **必须**配合防火墙规则限制源 IP，否则等同公开 inject_user_text 接口给任何同网段设备。

**选项 C：Tailscale**

设备装 Tailscale 后，dashboard 仅绑 Tailscale interface（如 `100.x.y.z`），LAN 仍不暴露。需要再加一个 env：

```yaml
environment:
  - OVS_DEBUG_DASHBOARD_BIND=100.111.134.124  # 设备的 Tailscale IP
```

优点：组织内任意 Tailscale 节点直接访问；不需要每次起隧道。
缺点：依赖 Tailscale 部署 + 设备 IP 写死到 compose（IP 变了要改）。

**Action**：在 `solutions/respeaker_flex_soarm/README.md` 或 docker compose 注释里把上面三个选项 + 推荐写清楚（A 最安全），让团队成员有迹可循。当前默认绑 127.0.0.1 是正确的安全 default，但缺少 "怎么在保持安全前提下远程访问" 的指引。

### E2.（占位）后续开发体验问题归这里

类似 inject_user_text 这种 "默认安全但需要开发者绕路" 的设计决策，后续出现的话都集中到 Plan E 而不是散到 A/B/C/D。Plan A/B/C 是产品性能 / 框架 / 战略；Plan D 是技术债；Plan E 专门收纳 DX 类。
