## Preset: SenseCAP Cloud {#cloud}

The nodes already report to the SenseCAP cloud through a gateway you have
running. Nothing on the radio side changes. A bridge container reads the cloud —
history first, then the live stream — and publishes Home Assistant entities to a
local broker.

| Device | Purpose |
|--------|---------|
| SenseCAP S21xx nodes | Measure soil and air, report over LoRaWAN |
| SenseCAP M2 gateway | Forwards uplinks to the SenseCAP cloud |
| Linux host with Docker | Runs Home Assistant, the MQTT broker and the bridge |

**Important:** this preset has not been run against a live SenseCAP account.
The cloud MQTT hostname is unconfirmed — two candidates are in circulation and
the deployment step offers both. The OpenAPI backfill has never been exercised
against real responses. Treat the first deployment as a bring-up, and read the
bridge log before trusting the dashboard.

## Step 1: Deploy Home Assistant and the Broker {#deploy_ha type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

Start Home Assistant and a Mosquitto broker on one host. Skip this only if you
already run both and can point the bridge at your existing broker.

### Prerequisites

1. A Linux host with Docker running, reachable over SSH. Any architecture with
   Docker works — the images used here publish both amd64 and arm64.
2. At least 8 GB free disk. The Home Assistant image alone is around 1.5 GB.
3. Ports 8123 and 1883 free, or different ports chosen in the step's inputs.
4. A broker password you choose now. The bridge step asks for the same value,
   so write it down — the broker refuses anonymous clients on purpose, because
   the bridge may run on a different machine.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 already in use | Something else is on it — an existing Home Assistant or Mosquitto. Stop it, or set different ports in this step's inputs |
| Mosquitto restarts with `Unable to open pwfile` | The password file was written but not owned by the `mosquitto` user. The bundled compose file fixes this with a `chown`; a hand-edited copy that dropped it will fail exactly this way |
| Home Assistant never answers on 8123 | First start takes a few minutes. Check `docker logs agri-env-homeassistant` before assuming it failed |
| Deploy cannot connect | Confirm SSH is reachable and the username is right — Raspberry Pi OS uses `pi`, Seeed reComputer images use `recomputer` |

### Target {#deploy_ha_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

Deploy to the host over SSH from this computer.

### Target {#deploy_ha_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

Run this directly on the host if you are working on the machine itself.

---

## Step 2: Deploy the Cloud Bridge {#deploy_cloud_bridge type=docker_deploy required=true config=devices/cloud_bridge.yaml}

Deploy the bridge with its SenseCAP cloud source enabled. It lists the devices on
your account, backfills their history, then subscribes to the live stream.

### Prerequisites

1. A SenseCAP API key pair — Access ID and Access Key — from the SenseCAP
   Portal under Security → Access API Keys. The Access Key is written only to a
   mode-600 `.env` file on the target host.
2. The broker address, port, username and password from step 1. Use the host's
   LAN address rather than `127.0.0.1` if the bridge runs on a different machine.
3. The bridge image. `agri-env-bridge:0.1.0` is **not published to any
   registry** yet — build it from the upstream project before deploying, or set
   `BRIDGE_IMAGE` to a tag you host yourself.
4. A decision on the backfill window. The OpenAPI reaches back three months at
   most and serves one month per request, so three months means three times the
   requests per device.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Bridge log shows a DNS failure for the cloud host | The two candidate hostnames are both unconfirmed. Redeploy with the other option in the MQTT host selector |
| Bridge log shows an authentication failure | Check the Access ID and Access Key pair, and that the key has not been revoked in the Portal |
| Devices appear but no values | Backfill puts only the latest value per entity into Home Assistant. If the nodes report hourly, the first live update can be up to an hour away |
| `no such image` on deploy | The image tag is not published. Build it locally and re-run |
| Nothing reaches the broker | Check the broker address is the LAN address, not `127.0.0.1`, when the bridge is not on the Home Assistant host |

### Target {#cloud_bridge_remote type=remote device_name="Bridge Host" config=devices/cloud_bridge.yaml default=true}

Deploy the bridge to the host over SSH.

### Target {#cloud_bridge_local type=local device_name="Bridge Host" config=devices/cloud_bridge.yaml}

Run it directly on the host.

---

## Step 3: Check the Data in Home Assistant {#verify_cloud type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Open Home Assistant and confirm the nodes arrived as devices with entities.

### Deployment Complete

Every node on the account is now a Home Assistant device named
`SenseCAP <DevEUI>`, with one entity per measurement it reports.

#### Quick verification

1. Sign in to Home Assistant and complete the onboarding wizard if this is a
   fresh install.
