# E1003 Smart Control Panel Demo

Connect reTerminal E1003 to your computer via USB and integrate it into Home Assistant. The App flashes the factory ESPHome firmware, sets up or verifies your Home Assistant instance, and automatically registers the panel via the ESPHome integration.

Everything is handled in streamlined steps with no firmware compilation or manual YAML editing required.

## What it does and what you need

Flash and connect the E1003 smart touch panel to Home Assistant to control smart lights and scenes.

Before starting, make sure you have:

- A reTerminal E1003 panel and a USB data cable.
- A computer running the deployment engine / App, with Home Assistant reachable on the network.
- 2.4 GHz Wi-Fi credentials for connecting the panel.

## Getting started

1. Connect the E1003 to your computer with the USB cable and select its serial port in the installer.
2. Deploy the factory firmware to the E1003 panel.
3. Deploy Home Assistant (or automatically skip if already running).
4. Enter the E1003 IP address and Home Assistant credentials to automatically connect the panel to Home Assistant.
5. In Home Assistant, bind the panel's touch triggers to your target light (`light.*`) via Home Assistant automations.

> **Functional note**: The panel firmware exposes touch controls (on/off toggle and brightness levels). In Home Assistant, create an automation to trigger actions on your target light entity when panel controls are pressed.

<details>
<summary>Technical details and verification status</summary>
<p>The reference firmware is based on 0.2.1 and uses plaintext native API (TCP 6053). It does not use API encryption or key copying, requires no MQTT or device web server, and supports USB updates only.</p>
<p>Software builds and UI checks have passed. Hardware acceptance remains pending. The hardware acceptance procedure covers the 0.2.1 upload, all five touch actions, Home Assistant state changes, and display updates after an external light change. E-paper display persistence when unpowered is normal and does not indicate touch circuit power.</p>
<p>The solution is configured with public CDN firmware download and supports one-click USB flashing. Normal operation requires Home Assistant network reachability; display state and brightness synchronization for arbitrary lights still require a Home Assistant Blueprint or adapter.</p>
</details>
