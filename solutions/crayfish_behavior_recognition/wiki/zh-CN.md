---
description: 水产养殖高密度水槽螯虾打斗与行为识别工程文档：4级漏斗流水线、8帧时序拼图网络、模型与运行时矩阵、MQTT/WS 输出协议及现场实测数据
title: 水产螯虾打斗与行为识别工程文档：架构、模型与实测数据
keywords:
  - 螯虾打斗识别
  - 水产养殖 AI
  - 澳洲淡水龙虾
  - reCamera Pro
  - SG2002 cvimodel
  - 时序行为分类
  - YOLO11
  - 残食预警
  - MQTT
image: https://files.seeedstudio.com/Solution/crayfish/cover.svg
slug: /solutions/crayfish-behavior-recognition
sidebar_position: 2
last_update:
  date: 10/30/2026
  author: seeed-solutions-hub
createdAt: '2026-10-30'
updatedAt: '2026-10-30'
url: https://wiki.seeedstudio.com/cn/solutions/crayfish-behavior-recognition/
generated_from: sensecraft-solutions@crayfish_behavior_recognition
---

## 方案背景与解决的核心问题

高密度水产养殖（如红螯螯虾 *Cherax quadricarinatus*、澳洲淡水龙虾、罗氏沼虾）环境下，个体的攻击性打斗直接导致大螯断肢，严重降低出塘品质；尤其在蜕壳期，软壳脆弱个体极易遭受同伴残食（Cannibalism）。常规理化传感器仅能反映水质，无法捕捉个体间的互动动态。

本工程方案采用 4 级漏斗过滤架构，全部在 Seeed reCamera 边缘相机本地运行，实现水槽打斗识别、脱壳期残食预警与公母性别统计。

- 开源仓库：[github.com/suharvest/crayfish-fight](https://github.com/suharvest/crayfish-fight)
- 方案落地页：[可部署方案页](/solutions/reference-designs/crayfish_behavior_recognition)

---

## 4 级漏斗算法架构

```
摄像头采集 (1080p @ 10-15fps)
   │
   ▼ [级 1] 目标检测   YOLO11n (640×640) → 螯虾 Bounding Box + ByteTrack 多目标跟踪
   │
   ▼ [级 2] 靠近触发   两虾中心距 < 1.1×体长 或 IoU > 0，持续 ≥ 3 帧
   │                    截取交互区域并外扩 20% margin 作为 ROI
   │
   ▼ [级 3] 单帧粗筛   YOLO11n-cls (224×224) 极速二分类，快速过滤普通游动
   │
   ▼ [级 4] 时序确认   YOLO11n-cls (448×448 拼图)，将 8 帧交互 ROI 拼图输入卷积网
   │                    彻底消除侧拍视角下的 2D 透视重叠伪接触
   │
   ▼ 事件输出         状态机仅在 start / change / end 状态切换时上报 MQTT 与 WebSocket
```

### 并行分支：性别分类器
在新生成的 Track ID 前 10 帧中，截取单只虾大螯与腹部形态，输入 YOLO11n-cls（128×128）进行多帧投票，输出 `male` / `female` / `unknown`，Top-1 准确率达 **82.0%**。

---

## 模型与现场验证集实测数据

数据来源：基于天津水产学院及养殖水槽现场 2,000+ 帧真实采集标注验证集（包含 15% 虚焦模糊与水面反光增广）。

| 模型 | 输入尺寸 | 目标任务 | 实测指标 | 部署运行时 |
|---|---|---|---|---|
| `det_v2_n` | 640×640×3 | 螯虾个体检测 | **mAP50: 0.950**<br>(Precision: 0.914, Recall: 0.880) | RV1126B RKNN INT8<br>SG2002 TPU BF16 |
| `behavior_temporal` | 448×448×3 | 8 帧时序打斗确认 | **Recall: 0.950**<br>Precision: 0.905 | RV1126B RKNN INT8 |
| `behavior_cls` | 224×224×3 | 单帧行为粗筛 | Recall: 0.775<br>Precision: 0.816 | RV1126B RKNN INT8<br>SG2002 TPU BF16 |
| `sex_cls` | 128×128×3 | 公母性别判定 | **Top-1: 0.820** | RV1126B RKNN INT8<br>SG2002 TPU BF16 |

---

## 硬件运行环境矩阵

| 硬件平台 | 处理器与算力 | 内存 | 运行栈 | 全流水线实测表现 |
|---|---|---|---|---|
| **reCamera Pro** | RV1126B · 3 TOPS NPU | 2GB LPDDR4 | Linux 5.10 + RKNN Python + RGA | **10~15 FPS**（4 级漏斗全闭环） |
| **reCamera 2002** | SG2002 · 1 TOPS TPU | 512MB DDR3 | BusyBox + 原生 C++ CVI TPU | **12~15 FPS**（检测 + 粗筛预警） |

---

## 数据输出接口协议

### 1. MQTT 状态切换告警 (`crayfish/behavior/event`)
仅在状态发生切换时发出，避免连续多帧重复打扰：
```json
{
  "timestamp": 1730286000.124,
  "event_id": "evt_20261030_0042",
  "phase": "start",
  "behavior": "fight",
  "confidence": 0.95,
  "duration_sec": 3.2,
  "pair": [
    {"track_id": 1, "sex": "male", "sex_conf": 0.88},
    {"track_id": 4, "sex": "female", "sex_conf": 0.91}
  ],
  "roi_box": [320, 240, 560, 480],
  "capture_url": "http://192.168.3.53:8124/captures/evt_0042.jpg"
}
```

### 2. MQTT 实时检测广播 (`crayfish/detection`)
用于养殖监控大屏绘制当前水槽个体分布：
```json
{
  "timestamp": 1730286000.124,
  "count": 6,
  "objects": [
    {"track_id": 1, "box": [0.24, 0.35, 0.41, 0.52], "score": 0.93, "sex": "male"},
    {"track_id": 2, "box": [0.55, 0.12, 0.68, 0.28], "score": 0.89, "sex": "unknown"}
  ]
}
```
