## Preset: Wio Weather Station Deployment {#default}

Deploy a self-contained environmental weather station on Wio Terminal. Operates completely standalone with an on-device dark-mode dashboard (4 joystick-navigated pages), with optional MQTT telemetry reporting to Home Assistant and AI Agent dashboard customization.

| Device | Purpose |
|---|---|
| Wio Terminal | Collects sensor data, drives the 2.4-inch LCD dashboard, and sends optional MQTT telemetry |
| Grove Beginner Kit (DHT11 & BMP280) | Environmental temperature, humidity, and barometric pressure sensing |

**What you'll get:**
- Completely standalone on-device dark-mode environmental dashboard on the Wio Terminal 2.4" TFT LCD across 4 interactive pages
- Optional Home Assistant integration with auto-discovered entities: temperature, humidity, pressure, illuminance, ambient noise, and Wi-Fi RSSI
- Configurable sensor polling intervals and physical button controls for manual refresh and discovery broadcasts
- Ready-to-use Lovelace YAML dashboard and AI Agent prompt template for instant UI customization

## Step 1: Flash Wio Weather Firmware {#flash_firmware type=wio_terminal_usb required=true config=devices/wio_terminal_deploy.yaml}

Flash the weather station firmware to the Wio Terminal over USB CDC.

### Prerequisites

1. Connect Wio Terminal to the computer using a USB Type-C data cable.
2. Ensure the 2.4 GHz Wi-Fi SSID and password are available (if Home Assistant integration is desired).
3. Ensure the Home Assistant MQTT Broker (Mosquitto) IP address and port are reachable (optional for standalone operation).
4. If automatic detection does not find the bootloader, slide the Wio Terminal power switch down twice quickly to enter bootloader mode (blue LED pulsing).

### Wiring

1. Connect the Grove BMP280 sensor to the **left Grove port (I2C)** using a 4-pin Grove cable.
2. Connect the Grove DHT11 sensor to the **right Grove port (D0/A0)** using a 4-pin Grove cable.
3. Ambient light and noise sensors use the onboard Wio Terminal sensors (zero extra wires).
4. Do not power the Grove Beginner Kit baseboard via its Micro-USB while connected to Wio Terminal to prevent dual-power conflicts.

### Troubleshooting

| Issue | Solution |
|---|---|
| Serial port not found | Check the USB cable for data lines; slide the power switch down twice quickly to enter bootloader mode |
| Bossac flashing fails | Ensure no serial monitor (e.g. Arduino IDE, PuTTY) is locking the serial port |
| Wi-Fi connection fails | Wio Terminal RTL8720DN supports 2.4 GHz Wi-Fi only; verify SSID and password |
| Sensors read invalid data | Check Grove cable seating; verify BMP280 is on the left (I2C) and DHT11 is on the right (D0) |

---

## Step 2: Configure Home Assistant & Dashboard {#ha_setup type=ha_integration required=false config=devices/ha_setup.yaml}

Automatically configure Home Assistant with the Mosquitto MQTT broker addon, MQTT integration entry, high temperature warning automation, and a dedicated Lovelace weather dashboard.

### Prerequisites

1. Home Assistant is running and reachable on your local network.
2. Administrator username and password for Home Assistant.
3. Wio Terminal has been flashed and is connected to Wi-Fi.

### What gets deployed

1. **Mosquitto MQTT Broker**: Supervisor addon installed and running.
2. **MQTT Integration**: Config entry pointing to your MQTT broker.
3. **Automations**: High temperature alert notifying when temperature exceeds 35°C.
4. **Dashboard**: `/wio-weather` Lovelace dashboard with gauges, entity cards, and 24h history trends for environmental telemetry.

### Troubleshooting

| Issue | Solution |
|---|---|
| Authentication failed | Check Home Assistant username and password |
| Entity discovery timeout | Press Button C on Wio Terminal to re-broadcast MQTT auto-discovery packets |
| Dashboard conflict | Ensure no existing dashboard with path `/wio-weather` is owned by another integration |

---

## Step 3: Customize Dashboard with AI Agent {#customize_ha_dashboard type=manual required=false config=devices/customize_ha_dashboard.yaml}

Leverage an AI coding assistant (Claude, ChatGPT, or Home Assistant Copilot) to generate a customized Lovelace dashboard for your Wio Terminal weather station.

### Prerequisites

1. Home Assistant is up and running, with sensor entities visible under **Developer Tools -> States** or **Settings -> Devices & Services -> MQTT**.
2. Identify your exact entity IDs (default `sensor.wio_weather_station_*` or `sensor.wio_weather_<mac>_*`).
3. Dashboard editing permissions in Home Assistant Lovelace.

### AI Agent Prompt Template

Copy the following structured prompt and provide it to your AI assistant (Claude, ChatGPT, or Home Assistant Copilot) along with your desired dashboard styling preferences:

