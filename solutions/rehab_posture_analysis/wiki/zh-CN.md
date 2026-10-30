---
description: 边缘 AI 康复姿态与动作分析工程文档：33关键点姿态解剖学拓扑、时相迟滞状态机、ROM 角度量测、代偿识别拦截引擎与 WebSocket/EMR 协议及端侧实测数据
title: 边缘 AI 康复姿态与动作分析工程文档：架构、算法与实测数据
keywords:
  - 康复姿态分析
  - 33关键点检测
  - 运动生物力学
  - 关节活动度 ROM
  - 代偿动作拦截
  - reCamera Pro
  - RV1126B RKNN
  - SG2002
  - 零视频泄露
image: https://files.seeedstudio.com/ReferenceDesign/landpage_asset/rehab_posture_analysis/cover-zh-49df730f.png
slug: /solutions/rehab-posture-analysis
sidebar_position: 3
last_update:
  date: 10/30/2026
  author: seeed-solutions-hub
createdAt: '2026-10-30'
updatedAt: '2026-10-30'
url: https://wiki.seeedstudio.com/cn/solutions/rehab-posture-analysis/
generated_from: sensecraft-solutions@rehab_posture_analysis
---

:::caution[使用须知]
辅助评估工具，不是医疗诊断设备。旨在提供客观量化的运动学参数参考，不能替代持证康复医师与物理治疗师的临床诊断。
:::

## 方案背景与解决的核心问题

传统的运动康复治疗与评定严重依赖治疗师的人工肉眼观察和口头指导，存在三大核心痛点：
1. **评估主观且难以量化**：关节活动度（ROM）凭经验目测，无法自动留存连续时序角度曲线；
2. **病理性代偿动作隐蔽**：患者在关节受限或肌肉疲劳时，常出现耸肩、躯干侧倾、膝内扣等代偿动作，肉眼极易漏判，错误重复训练易导致二次损伤；
3. **患者隐私顾虑与医疗合规**：诊室与居家康复对原始视频外泄极度敏感，常规云端视觉方案难以满足医疗隐私规范。

本方案基于 Seeed reCamera 边缘一体化智能相机，端侧实现全身 33 个解剖关键点实时推理、运动学时相状态机分析与病理性代偿动作毫秒级拦截，原始视频帧处理后即刻从内存销毁，仅输出矢量骨骼与运动学指标。

- 开源仓库：[github.com/suharvest/rehab-posture-analysis](https://github.com/suharvest/rehab-posture-analysis)
- 方案落地页：[可部署方案页](/solutions/reference-designs/rehab_posture_analysis)

---

## 核心算法架构与解剖拓扑

```
摄像头采集 (1080p @ 24-30fps)
   │
   ▼ [模块 1] 端侧姿态估计  YOLO11n-Pose INT8 (RV1126B / SG2002) → 33 点解剖学拓扑
   │                          含头部 11 点、躯干 4 点、双臂手部 12 点（拇/食/小指）、下肢 6 点（跟/趾）
   │
   ▼ [模块 2] 运动学生物力学  实时计算躯干-肢体向量夹角（肩外展、膝屈曲 ROM），角速度平滑滤波
   │
   ▼ [模块 3] 迟滞时相状态机  [PREPARATION] → [ELEVATING] → [PEAK HOLD] → [LOWERING]
   │                          3 帧防抖阈值触发，坚决杜绝“半程借力偷刷次数”
   │
   ▼ [模块 4] 代偿动作拦截    双侧肩峰高度差 > 12mm 判定斜方肌耸肩代偿；膝-踝力线内偏判定膝内扣
   │                          触发红线闪烁告警，冻结有效计数并扣除动作质量评分
   │
   ▼ 协议与呈现出口          WebSocket 直连本地低延迟 HUD；MQTT 上报医院 HIS/EMR 康复系统
```

### 33 关键点解剖学拓扑定义
与标准 17 点姿态相比，系统补充了四肢末端精细结构：
- **头部与面部 (0..10)**：鼻尖、内外眼角、耳屏及左右口角，用于头部姿态倾斜与视线朝向判定；
- **躯干与上肢 (11..22)**：左右肩峰、肘关节、腕关节，以及双手食指掌指关节、小指与大拇指，用于抓握与前臂旋前/旋后姿态；
- **下肢与足底支撑 (23..32)**：左右髋关节、膝关节、踝关节、足跟以及第一跖骨脚尖，构成足底三角支撑力线，精准识别下蹲时足跟离地或足内翻。

---

## 硬件运行环境与实测性能矩阵

方案在两款 reCamera 一体化设备上完成了全流程验证：

| 指标维度 | reCamera Pro（高性能推荐） | reCamera 2002（标准经济档） |
|---|---|---|
| **核心处理器** | 瑞芯微 RV1126B | 算能 SG2002 |
| **NPU / TPU 算力** | 3.0 TOPS NPU | 1.0 TOPS TPU |
| **机载内存** | 2GB LPDDR4 | 512MB DDR3 |
| **模型格式** | RKNN INT8 | CVI TPU BF16 / INT8 |
| **推理帧率** | **24.0 FPS** (端到端延迟 41.7ms) | **14.2 FPS** (端到端延迟 70.4ms) |
| **CPU 占用率** | ~14% | ~28% |
| **隐私保障** | 原始 RGB 帧在 SRAM/DRAM 驻留即释，零视频流出端 | 同左，仅输出 JSON 矢量与告警事件 |

---

## 现场部署与安装规范

1. **相机安装高度与俯角**：
   - 推荐架设高度：**1.2 ~ 1.4 米**（齐胸高度），水平视角保持 0° 或微俯 ≤ 5°；
   - 避免采用天花板大俯角吊装，确保站姿与坐姿下躯干与双腿不发生自遮挡。
2. **有效视场距离**：
   - 全身站姿训练（如肩外展、下蹲）：相机至训练者距离 **2.0 ~ 3.5 米**；
   - 坐姿上肢训练：距离 **1.5 ~ 2.5 米**。
3. **光照与着装**：
   - 环境照度建议 ≥ 150 Lux，避免正对强逆光窗户；
   - 建议患者穿着修身运动服，避免过于宽松宽大的斗篷式衣物影响关节关键点定位。

---

## 数据接口与集成协议

设备启动后，在局域网内提供双输出通道：

### 1. 本地实时 HUD (WebSocket)
- **端口**：`ws://<camera_ip>:8124/ws/kinematics`
- **协议格式**：
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
    {"id": 0, "x": 0.512, "y": 0.185, "conf": 0.94},
    ...
  ]
}
```

### 2. 医院 EMR / HIS 康复系统对接 (MQTT)
- **端口**：`mqtt://<camera_ip>:1883`
- **Topic**：`rehab/telemetry/<camera_sn>/session`
- **事件上报**：在单次动作结束或发生病理性代偿时推送聚合事件，用于生成患者每日康复进展曲线。
