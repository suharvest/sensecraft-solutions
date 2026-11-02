# Wio Terminal Weather Station & Home Assistant Gateway

## Overview

The Wio Terminal Weather Station is a self-contained desktop environmental monitoring station and modular IoT gateway. Powered by an ATSAMD51P19A Cortex-M4F core running at 120 MHz with an onboard Realtek RTL8720DN dual-band Wi-Fi module, it operates as a 100% standalone desktop device without requiring an active network connection, external hub, or Home Assistant instance. Local atmospheric and acoustic data are measured and rendered directly onto the integrated 2.4-inch 320x240 TFT LCD in a modern dark-mode geek aesthetic across four interactive pages controlled via the 5-way joystick.

When connected to a 2.4 GHz Wi-Fi network, the station optionally functions as an IoT gateway, streaming telemetry to Home Assistant using automatic MQTT Discovery. Users can further personalize their dashboard using an AI coding assistant (Claude, ChatGPT, or Home Assistant Copilot) with the included prompt template.

### System Architecture

```
+-------------------------------------------------------------+
|                      Wio Terminal                           |
|       ATSAMD51 (120MHz) + RTL8720DN (2.4GHz Wi-Fi)          |
|-------------------------------------------------------------|
|  2.4" TFT LCD Display (320x240) - Standalone Dashboard      |
|  - Page 0: Environmental Overview                           |
|  - Page 1: Temperature & Humidity Progression               |
|  - Page 2: Barometric Pressure & Noise Monitor              |
|  - Page 3: Wi-Fi RSSI, IP & MQTT Diagnostic                 |
|-------------------------------------------------------------|
|  Onboard Sensors:                                           |
|  - Analog Light Sensor (PD01 / A0)                          |
|  - Electret Microphone (PD08 / A2)                          |
|-------------------------------------------------------------|
|  Grove Expansion Connectors:                                |
|  - Left Grove (I2C): Grove BMP280 Barometric Sensor         |
|  - Right Grove (D0/A0): Grove DHT11 Temp & Humidity Sensor  |
+-------------------------------------------------------------+
          |                                         |
 (Standalone Local Loop)                 (Optional Wi-Fi Uplink)
          |                                         |
          v                                         v
 [Real-Time LCD UI]                 +----------------------------+
 [Joystick Navigation]              | Home Assistant MQTT Broker |
 [Local Audio RMS]                  |  - Discovery: retain=true  |
                                    |  - Telemetry: QoS 0        |
                                    |  - LWT: Status topic       |
                                    +----------------------------+
```

## Key Benefits

| Benefit | Details |
|---|---|
| Zero-Network Standalone Operation | Runs completely offline on 5V USB Type-C power; no gateway, cloud account, or Wi-Fi required for local monitoring |
| Rich Dark-Mode LCD UI | Integrated 2.4-inch 320x240 color display with 4 dedicated screens navigated seamlessly via the 5-way joystick |
| Modular Grove Expansion | Dual Grove ports (I2C and GPIO/ADC) support plug-and-play sensors with configurable sampling and refresh cadences |
| Native Home Assistant Gateway | Automatic MQTT Discovery registers all environmental and acoustic entities with zero manual YAML configuration |
| AI-Assisted Personalization | Prompt template empowers AI assistants to craft tailored Lovelace dashboard cards matching individual aesthetics |

### Standalone Operation & Extensibility

#### 1. Zero-Network Self-Contained Desktop Operation
- **Immediate Out-of-the-Box Display**: Powers up instantly over standard 5V USB Type-C. No Wi-Fi association, cloud account, or gateway pairing is needed for primary operation.
- **Hardware-Accelerated UI**: The ATSAMD51 Cortex-M4F handles real-time sensor polling, calibration, sound pressure level RMS filtering, and TFT LCD rendering in a standalone execution loop.
- **Interactive Multi-Page Navigation**: The physical 5-way analog joystick enables smooth navigation across 4 dedicated monitoring screens.

#### 2. Modular Grove Sensor Expansion & Customizable Rates
- **Dual Grove Expansion Slots**:
  - **Left Grove Port (Hardware I2C)**: Default connected to BMP280; compatible with Grove I2C sensors such as Grove - SGP30 / SCD30 (air quality & CO2), Grove - Sunlight Sensor (SI1145), or Grove - OLED display modules.
  - **Right Grove Port (Configurable GPIO / ADC)**: Default connected to DHT11; accepts any digital or analog Grove modules such as Grove - Dust Sensor (HM3301), Grove - Soil Moisture Sensor, or Grove - PIR Motion Sensor.
- **Customizable Sampling & Refresh Cadence**:
  - LCD screen refresh rate: Default 1 Hz for responsive acoustic meter tracking.
  - Meteorological sensor polling: Default 2 to 5 seconds for smooth climate trends.
  - Optional MQTT telemetry publish interval: Configurable independently to minimize network traffic and power consumption.

### On-Screen Dashboard UI

The display pipeline runs four screens navigated via the 5-way analog joystick (Left / Right):

