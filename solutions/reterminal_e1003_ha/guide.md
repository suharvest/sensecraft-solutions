## Preset: Smart Home Wall Panel {#usb_candidate}

Connect the E1003 panel via USB and integrate it into Home Assistant. The installer downloads and flashes the panel firmware, sets up or connects to your Home Assistant host, and automatically links the panel for smart home control.

> Note: Ensure the reTerminal E1003 panel is connected via USB. The flashing step downloads and installs the 0.2.1 firmware directly from the CDN.

## Step 1: Install E1003 panel firmware {#e1003_usb type=esp32_usb required=true verify=true config=devices/e1003_usb.yaml}

Select your serial port, click **Deploy**, and wait for firmware installation and reboot verification to complete.

### Prerequisites

- A reTerminal E1003 panel and a USB data cable.
- The computer, E1003 panel, and Home Assistant on the same reachable LAN.

### Wiring

1. Connect the E1003 carrier's USB-UART port to your computer with the USB cable.
2. Select the device serial port in the App (click “Refresh” in the same row if it does not appear).

### Flashing

1. Select the serial port corresponding to the connected E1003 device.
2. Click **Install** / Deploy. The installer downloads the 0.2.1 factory firmware from the CDN and flashes it to the panel at 115200 baud.
3. Keep the device connected until flashing and post-deployment reboot verification complete.

<details>
<summary>Technical details and release dependencies</summary>
<p>Reference firmware 0.2.1 uses plaintext native API without API encryption options or key export.</p>
<p>Factory firmware size is 1,337,056 bytes with SHA-256 <code>472fea16c509b46ecb04d6636a8d8acbc05756ce02157d20fd40eaf483401291</code>. Flashing uses 115200 baud, offset 0x0, no full-chip erase, and preserves NVS.</p>
<p>Current build, software, and CDN publication checks passed; physical touch, real HA control, and display synchronization can be verified on real hardware.</p>
</details>

### After setup

1. **Network Provisioning**: After flashing, configure 2.4 GHz Wi-Fi credentials via Improv Serial over USB at 115200 baud, or connect to the fallback ESPHome hotspot via the Captive Portal page (5 GHz only networks are not supported). Once connected, the panel joins your LAN and obtains an IP address.
2. **Device Integration**: If Step 3 (automatic integration) was not executed, open Home Assistant, go to **Settings → Devices & Services → Integrations**, add ESPHome, and enter the panel IP address (Native API requires no key).
3. **Two-Step Light Binding (No Automations Needed)**: The firmware calls Home Assistant actions directly via the Native API, with the target light specified by the on-device configuration entity. No manual Home Assistant Automation rules are required:
   - **Step 1 (Grant Action Permissions)**: In Home Assistant's ESPHome integration, find the E1003 device card, click the options/gear icon, and enable **"Allow the device to perform Home Assistant actions"**;
   - **Step 2 (Assign Target Light ID)**: Under the E1003 device's configuration entities, locate the target light entity (`text.e1003_target_light`), and enter your target light entity ID (such as `light.living_room`). The panel firmware will directly control this target light.
4. **Physical Touch Verification**:
   - Tap the on/off touch zone (Toggle) on the panel to confirm the target light toggles in real time;
   - Tap the 25%, 50%, 75%, and 100% brightness zones to confirm smooth stepped dimming, completing the physical closed loop.

> **Note**: Only these five touch zones have actions defined; other screen elements are static ambient graphics.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Device serial port not found | Click Refresh; verify the USB cable supports data transfer; close other programs using the serial port |
| Setup or write failed | Check the displayed error message, resolve the issue, and retry; do not erase NVS |
| Saving or verification in progress | Keep the device powered and wait for the final verification status |
| Button or light does not respond | Confirm "Allow the device to perform Home Assistant actions" is enabled in ESPHome device settings; verify `text.e1003_target_light` contains a valid, existing light entity ID; ensure the panel is online on the same local network |

---

## Step 2: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/ha_host.yaml}

Deploy a Home Assistant instance on your local or remote Docker host. If Home Assistant is already running on port 8123, this step automatically detects it and skips.

> **Platform Constraint**: The Home Assistant container relies on native host networking (`network_mode: host`) for mDNS and LAN device discovery. **Local installation is supported on Linux hosts only**. On macOS or Windows environments, Docker Desktop cannot provide native host networking: please **uncheck this step to skip it**, or select `ha_remote` to deploy to an independent Linux host (such as a Raspberry Pi or reComputer), or reuse an existing Home Assistant instance on your network.

### Target {#ha_local type=local config=devices/ha_host.yaml}

Deploy Home Assistant on a local Linux machine using host network mode (Linux host only; skip on macOS/Windows).

### Target {#ha_remote type=remote config=devices/ha_host.yaml default=true}

Deploy Home Assistant on a remote host (e.g. Raspberry Pi, reComputer) over the local network.

---

## Step 3: Connect E1003 to Home Assistant (Optional) {#connect_ha type=ha_integration required=false config=devices/ha_integration.yaml}

Automatically add the E1003 ESPHome panel to Home Assistant using the native config flow API.

### Prerequisites

- E1003 powered on and connected to your Wi-Fi network.
- Home Assistant instance running and reachable.
- Home Assistant administrator username and password.
