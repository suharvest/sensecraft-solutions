# Before you start

This system tracks people and assets **indoors with BLE beacons and outdoors
with the tracker's own GNSS**, and draws both on the same map. The three presets
below differ only in how many beacons and trackers you buy; they run the same
application image and have the same features.

The deployment is the same five hardware/software steps as before, plus two new
configuration steps: georeferencing the floor plan onto the outdoor map, and
setting up a geofence. The reference material for those two — basemaps, the
projection's limits, the geofence hysteresis defaults, the uplink field mapping —
is collected here once instead of being repeated under every preset.

**This is not a safety-certified system.** Positions can be late, wrong or
missing: LoRaWAN uplinks are lossy by design, GNSS does not work indoors, and BLE
trilateration degrades around metal. Do not use it as the only control on
anything where a missed or wrong position hurts someone.

**The application image tag is not published yet.** This package targets
`seeedcloud/sensecraft-indoor-positioning:outdoor-2026-09-05`, built from the
upstream `feature/outdoor` branch. Build and push that tag, or retag a local
build under the same name, before running the deployment step — the image that
was published earlier does not contain any of the outdoor features.

### Reference: outdoor maps and basemap choice

The map dropdown gets one extra entry, **Outdoor**, next to your floor plans;
there is also a standalone `/outdoor-map` route that subscribes to the same
WebSocket, for a wall display. A tracker is drawn on exactly one of the two — the
indoor Canvas view or the outdoor Leaflet view — never both.

Two basemap sources ship configured:

| Source | When to use it | Needs |
|---|---|---|
| OpenStreetMap raster tiles (default) | The host running the dashboard has internet | Outbound access to the OSM tile servers |
| Offline PMTiles archive | Air-gapped or unreliable site network | One `.pmtiles` file built in advance |

Amap and Tianditu are present as disabled templates. They serve GCJ-02
coordinates and no offset correction is implemented, so positions would land
tens of metres off. Leave them off.

Building an offline archive — do this on a machine with internet, not on site:

```bash
# macOS; or grab a release binary from github.com/protomaps/go-pmtiles
brew install protomaps/tap/pmtiles

# Do NOT download a planet file and cut it up. `extract` issues HTTP range
# requests and pulls only the tiles inside the bbox.
pmtiles extract \
  https://build.protomaps.com/20240401.pmtiles \
  data/pmtiles/demo.pmtiles \
  --bbox=113.9310,22.5230,113.9450,22.5330 \
  --maxzoom=18

pmtiles show data/pmtiles/demo.pmtiles
```

`--bbox` is `west,south,east,north` in decimal degrees. Start from your
registration origin and extend 1-2 km in every direction. The example above is
about 1.4 km x 1.1 km and produces a few MB.

Put the file in the `data/pmtiles` directory next to the compose file; it is
mounted read-only at `/app/uploads/pmtiles` and served through the existing
`/uploads` static mount. The preconfigured `pmtiles-offline` source points at
`/uploads/pmtiles/demo.pmtiles`; a different filename means editing that URL or
overriding `outdoor.tileSources` in `dashboard_config.json`. If the archive is
missing the map logs one console error and falls back to the online source.

Both basemaps carry OpenStreetMap data, so the ODbL attribution
"© OpenStreetMap contributors" and its link to
<https://www.openstreetmap.org/copyright> must stay visible. It is rendered by
default; do not remove it.

Not verified: no PMTiles archive has been built or loaded end to end in the
evaluation runs, because the build environment could not reach
`build.protomaps.com`. The UI switch and the fallback path were exercised, the
archive path was not.

### Reference: how floor-plan georeferencing works

Registration pins a floor plan to the earth with four numbers — origin latitude,
origin longitude, rotation in degrees, and scale — stored per map in
`dashboard_config.json` (no database table, no migration). A map without them is
simply indoor-only, exactly as before.

