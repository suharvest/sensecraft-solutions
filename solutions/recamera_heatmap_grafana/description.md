## What This Solution Does

Rearranging shelves and moving promotions around based on gut feeling rarely works well. This solution uses AI cameras to track customer movement and generate intuitive traffic distribution maps, showing you which areas are hot spots and which are dead zones — so you can make data-driven decisions for store operations.

And you don't have to stress about device selection — reCamera works out of the box for single-camera setups, while IP cameras + AI boxes can handle more channels. The same algorithm runs on different hardware with consistent results, so you can try before you commit.

## Key Benefits

| Benefit | Details |
|---------|---------|
| Find Hot Spots | See at a glance which shelves attract the most customers — no need to review hours of footage |
| Discover Dead Zones | Instantly identify which aisles get ignored and which corners are overlooked |
| Compare Time Periods | Morning vs evening, weekdays vs weekends — pull up historical data anytime |
| Flexible Device Options | reCamera for quick single-camera setup, IP cameras + AI boxes for multi-channel coverage — mix and match to fit your budget |

## Use Cases

| Scenario | How to Use |
|----------|------------|
| Retail Stores | See which shelves customers linger at longest, place featured products in hot spots |
| Chain Store Expansion | Validate with reCamera at one location first, then scale with IP cameras + AI boxes across stores |
| Existing Camera Upgrade | Keep your current IP cameras, add an AI box to enable heatmap analytics — no equipment replacement needed |
| Exhibition Halls | Find the most popular exhibits and visitor paths, optimize future layouts |

## Requirements

### Installation

- Camera should be mounted high for a top-down view covering the target area
- All devices must be on the same local network

### Single-Channel Setup Tips

- Camera distance to target: 3-5 meters
- Target object size in frame: ideally >30×30 pixels

## Deployment Comparison

| Option | Core Device | Camera Channels | Best For |
|--------|-------------|-----------------|----------|
| **AI Camera Direct** | reCamera + reComputer R1100 | 1 per camera | Quick evaluation, small single-point area |
| **Upgrade Existing Cameras** | IP camera + Jetson AI box | Multiple per box | Large area coverage, keep existing cameras |

## Data Contract

Every detector — reCamera, reCamera Pro, Jetson, Rockchip, Raspberry Pi + Hailo — publishes to the MQTT broker on the backend and never writes to InfluxDB itself. Telegraf is the single writer, so one dashboard covers every source and adding a device class means implementing one message format.

| Channel | Topic | Content |
|---------|-------|---------|
| Analytics | `<installation>/retail-vision/results/<camera-id>` | One batched JSON per publish interval (1 s default): zone counters plus one entry per tracked person |
| Availability | `<installation>/retail-vision/status` | `online` / `offline`, retained |

The payload is VisionPayload, the format the reCamera `retail-vision` C++ app already emits:

```json
{
  "timestamp": 1709500000000, "frame_width": 1280, "frame_height": 720,
  "zone": {"occupancy_count": 3, "browsing_count": 1, "engaged_count": 1,
           "assist_count": 0, "avg_dwell_time": 8.5,
           "entry_count": 12, "exit_count": 10},
  "persons": [{"slot": 0, "track_id": 7, "state": "engaged",
               "cx_pct": 41.2, "cy_pct": 63.8, "dwell_duration": 5.2}]
}
```

`<installation>` is only the first topic segment, there to keep several sites apart on one broker — a store, floor or room name works just as well. Batching matters: publishing one message per detected person put the broker's message rate at people × cameras × frame rate, which is what falls over first once a site runs more than one device.

Three fields carry their weight for a specific reason. `slot` is the person's index within the batch — everyone in one message shares a timestamp, and without a distinguishing tag InfluxDB overwrites them down to a single row per frame; index rather than `track_id` keeps the tag bounded by people-per-frame instead of growing for the life of the deployment. `cx_pct` / `cy_pct` are normalised centres, so one floor-plan calibration holds regardless of sensor resolution.

### Compute and Cost Notes

- Light compute load: each box processes locally, server only aggregates data
- IP camera + AI box throughput depends on box inference performance (scales with compute)
- Fully local, no cloud fees