2. Settings → Devices & Services → Add integration → **MQTT**. Broker is the
   host running the stack, port 1883, with the username and password from step 1.
   Skip if MQTT is already configured.
3. Open the MQTT integration. Each node appears as a device; open one and check
   its entities carry units — `°C`, `%`, `dS/m` — rather than plain numbers.
4. Import the dashboard: Overview → three-dot menu → Edit dashboard → three-dot
   menu → Raw configuration editor, and paste
   `assets/homeassistant/agri_env_dashboard.yaml`. Replace the example DevEUIs
   with your own.
5. Install the threshold alerts: merge
   `assets/homeassistant/automations.yaml` into Home Assistant's
   `automations.yaml` and reload automations. Adjust the thresholds and the
   `for:` durations — the shipped durations are zero, which is right for testing
   and wrong for a field where a single reading can wobble.

#### Next steps

- Set the offline threshold to match your nodes' reporting interval. The default
  assumes hourly reporting; nodes that report every six hours will otherwise be
  marked offline between uplinks.
- Add the entities you actually act on to a separate view. A dashboard listing
  every measurement every node emits is a dashboard nobody reads.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| MQTT integration connects but no devices appear | The bridge is not publishing. Check `docker logs agri-env-bridge-cloud` for the cloud connection line |
| Entities appear as `unavailable` right away | No uplink has arrived within the offline threshold. Either the nodes are silent, or the threshold is shorter than their reporting interval |
| An entity has no unit | Its `measurementId` is not in `assets/config/measurements.yaml`. Add it there — the file cites the decoder source line for every existing entry |
| Old entity ids keep coming back | Discovery configs are retained. Clear the broker's retained messages and Home Assistant's entity registry together, or the old topics reappear on restart |

---

## Preset: Self-hosted The Things Stack {#tts_local}

You run the network server. A WM1302 concentrator on a CM4 host feeds a The
Things Stack Open Source instance, and the bridge subscribes to its Application
Server MQTT. No cloud account is involved.

| Device | Purpose |
|--------|---------|
| SenseCAP S21xx nodes | Measure soil and air, report over LoRaWAN |
| WM1302 concentrator | The gateway radio, on SPI |
| CM4 host | Carries the concentrator, runs the packet forwarder and the stack |
| Linux host with Docker | Runs Home Assistant, the MQTT broker and the bridge |

**Important:** none of this preset has been run on hardware. The concentrator
has not been fitted, the stack has not been started on an ARM64 target, and its
first-start initialisation sequence has not been executed. The resource floor is
unmeasured. Steps below marked as awaiting verification are written from the
module and stack documentation, and each is the kind of step that fails in a
way specific to the board.

## Step 1: Deploy Home Assistant and the Broker {#deploy_ha_tts type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

The same Home Assistant and broker as the other presets. Deploy it first so the
bridge has somewhere to publish.

### Prerequisites

1. A Linux host with Docker running, reachable over SSH.
2. At least 8 GB free disk.
3. Ports 8123 and 1883 free, or different ports chosen in the step's inputs.
4. A broker password you choose now — the stack step asks for the same value.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 already in use | Stop what holds it, or set different ports in this step's inputs |
| Mosquitto restarts with `Unable to open pwfile` | The password file must be owned by the `mosquitto` user; the bundled compose file does this |
| Home Assistant never answers on 8123 | First start takes a few minutes — read `docker logs agri-env-homeassistant` |
| Deploy cannot connect | Check SSH and the username for your image |

### Target {#deploy_ha_tts_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

Deploy to the host over SSH.

### Target {#deploy_ha_tts_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

Run it directly on the host.

---

## Step 2: Fit the WM1302 Concentrator {#wm1302_tts type=manual required=true config=devices/wm1302_tts.yaml}

Fit the module, enable SPI, and run a packet forwarder pointed at the stack.
**Awaiting hardware verification** — no WM1302 was fitted while packaging this.

### Wiring

1. Power the host down before seating the module. Connect the LoRa antenna
   before applying power; transmitting into an open port can damage the radio.
2. Use the SPI variant of the module and confirm `/dev/spidev0.0` appears once
   SPI is enabled on the host.
3. The reset, power-enable and SX1261 control lines come from the carrier
   board's documentation, not the module's. Write down the pin numbers — the
   packet forwarder configuration refers to them.
4. Check the band printed on the module against the band your nodes use. A
   mismatch presents exactly as a gateway that hears nothing.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Forwarder exits without printing an EUI | SPI is not enabled or the reset line is wrong. Confirm `/dev/spidev0.0` exists first |
