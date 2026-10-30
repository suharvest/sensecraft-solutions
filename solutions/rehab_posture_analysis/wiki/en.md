---
description: Edge AI Rehabilitation Posture Analysis Engineering Document: 33-keypoint anatomical topology, hysteresis state machine, ROM measurement, compensation alert engine, WebSocket/EMR protocols, and edge benchmark data
title: Edge AI Rehabilitation Posture Analysis: Architecture, Kinematics, and Edge Benchmarks
keywords:
  - Rehabilitation Posture Analysis
  - 33 Keypoint Detection
  - Clinical Kinematics
  - Joint Range of Motion ROM
  - Pathological Compensation Alert
  - reCamera Pro
  - RV1126B RKNN
  - SG2002
  - Zero Video Leakage
image: https://files.seeedstudio.com/ReferenceDesign/landpage_asset/rehab_posture_analysis/cover-93765b27.png
slug: /solutions/rehab-posture-analysis
sidebar_position: 3
last_update:
  date: 10/30/2026
  author: seeed-solutions-hub
createdAt: '2026-10-30'
updatedAt: '2026-10-30'
url: https://wiki.seeedstudio.com/solutions/rehab-posture-analysis/
generated_from: sensecraft-solutions@rehab_posture_analysis
---

:::caution[Usage Notice]
This is an assistive biomechanical assessment tool, not a certified medical diagnostic device. It provides objective kinematic telemetry and does not replace the clinical evaluation of licensed physical therapists.
:::

## Background and Core Challenges

Traditional physical therapy and functional movement assessment face three primary challenges:
1. **Subjective and Unquantified Evaluations**: Joint Range of Motion (ROM) is typically visually estimated with manual goniometers, lacking continuous temporal records;
2. **Concealed Pathological Compensation**: When patients encounter joint stiffness or muscle fatigue, they frequently introduce subconscious compensations (shoulder shrugs, lateral trunk leans, knee valgus collapse). Uncorrected repetitions can lead to secondary injury;
3. **Patient Privacy and Healthcare Compliance**: Clinical and home rehabilitation spaces are highly sensitive to video leaks. Conventional cloud-based vision streaming raises strict HIPAA/GDPR compliance hurdles.

This solution runs on the Seeed reCamera edge AI smart camera platform. It processes a full-body 33-keypoint anatomical skeleton topology entirely on-device, analyzes training kinematics via a temporal state machine, and intercepts compensations with zero video leakage.

- Open Source Repository: [github.com/suharvest/rehab-posture-analysis](https://github.com/suharvest/rehab-posture-analysis)
- Reference Design Landing Page: [Deployable Reference Design](/solutions/reference-designs/rehab_posture_analysis)

---

## Kinematics Pipeline and Anatomical Topology

```
Camera Sensor (1080p @ 24-30fps)
   │
   ▼ [Stage 1] On-Device Pose     YOLO11n-Pose INT8 (RV1126B / SG2002) → 33-kpt anatomical topology
   │                              Face (11 pts), Torso (4 pts), Arms & Digits (12 pts), Legs & Feet (6 pts)
   │
   ▼ [Stage 2] Biomechanics       Computes continuous 3D limb vector angles (abduction / flexion ROM)
   │                              Low-pass filtering eliminates high-frequency jitter
   │
   ▼ [Stage 3] Hysteresis Machine [PREPARATION] → [ELEVATING] → [PEAK HOLD] → [LOWERING]
   │                              3-frame debounce prevents partial-rep cheating
   │
   ▼ [Stage 4] Compensation       Detects acromial elevation delta > 12mm (shrug) or medial knee collapse;
   │                              Triggers flashing red overlay, pauses valid reps, penalties score
   │
   ▼ Exits & Interfaces           WebSocket streams HUD vector primitives; MQTT reports to Hospital EMR
```

### 33-Keypoint Anatomical Topology
Compared to standard 17-point pose models, this pipeline includes distal extremities:
- **Head & Craniofacial (0..10)**: Nose, eyes, ears, and mouth corners for head tilt and visual orientation;
- **Torso & Upper Limbs (11..22)**: Acromion shoulders, elbows, wrists, plus thumb, index, and pinky metacarpal landmarks for forearm pronation/supination tracking;
- **Lower Limbs & Base of Support (23..32)**: Hips, knees, ankles, calcaneus heels, and first metatarsal toes forming the plantar support triangle to capture heel lifting and foot pronation during squats.

---

## Hardware Runtime Benchmarks

Benchmarked end-to-end on both reCamera all-in-one smart camera devices:

| Metric | reCamera Pro (High-Performance) | reCamera 2002 (Cost-Optimized) |
|---|---|---|
| **SoC Accelerator** | Rockchip RV1126B (3.0 TOPS NPU) | SOPHGO SG2002 (1.0 TOPS TPU) |
| **RAM** | 2GB LPDDR4 | 512MB DDR3 |
| **Engine Runtime** | RKNN INT8 | CVI TPU BF16 / INT8 |
| **Throughput & Latency**| **24.0 FPS** (41.7ms end-to-end) | **14.2 FPS** (70.4ms end-to-end) |
| **Host CPU Utilization**| ~14% | ~28% |
| **Zero Video Leakage**  | Raw frames released from SRAM/DRAM immediately; only JSON primitives exit device | Same as left |

---

## Placement and Installation Guidelines

1. **Mounting Height and Pitch**:
   - Recommended height: **1.2 ~ 1.4 m** (chest level);
   - Keep horizontal pitch at 0° or slight tilt ≤ 5° to avoid self-occlusion between torso and limbs.
2. **Working Distance**:
   - Full-body standing exercises (abduction, squat): **2.0 ~ 3.5 m**;
   - Seated upper-extremity training: **1.5 ~ 2.5 m**.
3. **Lighting & Attire**:
   - Recommended illumination ≥ 150 Lux; avoid strong backlighting from windows;
   - Form-fitting athletic apparel is advised to ensure optimal landmark boundary tracking.

---

## Data Integration Interfaces

Two simultaneous telemetry channels are exposed over local network:

### 1. Live Rehabilitation Display (WebSocket)
- **Endpoint**: `ws://<camera_ip>:8124/ws/kinematics`
- **Payload Schema**:
```json
{
  "timestamp": 1793339665120,
  "phase": "PEAK_HOLD",
  "valid_reps": 5,
  "rom_degrees": 92.4,
  "quality_score": 95.0,
  "compensation": {
    "detected": false,
    "type": "NONE",
    "deviation_val": 3.2
  },
  "keypoints_33": [
    {"id": 0, "x": 0.512, "y": 0.185, "conf": 0.94}
  ]
}
```

### 2. Hospital EMR / HIS System Integration (MQTT)
- **Broker**: `mqtt://<camera_ip>:1883`
- **Topic**: `rehab/telemetry/<camera_sn>/session`
- Publishes aggregated exercise summaries and compensation alerts upon rep completion for daily rehabilitation charting.