The transform is a local tangent plane at the origin. Its measured error is at
or below **0.21 m anywhere within 2 km of the origin at |lat| <= 60 deg**, which
is well inside the 0.7 m budget; the two implementations (server-side Python and
in-browser JavaScript) agree to 2.7e-20 degrees on the shared fixture, and a
round trip closes to 7.5e-10 m. Practical consequences: keep the origin near the
building rather than at some site-wide datum, and expect the approximation to be
refused above |lat| 85 deg.

Once a plan is registered, its metric history segments and its live points are
projected onto the same Leaflet map as the WGS84 segments. Segments in different
coordinate systems are never joined by a line — the gap at the switch point is
deliberate, not a rendering bug.

### Reference: geofences

A geofence is a WGS84 polygon (or multipolygon), or a circle given as a centre
and `radius_m`. An alarm rule with `location_mode: geo` references a fence and a
transition (`enter`, `exit`, or `both`), and — unlike the older BLE mode — needs
no beacon anywhere near the fence.

Defaults that decide whether an alarm fires:

| Parameter | Default | Effect |
|---|---|---|
| Confirmation | 3 consecutive points on the new side, spanning >= 10 s | A crossing shorter than three uplinks may not be reported at all |
| Accuracy gate | drop points with accuracy worse than 25 m | Never engages on this hardware — accuracy is always null |
| Buffer band | a point closer to the boundary than its own accuracy holds the current state | Also never engages, same reason |
| First observation | seeds inside/outside only | No spurious alarm right after a restart |
| Hysteresis scope | per (device, alarm rule) | Two rules on one fence count independently |

Enter alarms are broadcast as `tracker_checkin` and exit alarms as
`tracker_position_detection`, both carrying an extra `geofence` block; the stored
record has `pos_type: gps` and an empty `beacons` array. The rule's `time_range`
field has no effect in geo mode.

### Reference: GNSS fields in the uplink

Both integrations map the same measurement ids:

| Measurement id | Meaning | Notes |
|---|---|---|
| 4197 | Longitude | Validated with `is not None`, so a genuine 0.0 is kept |
| 4198 | Latitude | Both must be present for a GNSS fix to be accepted |
| 5002 | BLE scan results (MAC + RSSI) | Parsed even when the same packet has a GNSS fix |
| 3000 | Battery | On SenseCAP this is what closes a report |
| 4200 / 5003 | SOS (5003 event id 7) | |

A packet carrying both GNSS and BLE produces one combined report; the two
position results are appended to two separate history tracks, tagged
`coordSystem: wgs84` and `coordSystem: metric`. Which one the UI shows is decided
by the hysteresis state machine: 3 GNSS fixes within 20 s plus 15 s with no
configured beacon switches to outdoor; two consecutive scans of 2+ configured
beacons switch back to indoor. A beacon that is not in your configuration does
not count as evidence of being indoors. Until the state machine has enough
evidence — the first two packets after a device appears — the simple rule
applies: any valid lat/lon means outdoor.

**`accuracy` has no data source.** Neither SenseCAP nor ChirpStack sends a GNSS
accuracy measurement, so the field is carried end to end and is always `null`;
`alt` is the same. Everything that depends on it — the geofence accuracy gate and
the boundary buffer band — is therefore inert in the field and covered only by
unit tests. The server logs one line per point when it lets a null-accuracy point
through. If a future firmware adds the measurement, nothing structural has to
change.

### Reference: what has actually been measured

Replay measurements against the server, no real tracker and no real gateway in
the loop: 200 concurrent tags stable at P95 828 ms, 500 tags degrading at
P95 2.35 s, 1000 tags at P95 4.1 s with 0% loss and no crash; 50 tags at a 2 s
interval at P95 220 ms; SOS alarms at P50 24 ms; offline detection at 903 s and
950 s against a hard-coded 15 min threshold. Each tier ran 2-4 minutes on a
Jetson Orin Nano Super reached over Tailscale. Position error against ground
truth with a real T1000 has not been measured. Full conditions and sources are in
the solution description.

## Preset: Starter Kit {#starter}

