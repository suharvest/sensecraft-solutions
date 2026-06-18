## What This Solution Does

This solution makes a SO-ARM101 6-DoF robotic arm voice-controlled. Say "Hey Jarvis", give a natural-language command — the arm executes one of its configured poses or gesture sequences while the assistant talks back through your speaker.

The voice pipeline runs **fully on-device** on a Jetson Orin NX 16GB. Three companion containers deploy together: a streaming ASR + TTS service (Paraformer + Matcha), an OpenAI-compatible LLM service (Qwen3-4B-AWQ on TensorRT-Edge-LLM), and the voice-arm container that ties them together and drives the SO-ARM. No cloud API key, no usage caps, no internet dependency at runtime. Action poses (a named library of joint-angle sets) and the LLM system prompt are exposed as editable YAML files, so non-developers can add new poses or change how the arm interprets phrases without rebuilding the image. The container also exposes a small HTTP server that any other solution can poll for live joint state.

## Core Benefits

- **Hands-free arm control** — Say "wave" / "pick up" / "go home" and the arm moves; no teach pendant, no Python REPL
- **Customizable without code** — Action poses (`actions.yaml`) and LLM prompt rules (`prompt.yaml`) are plain YAML, editable from device settings
- **Integrable** — Live joint state served at `GET /observation` for other solutions (digital twins, recording tools, safety supervisors) to consume
- **Voice feedback** — Matcha-TTS speaks confirmations and answers back through your speaker, generated locally on the Jetson GPU
- **Fully local, no usage caps** — Speech and LLM inference run on-device; nothing leaves the Jetson once images are pulled

## Integration Scenarios

| Scenario | Description |
|----------|-------------|
| Voice-driven demos | Run interactive product demos at trade shows / training labs without operator intervention |
| Robotics education | Pair with a curriculum to teach voice AI + robotics in one project students can talk to |
| Teleoperation supervisor | Use voice commands to drive supervisory actions while a higher-level controller handles trajectories |
| Multi-solution composition | Other solutions consume `GET /observation` to record demonstrations, visualize the arm in a digital twin, or run safety checks |
| Accessibility research | Explore hands-free robotic manipulation for assistive use cases |

## Interfaces Exposed

| Endpoint | Purpose |
|----------|---------|
| `GET http://<jetson-ip>:8765/observation` | Latest joint positions + gripper state, flat JSON |
| `GET http://<jetson-ip>:8765/observation/schema` | Field-type schema for the observation payload |

These endpoints are polled by the verify panel during deployment, but any external system on the same network can read them.

## What You Need

### Hardware

| Part | Purpose |
|------|---------|
| SO-ARM101 Follower Arm | 6-DoF arm — receives `send_action` calls from the container |
| reComputer Super J4012 | Jetson Orin NX 16GB — runs the voice + arm container |
| reSpeaker Flex XVF3800 | 4-microphone array for far-field voice capture |
| Speaker | Audio output for the assistant's voice replies |
| USB-C cables | Jetson ↔ SO-ARM, Jetson ↔ reSpeaker |

### Software & Accounts

- **Docker** with NVIDIA runtime, available by default on JetPack 6.x (l4t-jetpack r36.x)
- **Internet on the Jetson for the first boot only** — to pull the voice + LLM images (~10 GB) and download the Qwen3 TensorRT engine artifact. Subsequent boots are fully offline.

## Usage Notes

- **First boot takes 5-10 minutes** — Image pulls, model download, and the Qwen3 TensorRT engine warmup run only on first start. Subsequent restarts are seconds.
- **Single-arm scope** — One container instance controls one arm via one USB serial port. Multiple arms = multiple containers + multiple ports.
- **Local-only inference, no API keys** — ASR, LLM, and TTS all run inside containers on the Jetson. No cloud account, no per-call cost, no rate limits.
- **Speakers required** — Voice feedback is core to the UX; the arm replies before it moves.
- **Customizing without rebuilding** — Edit `actions.yaml` to add new poses, or `prompt.yaml` to teach the LLM new phrases — go to **Devices → Voice Brain → Configure** after deployment.
