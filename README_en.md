**English** | [中文](README.md)

# SenseCraft Solutions

[![CI](https://github.com/suharvest/sensecraft-solutions/actions/workflows/guard.yml/badge.svg)](https://github.com/suharvest/sensecraft-solutions/actions/workflows/guard.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**18+ ready-to-deploy edge AI solutions for NVIDIA Jetson, RK3576/RK3588, and Raspberry Pi** — plus the open tooling to author and validate your own.

<!-- TODO: Add a hero screenshot or architecture diagram here (e.g. the SenseCraft app deploying a solution, or a diagram of the open/closed layers) -->

Deploy offline voice AI, computer vision, smart retail, robotics, and more — directly from the [SenseCraft desktop app](https://www.seeed.cc/category/reference-designs) or via the `solutionctl` CLI. No cloud dependency required.

---

## Solutions

| Solution | Hardware | Category |
|----------|----------|----------|
| [Local Voice Service](solutions/jetson_voice_assistant/) | Jetson Orin · RK3576 · RK3588 · RPi | Voice AI (ASR + TTS, ≤180ms, offline) |
| [Smart Retail Voice AI](solutions/smart_retail_voice_ai/) | Jetson | Retail / Voice |
| [Smart Space Assistant](solutions/smart_space_assistant/) | Jetson | Voice AI |
| [GPT OSS 20B](solutions/gpt_oss_20b/) | Jetson | Local LLM |
| [AI Lab](solutions/ai_lab/) | Jetson | AI development environment |
| [Depth Anything v3](solutions/depth_anything_v3/) | Jetson | Depth estimation |
| [Industrial Security](solutions/industrial_security_jetson/) | Jetson | Security / Vision |
| [Gun Detection (Frigate)](solutions/gun_detection_frigate/) | Jetson | Security / Vision |
| [NVBlox + Orbbec](solutions/nvblox_orbbec/) | Jetson | 3D reconstruction |
| [reCamera Heatmap (Grafana)](solutions/recamera_heatmap_grafana/) | reCamera | Analytics / Dashboard |
| [reCamera Parking Monitor](solutions/recamera_parking_monitor/) | reCamera | Smart Parking |
| [reCamera Ecosystem](solutions/recamera_ecosystem/) | reCamera | Platform tools |
| [Reachy Claw Voice Robot](solutions/reachy_claw_voice_robot/) | Reachy Mini + Jetson | Robotics + Voice |
| [ReSpeaker Flex + SO-ARM100](solutions/respeaker_flex_soarm/) | ReSpeaker + ARM | Robotics + Audio |
| [OpenClaw Deploy](solutions/openclaw_deploy/) | Jetson | Robotics |
| [Smart Warehouse](solutions/smart_warehouse/) | Jetson | Logistics / Vision |
| [Smart HVAC Control](solutions/smart_hvac_control/) | Jetson | Building automation |
| [Indoor Positioning (BLE + LoRaWAN)](solutions/indoor_positioning_ble_lorawan/) | Edge | Location / IoT |

---

## How it works

```
┌─────────────────────────────────────────────────────┐
│  This repo (open, Apache-2.0)                       │
│  ┌──────────────┐  ┌────────┐  ┌─────────────────┐ │
│  │ solutions/   │  │ spec/  │  │ packages/       │ │
│  │ YAML + guides│  │ schema │  │ solutionctl     │ │
│  │ (bilingual)  │  │ + rules│  │ solution-spec   │ │
│  └──────────────┘  └────────┘  └─────────────────┘ │
└──────────────────────────┬──────────────────────────┘
                           │ validated against
                           ▼
┌─────────────────────────────────────────────────────┐
│  SenseCraft Engine (closed-source, signed binary)   │
│  Distributed with the SenseCraft desktop app        │
│  Handles: device SSH, Docker deploy, app UI         │
└─────────────────────────────────────────────────────┘
```

Each solution is a self-contained directory: a `solution.yaml` (hardware catalog, deploy presets, bilingual metadata), bilingual `guide.md` + `description.md`, Docker Compose config, and assets. The engine validates solutions against the published JSON Schema contract in `spec/` before deployment.

`solutionctl` is the CLI face of the engine for headless use — it locates the installed binary and drives it via subprocess / local REST.

---

## Quick start

```bash
# Install dependencies
uv sync

# Validate a solution offline (no engine / app needed):
uv run --package sensecraft-solutionctl solutionctl validate solutions/jetson_voice_assistant

# Package a solution into an import-ready zip (to preview in the desktop app):
uv run --package sensecraft-solutionctl solutionctl export jetson_voice_assistant

# Deploy via the installed SenseCraft desktop app (headless):
uv run --package sensecraft-solutionctl solutionctl deploy jetson_voice_assistant --connection '{...}'
```

`solutionctl` auto-locates the engine binary: `$SENSECRAFT_ENGINE_BIN` env → `~/.sensecraft/engine.json` handshake → platform-native discovery (macOS `mdfind`, Windows registry, Linux `dpkg`).

---

## Repository layout

| Path | What |
|------|------|
| `solutions/` | Solution packages — `solution.yaml`, bilingual `guide.md`/`description.md`, device configs, assets |
| `spec/` | Generated contract: JSON Schema + `CONTRACT.md` (field rules, `docker_deploy` derivation, guide syntax) |
| `packages/sensecraft-solution-spec/` | `guide.md` parser primitives — run from the clone via `uv run` |
| `packages/solutionctl/` | Offline validator + thin client to the engine binary — run from the clone via `uv run` |
| `skills/` | Authoring playbooks (copywriting, docker/firmware prep) |
| `scripts/` | CI boundary guard (`public-repo-guard.sh`) |

---

## Writing a solution

The fastest path is to let an AI agent drive it: open this repo in an agent (Claude Code auto-loads the skills) and ask it to use the **`author-solution`** skill — it reproduces the project, scaffolds the solution, validates, and helps you preview & submit. Non-developers / AEs have a step-by-step companion: **[the AE submission guide](docs/AE-提交指南.md)**.

Reference docs: [`spec/CONTRACT.md`](spec/CONTRACT.md) for field/syntax rules, `docker_deploy` view derivation, and `guide.md` Step/Target syntax; [`CONTRIBUTING.md`](CONTRIBUTING.md) for the authoring & PR workflow; AI agents: [`AGENTS.md`](AGENTS.md) (**Part F** is the author-and-submit flow).

## Notes

- Solution `docker-compose` files use **demo default credentials** (e.g. local InfluxDB tokens). These are not secrets; change them for production.
- Container images are pulled from public registries.
- The provisioning engine (deployers, device communication, desktop app) is closed-source. Only the content + contract + tooling layer in this repo is Apache-2.0.

## License

[Apache-2.0](LICENSE).
