## Preset: SenseCAP Cloud {#cloud}

SenseCAP S21xx nodes already report to the SenseCAP cloud through a SenseCAP M2 gateway; nothing on the radio side changes. A bridge container pulls history and live data from the cloud and publishes them as local Home Assistant entities.

- **Host:** A Linux host with Docker for Home Assistant, the MQTT broker and the bridge.
- **Account:** A SenseCAP Portal account and an API key pair.
- **Known limits:** Two cloud MQTT hostnames are in circulation and the deployment offers both; after the first deployment, check the bridge log to confirm it connected.

## Step 1: Deploy Home Assistant and the Broker {#deploy_ha type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

Starts Home Assistant and a Mosquitto broker on one host. Skip this if you already run both and the bridge can reach your existing broker.

### Prerequisites

1. At least 8 GB free disk on the host.
2. Ports 8123 and 1883 free, or different ports set in this step's inputs.
3. A broker password, written down; the bridge step asks for the same value.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Port 8123 or 1883 already in use | Stop the existing Home Assistant or Mosquitto, or set different ports in this step's inputs |
| Mosquitto restarts with `Unable to open pwfile` | Make the password file owned by the `mosquitto` user |
| Home Assistant never answers on 8123 | First start takes a few minutes; run `docker logs agri-env-homeassistant` |
| Deploy cannot connect | Confirm SSH is reachable and the username is right (`pi` on Raspberry Pi OS, `recomputer` on reComputer) |

### Target {#deploy_ha_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

Deploy over SSH to a Linux host with Docker; amd64 and arm64 both work.

### Target {#deploy_ha_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

Deploy to this machine, which must be a Linux host with Docker.

---

## Step 2: Deploy the Cloud Bridge {#deploy_cloud_bridge type=docker_deploy required=true config=devices/cloud_bridge.yaml}

Deploys the bridge that reads the SenseCAP cloud. It lists the devices on your account, backfills their history, then subscribes to live data.

### Prerequisites

1. A SenseCAP API key pair (Access ID and Access Key) from the SenseCAP Portal under Security → Access API Keys.
2. The broker address, port, username and password from step 1. If the bridge runs on a different machine, use the LAN IP rather than `127.0.0.1`.
3. A backfill window: up to three months; a longer window means more requests.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Bridge log shows a DNS failure for the cloud host | Redeploy with the other option in the MQTT host selector |
| Bridge log shows an authentication failure | Check the Access ID and Access Key pair, and that the key has not been revoked in the Portal |
| Devices appear but no values | Backfill writes only the latest value per entity; with hourly reporting, the first live update can take up to an hour |
| `no such image` on deploy | With a self-built `BRIDGE_IMAGE`, build it locally first and re-run |
| Nothing reaches the broker | When the bridge is not on the Home Assistant host, set the broker address to the LAN IP |

### Target {#cloud_bridge_remote type=remote device_name="Bridge Host" config=devices/cloud_bridge.yaml default=true}

Deploy the bridge over SSH to a host with Docker.

### Target {#cloud_bridge_local type=local device_name="Bridge Host" config=devices/cloud_bridge.yaml}

Deploy to this machine, which must have Docker installed.

---

## Step 3: Check the Data in Home Assistant {#verify_cloud type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Open Home Assistant and confirm the nodes arrived as devices with entities.

### Deployment Complete

Every node on the account is a Home Assistant device named `SenseCAP <DevEUI>`, with one entity per measurement.

#### Quick verification

1. Sign in to Home Assistant and complete the onboarding wizard on a fresh install.
2. Settings → Devices & Services → Add integration → **MQTT**, with the host running the stack, port 1883, and the username and password from step 1. Skip if MQTT is already configured.
3. Open the MQTT integration, open a device, and check its entities carry units (`°C`, `%`, `dS/m`).
4. Import the dashboard: Overview → three-dot menu → Edit dashboard → three-dot menu → Raw configuration editor, paste `assets/homeassistant/agri_env_dashboard.yaml`, and replace the example DevEUIs with your own.
5. Import the threshold alerts: merge `assets/homeassistant/automations.yaml` into Home Assistant's `automations.yaml` and reload automations. The shipped `for:` durations are zero; adjust thresholds and durations before field use so a single noisy reading does not trigger an alert.

#### Next steps

