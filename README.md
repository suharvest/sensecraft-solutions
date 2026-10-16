[English](README_en.md) | **中文**

<p align="center">
  <img src="media/logo.png" alt="SenseCraft Solutions" width="120" />
</p>

# SenseCraft Solutions

[![CI](https://github.com/suharvest/sensecraft-solutions/actions/workflows/guard.yml/badge.svg)](https://github.com/suharvest/sensecraft-solutions/actions/workflows/guard.yml)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

**面向 NVIDIA Jetson、RK3576/RK3588 与 Raspberry Pi 的 18+ 个开箱即用边缘 AI 方案** —— 还附带用来创作和校验你自己方案的开源工具链。

<p align="center">
  <img src="media/solution_demo.gif" alt="SenseCraft Solutions demo" width="720" />
</p>

离线语音 AI、计算机视觉、智慧零售、机器人等方案，均可直接从 [SenseCraft 桌面应用](https://www.seeed.cc/category/reference-designs) 或通过 `solutionctl` 命令行部署，无需依赖云端。

---

## 方案列表

### 完整落地方案（Reference Designs）

| 方案名称 | 支持硬件 | 行业场景 |
|----------|----------|----------|
| [车牌识别与道闸联动](solutions/edge-anpr-plate-recognition/) | Jetson Orin · RK3588 · RK3576 | 智慧交通 / 车牌道闸 |
| [停车场出入口车辆进出计数](solutions/parking-entry-exit-counting/) | Jetson Orin · RK3588 · RK3576 | 智慧停车 / 车辆进出 |
| [停车场车位占用检测与空闲引导](solutions/parking-space-occupancy-detection/) | Jetson Orin · RK3588 · RK3576 | 智慧停车 / 车位占用 |
| [智能工牌私有化语音转写](solutions/smart-badge-voice-transcription/) | reComputer J40/J30 · RK3588 · RK3576 | 线下对话 / 语音转写质检 |
| [可打断对话式语音 AI](solutions/conversational_voice_ai/) | Jetson Orin · RK3576 · RK3588 | 语音交互 / 实时打断 |
| [零售对话采集与分析](solutions/retail_voice/) | reComputer RK3576 · reRouter CM4 | 智慧零售 / 语音分析 |
| [语音操作仓储管理系统](solutions/smart_warehouse/) | Jetson Orin · reComputer RK3576 | 智慧物流 / 语音出入库 |
| [Home Assistant 本地语音中枢](solutions/home-assistant-local-voice-hub/) | Raspberry Pi 5 · Jetson Orin NX | 全屋智能 / 本地语音联动 |
| [暖通自动化控制](solutions/smart_hvac_control/) | reComputer R11 · 工业边缘网关 | 楼宇自动化 / 暖通控制 |
| [多协议工业网关](solutions/multi_protocol_gateway/) | reComputer R11 · 工业边缘网关 | 工业物联网 / 协议转换 |
| [边缘安全防护与越界预警](solutions/edge_security/) | Jetson Orin · RK3588 · Hailo | 智能安防 / 越界与徘徊 |
| [边缘端跌倒检测](solutions/fall_detection/) | reCamera · Jetson Orin · Hailo | 康养看护 / 跌倒告警 |
| [智慧零售人流热力图](solutions/recamera_heatmap_grafana/) | reCamera · 边缘计算盒子 | 智慧零售 / 客流看板 |
| [无人门店人脸门禁](solutions/unmanned_store_access/) | reCamera D1001 · 边缘主机 | 智慧零售 / 刷脸开门 |
| [超市商品图像识别](solutions/edge_retail_recognition/) | Jetson Orin · RK3588 | 智慧零售 / 货架商品 |
| [投放点垃圾分类](solutions/edge_waste_sorting/) | reCamera · RK3588 · Jetson Orin | 智慧环保 / 垃圾分类 |
| [表面缺陷质检](solutions/edge_inspection_surface/) | Jetson Orin · RK3588 | 工业制造 / 表面质检 |
| [装配质检：缺件与尺寸](solutions/edge_inspection_assembly/) | Jetson Orin · RK3588 | 工业制造 / 装配质检 |
| [农业环境监测](solutions/agri_env_monitor/) | SenseCAP LoRaWAN · 边缘网关 | 智慧农业 / 环境传感 |
| [园区级蓝牙信标定位系统](solutions/indoor_positioning_ble_lorawan/) | 追踪信标 · 边缘网关 | 物联网 / 室内外定位 |

### 技术与工具演示（Technical Demos）

| 演示项目 | 适用硬件 | 说明 |
|----------|----------|------|
| [Local Voice Service](solutions/jetson_voice_assistant/) | Jetson Orin · RK3576 · RK3588 · RPi | 本地离线语音服务（ASR + TTS，≤180ms） |
| [Plug & Play AI Camera](solutions/recamera_ecosystem/) | reCamera | 即插即用 AI 摄像头应用中心 |
| [AI Lab](solutions/ai_lab/) | Rockchip NPU | 瑞芯微边缘 AI 模型中心 |
| [Depth Anything v3](solutions/depth_anything_v3/) | Jetson | 单目深度估计 |
| [GPT OSS 20B](solutions/gpt_oss_20b/) | Jetson | 本地大模型推理 |
| [Gun Detection (Frigate)](solutions/gun_detection_frigate/) | Jetson | 视觉枪支检测演示 |
| [reCamera ONVIF Gateway](solutions/recamera_onvif_nvr/) | reCamera | ONVIF / RTSP 网关支持 |
| [reCamera Parking Monitor](solutions/recamera_parking_monitor/) | reCamera | 轻量停车位检测 |
| [Sheep Counter (LoRa)](solutions/recamera_sheep_counter_lora/) | reCamera + LoRa | 绵羊计数与无线回传 |
| [Reachy Claw Voice Robot](solutions/reachy_claw_voice_robot/) | Reachy Mini + Jetson | 桌面对话机器人 |
| [ReSpeaker Flex + SO-ARM100](solutions/respeaker_flex_soarm/) | ReSpeaker + ARM | 语音机械臂控制 |
| [OpenClaw Deploy](solutions/openclaw_deploy/) | Jetson | 龙虾机器人 AI 网关 |
| [reBot B601-DM](solutions/voice_rebot_arm/) | Jetson | 语音抓取机械臂 |
| [LeKiwi Robot](solutions/voice_robot_lekiwi/) | Jetson | 语音轮式机器人 |
| [SenseCAP PaaS MCP Bridge](solutions/sensecraft_data_mcp/) | 通用主机 | MCP 数据桥接 |
| [Smart Space Assistant](solutions/smart_space_assistant/) | Jetson | 空间 AI 对话大屏 |
| [Z-Image-Turbo](solutions/z_image_turbo/) | Jetson | Jetson 端侧生图 |

---

## 工作原理

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

每个方案都是一个自包含的目录：一份 `solution.yaml`（硬件目录、部署预设、双语元数据）、双语的 `guide.md` + `description.md`、Docker Compose 配置以及资源文件。引擎在部署前会根据 `spec/` 中发布的 JSON Schema 契约对方案进行校验。

`solutionctl` 是引擎面向无界面（headless）使用的命令行入口 —— 它定位已安装的二进制文件，并通过子进程 / 本地 REST 驱动它。

---

## 快速开始

```bash
# 安装依赖
uv sync

# 离线校验方案（无需引擎 / App）：
uv run --package sensecraft-solutionctl solutionctl validate solutions/jetson_voice_assistant

# 打包方案为可导入的 zip（用于在桌面应用中预览）：
uv run --package sensecraft-solutionctl solutionctl export jetson_voice_assistant

# 通过已安装的 SenseCraft 桌面应用部署（无界面）：
uv run --package sensecraft-solutionctl solutionctl deploy jetson_voice_assistant --connection '{...}'
```

`solutionctl` 会自动定位引擎二进制：先看 `$SENSECRAFT_ENGINE_BIN` 环境变量 → 再走 `~/.sensecraft/engine.json` 握手 → 最后按平台原生方式发现（macOS `mdfind`、Windows 注册表、Linux `dpkg`）。

---

## 仓库结构

| Path | 说明 |
|------|------|
| `solutions/` | 方案包 —— `solution.yaml`、双语 `guide.md`/`description.md`、设备配置、资源文件 |
| `spec/` | 生成的契约：JSON Schema + `CONTRACT.md`（字段规则、`docker_deploy` 派生、guide 语法） |
| `packages/sensecraft-solution-spec/` | `guide.md` 解析原语 —— 从 clone 中通过 `uv run` 运行 |
| `packages/solutionctl/` | 离线校验器 + 引擎二进制的轻量客户端 —— 从 clone 中通过 `uv run` 运行 |
| `skills/` | 创作手册（文案、docker/固件准备） |
| `scripts/` | CI 边界守卫（`public-repo-guard.sh`） |

---

## 编写方案

最快的方式是让 AI agent 来驱动：在 agent 中打开本仓库（Claude Code 会自动加载这些 skills），让它使用 **`author-solution`** skill —— 它会复现项目、搭建方案骨架、完成校验，并协助你预览与提交。非开发者 / AE 有一份手把手的配套指南：**[AE 提交指南](docs/AE-提交指南.md)**。内置的验证 / 部署类型不满足时，可用通用兜底（`http_debug` 调任意接口 / `web_dashboard` 打开任意页面）或在设备配置里用 `actions` 自定义检查，详见 `skills/author-solution`。需要一个**全新的交互形态**？可用插件原型化，或向维护者提需求 —— 见 [插件开发指南](docs/plugin-development.md)。

参考文档：[`spec/CONTRACT.md`](spec/CONTRACT.md) 讲字段/语法规则、`docker_deploy` 视图派生以及 `guide.md` 的 Step/Target 语法；[`CONTRIBUTING.md`](CONTRIBUTING.md) 讲创作与 PR 流程；AI agent 请看 [`AGENTS.md`](AGENTS.md)（**Part F** 是创作并提交的完整流程）。

## 须知

- 方案的 `docker-compose` 文件使用 **演示用默认凭据**（例如本地 InfluxDB token）。这些并非机密，生产环境请自行更换。
- 容器镜像均从公共 registry 拉取。
- 分发引擎（部署器、设备通信、桌面应用）是闭源的。本仓库中只有内容 + 契约 + 工具链这一层是 Apache-2.0。

## 许可证

[Apache-2.0](LICENSE)。
