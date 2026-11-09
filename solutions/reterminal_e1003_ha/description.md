# Smart Home Control Panel for Home Assistant

## What this solution does for you

Most smart home setups force you to unlock a phone or look at a bright LCD in the dark. This setup turns a wall panel into a dedicated, always-on Home Assistant controller that runs entirely on your local network. You can choose between three presets:

- **E-paper (reTerminal E1003)**: Low power, glare-free, and connects via the ESPHome native API.
- **Color touch (SenseCAP Indicator)**: Compact desktop square screen for sensor monitoring and touch controls via the ESPHome native API.
- **Flagship color touch (reTerminal D1001)**: High-performance dual-core ESP32-P4 with an 800x1280 MIPI-DSI wide-angle color screen, portrait and landscape flexibility, modern PocketJS UI engine, and built-in factory HA control panel for 60fps ultra-smooth dimming and scene switching.

## Key Benefits

| Benefit | Details |
|---------|---------|
| Eye-Friendly Ambient Display | E-paper reads like paper with no glare, sitting naturally in bedrooms without lighting up the room at night |
| Ultra-Low Power Consumption | E-paper draws power only when refreshing the screen and keeps showing the last image even if power drops |
| Native Local Integration | Communicates directly with Home Assistant over the local network to trigger actions with zero cloud dependency |
| Three Form Factors | Pick e-paper for quiet bedside spaces, Indicator for compact desktop sensing, or D1001 for high-traffic living room and entryway hubs |
| 60fps Smooth Animation | reTerminal D1001 leverages ESP32-P4 hardware 2D/DMA acceleration and PocketJS for fluid touch sliders and transitions |
| Portrait & Landscape Versatility | reTerminal D1001 hardware natively supports both orientations with the factory app calibrated for high-density home controls |
| Rapid One-Click Deployment | Flash the firmware and connect to Home Assistant without manual compiling or editing low-level driver configurations |

## Where to use it

| Scenario | How it helps |
|----------|--------------|
| Bedside Dimming Control | Adjust light levels directly from the nightstand without a glaring screen waking you up |
| Entryway Scene Switch | Tap one button by the front door to trigger "Away" mode or restore your favorite lighting and climate when returning |
| Central Living Room Hub | View whole-house status on the high-definition reTerminal D1001 screen with stepless dimming, multi-scene control, and live weather |

## Usage Notes

### Required Hardware

| Device | Description | Required |
|--------|-------------|----------|
| reTerminal E1003 | Touch e-paper panel terminal (ESP32-S3) — E-paper preset | ✓ One of the three |
| SenseCAP Indicator (D1 / D1S / D1Pro / D1L) | Color touch panel (ESP32-S3) — Desktop color preset | ✓ One of the three |
| reTerminal D1001 | 800x1280 flagship touch panel (ESP32-P4 + ESP32-C6) — Flagship color preset | ✓ One of the three |
| USB Data Cable | For initial firmware flashing and panel power supply (USB-C high-speed cable recommended for D1001) | ✓ Required |
| Linux Host / Raspberry Pi | Host running Home Assistant (reusable existing HA instance; local Docker deployment requires Linux host network) | ✓ Required |

### Network Requirements

- The panel connects via 2.4 GHz Wi-Fi (5 GHz only networks are not supported).
- The setup computer, panel, and Home Assistant host must reside on the same reachable local area network.
