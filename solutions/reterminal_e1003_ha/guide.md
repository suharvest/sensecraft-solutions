## Preset: Install and set up {#usb_candidate}

For local testing, follow **install firmware → connect and set buttons → test in Home Assistant**.
The App currently handles USB installation; the coordinating session uses the setup client for the remaining settings. The formal candidate is disabled.

## Step 1: Install panel firmware {#flash_panel type=manual required=true config=devices/review_flash.yaml}

Choose the light first, then connect the panel. The firmware is precompiled; no compilation or configuration-file editing is needed.
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

Write settings after installation. The setup client currently handles these three values; the App has no corresponding form yet.

| Setting | What to enter |
| --- | --- |
| Wi-Fi name | The network the panel will join |
| Wi-Fi password | The password for that network |
| Light controlled by the buttons | Paste the light's entity ID, such as `light.bedroom`; on/off and all four brightness buttons share this light |

Keep power connected for at least 65 seconds after writing settings, then reset and verify they remain. The client generates a key during initial setup and reuses it afterward; you do not enter one here.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Light entity ID unknown | Find the light in Home Assistant's entity list and copy its ID starting with `light.` |
| Unsure whether settings saved | Wait 65 seconds, reset and read them back; immediate readback only confirms the live setting |

## Step 3: Enable control in Home Assistant {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

1. Confirm the discovered ESPHome device. If it is not discovered, add it manually using the device IP and port `6053`.
2. Enter the **device connection key** supplied by the setup client.
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
Real HA control and display synchronization still need acceptance; installation success does not complete the whole solution.
