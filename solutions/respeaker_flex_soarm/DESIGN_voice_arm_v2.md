# voice-arm v2 — 接入 openvoicestream_agent (streaming + function calling)

## 目标

把现在 voice-arm 容器里手撸的 `pipeline.py / stt.py / tts.py / llm.py / audio_recorder.py / wakeword.py` 替换成 `openvoicestream_agent` (OVS-Agent) 的 `MultiModeApp` + `@tool` 框架。只保留机械臂硬件相关的 `robot_arm.py / actions_manager.py / observation_server.py / audio_devices.py`。

## 收益

- **首字延迟从 ~2.8s 降到 ~0.5s**：LLM `stream=True` 逐 token → SLV `/v2v/stream` WS 服务端按句切分 → TTS sentence-by-sentence
- **删除约 1500 行手撸代码**（stt/tts/llm/pipeline/audio_recorder）
- **barge-in 支持**：OVS-Agent 内置 cancel 路径
- **Session 管理升级**：token-budget 裁剪 + tool_calls 原子回滚
- **debug dashboard 复用**：OVS-Agent 自带 web 调试面板

## 不收益 / 接受的 trade

- **Preamble TTS 立即播放**：LLM 在 tool_call 前说"好的"会立刻播，然后机械臂动作期间静默，然后后续 TTS 续上。文档明说接受
- **Tool 串行执行**：一次 LLM turn 内多 tool_calls 顺序跑。机械臂任务 1 轮 1 动作，cap=3 够
- **不走 MCP**：tools 都是 in-process Python `@tool` 函数。MCP 是 OVS-Agent 未来 adapter，不阻塞我们

---

## 架构

### 容器布局（分容器）

```
┌─────────────────────┐    ┌──────────────────────┐    ┌──────────────────────┐
│   seeed-voice       │    │   edge-llm           │    │   voice-arm (NEW)    │
│   :8621             │    │   :8000              │    │   :8765 (obs HTTP)   │
│   /v2v/stream WS    │◄───┤   /v1/chat/...      │◄───┤   ovs-agent +        │
│   (ASR/TTS/VAD)     │    │   (Qwen3-4B-AWQ)    │    │   ArmPlugin +        │
└─────────────────────┘    └──────────────────────┘    │   OpenWakeWordSource │
                                                       │   robot_arm.py       │
                                                       │   /dev/snd /dev/ACM* │
                                                       └──────────────────────┘
```

voice-arm 容器：单进程，跑 `ovs-agent run voice_arm`，内嵌 OpenWakeWordSource + ArmPlugin。**mic 单一所有者 = AudioIO**。

### 代码结构

```
solutions/respeaker_flex_soarm/assets/docker/
├── Dockerfile.slim              （改）增 ovs-agent 依赖 + sounddevice 替代 PyAudio
├── docker-compose.yml           （改）voice-arm service 入口换成 ovs-agent
├── requirements.txt             （改）+ openvoicestream-agent, sounddevice; - pyaudio, openai (agent 自带)
├── entrypoint.sh                （改）保留 ARM_PORT 探测 + pulse cookie + reSpeaker source 暂停，最后 exec ovs-agent run voice_arm
│
├── voice_arm/                   （新）— 我们的 app package
│   ├── __init__.py
│   ├── app.py                   class VoiceArmApp(MultiModeApp)
│   ├── arm_plugin.py            class ArmPlugin(Plugin) — 拥有 RobotArm 实例 + 暴露给 tools
│   ├── tapped_audio_io.py       class TappedAudioIO(AudioIO) — start_capture_tap()
│   ├── openwakeword_source.py   class OpenWakeWordSource(WakeSource)
│   ├── arm_tools.py             register_arm_tools(arm, actions_yaml)
│   └── config.yaml              ovs-agent config (subbed from defaults + env)
│
├── robot_arm.py                 （保留不动）— ArmPlugin 持有它
├── actions_manager.py           （保留不动）— ArmPlugin 用它加载 actions.yaml
├── observation_server.py        （保留）— 独立 thread/asyncio task 跑在 ArmPlugin.start()
├── audio_devices.py             （保留）— resolve_input_index() 给 TappedAudioIO 用
│
└── ❌ DELETE: pipeline.py, stt.py, tts.py, llm.py, audio_recorder.py, wakeword.py
```

