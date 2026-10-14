# Put Home Assistant controls on E1003

The fixed layout includes a clock, temperature and humidity, and a lighting card.
Choose the light for that card once; its on/off and four brightness buttons share the setting.

> Local testing now has installation and configuration entries: open the settings form from the App to change the light controlled by the buttons, without manual commands. The formal solution remains disabled. Real HA control, new-network setup through this form and display synchronization still need acceptance.

## What to set

| Setting | Purpose |
| --- | --- |
| Wi-Fi name and password (optional) | Leave blank to retain an existing connection; enter them for initial setup or a network change |
| Light controlled by the buttons | Copy the light's entity ID from Home Assistant, such as `light.bedroom` |

The device connection key is generated during initial setup and reused afterward. Select the form’s local copy option when you need to paste it into Home Assistant. Installation uses precompiled firmware; no configuration-file editing or compilation is needed.

## Where to use it

- At the bedside, check the time and use the lighting card to switch or dim the light.
- By your desk, check temperature and humidity and operate workspace lighting.

## Before you start

- Use reTerminal E1003 with the current fixed layout and a dimmable light already added to Home Assistant.
- Keep the setup computer, panel and Home Assistant on the same reachable LAN.
- The panel uses the ESPHome native API, with no MQTT or device web server required.
- Installation and updates use USB; wireless updates (OTA) are not supported.
