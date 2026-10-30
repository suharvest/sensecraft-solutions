# reCamera Region Motion Detection

Choose exactly which parts of the camera image should trigger motion alerts. The reCamera runs detection locally using classical computer vision on CPU, draws polygon ROI overlays live, and seamlessly integrates with Home Assistant via MQTT. No cloud service or NPU model is required.

Use it to monitor a doorway, workstation, or other polygon-shaped area while ignoring moving trees, roads, or other distracting parts of the frame. Draw detection polygons directly on the live camera stream inside the reCamera Console.

## Features

- **On-Screen Polygon Drawing:** Configure custom multi-point ROI zones directly on the live video in reCamera Console.
- **Real-Time Debug Overlay:** Port 8001 WebSocket delivers live H.264 video with ROI polygons, motion bounding boxes, and status cards.
- **Native Home Assistant Integration:** Uses standard MQTT Auto-Discovery (`binary_sensor.recamera_motion`) — zero custom plugins required on Home Assistant.
- **H.264 RTSP Streaming:** Port 8554 at `/live0` for NVRs, Home Assistant, and media players.
- **Live Snapshots:** High-resolution JPEG snapshots on port 8001 at `/snapshot.jpg`.
- **Lightweight CPU Processing:** Runs efficiently on CPU without TPU/NPU dependencies or model files.
