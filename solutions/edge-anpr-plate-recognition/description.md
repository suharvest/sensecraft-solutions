## What This Solution Does

Opening a barrier usually means a guard watching the lane, or buying an all-in-one plate-recognition camera and replacing the cameras you already have. This solution keeps your existing gate cameras and adds one recognition host on site to read plates. When a whitelisted vehicle arrives, the barrier opens; every entry and exit leaves a record with the plate number and a snapshot. Plates and images stay on site, nothing goes to the cloud.

## Core Value

| Benefit | Details |
|---------|---------|
| Keep your cameras | Works with your existing 1080p IP cameras; the recognition host pulls video over the local network |
| Whitelisted vehicles open the barrier | A whitelisted plate sends one open signal to the barrier; closing stays with the barrier's own loop detector or radar |
| One record per vehicle | Each vehicle is reported once: plate number, confidence and a snapshot link. Your parking system subscribes once and gets every lane |
| Data stays on site | Snapshots are stored on the recognition host for 7 days by default and leave it only when someone follows the link |
| Measured speed | On Jetson Orin Nano: about 30 frames per second at 1080p, about 6 ms of plate detection per frame |

## Use Cases

| Scenario | How it works |
|----------|--------------|
| Residential or campus gate | Residents' plates go on the whitelist and the barrier opens on arrival; visitors are still let in by the guard |
| Staff car park | Staff plates are imported with validity dates and stop opening the barrier when they expire |
| Entry/exit log | Without a barrier connection, record each vehicle's plate, time and snapshot for your parking system |

## Usage Notes

### Core Hardware

| Device | Role | Required |
|--------|------|----------|
| reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2) | Recognition host: pulls camera video and reads plates | One of three |
| reComputer RK3588 Series | Recognition host: pulls camera video and reads plates | One of three |
| reComputer RK3576 Series | Recognition host: pulls camera video and reads plates | One of three |
| IP camera | Your existing gate camera, 1080p or better, with an RTSP stream | ✓ Required |
| reComputer R1100 Series (R1124-10) | Gate controller: receives recognition messages, checks the whitelist and sends the open signal from its digital output | For automatic barrier opening |
| Interposing relay | DIN-rail relay between the gate controller and the barrier | For automatic barrier opening |

- On Jetson, the Orin Nano and Orin NX modules (reComputer J30 / J40) are supported, running JetPack 6.2.
- Mount the camera 3–8 m from the lane so plates are clearly readable.

### Network Requirements

- Camera, recognition host and gate controller on the same local network; wired connections recommended.
- The recognition host needs internet access during the first deployment to download the software and recognition models. After that it runs offline.

### Recognition Scope

- Mainland China single-row plates: blue (7 characters) and new-energy green (8 characters).
- Two-row, special-purpose and overseas plates are not supported.
- Measured accuracy on still images from the public CCPD dataset (none used in training; video-frame voting simulated with 7 views of each still image): green plates (1,000 images) 80.5% read fully correct from a single image; after voting, 89.0% of vehicles get a reported plate and 91.7% of reported plates are correct. Blue plates (2,400 images including night, blur, tilt, rotation and distant plates) 81.1% read fully correct from a single image. Jetson Orin Nano, RK3588 and RK3576 are within 2 points of each other (504-image subset).
- Before going live, check the results against real plates using day and night footage from your own gate.
