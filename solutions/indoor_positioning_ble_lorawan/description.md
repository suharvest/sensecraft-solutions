## What This Solution Does

Where did that forklift go? Is the equipment still in the warehouse? Did the tracked vehicle leave the yard? This solution uses battery-powered BLE beacons indoors, GNSS outdoors, and long-range LoRaWAN backhaul, and draws both on the same map. Indoor floor plans can be georeferenced onto the outdoor map, so a trail that starts in a building and continues in the yard stays on one screen.

## Core Benefits

| Benefit | Details |
|---------|---------|
| Find things fast | Open the web dashboard, search by name, see location in seconds |
| No wiring needed | Stick BLE beacons on walls, run them on their own batteries |
| Indoor and outdoor on one map | BLE positions indoors, GNSS positions outdoors, switched by a hysteresis state machine instead of a manual toggle |
| Floor plan georeferencing | Drag, rotate and scale an uploaded floor plan onto the outdoor map; the parameters persist |
| Geofences | Draw a polygon or circle in WGS84, alarm on enter, exit or both, without needing any beacon inside the fence |
| Works offline | Swap the OpenStreetMap raster basemap for a local PMTiles archive when the site has no internet |
| Auto check-in | Automatic attendance when entering zones, no manual sign-in |
| One-button SOS | Trackers have an emergency button, long press for an instant alert |

## Use Cases

| Scenario | How It Works |
|----------|--------------|
| Warehouse logistics | Attach trackers to forklifts and goods, see locations on web map |
| Factory patrol | Workers carry trackers, system auto-records routes and timestamps |
| Campus safety | Students wear trackers, press SOS in emergencies, staff get instant location |
| Elderly care | Residents wear trackers, get alerts when they leave safe zones |
| Yard and perimeter control | Draw a geofence around the yard, alarm when a tracked vehicle enters or leaves |
| Asset protection | Attach trackers to valuable equipment, get alerts if moved |

## Nominal Figures

These come from the device datasheets and from the deployment practice for this
hardware. They are **nominal values, not measurements from this package** — the
figures that were actually measured are in the next section.

| Item | Nominal value | Where it comes from |
|---|---|---|
| Positioning accuracy (indoor) | 1-3 m with 3+ beacons per zone; room level with 1 beacon | BLE trilateration practice for this beacon layout |
| Beacon battery life | 2 years, typically up to 3 | BC03 beacon datasheet |
| Gateway range | Up to 2 km | SenseCAP M2 gateway datasheet, line of sight |
| Trackers per gateway | 100-200 in the same range | Gateway capacity, depends on uplink interval and region |

Installation practice that these figures assume: beacons at 2.5-3 m height,
10-15 m apart, extra beacons where there is metal shelving.

## Measured Boundaries

Everything in this table is a replay measurement of the server side. Synthetic
uplinks were published to a local MQTT broker and the results captured from the
dashboard WebSocket — **no real T1000 tracker and no real gateway were in the
loop**, so none of these rows says anything about radio coverage or about how
close a reported position is to the truth on the ground. Position ground-truth
error against a real T1000 is still to be measured.

Common conditions unless a row says otherwise: `solution-indoor-positioning`
branch `feature/outdoor` @ `443bce6`, run on a Jetson Orin Nano Super (Ubuntu
22.04.5, aarch64, no GPU) as a plain arm64 host — not in Docker, `uv sync` +
`uvicorn`. The replay tool and the WebSocket capture ran on a Mac reaching the
Jetson over Tailscale (ping avg 4.2 ms, 0% loss). Each tier ran only 2-4 minutes,
not the 30 minutes the evaluation protocol asks for.

