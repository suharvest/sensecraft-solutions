## Preset: Off-Grid Mesh Communication {#offgrid_mesh_communication}

Out-of-the-box Meshtastic experience: T1000-E comes pre-flashed with Meshtastic firmware, eliminating the need to connect to a PC. Power on, pair over Bluetooth using the mobile app, and establish an off-grid ad-hoc mesh network for multi-node messaging, topology mapping, and location sharing.

| Device | Purpose |
|---|---|
| SenseCAP T1000-E | Off-grid communication terminal and relay node with integrated LoRa radio, BLE, and GPS |
| Smartphone (iOS / Android) | Runs the official Meshtastic client, communicating with T1000-E over Bluetooth Low Energy |

---

## Step 1: Power On & Pair via Mobile App {#pair_mesh_app type=manual required=true}

The device comes pre-loaded with Meshtastic firmware; no PC connection or flashing is required. Pair directly from the mobile app upon unboxing.

### Wiring

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

### Wiring

- **Dual-Node Loop (Recommended)**: If a second Meshtastic node (or a teammate phone paired to a compatible node) is available, verify that both units share the same region and default channel. Confirm incoming text appears on the receiving phone screen in real time.
- **Single-Node Baseline**: If testing with a single unit, verify proper RF transmission via the on-air checkmark status, node beacon broadcasts, and offline GPS positioning.

1. **Disconnect External Networks**: Turn off Wi-Fi and Cellular Data on your phone to confirm complete off-grid operation;
2. **Send Broadcast Message**: In the Meshtastic app **Messages** view, select the default Primary Channel, type a test message (such as `Hello Meshtastic from T1000-E`), and tap send;
3. **Confirm Delivery**: A cloud or checkmark icon next to the message confirms the packet was broadcast over the air via the T1000-E LoRa radio; peer nodes (if present) will receive and display it;
4. **Inspect Node List (Nodes)**: Tap **Nodes** in the navigation bar to inspect neighboring mesh nodes, signal-to-noise ratio (SNR), received signal strength (RSSI), and hop counts;
5. **Off-Grid Map (Map)**: Tap **Map** to view self and peer node locations on the offline map once GPS lock is achieved outdoors.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Message shows no delivery checkmark | Both nodes need the same region (Settings -> LoRa) and the same default channel. Check the region is set on the T1000-E. |
| Node list shows no neighbours | Neighbours appear only when a second node is within radio range; with a single node, verify the beacon and the on-air checkmark instead. |
| Map shows no position | GPS lock needs a clear view of the sky; test outdoors. |

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

### Wiring

1. Attach magnetic cable to pins on back of T1000-E and plug into PC USB port;
2. Select **Meshtastic Off-Grid Broadcast** below (default recommended) and click **Deploy**;
3. Device reboots automatically upon completion and enters calibration-ready mode.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Device is not detected over USB | Seat the magnetic cable on the pins on the back of the T1000-E and use a data cable; charge-only cables expose no serial port. |
| Flashing does not start or is interrupted | Reconnect the cable, select **Meshtastic Off-Grid Broadcast** again and click **Deploy**. This step is optional if the firmware is already installed. |

---

## Step 2: Rigid Surface Mounting {#mount_device type=manual required=true}

Vibration anomaly detection relies on rigid mechanical contact and true acoustic transmission. The sensor must be firmly adhered to the machinery before baseline calibration.

### Mounting Requirements

1. **Avoid Soft Foam**: Never use soft sponge or foam double-sided tape, which dampens high-frequency micro-vibrations;
2. **Recommended Medium**: Use **3M VHB 4910 (0.5mm acrylic tape)** or a high-strength magnetic base;
3. **Mounting Position**: Select a flat radial load surface on the motor, pump, or fan bearing housing free from grease and dirt;
4. **Orientation**: Press device firmly against the metal surface; connect magnetic cable to maintain power for calibration.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Alarms trigger on normal operation or never trigger | Soft foam or sponge tape damps high-frequency vibration. Use 3M VHB 4910 or a magnetic base on a clean, grease-free flat surface. |
| Device was moved after calibration | The baseline is learned at the mounted position; repeat Step 3 after changing the mounting position. |

---

## Step 3: Online Baseline Calibration on SenseCraft AI {#vibration_calibration type=web_dashboard required=true config=devices/vibration_calibrator.yaml}

With the device mounted, start the machinery and train the baseline model under steady, healthy operating conditions.