`default_config/`：保留 `actions.yaml` 和 `prompt.yaml`（系统提示词），新增 `agent.yaml` 模板（ovs-agent 配置，含 SLV/LLM URL 由 env 注入）。

---

## 关键改动详解

### 1. TappedAudioIO（~50 行）

```python
# voice_arm/tapped_audio_io.py
import asyncio
from openvoicestream_agent.audio_io import AudioIO

class TappedAudioIO(AudioIO):
    """AudioIO + multi-consumer capture tap.

    Wake-word source needs raw mic chunks in parallel with the SLV
    streaming consumer. We can't open the mic twice (ALSA exclusive
    on reSpeaker), so the single sounddevice callback fans out to
    every registered tap queue.

    Backpressure: each tap has its own bounded queue. If a tap consumer
    falls behind, its queue drops (oldest first) — never blocks the
    primary capture queue feeding SLV. Wake-word is OK with occasional
    drops; user-utterance ASR is not.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._taps: list[asyncio.Queue] = []
        self._taps_lock = asyncio.Lock()  # actually only mutated from loop thread

    def _safe_put(self, buf: bytes):
        # Override: in addition to primary _in_queue, fan out to taps.
        super()._safe_put(buf)
        for q in list(self._taps):
            try:
                q.put_nowait(buf)
            except asyncio.QueueFull:
                # Drop oldest, push newest (wake source can tolerate gaps).
                try:
                    q.get_nowait()
                    q.put_nowait(buf)
                except Exception:
                    pass

    async def start_capture_tap(self) -> "asyncio.Queue[bytes]":
        """Return a NEW queue that gets a copy of every mic chunk."""
        q: asyncio.Queue[bytes] = asyncio.Queue(maxsize=32)
        self._taps.append(q)
        return q
```

**风险**：`_safe_put` 是 AudioIO 内部方法，签名可能上游变。需要测试覆盖；如果担心 brittle，用组合代替继承（包一层 audio_io 实例 + 自己开 callback）。

### 2. OpenWakeWordSource（~150 行）

```python
# voice_arm/openwakeword_source.py
import asyncio
import logging
import time
from typing import Any

import numpy as np
from openwakeword import Model
from openvoicestream_agent.wake_source import WakeSource

logger = logging.getLogger(__name__)


class OpenWakeWordSource(WakeSource):
    name = "openwakeword"

    def __init__(
        self,
        app,
        model_name: str = "hey jarvis",
        threshold: float = 0.5,
        cooldown_s: float = 2.0,
        mic_channels: int = 6,
        wake_channel: str = "all",  # "all" | "0" | "1" ...
        chunk_samples: int = 1280,  # openwakeword expects 80ms @ 16k
    ):
        super().__init__(app)
        self.model = Model(
            wakeword_models=[model_name],
            inference_framework="onnx",  # numpy 2.x ABI safe
            vad_threshold=0.0,
        )
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self.mic_channels = mic_channels
        self.wake_channel = wake_channel
        self.chunk_samples = chunk_samples
        self._task: asyncio.Task | None = None
        self._last_wake = 0.0
        self._buffer = np.zeros(0, dtype=np.int16)

    async def start(self):
        self._task = asyncio.create_task(self._loop(), name="openwakeword")
        logger.info(f"OpenWakeWordSource started: model={self.model.models}")

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self):
        # Wait for AudioIO to be ready
        await asyncio.sleep(0.5)
        tap = await self.app.audio.start_capture_tap()
        while True:
            chunk = await tap.get()
            mono = self._extract_mono(chunk)
            self._buffer = np.concatenate([self._buffer, mono])
            # Process in 1280-sample windows (80ms @ 16k)
            while len(self._buffer) >= self.chunk_samples:
                window = self._buffer[: self.chunk_samples]
                self._buffer = self._buffer[self.chunk_samples :]
                scores = self.model.predict(window)
                for wname, score in scores.items():
                    if score > self.threshold and self._cooldown_ok():
                        logger.info(f"WAKE: {wname} score={score:.3f}")
                        self._last_wake = time.monotonic()
                        await self.app.wake(source=self.name)
                        self._buffer = np.zeros(0, dtype=np.int16)  # discard stale
                        break

    def _extract_mono(self, chunk: bytes) -> np.ndarray:
        """Convert int16 multichannel bytes → mono int16 array."""
        arr = np.frombuffer(chunk, dtype=np.int16)
        if self.mic_channels == 1:
            return arr
        # Reshape: (frames, channels)
        frames = arr.reshape(-1, self.mic_channels)
        if self.wake_channel == "all":
            # Mean across mics, clipped to int16 range
            return np.mean(frames, axis=1).astype(np.int16)
        else:
            ch = int(self.wake_channel)
            return frames[:, ch].copy()

    def _cooldown_ok(self) -> bool:
        return time.monotonic() - self._last_wake > self.cooldown_s
```

