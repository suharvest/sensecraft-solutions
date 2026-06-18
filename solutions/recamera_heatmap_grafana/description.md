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

### Compute and Cost Notes

- Light compute load: each box processes locally, server only aggregates data
- IP camera + AI box throughput depends on box inference performance (scales with compute)
- Fully local, no cloud fees
