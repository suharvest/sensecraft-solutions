# E1003 unified deployment technical demo

Select the device and enter light settings in one desktop App form. The intended flow checks firmware, installs 0.2.1 when needed and saves configuration. **The reference firmware uses plaintext-only API access, with no encryption option.** Saved Wi-Fi can be reused without a prior local key record. No compilation or `secrets.yaml` editing is needed.

**Current status:** 0.2.1 will remove compiled API encryption support. The App removes the encryption checkbox and all key-copy controls, requiring contract 14. Compilation and hardware verification are in progress; the new image size, SHA and final evidence are pending. The 0.2.0 keyless results are transitional history and do not prove continued keyless operation.

## What the demo provides

- One precompiled image with a fixed clock, temperature/humidity and lighting-card layout.
- Intended configuration and readback without an API key; no API key generation, entry or copying.
- A light binding retained after reset and App progress for checks, installation and saving.

The firmware defines only five touch zones: light on/off and 25%, 50%, 75% and 100% brightness, sharing “Light controlled by the buttons.” Other graphics have no click binding. Physical touch and real light control have not passed acceptance.

## Product and connection layout

![Official reTerminal E1003 product photo with Seeed's demonstration interface](gallery/e1003-product-official.jpg)

This photograph comes from Seeed's official product page. Its stock screen is not this firmware's layout or a hardware acceptance result.

![Generated architecture illustration: USB setup and LAN connectivity, with a superseded device-key element](gallery/e1003-architecture-cover.png)

USB handles device identification and network setup; the App writes and reads the light binding over the LAN. **Device key is a superseded design element, absent from the 0.2.1 reference firmware**; the cover awaits an update. This is a generated illustration; HA control and state synchronization still need acceptance.

## How to test

1. Connect USB, select the port in the App and enter “Light controlled by the buttons,” such as `light.bedroom`. Leave Wi-Fi blank to reuse a saved network; enter credentials for first connection.
2. Once final resources and the compatible App are ready, click **Deploy and save settings**, with no encryption choice or key input. The App checks project identity, version and hardware, skipping a match or verifying the image before installation.
3. Keep power connected through the 65-second save wait, reset and readback. Confirm the device in Home Assistant without an API key; no key copying is needed. Allow HA actions, then test the five touch zones separately.

## Interfaces and requirements

Uses Improv Serial and ESPHome native API (TCP 6053), with no MQTT or device web server. The 0.2.1 reference design uses plaintext-only API access. The computer, device and HA must share a reachable LAN.

Supports only the current E1003 layout and USB updates, with no OTA. State and brightness synchronization for arbitrary lights still need a HA Blueprint or adapter.

> This is the pending 0.2.1 / contract 14 design; the formal candidate remains disabled. The manifest still pins historical 0.2.0 resources, not the final 0.2.1 artifact. New size/SHA, acceptance evidence and a public download are pending. Encryption remains in a separate developer entry, outside this reference firmware.

See [App draft PR #162](https://github.com/suharvest/app_collaboration/pull/162) for the native implementation.
