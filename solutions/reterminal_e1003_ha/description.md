# E1003 unified deployment technical demo

Select the device and enter light settings in one desktop App form. The intended flow checks firmware, installs 0.2.1 when needed and saves configuration. **The reference firmware uses plaintext-only API access, with no encryption option.** Saved Wi-Fi can be reused without a prior local key record. No compilation or `secrets.yaml` editing is needed.

**Current status:** 0.2.1 is built without API encryption support. The App removes encryption and key-copy controls, requiring contract 14. Software checks and shared-frontend screenshot review passed, but the WCH port disappeared before upload: 0.2.1 has not been flashed to hardware. Historical 0.2.0 results do not verify this release.

## What the demo provides

- One precompiled image with a fixed clock, temperature/humidity and lighting-card layout.
- Reference firmware with plaintext-only API access; no API key generation, entry or copying.
- A light binding retained after reset and App progress for checks, installation and saving.

The firmware defines only five touch zones: light on/off and 25%, 50%, 75% and 100% brightness, sharing “Light controlled by the buttons.” Other graphics have no click binding. Physical touch and real light control have not passed acceptance. An e-paper image remaining after power-off does not prove that the touch circuitry has power.

## Product and connection layout

![Official reTerminal E1003 product photo with Seeed's demonstration interface](gallery/e1003-product-official.jpg)

This photograph comes from Seeed's official product page. Its stock screen is not this firmware's layout or a hardware acceptance result.

![Generated architecture illustration: USB setup and LAN connectivity, with No API key](gallery/e1003-keyless-cover.png)

USB handles device identification and network setup; the App writes and reads the light binding over the LAN. **No API key describes the fixed plaintext design**, not completed hardware acceptance. This is a generated illustration; HA control and state synchronization still need acceptance.

## How to test

1. Connect USB, select the port in the App and enter “Light controlled by the buttons,” such as `light.bedroom`. Leave Wi-Fi blank to reuse a saved network; enter credentials for first connection.
2. Once final resources and the compatible App are ready, click **Deploy and save settings**, with no encryption choice or key input. The App checks project identity, version and hardware, skipping a match or verifying the image before installation.
3. Keep power connected through the 65-second save wait, reset and readback. Confirm the device in Home Assistant without an API key; no key copying is needed. Allow HA actions, then test the five touch zones separately.

## Interfaces and requirements

Uses Improv Serial and ESPHome native API (TCP 6053), with no MQTT or device web server. The 0.2.1 reference design uses plaintext-only API access. The computer, device and HA must share a reachable LAN.

Supports only the current E1003 layout and USB updates, with no OTA. State and brightness synchronization for arbitrary lights still need a HA Blueprint or adapter.

> The actual 0.2.1 artifact is now pinned; device upload has not begun. The formal candidate stays disabled pending public contract 14, compatible App distribution, a firmware download URL and hardware acceptance. Encryption remains in a separate developer entry, outside this reference firmware.

See [App draft PR #162](https://github.com/suharvest/app_collaboration/pull/162) for the native implementation.