1. **Page 0: Overview**: Displays temperature (°C), relative humidity (%), atmospheric pressure (hPa), and illuminance (lx) across a 2x2 grid.
2. **Page 1: Temperature & Humidity**: Full-scale linear gauges showing current readings alongside thermal comfort index classifications.
3. **Page 2: Barometric Pressure & Noise**: Dynamic pressure trend analysis alongside a real-time sound pressure level gauge graded into five acoustic ranges: Quiet (<45 dBA), Comfort (45-55 dBA), Moderate (55-65 dBA), Noisy (65-75 dBA), and Hazard (>75 dBA).
4. **Page 3: System Status & Diagnostic**: Network status including allocated IP address, Wi-Fi RSSI signal strength bar, MQTT broker reachability, total telemetry transmission count, and Home Assistant discovery broadcast state.

Physical button controls:
- **Button A (Top Right)**: Forces immediate telemetry publish to the MQTT broker.
- **Button C (Top Left)**: Re-transmits Home Assistant Auto-Discovery configuration payloads.

### Home Assistant MQTT Discovery Protocol

When network transmission is enabled, the firmware registers all sensors via standard MQTT Discovery topics upon network association:

- **Discovery Config Topic**: `homeassistant/sensor/Wio-Weather-<MAC>/<component>/config` (retained)
- **State Topic**: `wio-weather/telemetry`
- **Availability / LWT Topic**: `wio-weather/status` (`online` / `offline`)

Discovered entities:

| Entity Name | Sensor Component | Device Class | Unit |
|---|---|---|---|
| Temperature | `sensor.wio_weather_<mac>_temperature` | `temperature` | `°C` |
| Humidity | `sensor.wio_weather_<mac>_humidity` | `humidity` | `%` |
| Barometric Pressure | `sensor.wio_weather_<mac>_pressure` | `atmospheric_pressure` | `hPa` |
| Ambient Light | `sensor.wio_weather_<mac>_illuminance` | `illuminance` | `lx` |
| Ambient Noise | `sensor.wio_weather_<mac>_ambient_noise` | `sound_pressure` | `dBA` |
| Wi-Fi Signal | `sensor.wio_weather_<mac>_wifi_rssi` | `signal_strength` | `dBm` |

### AI-Assisted Dashboard Customization

To build a personalized Home Assistant dashboard, users can provide the included AI Agent Prompt template to Claude, ChatGPT, or Home Assistant Copilot. The prompt contains the full entity manifest with ranges and display guidelines:
- `sensor.wio_weather_station_temperature`: -10 to 50 °C with multi-tier thermal comfort bands
- `sensor.wio_weather_station_humidity`: 0 to 100% with optimal 40-70% band
- `sensor.wio_weather_station_pressure`: 950 to 1050 hPa barometric gauge
- `sensor.wio_weather_station_light`: 0 to 10000 lx ambient illuminance
- `sensor.wio_weather_station_noise`: 30 to 100 dBA multi-colored sound level meter
- `sensor.wio_weather_station_status`: Online connectivity badge
- 24-hour multi-sensor historical trends via `history-graph`

## Application Scenarios

| Scenario | Description |
|---|---|
| Standalone Desktop Weather & Acoustic Monitor | Workstation or nightstand placement providing immediate local climate and sound-level readings with zero network or server dependencies |
| Home Assistant Smart Home Sensor Node | Seamless integration with smart home automation to trigger humidifiers, air conditioners, heating, or lighting scenes |
| Quiet Zone & Acoustic Compliance Monitoring | Real-time dBA noise metering for study areas, home offices, recording spaces, or libraries with multi-level threshold alerts |
| STEM Education & Embedded IoT Prototyping | Educational exploration of ATSAMD51 embedded development, LCD GUI rendering, Grove modular sensor interfacing, and MQTT protocols |

## Usage Notes & Requirements

### Hardware Wiring & Pin Mapping

The physical interface uses standard 4-pin Grove connectors on the bottom of the Wio Terminal casing:

| Sensor / Module | Physical Port | Interface Type | Pin Mapping | Operating Parameters |
|---|---|---|---|---|
| Grove BMP280 | Left Grove Port | Hardware I2C | SCL (D5), SDA (D4) | Address `0x76` / `0x77`, range 300-1100 hPa |
| Grove DHT11 | Right Grove Port | Digital GPIO | Signal (D0), VCC (3.3V), GND | Range 0-50 °C (±2 °C), 20-90% RH (±5%) |
| Onboard Light Sensor | Internal | Analog ADC | `WIO_LIGHT` (PD01 / A0) | Converted to illuminance (lx) |
| Onboard Microphone | Internal | Analog ADC | `WIO_MIC` (PD08 / A2) | RMS sampling converted to sound level (dBA) |

> When using sensor modules from a Grove Beginner Kit, decouple the module signals from the ATmega328P baseboard by snapping the module along the PCB perforations or disconnecting power from the Beginner Kit Micro-USB port.

### Network & Power Requirements

- **Power Supply**: Standard 5V USB Type-C power input (500mA minimum).
- **Wi-Fi Connectivity (Optional)**: 2.4 GHz Wi-Fi network (802.11 b/g/n). Required only for Home Assistant MQTT telemetry and dashboard integration; standalone LCD display operates without Wi-Fi.
- **Home Assistant & MQTT Broker (Optional)**: A reachable MQTT broker (e.g., Mosquitto MQTT add-on in Home Assistant) on the local network if remote telemetry is desired.
