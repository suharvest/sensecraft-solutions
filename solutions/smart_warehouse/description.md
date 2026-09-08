## What This Solution Does

This solution replaces the warehouse system's menus and forms with **speech**: say "Stock in 10 Watchers" and the record is written; ask "How many items on shelf A3?" and the answer comes back. Workers enter data where they are standing, instead of walking to a terminal or writing it down for later entry.

## Core Value

| Benefit | Details |
|---------|---------|
| Zero Learning Curve | No training, no menus to memorize — just speak to operate the system |
| Real-Time Accuracy | Direct database queries, inventory data updates instantly with no sync delays |
| Data Security | Supports pure local LAN deployment — data never leaves your facility, no internet required |
| Connect Existing Systems | Already have ERP/WMS? Simple integration available, no need to switch systems |

## Use Cases

| Scenario | How It Works |
|----------|--------------|
| Receiving Goods | Say "Stock in 5 Watchers" — system logs it automatically as you set down the goods |
| Order Picking | Say "Ship 3 units to ABC Company" — generates the shipping record |
| Daily Summary | Ask "What came in today?" — get a voice summary of the day's activity |
| Forklift Operations | Driver asks "How many items on shelf A3?" — gets voice response without leaving the seat |

## Requirements

### System Integration

- Connect to existing ERP/WMS: Bridge via data interface, requires ~few dozen lines of data mapping code
- Use built-in system: Platform includes warehouse management system, zero extra code
- Both options supported

### Voice Features

- Supports fuzzy voice detection (auto-matches closest command)
- Command library can be extended

## Deployment Comparison

### Deployment Options Compared

| Tier | Network | Devices | Best For |
|------|---------|---------|----------|
| **Trial · Starter** | Internet required | Watcher | Small warehouse, cloud-hosted by Seeed, monthly subscription |
| **Tier 1 · Basic** ⭐Recommended | Internet required | Watcher + R1125-10 | Quick start, inventory data stays on your network |
| **Tier 2A · Advanced (Single Site)** | Internet required | Watcher + R2135-12 | Data privacy, your own AI APIs, one site |
| **Tier 2B · Advanced (Multi Site)** | Internet required | Watcher ×1-3 + J4012 | Data privacy, your own AI APIs, up to 3 sites on one box |
| **Tier 3 · Premium** | LAN only | Watcher + R2135-12 + J5011 | Fully offline, data never leaves facility |

### Cost Notes

- Trial: Monthly subscription covering cloud warehouse hosting and voice AI compute
- Tier 1 / Tier 2A (cloud voice mode): Voice cost is included in the Watcher device, no extra fees
- Tier 2A (self-hosted voice) / Tier 2B: Voice AI runs against the LLM provider you choose (DeepSeek, OpenAI, etc.), billed by that provider
- Tier 3: All AI runs locally, no recurring service fees

### Optional: Face Recognition for Operator Verification

| Scale | Recommendation |
|-------|----------------|
| Light use (≤20 users) | Watcher built-in face recognition (stores up to 20 faces) |
| Heavy use (20+ users) | Use a reComputer R2135-12 (Hailo-8) + Watcher camera (supports more faces) |

## Measured Boundaries

Every number below comes from load runs on **a development-board baseline (a faster arm64 board, not a package device and not the R1100's CM4-class SoC)** on 2026-09-05 and 2026-09-06, against a digest-pinned arm64 image and a SQLite backend. They are not a throughput guarantee for other devices, larger datasets or a MySQL backend.

| What the warehouse gets | Typical | Device |
|---|---|---|
| Inventory query answered, 10 people looking at once | **p95 404 ms**, 0% errors | Development-board baseline |
| Stock-in recorded | **p95 106 ms**, 0% errors | Development-board baseline |
| Wrong or duplicate entries under concurrent stock-in | **0 of 1481** batches | Development-board baseline |
| Service back after a 34 s interruption | **about 1 s**, no backlog and no dirty data | Development-board baseline |
| Role and tenant isolation | **4 of 4** probes as expected | Development-board baseline |

Conditions: Mac client over Tailscale so each request crosses a real WAN hop, 60 s per level, 50 seeded materials, one warehouse, SQLite. Query latency grows with how many people are on it at once: p95 doubles to 824 ms at 20 concurrent readers and reaches 5.5 s at 50, where it is no longer usable. Stock-out sustains about 5-6 requests per second per API key under the default 600-per-minute threshold, counted per authenticated caller.

The same digest-pinned image was deployed on 2026-09-07 to the **reComputer R1000's CM4 platform** — a bench board rather than an R1000 chassis, so it is a platform reference value, not a measurement of the shipping product. This solution needs 4 GB of memory and up; pick an R1000 configuration of 4 GB or 8 GB. That run covers restart recovery only: 9.48 s and 9.04 s from container restart to a healthy service. The load figures above have not yet been reproduced on that platform and will be added after a run on a 4 GB / 8 GB R1000.

## Scope of the Numbers

- **Warehouse REST API under load** — one load run, 2026-09-05, on a faster arm64 development board (not the R1100's CM4-class SoC), 50 materials, SQLite, 60 s per concurrency level, client over Tailscale.
- **Concurrency and rate-limit behaviour after the fixes** — re-measured on the same device, 2026-09-06.
- **On-premise LLM throughput on Jetson** — approx. 16 tokens/sec on a reComputer Robotics J5011, stated upstream with no run log attached.
- **Speech recognition accuracy, wake-word range and end-to-end voice latency** — measure these on your own site.

## Known Limitations

- **Concurrent stock-in trades latency for correctness.** Batch numbers are allocated from an atomic counter, so writes to the same material serialise. Concurrency raises p95 rather than causing conflicts, and batch numbers stay unique. Give a busy site more warehouses or spread stock-in across materials rather than raising concurrency on one.
- **Stock-out is rate limited per authenticated caller.** The threshold is "BUSINESS_RATE_LIMIT", 600 requests per minute by default, counted per API key or session — terminals behind one NAT do not share a budget. Anti-enumeration limits on registration, password recovery and device verification stay keyed on the source IP. Raise the threshold before a site exceeds 10 requests per second on one key.
- **The REST layer has no offline queue.** Requests issued while the network or the service is down fail immediately and are never replayed after recovery; the reconnect/backoff logic covers only the MCP voice WebSocket channel, not HTTP inventory calls. Measured: 100% of requests failed during a 34 s outage, with no backlog and no dirty data after recovery. **Two ways around it**: keep the network available at the gateway (wired links, UPS power, service and clients on the same LAN so an outage never crosses the WAN), which shrinks the unavailable window to the device restart time; or queue writes on the client — stock-in/stock-out requests land locally first and replay in order once connectivity returns, de-duplicated by batch number. That client-side queue is not part of this package.
