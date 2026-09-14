# Agricultural Environment Monitoring

## What it does

SenseCAP LoRaWAN nodes measure air temperature and humidity, soil temperature, moisture, EC, CO2 and rainfall. This solution puts those readings on a Home Assistant dashboard, keeps history, and notifies you when a value crosses a threshold. Data can come through the SenseCAP cloud, or through a self-hosted The Things Stack or ChirpStack, which can run with no internet at all.

## What you get

- **A ready dashboard**: air temperature and humidity, soil temperature, moisture and EC, rainfall, battery and availability.
- **Threshold alerts**: a notification is raised when a value crosses a threshold and dismissed when it recovers.
- **Offline indication**: a node silent past the configured time shows as offline, with its last value kept.
- **Cloud history backfill**: the SenseCAP cloud preset fills in history from before installation on first start.
- **Switch paths without changing dashboards**: entity names are the same across all three presets.
- **Fully local option**: the ChirpStack preset needs no cloud account and no outbound connection.

## Where it fits

- Greenhouses: irrigation and feeding decided by soil moisture and EC.
- Open field plots: one gateway covering several sensor points.
- Sites with no internet, or where data may not leave (local ChirpStack preset).
- Existing SenseCAP cloud deployments that want a local dashboard and automations.

## Measured results

| Metric | Result |
|---|---|
| Node readings shown as live dashboard entities | **15 of 15** entities |
| Threshold notification raised and cleared | **Both directions** |
| Silent node marked offline | **15 of 15** entities |

Tested by replaying uplinks from 3 devices on a local host, 13 uplinks across the three ingest paths; take range, node capacity and battery life from the datasheets and measure them on site.

## Output Interfaces

| Interface | Content |
|---|---|
| MQTT `homeassistant/sensor/sensecap_<deveui>/<entity_key>/config` | Home Assistant discovery config |
| MQTT `agri_env/sensecap_<deveui>/<entity_key>/state` | Sensor value |
| MQTT `agri_env/sensecap_<deveui>/availability` | Node `online` / `offline` |

## Deployment Comparison

| | SenseCAP Cloud | Self-hosted The Things Stack | Local ChirpStack |
|---|---|---|---|
| Fits | Nodes already report to the cloud | You want to own the network server | M2 built-in network server, or R12 Series gateway |
| Internet needed | Yes | No | No |
| History from before install | Yes | No | No |
| Setup effort | Lightest; needs a SenseCAP API key | Heaviest | Shortest on M2 |

## Usage Notes

- Presets 2 and 3 need the SenseCAP decoder installed on the network server, or no entity appears.
- Two SenseCAP cloud MQTT hostnames exist; if the bridge log shows a DNS or authentication failure, redeploy with the other.
- If the broker is down, no preset receives updates.
- Before changing the entity naming rule, clear the broker's retained messages and Home Assistant's entity registry together.
- Do not expose the broker to the internet; on the ChirpStack preset the LNS-side broker has no authentication.

## Licensing note

The `measurementId` table in `assets/config/measurements.yaml` was read from `Seeed-Solution/SenseCAP-Decoder` (commit `d0a2342`), which has no LICENSE file, so its licence is unconfirmed. This package does not redistribute the decoder; it uses only the id-to-quantity correspondence and the guide links the upstream repository. Confirm the licensing position with Seeed before distributing the decoder itself.
