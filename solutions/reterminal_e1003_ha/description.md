# E1003 unified deployment technical demo

Select the device and enter light settings in one desktop App form. The App checks firmware, installs 0.2.0 when needed and saves configuration. **No API key is required by default; encryption is optional.** Saved Wi-Fi can be reused without a prior local key record. No compilation or `secrets.yaml` editing is needed.

**Verified:** The packaged backend and shared desktop frontend upgraded 0.1.0 to 0.2.0, reused Wi-Fi, cleared prior encryption, waited 65 seconds, reset and read the target without a key. This was not a native-window submission test. The check after ten minutes, new Wi-Fi through the form, physical touch, real HA control and display synchronization remain pending.

## What the demo provides

- One precompiled image with a fixed clock, temperature/humidity and lighting-card layout.
- Configuration and readback without an API key by default; optional encryption exposes key copying only after completion.
- A light binding retained after reset and App progress for checks, installation and saving.

The firmware defines only five touch zones: light on/off and 25%, 50%, 75% and 100% brightness, sharing “Light controlled by the buttons.” Other graphics have no click binding. Physical touch and real light control have not passed acceptance.

## Product and connection layout

![Official reTerminal E1003 product photo with Seeed's demonstration interface](gallery/e1003-product-official.jpg)

This photograph comes from Seeed's official product page. Its stock screen is not this firmware's layout or a hardware acceptance result.

![Generated architecture illustration: USB setup and LAN connectivity, with an optional device key](gallery/e1003-architecture-cover.png)

USB handles device identification and network setup; the App writes and reads the light binding over the LAN. **Device key is an optional encryption capability**, unused by default. This is a generated illustration; HA control and state synchronization still need acceptance.

## How to test

1. Connect USB, select the port in the App and enter “Light controlled by the buttons,” such as `light.bedroom`. Leave Wi-Fi blank to reuse a saved network; enter credentials for first connection.
2. Leave **Enable API encryption (optional)** unchecked and click **Deploy and save settings**. The App checks project identity, version and hardware, skipping a match or verifying the image before installation.
3. Keep power connected through the 65-second save wait, reset and readback. Confirm the device directly in Home Assistant in default mode; copy a key only when encryption was enabled. Allow HA actions, then test the five touch zones separately.

## Interfaces and requirements

Uses Improv Serial and ESPHome native API (TCP 6053), with no MQTT or device web server. API access is unencrypted by default with optional encryption. The computer, device and HA must share a reachable LAN.

Supports only the current E1003 layout and USB updates, with no OTA. State and brightness synchronization for arbitrary lights still need a HA Blueprint or adapter.

> The formal technical candidate remains disabled pending public contract 13 and a firmware download. The native window confirmed an unchecked encryption default and no key-copy button; the full upgrade/configuration evidence comes from the packaged backend and shared frontend.

See [App draft PR #162](https://github.com/suharvest/app_collaboration/pull/162) for the native implementation.
