## Preset: USB integration review {#usb_candidate}

## Step 1: Review USB firmware {#flash_panel type=manual required=true config=devices/review_flash.yaml}

**Blocked in this source candidate:** no public firmware resource exists.
A maintainer can stage the pinned local image using
[the resource instructions](assets/firmware/README.md). Only that separate
local review copy replaces this step with `esp32_usb`; the candidate stays
disabled. This step does not flash anything in the source package.

### Prerequisites

Use the E1003 and the existing fixed layout only. Close serial monitors and
coordinate exclusive device access before any hardware test. Select the actual
port; VID/PID `1a86:7522` is a hint, not proof of device identity. The reviewed
payload writes the factory image at 0x0, at 115200 baud, with full-chip erase
disabled. Do not enable erase during a normal USB update.

### Wiring

1. Connect the E1003 carrier USB-UART port to the computer with a data cable.
2. Keep stable USB power during flashing and later configuration saving.

### Troubleshooting

| Issue | Action |
| --- | --- |
| No flash control in this candidate | Maintainer must stage the exact local factory image; no download URL is available |
| Port is busy | Coordinate with its owner and close the serial monitor; do not take another session's port |
| Device does not restart on reopen | Adapter must perform an explicit WCH reset and allow ten seconds for boot |
| Update offers full-chip erase | Keep it disabled; stop if the engine cannot preserve that choice |

## Step 2: Review App configuration dependency {#configure_panel type=manual required=true config=devices/review_setup.yaml}

**Blocked:** current content cannot write Wi-Fi, an API key or the light target.
This manual review marker does not perform provisioning. Do not count a manual
step completion as device setup success. Do not run a maintainer script as an
end-user workaround.

The future App adapter must collect Wi-Fi SSID/password, generate and privately
save a separate API key for this device, then write/read back the pasted
`light.xxx` target using the encrypted native API. It must verify device
identity, retry key activation safely and show a saving countdown of at least
65 seconds after the last target write before permitting a power-off check.
No Wi-Fi/password/target form is supplied until these writes exist.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Wi-Fi fails | Adapter must report the Improv error and allow correction without losing the saved key record |
| Initial key setup expires | Reset and retry within the ten-minute setup window, reusing the private recovery record |
| Key already installed | Reconnect with the saved key; never replace it with a newly generated key on retry |
| Target readback matches | This proves the live value only; wait for saving, then verify again after reset |

## Step 3: Check Home Assistant acceptance {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

**Acceptance checklist for after the adapter is implemented.** This is a manual
verify step, not automated proof. The current disabled candidate cannot finish
the preceding setup.

1. In HA, confirm the discovered ESPHome device. If discovery is unavailable,
   add ESPHome using the verified device IP and TCP 6053. The Improv response
   URL contains address metadata; it is not a device web page.
2. Copy the per-device encryption key using an explicit private App reveal/copy
   action into the HA integration. Do not paste it into logs or reports.
3. Enable **Allow the device to perform Home Assistant actions** in the ESPHome
   integration options. Paste an existing dimmable `light.xxx` as the target
   through the future App adapter.
4. After the save interval, reset and check the same key and target. Test touch
   on/off and dimming against the real light, then close App and repeat.
5. Keep display synchronization marked incomplete until a HA Blueprint/adapter
   passes state, brightness-only changes, target A→B, HA restart, panel reconnect
   and unavailable-target tests. The old fixed-target example is insufficient.

### Troubleshooting

| Issue | Action |
| --- | --- |
| HA cannot reach the panel | Check LAN reachability and TCP 6053; use the verified IP if multicast discovery is unavailable |
| Touch has no effect | Check the target exists, dimming support, integration connection and action permission |
| Display follows an old light | Dynamic state push is pending; changing the control target does not implement display synchronization |
| Lost the private key record | Stop and use an explicitly authorized recovery process; normal reset does not erase the installed key |

### Deployment Complete

This candidate is ready for content review only. Flash write verification,
encrypted API verification and HA/light/display acceptance are separate results.
The manual renderer can mark a checklist complete without performing I/O;
keep the solution disabled until the adapter and acceptance gates pass.