**关键点**：
- 输入采样率必须 16k（AudioIO 默认就是 16k），如果 reSpeaker 上 ALSA 默认率不同需要在 sounddevice 端 resample
- buffer 在 wake 后清空，避免下个 wake 立刻命中残留
- chunk_samples=1280（80ms@16k）是 openwakeword 的标称输入

### 3. ArmPlugin（~100 行）

```python
# voice_arm/arm_plugin.py
import asyncio
import logging
import threading
from pathlib import Path
from typing import Any

from openvoicestream_agent.plugin import Plugin

from .arm_tools import register_arm_tools
from actions_manager import ActionsManager
from robot_arm import RobotArm

logger = logging.getLogger(__name__)


class ArmPlugin(Plugin):
    """Owns the SO-ARM serial port + actions library + observation HTTP server.

    Registers actions as @tool functions against the app's tool registry
    during setup. Tools dispatch into ArmPlugin.execute_action which
    runs serial I/O in a thread (LeRobot's bus is sync).
    """
    name = "arm"

    def __init__(self, app, config: dict):
        super().__init__(app)
        self.cfg = config
        self.arm: RobotArm | None = None
        self.actions: ActionsManager | None = None
        self._obs_server_thread: threading.Thread | None = None

    async def setup(self):
        # Load actions library
        actions_path = Path(self.cfg["actions_yaml_path"])
        self.actions = ActionsManager.load(actions_path)

        # Connect arm
        self.arm = RobotArm(
            port=self.cfg["arm_port"],
            arm_id=self.cfg["arm_id"],
            move_delay=self.cfg["move_delay"],
            gesture_delay=self.cfg["gesture_delay"],
        )
        # Connect on a thread — LeRobot is sync
        await asyncio.to_thread(self.arm.connect)
        logger.info(f"Arm connected on {self.cfg['arm_port']}")

        # Register tools (one @tool per action)
        register_arm_tools(
            registry=self.app.tool_registry,
            arm_plugin=self,
            actions=self.actions.list_with_descriptions(),
        )
        logger.info(f"Registered {len(self.actions.list_with_descriptions())} arm tools")

    async def start(self):
        # Start observation cache updater
        self._obs_task = asyncio.create_task(self._obs_loop(), name="arm-obs-cache")
        # Optional: start HTTP observation server (preserve existing /api/state etc.)
        from observation_server import start_server_thread
        self._obs_server_thread = start_server_thread(
            arm=self.arm,
            port=int(self.cfg.get("observation_port", 8765)),
        )

    async def stop(self):
        if self._obs_task:
            self._obs_task.cancel()
        if self.arm:
            await asyncio.to_thread(self.arm.disconnect)

    async def _obs_loop(self):
        while True:
            try:
                await asyncio.to_thread(self.arm.update_cache)
            except Exception:
                logger.exception("arm obs cache update failed")
            await asyncio.sleep(0.5)

    async def execute_action(self, name: str) -> dict:
        """Called by tool dispatch. Returns {success, action, error?}."""
        try:
            frames = self.actions.get_frames(name)
            await asyncio.to_thread(self.arm.execute_sequence, frames)
            return {"success": True, "action": name}
        except KeyError:
            return {"success": False, "error": f"unknown action: {name}"}
        except Exception as e:
            logger.exception(f"action {name} failed")
            return {"success": False, "error": str(e)}
```

### 4. arm_tools (~30 行)

```python
# voice_arm/arm_tools.py
import asyncio
from openvoicestream_agent.tools import ToolCallCtx

def register_arm_tools(registry, arm_plugin, actions: list[dict]):
    """Build one @tool per action. Closures capture action name + plugin."""
    for entry in actions:
        action_name = entry["name"]
        description = entry.get("description") or f"Execute the {action_name} action."

        # Factory closure to capture variables correctly
        def _make(name=action_name, desc=description):
            async def _tool() -> dict:
                """Execute a pre-recorded arm motion."""
                return await arm_plugin.execute_action(name)
            _tool.__name__ = name
            _tool.__doc__ = desc
            registry.tool(name=name, description=desc, timeout_s=15.0)(_tool)

        _make()
```

