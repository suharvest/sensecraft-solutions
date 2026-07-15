## Preset: LoRa Gateway (Full System) {#lora_gateway}

Count sheep at the gate and see real-time totals on your phone and in a Home Assistant dashboard — even on an off-grid farm with no WiFi in the field.

| Device | Purpose |
|--------|---------|
| reCamera 2002 | Runs YOLO sheep detector and gate-crossing counter |
| XIAO ESP32-S3 + Wio-SX1262 | LoRa transmitter node (Meshtastic firmware) |
| reComputer R1100 / Raspberry Pi | Gateway — bridges LoRa messages to MQTT and Home Assistant |

**What you'll get:**
- Automatic IN / OUT / INSIDE sheep counts every time an animal crosses the gate
- LoRa heartbeat every 15 minutes to keep all displays in sync
- Real-time Home Assistant dashboard with daily totals and trend history
- Works off-grid — only the gateway computer needs a LAN connection to HA

**Requirements:** reCamera connected via USB or Ethernet · XIAO ESP32-S3 with Wio-SX1262 LoRa board · reComputer or Raspberry Pi running Home Assistant on the local network

---

## Step 1: Deploy Sheep Counter to reCamera {#deploy_recamera type=recamera_cpp required=true config=devices/recamera.yaml}

Deploy the versioned YOLO sheep counter package and its managed boot services to your reCamera.

### Wiring

1. Connect reCamera to your computer via USB-C or Ethernet
2. Connect the XIAO ESP32-S3 LoRa node to reCamera's UART port (`/dev/ttyS3`):
   - XIAO TX → reCamera RX
   - XIAO RX → reCamera TX
   - Shared GND
3. Enter your reCamera IP address (USB default: `192.168.42.1`) and SSH password

### Deployment Complete

The deployer will:
- Stop the default Node-RED and SSCMA services to free the NPU
- Download and checksum-verify the `recamera-sheep-counter-lora` package from the SenseCraft CDN
- Install its counter and supervisor as init.d services that start on every boot

After deployment, SSH into the camera and tail the log to confirm it's running:

```
ssh recamera@192.168.42.1
tail -f /var/log/sheep_counter.log
```

You should see detection events like `EVT,IN,1,0,1,123` appearing when sheep cross the gate line.

### Troubleshooting

| Issue | Solution |
|-------|---------|
| SSH connection failed | Check cable; try password `recamera.2` if `recamera` doesn't work |
| Counter exits immediately | Check `/var/log/sheep_counter.log`, then run `/etc/init.d/S85sscma-keepalive restart` |
| No log output after 2 min | Ensure SSCMA inference daemon is running: `/etc/init.d/S85sscma-keepalive start` |
| No UART events reaching XIAO | Confirm XIAO GND is shared with reCamera; check wiring on `/dev/ttyS3` |

---

## Step 2: Configure the XIAO LoRa Transmitter {#configure_xiao type=manual required=true}

Flash Meshtastic firmware to the XIAO ESP32-S3 and configure it to act as a Serial + Detection Sensor node.

### Wiring

