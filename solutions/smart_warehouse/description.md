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
| Heavy use (20+ users) | Use R2000 + Watcher camera (supports more faces) |
