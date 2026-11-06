# Turn Industrial RS485 Dumb Terminals into Smart Nodes

## What this solution does for you

Buildings, workshops, machine rooms, and campuses are filled with traditional industrial sensors and meters—temperature transmitters, power meters, flow meters, and multi-color indicator lights. While reliable and durable, they act as "dumb terminals": isolated, silent, and unable to communicate directly with modern smart systems.

This solution provides a lightweight "digital translator bridge":
Without replacing expensive existing hardware, simply connect a **Seeed Studio XIAO** and **RS485 expansion board** to your RS485 wiring to transform silent sensors into communicative smart nodes. Real-time metrics appear automatically in Home Assistant and trigger space-wide automations.

In addition to the standard temperature and humidity probe, this solution seamlessly accommodates any third-party Modbus RS485 equipment (meters, warning lights, weather stations) via straightforward configuration.

## Core values

| Benefit | Description |
|---|---|
| **Awaken Dumb Devices** | Upgrade existing legacy sensors into smart IoT nodes without replacing hardware |
| **Broad 485 Hardware Support** | Works with included probes or any existing factory RS485 sensors, meters, and lights |
| **Zero-Code Integration** | Eliminate low-level register and protocol coding with ready-to-use parameter templates |
| **Spatial Automation** | Synchronize real-time telemetry into Home Assistant to trigger HVAC, lighting, and fans |
| **Local Offline Autonomy** | Local network communication ensures full operation even when internet access is unavailable |

## Use cases

| Scenario | Application |
|---|---|
| **Smart Building & Energy** | Monitor power meters and duct temperature/humidity, optimizing HVAC consumption on a single screen |
| **Industrial Workshop Monitoring** | Track production line ambient metrics and trigger 3-color tower lights upon threshold violation |
| **Server & Switch Room Guard** | 24/7 autonomous monitoring of cabinet temperature, sending immediate push alerts upon overheating |

## Usage Notes

### Core hardware

| Device | Description | Required |
|---|---|---|
| **Seeed Studio XIAO Board** | Gateway microcontroller (supports C3, S3, and C6) | ✓ Required |
| **Seeed Studio RS485 Board** | Dedicated RS485 expansion board for XIAO with 120Ω termination switch | ✓ Required |
| **Industrial RS485 Sensors** | Standard XY-MD02 probe or user-owned RS485 sensors/meters/lights | ✓ Required |
| **12V DC Power Adapter** | Standard power supply for industrial sensors | If sensor requires |
| **USB Type-C Cable** | Flashes generated firmware onto the XIAO board and provides power | ✓ Required |

### Server & Network requirements

- **Compilation Server**: Any standard ARM64 Linux device (e.g. RK3576, RK3588, Raspberry Pi) with 4+ cores and 4GB-8GB RAM running Docker. Can also run directly on the local computer's Docker.
- **Wi-Fi Network**: 2.4 GHz Wi-Fi network for gateway telemetry streaming.
- **Home Assistant**: Gateway board and Home Assistant host must reside on the same local network.
