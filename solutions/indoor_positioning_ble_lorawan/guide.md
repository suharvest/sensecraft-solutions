## Preset: Starter Kit {#starter}

For small offices or single rooms up to 500 sqm. Positions indoors come from BLE beacons and outdoors from the tracker's own GNSS, drawn on one map, with geofence enter/exit alarms.

- **Hardware:** 1 SenseCAP M2 gateway, 9 BC03 BLE beacons, 1+ SenseCAP T1000 trackers.
- **Coverage:** Up to 500 sqm, 2 km LoRaWAN range (nominal).
- **Server:** a computer or server with Docker to run the positioning application.

**Limitation:** this is not a safety-certified system. Positions can be late, wrong or missing (LoRaWAN uplinks can be lost, GNSS does not work indoors, BLE positioning degrades around metal). Do not use it as the only control where a wrong or missing position can hurt someone.

## Step 1: Deploy BLE Beacons {#beacons type=manual required=true}

Place BLE beacons at fixed locations indoors as position reference points. Areas
covered by GNSS only (yards, roads, parking) need no beacons.

### Wiring

1. Place at least 3 beacons per area (trilateration) or 1 beacon (room level)
2. Install at 2.5-3 m height, 5-10 m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Beacon light not on | Replace the battery |
| Inaccurate positioning | Add beacons or reduce spacing |
| Tracker can't scan beacons | Move the beacon so it is not too high or obstructed |
| Tracker stays "outdoor" inside the building | Add the beacon's MAC to the map configuration; unconfigured beacons do not count as indoor |

---

## Step 2: Setup LoRaWAN Gateway {#gateway type=manual required=true}

Connect the gateway to enable wireless communication between tracker and positioning app.

### Wiring

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Symptom | Action |
|---------|--------|
| LED not on | Check the power adapter and cable |
| LED blinking red | Check the Ethernet cable or WiFi configuration |
| App QR scan failed | Make sure the gateway is online |
| Tracker data not reporting | Confirm gateway and tracker use the same frequency band |

---

## Step 3: Deploy Positioning Application {#app_server type=docker_deploy required=true config=devices/app_deploy.yaml}

Deploy the positioning application. Prepare the application image first (see the preset notes).

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available
3. For an offline basemap, put the `.pmtiles` map file in `data/pmtiles` next to the compose file before deploying

### Deployment Complete

1. Visit `http://localhost:5173`, log in with `admin` / `12345678` (change the default password under Configuration → Authentication after logging in)
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Deployment failed | Start Docker Desktop |
| Image not found | Build the image from the upstream branch and tag it locally |
| Port occupied | Close the program using port 5173 or change the port |
| Webpage won't open | Wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server
5. For an offline basemap, put the `.pmtiles` map file in `data/pmtiles` under the remote deploy directory

### Deployment Complete

1. Visit `http://<device-ip>:5173`, log in with `admin` / `12345678` (change the default password under Configuration → Authentication after logging in)
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Symptom | Action |
|---------|--------|
| SSH connection failed | Check the IP address and username/password |
| Deployment failed | Install Docker on the remote server |
| Image not found | Build and push the image, or load it on the remote host |
| Webpage won't open | Open port 5173 in the remote server's firewall |

---

## Step 4: Configure and Activate Tracker {#tracker type=manual required=true}

Set up the tracker and confirm both indoor and outdoor positions are reported.

### Wiring

1. Press power button 3 s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to the tracker
3. Select the correct LoRaWAN region, and enable both BLE scanning and GNSS positioning
4. Walk near beacons indoors, press the button to trigger a report, confirm the position appears on the floor plan
5. Walk outside, wait for a GNSS fix, confirm the tracker moves to the outdoor map

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Keeps blinking after power on | Check the gateway is online and the frequency band matches |
| Tracker not visible on webpage | Check the network server / SenseCAP integration settings in the dashboard |
| Position not updating | Press the button to trigger a report, or adjust the reporting interval |
| Indoor position displayed incorrectly | Check the beacon markers on the plan |
| Does not switch to outdoor | Needs 3 GNSS fixes within 20 s and 15 s without a configured beacon; near a window it can switch back and forth |

---

## Step 5: Georeference the Floor Plan {#georeference type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

Align the floor plan with the outdoor map so indoor and outdoor trails show in one view. Skip it if you do not need the two together.

### Prerequisites

- The floor plan is uploaded and its real-world size in metres is set
- You are logged in as `admin`
- The site is visible on the outdoor map (online OSM map, or an offline `.pmtiles` map)