| Metric | Measured | Conditions | Source |
|---|---|---|---|
| Capacity, stable | 200 concurrent tags, P95 end-to-end 828 ms, 0% uplink loss | one uplink per tag per 30 s, 800 uplinks, 2 min | this run, `runs/2026-09-05-orin-nano/boundary.capacity.yaml` |
| Capacity, degrading | 500 tags, P95 2.35 s, 0% loss | same, 2000 uplinks, 2 min; only the 2 s latency budget is missed | same |
| Capacity, at 1000 tags | P95 4.1 s, 0% loss, process still serving | same; no failure tier was reached, load was not pushed further | same |
| Update rate | 50 tags at a 2 s uplink interval, P95 220 ms, 0% loss over 4500 uplinks | 3 min; 30 s / 10 s / 5 s intervals were also all stable (P95 89 / 163 / 146 ms) | this run, `boundary.update_frequency.yaml` |
| SOS alarm latency | P50 24 ms, P95 29 ms, max 29 ms, n=20 | single tag, no concurrent load; uplink timestamp to WebSocket broadcast | this run, `boundary.sos_latency.yaml` |
| Offline detection | 903 s and 950 s | 2 repetitions, expected window [900 s, 960 s] from the hard-coded 15 min threshold and 60 s poll | this run, `boundary.offline_latency.yaml` |
| Geofence alarm latency | P50 14 ms, max 14 ms, 2 alarms | macOS loopback smoke run, single tag, 17 uplinks — not the Jetson run, and not a deployment-representative number | `runs/2026-09-05-geofence-smoke/results.md` |
| Geofence hysteresis | 6 in-and-out flips at the fence line produced 0 alarms; enter and exit each fired on the third consecutive point | same smoke run | same |
| Georeferencing error | <= 0.21 m anywhere within 2 km of the origin, \|lat\| <= 60 deg | worst case of an azimuth sweep (every 15 deg, radii 500/1000/2000 m, lat0 0/22.5/45/60); budget was 0.7 m | `runs/2026-09-05-georef/results.md` |
| Georeferencing, two implementations | Python vs JavaScript differ by 2.7e-20 deg; round trip closes to 7.5e-10 m | same fixture read by both unit-test suites | same |

Known gaps, carried from the implementation notes:

- **`accuracy` is always `null`.** Neither the SenseCAP nor the ChirpStack
  uplink carries a GNSS accuracy measurement, so the field exists end to end but
  has no data source. The geofence engine treats a missing `accuracy` as passing
  the accuracy gate and logs it per point; the accuracy buffer band around a
  fence boundary is therefore only covered by unit tests, never by a live run.
  The same applies to `alt`.
- No concurrency was layered under the SOS and geofence latency runs, so neither
  says what happens to alarm latency at 500+ tags.
- The offline threshold (15 min) and poll interval (60 s) are hard-coded, not
  configurable.
- The PMTiles offline basemap has not been exercised end to end: the build
  environment could not reach `build.protomaps.com`, so no archive was produced.

## Output Interfaces

| Interface | Endpoint | Payload |
|---|---|---|
| WebSocket | `ws://<host>:5173/ws` | `tracker_update` with a `position` that is either `{x, y, coordSystem: "metric"}` or `{lat, lon, accuracy, coordSystem: "wgs84"}`; `tracker_checkin` / `tracker_position_detection` carry an extra `geofence` block for enter / exit; `tracker_sos`; `tracker_offline` |
| REST | `GET/PUT /api/configuration/dashboard/maps/{mapName}/registration` | `{origin_lat, origin_lon, rotation_deg, scale}` |
| REST | `POST /api/geofences`, `POST /api/events` | Fence geometry (GeoJSON polygon, or point plus `radius_m`) and the alarm rule that references it |
| LoRaWAN uplink | SenseCAP OpenStream, or a ChirpStack MQTT topic | Field mapping is in the deployment guide |

Open source; integrates with third-party LoRaWAN network servers (ChirpStack,
TTN and similar) as well as the SenseCAP platform.

## Deployment Comparison

| Option | Coverage | Default Config | Best For |
|--------|----------|----------------|----------|
| **Starter Kit** ⭐ | Up to 500 sqm | 6 beacons + 1 tracker | Small office, first-time setup |
| **Standard Setup** | 500-2000 sqm | 15 beacons + 3 trackers | Medium warehouse, factory floor |
| **Enterprise** | 2000+ sqm | 30 beacons + 10 trackers | Large campus, multi-floor facilities |

All three run the same application image and the same feature set. Outdoor
tracking, georeferencing and geofences need no extra hardware beyond the T1000's
own GNSS — the presets differ only in beacon and tracker counts, i.e. in how much
indoor area gets metre-level coverage.

## Usage Notes

- Georeferencing is only meaningful within roughly 2 km of the origin; the local
  tangent-plane approximation is refused above \|lat\| 85 deg and its error grows
  with radius and latitude.
- Switching a tracker between indoor and outdoor display needs evidence to
  accumulate: 3 GNSS fixes within 20 s and 15 s without any configured beacon to
  go outdoor, two consecutive scans of 2+ configured beacons to come back in. The
  first two packets after a device comes online still use the simple rule
  (any lat/lon means outdoor).
- In geo mode the alarm rule's `time_range` field has no effect — the fence's own
  "3 consecutive points, 10 s" confirmation replaces it.
- The bundled MQTT broker configuration is for bench use. Put a broker with
  credentials in front of anything that leaves the lab.
