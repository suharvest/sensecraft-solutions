## What This Solution Does

A small AI camera that you plug in, pick an app, and it just works. Object detection, text reading, face analysis, smart home integration — choose what you need, deploy in one click. All AI processing happens on the camera itself, so your video never leaves your network.

## Key Benefits

| Benefit | Details |
|---------|---------|
| Pick an App, Click Deploy | Heatmap, text reader, face analysis, Home Assistant — each is a one-click install, no coding needed |
| One Camera, Many Uses | The same camera can detect objects, read text, analyze faces, or connect to your smart home |
| Plug & Play | Connect via USB, pick an app, hit deploy — done in minutes |
| Privacy by Default | AI runs on the camera; video and data stay on your local network |

## Use Cases

| Scenario | How to Use |
|----------|------------|
| Quick Demo | Deploy the heatmap preview to show what the camera can do — no extra hardware needed |
| Smart Home | Add the camera to Home Assistant for live video + AI-triggered automations |
| Text Reading | Point at signs, labels, or displays — recognized text appears on screen in real-time |
| Face Analysis | Detect faces and see age, gender, and emotion — all processed on-device with privacy in mind |
| Mix & Match | Use heatmap for analytics AND Home Assistant for automations — both from the same camera |

## Requirements

### Inputs and Outputs

By application:
- Heatmap preview: Video input → Web heatmap output
- Home Assistant: Video input → RTSP stream + AI sensor entities output
- OCR: Video input → Recognized text output (real-time overlay)
- Face analysis: Video input → Age/gender/emotion labels output (optional privacy blur)

### Network

- Camera and server must be on the same local network
- USB connection for initial setup (IP: 192.168.42.1)

### Privacy

- All AI detection runs locally on the camera
- Video streams and data stay on your local network

## Deployment Comparison

| Option | Core Device | Feature | Best For |
|--------|-------------|---------|----------|
| **Retail People Flow Heatmap** ⚡ | reCamera | Spot hot zones vs cold zones from shopper positions | Retail traffic analysis, no extra hardware needed |
| **Home Assistant Integration** 🏠 | reCamera + reComputer R1100 | RTSP stream + AI sensors in HA | Smart home users, existing HA setup |
| **OCR Text Reader** 🆕 | reCamera | Read Chinese/English text | Meter readings, label scanning, document processing |
| **Face Analysis** 🆕 | reCamera | Age/gender/emotion + privacy blur | Traffic analysis, smart reception |

All options run fully local with no cloud fees.
