## Preset: Turn RS485 Dumb Terminals into Smart Nodes {#modbus_gateway}

Transform silent, isolated industrial RS485 sensors (e.g. XY-MD02 temperature/humidity probes, power meters, tower lights, or custom Modbus hardware) into communicative smart nodes using XIAO boards and ESPHome. Directly monitor live metrics in Home Assistant.

## Step 1: Deploy Compilation Environment {#compiler type=docker_deploy required=true config=devices/compiler_host.yaml}

Launch the lightweight compiler service on your local computer or remote ARM64 edge server (such as RK3576, RK3588, or Raspberry Pi) to prepare the build environment.

### Prerequisites

- Target machine is any standard ARM64 Linux device (e.g. RK3576, RK3588, Raspberry Pi with 4+ cores and 4GB-8GB RAM) or local PC running Docker. No special hardware required.
- Internet connectivity to pull the container image.

### Target {#local type=local config=devices/compiler_host.yaml}

Deploy the compilation service in Docker on this machine.

### Target {#remote type=remote config=devices/compiler_host.yaml default=true}

Deploy the compilation service remotely to another device over SSH.

### Troubleshooting

| Issue | Solution |
| --- | --- |
| Port 6052 occupied | Check conflicting processes or change the mapped port in config |
| Docker daemon not running | Start Docker Desktop or execute `sudo systemctl start docker` |

## Step 2: Build Firmware from Source {#builder type=script required=true config=devices/firmware_builder.yaml}

Send an ESPHome YAML to the compiler and get the firmware. Wi-Fi, Modbus address and registers are all set in that YAML. Leave the YAML field empty to build the bundled XY-MD02 template (`assets/esphome/xy_md02.yaml` in this solution); the board then opens the hotspot "xiao-rs485-fallback" for Wi-Fi setup. For another sensor, give that template and the sensor's Modbus register table to an AI assistant, answer its questions (model, address, registers, Wi-Fi), save the result as a .yaml file and enter its path.

### Prerequisites

- Step 1 compilation service is running on port 6052.
- Optional: your own ESPHome YAML file on this computer.

### Troubleshooting

| Issue | Solution |
| --- | --- |
| Cannot reach compiler service | Verify the IP address and ensure port 6052 is not blocked by a firewall |
| Compilation error 400 | Verify indentation in the YAML code (must use 2 spaces, no Tabs) |
| "ESPHome YAML not found" | Check the YAML path, or leave it empty to build the bundled XY-MD02 template |
| Board does not join Wi-Fi | Put your 2.4 GHz Wi-Fi in the YAML, or connect a phone to the "xiao-rs485-fallback" hotspot and enter it there |

## Step 3: Flash Firmware to Board {#flasher type=esp32_usb required=true config=devices/xiao_rs485.yaml}

Connect the XIAO gateway board via USB Type-C, select the serial port, and flash the compiled firmware.

### Prerequisites

- Seeed Studio XIAO board with RS485 expansion board.
- Target sensor (e.g. XY-MD02) and 12V DC power supply.
- USB Type-C data cable.

### Wiring

1. Mount the RS485 expansion board onto the XIAO board.
2. Signal wires: connect expansion board A+ to sensor A+, and B- to sensor B-.
3. Common ground: connect expansion board GND to sensor GND.
4. Power supply: 12V DC positive to sensor VCC, negative to sensor GND (shared with expansion board).

### Troubleshooting

| Issue | Solution |
| --- | --- |
| Serial port not detected | Re-plug USB data cable and check USB-UART drivers |
| Flashing timeout or chip not responding | Hold the BOOT button while plugging in the USB cable to enter download mode |

## Step 4: Verify Data in Home Assistant {#dashboard type=web_dashboard verify=true required=true config=devices/ha_dashboard.yaml}

Open Home Assistant to verify automatic discovery and view live sensor telemetry on the dashboard.

### Prerequisites

- A running Home Assistant instance on the same local network.
- Gateway device connected to 2.4 GHz Wi-Fi.

### Troubleshooting

| Issue | Solution |
| --- | --- |
| Device not discovered | Ensure Home Assistant and gateway board are on the same subnet |
| Values are empty or stale | Verify sensor 12V power supply and check if A+/B- polarity is reversed |

### After Setup

Deployment complete! Your legacy industrial sensors are now awake and streaming telemetry live into Home Assistant.