### 5. VoiceArmApp (~40 行)

```python
# voice_arm/app.py
import logging
from pathlib import Path

import yaml
from apps.multi_mode.app import MultiModeApp
from openvoicestream_agent.tools import default_registry

from .arm_plugin import ArmPlugin
from .openwakeword_source import OpenWakeWordSource
from .tapped_audio_io import TappedAudioIO

logger = logging.getLogger(__name__)


class VoiceArmApp(MultiModeApp):
    """SO-ARM voice agent. Wakeword → SLV streaming → LLM tool call → arm motion."""

    def _make_audio_io(self):
        """Override BaseApp default to use TappedAudioIO."""
        return TappedAudioIO(
            input_device=self.config.input_device,
            output_device=self.config.output_device,
            input_sr=16000,
            output_sr=getattr(self.config, "output_sr", 24000),
        )

    def __init__(self, config):
        super().__init__(config)

        # Mount our own tool registry (allowlist will be in config.yaml)
        self.tool_registry = default_registry

        # Arm plugin owns serial port + tool registration
        arm_cfg = config.arm  # nested config block
        self.register(ArmPlugin(self, arm_cfg))

        # Local wake word
        wake_cfg = config.wakeword
        self.register(OpenWakeWordSource(
            self,
            model_name=wake_cfg.get("model", "hey jarvis"),
            threshold=wake_cfg.get("threshold", 0.5),
            cooldown_s=wake_cfg.get("cooldown_s", 2.0),
            mic_channels=wake_cfg.get("mic_channels", 6),
            wake_channel=wake_cfg.get("wake_channel", "all"),
        ))


App = VoiceArmApp  # for ovs-agent CLI loader
```

**关键**：覆盖 BaseApp 的 audio_io 工厂方法。如果上游没有提供 hook（只是直接 `self.audio = AudioIO(...)`），需要更暴力的 monkey-patch 或 post-init 替换。**这是设计中最大的不确定点之一，需要 codex 确认 BaseApp 的 audio 实例化时机。**

### 6. config.yaml 模板

```yaml
# /opt/seeed/voice_arm/config/agent.yaml
# 由 entrypoint.sh 渲染：env vars 替换 ${VAR}
pipeline_mode: wake_word
default_mode: chat
wake_sources: []  # 我们手动注册 OpenWakeWordSource，不走 stub registry

slv_url: ws://${VOICE_SERVICE_HOST}:${VOICE_SERVICE_PORT}/v2v/stream

llm_backend: edge_llm
llm_base_url: http://${LLM_SERVICE_HOST}:${LLM_SERVICE_PORT}/v1
llm_model: ${LLM_MODEL}
llm_first_token_timeout_s: 15.0
llm_stream_idle_timeout_s: 30.0

# Tool calling (NEW)
tools_enabled: true
tools_default_allowlist:
  - home
  - pick_ready
  - open_gripper
  - close_gripper
  - look_up
  - look_down
  - wave
  - dance
  - high_five
tools_max_iterations: 3

# Mode-specific system prompt (loaded from prompt.yaml)
mode_overrides:
  chat:
    system_prompt: |
      ${SYSTEM_PROMPT_FROM_PROMPT_YAML}

# Audio
input_device: ${MIC_INDEX}      # plughw:X,Y string from audio_devices.py
output_device: ${SPEAKER_DEVICE}
output_sr: 16000                # matcha TTS native, avoid resample

# Our extension blocks
wakeword:
  model: ${WAKEWORD_MODEL}
  threshold: ${WAKEWORD_THRESHOLD}
  cooldown_s: ${WAKEWORD_COOLDOWN}
  mic_channels: 6
  wake_channel: ${WAKEWORD_CHANNEL}

arm:
  arm_port: ${ARM_PORT}
  arm_id: ${ARM_ID}
  move_delay: ${ARM_MOVE_DELAY}
  gesture_delay: ${ARM_GESTURE_DELAY}
  actions_yaml_path: /opt/seeed/voice_arm/config/actions.yaml
  observation_port: ${OBSERVATION_PORT}
```

### 7. entrypoint.sh 改动

保留：ARM_PORT 探测、pulse cookie 复制、reSpeaker source 暂停、wakeword 模型下载、PYTHONPATH 设置。

