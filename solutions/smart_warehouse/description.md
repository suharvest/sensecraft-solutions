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

Every number below comes from load runs on **a development-board baseline (a faster arm64 board, not a package device and not the R1100's CM4-class SoC)** on 2026-09-05 and 2026-09-06, against a digest-pinned arm64 image and a SQLite backend. They are not a throughput guarantee for other devices, larger datasets or a MySQL backend. The same digest-pinned image was deployed on 2026-09-07 to the **reComputer R1000's CM4 platform** — a bench board rather than an R1000 chassis, so it is a platform reference value, not a measurement of the shipping product. This solution needs 4 GB of memory and up; pick an R1000 configuration of 4 GB or 8 GB. That run covers restart recovery only: 9.48 s and 9.04 s from container restart to a healthy service, two runs polled at 250 ms on the device's own loopback (`evaluation/runs/2026-09-07-recomputer-r1000/results.md` in the warehouse_system project). The load figures in the table have not yet been reproduced on that platform and will be added after a run on a 4 GB / 8 GB R1000.

| Scenario | Level | Measured | Conditions | Source |
|----------|-------|----------|------------|--------|
| Inventory query "GET /api/materials/list" | concurrency 10 | p95 404 ms, p99 2.7 s, 0% errors — stable | RPi5, Mac client over Tailscale (real WAN hop), 60 s at this level, 50 seeded materials, 1 warehouse, SQLite | "runs/2026-09-05-load/raw-rpi5/query_summary.json" |
| Inventory query "GET /api/materials/list" | concurrency 20 | p95 824 ms, p99 5.3 s, 0% errors — degrading (p95 over 500 ms, doubled vs. level 10) | RPi5, Mac client over Tailscale, 60 s at this level, 50 seeded materials, SQLite | "runs/2026-09-05-load/raw-rpi5/query_summary.json" |
| Inventory query "GET /api/materials/list" | concurrency 50 | p95 5.5 s, p99 8.7 s, still 0% errors — latency no longer usable | RPi5, Mac client over Tailscale, 60 s at this level, 50 seeded materials, SQLite | "runs/2026-09-05-load/raw-rpi5/query_summary.json" |
| Stock-in "POST /api/materials/stock-in" | concurrency 1 | p95 106 ms, 0% errors — stable | RPi5, Mac client over Tailscale, 60 s at this level, all requests on the same material, SQLite | "runs/2026-09-05-load/raw-rpi5/stock_in_summary.json" |
| Stock-in "POST /api/materials/stock-in" | concurrency 5 / 10 / 20 | 0% errors at every level, 1481 batches created with 0 duplicate batch numbers, p95 634 ms – 4.96 s | Same host and client, all requests on the same material, SQLite; batch numbers come from an atomic counter, which serialises writes and is why p95 climbs with concurrency | Re-test on the same board, 2026-09-06 |
| Stock-out "POST /api/materials/stock-out" | concurrency 10 / 20 / 50 | 0 HTTP 429 at the default 600/minute threshold; sustained throughput about 5–6 req/s per API key | Same host and client, two API keys behind one exit IP, traffic split evenly, SQLite; the limit is counted per authenticated caller, so keys behind one NAT do not share a budget | Re-test on the same board, 2026-09-06 |
| Service interruption | ~10 req/s query traffic, 34 s outage | 100% request failure during the outage, nothing queued or replayed; full recovery within ~1 s of the service coming back, no backlog and no dirty data | RPi5, outage simulated by stopping and restarting the container (34 s includes the migration checks on boot), Mac client over Tailscale, SQLite | "runs/2026-09-05-load/raw-rpi5/offline_summary.json" |
| Role and tenant isolation | 4 single-shot probes | All 4 as expected: VIEW key on a write endpoint 403, VIEW key on a read endpoint 200, cross-tenant write 403, cross-tenant read 403 | RPi5, "DEPLOY_MODE=multi_tenant", 2 tenants, 2 warehouses, view/operate/admin API keys | "runs/2026-09-05-load/results.md" |

## Known Limitations

- **Concurrent stock-in trades latency for correctness.** Batch numbers are allocated from an atomic counter, so writes to the same material serialise. Concurrency raises p95 rather than causing conflicts, and batch numbers stay unique. Give a busy site more warehouses or spread stock-in across materials rather than raising concurrency on one.
- **Stock-out is rate limited per authenticated caller.** The threshold is "BUSINESS_RATE_LIMIT", 600 requests per minute by default, counted per API key or session — terminals behind one NAT do not share a budget. Anti-enumeration limits on registration, password recovery and device verification stay keyed on the source IP. Raise the threshold before a site exceeds 10 requests per second on one key.
- **The REST layer has no offline queue.** Requests issued while the network or the service is down fail immediately and are never replayed after recovery; the reconnect/backoff logic covers only the MCP voice WebSocket channel, not HTTP inventory calls. Measured: 100% of requests failed during a 34 s outage, with no backlog and no dirty data after recovery. **Two ways around it**: keep the network available at the gateway (wired links, UPS power, service and clients on the same LAN so an outage never crosses the WAN), which shrinks the unavailable window to the device restart time; or queue writes on the client — stock-in/stock-out requests land locally first and replay in order once connectivity returns, de-duplicated by batch number. That client-side queue is not part of this package.
