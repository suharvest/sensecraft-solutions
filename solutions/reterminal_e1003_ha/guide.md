## Preset: Configure E1003 {#usb_candidate}

Connect the E1003 panel via USB and integrate it into Home Assistant. The installer checks firmware, installs it when needed, deploys or connects to Home Assistant, and automatically links the panel.

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

1. If connecting Wi-Fi for the first time, configure Wi-Fi credentials via Improv Serial or the ESPHome captive portal.
2. If not using Step 3 automatic integration, navigate to Settings → Devices & Services → Integrations in Home Assistant, add ESPHome, and enter the panel IP (no API key required).
3. In Home Assistant, create an Automation (Settings → Automations & Scenes → Create Automation) to bind the panel actions:
   - **Trigger**: State / Device trigger from E1003 entities (power button or brightness level).
   - **Action**: Call service `light.toggle` or `light.turn_on` on your desired dimmable light entity (such as `light.living_room`).
4. Test the on/off touch zone and the 25%, 50%, 75%, and 100% brightness zones.

> **Note**: Only these five touch zones have actions defined; other screen elements are static.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Device serial port not found | Click Refresh; verify the USB cable supports data transfer; close other programs using the serial port |
| Setup or write failed | Check the displayed error message, resolve the issue, and retry; do not erase NVS |
| Saving or verification in progress | Keep the device powered and wait for the final verification status |
| Button or light does not respond | Confirm the automation trigger and action are set correctly in Home Assistant; ensure “Allow the device to perform Home Assistant actions” is enabled in the ESPHome device options |

---

## Step 2: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/ha_host.yaml}

Deploy a Home Assistant instance on your local or remote Docker host. If Home Assistant is already running on port 8123, this step automatically detects it and skips.

### Target {#ha_local type=local config=devices/ha_host.yaml default=true}

Deploy Home Assistant on the local machine.

### Target {#ha_remote type=remote config=devices/ha_host.yaml}

Deploy Home Assistant on a remote host (e.g. Raspberry Pi, reComputer) over the local network.

---

## Step 3: Connect E1003 to Home Assistant (Optional) {#connect_ha type=ha_integration required=false config=devices/ha_integration.yaml}

Automatically add the E1003 ESPHome panel to Home Assistant using the native config flow API.

### Prerequisites

- E1003 powered on and connected to your Wi-Fi network.
- Home Assistant instance running and reachable.
- Home Assistant administrator username and password.
