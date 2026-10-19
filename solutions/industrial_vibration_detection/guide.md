## Preset: Off-Grid Mesh Communication {#offgrid_mesh_communication}

Out-of-the-box Meshtastic experience: T1000-E comes pre-flashed with Meshtastic firmware, eliminating the need to connect to a PC. Power on, pair over Bluetooth using the mobile app, and establish an off-grid ad-hoc mesh network for multi-node messaging, topology mapping, and location sharing.

| Device | Purpose |
|---|---|
| SenseCAP T1000-E | Off-grid communication terminal and relay node with integrated LoRa radio, BLE, and GPS |
| Smartphone (iOS / Android) | Runs the official Meshtastic client, communicating with T1000-E over Bluetooth Low Energy |

---

## Step 1: Power On & Pair via Mobile App {#pair_mesh_app type=manual required=true}

The device comes pre-loaded with Meshtastic firmware; no PC connection or flashing is required. Pair directly from the mobile app upon unboxing.

### Instructions

1. **Power On**: Press and hold the front button on T1000-E for 3 seconds. The buzzer will beep and the LED will alternate blue and green, indicating the device is powered on and advertising over Bluetooth;
2. **Download App**: Search for and install the official **Meshtastic** app from the Apple App Store or Google Play / APKPure;
3. **Scan for Device**: Enable Bluetooth on your phone, launch the Meshtastic app, and open the device scanner;
4. **Pair & Bind**: Locate the entry named `Meshtastic_xxxx` in the list, tap to connect, and accept the Bluetooth pairing prompt;
5. **Set Region & Node Name**: Once connected, navigate to **Settings → LoRa** at the bottom, set **Region** to match your hardware's operating band (e.g., `US` for 915MHz, `EU_868` for 868MHz, or `CN` for 470MHz), and optionally configure your node name under **User** settings.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Device not discovered | Ensure button was held for 3s to turn on; if no LED lights, charge with magnetic cable for 30 minutes |
| Pairing rejected or timed out | Remove device from phone system Bluetooth settings, return to Meshtastic app and re-initiate pairing |
| Region Unset warning | You must select the correct country/regional LoRa frequency band in settings to enable radio transmission |
| Flashed custom firmware and want to restore | Connect magnetic cable to PC and reflash official firmware via [flasher.meshtastic.org](https://flasher.meshtastic.org/) |

---

## Step 2: Verify Off-Grid Messaging & Node Topology {#verify_mesh_chat type=manual required=true verify=true}

Verify ad-hoc packet delivery and node topology with all external connectivity disabled.

### Verification Prerequisites & Instructions

- **Dual-Node Loop (Recommended)**: If a second Meshtastic node (or a teammate phone paired to a compatible node) is available, verify that both units share the same region and default channel. Confirm incoming text appears on the receiving phone screen in real time.
- **Single-Node Baseline**: If testing with a single unit, verify proper RF transmission via the on-air checkmark status, node beacon broadcasts, and offline GPS positioning.

1. **Disconnect External Networks**: Turn off Wi-Fi and Cellular Data on your phone to confirm complete off-grid operation;
2. **Send Broadcast Message**: In the Meshtastic app **Messages** view, select the default Primary Channel, type a test message (such as `Hello Meshtastic from T1000-E`), and tap send;
3. **Confirm Delivery**: A cloud or checkmark icon next to the message confirms the packet was broadcast over the air via the T1000-E LoRa radio; peer nodes (if present) will receive and display it;
4. **Inspect Node List (Nodes)**: Tap **Nodes** in the navigation bar to inspect neighboring mesh nodes, signal-to-noise ratio (SNR), received signal strength (RSSI), and hop counts;
5. **Off-Grid Map (Map)**: Tap **Map** to view self and peer node locations on the offline map once GPS lock is achieved outdoors.

### Deployment Complete

Your T1000-E is now an active node on the off-grid LoRa mesh, capable of kilometer-range emergency text messaging and location tracking without any base stations or cloud dependencies.

---

## Preset: Vibration Anomaly & Device Alert {#industrial_vibration_monitor}

Add edge intelligence to mesh communication: mount T1000-E firmly onto rotating machinery, calibrate baseline on SenseCraft AI, and broadcast edge vibration alerts over Meshtastic to nearby nodes.

| Device | Purpose |
|---|---|
| SenseCAP T1000-E | Mounted on machinery surface to capture 3-axis vibration, extract features, and emit mesh alerts |
| 3M VHB 4910 Acrylic Tape | Ensures rigid contact with machinery surface to prevent high-frequency vibration damping |
| Magnetic USB Cable | Connects to PC for online operational calibration in SenseCraft AI Studio |

---

## Step 1: Check or Flash Vibration Firmware (Optional) {#flash_vibration type=nrf52_usb required=false config=devices/t1000e_tracker.yaml}

If your T1000-E has not yet been loaded with vibration anomaly detection (VAD) algorithms, connect with the magnetic USB cable to flash; skip if already installed.

### Instructions

1. Attach magnetic cable to pins on back of T1000-E and plug into PC USB port;
2. Select **Meshtastic Off-Grid Broadcast** below (default recommended) and click **Deploy**;
3. Device reboots automatically upon completion and enters calibration-ready mode.

---

## Step 2: Rigid Surface Mounting {#mount_device type=manual required=true}

Vibration anomaly detection relies on rigid mechanical contact and true acoustic transmission. The sensor must be firmly adhered to the machinery before baseline calibration.

### Mounting Requirements

1. **Avoid Soft Foam**: Never use soft sponge or foam double-sided tape, which dampens high-frequency micro-vibrations;
2. **Recommended Medium**: Use **3M VHB 4910 (0.5mm acrylic tape)** or a high-strength magnetic base;
3. **Mounting Position**: Select a flat radial load surface on the motor, pump, or fan bearing housing free from grease and dirt;
4. **Orientation**: Press device firmly against the metal surface; connect magnetic cable to maintain power for calibration.

---

## Step 3: Online Baseline Calibration on SenseCraft AI {#vibration_calibration type=web_dashboard required=true config=devices/vibration_calibrator.yaml}

With the device mounted, start the machinery and train the baseline model under steady, healthy operating conditions.

### Instructions

1. Start the monitored machinery and verify it is running in a steady, healthy operational state;
2. Click **Open Dashboard** below to open SenseCraft AI Studio in your browser;
3. Click **Connect**, select the **SenseCAP T1000-E** serial port, and grant permission;
4. Observe real-time 3-axis acceleration waveforms. Once waveform features stabilize, click **Start Learning / Train Baseline**;
5. Upon calibration, model parameters are written back to internal non-volatile memory;
6. **Critical Step**: Click **Disconnect** in the web studio to release the serial port, then disconnect the magnetic cable to enter autonomous monitoring.

---

## Step 4: Verify Off-Grid Alarm Broadcast {#verify_vibration_alert type=manual required=true verify=true}

Verify the off-grid alert propagation loop after unplugging the cable.

### Instructions

1. **Enter Inspection State**: After removing the cable, T1000-E enters low-power periodic vibration monitoring;
2. **Simulate Anomaly**: Induce a minor impact or eccentric vibration on the machinery (or lightly tap near the bearing housing);
3. **Emit Alert**: When the edge model detects deviation exceeding the calibrated baseline, it wakes the radio and encapsulates a vibration alert packet into the Meshtastic mesh;
4. **Mobile Verification**: On-site maintenance personnel open the Meshtastic app to receive the instant alert notification, device ID, and GPS coordinates.

### Deployment Complete

You have completed the full loop from foundational off-grid mesh communications to autonomous edge device intelligence, achieving predictive maintenance alerts in harsh industrial environments without external network infrastructure.
