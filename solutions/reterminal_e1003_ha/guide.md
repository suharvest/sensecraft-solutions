## Preset: E-paper Smart Home Panel {#usb_candidate}

Connect the E1003 e-paper panel via USB and integrate it into Home Assistant. The installer downloads and flashes the panel firmware, sets up or connects to your Home Assistant host, and automatically links the panel for smart home control.

> Note: Ensure the reTerminal E1003 panel is connected via USB. The flashing step downloads and installs the firmware directly from the CDN.

## Step 1: Install E1003 panel firmware {#e1003_usb type=esp32_usb required=true verify=true config=devices/e1003_usb.yaml}

Select your serial port, click **Deploy**, and wait for firmware installation and reboot verification to complete.

### Prerequisites

- A reTerminal E1003 panel and a USB data cable (with data transfer support).

### Wiring

1. Connect the E1003 carrier's USB-UART port to your computer with the USB cable.
2. Select the device serial port in the App (click “Refresh” in the same row if it does not appear).

### Flashing

1. Select the serial port corresponding to the connected E1003 device.
2. Click **Install** / Deploy. The installer downloads the factory firmware from the CDN and flashes it to the panel at 115200 baud.
3. Keep the device connected until flashing and post-deployment reboot verification complete.

<details>
<summary>Technical details</summary>
<p>Factory firmware: 1,325,184 bytes, SHA-256 <code>fc89d3b3a1091fb883e24a17b4572920fb9e6daeda7e445f81b029d10c9ac17c</code>. Flashing uses 115200 baud, offset 0x0, no full-chip erase, and preserves NVS.</p>
</details>

### After setup

1. **Wi-Fi**: Join the `reterminal-e1003-xxxxxx` hotspot shown on the panel (no password), open `192.168.4.1` and pick your 2.4 GHz Wi-Fi. The panel then shows its IP and `HA WAITING`.
2. **Home Assistant**: Run Step 3, or add the **ESPHome** integration with the panel IP (port `6053`). The panel shows `HA CONNECTED`. No API key or extra permission is needed.
3. **Light**: [Import the blueprint](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FLove4yzp%2Fesphome-reterminal-e1003-workspace%2Fblob%2Fmain%2Fha%2Fblueprints%2Fautomation%2Fe1003_light_sync.yaml) and create an automation. Choose the light, plus `Main light command`, `Main light state` and `Main light value` from this panel. Toggle the light once in Home Assistant to sync the screen. To control another light later, change it in the automation.

**Change Wi-Fi**: tap the Wi-Fi area on the screen twice (within 8 s), then repeat step 1. Pairing is kept; if Home Assistant does not reconnect, use **Reconfigure** on the ESPHome entry to enter the new IP.

**Green button**: press once for a full refresh (clears ghosting); hold 3 s to restart.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Device serial port not found | Click Refresh; use a data-capable USB cable; close other programs using the port |
| Write failed | Check the error message and retry; do not erase NVS |
| Stays at `HA WAITING` | Put Home Assistant on the same LAN and add ESPHome by the IP on the screen |
| Light does not respond | Make sure the automation uses the blueprint and all three entities come from this panel |


---

## Step 2: Deploy Home Assistant (Optional) {#deploy_ha type=docker_deploy required=false config=devices/ha_host.yaml}

Deploy a Home Assistant instance on your local or remote Docker host. If Home Assistant is already running on port 8123, this step automatically detects it and skips.

> **Platform Constraint**: The Home Assistant container relies on native host networking (`network_mode: host`) for mDNS and LAN device discovery. **Local installation is supported on Linux hosts only**. On macOS or Windows environments, Docker Desktop cannot provide native host networking: please **uncheck this step to skip it**, or select `ha_remote` to deploy to an independent Linux host (such as a Raspberry Pi or reComputer), or reuse an existing Home Assistant instance on your network.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Home Assistant is already running on port 8123 | The step detects the running instance and skips installation; continue to the next step. |
| Local install fails on macOS or Windows | The container uses host networking, which Docker Desktop does not provide. Select the remote target (a Linux host such as a Raspberry Pi or reComputer) or reuse an existing Home Assistant. |

