## What This Solution Does

This solution leverages the Seeed Studio SenseCAP Card Tracker T1000-E (Nordic nRF52840 + Semtech LR1110) to deliver a two-stage practical experience from out-of-the-box off-grid mesh communication to edge device intelligence:
- **Pure Mesh Communication**: The device comes pre-flashed with Meshtastic firmware. Simply press and hold the button to power on and pair with your mobile phone via Bluetooth. Establish an off-grid ad-hoc mesh network to exchange text messages, check node topologies, and share location without any cellular or internet coverage.
- **Device Message Integration**: Using the on-board 3-axis accelerometer and lightweight edge algorithms alongside SenseCraft AI online calibration, the device autonomously detects machinery anomaly vibrations and packages them into Meshtastic alert broadcasts to nearby nodes on the local mesh.

## Key Benefits

| Benefit | Details |
|---|---|
| **Out-of-the-Box Zero Flashing (Preset 1)** | T1000-E comes pre-loaded with Meshtastic firmware; for Preset 1, unbox, power on, and bind directly through the mobile app over Bluetooth without connecting to a PC |
| **Truly Off-Grid Mesh Networking** | Multi-hop ad-hoc networking over LoRa radio; nodes automatically route packets without depending on cell towers, gateways, SIM cards, or cloud servers |
| **Autonomous Edge Anomaly Detection** | The on-board accelerometer removes gravity bias dynamically and extracts 6D vibration features, running inference locally on the device without streaming raw waveforms |
| **Decoupled Comms & Device Events** | Device health status, vibration alarms, and location data are encapsulated into standard Meshtastic payloads, combining communication infrastructure with practical IoT alerts |

## Suitable Scenarios: Two Progressive Presets

The solution provides two progressive presets ranging from basic communications to industrial equipment inspection:

| Scenario Preset | Educational & Experience Focus | Core Workflow | Hardware |
|---|---|---|---|
| **Off-Grid Mesh Communication** | Foundational Comms: LoRa mesh networking & mobile pairing | Power on → Pair via mobile Bluetooth → Test off-grid broadcast, node map, and GPS | SenseCAP T1000-E |
| **Vibration Anomaly & Device Alert** | Comms + Device Events: Edge feature extraction & event triggers | Firm mechanical mounting → Online baseline calibration via SenseCraft AI → Trigger alert broadcast | SenseCAP T1000-E |

## Deployment Requirements

- **Mobile Application**: Install the official **Meshtastic App** from the Apple App Store or Google Play / APKPure;
- **Regional Frequency Band**: During initial pairing, set the LoRa region in the mobile app to match your hardware variant (e.g. US 915MHz, EU 868MHz, or CN 470MHz);
- **Mounting Medium**: When mounting for machinery vibration detection, use firm acrylic tape (such as 3M VHB 4910) on a clean motor or bearing surface. Avoid foam tape to prevent high-frequency damping;
- **Calibration Disconnection**: When completing online baseline learning in SenseCraft AI Studio, click **Disconnect** on the web page to release the serial port before unplugging the magnetic cable.
