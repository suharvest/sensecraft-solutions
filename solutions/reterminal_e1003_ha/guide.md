## Preset: USB setup {#usb_candidate}

This candidate cannot yet be deployed through the App. The steps below describe
the planned setup flow. Until device configuration is integrated, these steps
cannot be executed directly.

## Step 1: Connect E1003 {#flash_panel type=manual required=true config=devices/review_flash.yaml}

USB firmware flashing is not yet available. Before connecting the device,
have a USB data cable ready and close any serial tools that might use the port.

### Prerequisites

Have a reTerminal E1003, a running Home Assistant instance, and a dimmable light.
The setup computer, E1003 panel, and Home Assistant must be on the same reachable local network.

### Wiring

1. Connect the USB-UART port on the E1003 carrier board to your computer using a USB data cable.
2. Keep power connected and stable while writing firmware and saving settings.

### Troubleshooting

| Issue | Solution |
| --- | --- |
| Device port not found | Make sure the USB cable supports data transfer, and close other apps using the serial port |
| Flashing options not showing | This feature is not integrated yet; the current candidate cannot be deployed directly |

## Step 2: Set Wi-Fi and light target {#configure_panel type=manual required=true config=devices/review_setup.yaml}

App configuration controls for this step are not yet available. Once integrated,
users will enter their Wi-Fi credentials and paste the target entity ID (such as `light.bedroom`).
Each panel will use its own encryption key.

After changing the light target, keep the device powered for at least 65 seconds
to allow settings to save before disconnecting power or resetting the panel.

### Troubleshooting

| Issue | Solution |
| --- | --- |
| Light entity ID unknown | Open the Entities list in Home Assistant, locate your light, and copy the ID starting with `light.` |
| Not sure if settings saved | Wait past the 65-second window, then reboot the device to verify the target persists; immediate readback does not guarantee flash storage |

## Step 3: Confirm the device in Home Assistant {#verify_ha type=manual required=true verify=true config=devices/review_ha.yaml}

Complete device setup before performing these verification steps.

1. Confirm the discovered ESPHome device in Home Assistant. If it does not appear automatically,
   add the ESPHome integration manually using the device IP and port `6053`.
2. Enter the panel's encryption key (the App control to reveal or copy this key is still pending integration).
3. In the ESPHome integration options, enable **Allow the device to perform Home Assistant actions**.
4. Test light toggling and dimming from the touch panel, then close the App and test again.

### Troubleshooting

| Issue | Solution |
| --- | --- |
| Home Assistant cannot connect | Check local network connectivity, and confirm the IP, port, and encryption key are correct |
| Touching the panel has no effect | Verify the entity ID, ensure the light supports dimming, and check that device action permissions are enabled |
| Display does not follow light state | State and brightness synchronization for arbitrary lights is not yet implemented and requires a HA Blueprint or adapter |

### Deployment Complete

Final acceptance will verify that settings persist after reboot, light control works
with the App closed, and the display accurately tracks the target light's state and brightness.
The current candidate cannot complete this deployment flow; checking off this list does not mean the device has been configured.
