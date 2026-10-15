## Preset: Deploy E1003 {#usb_candidate}

One form, one submission: **enter settings → automatic check and installation when needed → save and read back after reset**. No API key is required by default; encryption is optional.
These instructions require a contract 13 App. The formal candidate remains disabled pending the public contract and firmware download; its manual review steps do not write to devices.

## Step 1: Connect and enter settings {#flash_panel type=manual required=true config=devices/review_flash.yaml}

Use the single “Deploy E1003” entry. The App decides whether installation is needed.

### Prerequisites

Have a compatible test App, USB data cable and HA light entity ID. Keep the computer, panel and HA on the same reachable LAN. Prepare Wi-Fi credentials for first connection.

### Wiring

1. Connect the carrier's USB-UART port to the computer and close tools using it.
2. Enter the settings below in the embedded App form; deployment continues in this same form.

| Setting | What to enter |
| --- | --- |
| USB port | Select the connected E1003 |
| Light controlled by the buttons | Paste an entity ID such as `light.bedroom`; all five lighting touch zones share it |
| Wi-Fi name | Leave blank to reuse a saved network without a prior local key record; enter it for first connection |
| Wi-Fi password | Enter the selected network’s password; input is masked. Leave blank when reusing Wi-Fi |
| Enable API encryption (optional) | Unchecked by default for direct use without an API key; when selected, the App generates or reuses a device-specific key |

### Troubleshooting

| Issue | Action |
| --- | --- |
| Port not found | Check the data cable and close tools using the port |
| Optional encryption setting missing | Use a test App with contract 13; the formal candidate has no execution entry yet |

## Step 2: Deploy and save settings {#configure_panel type=manual required=true config=devices/review_setup.yaml}

Click **Deploy and save settings** and keep USB power connected. The App automatically:

1. Checks project, version, hardware and name. A 0.2.0 match skips flashing; otherwise it verifies image size/SHA, installs and checks identity again. No full-chip erase is used; NVS is preserved.
2. Reuses or configures Wi-Fi and writes the light binding in the selected mode. No API key is required by default. An encrypted device needs its original recovery key to authorize clearing encryption; the record's key is removed only after keyless reconnect succeeds.
3. Waits at least 65 seconds, resets and reads back in the selected mode. **Copy encryption key for Home Assistant** appears only after encrypted configuration completes.

An inaccessible port, wrong hardware or failed verification stops the operation. Default mode does not require a prior local record to reuse Wi-Fi; an already encrypted device still needs its original key for switching modes.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Image missing or invalid | Use a complete test package; do not substitute a different build with the same version |
| Encrypted device cannot switch to keyless mode | Use the App holding the original key; do not erase NVS or delete its recovery record to bypass authorization |
| Unsure whether settings saved | Wait for reset and readback; keep power connected during installation, saving and reset |

## Step 3: Verify light control in Home Assistant {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

Real HA control and physical touch still need acceptance.

1. Confirm the discovered ESPHome device, or add its IP and port `6053` if needed.
2. Use no API key in default mode. Only when encryption was enabled, copy the key from the successful App setup into HA.
3. Allow the device to perform Home Assistant actions.
4. Test the five zones: on/off and 25%, 50%, 75% and 100% brightness, then close the App and repeat. Other graphics have no click binding.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Cannot connect | Check the network, address and selected encryption mode; encrypted mode also needs the correct key |
| Touch or light does not respond | Check the five zones, light entity and action permission. Coordinates are unchanged; no touch fix is claimed |
| Display does not follow the light | Dynamic state and brightness synchronization still need a HA Blueprint or adapter |

### Deployment Complete

Record firmware checks, installation, mode transition, reset readback and actual light control separately. The packaged backend and shared frontend upgraded 0.1.0 to 0.2.0, reused Wi-Fi, cleared the old key, saved and completed keyless readback. This was not a native-window submission test. The check after ten minutes, new Wi-Fi through the form, touch, HA control and display synchronization remain pending.
