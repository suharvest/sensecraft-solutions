# Known Issues — respeaker_flex_soarm

## ISSUE-001: Multi-turn LLM tool-switching degradation (Qwen3-4B-AWQ)

**Severity**: User-visible. LLM 在第 3 轮以上切换不同工具时倾向跳过 tool_call，直接生成 "已X" 文本响应 → 用户听到回复但机械臂不动。

### 复现条件

清干净 session 后，inject 不同工具：
1. Turn 1 "挥手" (history=1) → ✓ tool_call(wave)
2. Turn 2 "跳舞" (history=5) → ✓ tool_call(dance)
3. Turn 3 "点头" (history=9) → ✗ 退化，直接 "已点头"，无 tool_call
4. 后续轮次全部退化

### 不复现条件

- 同一个工具重复（连 6 轮 "挥手" 全过）
- 单轮场景（每次清 history）

### 根因（hypothesis）

Qwen3-4B-AWQ small 模型 + 工具切换 + recency bias。模型从 history 学到 "user → assistant '已X'" 模式后 fallback 到文本响应。原因可能是：
- Chat template tool_calls 渲染到 prompt 的强度不够（验证过 client 端 messages 有 tool_calls，server 端实际 prompt 未验证 —— DEBUG_PROMPT 日志在 EdgeLLMBackend 路径下没触发）
- 4B 模型 attention 跨多 turn + 工具切换时不稳
- ASR 加 "。" 句号让 trigger phrase 不再 literal 匹配

### 当前 workaround

**单轮模式**：voice-arm 默认每 turn 结束后清 history (`clear_history_on_turn_end: true`)。voice-arm 是命令接口不是 chatbot，不需要 multi-turn 上下文。

实现位置：`assets/docker/voice_arm/arm_plugin.py` 的 `on_assistant_done()` hook —— 通过 ovs-agent 框架现成的 `on_assistant_done` 广播回调，在每轮 tts_done 后清掉 `session.history`（保留 prefix/graph warmup 标志，避免每轮重 warmup 增加 ~200ms 延迟）。

可通过 `agent.yaml` 里 `metadata.arm.clear_history_on_turn_end: false` opt-out（或 env `ARM_CLEAR_HISTORY_ON_TURN_END=false`）。

### 待修方向（按优先级）

1. **Verify chat template rendering**: 派 codex 或手工 dump server-side rendered prompt 字符串，确认 history 里 assistant.tool_calls 是否真的渲染到模型 token 序列里。如果没渲染，那是 chat template bug，单独 fix；如果渲染了，确认是模型能力问题
2. **Prompt strengthening**: 加 anti-mimicry 规则 "STRICTLY follow system instructions, DO NOT infer pattern from history"
3. **Tool schema enhancement**: 给每个 tool 加更明显的 trigger phrase 规则
4. **Model upgrade**: 尝试 Qwen3-7B 或更大模型看是否消失
5. **Detect & strip 2-段 turn**: runner 检测 LLM 没调 tool 但用户输入含 trigger 词时，从 history strip 这轮（不让污染累积）
6. **Long-term**: 考虑 specialized robot-tool-calling fine-tune

### 相关 commit / 测试

- 单轮模式 fix: 本次交付（feat(voice_arm): default single-turn mode）
- 复现测试: 3 轮 inject 不同工具，看 history=9 turn 是否退化

---

## ISSUE-002: `nod` action LLM selection failure (Qwen3-4B-AWQ)

**Severity**: 1/10 actions affected。其他 9 个 actions (wave/dance/shake_head/look_up/look_down/home/open_gripper/close_gripper/pick_ready) 全部正常工作。

### 现象

即使在干净 session（单轮模式，history 空）下，inject 或语音 "点头" → LLM 不调 `nod` tool，直接生成 "已点头" 文本 → 机械臂不动。

### 验证

- "挥手" → ✓ tool_call(wave)
- "跳舞" → ✓ tool_call(dance)
- "摇头" → ✓ tool_call(shake_head)  ← 本质相似的动作正常
- "点头" → ✗ 仅文本 "已点头"，无 tool_call

### 根因 hypothesis

- Qwen3-4B-AWQ 对中文 "点头" trigger 词有特殊偏置（可能训练数据里 "点头" 多以"表示同意"的语义出现 → 模型倾向用文本表态而非动作执行）
- description 原表述 "Nod the wrist" 模型可能跟其他动作的 wrist 描述混
- 中文 token "点头" 在 chat template 渲染后可能命中某个内置 acknowledgement pattern

### 尝试过未生效（本次交付）

3 个候选都试过，全部失败（"已点头" 仍出现，零 tool_call）：

1. **候选 1 — 强化 description**：明确"wrist up-down repeatedly"+ 多 trigger 词（点点头/点一下头/同意）
2. **候选 2 — MUST 指令**：description 加 "MUST be called when user says 点头"
3. **候选 3 — system_prompt 专属规则**：在 prompt.yaml 加 "Special rule: if user says 点头 ... you MUST call the nod tool" + "Never just reply with text like 已点头"

候选 1 的强化 description 作为最终配置保留（无害且语义更清晰），候选 3 已回滚 prompt.yaml。

### 待修方向

1. **重命名 action**：把 `nod` 改成 `head_nod` 或 `wrist_nod` 避开 "nod" 关键词偏置 —— 简单可行，下一版可尝试
2. **加 anti-mimicry 系统规则**：放宽到所有 tool ("STRICTLY: when user asks for any motion, CALL the tool; NEVER reply 已X 文本")
3. **Few-shot 示例**：在 system prompt 加 1-2 个 "user: 点头 → tool_call(nod)" 示例
4. **模型升级**：Qwen3-7B 或 specialized robot-tool fine-tune

### Workaround

用户用 "摇头" / "挥手" / "跳舞" 等其他 9 个 action 触发词均工作正常。如必须演示"点头"动作，建议改语音为 "做一个点头动作" 或暂时跳过该动作。