| Gateway stays disconnected in the Console | UDP 1700 is not reaching the stack host. Check the firewall before touching the radio configuration |
| Concentrator starts but no uplinks | Band mismatch between module, frequency plan and nodes is the first thing to rule out |

---

## Step 3: Deploy The Things Stack and the Bridge {#deploy_tts type=docker_deploy required=true config=devices/tts_stack.yaml}

Bring up The Things Stack with Postgres and Redis, initialise it, and start the
bridge beside it. Allow 15–30 min for the first run.

### Prerequisites

1. At least 10 GB free disk for the stack, database and Redis images plus the
   database volume.
2. The host's LAN address. The Console's OAuth URLs are built from it, so
   `127.0.0.1` produces a Console you cannot sign in to from another machine.
3. Ports 1885 (Console) and 1700/udp (packet forwarder) free.
4. The broker address, port, username and password from step 1.
5. The bridge image. `agri-env-bridge:0.1.0` is **not published to any
   registry** — build it or override `BRIDGE_IMAGE`.
6. The application ID and API key are asked for here but created in step 4.
   Deploy this step, create them in the Console, then restart the bridge with
   `docker compose restart bridge`.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `is-db migrate` fails | Postgres was not ready. Re-run the initialisation — every command in it is safe to repeat |
| Console loads but sign-in loops | The OAuth URLs were built from the wrong host. Redeploy with the LAN address |
| Bridge log shows no `TTS MQTT connected` | The application or its API key does not exist yet. Create them in step 4 and restart the bridge |
| Stack container is killed on start | Unmeasured resource floor — check available memory before assuming a configuration error |

### Target {#tts_stack_remote type=remote device_name="Gateway Host" config=devices/tts_stack.yaml default=true}

Deploy to the gateway host over SSH.

### Target {#tts_stack_local type=local device_name="Gateway Host" config=devices/tts_stack.yaml}

Run it directly on the gateway host.

---

## Step 4: Join the Sensors to The Things Stack {#join_tts type=manual required=true config=devices/join_tts_device.yaml}

Create the application, install the payload formatter, and join the nodes.
**Awaiting hardware verification** — no node was joined while packaging this.

### Prerequisites

1. The gateway shows as `Connected` in the Console.
2. Each node's DevEUI, JoinEUI and AppKey, printed on the node or readable with
   the SenseCAP Mate app over NFC.
3. The SenseCAP decoder for your node series, from the upstream repository. The
   uplinks are binary — without it no entity can appear. That repository has no
   LICENSE file and its licensing is unconfirmed; installing it is your decision.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Join request but no join accept | The keys or the regional parameters do not match the node |
| No join request at all | The gateway is not hearing the node. Check the gateway's status before re-checking keys |
| Uplinks arrive with no `decoded_payload` | The payload formatter is missing or attached to a different application |
| `decoded_payload` present but no `messages` array | Wrong decoder for the node series — take the one for your series, not a neighbouring one |

---

## Step 5: Check the Data in Home Assistant {#verify_tts type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Open Home Assistant and confirm the nodes arrived.

### Deployment Complete

The nodes are on a network server you control, and their measurements are Home
Assistant entities with the same ids the other presets produce.

#### Quick verification

1. Sign in to Home Assistant and complete onboarding if this is a fresh install.
2. Settings → Devices & Services → Add integration → **MQTT**, pointed at the
   broker from step 1.
3. Open the MQTT integration. Each joined node is a device named
   `SenseCAP <DevEUI>`; open one and check the units are present.
4. Import `assets/homeassistant/agri_env_dashboard.yaml` into the Lovelace raw
   configuration editor and replace the example DevEUIs with your own.
5. Merge `assets/homeassistant/automations.yaml` into Home Assistant's
   `automations.yaml`, reload automations, and set the thresholds and `for:`
   durations for your site.

#### Next steps

- Set the offline threshold to match the nodes' reporting interval.
- Keep the Console's gateway page open during the first day. A gateway that
  drops and reconnects shows there long before it shows on the dashboard.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Devices appear, entities are `unavailable` | No uplink within the offline threshold — check the interval against the threshold |
| One node missing while others work | Check that node's Live data in the Console. If uplinks arrive there, the decoder is the difference |
| An entity has no unit | Its `measurementId` is not in `assets/config/measurements.yaml`. Add it |
| Old entity ids keep coming back | Retained discovery configs. Clear them on the broker and clear the entity registry together |

---

## Preset: Local ChirpStack {#chirpstack_local}