- Set the offline threshold to match the nodes' reporting interval. The default assumes hourly reporting; nodes reporting every six hours are marked offline between uplinks.
- Put the entities you act on in a separate view.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| MQTT integration connects but no devices appear | Run `docker logs agri-env-bridge-cloud` and confirm the cloud connection line is there |
| Entities appear as `unavailable` right away | Confirm the nodes are reporting and the offline threshold is not shorter than their interval |
| An entity has no unit | Add its `measurementId` to `assets/config/measurements.yaml` |
| Old entity ids keep coming back | Clear the broker's retained messages and Home Assistant's entity registry together |

---

## Preset: Self-hosted The Things Stack {#tts_local}

A reComputer R12 Series gateway receives data from SenseCAP S21xx nodes and hands it to a self-hosted The Things Stack Open Source instance; the bridge subscribes to its MQTT and publishes Home Assistant entities. No cloud account is needed.

- **Host:** A Linux host with Docker for Home Assistant, the MQTT broker and the bridge.
- **Nodes:** Each node's DevEUI, JoinEUI and AppKey, with the node band matching the gateway.
- **Known limits:** Check available memory on the gateway host before starting the stack.

## Step 1: Deploy Home Assistant and the Broker {#deploy_ha_tts type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

Starts Home Assistant and a Mosquitto broker on one host.

### Prerequisites

1. At least 8 GB free disk on the host.
2. Ports 8123 and 1883 free, or different ports set in this step's inputs.
3. A broker password, written down; the stack step asks for the same value.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Port 8123 or 1883 already in use | Stop what holds it, or set different ports in this step's inputs |
| Mosquitto restarts with `Unable to open pwfile` | Make the password file owned by the `mosquitto` user |
| Home Assistant never answers on 8123 | First start takes a few minutes; run `docker logs agri-env-homeassistant` |
| Deploy cannot connect | Check SSH and the username for your OS image |

### Target {#deploy_ha_tts_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

Deploy over SSH to a Linux host with Docker.

### Target {#deploy_ha_tts_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

Deploy to this machine, which must be a Linux host with Docker.

---

## Step 2: Bring Up the Gateway Radio {#r12_gateway_tts type=manual required=true config=devices/r12_gateway_tts.yaml}

On the R12, connect the antenna, confirm the SPI device, and run a packet forwarder pointed at The Things Stack.

### Wiring

1. Connect the LoRa antenna to its SMA jack before applying power; transmitting without an antenna can damage the radio.
2. Confirm `/dev/spidev0.0` is present; if not, enable SPI and reboot.
3. Look up the reset, power-enable and SX1261 pin numbers in the R12 product wiki and write them down for the packet forwarder configuration.
4. Check that the regional band the gateway was ordered on matches the nodes' band; the band cannot be changed in software.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Forwarder exits without printing an EUI | Confirm `/dev/spidev0.0` exists, then check the reset pin |
| Gateway stays disconnected in the Console | Check that the firewall passes UDP 1700 to the stack host |
| Concentrator starts but no uplinks | Check that the gateway band, frequency plan and node band match |

---

## Step 3: Deploy The Things Stack and the Bridge {#deploy_tts type=docker_deploy required=true config=devices/tts_stack.yaml}

Starts The Things Stack (with Postgres and Redis), initialises it, and starts the bridge. Allow 15–30 min for the first run.

### Prerequisites

1. At least 10 GB free disk.
2. The host's LAN IP (not `127.0.0.1`, or other machines cannot sign in to the Console).
3. Ports 1885 (Console) and 1700/udp (packet forwarder) free.
4. The broker address, port, username and password from step 1.
5. The application ID and API key are created in step 4: deploy this step, create them in the Console and fill them in, then run `docker compose restart bridge`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| `is-db migrate` fails | Postgres was not ready; re-run the initialisation |
| Console loads but sign-in loops | Redeploy with the host's LAN IP |
| Bridge log shows no `TTS MQTT connected` | Create the application and API key in step 4, then restart the bridge |
| Stack container is killed on start | Check the host's available memory |

### Target {#tts_stack_remote type=remote device_name="Gateway Host" config=devices/tts_stack.yaml default=true}

Deploy to the gateway host over SSH.

### Target {#tts_stack_local type=local device_name="Gateway Host" config=devices/tts_stack.yaml}

Deploy to this machine, which must be the gateway host.

---

## Step 4: Join the Sensors to The Things Stack {#join_tts type=manual required=true config=devices/join_tts_device.yaml}

Create the application, install the payload formatter, and join the nodes.

### Prerequisites

1. The gateway shows as `Connected` in the Console.
2. Each node's DevEUI, JoinEUI and AppKey, printed on the node or readable with the SenseCAP Mate app over NFC.
3. The SenseCAP decoder for your node series (upstream repository); without it no entity appears. That repository has no LICENSE file and its licensing is unconfirmed.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Join request but no join accept | Check the keys and regional parameters |
| No join request at all | Check the gateway status first to confirm it hears the node |
| Uplinks arrive with no `decoded_payload` | Install the payload formatter on this application |
| `decoded_payload` present but no `messages` array | Use the decoder for your node series |