Best for small offices or single rooms up to 500 sqm. Quick to set up, minimal hardware required.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1 | LoRaWAN network coverage |
| BC03 BLE Beacons | 6 | Indoor position reference points |
| SenseCAP T1000 Tracker | 1+ | Tracked asset/person, BLE scan indoors and GNSS outdoors |

**What you'll get:**
- Real-time indoor and outdoor location on one map
- Floor plans georeferenced onto the outdoor map
- Geofence alarms on enter/exit, with no beacon needed inside the fence

**Coverage:** Up to 500 sqm · 2 km LoRaWAN range (nominal)

**Important:** read the safety note and the measured-boundary summary at the top
of this guide before relying on any of this. Positions can be late, wrong or
missing, and `accuracy` is always null on this hardware.

## Step 1: Deploy BLE Beacons {#beacons type=manual required=true}

Place BLE beacons at fixed locations indoors as position reference points. Areas
covered by GNSS only (yards, roads, parking) need no beacons.

### Wiring

1. Place at least 3 beacons per area (trilateration) or 1 beacon (room level)
2. Install at 2.5-3 m height, 10-15 m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Beacon light not on | Battery depleted - replace the battery |
| Inaccurate positioning | Too few beacons or spacing too large - increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed - adjust installation position |
| Tracker stays "outdoor" inside the building | Only configured beacons count as indoor evidence - add the beacon's MAC to the map configuration |

---

## Step 2: Setup LoRaWAN Gateway {#gateway type=manual required=true}

Connect the gateway to enable wireless communication between tracker and positioning app.

### Wiring

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Issue | Solution |
|-------|----------|
| LED not on | Power issue - check power adapter and cable |
| LED blinking red | Network not connected - check Ethernet cable or WiFi configuration |
| App QR scan failed | Gateway not connected to internet - ensure gateway is online |
| Tracker data not reporting | Frequency band mismatch - confirm gateway and tracker use same band |

---

## Step 3: Deploy Positioning Application {#app_server type=docker_deploy required=true config=devices/app_deploy.yaml}

The image tag this package targets is not published yet - see the note at the top
of this guide.

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available
3. For an offline basemap, put the `.pmtiles` archive in `data/pmtiles` next to the compose file before deploying

### Deployment Complete

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment failed | Docker not running - start Docker Desktop |
| Image not found | The outdoor tag is not published - build it from the upstream branch and tag it locally |
| Port occupied | Other program using port 5173 - close the program or change port |
| Webpage won't open | Service not fully started - wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server
5. For an offline basemap, the `.pmtiles` archive must end up in `data/pmtiles` under the remote deploy directory

### Deployment Complete

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | IP or credentials incorrect - check IP address and username/password |
| Deployment failed | Remote server has no Docker - install Docker on the remote server |
| Image not found | The outdoor tag is not published - build and push it, or load it on the remote host |
| Webpage won't open | Firewall blocking - open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker type=manual required=true}

Set up the tracker and check that both position sources arrive.

### Wiring

1. Press power button 3 s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to the tracker
3. Select the correct LoRaWAN region, and enable both BLE scanning and GNSS positioning
4. Walk near beacons indoors, press the button to trigger a report, confirm the position appears on the floor plan
5. Walk outside, wait for a GNSS fix, confirm the tracker moves to the outdoor map

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Keeps blinking after power on | Failed to join network - check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Integration not configured - check the network server / SenseCAP settings in the dashboard |
| Position not updating | Tracker in sleep mode - press button to trigger report, or adjust reporting interval |
| Indoor position displayed incorrectly | Beacon coordinates misconfigured - check the beacon markers on the plan |
| Does not switch to outdoor | Needs 3 GNSS fixes within 20 s and 15 s without a configured beacon; a fix indoors near a window can keep it flapping |

---

## Step 5: Georeference the Floor Plan {#georeference type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

Pin the uploaded floor plan onto the outdoor map so indoor and outdoor trails
share one view. Skip only if you never need the two together.

### Prerequisites