ChirpStack is the network server, either built into the M2 gateway or running in
Docker on a CM4 host with a WM1302. This is the shortest route to a deployment
that never touches the internet.

| Device | Purpose |
|--------|---------|
| SenseCAP S21xx nodes | Measure soil and air, report over LoRaWAN |
| SenseCAP M2 gateway | Radio plus, in local mode, the network server itself |
| CM4 host + WM1302 | The alternative to the M2 — runs ChirpStack in Docker |
| Linux host with Docker | Runs Home Assistant, the MQTT broker and the bridge |

**Important:** neither route of this preset has been run on hardware. No M2 was
switched to local mode, no concentrator was fitted, and ChirpStack was not
started on an ARM64 target. Whether the M2 can report to the cloud and to a
local network server at the same time is unverified — do not plan around it
until you have confirmed it on the unit in front of you.

## Step 1: Deploy Home Assistant and the Broker {#deploy_ha_cs type=docker_deploy required=true config=devices/homeassistant_deploy.yaml}

The same Home Assistant and broker as the other presets.

### Prerequisites

1. A Linux host with Docker running, reachable over SSH.
2. At least 8 GB free disk.
3. Ports 8123 and 1883 free, or different ports chosen in the step's inputs.
4. A broker password you choose now — the ChirpStack step asks for the same value.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8123 or 1883 already in use | Stop what holds it, or set different ports in this step's inputs |
| Mosquitto restarts with `Unable to open pwfile` | The password file must be owned by the `mosquitto` user; the bundled compose file does this |
| Home Assistant never answers on 8123 | First start takes a few minutes — read `docker logs agri-env-homeassistant` |
| Deploy cannot connect | Check SSH and the username for your image |

### Target {#deploy_ha_cs_remote type=remote device_name="Linux Host" config=devices/homeassistant_deploy.yaml default=true}

Deploy to the host over SSH.

### Target {#deploy_ha_cs_local type=local device_name="Linux Host" config=devices/homeassistant_deploy.yaml}

Run it directly on the host.

---

## Step 2: Switch the M2 to Local Network Server {#m2_local_lns type=manual required=false config=devices/m2_local_lns.yaml}

Take the gateway off the cloud and turn on its built-in ChirpStack. Do this step
**or** step 3, not both. **Awaiting hardware verification** — no M2 was switched
while packaging this.

### Prerequisites

1. The M2's LAN address and its web interface credentials.
2. The model, band and firmware version from its status page, written down. The
   menu path below is `LoRa → LoRa Network`; if what you see differs, the
   firmware version is the first thing to quote when asking about it.
3. An MQTT host, port, username and password for the built-in network server to
   publish to. This is a direct MQTT connection — not Semtech UDP, not Basic
   Station — so the bridge subscribes to that broker.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Uplinks stop appearing in the Portal | Expected — local mode takes the gateway off the cloud. Whether both can run at once is unverified on this firmware |
| The built-in ChirpStack has no application | Create the tenant, application and device profile before joining nodes in step 5 |
| Uplinks arrive with no `object` | The device profile has no codec. Paste the SenseCAP decoder for your node series into it |

---

## Step 3: Fit the WM1302 Concentrator {#wm1302_chirpstack type=manual required=false config=devices/wm1302_chirpstack.yaml}

The alternative to step 2: build the gateway yourself on a CM4 host and run
ChirpStack there. **Awaiting hardware verification** — no WM1302 was fitted while
packaging this.

### Wiring

1. Power the host down before seating the module, and connect the LoRa antenna
   before applying power.
2. Use the SPI variant and confirm `/dev/spidev0.0` appears once SPI is enabled.
3. Take the reset, power-enable and SX1261 pin numbers from the carrier board's
   documentation and write them down.
4. The band printed on the module must match the frequency plan chosen in step 4
   and the band the nodes use.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Forwarder exits without printing an EUI | SPI is not enabled or the reset line is wrong |
| Gateway's `Last seen` never updates | Packets are not arriving — check UDP 1700 through the firewall first |
| Concentratord starts but the gateway bridge sees nothing | Its ZMQ endpoints must be reachable from inside the container. This is the unverified part of this route — fall back to the UDP packet forwarder to get uplinks flowing, then revisit |

---

## Step 4: Deploy ChirpStack and the Bridge {#deploy_chirpstack type=docker_deploy required=true config=devices/chirpstack_stack.yaml}

One step covers both routes. Choose `m2` to start only the bridge, or `local` to
bring up ChirpStack on this host as well.

### Prerequisites

1. On the `m2` route: the M2's broker address, port, username and password from
   step 2.
