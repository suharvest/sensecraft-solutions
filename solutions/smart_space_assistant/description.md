## What This Solution Does

Your AI assistant is smart, but it can't "see" — it doesn't know who's talking to it.

Imagine this: You come home from work, and your AI assistant recognizes your face and says "Welcome back, John! You have 3 important emails today." When guests arrive, it can tell the difference between family and strangers. In a showroom, it recognizes VIP customers and provides personalized service.

This solution gives your AI assistant "eyes" and a "big screen," turning it into a true smart space butler.

## Core Value

| Benefit | Details |
|---------|---------|
| Recognize & Greet | Say "Remember my face, my name is John," and get greeted automatically next time |
| Personalized Service | Different people get different responses and actions |
| Privacy in Your Hands | All face data stays on local device, never uploaded to cloud |
| Large Display | Cast conversations to TV/monitor for everyone to see |
| Narrate Mode | AI switches background images based on conversation — great for tours & demos |

## Application Scenarios

| Scenario | How It Works |
|----------|--------------|
| Smart Home | Auto-greet family on entry, remind kids about homework, check on elderly's health |
| Guest Reception | Identify VIP customers, auto-display personalized service info on big screen |
| Exhibition | AI interactive display attracts visitors, remembers preferences for next visit |
| Office | Greet you by name in the morning, tell you today's schedule |

## Requirements

### Inputs and Outputs

Voice + face video input; voice response + display content + custom actions output

### Face Recognition Feature

| Condition | Details |
|-----------|---------|
| Capacity | Remembers up to 20 faces |
| Lighting | Requires normal indoor lighting, won't work well in darkness |
| Angle | Frontal face works best, side profiles may be less accurate |
| Device | Only needs SenseCAP Watcher, your existing device works |

### Display Casting Feature

| Condition | Details |
|-----------|---------|
| Display | Requires a TV or monitor with HDMI support |
| Computing | Requires a computer or Raspberry Pi to run the display service |
| Network | Watcher and display device must be on the same WiFi |

### Two Features Can Be Installed Separately

- Just want face recognition? Install only that
- Just want large display? Install only display casting
- Want both? Install both, they work independently

## Deployment Comparison

| Option | Core Device | Feature | Best For |
|--------|-------------|---------|----------|
| **Display Cast** ✨ | SenseCAP Watcher + reComputer R1100 | Cast conversations to TV/monitor | Exhibition demos, multi-person interaction, home entertainment |
| **Face Recognition** | SenseCAP Watcher | Recognize & greet, personalized service | Smart home, VIP reception, office automation |
