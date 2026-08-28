## What This Solution Does

You want to know how many people walked into the shop this morning, how many are queuing right now, whether the meeting room is actually occupied. The usual answer is a camera, a network cable, a server, and a video stream leaving the building.

This solution does it with one camera module and a USB cable. The Grove Vision AI Module V2 detects people, tracks them frame to frame, counts each crossing of the lines you draw, and reports how many people are standing in the zones you draw. The video stays on the USB link: frames go straight to the app on your own computer for the live preview, and never touch a network or a cloud service.

## Core Value

| Benefit | Details |
|---------|---------|
| Everything on device | Detection, tracking and counting run on the Himax WE2 and its Ethos-U55 NPU |
| No network, no cloud | Counts, detection coordinates and the preview image all travel over the USB cable only — nothing is uploaded |
| Draw your own geometry | Up to 4 counting lines with In/Out totals, up to 4 zones with live occupancy |
| No infrastructure | No network, no server, no account — a USB cable is the whole install |
| Open data out | SSCMA JSON over serial, easy to pipe into your own script or gateway |

## Application Scenarios

| Scenario | How It Works |
|----------|--------------|
| Shop entrance | A counting line across the doorway gives footfall in and out per direction |
| Queue monitoring | A zone over the queue area gives a live count to drive staffing decisions |
| Meeting room / office | A zone tells you whether the room is genuinely occupied, without a booking system |
| Corridor and stairwell flow | Multiple lines along a path show which way traffic is moving |
| Exhibition booth | A zone around the booth measures dwell, a line at the entrance measures visits |

## Measured Performance

| Metric | Value |
|--------|-------|
| Inference time | 48 ms per frame |
| End-to-end throughput | About 13 fps |
| Input resolution | 240 x 240 |
| Model | Swift-YOLO Nano, single class (person) |
| Model accuracy | 92.6% mAP after INT8 quantization |
| Runs on | Ethos-U55 NPU (Vela-compiled) |

These are measured on the module. Real-world counting accuracy depends on your mounting, lighting and traffic density — see the mounting notes below and validate in your own space.

## Requirements and Limits

| Condition | Details |
|-----------|---------|
| Hardware | Grove Vision AI Module V2 and a USB-C data cable — nothing else |
| Counting lines | Up to 4, each with its own In and Out totals |
| Counting zones | Up to 4, each with a live occupancy number |
| Lighting | Normal indoor lighting. Strong backlight behind the subject is the common failure case |
| Density | Tracking is per-frame association; heavy occlusion in dense crowds will cost accuracy |
| Not yet measured | Counting accuracy against a human ground-truth count, and detection recall from a straight-down ceiling mount, have not been tested |

## Mounting Suggestions

These follow from how the model and the tracker work; treat them as starting points to validate, not as guaranteed settings.

- **Tilted overhead** is the usual choice — it keeps people in the conventional viewpoint the detector was trained on. Set the tracking anchor to **box bottom center (feet)**. With the box center, the bounding box grows as a person approaches the camera, dragging the anchor point across a nearby line and registering a crossing that did not happen.
- **Straight down** minimizes people occluding each other, which helps under dense traffic. The trade-off is that the model was trained on conventional viewpoints, so detection recall from directly overhead may drop. Test before committing.
- Keep counting lines away from the frame edge so each track is stable on both sides of the line.