### Wiring

1. Select the **Outdoor** entry in the map dropdown and pan to your site
2. Enter registration mode and pick the floor plan
3. Use Drag / Rotate / Scale until the plan lines up with the building
4. Check the toolbar values: origin lat, origin lon, rotation, scale
5. Save; the dashboard confirms with "Registration saved."

Keep the origin within about 2 km of the area you care about.

### Deployment Complete

Reload the browser, re-enter registration mode and select the same plan: the four parameters are still the saved values, and trackers on that plan draw on the same map as outdoor trails.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Save rejected with 422 | Latitude must not exceed 85 degrees and scale must be above 0 |
| Save rejected with 403 | Log in as `admin` |
| Parameters gone after reload | Save again and confirm "Registration saved." appears |
| Map jumps to blank blue after typing coordinates | Pan back to the site and re-enter the numbers |
| Rotate/Scale handles do not appear | Leave and re-enter registration mode |

---

## Step 6: Set Up a Geofence Alarm {#geofence type=manual required=true verify=true config=devices/geofence_setup.yaml}

Draw a fence on the outdoor map and alarm when a tracker enters or leaves it. No beacon is needed inside the fence.

### Prerequisites

- At least one tracker is reporting GNSS positions
- You know which direction to alarm on: enter, exit, or both

### Wiring

1. Create the geofence: a GeoJSON polygon, or a centre point plus `radius_m`
2. Create the alarm rule with `location_mode: geo`, point it at the fence, choose the transition
3. Walk a tracker across the boundary. An alarm needs 3 consecutive points on the new side spanning at least 10 s

### Deployment Complete

One enter alarm and one exit alarm appear, and loitering on the boundary produces none. The alarms show in the dashboard alarm list.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| No alarm at all | The crossing was shorter than 3 uplinks or 10 s; enlarge the fence or shorten the uplink interval |
| Alarm fires late | Expected: confirmation needs 3 consecutive points spanning at least 10 s |
| Alarm right after a restart | Check whether the same rule is configured twice |
| `time_range` has no effect | Expected: geo mode does not use it |
| Beacon selector still demanded | Switch `location_mode` to `geo` |

---

## Step 7: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is live. Click below to open it in your browser.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine |
| Outdoor entry missing from the map dropdown | Redeploy with the outdoor image tag |

---
### Deployment Complete

The system is ready.

#### Quick Verification

1. Walk a tracker near beacons indoors and confirm it appears on the floor plan
2. Walk outside and confirm it moves to the outdoor map after a few GNSS fixes
3. Cross a geofence boundary and confirm the alarm
4. Double-press the tracker button and confirm the SOS alarm

#### Next Steps

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)

## Preset: Standard Setup {#standard}

For medium facilities (500-2000 sqm) such as warehouses, offices or retail stores. Positions indoors come from BLE beacons and outdoors from the tracker's own GNSS, drawn on one map, with geofence enter/exit alarms.

- **Hardware:** 1 SenseCAP M2 gateway, 23 BC03 BLE beacons, 3+ SenseCAP T1000 trackers.
- **Coverage:** 500-2000 sqm, 2 km LoRaWAN range (nominal).
- **Server:** a computer or server with Docker to run the positioning application.

**Limitation:** this is not a safety-certified system. Positions can be late, wrong or missing (LoRaWAN uplinks can be lost, GNSS does not work indoors, BLE positioning degrades around metal). Do not use it as the only control where a wrong or missing position can hurt someone.

## Step 1: Deploy BLE Beacons {#beacons_standard type=manual required=true}

Place BLE beacons at fixed locations indoors as position reference points. Areas
covered by GNSS only (yards, roads, parking) need no beacons.

### Wiring

1. Place at least 3 beacons per area (trilateration) or 1 beacon (room level)
2. Install at 2.5-3 m height, 5-10 m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Beacon light not on | Replace the battery |
| Inaccurate positioning | Add beacons or reduce spacing |
| Tracker can't scan beacons | Move the beacon so it is not too high or obstructed |
| Tracker stays "outdoor" inside the building | Add the beacon's MAC to the map configuration; unconfigured beacons do not count as indoor |

---

## Step 2: Setup LoRaWAN Gateway {#gateway_standard type=manual required=true}

Connect the gateway to enable wireless communication between tracker and positioning app.