```text
You are a Home Assistant UI specialist. Please generate a modern Lovelace Dashboard configuration in YAML for my Wio Terminal Desktop Environmental Weather Station.

Here is my entity manifest:
1. Temperature Sensor:
   - Entity ID: sensor.wio_weather_station_temperature
   - Unit: °C (Range: -10 to 50 °C)
   - Style: Gauge with green (18-26 °C), yellow (26-32 °C), red (>32 °C) thresholds.
2. Humidity Sensor:
   - Entity ID: sensor.wio_weather_station_humidity
   - Unit: % (Range: 0 to 100%)
   - Style: Gauge with optimal comfort band at 40-70%.
3. Atmospheric Pressure Sensor:
   - Entity ID: sensor.wio_weather_station_pressure
   - Unit: hPa (Typical Range: 950 to 1050 hPa)
   - Style: Gauge or numerical stat card with trend indicator.
4. Ambient Illuminance Sensor:
   - Entity ID: sensor.wio_weather_station_illuminance
   - Unit: lx (Range: 0 to 10000 lx)
   - Style: Compact entity card with dynamic mdi:white-balance-sunny icon.
5. Sound / Ambient Noise Level:
   - Entity ID: sensor.wio_weather_station_ambient_noise
   - Unit: dBA (Range: 30 to 100 dBA)
   - Style: Sound meter gauge with quiet (<55 dBA), moderate (55-70 dBA), high (>70 dBA) colored segments.
6. Wi-Fi Signal Strength:
   - Entity ID: sensor.wio_weather_station_wifi_rssi
   - Unit: dBm
   - Style: Entity row or sensor card showing signal strength.

Requirements:
- Structure the dashboard using vertical-stack and horizontal-stack cards.
- Include a 24-hour history graph comparing temperature, humidity, and atmospheric pressure.
- Clean, modern aesthetic suitable for desktop or tablet wall displays.
- Provide pure YAML ready to paste into Home Assistant Manual Card.
```

### Ready-to-Use Lovelace Dashboard YAML

You can also directly apply this Lovelace dashboard configuration:

```yaml
type: vertical-stack
title: Wio Terminal Weather Station
cards:
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.wio_weather_station_temperature
        name: Temperature
        min: -10
        max: 50
        needle: true
        severity:
          green: 18
          yellow: 26
          red: 32
      - type: gauge
        entity: sensor.wio_weather_station_humidity
        name: Humidity
        min: 0
        max: 100
        needle: true
        severity:
          red: 20
          green: 40
          yellow: 70
  - type: horizontal-stack
    cards:
      - type: gauge
        entity: sensor.wio_weather_station_pressure
        name: Barometric Pressure
        min: 900
        max: 1100
        needle: true
      - type: gauge
        entity: sensor.wio_weather_station_ambient_noise
        name: Ambient Noise
        min: 30
        max: 100
        needle: true
        severity:
          green: 30
          yellow: 55
          red: 70
  - type: entities
    title: Station Status & Lighting
    show_header_toggle: false
    entities:
      - entity: sensor.wio_weather_station_wifi_rssi
        name: Wi-Fi Signal
        icon: mdi:wifi
      - entity: sensor.wio_weather_station_illuminance
        name: Ambient Illuminance
        icon: mdi:white-balance-sunny
  - type: history-graph
    title: 24h Environmental Trends
    hours_to_show: 24
    refresh_interval: 60
    entities:
      - entity: sensor.wio_weather_station_temperature
        name: Temperature (°C)
      - entity: sensor.wio_weather_station_humidity
        name: Humidity (%)
      - entity: sensor.wio_weather_station_pressure
        name: Pressure (hPa)
```

### Deployment Complete

1. In Home Assistant, open your target Dashboard and click the pencil icon (**Edit Dashboard**) in the top right.
2. Click **+ Add Card**, scroll down to the bottom and select **Manual** (YAML mode).
3. Paste the generated or sample YAML code into the editor, check the live preview, and click **Save**.

### Troubleshooting

| Issue | Solution |
|---|---|
| Entities show "Entity not found" | Verify your Home Assistant entity IDs under Developer Tools -> States; replace `sensor.wio_weather_station_*` with your specific device entity IDs |
| Gauge ranges do not match local climate | Edit the Lovelace YAML `min`, `max`, and `severity` values to suit your indoor or outdoor environment |
| History graph shows "No state history found" | Ensure the recorder integration is active and wait a few minutes for initial state data points to accumulate |

---

## Step 4: Verify in Home Assistant Dashboard {#verify_ha type=web_dashboard required=false config=devices/verify_ha.yaml}

Open the Home Assistant web interface to verify the deployed `/wio-weather` Lovelace dashboard, automatic MQTT discovery, and sensor telemetry.

### What to check

1. Navigate to the `/wio-weather` dashboard from the sidebar or by opening `http://<ha-host>:<ha-port>/wio-weather`.
2. Check that real-time gauges for Temperature and Humidity update as new data arrives.
3. Check Barometric Pressure, Ambient Noise, Illuminance, and Wi-Fi RSSI cards.
4. Confirm that the 24-hour history graph plots historical trends.

### Troubleshooting

| Issue | Solution |
|---|---|
| Dashboard shows blank cards | Confirm that Wio Terminal is connected to Wi-Fi and sending MQTT packets; press Button C to re-broadcast discovery |
| URL unreachable | Check that Home Assistant is running on the specified host and port |
