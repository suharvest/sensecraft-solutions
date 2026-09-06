## What it does

A depth camera tells you how far things are. It also costs more, needs a second
lens or a projector, and gives you one more thing to mount and align.

This runs a monocular depth model on the reCamera you already have. One ordinary
image goes in; a dense per-pixel depth map comes out, on the camera's own TPU.
The video stream carries a colour depth preview in the corner, and MQTT carries
the numbers.

## What "depth" means here

**Relative, not metres.** The model orders the scene from near to far. It does
not measure distance, and nothing in the output should be read as one. Absolute
distance would need camera calibration and target-domain training, neither of
which is part of this.

That ordering is still enough for a useful class of questions: is anything close
to the camera right now, which side of the frame is nearer, has something moved
into the foreground.

## Measured on hardware

reCamera (SG2002 / CV181x), BF16 model, 655-frame sample:

| | |
|---|---|
| TPU forward pass | 19.7 ms (p95 19.8) |
| Whole per-frame path | 35.4 ms |
| Model size / ION | 2.9 MB / 6.7 MB |
| Stability | 524 frames, no pipeline stalls |

The forward pass is stable to within 0.1 ms frame to frame. Everything else in
the budget is CPU-side work — preprocessing, statistics, the colour preview —
which is why the whole path is longer than the model alone.

## Where it works and where it does not

Checked against a room with real depth: near furniture on one side reads red,
the receding floor and far wall read blue, and the reported 3x3 grid agrees with
what the preview draws.

Pointed at a blank ceiling, the usable range collapses — the spread between the
2nd and 98th percentile fell from 1.72 to 0.41 on the same camera. Large
untextured surfaces, glass and sky are the documented weak cases for this class
of model. The second gallery image is that failure, not a good result.

The model was trained on indoor scenes. Outdoors the range compresses sharply.

## What you get

- **RTSP** on port 8554 with the depth preview composited into the corner
- **MQTT** with per-frame percentiles, a near-area ratio, and a 3x3 proximity
  grid so you can ask "is the left side nearer than the right"
- **Home Assistant** discovery for the near-area and near-presence entities
- **ONVIF** so a VMS can find the camera and pull the stream

## Source

The app and the model conversion scripts are open:
<https://github.com/Seeed-Studio/sscma-example-sg200x> under
`solutions/depth-estimation/` and `tools/model_conversion/fastdepth/`.
