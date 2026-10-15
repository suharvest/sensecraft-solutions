## Preset: Install and set up {#usb_candidate}

Test in this order: **install firmware → save configuration inside the App → verify light control in Home Assistant**.
The configuration instructions require a desktop App with the embedded E1003 form (contract 11). The formal candidate remains disabled pending public contract and firmware resources; its manual steps are review instructions and do not write to devices.

## Step 1: Install panel firmware {#flash_panel type=manual required=true config=devices/review_flash.yaml}

Initial installation uses one precompiled image, with no configuration-file editing or compilation. If this image is already installed, go straight to Step 2.

### Prerequisites

Use a compatible local test App and verified firmware resource. Copy the entity ID of an existing dimmable light in Home Assistant. Keep the computer, panel and Home Assistant on the same reachable LAN.

### Wiring

1. Connect the E1003 carrier's USB-UART port to the computer with a data cable. Close tools using that port.
2. Select the panel port in the App and install. Keep full-chip erase off and power stable; installation passes only after write verification.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Port not found | Check the data cable and close tools using the port |
| No installation control | The formal candidate has no installation entry yet; use the prepared package for local testing |

## Step 2: Save configuration inside the App {#configure_panel type=manual required=true config=devices/review_setup.yaml}

Fill in the embedded E1003 form on the App deployment page. No external webpage or script path selection is needed.

| Setting | What to enter |
| --- | --- |
| USB port | Select the connected E1003 |
| Light controlled by the buttons | Paste the light's entity ID, such as `light.bedroom`; on/off and all four brightness buttons share this light |
| Wi-Fi name | Required for first connection; leave blank only when this App has the device record and the device is already connected |
| Wi-Fi password | Enter the selected network's password; input is masked |

Click **Save device configuration** and keep USB connected. The App checks identity, generates or reuses a device-specific connection key, writes the binding, waits at least 65 seconds, resets and performs encrypted readback. Configuration passes only after all checks succeed. You do not enter a key; a copy button becomes available after success.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Light entity ID unknown | Copy the light's ID starting with `light.` from Home Assistant's entity list |
| Unsure whether settings saved | Wait for reset and encrypted readback; keep power connected during saving |
| Configured device has no key record | Return to the App that saved its record; do not erase configuration to attempt recovery |

## Step 3: Verify light control in Home Assistant {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

This step requires a real Home Assistant instance and light; hardware acceptance is still pending.

1. Confirm the discovered ESPHome device. If needed, add it manually using the device IP and port `6053`.
2. Click **Copy encryption key for Home Assistant** in the App configuration panel and paste it into Home Assistant.
3. Enable **Allow the device to perform Home Assistant actions**.
4. Test on/off and 25%, 50%, 75% and 100% brightness, then close the App and repeat. Record whether the light actually responds.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Cannot connect | Check the LAN, device IP and connection key |
| Light does not respond | Check the chosen light, dimming support and action permission |
| Display does not follow the light | Dynamic state and brightness synchronization still need a HA Blueprint or adapter; hardware acceptance is pending |

### Deployment Complete

Record installation verification, persistence after reset and real light control separately. The first two have passed; new Wi-Fi through this form, real HA control and dynamic display synchronization still need hardware acceptance. Configuration success does not verify light control.