替换最后一行：
```bash
# 旧
exec python3 pipeline.py

# 新
exec uv run ovs-agent run voice_arm \
  --config /opt/seeed/voice_arm/config/agent.yaml
```

新增：渲染 `agent.yaml`（envsubst 或 Python 一行）从 `default_config/agent.yaml.tmpl` + 当前 env。

### 8. Dockerfile.slim 改动

```dockerfile
# 增
RUN pip install --no-cache-dir \
    openvoicestream-agent \
    sounddevice \
    websockets

# 减
# pyaudio (替换为 sounddevice)
# openai (agent 内部带)
# httpx (agent 内部带)

# apt 增
RUN apt-get update && apt-get install -y --no-install-recommends \
    libportaudio2 \
  && rm -rf /var/lib/apt/lists/*
```

### 9. docker-compose.yml 改动

`voice-arm` service：
- 仍然 depends_on seeed-voice + edge-llm
- env vars 重组（去掉 STT_LANGUAGE / TTS_SID / TTS_SPEED — 现在归 SLV 管，由 agent 通过 SLV 默认 profile 配置）
- 仍然挂 /dev/snd, /dev/user, host pulse cookie
- 仍然 cgroup rules + group_add

---

## Codex 审核结果（2026-05-25）— 必须 patch 的修正

R1/R4/R6/R7/R10 + 3 个命名错误是硬伤；以下 patch 必须落到实施代码里：

| Fix | 改动 |
|---|---|
| **F1 (R1)** AudioIO 替换时机 | `VoiceArmApp.__init__`：调用 `super().__init__(config)` 之后立即 `self.audio = TappedAudioIO(...)`（覆盖 BaseApp 的实例）。不要 override `_make_audio_io`（没这个方法）。要在 `run()` 打开 stream 前完成 |
| **F2 (R4)** Plugin.setup 是同步 | `ArmPlugin`：`setup()` 改为**同步方法**，只做：(a) 加载 actions.yaml；(b) `register_arm_tools(...)` 注册 tools。 arm.connect / obs_server.start 移到 `async def start()` |
| **F3 (R6)** AudioIO 单通道 | `AudioIO` 写死 `channels=1`（`audio_io.py:139`）。在 sounddevice 层让 PortAudio 做 down-mix，OpenWakeWordSource 不再 reshape 6→1。默认配 `mic_channels=1`。reSpeaker 实际能否在 ch=1 模式下打开 USB hw exclusive 设备需要部署时验证（gotcha 风险） |
| **F4 (R7)** ActionsManager API | 用 `actions.get_sequence(name)`，不是 `get_frames(name)`。`get_sequence` 可能返回 None 要处理 |
| **F5 (R10)** observation_server | import `from observation_server import start_observation_server`，调用 `start_observation_server(robot_arm, actions_manager, port)` |
| **F6** Config 字段名 | 用 `audio_input_device` / `audio_output_device` / `audio_output_sample_rate`，不是 `input_device` / `output_device` / `output_sr` |
| **F7** import 路径 | `from apps.multi_mode.app import MultiModeApp` —— `apps/` 在 `seeed-local-voice/agent/apps/`，**不在** `openvoicestream_agent/apps/`。容器内 PYTHONPATH 要包含 `seeed-local-voice/agent` |
| **F8** plugin start 非阻塞 | `ArmPlugin.start()` 在 event loop 里，arm.connect / serial open 必须包 `asyncio.to_thread(...)`，否则 stall 整个 agent |

### 已确认安全 ✅
- **R5**：SLV PCM 4字节头自带 sample rate，BaseApp 自动 set，我们配的只是设备默认值
- **R9**：`/no_think` 在 system_prompt 里逐字保留，不被 strip
- **R8**：机械臂动作跑完不中断，barge-in 只回滚 LLM history（**用户决策：物理动作半截更危险**）

### 部署时验证 ⚠️
- **R2**：TappedAudioIO 的 tap fanout 别 stall 主 queue（慢消费者只丢 tap queue 自己的数据）
- **R3**：`default_registry` 全局单例，agent 重启 / 测试中要确认无 tools 残留（首次启动 clear 一次）
- **R6 后续**：reSpeaker XVF3800 6ch USB 设备在 sounddevice `channels=1` 模式下能开成功吗？PortAudio down-mix 通常 OK，但 USB hw exclusive 可能拒绝。**首次部署时 list_devices + 试录音**，若失败 fallback 到多通道 AudioIO 自实现

