# Agricultural Environment Monitoring

## What it does

SenseCAP LoRaWAN nodes measure soil and air — temperature, humidity, soil
moisture, electrical conductivity, CO2, rainfall — and report over LoRaWAN. This
package takes those uplinks, whichever way they arrive, and turns them into Home
Assistant entities with the right unit, device class and state class, so they
show up on a dashboard, keep history, and can trigger a notification when a
value crosses a threshold.

There are three ways in, and they end in the same place. Preset 1 reads the
SenseCAP cloud. Preset 2 reads a The Things Stack instance you run yourself.
Preset 3 reads ChirpStack — either the one built into an M2 gateway, or one you
run in Docker beside a WM1302 concentrator. A single service, `agri-env-bridge`,
sits behind all three: it maps SenseCAP `measurementId` values to entity
semantics, deduplicates, tracks whether each node is still reporting, and
publishes Home Assistant MQTT discovery messages.

## What you get

**One entity naming scheme across all three paths.** An entity is
`sensor.sensecap_<deveui>_<entity_key>` no matter which preset produced it. A
site can move from the cloud to a local network server without rewriting a
dashboard, an automation or an export.

**Availability that means something.** Each node has a retained availability
topic. When a node has been silent for longer than the configured threshold, it
flips to `offline` and its entities show as unavailable in Home Assistant — with
the last value kept rather than blanked. The default threshold is two S210x
reporting cycles plus margin.

**History on first start, on the cloud preset.** The bridge pages the SenseCAP
OpenAPI month by month and writes what it finds into a local SQLite store, keyed
on `(DevEUI, measurementId, timestamp)` so a backfill and the live stream never
double-count the same reading. Home Assistant receives the latest value per
entity; its own recorder history starts from the moment it comes online.

**A dashboard and threshold alerts to import.** A Lovelace dashboard covering air
temperature and humidity, soil temperature, moisture and EC, rainfall, battery
and availability, plus automations that raise a persistent notification when a
value crosses a threshold and dismiss it when the value recovers.

**An option with no internet at all.** With ChirpStack running on the gateway
itself and the bridge and Home Assistant on a local host, nothing needs to leave
the site — no cloud account, no outbound connection.

## Where it fits

- Greenhouses, where soil moisture and EC decide when to irrigate and feed.
- Open field plots, where the gateway covers several sensor points and rainfall
  and soil temperature matter more than air conditions.
- Sites with no usable internet, or where the data is not permitted to leave —
  the local ChirpStack preset covers both.
- Existing SenseCAP deployments that already report to the cloud and want a local
  dashboard and local automations without moving anything.

## How well it works

This solution has **not** been run against a real LoRaWAN network. Everything
below comes from one local smoke run on a Mac desktop Docker host with recorded
uplinks replayed into the broker — it is not hardware evidence, and it says
nothing about radio coverage, node capacity or end-to-end latency.

| Check | Result | Conditions | Source |
|---|---|---|---|
| Entities created by MQTT discovery | 15 entities across 3 devices | 13 replayed uplinks, three source formats (cloud, The Things Stack, ChirpStack) in one run | Local smoke, 2026-09-05 — not hardware |
| Unit, device class and state class applied | All 15 as configured | Read back from Home Assistant `GET /api/states` | Local smoke, 2026-09-05 — not hardware |
| Deduplication and latest-value selection | Correct on the one entity with two timestamps | Replay contained the same entity twice; the later value won | Local smoke, 2026-09-05 — not hardware |
| Availability flip to offline | All 15 entities went `unavailable` | Threshold shortened to 60 s for the test; watchdog scans every 15 s | Local smoke, 2026-09-05 — not hardware |
| Threshold notification raised and dismissed | Both directions | Soil moisture crossed below and back above the configured threshold; air temperature crossed above | Local smoke, 2026-09-05 — not hardware |

Not measured, and therefore not claimed: radio range, how many nodes one gateway
carries, packet loss and recovery, gateway restart time, node battery life,
end-to-end latency, and the behaviour of the SenseCAP OpenAPI backfill against a
live account. The bridge's cloud source has never held a real credential.

