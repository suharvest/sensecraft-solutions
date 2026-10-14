## What the Solution Does

Use the cameras already in your car park to tell which bays are taken, with free spaces always up to date.

Evaluate whether each parking space is occupied or vacant using standard IP surveillance cameras. Status updates publish in real time over MQTT to free-space guidance signs and parking management software without installing per-bay sensors. Video never leaves the site.

- **Per-Bay Visual Detection**: Evaluates vehicle coverage within configured bay polygons, determining "occupied" or "vacant" status in real time.
- **Live Space Broadcasting**: Publishes per-bay states and aggregated vacant counts over MQTT to drive digital signage and mobile apps.
- **Multi-Camera Aggregation**: A single edge host processes multiple RTSP streams, covering dozens to hundreds of parking bays.

## Core Value

- **Zero Dedicated Sensor Installation**: Repurposes existing IP security cameras—no ceiling ultrasonic sensors, cable trays, or buried geomagnetics required.
- **Local Edge Inference**: Decoding and bay analysis run entirely on the local edge computer, keeping video data strictly on premise.
- **Interactive Web Bay Editor**: Draw and adjust parking bay polygons directly over the live camera view in a browser; changes apply immediately.
- **Cross-Platform Accelerator Support**: Supported across reComputer J30 / J40 Series (Jetson Orin Nano / NX), reComputer RK3576 Series, and RK3588 Series.

## Suitable Scenarios

Car parks where cameras overlook bays from an elevated vantage point and operators need live space availability:

- **Underground Garage Signage**: Several cameras per level; available bays are summed per level and displayed on entrance and ramp signs.
- **Shopping Malls and Commercial Garages**: Count free bays by zone to guide incoming drivers to zones with open capacity.
- **Reserved Bay Monitoring**: Draw dedicated polygons over EV-charging, disabled, or reserved spaces to notify staff when occupied.

## Measured Performance

Each camera stream is evaluated at one frame per second:

| Metric | Typical | Device |
|---|---|---|
| Streams on one host | **6**, 620 s continuous, no dropped frames | reComputer J30 Series (J3011) |
| Bays marked "unknown" after a camera drops | **about 10 s** | reComputer RK3576 Series |

## Usage Notes

- **Camera Mounting**: Mount cameras high looking down at an angle so bays are not completely occluded by tall adjacent vehicles. Draw one bounding polygon per bay.
- **Multi-Stream Expansion**: When adding cameras, add streams sequentially and verify ongoing status updates on the dashboard.
- **Output Interfaces**: Publishes bay states under `<site>/parking/<camera>/slots` on MQTT port 1883 and exposes an HTTP `/healthz` health endpoint.

> 📖 **Engineering Reference:** Full architecture internals, measured benchmarks, and failure modes are documented in the [Engineering Wiki · Parking Space Occupancy Detection](https://wiki.seeedstudio.com/solutions/edge-parking-occupancy/).