1. Connect the XIAO ESP32-S3 to your computer via USB-C
2. Open the [Meshtastic Web Flasher](https://flasher.meshtastic.org/) in Chrome/Edge
3. Select **XIAO ESP32-S3** as the target device and flash the latest stable Meshtastic firmware
4. After flashing, open the [Meshtastic Web Client](https://client.meshtastic.org/) to configure:
   - **Serial Module** → Enable → Baud Rate: `115200` → Receive mode: passthrough
   - **Detection Sensor Module** → Enable → Monitor GPIO: `490` → Detection high → Alert message prefix: `SHEEP`
   - Set a unique **Node name** (e.g. `SheepGate1`) so you can identify it on the mesh
5. Pair the XIAO with a Meshtastic-compatible LoRa receiver (phone app or local node)

### Deployment Complete

Once configured, trigger a test crossing by briefly pulling GPIO 490 HIGH. You should see:
- A "SHEEP" alert on your Meshtastic phone app within 30 seconds
- The raw `EVT,IN,...` line appearing in your Meshtastic channel as a text message

### Troubleshooting

| Issue | Solution |
|-------|---------|
| Flasher can't detect XIAO | Hold BOOT while plugging in USB; release after the port appears |
| No messages on the mesh | Check RF frequency matches all mesh nodes; confirm channel preset is the same |
| Serial data arrives garbled | Confirm baud rate is 115200 on both the XIAO Serial Module and the reCamera UART |
| GPIO alerts not firing | Verify the sheep_counter binary is sending a ~0.5 s pulse on GPIO 490 on each crossing |

---

## Step 3: Deploy Gateway Bridge to reComputer {#deploy_gateway type=script required=true config=devices/gateway.yaml}

Deploy the two Python bridge services (`meshtastic_mqtt_bridge` and `ha_bridge`) to your local gateway computer via an automated install script. These services listen for LoRa messages and publish sheep counts to Home Assistant via MQTT.

Before you start, ensure Home Assistant is running on your LAN and its MQTT integration is connected to the same broker with discovery enabled. You will enter the gateway SSH connection, MQTT broker IP, and Meshtastic receiver serial port in the deploy form.

### Wiring

1. Connect the LoRa receiver node (a second Meshtastic device, e.g. reComputer serial or a plugged-in USB Meshtastic radio) to the gateway computer

### Deployment Complete

After deployment, verify the systemd services are healthy:

```
ssh recomputer@<gateway-ip>
systemctl status meshtastic-bridge ha-bridge
```

Both should show `active (running)`.

Import the `ha_dashboard.yaml` file into Home Assistant:
1. Copy `assets/gateway/ha_dashboard.yaml` from this solution package to your HA config directory (or use `/opt/sheep-gateway/ha_dashboard.yaml` if the gateway scripts were already deployed)
2. In HA: Settings → Dashboards → Import → select the file

### Troubleshooting

| Issue | Solution |
|-------|---------|
| meshtastic-bridge not starting | Confirm the Meshtastic USB radio is plugged into the gateway; check `journalctl -u meshtastic-bridge` |
| ha-bridge fails to connect | Confirm the MQTT broker IP is reachable on port 1883 and accepts the gateway connection |
| No MQTT messages | Verify the MQTT broker IP and that the broker accepts unauthenticated connections on port 1883 |
| Services stop on reboot | Run `systemctl enable meshtastic-bridge ha-bridge` to re-enable |

---

## Step 4: Open Sheep Counter Dashboard {#verify_dashboard type=web_dashboard required=true config=devices/ha_dashboard.yaml}

The full system is now running. Click below to open the Home Assistant sheep counter dashboard and confirm live counts are coming in.

### Deployment Complete

Your sheep counter is live! On the dashboard you will see:

- **IN / OUT / INSIDE** — real-time counters since the last dashboard reset
- **Last event time** — timestamp of the most recent gate crossing
- **Daily history** — 24-hour trend graph

#### Quick Verification

1. Wave your hand in front of the camera (or walk past the gate line) to simulate a crossing
2. Watch the `EVT,IN,...` line appear in `/var/log/sheep_counter.log` on the reCamera
3. Within ~30 s, the IN counter should increment on the HA dashboard

#### Tips

- Mount reCamera at an angle to the gate so sheep cross the virtual line cleanly
- Adjust the gate-line position in the counter config if your crossing rate is low
- The LoRa heartbeat (`HB` messages every 15 min) keeps displays in sync after radio gaps

#### Next Steps

- [Project source & documentation](https://github.com/biancayoung/recamera-sheep-counter-lora)
- Add a Meshtastic phone app to get mobile alerts in the field

### Troubleshooting

| Issue | Solution |
|-------|---------|
| Dashboard page shows no data | Confirm ha-bridge is running, MQTT discovery is enabled in HA, and the `sensor.sheep_*` entities exist |
| Counts not updating | Trigger a manual crossing; check MQTT traffic with `mosquitto_sub -t sheep/# -v` |
| HA entities show unavailable | Re-import the `ha_dashboard.yaml` and restart the ha-bridge service |
