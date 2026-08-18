## What This Solution Helps You Do

Industrial sites often expose the same building or production data through several incompatible device protocols. MissionPack gives those connections one home: add each controller, confirm its points, monitor values in one table, and expose selected data through a controlled MQTT service.

The solution is designed first for the reComputer R1000/R1100 Series and reTerminal DM Series, including on-device touch operation on reTerminal DM.

The prediction workflow remains available as an optional plugin. The gateway and point-management functions work without training a model.

## Key Benefits

| Benefit | What it means on site |
|---------|-----------------------|
| Connect common industrial protocols | Configure OPC UA, Modbus TCP, BACnet/IP, or MQTT sources from the same web console; Modbus RTU/RS-485 is available through the serial-device deployment profile with an explicit hardware-validation gate |
| Discover, then confirm | Browse OPC UA nodes, scan Modbus unit IDs, use BACnet Who-Is, or observe MQTT topics; review candidates before they become managed points |
| Keep manual setup as a fallback | Every supported discovery flow also allows an engineer to enter a point address manually |
| Operate from one point table | Filter points by source, inspect live values and quality, and require confirmation before a control command is sent |
| Publish a stable northbound contract | The embedded broker publishes versioned point, presence, command, and receipt topics for other on-site systems |

## Use Cases

| Scenario | How it is used |
|----------|----------------|
| Building energy management | Bring BACnet/IP air handlers and Modbus meters into one point list, then feed selected values to an energy dashboard |
| HVAC retrofit | Keep an existing OPC UA controller while adding newer MQTT sensors without rewriting the control application |
| Small industrial gateway | Install on a reComputer R1000/R1100 or reTerminal DM beside a panel and provide one MQTT contract to the customer's supervisory system |
| Controlled optimization | Use the optional prediction plugin to train from CSV data, select input/output points, and review command receipts |

## Usage Notes

### Core Hardware

| Device | Purpose | Required |
|--------|---------|----------|
| reComputer R1000 Series | Runs protocol connections, the point registry, MQTT data service, and web console | Choose one |
| reComputer R1100 Series | Runs protocol connections, the point registry, MQTT data service, and web console | Choose one |
| reTerminal DM Series | Runs the gateway and provides an on-device touch display for setup and operations | Choose one |
| USB-to-RS-485 adapter | Connects a Modbus RTU bus | Only for Modbus RTU |

### Network and Protocol Boundaries

- The gateway must be able to reach each Ethernet protocol network. BACnet broadcasts may require the correct network interface and subnet configuration.
- OPC UA browsing, BACnet Who-Is, Modbus TCP unit scanning, and MQTT topic observation create candidates. A user must confirm candidates before they become managed points.
- Modbus RTU configuration and transport are included, but the standard Docker profile does not attach a host serial device. Use the serial-device installer/profile, and keep production writes disabled until the exact USB-to-RS-485 adapter and target controller pass hardware-in-the-loop validation.
- The remote Linux target uses host networking so BACnet/IP broadcast discovery can reach the physical subnet. Docker Desktop's bridged local target may require manual BACnet addressing.
- Deployment runs a network-isolated, one-shot volume ownership migration before the non-root gateway starts. This preserves data created by earlier root-based images while keeping the long-running service unprivileged.
- The northbound service uses the native **MissionPack v1 MQTT topic contract**. It is inspired by industrial lifecycle messaging but is **not Sparkplug B compatible** in this release.
- Plain MQTT is telemetry-only. Enable TLS and an authorized control identity before allowing remote commands.
