# Put Home Assistant controls on E1003

The fixed layout includes a clock, temperature and humidity, and a lighting card.
Choose the light for that card once; its on/off and four brightness buttons share the setting.

> Local integration testing: the App can install the panel firmware; the setup client handles networking and button settings. The formal solution remains disabled. Display state and brightness synchronization still need integration.

## What to set

| Setting | Purpose |
| --- | --- |
| Wi-Fi name and password | Connect the panel to your LAN |
| Light controlled by the buttons | Copy the light's entity ID from Home Assistant, such as `light.bedroom` |

The client generates the device connection key during initial setup. Copy it when adding the panel to Home Assistant. Installation uses precompiled firmware; no configuration-file editing or compilation is needed.

## Where to use it

- At the bedside, check the time and use the lighting card to switch or dim the light.
- By your desk, check temperature and humidity and operate workspace lighting.

## Before you start

- Use reTerminal E1003 with the current fixed layout and a dimmable light already added to Home Assistant.
- Keep the setup computer, panel and Home Assistant on the same reachable LAN.
- The panel uses the ESPHome native API, with no MQTT or device web server required.
- Installation and updates use USB; wireless updates (OTA) are not supported.
