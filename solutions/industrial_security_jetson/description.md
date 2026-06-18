## What This Solution Does

Industrial sites need eyes on restricted zones around the clock — but cloud-based AI surveillance means video leaves the premises, latency spikes, and a dropped network connection blinds the whole system. This solution runs AI person detection and rule-checking entirely on a reComputer Industrial (Jetson Orin) at the edge: video never leaves the local network, alerts fire in under a second, and it keeps working when the internet doesn't.

## Core Benefits

| Benefit | Details |
|---------|---------|
| Data stays on-site | Video frames are processed locally on the reComputer — nothing is uploaded, no cloud account, no data egress |
| Sub-second alerts | The Jetson GPU analyzes every frame at 15-30 FPS, intrusions are flagged within ~1 second |
| Flexible safety rules | Draw restricted zones, virtual fence lines, and dwell-time triggers directly in the browser — no code |
| Works offline | Once deployed, the system runs without internet — perfect for remote sites, factories, mines |
| Standard cameras | Plug in any RTSP IP camera (Hikvision, Dahua, ONVIF generic) — no proprietary hardware lock-in |
| Multi-camera support | Monitor multiple areas simultaneously with independent processing pipelines sharing one detection model |
| Event persistence | SQLite database stores all events with date filtering — restart without losing history |

## Use Cases

| Scenario | What It Catches |
|----------|----------------|
| Factory floor safety zones | Workers entering machinery exclusion areas during operation |
| Warehouse restricted areas | After-hours intrusion into chemical / high-value storage zones |
| Construction site perimeters | Unauthorized people crossing fence lines or entering excavation pits |
| Mining hazard zones | Personnel entering blast areas or unstable ground |
| Substation / utility yards | Trespassing in high-voltage equipment areas |

## What You Need

### Hardware

| Device | Purpose | Required |
|--------|---------|----------|
| reComputer Industrial (Jetson Orin NX / Nano) | Runs the detection model with Jetson GPU acceleration | Yes |
| RTSP IP camera | Provides the live video feed (Hikvision, Dahua, or any ONVIF-compatible) | Yes |
| Local network switch / PoE switch | Connects the Jetson and the camera | Yes |

### Software

- Jetson with **JetPack 6.x** (L4T 36.x) flashed
- Docker + NVIDIA Container Runtime (pre-installed on Seeed reComputer Industrial)
- SSH access from your computer to the Jetson

### Detection Models

| Model | Framework | Precision | Performance |
|-------|-----------|-----------|-------------|
| YOLO26n | Ultralytics (NMS-free) | FP16 TensorRT | ~268 QPS, ~3.7ms latency |
| YOLOv8n | Ultralytics | FP16 TensorRT | Real-time inference |
| YOLOv5n | Ultralytics | FP16 TensorRT | Lightweight option |

> The first run automatically builds a Jetson GPU-optimized TensorRT engine from the ONNX model and caches it for subsequent restarts.

### Notes Before You Deploy

- The first deployment pulls a ~3-5 GB Docker image — keep an eye on disk space
- The first run builds a Jetson GPU-optimized detection engine (1-2 minutes) and caches it for subsequent restarts
- Test your camera RTSP URL with VLC or `ffprobe` before deploying — most issues come from a wrong URL
- One Jetson handles multiple cameras in this configuration — each camera has an independent processing pipeline

## Key Features

### Multi-Camera Management

- **Simultaneous RTSP/USB input** — connect multiple cameras with independent processing pipelines
- **Camera auto-discovery** — automatically scan for RTSP cameras on the subnet
- **Shared detection model** — all cameras share one TensorRT engine for efficient GPU utilization
- **Per-camera configuration** — each camera has independent zones, lines, and rules

### TensorRT FP16 Acceleration

- **YOLO26n support** — latest Ultralytics model with NMS-free end-to-end inference
- **GPU hardware decoding** — GStreamer NVDEC for RTSP streams with near-zero CPU overhead
- **Optimized for Jetson** — tested on reComputer Industrial J4012 (Orin NX 16GB) at 30+ FPS

### Interactive Web Dashboard

- **Real-time annotated video** — bounding boxes, zones, and fence lines overlaid on live feed
- **Browser-based zone drawing** — draw restricted zones and fence lines directly on the video
- **WebSocket streaming** — low-latency video delivery to the browser
- **Adaptive grid layout** — automatically adjusts to multi-camera setups
- **HDMI fullscreen mode** — press **F** key to toggle fullscreen display

### Event Persistence & Tracking

- **SQLite database** — events stored persistently, survive restarts
- **Centroid tracking** — track detected persons across frames
- **Date filtering** — query events by date for historical review
- **Auto-cleanup** — automatically removes expired event data