---

## Step 5: Check the Data in Home Assistant {#verify_tts type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Open Home Assistant and confirm the nodes arrived.

### Deployment Complete

Each joined node is a Home Assistant device, with the same entity ids as the other presets.

#### Quick verification

1. Sign in to Home Assistant and complete onboarding on a fresh install.
2. Settings → Devices & Services → Add integration → **MQTT**, pointed at the broker from step 1.
3. Open the MQTT integration; each node is a device named `SenseCAP <DevEUI>`. Open one and check the entities carry units.
4. Paste `assets/homeassistant/agri_env_dashboard.yaml` into the Lovelace raw configuration editor and replace the example DevEUIs with your own.
5. Merge `assets/homeassistant/automations.yaml` into Home Assistant's `automations.yaml`, reload automations, and set the thresholds and `for:` durations for your site.

#### Next steps

- Set the offline threshold to match the nodes' reporting interval.
- Keep the Console's gateway page open during the first day; gateway drops and reconnects show there first.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Devices appear, entities are `unavailable` | Check the reporting interval against the offline threshold |
| One node missing while others work | Check that node's Live data in the Console; if uplinks arrive there, check the decoder |
| An entity has no unit | Add its `measurementId` to `assets/config/measurements.yaml` |
| Old entity ids keep coming back | Clear the broker's retained messages and the entity registry together |

---

## Preset: Local ChirpStack {#chirpstack_local}

ChirpStack is the network server, either built into the SenseCAP M2 gateway or running in Docker on a reComputer R12 Series gateway; data from the SenseCAP S21xx nodes never leaves the local network.

- **Host:** A Linux host with Docker for Home Assistant, the MQTT broker and the bridge.
- **Nodes:** Each node's DevEUI, JoinEUI and AppKey, with the node band matching the gateway.
- **Known limits:** Local mode takes the M2 off the SenseCAP cloud; whether your firmware can report to both at once has to be confirmed on the unit.

## Step 1: Deploy Home Assistant and the Broker {#deploy_ha_cs type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

Starts Home Assistant and a Mosquitto broker on one host.

### Prerequisites

1. At least 8 GB free disk on the host.
2. Ports 8123 and 1883 free, or different ports set in this step's inputs.
3. A broker password, written down; the ChirpStack step asks for the same value.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Port 8123 or 1883 already in use | Stop what holds it, or set different ports in this step's inputs |
| Mosquitto restarts with `Unable to open pwfile` | Make the password file owned by the `mosquitto` user |
| Home Assistant never answers on 8123 | First start takes a few minutes; run `docker logs agri-env-homeassistant` |
| Deploy cannot connect | Check SSH and the username for your OS image |

### Target {#deploy_ha_cs_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

Deploy over SSH to a Linux host with Docker.

### Target {#deploy_ha_cs_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

Deploy to this machine, which must be a Linux host with Docker.

---

## Step 2: Switch the M2 to Local Network Server {#m2_local_lns type=manual required=false config=devices/m2_local_lns.yaml}

Take the M2 off the cloud and turn on its built-in ChirpStack. Do this step **or** step 3, not both.

### Prerequisites

1. The M2's LAN IP and web interface credentials.
2. The model, band and firmware version from its status page, written down. The menu path is `LoRa → LoRa Network`; if yours differs, check the firmware version first.
3. An MQTT host, port, username and password for the built-in network server to publish to; the bridge subscribes to that broker.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Uplinks stop appearing in the Portal | Expected in local mode |
| The built-in ChirpStack has no application | Create the tenant, application and device profile before joining nodes in step 5 |
| Uplinks arrive with no `object` | Paste the SenseCAP decoder for your node series into the device profile's codec |

---

## Step 3: Bring Up the Gateway Radio {#r12_gateway_chirpstack type=manual required=false config=devices/r12_gateway_chirpstack.yaml}

The alternative to step 2: use a reComputer R12 Series gateway instead of the M2, with the gateway and ChirpStack both running on the R12.

### Wiring

