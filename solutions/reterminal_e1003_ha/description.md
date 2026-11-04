# Smart Home Control Panel for Home Assistant

## What this solution does for you

Most smart home setups force you to unlock a phone or look at a bright LCD in the dark. This setup turns a wall panel into a dedicated, always-on Home Assistant controller that runs entirely on your local network. You can choose between two presets:

- **E-paper (reTerminal E1003)**: Low power, glare-free, and connects via the ESPHome native API.
- **Color touch (SenseCAP Indicator)**: Higher information density, richer touch controls, and connects via the ESPHome native API.

## Key Benefits

| Benefit | Details |
|---------|---------|
| Eye-Friendly Ambient Display | Reads like paper with no glare, so it sits naturally in bedrooms or living spaces without lighting up the room at night |
| Ultra-Low Power Consumption | Draws power only when refreshing the screen, and keeps showing the last image even if power drops |
| Native Local Integration | Talks directly to Home Assistant using the ESPHome native API to trigger actions locally, without cloud dependence or custom automation scripts |
| Two Screen Choices | Pick the e-paper option for quiet, always-on spaces like bedrooms, or the color panel when you need dense status views and richer touch |
| Rapid One-Click Deployment | Flash the firmware and register the device in Home Assistant without manual compiling or editing YAML files |

## Where to use it

| Scenario | How it helps |
|----------|--------------|
| Bedside Dimming Control | Adjust light levels directly from the nightstand without a glaring screen waking you up |
| Entryway Scene Switch | Tap one button by the front door to turn everything off when leaving, or bring the house to life when you return |
| Living Room Atmosphere | Switch between cinema, reading, and entertaining modes using dedicated on-screen touch zones |

## Usage Notes

### Required Hardware

| Device | Description | Required |
|--------|-------------|----------|
| reTerminal E1003 | Touch e-paper panel terminal (ESP32-S3) — E-paper preset | ✓ One of the two |
| SenseCAP Indicator (D1 / D1S / D1Pro / D1L) | Color touch panel (ESP32-S3) — Color preset | ✓ One of the two |
| USB Data Cable | For initial firmware flashing and panel power supply | ✓ Required |
| Linux Host / Raspberry Pi | Host running Home Assistant (reusable existing HA instance; local Docker deployment requires Linux host network) | ✓ Required |

### Network Requirements

- The panel connects via 2.4 GHz Wi-Fi (5 GHz only networks are not supported).
- The setup computer, panel, and Home Assistant host must reside on the same reachable local area network.
