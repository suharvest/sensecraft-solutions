# reTerminal E1003 Smart Home Control Panel

## What this solution does for you

Traditional smart home controls often require navigating mobile apps or looking at glaring LCD screens in dark rooms. This solution uses the reTerminal E1003 low-power e-paper display as an always-on ambient smart home control panel. Connected seamlessly to Home Assistant via the native ESPHome API, it gives you intuitive wall-mounted touch control for lights, stepped dimming, and whole-home automation scenes without cloud dependencies.

## Key Benefits

| Benefit | Details |
|---------|---------|
| Eye-Friendly Ambient Display | E-paper provides non-glare, paper-like reading that blends naturally into bedrooms and living spaces without dark-room glare |
| Ultra-Low Power Consumption | Power is consumed only during display refresh, with persistent image retention even on power loss |
| Native Local Integration | Integrates directly with Home Assistant via the ESPHome native API to invoke actions directly from on-device entities without manual automations or cloud dependencies |
| Rapid One-Click Deployment | Automated firmware flashing and HA registration with no manual code compilation or complex YAML editing |

## Where to use it

| Scenario | How it helps |
|----------|--------------|
| Bedside Dimming Control | Adjust light brightness gently in the dark without harsh screen backlights disturbing your sleep |
| Entryway Scene Switch | Trigger "Leave Home" (all off) or "Arrive Home" modes with a single tap by the front door |
| Living Room Atmosphere | Switch between cinema, reading, and entertaining presets with dedicated tactile touch zones |

## Usage Notes

### Required Hardware

| Device | Description | Required |
|--------|-------------|----------|
| reTerminal E1003 | Touch e-paper panel terminal (ESP32-S3) | ✓ Required |
| USB Data Cable | For initial firmware flashing and panel power supply | ✓ Required |
| Linux Host / Raspberry Pi | Host running Home Assistant (reusable existing HA instance; local Docker deployment requires Linux host network) | ✓ Required |

### Network Requirements

- The panel connects via 2.4 GHz Wi-Fi (5 GHz only networks are not supported).
- The setup computer, reTerminal E1003 panel, and Home Assistant host must reside on the same reachable local area network.