- The floor plan is uploaded and its real-world size in metres is set
- You are logged in as `admin` - a guest session gets 403 on the registration endpoint
- The site is visible on the outdoor map (online OSM tiles, or your PMTiles archive)

### Wiring

1. Select the **Outdoor** entry in the map dropdown and pan to your site
2. Enter registration mode and pick the floor plan; the first guess is view centre, true north, scale 1
3. Use Drag / Rotate / Scale until the plan lines up with the building; the aspect ratio is locked
4. Check the toolbar numbers - origin lat, origin lon, rotation, scale - they stay in sync with the image both ways
5. Save; the dashboard confirms with "Registration saved."

Keep the origin within about 2 km of the area you care about. That is the radius
within which the measured projection error stays at or below 0.21 m.

### Deployment Complete

Reload the browser, re-enter registration mode and select the same plan: the four
parameters must still be the saved values. Then confirm that a tracker on that
plan and its metric trail now draw on the same Leaflet map as the WGS84 trail,
with no line joining the two across the switch point.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Save rejected with 422 | Latitude above 85 degrees, or scale 0 or negative |
| Save rejected with 403 | You are on a guest session - log in as admin |
| Parameters gone after reload | The save did not land - check `maps[].map.registration` in `dashboard_config.json` inside the container |
| Map jumps to blank blue after typing coordinates | The view follows the image on form edits; if it does not, pan back to the site and re-enter the numbers |
| Rotate/Scale handles do not appear | The overlay image had not finished loading - leave and re-enter registration mode |

---

## Step 6: Set Up a Geofence Alarm {#geofence type=manual required=true verify=true config=devices/geofence_setup.yaml}

Draw a fence in WGS84 and alarm when a tracker enters or leaves it. No beacon is
needed inside the fence.

### Prerequisites

- At least one tracker is reporting GNSS positions
- You know which direction you care about: enter, exit, or both

### Wiring

1. Create the geofence: a GeoJSON polygon, or a centre point plus `radius_m`
2. Create the alarm rule with `location_mode: geo`, point it at the fence, choose the transition
3. Review the hysteresis defaults in the reference section above - in particular the "3 consecutive points, 10 s" confirmation
4. Trigger a crossing: walk a tracker across the boundary, or replay `evaluation/traces/geofence_dwell.jsonl` with `evaluation/replay_chirpstack.py` from the upstream repository

### Deployment Complete

One enter alarm and one exit alarm appear, each on the third consecutive point on
the new side, and loitering on the boundary produces none - the reference run
flipped 6 times at the line with 0 alarms. The alarm shows in the dashboard alarm
list and in the WebSocket broadcast with a `geofence` block; the stored record has
`pos_type: gps` and an empty `beacons` array.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No alarm at all | The crossing was shorter than 3 uplinks, or shorter than 10 s - enlarge the fence or shorten the uplink interval |
| Alarm fires late | Expected: confirmation needs 3 consecutive points spanning at least 10 s |
| Alarm right after a restart | Should not happen - the first observation only seeds the state; if it does, the rule is duplicated |
| `time_range` has no effect | Correct - in geo mode the fence confirmation replaces it |
| Beacon selector still demanded | The rule is still in BLE mode - switch `location_mode` to geo |

---

## Step 7: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is live. Click below to open it in your browser.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine |
| Outdoor entry missing from the map dropdown | The running image is the pre-outdoor tag - redeploy with the outdoor tag |

---
### Deployment Complete

The system is ready.

#### Quick Verification

1. Walk a tracker near beacons indoors and confirm it appears on the floor plan
2. Walk outside and confirm it moves to the outdoor map after a few GNSS fixes
3. Cross a geofence boundary and confirm the alarm
4. Press the tracker button and confirm the SOS alarm

#### Next Steps

Basemaps, georeferencing limits, geofence defaults and the uplink field mapping
are all in the reference sections at the top of this guide.

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)

## Preset: Standard Setup {#standard}

