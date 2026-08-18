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
| How it was used | looped into a local MediaMTX on the board and pulled over RTSP/TCP by the detector |

## Platform the assets were captured on

All three live assets come from one run of the `rk3588_hub` preset's own stack
on a Radxa ROCK 5T (RK3588, kernel 6.1.84), not from a workstation.

| Item | Value |
|---|---|
| Detector | `rk3588-01` / `cam-0`, `yolov8n_zoo_int8.rk3588@856ae37c39d3`, RKNN int8 |
| Runtime | `rknn-lite2-2.3.2` on the RK3588 NPU, `npu_core_mask: null` (runtime schedules across the three cores) |
| Decode | Rockchip MPP hardware decoder (`mppvideodec`), `health.decode: hw`, `fallback_active: false` |
| Measured | `health.fps` 13.1–13.6, `inference_time_ms` 18–36 on a 1280×720 H.264 source |
| Rules | zone `Corridor end doorway` (4 points, dwell 10 s), line `Mid-corridor tripwire` (0.80,0.52)→(0.20,0.58) with `direction: forward`, cooldown 20 s |
| Hub | `edge-security-hub:0.1.0` container on the same board, broker `eclipse-mosquitto:2` on the same board |

The tripwire arrow drawn on the cover points to the half-plane the hub's own
convention calls the destination of a `forward` crossing: `side()` is the sign
of `(end-start) × (p-start)` and `forward` is `+1 → -1`, which for these two
endpoints is the direction walking toward the camera.

The dataset is a firearms-detection benchmark. **Only the pedestrians and the
surveillance viewpoint are used here.** The segment was picked by reviewing the
frames first: people walk through the corridor and a group stands talking at the
far end; no weapon is visible in any frame that appears in these assets. Nothing
in this solution detects or claims to detect weapons — the model is a
person-only YOLOv8n.

## Files

| File | Source |
|---|---|
| `cover-corridor.jpg` | 1280×720. The detector's preview for that instant is matched back to the source frame it was decoded from (normalised cross-correlation, best score 0.987), and that full-resolution frame carries the overlay. Boxes, track ids and scores are that frame's own MQTT `sensecraft.detection/1` payload; the zone and line are the rules stored in the hub; the HUD strings are read out of the payload and the device's `sensecraft.status/1` message, not typed in. |
| `workbench-alert.gif` | 1000×404, 10 fps, 11.9 s. Screen recording of the alert workbench against the hub on the board, filtered to line-crossing alerts, ending on an Acknowledge that stamps the row with `admin` and the wall-clock time. Every thumbnail is a snapshot the detector published for that alert. |
| `rules-editor-live.gif` | 1000×404, 10 fps, 11.9 s. Screen recording of the rule editor. The background is the camera frame the hub proxies from the RK3588 detector's preview endpoint. A second zone and a second line are drawn on it, the new line's direction is cycled from `both` to `forward`, and Save persists rev 2. |
| `architecture-diagram.png`, `architecture.svg`, `cover.svg` | Drawn for this solution package. No third-party artwork. |
| `cover.jpg`, `rules-editor.jpg`, `devices.jpg` | Earlier development-period screenshots. Kept for reference; no longer referenced by `solution.yaml`. |

No images are taken from third-party sites.
