## Preset: Starter Kit {#starter}

Best for small offices or single rooms up to 500 sqm. Quick to set up, minimal hardware required.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1 | LoRaWAN network coverage |
| BC01 BLE Beacons | 6 | Position reference points |
| SenseCAP T1000 Tracker | 1+ | Tracked asset/person |

**What you'll get:**
- Real-time location of tracked assets/people
- Web-based map visualization
- Zone-based or triangulation positioning

**Coverage:** Up to 500 sqm · 2km LoRaWAN range

## Step 1: Deploy BLE Beacons {#beacons type=manual required=true}

Place BLE beacons at fixed locations around your space as position reference points.

### Wiring

1. Place at least 3 beacons per area (triangulation) or 1 beacon (proximity)
2. Install at 2.5-3m height, 10-15m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Beacon light not on | Battery depleted - replace CR2477 battery |
| Inaccurate positioning | Too few beacons or spacing too large - increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed - adjust installation position |

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
| Tracker data not reporting | Frequency band mismatch - confirm gateway and tracker use same band (e.g., CN470) |

---

## Step 3: Deploy Positioning Application {#app_server type=docker_deploy required=true config=devices/app_deploy.yaml}

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the indoor positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available

### Deployment Complete

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://your-local-ip:5173/api/webhook`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment failed | Docker not running - start Docker Desktop |
| Port occupied | Other program using port 5173 - close the program or change port |
| Webpage won't open | Service not fully started - wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the indoor positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server

### Deployment Complete

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://<device-ip>:5173/api/webhook`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | IP or credentials incorrect - check IP address and username/password |
| Deployment failed | Remote server has no Docker - install Docker on the remote server |
| Webpage won't open | Firewall blocking - open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker type=manual required=true}

Set up the tracker and test positioning accuracy by walking near the installed beacons.

### Wiring

1. Press power button 3s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to tracker
3. Set mode to "BLE Scan", select correct LoRaWAN region
4. Walk near beacons, press button to trigger report, verify positioning works

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Keeps blinking after power on | Failed to join network - check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Webhook not configured - check if network server webhook points to positioning app |
| Position not updating | Tracker in sleep mode - press button to trigger report, or adjust reporting interval |
| Position displayed incorrectly | Beacon coordinates misconfigured - check if beacon position markers on webpage are correct |

---

## Step 5: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

---
### Deployment Complete

Indoor positioning system is ready!

#### Access Your System

- **URL:** http://\<server-ip\>:5173
- **Login:** admin / 83EtWJUbGrPnQjdCqyKq

#### Initial Setup

1. Upload your floor map image
2. Mark beacon positions on the map (enter MAC addresses)
3. Configure LoRaWAN network server webhook

#### Quick Verification

- Walk near beacons with tracker
- Press tracker button to trigger position report
- Check web dashboard for real-time location updates

#### Next Steps

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)

## Preset: Standard Setup {#standard}

Best for medium facilities (500-2000 sqm) like warehouses, offices, or retail stores.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1 | LoRaWAN network coverage |
| BC01 BLE Beacons | 15 | Position reference points |
| SenseCAP T1000 Tracker | 3+ | Tracked assets/people |

**What you'll get:**
- Real-time location of tracked assets/people
- Multi-zone coverage with meter-level accuracy
- Web-based map visualization with history

**Coverage:** Up to 2000 sqm · Multiple rooms/floors supported

## Step 1: Deploy BLE Beacons {#beacons type=manual required=true}

Place BLE beacons at fixed locations around your space as position reference points.

### Wiring

1. Place at least 3 beacons per area (triangulation) or 1 beacon (proximity)
2. Install at 2.5-3m height, 10-15m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Beacon light not on | Battery depleted - replace CR2477 battery |
| Inaccurate positioning | Too few beacons or spacing too large - increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed - adjust installation position |

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
| Tracker data not reporting | Frequency band mismatch - confirm gateway and tracker use same band (e.g., CN470) |

---

## Step 3: Deploy Positioning Application {#app_server type=docker_deploy required=true config=devices/app_deploy.yaml}

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the indoor positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available

### Deployment Complete

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://your-local-ip:5173/api/webhook`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment failed | Docker not running - start Docker Desktop |
| Port occupied | Other program using port 5173 - close the program or change port |
| Webpage won't open | Service not fully started - wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the indoor positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server

### Deployment Complete

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://<device-ip>:5173/api/webhook`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | IP or credentials incorrect - check IP address and username/password |
| Deployment failed | Remote server has no Docker - install Docker on the remote server |
| Webpage won't open | Firewall blocking - open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker type=manual required=true}

Set up the tracker and test positioning accuracy by walking near the installed beacons.

### Wiring

1. Press power button 3s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to tracker
3. Set mode to "BLE Scan", select correct LoRaWAN region
4. Walk near beacons, press button to trigger report, verify positioning works

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Keeps blinking after power on | Failed to join network - check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Webhook not configured - check if network server webhook points to positioning app |
| Position not updating | Tracker in sleep mode - press button to trigger report, or adjust reporting interval |
| Position displayed incorrectly | Beacon coordinates misconfigured - check if beacon position markers on webpage are correct |

