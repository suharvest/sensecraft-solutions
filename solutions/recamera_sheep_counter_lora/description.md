## What This Solution Does for You

Managing livestock at a remote farm or off-grid paddock is hard when you can't see the gate. This solution turns a reCamera into an automatic sheep counter that broadcasts IN / OUT / INSIDE totals over LoRa — reaching your phone and a Home Assistant dashboard, even kilometres away, with no WiFi at the gate.

## Core Value

| Benefit | Details |
|---------|---------|
| Works anywhere | LoRa radio carries counts up to 5 km line-of-sight — no cellular or WiFi at the gate |
| Hands-free counting | YOLO model counts every sheep crossing the gate line automatically |
| Real-time phone alerts | Each crossing sends an instant Meshtastic notification to your phone |
| Persistent dashboard | Home Assistant keeps a running total and 24-hour history you can check anytime |
| Off-grid resilient | LoRa heartbeat every 15 minutes re-syncs counts after signal loss |

## Use Cases

| Scenario | How it works |
|----------|-------------|
| Daily mustering | Know how many sheep entered or left the paddock without counting by hand |
| Night security | Get an alert whenever sheep cross the gate during off-hours |
| Remote farm monitoring | Farmer checks the HA dashboard from town — no need to drive out |
| Multi-gate tracking | Add more reCamera + LoRa nodes per gate; all report to the same HA instance |

## Usage Notes

### Core Hardware (Required)

| Device | Notes | Required |
|--------|-------|---------|
| Seeed reCamera 2002 HQ PoE | Runs the YOLO sheep detector and counting binary; RISC-V SG2002 NPU, no WiFi | ✓ Required |
| XIAO ESP32-S3 + Wio-SX1262 | Meshtastic LoRa node — connects to reCamera via UART, transmits counts | ✓ Required |
| reComputer R1100 or Raspberry Pi | Gateway host — needs LAN access; runs bridge services and optionally Home Assistant | ✓ Required |
| Meshtastic LoRa receiver | Second Meshtastic device at the gateway (USB serial or standalone radio) | ✓ Required |
| Home Assistant server | Displays the dashboard and stores count history | ✓ Required |

### Network Requirements

- reCamera needs only a direct USB or Ethernet connection to your laptop during deployment — no internet required at the gate
- The gateway computer needs LAN access to your Home Assistant server
- LoRa range: up to ~5 km line-of-sight with Meshtastic at default settings; range is reduced in hilly or wooded terrain
