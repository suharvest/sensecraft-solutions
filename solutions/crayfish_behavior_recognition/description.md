# Aquaculture Crayfish Behavior & Fighting Recognition

## Overview

In high-density commercial aquaculture (such as Australian redclaw crayfish *Cherax quadricarinatus* and giant freshwater prawns), intra-species aggression directly reduces survival rates and market yield. Territorial conflicts and competition for mates cause claw loss and limb damage. During molting cycles, soft-shell individuals are highly vulnerable to cannibalism. Conventional water quality sensors (DO, pH, temperature) only track chemical parameters and cannot detect real-time behavioral dynamics or aggression frequency.

The **Aquaculture Crayfish Behavior & Fighting Recognition Solution** provides an autonomous 4-stage funnel vision pipeline running entirely on Seeed reCamera smart edge cameras. Processing occurs locally on edge NPU/TPU hardware without sending video off-site. The camera publishes state-change alerts, event screenshots, and sex distribution statistics to farm management dashboards, mitigating cannibalism risks and feed waste.

---

## 4-Stage Funnel Pipeline Architecture

1. **Stage 1: High-Precision Detection (YOLO11n 640x640)**  
   Trained on indoor tank environments with water refraction and reflection, achieving **mAP50 of 0.950** (Precision 0.914, Recall 0.880) on field validation sets. Augmented with 15% defocus blur to separate touching individuals reliably.
2. **Stage 2: Geometric Proximity Trigger (Zero-Compute Rules)**  
   Evaluates pairwise center distance and bounding box IoU across tracked individuals. A crop ROI (+20% margin) is triggered only when distance drops below $1.1\times$ average body length for $\ge 3$ consecutive frames, reducing baseline inference computation by over 90%.
3. **Stage 3: Single-Frame Coarse Classifier (YOLO11n-cls 224x224)**  
   Instantly filters normal coexistence from aggressive interactions within the triggered ROI.
4. **Stage 4: 8-Frame Temporal Confirmation (YOLO11n-cls 448x448 Mosaic)**  
   Arranges 8 consecutive ROI crops into a grid mosaic for temporal confirmation, achieving **0.950 Recall and 0.905 Precision** on aggressive behaviors. Eliminates false-positive triggers caused by side-view 2D perspective overlaps.
5. **Parallel Branch: Sex Classification (YOLO11n-cls 128x128)**  
   Executes multi-frame voting over the initial 10 frames of newly tracked tracks, delivering **82.0% Top-1 accuracy** to track male-to-female ratios continuously.

---

## Hardware Benchmarks & Deployment

| Platform | Compute Architecture | Runtime Stack | Inference Throughput | Highlights |
|---|---|---|---|---|
| **reCamera Pro** | RV1126B · 3 TOPS NPU · 2GB RAM | Linux 5.10 + RKNN INT8 | Full pipeline @ 10-15 FPS | Complete autonomous 4-stage funnel closure, temporal verification, on-device sample capture |
| **reCamera 2002** | SG2002 · 1 TOPS TPU · 256/512MB RAM | BusyBox + CVI TPU BF16 | 640² detection @ 12-15 FPS | Ultra-compact PoE camera, native C++ daemon, dual-model cascade alert |

---

## Output Interfaces

- **MQTT Alert Topics**: `crayfish/behavior/event` emits state transitions (`start`, `change`, `end`); `crayfish/detection` broadcasts real-time tracked coordinates.
- **WebSocket Protocol**: Port 8124 delivers triggered interaction ROI crops with metadata.
- **RTSP Stream**: `rtsp://<ip>:8554/live0` with hardware OSD bounding boxes.
