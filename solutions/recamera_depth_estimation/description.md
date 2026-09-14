## What it does

Turns the ordinary image on a reCamera you already have into a per-pixel depth map, with no depth camera or stereo lens. The video stream carries a colour depth preview in the corner (red near, blue far), and MQTT carries the numbers.

## What "depth" means here

**Relative, not metres.** The output answers "is anything close to the camera", "which side of the frame is nearer" and "has something moved into the foreground"; it should not be read as distance.

## Measured results

| Metric | Result |
|---|---|
| Per-frame processing time | **35.4 ms** |
| Continuous run | **524 frames, no stalls** |
| Model size | **2.9 MB** |

Tested on reCamera (SG2002), 655-frame sample.

## Where it works and where it does not

- **Works**: indoor scenes with real depth; near furniture reads red, the far wall reads blue, and the 3x3 grid matches the preview.
- **Does not work**: on a blank ceiling the usable spread fell from **1.72** to **0.41**; untextured surfaces, glass and sky behave the same. The second gallery image shows this case.
- **Outdoors**: the model was trained on indoor scenes, so the range compresses sharply.

## What you get

- **RTSP stream** on port 8554 with the depth preview in the corner
- **MQTT data**: near-area ratio and a 3x3 proximity grid, so you can tell which side is nearer
- **Home Assistant** discovery for the near-area and near-presence entities
- **ONVIF** so a VMS can find the camera and pull the stream

## Source

The app and the model conversion scripts are open:
<https://github.com/Seeed-Studio/sscma-example-sg200x> under
`solutions/depth-estimation/` and `tools/model_conversion/fastdepth/`.
