## What This Solution Does

This solution adds gun detection to existing cameras. Every frame is analysed on the device, and an alert is raised when a gun is detected, without a person watching the feed.

## Core Value

| Benefit | Details |
|---------|---------|
| Instant detection | AI scans every video frame in real-time, no human fatigue |
| Works offline | Runs entirely on local hardware, no cloud dependency, no data leaves your network |
| Easy to set up | One-click deployment, starts with demo videos so you can see it working immediately |
| Hardware flexible | Choose NVIDIA Jetson (GPU) or reComputer AI Industrial R21 + Hailo (NPU) based on your needs |

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
| **reComputer AI Industrial R21 + Hailo** | Hailo NPU | ~2 streams | $350 | $175/stream |
| **reComputer J30 series** (Jetson entry) | TensorRT GPU | ~2 streams | $630 | $315/stream |
| **reComputer J40 series** (Jetson multi) ⭐ | TensorRT GPU | ~6 streams | $1000 | $150/stream (best value) |
| **reComputer J50 series** (Jetson high-end) | TensorRT GPU | ~9 streams | $2500 | $300/stream |

Choose based on your stream count needs: R21+Hailo or J30 series for few cameras; J40 series for best multi-stream value; J50 series for high frame rate / many streams.