### Target {#ha_local type=local config=devices/ha_host.yaml}

Deploy Home Assistant on a local Linux machine using host network mode (Linux host only; skip on macOS/Windows).

### Target {#ha_remote type=remote config=devices/ha_host.yaml default=true}

Deploy Home Assistant on a remote host (e.g. Raspberry Pi, reComputer) over the local network.

---

## Step 3: Connect E1003 to Home Assistant (Optional) {#connect_ha type=ha_integration required=false config=devices/ha_integration.yaml}

Automatically add the E1003 ESPHome panel to Home Assistant using the native config flow API. Then import the light blueprint (Step 1, After setup).

### Prerequisites

- E1003 powered on and joined to the same LAN as Home Assistant (connected to 2.4 GHz Wi-Fi).
- Home Assistant instance running and reachable.
- Home Assistant administrator username and password.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Home Assistant login fails | Use a Home Assistant administrator account and confirm the instance is reachable from this computer. |
| E1003 panel is not found | The panel must be powered on and joined to a 2.4 GHz Wi-Fi network on the same LAN. Otherwise add the ESPHome integration manually in Home Assistant with the panel IP (Native API needs no key). |

---

## Preset: Color Touch Smart Home Panel {#indicator_panel}

Flash the SenseCAP Indicator over USB and add it to Home Assistant through the ESPHome integration. No MQTT broker is needed.

## Step 1: Install Indicator panel firmware {#indicator_usb type=esp32_usb required=true verify=true config=devices/indicator_usb.yaml}

Connect the Indicator's USB-C port, select the serial port (enter it manually if it is not listed), click **Deploy**, and keep it connected until verification finishes.

### Prerequisites

- A SenseCAP Indicator (D1 / D1S / D1Pro / D1L) and a USB data cable (with data transfer support).

### After setup

1. On the device screen, join your 2.4 GHz Wi-Fi (Settings) and note the IP shown in Settings.
2. Run Step 3, or add the **ESPHome** integration in Home Assistant with that IP and port `6053`. Leave the encryption key blank.
3. The device page shows 12 entities (temperature, humidity, CO2, tVOC, 6 switches, 2 numbers). Home Assistant does not create dashboard cards for them; add the ones you want.

> **Note**: Without an encryption key, the connection is plaintext and anyone on the LAN can read and control the panel. Use it on a trusted network, or set a key with `native psk <base64>` on the serial console and enter the same key in Home Assistant.

MQTT is optional and keeps the topics `indicator/sensor`, `indicator/switch/set` and `indicator/switch/state`. Set the broker under Settings → MQTT broker, or with `setmqtt` on the serial console.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Device serial port not found | Refresh or enter the port manually; use a data-capable USB cable |
| Device not discovered in Home Assistant | Add ESPHome manually with the Indicator's IP and port `6053` (discovery needs mDNS on the LAN) |

---

## Step 2: Deploy Home Assistant (Optional) {#indicator_deploy_ha type=docker_deploy required=false config=devices/ha_host.yaml}

Deploy Home Assistant on a Docker host. If it is already running on port 8123, this step skips itself. Local install is Linux only; on macOS or Windows choose the remote target.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Home Assistant is already running on port 8123 | The step detects the running instance and skips installation; continue to the next step. |
| Local install fails on macOS or Windows | The container uses host networking, which Docker Desktop does not provide. Select the remote target (a Linux host such as a Raspberry Pi or reComputer) or reuse an existing Home Assistant. |

### Target {#indicator_ha_local type=local config=devices/ha_host.yaml}

Deploy on this Linux machine.

### Target {#indicator_ha_remote type=remote config=devices/ha_host.yaml default=true}

Deploy on a remote host (e.g. Raspberry Pi, reComputer).

---

## Step 3: Connect Indicator to Home Assistant (Optional) {#indicator_connect_ha type=ha_integration required=false config=devices/indicator_ha_integration.yaml}

Automatically add the Indicator to Home Assistant as an ESPHome device.

### Prerequisites

