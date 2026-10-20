# E1003 Light Panel Setup Demo

Connect reTerminal E1003 to your computer via USB and specify the Home Assistant dimmable light you want to control. The App checks the device, installs prebuilt firmware when needed, and saves light bindings and network settings.

Everything is handled in a single form, with no firmware compilation, configuration editing, or API key setup required.

## What it does and what you need

Bind touch controls on the E1003 panel to a dimmable light (`light.*`) in Home Assistant.

Before starting, make sure you have:

- A reTerminal E1003 panel and a USB data cable.
- A computer running the App, and a Home Assistant instance on the same reachable LAN.
- The entity ID of your dimmable light (such as `light.bedroom`).

## Getting started

1. Connect the E1003 to your computer with the USB cable and select its serial port in the App.
2. Enter the light entity ID. Enter your 2.4 GHz Wi-Fi details if setting up networking (leave blank if the device is already connected).
3. Click **Save settings**. The App automatically checks firmware, saves settings, and verifies after reboot.
4. Once verified, follow the on-screen instructions to add the ESPHome device in Home Assistant and enable action execution.

> **Functional note**: Only five touch areas have actions defined: on/off and 25%, 50%, 75%, and 100% brightness. Other screen graphics are static. For hardware acceptance, install firmware 0.2.1 on a real E1003, tap each of the five areas, confirm the Home Assistant light changes, then change the light from Home Assistant and confirm the panel display updates.

<details>
<summary>Technical details and verification status</summary>
<p>The reference firmware is based on 0.2.1 and uses plaintext native API (TCP 6053). It does not use API encryption or key copying, requires no MQTT or device web server, and supports USB updates only.</p>
<p>Software builds and UI checks have passed. Hardware acceptance remains pending. The hardware acceptance procedure covers the 0.2.1 upload, all five touch actions, Home Assistant state changes, and display updates after an external light change. E-paper display persistence when unpowered is normal and does not indicate touch circuit power.</p>
<p>The solution is configured with public CDN firmware download and supports one-click USB flashing. Normal operation requires Home Assistant network reachability; display state and brightness synchronization for arbitrary lights still require a Home Assistant Blueprint or adapter.</p>
</details>
