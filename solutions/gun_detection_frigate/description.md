## What This Solution Does

Security cameras are everywhere, but someone still has to watch them 24/7 to spot a threat. This solution adds AI-powered gun detection to your existing cameras — the system watches every frame and alerts you the moment a gun appears.

## Core Value

| Benefit | Details |
|---------|---------|
| Instant detection | AI scans every video frame in real-time, no human fatigue |
| Works offline | Runs entirely on local hardware, no cloud dependency, no data leaves your network |
| Easy to set up | One-click deployment, starts with demo videos so you can see it working immediately |
| Hardware flexible | Choose NVIDIA Jetson (GPU) or reComputer R2000 + Hailo (NPU) based on your needs |

## Use Cases

| Scenario | How It Works |
|----------|-------------|
| School safety | Install IP cameras at entrances, get instant alerts when a gun is detected |
| Retail security | Monitor store cameras 24/7, automatically flag gun-related events with recordings |
| Office building | Add gun detection to existing CCTV system, integrate alerts via MQTT |
| Public venues | Real-time monitoring across multiple cameras with centralized web dashboard |

## Prerequisites

### Camera Connection

- IP cameras: Connect via RTSP URL (`rtsp://user:pass@ip/stream`)
- USB cameras: Plug and play, auto-detected by device

### Output Integration

- MQTT: Configure broker address + topic
- Webhook: Configure callback URL
- Screenshot storage: Configure local directory

### Camera Placement Tips

- Mount at entrances, hallways, and other key locations
- Ensure clear view of target areas, keep camera stable

## Deployment Comparison

| Option | Acceleration | Recommended Streams | Device Price | Cost per Stream |
|--------|--------------|---------------------|--------------|-----------------|
| **reComputer R2000 + Hailo** | Hailo NPU | ~2 streams | $350 | $175/stream |
| **reComputer J3011** (Jetson entry) | TensorRT GPU | ~2 streams | $630 | $315/stream |
| **reComputer J4012** (Jetson multi) ⭐ | TensorRT GPU | ~6 streams | $1000 | $150/stream (best value) |
| **reComputer J5012** (Jetson high-end) | TensorRT GPU | ~9 streams | $2500 | $300/stream |

Choose based on your stream count needs: R2000+Hailo or J3011 for few cameras; J4012 for best multi-stream value; J5012 for high frame rate / many streams.
