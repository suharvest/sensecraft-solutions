## Preset: Install and set up {#usb_candidate}

For local testing, follow **install firmware → connect and set buttons → test in Home Assistant**.
The local App configuration entry opens an editable settings page; no manual command is needed. The formal candidate is disabled.

## Step 1: Install panel firmware {#flash_panel type=manual required=true config=devices/review_flash.yaml}

If the panel firmware is already installed, go straight to Step 2; no reflash is needed. Initial installation uses precompiled firmware, with no compilation or configuration-file editing.
For local testing, use the imported test solution. The formal candidate does not bundle a ready-to-deploy firmware resource.

### Prerequisites

Have a dimmable light already added to Home Assistant and copy its entity ID.
Keep the setup computer, panel and Home Assistant on the same reachable LAN.

### Wiring

1. Connect the E1003 carrier's USB-UART port to the computer with a data cable. Close tools using that port.
2. Select the connected panel's port in the App and run installation. Keep full-chip erase off and maintain stable power.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Port not found | Check the data cable and close tools using the port |
| No installation control | Confirm you opened the imported local test solution |

## Step 2: Connect and set buttons {#configure_panel type=manual required=true config=devices/review_setup.yaml}

Open the local settings page from the App configuration entry, select the configuration preset and fill in the form. Submitting runs the adapter to write settings to the device.

| Setting | What to enter |
| --- | --- |
| USB port | Select the connected E1003 |
| Light controlled by the buttons | Paste the light's entity ID, such as `light.bedroom`; on/off and all four brightness buttons share this light |
| Wi-Fi name (optional) | Leave blank if connected; enter it for initial setup or a network change |
| Wi-Fi password (optional) | The password for the selected network |
| Copy device connection key (optional) | Copy locally after success for use in Home Assistant |

Keep USB connected after submitting. The adapter waits at least 65 seconds, resets the panel and performs encrypted readback before reporting success. It reuses a private key record or generates a key during initial setup; you do not enter one here.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Light entity ID unknown | Find the light in Home Assistant's entity list and copy its ID starting with `light.` |
| Unsure whether settings saved | Wait for configuration success; do not disconnect during saving or reset |

## Step 3: Enable control in Home Assistant {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

1. Confirm the discovered ESPHome device. If it is not discovered, add it manually using the device IP and port `6053`.
2. Select the form’s **device connection key** copy option, then paste it into Home Assistant after configuration succeeds.
3. Enable **Allow the device to perform Home Assistant actions**.
4. Test on/off and all four brightness buttons, then close the App and test again.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Cannot connect | Check the LAN, device IP and connection key |
| Light does not respond | Check the selected light, its dimming support and the action permission |
| Display does not follow the light | State and brightness synchronization still need a HA Blueprint or adapter; button binding alone does not synchronize the display |

### Deployment Complete

Confirm each result separately: firmware installed, settings retained after reset, and the real light responds to the buttons.
New-network setup through this form, real HA control and display synchronization still need acceptance; installation or configuration success does not complete the whole solution.
