## Preset: Multi-Protocol Data Hub {#standard}

Deploy one lightweight integration layer that turns different controllers into a unified, controllable point model.

| Device | Purpose |
|--------|---------|
| reComputer R1000 / R1100 Series | Unifies field protocols into one point model and MQTT interface |
| reTerminal DM Series | Runs the same services with an on-device touch display |
| Industrial controllers | Provide OPC UA, Modbus, BACnet/IP, or MQTT data |

**What you'll get:**
- One place to configure OPC UA, Modbus, BACnet/IP, and MQTT controllers
- Automatic discovery where available, with manual point entry as the fallback
- One point table for reading, filtering, and safely controlling field data
- One versioned MQTT contract for upstream data, commands, and receipts

**Requirements:** Docker Engine 20.10+ · 4 GB free disk space · Network access to the target controllers

## Step 1: Deploy the Multi-Protocol Data Hub {#gateway type=docker_deploy required=true config=devices/gateway.yaml}

Start protocol integration and data services while preserving point configuration, audit history, and models across restarts.

### Target {#gateway_local type=local config=devices/gateway.yaml default=true}

Deploy on the machine running SenseCraft Solution.

### Wiring

![Connection architecture](gallery/architecture.svg)

1. Connect this machine to the same network as the Ethernet controllers.
2. The standard local Docker target does not attach a serial device. Use a serial-device deployment profile for Modbus RTU and keep production writes disabled until hardware validation is complete.
3. Keep the default web and MQTT ports, or select unused host ports before deployment.

BACnet/IP broadcast discovery may not cross Docker Desktop's bridge network. Use manual BACnet addressing here, or choose the remote Linux target for subnet discovery.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker is not available | Start Docker Desktop or Docker Engine, then retry |
| Port 8280 or 1883 is busy | Choose another web or MQTT host port in the deployment form |
| Image download fails | Confirm the host can reach `sensecraft-missionpack.seeed.cn` and has at least 4 GB free |
| Health check stays pending | Inspect `docker logs missionpack-industrial-gateway` and confirm `/readyz` returns HTTP 200 |

### Target {#gateway_edge type=remote device_name="reComputer R / reTerminal DM" config=devices/gateway.yaml}

Deploy over SSH to a reComputer R1000/R1100 Series or reTerminal DM device on the controller network.

### Wiring

![Connection architecture](gallery/architecture.svg)

1. Connect the selected reComputer R or reTerminal DM Ethernet interface to the controller network and record its IP address.
2. If Modbus RTU is required, use the serial-device installer/profile to attach the USB-to-RS-485 adapter; do not enable production writes before hardware validation.
3. Enter the device SSH address and credentials, then start deployment.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection fails | Check the device IP, username, credentials, and SSH service |
| Registry cannot be reached | Confirm DNS and firewall access to `sensecraft-missionpack.seeed.cn` |
| Web console cannot be opened | Allow the selected web port through the device firewall and verify the container is healthy |
| BACnet discovery returns no devices | Select the interface on the BACnet subnet and check that broadcasts are not blocked |

## Step 2: Configure Unified Access and Data Service {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Open the web console, create the first administrator, and bring the first field controller into the unified point model.

### Prerequisites

The service container from Step 1 must be healthy. No registration token is required for first-run administrator setup.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The page does not load | Wait for Step 1 to report healthy, then verify the selected web port |
| A discovered point is missing | Use manual point configuration as the fallback and verify its protocol address |
| A control command is rejected | Check point write permission, current quality, safety rules, and the command receipt |
| MQTT control is unavailable | Enable TLS and configure a control identity; plaintext mode is telemetry-only |

### Deployment Complete

1. Create the first administrator account; no token is required.
2. Open **Access**, click **Add**, choose OPC UA, Modbus, BACnet/IP, or MQTT, and configure the controller.
3. Run protocol discovery where available, review the candidates, and confirm only the points you need. Use manual configuration when discovery is unavailable or incomplete.
4. Open **Points** to verify live values and quality before granting write access.
5. Open **Data Service** to configure the embedded MQTT broker and review point, presence, command, and receipt topics.
6. Optionally open the prediction plugin to import CSV data and configure input/output points.

#### Protocol Release Status

| Protocol | Current boundary |
|----------|------------------|
| OPC UA | Source configuration, browse/manual points, live reads, and controlled writes |
| Modbus TCP | Manual points, unit scan, live reads, and controlled writes |
| BACnet/IP | Who-Is discovery, manual points, priority writes, and relinquish |
| MQTT source | Explicit topic mappings and bounded topic observation |
| Modbus RTU/RS-485 | Configuration and transport included; requires the serial-device deployment profile and USB hardware validation |
| Northbound MQTT | MissionPack v1 native topics; Sparkplug B is not implemented in this release |