### Wiring

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Symptom | Action |
|---------|--------|
| LED not on | Check the power adapter and cable |
| LED blinking red | Check the Ethernet cable or WiFi configuration |
| App QR scan failed | Make sure the gateway is online |
| Tracker data not reporting | Confirm gateway and tracker use the same frequency band |

---

## Step 3: Deploy Positioning Application {#app_server_standard type=docker_deploy required=true config=devices/app_deploy.yaml}

Deploy the positioning application. Prepare the application image first (see the preset notes).

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available
3. For an offline basemap, put the `.pmtiles` map file in `data/pmtiles` next to the compose file before deploying

### Deployment Complete

1. Visit `http://localhost:5173`, log in with `admin` / `12345678` (change the default password under Configuration → Authentication after logging in)
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Deployment failed | Start Docker Desktop |
| Image not found | Build the image from the upstream branch and tag it locally |
| Port occupied | Close the program using port 5173 or change the port |
| Webpage won't open | Wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server
5. For an offline basemap, put the `.pmtiles` map file in `data/pmtiles` under the remote deploy directory

### Deployment Complete

1. Visit `http://<device-ip>:5173`, log in with `admin` / `12345678` (change the default password under Configuration → Authentication after logging in)
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Symptom | Action |
|---------|--------|
| SSH connection failed | Check the IP address and username/password |
| Deployment failed | Install Docker on the remote server |
| Image not found | Build and push the image, or load it on the remote host |
| Webpage won't open | Open port 5173 in the remote server's firewall |

---

## Step 4: Configure and Activate Tracker {#tracker_standard type=manual required=true}

Set up the tracker and confirm both indoor and outdoor positions are reported.

### Wiring

1. Press power button 3 s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to the tracker
3. Select the correct LoRaWAN region, and enable both BLE scanning and GNSS positioning
4. Walk near beacons indoors, press the button to trigger a report, confirm the position appears on the floor plan
5. Walk outside, wait for a GNSS fix, confirm the tracker moves to the outdoor map

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Keeps blinking after power on | Check the gateway is online and the frequency band matches |
| Tracker not visible on webpage | Check the network server / SenseCAP integration settings in the dashboard |
| Position not updating | Press the button to trigger a report, or adjust the reporting interval |
| Indoor position displayed incorrectly | Check the beacon markers on the plan |
| Does not switch to outdoor | Needs 3 GNSS fixes within 20 s and 15 s without a configured beacon; near a window it can switch back and forth |

---

## Step 5: Georeference the Floor Plan {#georeference_standard type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

Align the floor plan with the outdoor map so indoor and outdoor trails show in one view. Skip it if you do not need the two together.

### Prerequisites

- The floor plan is uploaded and its real-world size in metres is set
- You are logged in as `admin`
- The site is visible on the outdoor map (online OSM map, or an offline `.pmtiles` map)

### Wiring

1. Select the **Outdoor** entry in the map dropdown and pan to your site
2. Enter registration mode and pick the floor plan
3. Use Drag / Rotate / Scale until the plan lines up with the building
4. Check the toolbar values: origin lat, origin lon, rotation, scale
5. Save; the dashboard confirms with "Registration saved."

Keep the origin within about 2 km of the area you care about.

### Deployment Complete

Reload the browser, re-enter registration mode and select the same plan: the four parameters are still the saved values, and trackers on that plan draw on the same map as outdoor trails.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Save rejected with 422 | Latitude must not exceed 85 degrees and scale must be above 0 |
| Save rejected with 403 | Log in as `admin` |
| Parameters gone after reload | Save again and confirm "Registration saved." appears |
| Map jumps to blank blue after typing coordinates | Pan back to the site and re-enter the numbers |
| Rotate/Scale handles do not appear | Leave and re-enter registration mode |

---

## Step 6: Set Up a Geofence Alarm {#geofence_standard type=manual required=true verify=true config=devices/geofence_setup.yaml}

Draw a fence on the outdoor map and alarm when a tracker enters or leaves it. No beacon is needed inside the fence.

### Prerequisites

- At least one tracker is reporting GNSS positions
- You know which direction to alarm on: enter, exit, or both

### Wiring

1. Create the geofence: a GeoJSON polygon, or a centre point plus `radius_m`
2. Create the alarm rule with `location_mode: geo`, point it at the fence, choose the transition
3. Walk a tracker across the boundary. An alarm needs 3 consecutive points on the new side spanning at least 10 s

### Deployment Complete