2. On the `local` route: at least 8 GB free disk, and a frequency plan matching
   the concentrator and the nodes.
3. The broker address, port, username and password from step 1.
4. The bridge image. `agri-env-bridge:0.1.0` is **not published to any
   registry** — build it or override `BRIDGE_IMAGE`.
5. The application ID. `+` subscribes to every application on that broker, which
   is the simplest thing that works for a single-tenant site.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Bridge log shows no `ChirpStack MQTT connected` | On the `m2` route, re-check the address and credentials from the gateway's LoRa Network page. On the `local` route, check `docker compose --profile local-lns ps` |
| ChirpStack services did not start on the `local` route | The profile is only activated when `lns_mode` is `local`. Re-run the step with the right choice |
| Web interface on 8080 is unreachable | Only the `local` route runs one. On the `m2` route ChirpStack lives inside the gateway |
| `no such image` on deploy | The bridge image tag is not published. Build it locally and re-run |

### Target {#chirpstack_remote type=remote device_name="Bridge Host" config=devices/chirpstack_stack.yaml default=true}

Deploy over SSH to the host that will run the bridge.

### Target {#chirpstack_local_target type=local device_name="Bridge Host" config=devices/chirpstack_stack.yaml}

Run it directly on that host.

---

## Step 5: Join the Sensors to ChirpStack {#join_chirpstack type=manual required=true config=devices/join_chirpstack_device.yaml}

Register the nodes and confirm their uplinks decode. **Awaiting hardware
verification** — no node was joined while packaging this.

### Prerequisites

1. A device profile whose LoRaWAN version and regional parameters match the
   nodes, with the SenseCAP decoder for their series in its codec field. That
   repository has no LICENSE file and its licensing is unconfirmed; installing
   it is your decision.
2. Each node's DevEUI, JoinEUI and AppKey.
3. The gateway visible in ChirpStack with a recent `Last seen`.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| ChirpStack rejects the DevEUI | It already exists in another tenant — the usual surprise when moving a node off another network |
| Join request but no accept | Keys or regional parameters do not match |
| Uplinks arrive with no `object.messages` | The device profile has no codec, or the wrong one for the series |

---

## Step 6: Check the Data in Home Assistant {#verify_chirpstack type=web_dashboard required=false config=devices/ha_dashboard.yaml}

Open Home Assistant and confirm the nodes arrived — then, if this is an offline
deployment, confirm it stays working with the internet cut.

### Deployment Complete

The whole path from node to dashboard is on your own network. Nothing in it
depends on a cloud account.

#### Quick verification

1. Sign in to Home Assistant and complete onboarding if this is a fresh install.
2. Settings → Devices & Services → Add integration → **MQTT**, pointed at the
   broker from step 1.
3. Open the MQTT integration. Each joined node is a device named
   `SenseCAP <DevEUI>`; open one and check the units are present.
4. Import `assets/homeassistant/agri_env_dashboard.yaml` into the Lovelace raw
   configuration editor and replace the example DevEUIs with your own.
5. Merge `assets/homeassistant/automations.yaml` into Home Assistant's
   `automations.yaml`, reload automations, and set the thresholds and `for:`
   durations for your site.

#### Offline acceptance

Run this once the dashboard is working, to confirm the deployment survives with
no internet:

1. Note the current value and last-updated time of one entity per node.
2. Cut the site's WAN — unplug the uplink, or block outbound traffic at the
   firewall. Leave the local network up.
3. Wait for at least two reporting intervals. Every entity must keep updating.
   If any stop, something in the path is still reaching outward; the bridge log
   and the gateway's own page will say which.
4. Restart the gateway. Time how long it takes from power-on to the first uplink
   appearing in Home Assistant, and record it — this is the number to quote for
   recovery, and it is site-specific.
5. Restore the WAN. Nothing should change, because nothing was using it.

Record what you measure. This package ships no distance, node-count or
success-rate figures because none have been measured; the numbers you take here
are the ones that describe your site.

#### Next steps

- Set the offline threshold to match the nodes' reporting interval.
- For an air-gapped site, pull the container images once while the host still has
  a network, or load them from an archive — the compose files reference public
  registries and will not pull with the WAN cut.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Devices appear, entities are `unavailable` | No uplink within the offline threshold — check the interval against the threshold |
| Entities stop updating when the WAN is cut | Something in the path still resolves or reaches outward. Read the bridge log and the gateway's network page |
| An entity has no unit | Its `measurementId` is not in `assets/config/measurements.yaml`. Add it |
| Old entity ids keep coming back | Retained discovery configs. Clear them on the broker and clear the entity registry together |
