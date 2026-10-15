## Preset: Deploy E1003 {#usb_candidate}

Use one form and submit once: **enter settings → automatic check and installation when needed → save and verify after reset**, then test light control separately in Home Assistant.
These instructions describe the unified App flow (contract 12). The formal candidate remains disabled pending public contract and firmware resources; its three manual review steps explain the flow and do not write to devices.

## Step 1: Connect and enter settings {#flash_panel type=manual required=true config=devices/review_flash.yaml}

Use the single “Deploy E1003” entry. The App decides whether firmware installation is needed.

### Prerequisites

Have a compatible test App, USB data cable and the entity ID of a dimmable Home Assistant light. Keep the computer, panel and Home Assistant on the same reachable LAN. Prepare Wi-Fi credentials for first connection.

### Wiring

1. Connect the E1003 carrier's USB-UART port to the computer with a data cable. Close tools using the port.
2. In the embedded App form, select the device port and enter the settings below. Checks, installation and saving continue in this same form.

| Setting | What to enter |
| --- | --- |
| USB port | Select the connected E1003 |
| Light controlled by the buttons | Paste the light's entity ID, such as `light.bedroom`; on/off and all four brightness buttons share this light |
| Wi-Fi name | Required for first connection; leave blank only when this App has the device record and the panel is connected |
| Wi-Fi password | Enter the selected network's password; input is masked |

### Troubleshooting

| Issue | Action |
| --- | --- |
| Port not found | Check the data cable and close tools using the port |
| Unified form missing | Use a test App with the contract 12 unified flow; the formal candidate has no execution entry yet |

## Step 2: Deploy and save settings {#configure_panel type=manual required=true config=devices/review_setup.yaml}

Click **Deploy and save settings** in the same form and keep USB connected. The App automatically:

1. Checks firmware project identity, version, hardware and device name; a complete match skips flashing.
2. When installation is needed, verifies the precompiled image's size and SHA-256, writes and verifies it, then checks firmware identity again. Full-chip erase is off and the configuration partition is preserved.
3. Generates or reuses the device-specific key, writes settings, waits at least 65 seconds, resets and performs encrypted readback. Saving succeeds only after these checks pass; key copying is then available.

An inaccessible port or an explicitly different hardware type stops the operation. Failed checks or installation prevent configuration from continuing. Keep power connected, resolve the reported issue and retry.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Image missing or invalid | Use a test package with the verified image; do not substitute another build with the same version |
| Unsure whether settings saved | Wait for reset and encrypted readback; keep power connected during installation, saving and reset |
| Configured device has no key record | Return to the App that saved its record; do not erase configuration to attempt recovery |

## Step 3: Verify light control in Home Assistant {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

This step requires a real Home Assistant instance and light; hardware acceptance is still pending.

1. Confirm the discovered ESPHome device. If needed, add it manually using the device IP and port `6053`.
2. Click **Copy encryption key for Home Assistant** in the App panel and paste it into Home Assistant.
3. Enable **Allow the device to perform Home Assistant actions**.
4. Test on/off and 25%, 50%, 75% and 100% brightness, then close the App and repeat. Record whether the light actually responds.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Cannot connect | Check the LAN, device IP and connection key |
| Light does not respond | Check the chosen light, dimming support and action permission |
| Display does not follow the light | Dynamic state and brightness synchronization still need a HA Blueprint or adapter; hardware acceptance is pending |

### Deployment Complete

Record the automatic decision, installation or skip, configuration persistence and real light control separately. The packaged backend and shared frontend completed matching-firmware skip, a 65-second save wait, reset and encrypted readback. In the controlled installation test, only the first probe was forced to return no response; real writing, verification, a second identity check and retention of the key/binding then passed. Factory-blank devices, new Wi-Fi through the form, real HA control and dynamic display synchronization still need acceptance.
