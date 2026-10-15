## Preset: Deploy E1003 {#usb_candidate}

One form, one submission: **enter settings → automatic check and installation when needed → save and read back after reset**. The target 0.2.1 reference firmware is plaintext-only, with no encryption choice or key copying.
These instructions describe the pending 0.2.1 / contract 14 target flow; the new build and final evidence are not available yet. The formal candidate remains disabled pending the public contract and firmware download; its manual review steps do not write to devices.

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

### Troubleshooting

| Issue | Action |
| --- | --- |
| Port not found | Check the data cable and close tools using the port |
| Encryption or key-copy controls still appear | This is an older interface; the final contract 14 flow omits them and still needs acceptance |

## Step 2: Deploy and save settings {#configure_panel type=manual required=true config=devices/review_setup.yaml}

Click **Deploy and save settings** and keep USB power connected. The App automatically:

1. Checks project, version, hardware and name. Once final resources are synchronized, a 0.2.1 match skips flashing; otherwise it verifies image size/SHA, installs and checks identity again. No full-chip erase is used; NVS is preserved.
2. Reuses or configures Wi-Fi and writes the light binding through the plaintext-only API, without setting encryption. Migration from older firmware must follow the final 0.2.1 acceptance results.
3. Waits at least 65 seconds, resets and reads back without a key. No key-copy control is provided.

An inaccessible port, wrong hardware or failed verification stops the operation. The target flow does not ask users for a key; upgrading encrypted devices and handling their records still need final migration evidence.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Image missing or invalid | Use a complete test package; do not substitute a different build with the same version |
| An older encrypted device fails migration | Stop and check final upgrade evidence; do not erase NVS or delete recovery records yourself |
| Unsure whether settings saved | Wait for reset and readback; keep power connected during installation, saving and reset |

## Step 3: Verify light control in Home Assistant {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

Real HA control and physical touch still need acceptance.

1. Confirm the discovered ESPHome device, or add its IP and port `6053` if needed.
2. Connect without an API key; there is no key to copy or enter.
3. Allow the device to perform Home Assistant actions.
4. Test the five zones: on/off and 25%, 50%, 75% and 100% brightness, then close the App and repeat. Other graphics have no click binding.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Cannot connect | Check the network, address and firmware version; do not follow the older encryption instructions |
| Touch or light does not respond | Check the five zones, light entity and action permission. Coordinates are unchanged; no touch fix is claimed |
| Display does not follow the light | Dynamic state and brightness synchronization still need a HA Blueprint or adapter |

### Deployment Complete

Record checks, installation, saving, reset/keyless readback and real light control separately. The 0.2.1 build, upgrade, sustained keyless behavior and final App flow still need acceptance; transitional 0.2.0 results do not prove them. New Wi-Fi, touch, HA control and display synchronization remain pending.
