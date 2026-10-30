---
description: Aquaculture crayfish behavior and fighting recognition engineering documentation - 4-stage funnel pipeline, 8-frame mosaic temporal classifier, runtime matrix, MQTT/WS schemas, and field benchmark numbers
title: Aquaculture Crayfish Behavior & Fighting Recognition Engineering Guide
keywords:
  - crayfish behavior recognition
  - aquaculture edge AI
  - Cherax quadricarinatus
  - reCamera Pro
  - SG2002 cvimodel
  - temporal classifier
  - YOLO11
  - cannibalism alert
  - MQTT
image: https://files.seeedstudio.com/Solution/crayfish/cover.svg
slug: /solutions/crayfish-behavior-recognition
sidebar_position: 2
last_update:
  date: 10/30/2026
  author: seeed-solutions-hub
createdAt: '2026-10-30'
updatedAt: '2026-10-30'
url: https://wiki.seeedstudio.com/solutions/crayfish-behavior-recognition/
generated_from: sensecraft-solutions@crayfish_behavior_recognition
---

## Overview

In commercial recirculating aquaculture systems (RAS), intra-species aggression in redclaw crayfish (*Cherax quadricarinatus*) causes claw amputations and cannibalism on vulnerable soft-shell molting individuals. 

This engineering design provides an autonomous 4-stage funnel processing pipeline running strictly on-device inside Seeed reCamera smart edge cameras, delivering real-time aggression detection, molting risk mitigation, and sex distribution tracking without video leakage.

- Repository: [github.com/suharvest/crayfish-fight](https://github.com/suharvest/crayfish-fight)
- Landing Page: [Reference Design Landing Page](/solutions/reference-designs/crayfish_behavior_recognition)

---

## 4-Stage Funnel Architecture

```
Camera Stream (1080p @ 10-15fps)
   │
   ▼ [Stage 1] Object Detection   YOLO11n (640x640) → Crayfish Bounding Boxes + ByteTrack
   │
   ▼ [Stage 2] Proximity Trigger  Pairwise center distance < 1.1x body length for >= 3 frames
   │                              Extract interaction crop with +20% margin
   │
   ▼ [Stage 3] Coarse Filter      YOLO11n-cls (224x224) binary screening
   │
   ▼ [Stage 4] Temporal Confirm   YOLO11n-cls (448x448 mosaic), 8-frame temporal interaction grid
   │                              Rejects 2D perspective overlap optical illusions
   │
   ▼ Event Dispatch               Emits state transitions (start / change / end) via MQTT & WS
```

### Parallel Sex Classifier
Over the first 10 frames of newly tracked individuals, cropped morphology is classified with YOLO11n-cls (128x128) voting, achieving **82.0% Top-1 accuracy** to track male-to-female ratios automatically.

---

## Model Benchmark Numbers

Measured on real-tank validation datasets with 15% defocus blur and water surface refraction:

| Model | Input Shape | Task | Measured Metric | Runtimes |
|---|---|---|---|---|
| `det_v2_n` | 640×640×3 | Crayfish Detection | **mAP50: 0.950**<br>(Precision: 0.914, Recall: 0.880) | RV1126B RKNN INT8<br>SG2002 TPU BF16 |
| `behavior_temporal` | 448×448×3 | 8-Frame Temporal Verification | **Recall: 0.950**<br>Precision: 0.905 | RV1126B RKNN INT8 |
| `behavior_cls` | 224×224×3 | Single-Frame Coarse Screen | Recall: 0.775<br>Precision: 0.816 | RV1126B RKNN INT8<br>SG2002 TPU BF16 |
| `sex_cls` | 128×128×3 | Sex Classification | **Top-1: 0.820** | RV1126B RKNN INT8<br>SG2002 TPU BF16 |

---

## Hardware Runtime Matrix

| Hardware | Processor | RAM | Stack | Full Pipeline Throughput |
|---|---|---|---|---|
| **reCamera Pro** | RV1126B · 3 TOPS NPU | 2GB LPDDR4 | Linux 5.10 + RKNN Python + RGA | **10-15 FPS** (Autonomous 4-stage closure) |
| **reCamera 2002** | SG2002 · 1 TOPS TPU | 512MB DDR3 | BusyBox + Native C++ CVI TPU | **12-15 FPS** (Detection + Coarse alert) |

---

## Telemetry Payload Schemas

### 1. MQTT Event Topic (`crayfish/behavior/event`)
Emitted strictly upon state transitions (`start`, `change`, `end`):
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

### 2. MQTT Telemetry Stream (`crayfish/detection`)
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