### Wiring

1. Start the monitored machinery and verify it is running in a steady, healthy operational state;
2. Click **Open Dashboard** below to open SenseCraft AI Studio in your browser;
3. Click **Connect**, select the **SenseCAP T1000-E** serial port, and grant permission;
4. Observe real-time 3-axis acceleration waveforms. Once waveform features stabilize, click **Start Learning / Train Baseline**;
5. Upon calibration, model parameters are written back to internal non-volatile memory;
6. **Critical Step**: Click **Disconnect** in the web studio to release the serial port, then disconnect the magnetic cable to enter autonomous monitoring.

### Troubleshooting

| Symptom | Fix |
|---|---|
| T1000-E serial port is not listed after clicking Connect | Use a Chromium-based browser, connect the magnetic cable and grant the serial permission when prompted. |
| Learning does not start | Start the machinery first and wait until the 3-axis waveform is stable, then click **Start Learning / Train Baseline**. |
| Device cannot be reconnected later or does not enter monitoring | Click **Disconnect** in the web studio before unplugging the magnetic cable so the serial port is released. |

---

## Step 4: Verify Off-Grid Alarm Broadcast {#verify_vibration_alert type=manual required=true verify=true}

Verify the off-grid alert propagation loop after unplugging the cable.

### Wiring

1. **Enter Inspection State**: After removing the cable, T1000-E enters low-power periodic vibration monitoring;
2. **Simulate Anomaly**: Induce a minor impact or eccentric vibration on the machinery (or lightly tap near the bearing housing);
3. **Emit Alert**: When the edge model detects deviation exceeding the calibrated baseline, it wakes the radio and encapsulates a vibration alert packet into the Meshtastic mesh;
4. **Mobile Verification**: On-site maintenance personnel open the Meshtastic app to receive the instant alert notification, device ID, and GPS coordinates.

### Troubleshooting

| Symptom | Fix |
|---|---|
| No alert reaches the phone | Confirm Step 3 finished, the cable is removed, and the phone is connected to a node on the same region and channel as in the first preset. |
| Impact does not trigger an alert | The alert fires only when vibration deviates from the calibrated baseline; use a stronger impact or eccentric load, or repeat Step 3. |

### Deployment Complete

You have completed the full loop from foundational off-grid mesh communications to autonomous edge device intelligence, achieving predictive maintenance alerts in harsh industrial environments without external network infrastructure.

---

## Preset: Mesh to Home Assistant Central Map {#mesh_ha_bridge}

Bridge Meshtastic off-grid mesh communications to Home Assistant via a USB-connected receiver node. Field T1000-E vibration tracker nodes report GPS positions and vibration anomaly alerts over the mesh network without cellular or Wi-Fi infrastructure, aggregated and visualized on a central Home Assistant map.

> **Prerequisites**: The T1000-E used for vibration detection must have the VAD firmware flashed and baseline calibration completed (refer to Preset 2 Steps 1 and 3). If using the factory Meshtastic firmware directly, the device operates as a mobile GPS tracker and triggers an SOS alarm on the vibration sensor entity (`binary_sensor.vibration_<node_id>`) in Home Assistant while reporting position coordinates to the map.

| Device | Purpose |
|---|---|
| SenseCAP T1000-E (Gateway Node) | Connected to host via USB data cable to receive mesh packets and forward over serial |
| SenseCAP T1000-E (Tracker Node) | Mounted on machinery to detect vibration anomalies and broadcast alerts with GPS coordinates |
| Host Machine | Runs Docker to host the Mesh-MQTT serial bridge container |

---

## Step 1: Deploy Mesh-MQTT Serial Bridge {#deploy_bridge type=docker_deploy required=true config=devices/meshtastic_bridge.yaml}

Bridges Meshtastic mesh packets from the USB receiver node to an MQTT broker, and publishes Home Assistant MQTT Discovery entities for live vibration alerting and GPS map tracking.

### Wiring

1. Connect the receiving Meshtastic node (e.g. T1000-E in receiving mode or USB dongle) to a USB port on the host machine using a data cable;
2. Verify the serial port device path (typically `/dev/ttyACM0` on Linux);
3. Enter your MQTT Broker details below and start deployment.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Serial port `/dev/ttyACM0` not found | Verify USB cable connection and run `ls /dev/ttyACM*` on the host to check the device path. |
| Container health check failed | Ensure the USB receiver is plugged in and the MQTT broker is reachable. Run `docker logs vibration-mesh-bridge` for details. |
| Cannot connect to MQTT Broker | Verify broker IP address, port, and authentication credentials. |

