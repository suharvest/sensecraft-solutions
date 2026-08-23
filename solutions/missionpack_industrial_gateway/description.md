## What This Solution Helps You Do

For building, energy, and equipment-management integrators, the expensive part is often not the dashboard. It is rebuilding controller drivers, point mappings, and data conversions at every customer site. This solution brings OPC UA, Modbus, BACnet/IP, and MQTT into one point model, so upstream systems integrate with one MQTT read/write interface.

Site differences become configuration: add a controller, discover or enter points manually, verify data quality, and expose selected data to an energy platform, SCADA, cloud service, or customer application. Integrators no longer need a separate protocol-conversion layer for every project.

The solution is designed first for the reComputer R1000/R1100 Series and reTerminal DM Series, including on-device touch operation on reTerminal DM.

The prediction workflow remains available as an optional plugin. Multi-protocol access, unified point management, and data service work independently without training a model.

## Key Benefits

| Benefit | What it means on site |
|---------|-----------------------|
| Integrate several field protocols once | OPC UA, Modbus TCP/RTU, BACnet/IP, and MQTT share one point model instead of separate upstream adapters |
| Turn site differences into configuration | Browse OPC UA, scan Modbus units, use BACnet Who-Is, or observe MQTT topics; enter points manually whenever discovery is incomplete |
| Read and control through one interface | The embedded broker publishes versioned data, presence, command, and receipt topics, so integrators maintain one northbound contract |
| Verify and trace every control result | Check permissions and data quality before a write, then inspect effective value, device readback, and command receipt |
| Reuse the integration across projects | New deployments mainly change controllers and point mappings instead of rebuilding the protocol bridge beneath each application |

## Use Cases

| Scenario | How it is used |
|----------|----------------|
| Building energy solution delivery | Bring BACnet/IP air handlers and Modbus meters into one point model, then feed an energy dashboard or customer platform |
| HVAC retrofit | Keep an OPC UA controller while adding MQTT sensors; upstream control continues through the same interface |
| Multi-vendor equipment integration | Resolve protocol and addressing differences on a reComputer R1000/R1100 or reTerminal DM, then expose one contract to the customer system |
| Controlled optimization | Add the prediction plugin above the unified points, import CSV data, select inputs and outputs, and trace every control result |

## Usage Notes

### Core Hardware

| Device | Purpose | Required |
|--------|---------|----------|
| reComputer R1000 Series | Runs multi-protocol access, the unified point model, MQTT data service, and web console | Choose one |
| reComputer R1100 Series | Runs multi-protocol access, the unified point model, MQTT data service, and web console | Choose one |
| reTerminal DM Series | Runs the same services and provides an on-device touch display for setup and operations | Choose one |
| USB-to-RS-485 adapter | Connects a Modbus RTU bus | Only for Modbus RTU |

### Network and Protocol Boundaries

- The data-hub device must be able to reach each Ethernet protocol network. BACnet broadcasts may require the correct network interface and subnet configuration.
- OPC UA browsing, BACnet Who-Is, Modbus TCP unit scanning, and MQTT topic observation create candidates. A user must confirm candidates before they become managed points.
- Modbus RTU configuration and transport are included, but the standard Docker profile does not attach a host serial device. Use the serial-device installer/profile, and keep production writes disabled until the exact USB-to-RS-485 adapter and target controller pass hardware-in-the-loop validation.
- The remote Linux target uses host networking so BACnet/IP broadcast discovery can reach the physical subnet. Docker Desktop's bridged local target may require manual BACnet addressing.
- Deployment runs a network-isolated, one-shot volume ownership migration before the non-root data service starts. This preserves data created by earlier root-based images while keeping the long-running service unprivileged.
- The northbound service uses the native **MissionPack v1 MQTT topic contract**. It is inspired by industrial lifecycle messaging but is **not Sparkplug B compatible** in this release.
- Plain MQTT is telemetry-only. Enable TLS and an authorized control identity before allowing remote commands.
