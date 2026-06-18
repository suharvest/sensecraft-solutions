## What This Solution Does

Warehouse management systems are powerful, but the learning curve is steep — training sessions, memorizing menu locations, mastering complex workflows. Many warehouse workers prefer writing on paper first, then asking someone to enter data later.

This solution turns complex system operations into **speaking** — say "Stock in 10 Watchers" and it's done, ask "How many items on shelf A3?" and get an instant answer. No training needed, just talk.

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

| Option | Network | Devices | Best For |
|--------|---------|---------|----------|
| **SenseCraft Cloud** ⭐Recommended | Internet required | Watcher + R1100/R2000 | Quick start, low cost |
| **Private Cloud** | Internet required | Watcher + R1100/R2000 | Data privacy, use your own cloud APIs |
| **Edge Computing** | LAN only | Watcher + R1100/R2000 + AGX Orin | Fully offline, data never leaves facility |

### Cost Notes

- SenseCraft Cloud / Private Cloud: Native voice cost included in Watcher device, no extra fees
- Edge Computing: Requires separate voice box + AI box deployment, concurrency depends on these boxes' compute capacity

### Optional: Face Recognition for Operator Verification

| Scale | Recommendation |
|-------|----------------|
| Light use (≤20 users) | Watcher built-in face recognition (stores up to 20 faces) |
| Heavy use (20+ users) | Use R2000 + Watcher camera (supports more faces) |