---

## 原风险列表（保留供参考）

| # | 风险 | 缓解 |
|---|---|---|
| R1 | `BaseApp` 怎么实例化 `self.audio`？我们的 `_make_audio_io()` override 假设是工厂模式。如果是 `__init__` 里直接 `AudioIO(...)`，子类化无法替换 | codex 读 `app_base.py` 实际看一下 |
| R2 | `AudioIO._safe_put` 是私有方法，未来上游改动会破坏我们的 TappedAudioIO 子类 | 备选：组合替代继承，自己开 sounddevice callback。但要 mic 单消费者 |
| R3 | `tool_registry` 全局单例 `default_registry`。多个 VoiceArmApp 实例（不会有，但理论上）会污染 | 不阻塞，但记录 |
| R4 | `register_arm_tools` 在 `ArmPlugin.setup` 调用，时序上是 BaseApp 初始化结束、`run()` 开始之前吗？runner 跑第一轮时 registry 必须已就绪 | codex 看 plugin lifecycle 顺序 |
| R5 | `output_sr=16000` 假设 SLV /v2v/stream 返回 matcha 16k PCM。如果实际 24k 会播放慢 25% | 用 SLV 协议事件里的 sample rate（slv_client 应有），不是配置写死 |
| R6 | reSpeaker 6 通道在 sounddevice 下能开吗？现有 PyAudio 路径已验证可行，但 sounddevice 用的是 PortAudio v19，行为可能不同 | 部署后先 list_mics + 测试录音 |
| R7 | `actions.yaml` 改 schema 后 `actions_manager.get_frames(name)` 是否存在？现有代码 `list_with_descriptions()` + 旧 schema 兼容 | 检查 actions_manager.py |
| R8 | LLM tool_call 后 ArmPlugin 用 `asyncio.to_thread(execute_sequence)` 跑阻塞 serial I/O。如果用户 barge-in 中断这一轮，机械臂动作不能被 cancel（serial 没法中途打断） | 接受。barge-in cancel 只回滚 history，物理动作跑完。文档明说 |
| R9 | `prompt.yaml` 含 `/no_think` 软开关，agent 的 `system_prompt` 字段会不会去掉它（trim 之类）？ | grep agent 源码确认 |
| R10 | observation_server.py 用了 Flask/FastAPI（不知道）开 8765，在 asyncio 环境下要不要包成 task | 看现有代码 |

---

## 测试 / EVIDENCE 要求

### 单元
- `TappedAudioIO` 多 tap 并行收数据，慢消费者不阻塞主消费者
- `OpenWakeWordSource._extract_mono` 6→1 通道正确
- `register_arm_tools` 闭包正确（不被覆盖到最后一个 name）
- `ArmPlugin.execute_action` 返回 dict 形状

### 集成（mock SLV + LLM）
- VoiceArmApp 启动 → wake → fake LLM 吐 tool_call("home") → ArmPlugin.execute_action 被调 → response 写回 LLM → 第二轮 LLM 文本 → TTS

### 设备（seeed-orin-nx）
1. 部署 → `docker logs voice-arm` 看启动无错
2. 真说 "hey jarvis, 回到原点" → 看：
   - `[WAKE]` 日志
   - SLV ASR final 文本
   - LLM tool_call 日志（含 first-token timing）
   - ArmPlugin execute_action 日志
   - 物理动作发生
   - SLV TTS 音频从 JST 喇叭出来
3. 时间测量：
   - wake → first TTS sound（目标 < 1.5s）
   - 对照旧版的 2.8s
4. 鲁棒性：
   - 连续 10 次唤醒，无 mic 死锁
   - tool_call 异常（ARM 拔掉）→ LLM 收到 error → 自然语言反馈

### 回滚预案
- 旧 `pipeline.py` 链路代码保留在 git history（不删 commit）
- docker-compose 留 env var `VOICE_ARM_MODE=legacy` 切回旧 entrypoint（可选，纯保险）

---

## 工作量预估

| 阶段 | 时长 |
|---|---|
| 设计文档（本文件） | ✅ 完成 |
| codex 审 + 修订 | 0.5h |
| 实施（dispatch general-purpose） | 4-6h |
| 设备部署 + 调通 | 2h |
| **总** | **~1 天** |
