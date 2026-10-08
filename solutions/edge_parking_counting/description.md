## What this solution does for you

Knowing how many free spaces a car park has usually means burying induction loops in every lane or fitting counters to the barriers. This solution uses the IP camera already at the entrance: after deployment you drag a counting line across the picture in a web page, every vehicle that crosses it is counted as in or out, and the number of vehicles inside and the free spaces are sent to your system as they change.

## Key benefits

| Benefit | Details |
|---------|---------|
| Uses your existing camera | Connects to the RTSP IP camera already at the entrance; no loops to bury, no barrier changes |
| In and out counted separately | Each crossing is classed as entering or leaving, so a two-way lane is still counted correctly |
| Free spaces updated live | Vehicles inside and free spaces are published after every crossing, ready for a free-space sign or a parking system |
| Processed on site | The video is analysed on the device next to the entrance; only the counts leave it |
| Vehicle types | Cars, motorcycles, buses and trucks are told apart, and every crossing record carries the type |

## Use cases

| Scenario | How it works |
|----------|--------------|
| Shopping mall or office car park | The entrance sign shows "37 spaces free" and updates as vehicles come and go |
| Campus or factory gate | Daily in/out totals, with trucks and cars counted separately |
| Car park full alert | When free spaces reach 0, the parking system receives the message and switches to "Full" |
| Several entrances | One set per entrance; your system adds them up by site ID |

## What you get after deployment

Each time a vehicle crosses the counting line, the device sends two messages to your MQTT server:

- **Crossing record** (topic `<site ID>/parking/<entrance ID>/crossing`): direction (in / out), vehicle type, confidence, and vehicles inside and free spaces after the crossing.
- **Car park status** (topic `<site ID>/parking/<entrance ID>/occupancy`): vehicles inside, total spaces, free spaces, and today's in and out totals.

Your parking management system, free-space sign or Home Assistant subscribes to these two topics to use the data.

## Usage Notes

### Core hardware

| Device | Purpose | Required |
|--------|---------|----------|
| reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2) | Analyses the camera picture and counts; needs JetPack 6.2 | Pick one |
| reComputer RK3588 Series | Analyses the camera picture and counts | Pick one |
| reComputer RK3576 Series | Analyses the camera picture and counts | Pick one |
| Entrance IP camera | RTSP stream (H.264 or H.265), fixed view of the lane | ✓ Required |
| MQTT server | Receives the counts; an existing site server or a Mosquitto install | ✓ Required |

### Network requirements

- The counting device, the camera and the MQTT server must be on the same LAN or able to reach each other
- The first deployment downloads the app (about 0.5–0.7 GB) and the vehicle model; after that it runs without internet
- One device handles one camera, i.e. one entrance

## Deployment Comparison

| | reComputer J30 / J40 (Jetson Orin Nano / Orin NX) | reComputer RK3588 Series | reComputer RK3576 Series |
|---|---|---|---|
| Measured processing rate | Orin Nano: 30 frames per second (640×360 input at 30 fps) | About 3 frames per second (1280×720 input at 5 fps) | 30 frames per second (640×360 input at 30 fps) |
| Analysis time per frame | Orin Nano: about 3.6 ms | About 18 ms | — |
| Suited to | Entrances where vehicles drive through at normal speed | Barrier entrances where vehicles slow down or stop for the barrier | Entrances where vehicles drive through at normal speed |
| System requirements | Jetson Orin Nano or Orin NX module, JetPack 6.2 | The deploy step checks the board's NPU runtime and video decoding libraries and tells you what to install if any are missing | Same as RK3588 |

Measured on Jetson Orin Nano: on a 30 fps test video, all 41 line crossings were counted with the correct direction. RK3588 processes about 3 frames per second, so a vehicle needs to be in view for about 1 second or longer as it crosses the line to be counted reliably. Measured on RK3576: on a 30 fps test video, every frame was processed and vehicles were counted in both directions.
