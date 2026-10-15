# E1003 unified deployment technical demo

Connect E1003 and enter settings in one desktop App form. The App checks the installed firmware, skips installation when it matches, or installs the shared precompiled image when needed, then saves network settings, a device-specific key and a light-button binding. No flash-mode choice, compilation or `secrets.yaml` editing is needed.

**Verified:** The packaged backend and shared frontend completed matching-firmware skip, a 65-second save wait, reset and encrypted readback. A controlled installation test also performed real writing and verification: only the first identity probe was forced to return no response, and the device retained its key and binding. This did not test a factory-blank device. New Wi-Fi, real Home Assistant light control and display synchronization still need acceptance.

## What the demo provides

- One precompiled image with a fixed clock, temperature/humidity and lighting-card layout.
- A separate connection key for each device and a light binding retained after reset; changing the binding requires no rebuild.
- Save progress, encrypted readback results and a key-copy button inside the App.

The lighting card's on/off and four brightness buttons share one setting: “Light controlled by the buttons.” Saving it proves that the binding persists; test actual light control separately in Home Assistant.

## Product and connection layout

![Official reTerminal E1003 product photo with Seeed's demonstration interface](gallery/e1003-product-official.jpg)

This E1003 photograph comes from Seeed's official product page. Its screen shows the stock demonstration interface, rather than this firmware's layout or a hardware acceptance result.

![Generated architecture illustration: desktop App configures E1003 over USB; Home Assistant validation pending](gallery/e1003-architecture-cover.png)

USB handles device identification and network setup. Once the panel is connected, the App writes the light binding and verifies persistence over an encrypted LAN connection. Home Assistant connects over the LAN in the subsequent test. This generated architecture illustration uses schematic device and App appearances; real light control and state synchronization still need acceptance.

## How to test

1. Connect E1003 over USB. In the single App form, select the port and enter “Light controlled by the buttons,” such as `light.bedroom`. Enter Wi-Fi for first connection; leave it blank only when this App has the device record and the panel is connected.
2. Click **Deploy and save settings**. The App checks project identity, version and hardware. A match skips flashing; otherwise the image is verified before installation. There is no preset switch or manual flash decision.
3. Keep power connected through configuration, the 65-second save wait, reset and encrypted readback. Copy the key inside the App, confirm the device and allow actions in Home Assistant, then test actual light control separately.

## Interfaces and requirements

USB uses Improv Serial for network setup. The LAN connection uses encrypted ESPHome native API (TCP 6053) for configuration and readback. No MQTT or device web server is required. The computer, panel and Home Assistant must be mutually reachable; light-control testing requires an existing dimmable light entity.

This demo supports only the current E1003 layout and USB updates, with no OTA. Display state and brightness synchronization for arbitrary lights still need a HA Blueprint or adapter.

> This technical demo candidate is disabled. The unified flow requires an App with automatic firmware checks (contract 12). Public contract synchronization and a public firmware download are pending; this candidate cannot yet execute installation and configuration directly.

The native configuration implementation is in [App draft PR #162](https://github.com/suharvest/app_collaboration/pull/162).
