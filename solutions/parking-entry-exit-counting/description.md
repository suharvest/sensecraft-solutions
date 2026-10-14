## What the Solution Does

Count vehicles in and out with the gate cameras you already have, and keep the free-space count live.

Use existing entry and exit cameras to track vehicle movements, broadcasting in-facility counts and available spaces directly to your signage and parking management system—no ground loops or gate modifications required.

- **Directional Line-Crossing Counting**: Draws virtual tripwires across entry and exit lanes, tracking vehicles and discerning direction automatically.
- **Live Space Updates**: Automatically updates total occupancy and remaining spaces after every passage, published via MQTT in real time.
- **Multi-Class Vehicle Classification**: Detects and categorizes cars, trucks, buses, and motorcycles.

## Core Value

- **Zero Pavement Construction**: Leverages existing RTSP surveillance cameras without excavating roads for induction loops.
- **Local Real-Time Edge Processing**: Video decoding, detection, multi-frame tracking, and line-crossing verdicts happen on the local edge box—no video streams leave the site.
- **Cross-Platform Accelerator Support**: Supported across reComputer J30 / J40 Series (Jetson Orin Nano / NX), reComputer RK3576 Series, and RK3588 Series.
- **Multi-Gate Aggregation**: Each entrance/exit operates independently; an upstream system aggregates total spaces by site ID.

## Suitable Scenarios

Sites where vehicles pass through designated lanes and live lot occupancy must be tracked:

- **Shopping Mall and Office Garages**: Entrance display signs show available spaces in real time, switching to "Full" at zero.
- **Campus and Factory Main Gates**: Tracks daily vehicle flow separated by trucks and passenger cars.
- **Multi-Gate Parking Facilities**: Deploy one edge unit per gate; central systems aggregate spaces across all access points.

## Measured Performance

Tested with standard vehicle passage test footage:

| Metric | Typical | Device |
|---|---|---|
| Crossings counted | **41/41**, every direction correct | reComputer J30 Series (J3011, 30 fps input) |
| Processing speed | **30 fps** (640×360 input) | reComputer J30 Series (J3011) |
| Processing speed | **30 fps** (640×360 input) | reComputer RK3576 Series |
| Processing speed | **about 3 fps** (1280×720 input at 5 fps) | reComputer RK3588 Series |

## Usage Notes

- **Camera Mounting**: One unit connects to one fixed-angle camera covering one lane. Position the camera looking down at the lane so vehicles are not obstructed.
- **Hardware Selection**: reComputer J30 and RK3576 handle high-speed traffic at 30 fps; the RK3588 suits barrier gates where vehicles slow down or stop before passing.
- **Integration Interfaces**: Publishes events over MQTT port 1883 and provides HTTP `/healthz` endpoints.

> 📖 **Engineering Reference:** Full architecture internals, measured benchmarks, and failure modes are documented in the [Engineering Wiki · Parking Vehicle Counting](https://wiki.seeedstudio.com/solutions/edge-parking-counting/).