## Output Interfaces

| Interface | Topic | Payload |
|---|---|---|
| MQTT discovery | `homeassistant/sensor/sensecap_<deveui>/<entity_key>/config` | Retained discovery config, one per entity |
| MQTT state | `agri_env/sensecap_<deveui>/<entity_key>/state` | Retained value |
| MQTT availability | `agri_env/sensecap_<deveui>/availability` | Retained `online` or `offline` |

The Home Assistant entity id follows from the device name and the entity name:
`sensor.sensecap_<deveui>_<entity_key>`, with the DevEUI in lower case. It uses
the full DevEUI on purpose — a shortened form collides between nodes whose
addresses share a suffix.

## Deployment Comparison

**SenseCAP Cloud** — pick this when the nodes already report to the cloud and
you want a local dashboard without touching the radio side. It is the only
preset that can show history from before it was installed, and the only one that
needs outbound internet. It also needs a SenseCAP API key pair.

**Self-hosted The Things Stack** — pick this when you want the network server
under your own control and are prepared to build a gateway: a WM1302
concentrator on a CM4 host, a packet forwarder, and a stack with its own
Postgres and Redis. The heaviest of the three in both setup effort and resource
use.

**Local ChirpStack** — pick this when the gateway can be the network server. On
an M2 the whole network server is a setting in its web interface, which makes
this the shortest path to a fully local deployment; on a CM4 host with a WM1302
it is a Docker stack instead. This is the preset the offline acceptance scenario
uses.

## Usage Notes

- **The decoder is not optional on presets 2 and 3.** SenseCAP uplinks are
  binary. Without the payload formatter (The Things Stack) or the device-profile
  codec (ChirpStack) installed, the network server hands the bridge bytes with no
  measurements in them, and no entity can appear. The bridge cannot recover what
  the network server did not decode.
- **Two SenseCAP cloud MQTT hostnames are in circulation and neither has been
  confirmed.** The deployment step offers both. If the bridge log shows a DNS or
  authentication failure, redeploy with the other one.
- **The broker is a single point of failure for the dashboard.** State topics are
  retained, so Home Assistant recovers the last value after a restart, but a
  broker that is down means no updates from any preset.
- **Values are passed through, not converted.** The bridge attaches the unit
  configured for a `measurementId` and does not scale the number. If a particular
  node model reports a quantity in a different unit, correct it in
  `assets/config/measurements.yaml` — no code change is needed.
- **Changing the entity naming rule requires clearing retained messages.**
  Discovery configs are retained, so old topics come back after a restart unless
  the broker's retained messages and Home Assistant's entity registry are cleared
  together.
- **Do not expose the broker to the internet.** It carries credentials in
  `.env` files on the host and, on the ChirpStack preset, the LNS-side broker runs
  without authentication on the compose network. Both are safe on a trusted LAN
  and not elsewhere.
- **The bridge image is not published yet.** `agri-env-bridge:0.1.0` exists as a
  tag reference only; build it locally before deploying, or point `BRIDGE_IMAGE`
  at your own registry.

## Licensing note

The `measurementId` to physical quantity table in
`assets/config/measurements.yaml` was read out of the SenseCAP decoder sources at
`Seeed-Solution/SenseCAP-Decoder` commit `d0a2342`. **That repository has no
LICENSE file**, and its README has no licensing section; the only licence
declaration anywhere in it is a third-party contributed file header reading
`Unlicensed for internal use`. The licence for the decoder is therefore
**unconfirmed**.

This package does not redistribute the decoder. It uses only the factual
`id -> quantity` correspondence, cites the source file and line for each entry,
and derives the Home Assistant `device_class`, `unit_of_measurement` and
`state_class` columns from the Home Assistant sensor documentation instead. The
guide links the upstream repository for presets 2 and 3 rather than shipping the
JavaScript. Confirm the licensing position with Seeed before distributing the
decoder itself with a deployment.
