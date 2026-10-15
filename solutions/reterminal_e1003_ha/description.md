# E1003 precompiled firmware and runtime configuration demo

Test how one firmware image serves different E1003 panels: install over USB, then configure the network, a device-specific connection key and a light-button binding inside the desktop App. No compilation, `secrets.yaml` editing or maintainer scripts are needed.

**Verified:** App flashing, plus saving a light ID through the embedded form, waiting 65 seconds, resetting and reading it back over an encrypted connection. New Wi-Fi setup through this form, real Home Assistant light control and display synchronization still need hardware acceptance.

## What the demo provides

- One precompiled image with a fixed clock, temperature/humidity and lighting-card layout.
- A separate connection key for each device and a light binding retained after reset; changing the binding requires no rebuild.
- Save progress, encrypted readback results and a key-copy button inside the App.

The lighting card's on/off and four brightness buttons share one setting: “Light controlled by the buttons.” Saving it proves that the binding persists; test actual light control separately in Home Assistant.

## How to test

1. Install firmware over USB for first use; skip flashing if this image is already installed.
2. In the embedded App form, select the USB port and enter the light's entity ID, such as `light.bedroom`. Enter Wi-Fi for first connection; leave it blank only when this App has the device record and the device is already connected.
3. Save and keep power connected until reset and encrypted readback pass. Copy the key inside the App, confirm the device and allow actions in Home Assistant, then test the panel buttons.

## Interfaces and requirements

USB uses Improv Serial for network setup. The LAN connection uses encrypted ESPHome native API (TCP 6053) for configuration and readback. No MQTT or device web server is required. The computer, panel and Home Assistant must be mutually reachable; light-control testing requires an existing dimmable light entity.

This demo supports only the current E1003 layout and USB updates, with no OTA. Display state and brightness synchronization for arbitrary lights still need a HA Blueprint or adapter.

> This technical demo candidate is disabled. The embedded form has been tested in a local App build and requires an App containing this feature (contract 11). Public contract synchronization and a public firmware download are pending; this candidate cannot yet execute installation and configuration directly.

The native configuration implementation is in [App draft PR #162](https://github.com/suharvest/app_collaboration/pull/162).
