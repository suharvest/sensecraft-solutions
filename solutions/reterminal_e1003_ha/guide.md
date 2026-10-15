## Preset: Configure E1003 {#usb_candidate}

Connect the E1003 panel via USB and specify the light to control. The App checks firmware, installs it when needed, and saves your settings.

> This solution candidate is currently in technical review and remains disabled. This manual review step does not write to hardware; full execution requires App contract synchronization and a public firmware URL.

## Step 1: Configure E1003 {#review_setup type=manual required=true verify=true config=devices/review_setup.yaml}

In a compatible test App, enter your settings, click **Save settings**, and wait for **Settings saved and verified**.

### Prerequisites

- A reTerminal E1003 panel and a USB data cable.
- A dimmable light already added to Home Assistant, with its entity ID ready (such as `light.bedroom`).
- The computer, E1003 panel, and Home Assistant on the same reachable LAN.

### Wiring

1. Connect the E1003 carrier's USB-UART port to your computer with the USB cable.
2. Select the device serial port in the App (click “Refresh” in the same row if it does not appear).

### Setup

1. **Enter the light to control**: In the “Light controlled by the buttons” field, enter the Home Assistant dimmable light entity ID (such as `light.bedroom`). Input is manual; the App does not automatically discover lights.
2. **Wi-Fi setup (optional)**: For first-time networking or network changes, enter the 2.4 GHz Wi-Fi SSID and password. If the device has previously connected to this Wi-Fi, leave both blank to reuse saved credentials (leaving them blank does not imply the App detected the network).
3. **Save and verify**: Click **Save settings**. The App verifies the firmware version, installs the prebuilt image if there is a mismatch, and writes the light bindings.
4. **Wait for completion**: After writing, the device reboots and verifies readback. Keep power connected for at least 65 seconds. Setup is complete only when the screen displays **Settings saved and verified** (do not disconnect while the countdown reaches zero or while showing “Restarting”).

<details>
<summary>Technical details and release dependencies</summary>
<p>Reference firmware 0.2.1 uses plaintext native API without API encryption options or key export. Public contract 5 currently provides only this manual review step; App contract 15 code is committed (a597ccad) pending public content schema synchronization.</p>
<p>Factory firmware size is 1,337,072 bytes with SHA-256 <code>23dae64ed8b79f05a423a2748b6b3e2f1369e96b80f0d16fd03deebb62609528</code>. Flashing uses 115200 baud, offset 0x0, no full-chip erase, and preserves NVS. Formal execution also requires a compatible App build and a public firmware download URL.</p>
<p>Current build, software, and UI checks passed; final 0.2.1 hardware upload, new Wi-Fi, upgrade migration, sustained plaintext operation, physical touch, real HA control, and display synchronization remain pending acceptance.</p>
</details>

### After setup

Proceed only after the App displays **Settings saved and verified**:

1. Note the **Device address** shown on the completion screen.
2. In Home Assistant, navigate to Settings → Devices & Services → Integrations, add an ESPHome device, and enter the device address (no API key required).
3. In the device options, check “Allow the device to perform Home Assistant actions”.
4. Test the on/off touch zone and the 25%, 50%, 75%, and 100% brightness zones. Close the App and retest.

> **Note**: Only these five touch zones have actions defined; other screen elements are static. Saved settings do not imply physical control or two-way display synchronization have completed acceptance.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Device serial port not found | Click Refresh; verify the USB cable supports data transfer; close other programs using the serial port |
| Setup or write failed | Check the displayed error message, resolve the issue, and retry; do not erase NVS |
| Saving or verification in progress | Keep the device powered and wait for the final verification status |
| Button or light does not respond | Confirm the light entity ID is correct and dimmable; ensure “Allow the device to perform Home Assistant actions” is enabled in Home Assistant |