1. Connect the LoRa antenna to its SMA jack before applying power.
2. Confirm `/dev/spidev0.0` is present; if not, enable SPI and reboot.
3. Look up the reset, power-enable and SX1261 pin numbers in the R12 product wiki and write them down.
4. The regional band the gateway was ordered on must match the frequency plan chosen in step 4 and the nodes' band.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Forwarder exits without printing an EUI | Confirm SPI is enabled, then check the reset pin |
| Gateway's `Last seen` never updates | Check that the firewall passes UDP 1700 |
| Concentratord starts but the gateway bridge sees nothing | Switch to the UDP packet forwarder to get uplinks flowing, then check whether the concentratord ZMQ endpoints are reachable from inside the container |

---

## Step 4: Deploy ChirpStack and the Bridge {#deploy_chirpstack type=docker_deploy required=true config=devices/chirpstack_stack.yaml}

Choose `m2` to start only the bridge, or `local` to start ChirpStack on this host as well.

### Prerequisites

1. On the `m2` route: the M2's broker address, port, username and password from step 2.
2. On the `local` route: at least 8 GB free disk, and a frequency plan matching the gateway and the nodes.
3. The broker address, port, username and password from step 1.
4. The application ID; `+` subscribes to every application on that broker.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Bridge log shows no `ChirpStack MQTT connected` | On the `m2` route, re-check the address and credentials on the gateway's LoRa Network page; on the `local` route, run `docker compose --profile local-lns ps` |
| ChirpStack services did not start on the `local` route | Confirm `lns_mode` is `local` and re-run this step |
| Web interface on 8080 is unreachable | Only the `local` route has it; on the `m2` route, use the gateway's web interface |
| `no such image` on deploy | With a self-built `BRIDGE_IMAGE`, build it locally first and re-run |

### Target {#chirpstack_remote type=remote device_name="Bridge Host" config=devices/chirpstack_stack.yaml default=true}

Deploy over SSH to the host that will run the bridge.

### Target {#chirpstack_local_target type=local device_name="Bridge Host" config=devices/chirpstack_stack.yaml}

Deploy to this machine, which will run the bridge.

---

## Step 5: Join the Sensors to ChirpStack {#join_chirpstack type=manual required=true config=devices/join_chirpstack_device.yaml}

Register the nodes and confirm their uplinks decode.

### Prerequisites

1. A device profile whose LoRaWAN version and regional parameters match the nodes, with the SenseCAP decoder for their series in its codec field (the upstream repository has no LICENSE file and its licensing is unconfirmed).
2. Each node's DevEUI, JoinEUI and AppKey.
3. The gateway visible in ChirpStack with a recent `Last seen`.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| ChirpStack rejects the DevEUI | The DevEUI already exists in another tenant, which is common when moving nodes from another network |
| Join request but no accept | Check the keys and regional parameters |
| Uplinks arrive with no `object.messages` | Set the codec for the node series in the device profile |

---

## Step 6: Check the Data in Home Assistant {#verify_chirpstack type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Open Home Assistant and confirm the nodes arrived; for an offline deployment, also confirm it keeps working with the internet cut.

### Deployment Complete

Data from node to dashboard stays on the local network and does not depend on a cloud account.

#### Quick verification

1. Sign in to Home Assistant and complete onboarding on a fresh install.
2. Settings → Devices & Services → Add integration → **MQTT**, pointed at the broker from step 1.
3. Open the MQTT integration; each node is a device named `SenseCAP <DevEUI>`. Open one and check the entities carry units.
4. Paste `assets/homeassistant/agri_env_dashboard.yaml` into the Lovelace raw configuration editor and replace the example DevEUIs with your own.
5. Merge `assets/homeassistant/automations.yaml` into Home Assistant's `automations.yaml`, reload automations, and set the thresholds and `for:` durations for your site.

#### Offline acceptance

Run this once the dashboard works:

1. Note the current value and last-updated time of one entity per node.
2. Cut the site's WAN (unplug the uplink or block outbound traffic at the firewall) and leave the local network up.
3. Wait for at least two reporting intervals; every entity should keep updating. If any stop, check the bridge log and the gateway's page.
4. Restart the gateway and record the time from power-on to the first uplink in Home Assistant as the site's recovery time.
5. Restore the WAN; the data is unaffected.

#### Next steps

- Set the offline threshold to match the nodes' reporting interval.
- For an air-gapped site, pull the container images while the host still has a network, or load them from an archive; they cannot be pulled with the WAN cut.

### Troubleshooting

| Symptom | Fix |
|-------|----------|
| Devices appear, entities are `unavailable` | Check the reporting interval against the offline threshold |
| Entities stop updating when the WAN is cut | Check the bridge log and the gateway's network page for whatever still reaches outward |
| An entity has no unit | Add its `measurementId` to `assets/config/measurements.yaml` |
| Old entity ids keep coming back | Clear the broker's retained messages and the entity registry together |
