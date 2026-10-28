# Eldercare Safety Monitor

An edge multimodal eldercare safety monitoring system running directly on **reCamera Pro** (Rockchip RV1126B, 3.0 TOPS NPU). 

The system seamlessly combines computer vision pose tracking and continuous offline automatic speech recognition (ASR) to detect falls and capture emergency voice calls simultaneously within a single embedded device. All computations are conducted entirely on-device: **video frames and audio chunks never leave local volatile memory**, preserving senior privacy while providing millisecond-level alerting.

---

## What This Solution Does

- **Traditional Motion Sensors & Radars**: Frequently triggered by room activities, pets, or robot vacuums, and unable to distinguish lying on the floor from sitting or tying shoelaces.
- **Cloud-Connected Cameras**: Transmitting continuous 24/7 video streams to third-party cloud services raises severe privacy resistance, especially in bedrooms and living rooms, and fails entirely during broadband outages.
- **Multimodal Edge Collaboration**:
  - **Vision Channel**: High-precision estimation of 17 human body keypoints. Analyzes vertical torso velocity, spine angle (>65°), and immobility duration.
  - **Acoustic Channel**: Integrated microphone array running Silero VAD and SenseVoice-Small ASR, continuously matching emergency keywords ("Help", "救命", "摔倒了", "Emergency").
  - **Fused Decision**: A visual fall accompanied by a distress call triggers immediate maximum-priority alert dispatch; if visual line-of-sight is obstructed by furniture, acoustic help calls trigger alerts independently.

---

## Key Benefits & Technical Specifications

### 1. Skeleton Pose & Fall Detection (YOLO11n-Pose)
- **Architecture**: YOLO11n-Pose (quantized INT8 on Rockchip NPU), tracking 17 COCO body joints.
- **State Machine Analysis**:
  - **Upright / Normal Activity** (`upright`): Spine angle from vertical < 45°.
  - **Rapid Descent** (`fall_event`): Sudden acceleration downwards; torso angle surges beyond 65°.
  - **Confirmed Fall** (`fallen`): Persistent immobility on the floor exceeding **3 seconds** triggers an irrevocable alarm.
- **Inference Latency**: ~**50 ms** per frame on RV1126B NPU, sustaining **15 - 20 FPS** throughput.

### 2. Continuous Offline Speech Recognition (SenseVoice ASR)
- **Acoustic Front-end**: Silero VAD (ONNX) for real-time speech activity detection; zero NPU load during silence.
- **ASR Back-end**: SenseVoice-Small T172 scaled hybrid-precision single model (RKNN), 172-frame window with 32-frame hop.
- **Accuracy & Speed**:
  - **Chinese CER**: **1.8%** (short segments) / **2.5%** (long segments)
  - **English WER**: **3.9%** (short segments) / **2.8%** (long segments)
  - **Real-Time Factor (RTF)**: **≤ 0.11** (decoding takes only 1/10th of spoken audio length)
  - **Distress Word Lexicon**: "Help", "Emergency", "救命", "摔倒了", "帮帮我", "快来人".
- **Zero Cloud Reliance**: Completely independent of cloud APIs, operating reliably during offline or restricted network environments.

### 3. Concurrent System Resource Footprint
- **CPU Utilization**: Average **~45%** on quad-core Cortex-A7 @ 1.5GHz.
- **Memory Safety Floor**: `MemAvailable` sustained at **> 500 MiB**.
- **Typical Power Draw**: **~3.5 W** under continuous dual-model execution.

---

## Interfaces & Communication

### 1. Structured MQTT Event Stream
Publishes structured JSON alerts to local MQTT brokers (such as Home Assistant, Node-RED, or alarm gateways).

- **Topic**: `<device_name>/eldercare-monitor/events`
- **Payload Schema**:
```json
{
  "timestamp": 1729676400.450,
  "device_id": "living_room_cam",
  "fall_alert": {
    "detected": true,
    "state": "fallen",
    "person_id": 1,
    "confidence": 0.94,
    "torso_angle": 78.5,
    "immobility_sec": 3.2
  },
  "voice_alert": {
    "detected": true,
    "text": "Help, I fell down!",
    "keyword": "Help",
    "confidence": 0.98,
    "duration_sec": 1.2
  }
}
```

### 2. Live WebSocket Feed
- **Endpoint**: `ws://<device-ip>:8123/ws/inference/results`
- **Payload**: Binary protobuf stream carrying 17 keypoint coordinates, object bounding boxes, and track IDs for local browser overlay rendering.

---

## Suitable Scenarios

- **Home Eldercare & Living Spaces**: Bedrooms, living rooms, and private quarters where continuous video streaming to the cloud is unacceptable.
- **Senior Care Facilities & Assisted Living**: Corridors, community activity rooms, and blind spots requiring automated real-time alerts.
- **Autonomous Emergency Response**: Local integration with Home Assistant or on-premise alarm systems for instantaneous notification.

---

## Measured Benchmarks & Usage Notes

1. **Mounting Height**: **2.2 to 2.5 meters** above the floor on a corner or wall mount.
2. **Tilt Angle**: Downwards tilt of **15° to 25°**. Avoid 90° top-down placement (which compresses vertical joint distance and hinders pose classification).
3. **Room Coverage**: Optimal coverage for rooms up to **4m × 5m** (e.g. living rooms, bedrooms).
4. **Acoustic Environment**: Position away from continuous high-power noise sources (e.g. direct airflow from air conditioners).