Best for medium facilities (500-2000 sqm) like warehouses, offices, or retail stores.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1 | LoRaWAN network coverage |
| BC03 BLE Beacons | 15 | Indoor position reference points |
| SenseCAP T1000 Tracker | 3+ | Tracked asset/person, BLE scan indoors and GNSS outdoors |

**What you'll get:**
- Real-time indoor and outdoor location on one map
- Floor plans georeferenced onto the outdoor map
- Geofence alarms on enter/exit, with no beacon needed inside the fence

**Coverage:** 500-2000 sqm · 2 km LoRaWAN range (nominal)

**Important:** read the safety note and the measured-boundary summary at the top
of this guide before relying on any of this. Positions can be late, wrong or
missing, and `accuracy` is always null on this hardware.

## Step 1: Deploy BLE Beacons {#beacons_standard type=manual required=true}

Place BLE beacons at fixed locations indoors as position reference points. Areas
covered by GNSS only (yards, roads, parking) need no beacons.

### Wiring

1. Place at least 3 beacons per area (trilateration) or 1 beacon (room level)
2. Install at 2.5-3 m height, 10-15 m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Beacon light not on | Battery depleted - replace the battery |
| Inaccurate positioning | Too few beacons or spacing too large - increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed - adjust installation position |
| Tracker stays "outdoor" inside the building | Only configured beacons count as indoor evidence - add the beacon's MAC to the map configuration |

---

## Step 2: Setup LoRaWAN Gateway {#gateway_standard type=manual required=true}

Connect the gateway to enable wireless communication between tracker and positioning app.

### Wiring

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Issue | Solution |
|-------|----------|
| LED not on | Power issue - check power adapter and cable |
| LED blinking red | Network not connected - check Ethernet cable or WiFi configuration |
| App QR scan failed | Gateway not connected to internet - ensure gateway is online |
| Tracker data not reporting | Frequency band mismatch - confirm gateway and tracker use same band |

---

## Step 3: Deploy Positioning Application {#app_server_standard type=docker_deploy required=true config=devices/app_deploy.yaml}

The image tag this package targets is not published yet - see the note at the top
of this guide.

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available
3. For an offline basemap, put the `.pmtiles` archive in `data/pmtiles` next to the compose file before deploying

### Deployment Complete

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment failed | Docker not running - start Docker Desktop |
| Image not found | The outdoor tag is not published - build it from the upstream branch and tag it locally |
| Port occupied | Other program using port 5173 - close the program or change port |
| Webpage won't open | Service not fully started - wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server
5. For an offline basemap, the `.pmtiles` archive must end up in `data/pmtiles` under the remote deploy directory

### Deployment Complete

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | IP or credentials incorrect - check IP address and username/password |
| Deployment failed | Remote server has no Docker - install Docker on the remote server |
| Image not found | The outdoor tag is not published - build and push it, or load it on the remote host |
| Webpage won't open | Firewall blocking - open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker_standard type=manual required=true}

Set up the tracker and check that both position sources arrive.

### Wiring

1. Press power button 3 s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to the tracker
3. Select the correct LoRaWAN region, and enable both BLE scanning and GNSS positioning
4. Walk near beacons indoors, press the button to trigger a report, confirm the position appears on the floor plan
5. Walk outside, wait for a GNSS fix, confirm the tracker moves to the outdoor map

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Keeps blinking after power on | Failed to join network - check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Integration not configured - check the network server / SenseCAP settings in the dashboard |
| Position not updating | Tracker in sleep mode - press button to trigger report, or adjust reporting interval |
| Indoor position displayed incorrectly | Beacon coordinates misconfigured - check the beacon markers on the plan |
| Does not switch to outdoor | Needs 3 GNSS fixes within 20 s and 15 s without a configured beacon; a fix indoors near a window can keep it flapping |

---

## Step 5: Georeference the Floor Plan {#georeference_standard type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

Pin the uploaded floor plan onto the outdoor map so indoor and outdoor trails
share one view. Skip only if you never need the two together.

### Prerequisites