---

## Step 5: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

---
### Deployment Complete

Indoor positioning system is ready!

#### Access Your System

- **URL:** http://\<server-ip\>:5173
- **Login:** admin / 83EtWJUbGrPnQjdCqyKq

#### Initial Setup

1. Upload your floor map image
2. Mark beacon positions on the map (enter MAC addresses)
3. Configure LoRaWAN network server webhook

#### Quick Verification

- Walk near beacons with tracker
- Press tracker button to trigger position report
- Check web dashboard for real-time location updates

#### Next Steps

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)

## Preset: Enterprise {#enterprise}

Best for large facilities (2000+ sqm) like factories, hospitals, or campus buildings.

| Device | Quantity | Purpose |
|--------|----------|---------|
| SenseCAP M2 Gateway | 1+ | LoRaWAN coverage (add more for larger areas) |
| BC01 BLE Beacons | 30+ | Position reference points |
| SenseCAP T1000 Tracker | 10+ | Tracked assets/people |

**What you'll get:**
- Campus-wide real-time tracking
- High-precision triangulation positioning
- Scalable to thousands of tracked assets

**Coverage:** 2000+ sqm · Add gateways for multi-building coverage

## Step 1: Deploy BLE Beacons {#beacons type=manual required=true}

Place BLE beacons at fixed locations around your space as position reference points.

### Wiring

1. Place at least 3 beacons per area (triangulation) or 1 beacon (proximity)
2. Install at 2.5-3m height, 10-15m spacing
3. Record each beacon's MAC address and location

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Beacon light not on | Battery depleted - replace CR2477 battery |
| Inaccurate positioning | Too few beacons or spacing too large - increase beacon density |
| Tracker can't scan beacons | Beacon installed too high or obstructed - adjust installation position |

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
| Tracker data not reporting | Frequency band mismatch - confirm gateway and tracker use same band (e.g., CN470) |

---

## Step 3: Deploy Positioning Application {#app_server type=docker_deploy required=true config=devices/app_deploy.yaml}

### Target {#app_server_local type=local config=devices/app_deploy.yaml default=true}

Deploy the indoor positioning application on your local computer.

### Wiring

1. Ensure Docker Desktop is installed and running
2. Ensure port 5173 is available

### Deployment Complete

1. Visit `http://localhost:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://your-local-ip:5173/api/webhook`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deployment failed | Docker not running - start Docker Desktop |
| Port occupied | Other program using port 5173 - close the program or change port |
| Webpage won't open | Service not fully started - wait a few minutes and refresh |

### Target {#app_server_remote type=remote config=devices/app_deploy.yaml}

Deploy the indoor positioning application to a remote server via SSH.

### Wiring

1. Connect target device to network
2. Get device IP address
3. Get SSH credentials (username/password)
4. Ensure Docker is installed on the remote server

### Deployment Complete

1. Visit `http://<device-ip>:5173`, login with `admin` / `83EtWJUbGrPnQjdCqyKq`
2. Upload floor map, mark beacon positions on map (enter MAC addresses)
3. Configure LoRaWAN network server webhook to `http://<device-ip>:5173/api/webhook`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | IP or credentials incorrect - check IP address and username/password |
| Deployment failed | Remote server has no Docker - install Docker on the remote server |
| Webpage won't open | Firewall blocking - open port 5173 on the remote server |

---

## Step 4: Configure and Activate Tracker {#tracker type=manual required=true}

Set up the tracker and test positioning accuracy by walking near the installed beacons.

### Wiring

1. Press power button 3s to turn on, blinking green = joining network
2. Use SenseCraft App to connect to tracker
3. Set mode to "BLE Scan", select correct LoRaWAN region
4. Walk near beacons, press button to trigger report, verify positioning works

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Keeps blinking after power on | Failed to join network - check if gateway is online and frequency band matches |
| Tracker not visible on webpage | Webhook not configured - check if network server webhook points to positioning app |
| Position not updating | Tracker in sleep mode - press button to trigger report, or adjust reporting interval |
| Position displayed incorrectly | Beacon coordinates misconfigured - check if beacon position markers on webpage are correct |

---

## Step 5: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The positioning dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |
### Deployment Complete

Indoor positioning system is ready!

#### Access Your System

- **URL:** http://\<server-ip\>:5173
- **Login:** admin / 83EtWJUbGrPnQjdCqyKq

#### Initial Setup

1. Upload your floor map image
2. Mark beacon positions on the map (enter MAC addresses)
3. Configure LoRaWAN network server webhook

#### Quick Verification

- Walk near beacons with tracker
- Press tracker button to trigger position report
- Check web dashboard for real-time location updates

#### Next Steps

- [View Wiki Documentation](https://wiki.seeedstudio.com/solutions/indoor-positioning-bluetooth-lorawan-tracker/)
- [GitHub Repository](https://github.com/Seeed-Solution/Solution_IndoorPositioning_H5)
- [Try Online Demo](https://indoorpositioning-demo.seeed.cc/)
