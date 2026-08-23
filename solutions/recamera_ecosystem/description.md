## What This Solution Does

Plug in an AI camera, open its console in a browser, and install an app: object
detection, text reading, face analysis, drowsiness monitoring, weather
classification, QR scanning, rep counting, fall detection or retail people
counting. Switching apps is a click. All AI runs on the camera, so video never
leaves your network — and when you want the results elsewhere, the camera
publishes them over MQTT and Home Assistant picks them up automatically.

## Key Benefits

| Benefit | Details |
|---------|---------|
| An app gallery on the camera | Install and switch apps from the browser. Your computer does the downloading, so the camera itself needs no internet |
| One camera, many jobs | The same hardware detects objects, reads text, analyzes faces or counts customers, depending on which app is running |
| Home Assistant without glue code | The camera publishes MQTT discovery configs; entities appear on their own, and change when you switch apps |
| Privacy by default | AI runs on the camera. Video and detections stay on your local network, and the console can blur faces before the frame is even encoded |
| Works with what you already have | RTSP for any player, ONVIF discovery for an NVR or VMS (reCamera) |

## The Two Presets

| Preset | Hardware | Where apps come from | MQTT broker |
|--------|----------|----------------------|-------------|
| **reCamera** | reCamera 2002 | The reCamera Console's app gallery, installed by this solution | On the camera, plus the one you deploy with Home Assistant |
| **reCamera Pro** | reCamera Pro | The camera's own App Center, delivered by firmware | None on the camera — the broker comes from the Home Assistant step |

Both follow the same five steps: get the device current, pick an app, deploy
Home Assistant if you want it, point both ends at the same broker, then build
the dashboard.

## Apps in the Gallery

| App | What it does |
|-----|--------------|
| Object Detection | People, vehicles and 80 other everyday classes |
| OCR Text Reader | Chinese and English text from signs, labels and meter displays |
| Face Analysis | Age, gender and emotion, with optional privacy blur on the stream |
| Drowsiness Detection | Eye closure, PERCLOS and yawn frequency from FaceMesh |
| Weather Classification | Clear / cloudy / foggy / rainy / snowy from the camera view |
| QR Code Reader | Every code in frame decoded at once, no model and no handheld scanner |
| Fitness Trainer | Rep counting and form flags for squats, push-ups and curls |
| Fall Detection | Rapid falls from an on-device pose timeline, for fixed indoor views |
| Retail People Counting | Entry / exit counts plus browsing, engaged and assistance states |

The reCamera Pro's App Center carries its own build of most of these, plus
voice transcription. Weather classification is reCamera only.

## Requirements

### Network

- The camera and, if you use it, the Home Assistant machine must be on the same local network
- USB works for initial setup (address `192.168.42.1`)
- The computer running this app needs internet access to download apps on the camera's behalf; the camera does not

### For the Home Assistant steps

- Docker on the machine that will run Home Assistant, with ports 8123 and 1883 free
- Or an existing Home Assistant and MQTT broker, in which case steps 3 and 4 collapse into filling in one address

### Privacy

- All AI detection runs locally on the camera
- Video streams and detection data stay on your local network