- The floor plan is uploaded and its real-world size in metres is set
- You are logged in as `admin` - a guest session gets 403 on the registration endpoint
- The site is visible on the outdoor map (online OSM tiles, or your PMTiles archive)

### Wiring

1. Select the **Outdoor** entry in the map dropdown and pan to your site
2. Enter registration mode and pick the floor plan; the first guess is view centre, true north, scale 1
3. Use Drag / Rotate / Scale until the plan lines up with the building; the aspect ratio is locked
4. Check the toolbar numbers - origin lat, origin lon, rotation, scale - they stay in sync with the image both ways
5. Save; the dashboard confirms with "Registration saved."

Keep the origin within about 2 km of the area you care about. That is the radius
within which the measured projection error stays at or below 0.21 m.

### Deployment Complete

Reload the browser, re-enter registration mode and select the same plan: the four
parameters must still be the saved values. Then confirm that a tracker on that
plan and its metric trail now draw on the same Leaflet map as the WGS84 trail,
with no line joining the two across the switch point.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Save rejected with 422 | Latitude above 85 degrees, or scale 0 or negative |
| Save rejected with 403 | You are on a guest session - log in as admin |
| Parameters gone after reload | The save did not land - check `maps[].map.registration` in `dashboard_config.json` inside the container |
| Map jumps to blank blue after typing coordinates | The view follows the image on form edits; if it does not, pan back to the site and re-enter the numbers |
| Rotate/Scale handles do not appear | The overlay image had not finished loading - leave and re-enter registration mode |

---

## Step 6: Set Up a Geofence Alarm {#geofence_standard type=manual required=true verify=true config=devices/geofence_setup.yaml}

Draw a fence in WGS84 and alarm when a tracker enters or leaves it. No beacon is
needed inside the fence.

### Prerequisites

- At least one tracker is reporting GNSS positions
- You know which direction you care about: enter, exit, or both

### Wiring

1. Create the geofence: a GeoJSON polygon, or a centre point plus `radius_m`
2. Create the alarm rule with `location_mode: geo`, point it at the fence, choose the transition
3. Review the hysteresis defaults in the reference section above - in particular the "3 consecutive points, 10 s" confirmation
4. Trigger a crossing: walk a tracker across the boundary, or replay `evaluation/traces/geofence_dwell.jsonl` with `evaluation/replay_chirpstack.py` from the upstream repository

### Deployment Complete

One enter alarm and one exit alarm appear, each on the third consecutive point on
the new side, and loitering on the boundary produces none - the reference run
flipped 6 times at the line with 0 alarms. The alarm shows in the dashboard alarm
list and in the WebSocket broadcast with a `geofence` block; the stored record has
`pos_type: gps` and an empty `beacons` array.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No alarm at all | The crossing was shorter than 3 uplinks, or shorter than 10 s - enlarge the fence or shorten the uplink interval |
| Alarm fires late | Expected: confirmation needs 3 consecutive points spanning at least 10 s |
| Alarm right after a restart | Should not happen - the first observation only seeds the state; if it does, the rule is duplicated |
| `time_range` has no effect | Correct - in geo mode the fence confirmation replaces it |
| Beacon selector still demanded | The rule is still in BLE mode - switch `location_mode` to geo |

---

## Step 7: Open Dashboard {#dashboard_standard type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is live. Click below to open it in your browser.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine |
| Outdoor entry missing from the map dropdown | The running image is the pre-outdoor tag - redeploy with the outdoor tag |

---
### Deployment Complete

The system is ready.

#### Quick Verification

1. Walk a tracker near beacons indoors and confirm it appears on the floor plan
2. Walk outside and confirm it moves to the outdoor map after a few GNSS fixes
3. Cross a geofence boundary and confirm the alarm
4. Press the tracker button and confirm the SOS alarm

#### Next Steps

Basemaps, georeferencing limits, geofence defaults and the uplink field mapping
are all in the reference sections at the top of this guide.

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)

## Preset: Enterprise {#enterprise}