One enter alarm and one exit alarm appear, and loitering on the boundary produces none. The alarms show in the dashboard alarm list.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| No alarm at all | The crossing was shorter than 3 uplinks or 10 s; enlarge the fence or shorten the uplink interval |
| Alarm fires late | Expected: confirmation needs 3 consecutive points spanning at least 10 s |
| Alarm right after a restart | Check whether the same rule is configured twice |
| `time_range` has no effect | Expected: geo mode does not use it |
| Beacon selector still demanded | Switch `location_mode` to `geo` |

---

## Step 7: Open Dashboard {#dashboard_standard type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is live. Click below to open it in your browser.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine |
| Outdoor entry missing from the map dropdown | Redeploy with the outdoor image tag |

---
### Deployment Complete

The system is ready.

#### Quick Verification

1. Walk a tracker near beacons indoors and confirm it appears on the floor plan
2. Walk outside and confirm it moves to the outdoor map after a few GNSS fixes
3. Cross a geofence boundary and confirm the alarm
4. Double-press the tracker button and confirm the SOS alarm

#### Next Steps

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)

## Preset: Enterprise {#enterprise}

For large campuses over 2000 sqm, multi-floor buildings, and sites with both indoor and outdoor areas. Positions indoors come from BLE beacons and outdoors from the tracker's own GNSS, drawn on one map, with geofence enter/exit alarms.

- **Hardware:** 1 SenseCAP M2 gateway, 36 BC03 BLE beacons, 10+ SenseCAP T1000 trackers.
- **Coverage:** 2000+ sqm, 2 km LoRaWAN range (nominal).
- **Server:** a computer or server with Docker to run the positioning application.

**Limitation:** this is not a safety-certified system. Positions can be late, wrong or missing (LoRaWAN uplinks can be lost, GNSS does not work indoors, BLE positioning degrades around metal). Do not use it as the only control where a wrong or missing position can hurt someone.

## Step 1: Deploy BLE Beacons {#beacons_enterprise type=manual required=true}

Place BLE beacons at fixed locations indoors as position reference points. Areas
covered by GNSS only (yards, roads, parking) need no beacons.

### Wiring

1. Place at least 3 beacons per area (trilateration) or 1 beacon (room level)
2. Install at 2.5-3 m height, 5-10 m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Beacon light not on | Replace the battery |
| Inaccurate positioning | Add beacons or reduce spacing |
| Tracker can't scan beacons | Move the beacon so it is not too high or obstructed |
| Tracker stays "outdoor" inside the building | Add the beacon's MAC to the map configuration; unconfigured beacons do not count as indoor |

---

## Step 2: Setup LoRaWAN Gateway {#gateway_enterprise type=manual required=true}

Connect the gateway to enable wireless communication between tracker and positioning app.

### Wiring

1. Power on gateway, connect to network (Ethernet or WiFi)
2. Use SenseCraft App to scan QR code and bind gateway
3. Solid green LED indicates ready

### Troubleshooting

| Symptom | Action |
|---------|--------|
| LED not on | Check the power adapter and cable |
| LED blinking red | Check the Ethernet cable or WiFi configuration |
| App QR scan failed | Make sure the gateway is online |
| Tracker data not reporting | Confirm gateway and tracker use the same frequency band |

---

## Step 3: Deploy Positioning Application {#app_server_enterprise type=docker_deploy required=true config=devices/app_deploy.yaml}

Deploy the positioning application. Prepare the application image first (see the preset notes).

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available
3. For an offline basemap, put the `.pmtiles` map file in `data/pmtiles` next to the compose file before deploying

### Deployment Complete

1. Visit `http://localhost:5173`, log in with `admin` / `12345678` (change the default password under Configuration → Authentication after logging in)
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Deployment failed | Start Docker Desktop |
| Image not found | Build the image from the upstream branch and tag it locally |
| Port occupied | Close the program using port 5173 or change the port |
| Webpage won't open | Wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server
5. For an offline basemap, put the `.pmtiles` map file in `data/pmtiles` under the remote deploy directory

### Deployment Complete

1. Visit `http://<device-ip>:5173`, log in with `admin` / `12345678` (change the default password under Configuration → Authentication after logging in)
2. Upload the floor plan and enter the area it covers in metres
3. Mark beacon positions on the plan (enter MAC addresses)
4. Point the LoRaWAN network server at this host, or configure the SenseCAP / ChirpStack integration in the dashboard

### Troubleshooting