### Target {#deploy_bridge_local type=local device_name="Local Host" config=devices/meshtastic_bridge.yaml default=true}

Deploy to this machine running Docker.

### Target {#deploy_bridge_remote type=remote device_name="Linux Host" config=devices/meshtastic_bridge.yaml}

Deploy over SSH to a Linux host with Docker.

---

## Step 2: Connect to Home Assistant (Optional) {#connect_ha type=ha_integration required=false config=devices/ha_integration.yaml}

Automatically configure the MQTT integration on your existing Home Assistant instance via its API. If your Home Assistant instance already has MQTT configured, you can skip this step.

### Wiring

1. Ensure your Home Assistant instance is running and accessible on the local network;
2. Enter your Home Assistant URL and administrator credentials below;
3. Provide the MQTT broker address and credentials used by the Mesh-MQTT bridge;
4. Click **Deploy** to configure the MQTT integration on Home Assistant.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Authentication failed | Check the Home Assistant administrator username and password. |
| Cannot reach Home Assistant | Ensure Home Assistant is running and the host and port (default 8123) are correct. |
| MQTT integration already exists | If MQTT is already configured in Home Assistant, skip this step. |

---

## Step 3: Prepare and Mount T1000-E Vibration Tracker {#mount_tracker type=manual required=true}

Rigidly mount the T1000-E vibration tracker node onto the monitored industrial equipment to detect abnormal vibrations and broadcast alerts over the Meshtastic mesh.

> **Prerequisites**: The T1000-E used for vibration detection must have the VAD firmware flashed and baseline calibration completed (refer to Preset 2 Steps 1 and 3). If using the factory Meshtastic firmware directly, the device operates as a mobile GPS tracker and triggers an SOS alarm on the vibration sensor entity (`binary_sensor.vibration_<node_id>`) in Home Assistant while reporting position coordinates to the map.

### Wiring

1. **Power On**: Press and hold the button on the T1000-E tracker node for 3 seconds until it beeps and powers on;
2. **Channel Configuration**: Ensure the tracker node is set to the same LoRa frequency region and default channel as the receiving gateway node;
3. **Rigid Mounting**: Firmly adhere the T1000-E tracker node to a clean, flat surface on the motor, pump, or fan bearing housing using **3M VHB 4910 acrylic tape** or a magnetic mount. Avoid soft foam tapes;
4. **GPS Visibility**: For physical map tracking, ensure the node has outdoor GPS line-of-sight, or relies on mesh broadcast coordinates.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Tracker node not broadcasting | Verify power status and confirm the tracker node shares the same LoRa region and channel as the gateway. |
| Inaccurate or damped vibration readings | Avoid foam tape; use 3M VHB 4910 acrylic double-sided tape on a clean, degreased metallic surface. |

---

## Step 4: View Central Map in Home Assistant {#verify_map type=web_dashboard required=true verify=true config=devices/ha_dashboard.yaml}

Open the Home Assistant map dashboard to monitor physical node positions and verify vibration anomaly alert status in real time.

### Wiring

1. In the input fields below, confirm the Home Assistant host and port (default: `127.0.0.1:8123`);
2. Click **Open Dashboard** to navigate directly to the Home Assistant Map view (`/map`);
3. Verify that the tracker node appears as `device_tracker.vibration_<node_id>` on the map with current GPS coordinates;
4. Tap near the monitored machinery or simulate vibration to trigger an alert, and verify the `binary_sensor.vibration_<node_id>` state changes to `ON` in Home Assistant.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Tracker entity not appearing on map | Ensure the tracker node has obtained a GPS fix and broadcast at least one position packet. Check bridge logs with `docker logs vibration-mesh-bridge`. |
| Vibration sensor stays OFF during vibration | Check that the packet contains `VIBRATION_ALERT` or `ALARM`. Verify in the Meshtastic mobile app or bridge container stdout. |
| Map page does not open | Ensure Home Assistant is running on the specified host and port (default `http://127.0.0.1:8123`). |

### Deployment Complete

The Meshtastic to Home Assistant Central Map monitoring preset is now fully deployed. Edge vibration alerts and GPS locations from field T1000-E nodes are aggregated over the off-grid mesh and visualized centrally on your Home Assistant dashboard.