Best for large campuses over 2000 sqm, multi-floor buildings, and sites with both indoor and outdoor areas.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1 | LoRaWAN network coverage |
| BC03 BLE Beacons | 30 | Indoor position reference points |
| SenseCAP T1000 Tracker | 10+ | Tracked asset/person, BLE scan indoors and GNSS outdoors |

**What you'll get:**
- Real-time indoor and outdoor location on one map
- Floor plans georeferenced onto the outdoor map
- Geofence alarms on enter/exit, with no beacon needed inside the fence

**Coverage:** 2000+ sqm · 2 km LoRaWAN range (nominal)

**Important:** read the safety note and the measured-boundary summary at the top
of this guide before relying on any of this. Positions can be late, wrong or
missing, and `accuracy` is always null on this hardware.

## Step 1: Deploy BLE Beacons {#beacons_enterprise type=manual required=true}

Place BLE beacons at fixed locations indoors as position reference points. Areas
covered by GNSS only (yards, roads, parking) need no beacons.

### Wiring

1. Place at least 3 beacons per area (trilateration) or 1 beacon (room level)
2. Install at 2.5-3 m height, 10-15 m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Beacon light not on | Battery depleted - replace the battery |
| Inaccurate positioning | Too few beacons or spacing too large - increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed - adjust installation position |
| Tracker stays "outdoor" inside the building | Only configured beacons count as indoor evidence - add the beacon's MAC to the map configuration |

---

## Step 2: Setup LoRaWAN Gateway {#gateway_enterprise type=manual required=true}

Connect the gateway to enable wireless communication between tracker and positioning app.

### Wiring

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Issue | Solution |
|-------|----------|
| LED not on | Power issue - check power adapter and cable |
| LED blinking red | Network not connected - check Ethernet cable or WiFi configuration |
| App QR scan failed | Gateway not connected to internet - ensure gateway is online |
| Tracker data not reporting | Frequency band mismatch - confirm gateway and tracker use same band |

---

## Step 3: Deploy Positioning Application {#app_server_enterprise type=docker_deploy required=true config=devices/app_deploy.yaml}

The image tag this package targets is not published yet - see the note at the top
of this guide.

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available
3. For an offline basemap, put the `.pmtiles` archive in `data/pmtiles` next to the compose file before deploying

### Deployment Complete

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment failed | Docker not running - start Docker Desktop |
| Image not found | The outdoor tag is not published - build it from the upstream branch and tag it locally |
| Port occupied | Other program using port 5173 - close the program or change port |
| Webpage won't open | Service not fully started - wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server
5. For an offline basemap, the `.pmtiles` archive must end up in `data/pmtiles` under the remote deploy directory

### Deployment Complete

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | IP or credentials incorrect - check IP address and username/password |
| Deployment failed | Remote server has no Docker - install Docker on the remote server |
| Image not found | The outdoor tag is not published - build and push it, or load it on the remote host |
| Webpage won't open | Firewall blocking - open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker_enterprise type=manual required=true}

Set up the tracker and check that both position sources arrive.

### Wiring

1. Press power button 3 s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to the tracker
3. Select the correct LoRaWAN region, and enable both BLE scanning and GNSS positioning
4. Walk near beacons indoors, press the button to trigger a report, confirm the position appears on the floor plan
5. Walk outside, wait for a GNSS fix, confirm the tracker moves to the outdoor map

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Keeps blinking after power on | Failed to join network - check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Integration not configured - check the network server / SenseCAP settings in the dashboard |
| Position not updating | Tracker in sleep mode - press button to trigger report, or adjust reporting interval |
| Indoor position displayed incorrectly | Beacon coordinates misconfigured - check the beacon markers on the plan |
| Does not switch to outdoor | Needs 3 GNSS fixes within 20 s and 15 s without a configured beacon; a fix indoors near a window can keep it flapping |

---

## Step 5: Georeference the Floor Plan {#georeference_enterprise type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

Pin the uploaded floor plan onto the outdoor map so indoor and outdoor trails
share one view. Skip only if you never need the two together.