- The Indicator is powered on and joined to the same LAN as Home Assistant (connected to Wi-Fi), and you know its IP.
- Home Assistant is running and reachable, with an administrator account.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Home Assistant login fails | Use a Home Assistant administrator account and confirm the instance is reachable from this computer. |
| Indicator is not found | The Indicator must be powered on and joined to the same LAN as Home Assistant, and the IP you entered must be correct. Otherwise add the ESPHome integration manually in Home Assistant with the Indicator IP. |

---

## Preset: Flagship Color Touch Panel (reTerminal D1001) {#d1001_panel}

Connect the reTerminal D1001 flagship touch terminal via USB. The installer automatically downloads and flashes the factory PocketJS firmware, providing portrait and landscape flexibility and seamless Home Assistant control.

## Step 1: Install reTerminal D1001 panel firmware {#d1001_usb type=esp32_usb required=true verify=true config=devices/d1001_usb.yaml}

Connect the reTerminal D1001 USB-C port to your computer, select the serial port, click **Deploy**, and keep connected until firmware writing and reboot verification finish.

### Prerequisites

- A reTerminal D1001 (ESP32-P4 + ESP32-C6, 800x1280 MIPI-DSI display) and a USB-C data cable.

### Wiring and Flashing

1. Connect the USB-C data cable to the reTerminal D1001 port and plug the other end into your computer.
2. Select the recognized serial port in the App (e.g. `/dev/ttyACM*`, `/dev/ttyUSB*`, or `COM*`).
3. Click **Install** / Deploy. The installer flashes the factory image to the ESP32-P4 flash at 460800 baud.
4. Keep the board powered until writing completes and the device automatically reboots.

<details>
<summary>Technical details</summary>
<p>Factory merged firmware size: 11,689,192 bytes, SHA-256 <code>72e25050d1f1c0d0f02dbc11cc249ab93e3ff8a57ef176f681ce8fbf5085950d</code>. Flash parameters: 460800 baud, offset 0x0, DIO 80MHz 16MB flash layout, preserves storage partition.</p>
</details>

### After setup and LAN Connection

1. **Display & Viewport**: The panel boots into the factory PocketJS HA dashboard with a 400x640 logical viewport rendered on the 800x1280 MIPI-DSI panel at density 2. The hardware supports both portrait and landscape mounting orientations, with the factory app calibrated for vertical touch operation.
2. **Wi-Fi Setup**: Join your 2.4 GHz Wi-Fi from the settings screen, ensuring the panel is on the same local network as your Home Assistant host.
3. **Home Assistant Link**:
   - In Settings, enter your local Home Assistant base URL (e.g. `http://192.168.x.x:8123`) and a Long-Lived Access Token.
   - The panel automatically synchronizes your configured light entity, brightness slider, and discovers live weather via the HA template API.
4. **Onboard Peripherals**: The panel supports onboard RGB LED indication, hardware side buttons, and RTC (PCF8563) time synchronization via SNTP.

### Troubleshooting

| Issue | Action |
| --- | --- |
| Device serial port not found | Click Refresh; verify that the USB-C cable supports data; ensure Espressif USB-JTAG/Serial is detected |
| Flashing interrupted or verification fails | Ensure adequate USB power and retry; do not erase the full flash to preserve partition configurations and storage |
| Screen displays HA disconnected | Verify panel Wi-Fi connectivity and confirm the panel and HA host can communicate over LAN; recheck HA Base URL and Token |

---

## Step 2: Deploy Home Assistant (Optional) {#d1001_deploy_ha type=docker_deploy required=false config=devices/ha_host.yaml}

Deploy Home Assistant on a Docker host. If port 8123 is already active, this step skips itself automatically. Local install is Linux only; on macOS or Windows choose the remote target.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Home Assistant is already running on port 8123 | The step detects the running instance and skips installation; continue to the next step. |
| Local install fails on macOS or Windows | The container uses host networking, which Docker Desktop does not provide. Select the remote target (a Linux host such as a Raspberry Pi or reComputer) or reuse an existing Home Assistant. |

### Target {#d1001_ha_local type=local config=devices/ha_host.yaml}

Deploy on this Linux machine.

### Target {#d1001_ha_remote type=remote config=devices/ha_host.yaml default=true}

Deploy on a remote host (e.g. Raspberry Pi, reComputer).
