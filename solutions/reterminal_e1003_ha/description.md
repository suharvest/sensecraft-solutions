# A local Home Assistant light panel

**Integration candidate — disabled.** This content prepares a USB deployment
for reTerminal E1003 with the existing fixed display/touch layout. The intended
flow uses one precompiled image: enter Wi-Fi settings in App, bind a `light.xxx`
entity, then confirm the device and action permission in Home Assistant (HA).
Users should not edit `secrets.yaml`, install ESPHome, compile firmware, or run
maintainer scripts. App integration is still required to deliver that flow.

## What this candidate provides

| Item | Current status |
| --- | --- |
| One firmware for the same hardware/layout | Built without personal Wi-Fi credentials or a static API key |
| USB Wi-Fi, unique API key and target configuration | Verified by the firmware maintainer client on one panel; App adapter pending |
| Configuration after reboot / USB update | Two resets and same-image, same-partition USB overwrite verified in the firmware project |
| Light control and matching display state | Real HA light/touch acceptance pending; arbitrary target state/brightness needs a Blueprint or adapter |

## Intended use

An existing HA installation with one dimmable light, for example an office or
bedside light. The setup computer, E1003 and HA must share a reachable LAN.
The device uses the encrypted ESPHome native API (TCP 6053); it has no MQTT
dependency or device web server. App is intended for setup and should not be
required to keep the panel running.

## Expected result and limits

After the remaining integration work, the panel should control the selected
light and display its state and brightness. **Changing the runtime target
currently configures control binding only. Automatic display synchronization
for arbitrary targets has not been delivered.** HA discovery, real-light
control, display/touch behavior, two-panel isolation and App deployment still
need acceptance evidence.

This prototype is USB-only. OTA is disabled because the pinned OTA schema does
not support inheriting the runtime API key. No unauthenticated OTA workaround
is permitted. Runtime text changes require at least 65 seconds before removing
power, followed by a persistence check. The candidate has no public firmware
download; maintainers can stage a hash-checked local review package using the
[resource instructions](assets/firmware/README.md).
