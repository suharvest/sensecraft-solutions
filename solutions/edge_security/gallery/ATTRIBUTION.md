# Gallery sources

## Footage behind the screenshots

The camera feed in `cover-corridor.jpg`, `workbench-alert.gif` and
`rules-editor-live.gif` is not a staged office clip — it is real fixed-camera
CCTV of a university corridor, replayed over RTSP into the solution's own
detector.

| Item | Value |
|---|---|
| Source dataset | CCTV-Gun, UCF subset (`Cam7-From09-05-50To10-09-24_Segment_8`) |
| Frames used | 900–1112, a single continuous run (frame 1012 is missing from the dataset and is filled by repeating 1011) |
| Original frames | 1920×1080, sampled at ~2 fps, burnt-in timestamp 22/09/2018 09:33:41 → 09:35:27 |
| What we made | 1280×720 H.264, 15 fps, 106.4 s, each source frame held for its real 0.5 s so motion runs at wall-clock speed |
| How it was used | looped into a local MediaMTX and pulled by the detector at 5 fps |

The dataset is a firearms-detection benchmark. **Only the pedestrians and the
surveillance viewpoint are used here.** The segment was picked by reviewing the
frames first: people walk through the corridor and a group stands talking at the
far end; no weapon is visible in any frame that appears in these assets. Nothing
in this solution detects or claims to detect weapons — the model is a
person-only YOLOv8n.

## Files

| File | Source |
|---|---|
| `cover-corridor.jpg` | One preview frame from the running detector, with that frame's own MQTT `sensecraft.detection/1` payload (4 person boxes, track ids, scores) and the two configured rules drawn on top. Boxes and rule geometry are the live values, not illustrations. |
| `workbench-alert.gif` | Screen recording of the alert workbench on a live hub (`spark-cctv-01/cam-0`), including an Acknowledge action. |
| `rules-editor-live.gif` | Screen recording of the rule editor. The background is the camera frame the hub proxies from the detector's preview endpoint. |
| `architecture-diagram.png`, `architecture.svg`, `cover.svg` | Drawn for this solution package. No third-party artwork. |
| `cover.jpg`, `rules-editor.jpg`, `devices.jpg` | Earlier development-period screenshots. Kept for reference; no longer referenced by `solution.yaml`. |

No images are taken from third-party sites.
