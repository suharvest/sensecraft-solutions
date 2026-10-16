# reCamera Region Motion Detection

Choose exactly which parts of the camera image should trigger motion alerts. The reCamera runs detection locally, keeps recent event snapshots, and exposes a small HTTP API, an H.264 RTSP stream, and webhook notifications. No cloud service or NPU model is required.

Use it to monitor a doorway, workstation, or other polygon-shaped area while ignoring moving trees, roads, or other distracting parts of the frame. The Home Assistant integration can edit regions and show the live stream and event snapshots.

## What it provides

- Include and exclude polygons with normalized image coordinates
- Motion start/end events with bounding boxes and optional JPEG snapshots
- HTTP status, configuration, event, and snapshot endpoints on port 8080
- H.264 RTSP stream on port 8554 at `/live0`
- Optional webhook delivery to Home Assistant or another HTTP receiver

The camera pipeline is exclusive: the service stops the stock camera services while it is running. Use the Solution app manager to switch back to another camera application.