| Symptom | Action |
|---------|--------|
| SSH connection failed | Check the IP address and username/password |
| Deployment failed | Install Docker on the remote server |
| Image not found | Build and push the image, or load it on the remote host |
| Webpage won't open | Open port 5173 in the remote server's firewall |

---

## Step 4: Configure and Activate Tracker {#tracker_enterprise type=manual required=true}

Set up the tracker and confirm both indoor and outdoor positions are reported.

### Wiring

1. Press power button 3 s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to the tracker
3. Select the correct LoRaWAN region, and enable both BLE scanning and GNSS positioning
4. Walk near beacons indoors, press the button to trigger a report, confirm the position appears on the floor plan
5. Walk outside, wait for a GNSS fix, confirm the tracker moves to the outdoor map

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Keeps blinking after power on | Check the gateway is online and the frequency band matches |
| Tracker not visible on webpage | Check the network server / SenseCAP integration settings in the dashboard |
| Position not updating | Press the button to trigger a report, or adjust the reporting interval |
| Indoor position displayed incorrectly | Check the beacon markers on the plan |
| Does not switch to outdoor | Needs 3 GNSS fixes within 20 s and 15 s without a configured beacon; near a window it can switch back and forth |

---

## Step 5: Georeference the Floor Plan {#georeference_enterprise type=manual required=true verify=true config=devices/georeference_floorplan.yaml}

Align the floor plan with the outdoor map so indoor and outdoor trails show in one view. Skip it if you do not need the two together.

### Prerequisites

- The floor plan is uploaded and its real-world size in metres is set
- You are logged in as `admin`
- The site is visible on the outdoor map (online OSM map, or an offline `.pmtiles` map)

### Wiring

1. Select the **Outdoor** entry in the map dropdown and pan to your site
2. Enter registration mode and pick the floor plan
3. Use Drag / Rotate / Scale until the plan lines up with the building
4. Check the toolbar values: origin lat, origin lon, rotation, scale
5. Save; the dashboard confirms with "Registration saved."

Keep the origin within about 2 km of the area you care about.

### Deployment Complete

Reload the browser, re-enter registration mode and select the same plan: the four parameters are still the saved values, and trackers on that plan draw on the same map as outdoor trails.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Save rejected with 422 | Latitude must not exceed 85 degrees and scale must be above 0 |
| Save rejected with 403 | Log in as `admin` |
| Parameters gone after reload | Save again and confirm "Registration saved." appears |
| Map jumps to blank blue after typing coordinates | Pan back to the site and re-enter the numbers |
| Rotate/Scale handles do not appear | Leave and re-enter registration mode |

---

## Step 6: Set Up a Geofence Alarm {#geofence_enterprise type=manual required=true verify=true config=devices/geofence_setup.yaml}

Draw a fence on the outdoor map and alarm when a tracker enters or leaves it. No beacon is needed inside the fence.

### Prerequisites

- At least one tracker is reporting GNSS positions
- You know which direction to alarm on: enter, exit, or both

### Wiring

1. Create the geofence: a GeoJSON polygon, or a centre point plus `radius_m`
2. Create the alarm rule with `location_mode: geo`, point it at the fence, choose the transition
3. Walk a tracker across the boundary. An alarm needs 3 consecutive points on the new side spanning at least 10 s

### Deployment Complete

One enter alarm and one exit alarm appear, and loitering on the boundary produces none. The alarms show in the dashboard alarm list.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| No alarm at all | The crossing was shorter than 3 uplinks or 10 s; enlarge the fence or shorten the uplink interval |
| Alarm fires late | Expected: confirmation needs 3 consecutive points spanning at least 10 s |
| Alarm right after a restart | Check whether the same rule is configured twice |
| `time_range` has no effect | Expected: geo mode does not use it |
| Beacon selector still demanded | Switch `location_mode` to `geo` |

---

## Step 7: Open Dashboard {#dashboard_enterprise type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is live. Click below to open it in your browser.

### Troubleshooting

| Symptom | Action |
|---------|--------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine |
| Outdoor entry missing from the map dropdown | Redeploy with the outdoor image tag |

---
### Deployment Complete

The system is ready.

#### Quick Verification

1. Walk a tracker near beacons indoors and confirm it appears on the floor plan
2. Walk outside and confirm it moves to the outdoor map after a few GNSS fixes
3. Cross a geofence boundary and confirm the alarm
4. Double-press the tracker button and confirm the SOS alarm

#### Next Steps

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)