### Prerequisites

- The floor plan is uploaded and its real-world size in metres is set
- You are logged in as `admin` - a guest session gets 403 on the registration endpoint
- The site is visible on the outdoor map (online OSM tiles, or your PMTiles archive)

### Wiring

1. Select the **Outdoor** entry in the map dropdown and pan to your site
2. Enter registration mode and pick the floor plan; the first guess is view centre, true north, scale 1
3. Use Drag / Rotate / Scale until the plan lines up with the building; the aspect ratio is locked
4. Check the toolbar numbers - origin lat, origin lon, rotation, scale - they stay in sync with the image both ways
5. Save; the dashboard confirms with "Registration saved."

Keep the origin within about 2 km of the area you care about. That is the radius
within which the measured projection error stays at or below 0.21 m.

### Deployment Complete

Reload the browser, re-enter registration mode and select the same plan: the four
parameters must still be the saved values. Then confirm that a tracker on that
plan and its metric trail now draw on the same Leaflet map as the WGS84 trail,
with no line joining the two across the switch point.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Save rejected with 422 | Latitude above 85 degrees, or scale 0 or negative |
| Save rejected with 403 | You are on a guest session - log in as admin |
| Parameters gone after reload | The save did not land - check `maps[].map.registration` in `dashboard_config.json` inside the container |
| Map jumps to blank blue after typing coordinates | The view follows the image on form edits; if it does not, pan back to the site and re-enter the numbers |
| Rotate/Scale handles do not appear | The overlay image had not finished loading - leave and re-enter registration mode |

---

## Step 6: Set Up a Geofence Alarm {#geofence_enterprise type=manual required=true verify=true config=devices/geofence_setup.yaml}

Draw a fence in WGS84 and alarm when a tracker enters or leaves it. No beacon is
needed inside the fence.

### Prerequisites

- At least one tracker is reporting GNSS positions
- You know which direction you care about: enter, exit, or both

### Wiring

1. Create the geofence: a GeoJSON polygon, or a centre point plus `radius_m`
2. Create the alarm rule with `location_mode: geo`, point it at the fence, choose the transition
3. Review the hysteresis defaults in the reference section above - in particular the "3 consecutive points, 10 s" confirmation
4. Trigger a crossing: walk a tracker across the boundary, or replay `evaluation/traces/geofence_dwell.jsonl` with `evaluation/replay_chirpstack.py` from the upstream repository

### Deployment Complete

One enter alarm and one exit alarm appear, each on the third consecutive point on
the new side, and loitering on the boundary produces none - the reference run
flipped 6 times at the line with 0 alarms. The alarm shows in the dashboard alarm
list and in the WebSocket broadcast with a `geofence` block; the stored record has
`pos_type: gps` and an empty `beacons` array.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No alarm at all | The crossing was shorter than 3 uplinks, or shorter than 10 s - enlarge the fence or shorten the uplink interval |
| Alarm fires late | Expected: confirmation needs 3 consecutive points spanning at least 10 s |
| Alarm right after a restart | Should not happen - the first observation only seeds the state; if it does, the rule is duplicated |
| `time_range` has no effect | Correct - in geo mode the fence confirmation replaces it |
| Beacon selector still demanded | The rule is still in BLE mode - switch `location_mode` to geo |

---

## Step 7: Open Dashboard {#dashboard_enterprise type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is live. Click below to open it in your browser.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine |
| Outdoor entry missing from the map dropdown | The running image is the pre-outdoor tag - redeploy with the outdoor tag |

---
### Deployment Complete

The system is ready.

#### Quick Verification

1. Walk a tracker near beacons indoors and confirm it appears on the floor plan
2. Walk outside and confirm it moves to the outdoor map after a few GNSS fixes
3. Cross a geofence boundary and confirm the alarm
4. Press the tracker button and confirm the SOS alarm

#### Next Steps

Basemaps, georeferencing limits, geofence defaults and the uplink field mapping
are all in the reference sections at the top of this guide.

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)
