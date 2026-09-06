## Preset: Multi-Protocol Data Hub {#standard}

Deploy one lightweight integration layer that turns different controllers into a unified, controllable point model.

| Device | Purpose |
|--------|---------|
| reComputer R1000 / R1100 Series | Unifies field protocols into one point model and MQTT interface |
| reTerminal DM Series | Runs the same services with an on-device touch display |
| Industrial controllers | Provide OPC UA, Modbus, BACnet/IP, or MQTT data |

**What you'll get:**
- One place to configure OPC UA, Modbus, BACnet/IP, and MQTT controllers
- Automatic discovery where available, with manual point entry as the fallback
- One point table for reading, filtering, and safely controlling field data
- One versioned MQTT contract for upstream data, commands, and receipts

**Requirements:** Docker Engine 20.10+ · 4 GB free disk space · Network access to the target controllers

## Step 1: Deploy the Multi-Protocol Data Hub {#gateway type=docker_deploy required=true config=devices/gateway.yaml}

Start protocol integration and data services while preserving point configuration, audit history, and models across restarts.

### Target {#gateway_local type=local config=devices/gateway.yaml default=true}

Deploy on the machine running SenseCraft Solution.

### Wiring

![Connection architecture](gallery/architecture.svg)

1. Connect this machine to the same network as the Ethernet controllers.
2. The standard local Docker target does not attach a serial device. Use a serial-device deployment profile for Modbus RTU and keep production writes disabled until hardware validation is complete.
3. Keep the default web and MQTT ports, or select unused host ports before deployment.

BACnet/IP broadcast discovery may not cross Docker Desktop's bridge network. Use manual BACnet addressing here, or choose the remote Linux target for subnet discovery.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker is not available | Start Docker Desktop or Docker Engine, then retry |
| Port 8280 or 1883 is busy | Choose another web or MQTT host port in the deployment form |
| Image download fails | Confirm the host can reach `sensecraft-missionpack.seeed.cn` and has at least 4 GB free |
| Health check stays pending | Inspect `docker logs missionpack-industrial-gateway` and confirm `/readyz` returns HTTP 200 |

### Target {#gateway_edge type=remote device_name="reComputer R / reTerminal DM" config=devices/gateway.yaml}

Deploy over SSH to a reComputer R1000/R1100 Series or reTerminal DM device on the controller network.

### Wiring

![Connection architecture](gallery/architecture.svg)

1. Connect the selected reComputer R or reTerminal DM Ethernet interface to the controller network and record its IP address.
2. If Modbus RTU is required, use the serial-device installer/profile to attach the USB-to-RS-485 adapter; do not enable production writes before hardware validation.
3. Enter the device SSH address and credentials, then start deployment.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection fails | Check the device IP, username, credentials, and SSH service |
| Registry cannot be reached | Confirm DNS and firewall access to `sensecraft-missionpack.seeed.cn` |
| Web console cannot be opened | Allow the selected web port through the device firewall and verify the container is healthy |
| BACnet discovery returns no devices | Select the interface on the BACnet subnet and check that broadcasts are not blocked |

## Step 2: Configure Unified Access and Data Service {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Open the web console, create the first administrator, and bring the first field controller into the unified point model.

1. Create the first administrator account; no token is required.
2. Open **Access**, click **Add**, choose OPC UA, Modbus, BACnet/IP, or MQTT, and configure the controller.
3. Run protocol discovery where available, review the candidates, and confirm only the points you need. Use manual configuration when discovery is unavailable or incomplete.
4. Open **Points** to verify live values and quality before granting write access.
5. Open **Data Service** to configure the embedded MQTT broker and review point, presence, command, and receipt topics.
6. Optionally open the prediction plugin to import CSV data and configure input/output points.

### Prerequisites

The service container from Step 1 must be healthy. No registration token is required for first-run administrator setup.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The page does not load | Wait for Step 1 to report healthy, then verify the selected web port |
| A discovered point is missing | Use manual point configuration as the fallback and verify its protocol address |
| A control command is rejected | Check point write permission, current quality, safety rules, and the command receipt |
| MQTT control is unavailable | Enable TLS and configure a control identity; plaintext mode is telemetry-only |

## Step 3: Publish Northbound and Verify Store-and-Forward — pending image build {#northbound type=manual required=false}

> **This step is not runnable with the image this package deploys.** The published tag
> `missionpack-knn:v1.6.7` used by Step 1 does not contain the northbound publisher, so every
> call below returns HTTP 404. The step therefore carries no configuration to run and no
> verification to pass — it is reference material for the pending build. Once the image that
> carries the feature is published, this step gets its `config=devices/northbound_setup.yaml`
> and `verify=true` back, and the verification below becomes the step's verification.

Point the gateway at an external or cloud MQTT broker, then prove that a broker outage buffers data on disk and replays it in order after reconnect. Skip this step if the embedded broker from Step 2 is the only consumer.

### Prerequisites

An administrator session from Step 2, a reachable external MQTT broker with a CA bundle, and an image tag that carries northbound publishing.

**Image tag status.** The published tag `sensecraft-missionpack.seeed.cn/solution/missionpack-knn:v1.6.7` used by this package does **not** contain the northbound publisher. The feature exists upstream on `feature/northbound-publish` (`f831bae`); the image has not been built or pushed yet. The immutable tag it will carry is **to be assigned** — do not substitute `latest`. Until that tag is published, `GET /system/northbound-publish/status` returns HTTP 404 and this step cannot be completed.

**Endpoints.**

| Call | Purpose |
|------|---------|
| `PUT /system/northbound-publish/config` | Broker host/port, topic prefix, batch flush size and interval, spool limits, TLS material. Credentials are write-only and are never echoed back |
| `POST /system/northbound-publish/start` | Connect and begin publishing |
| `POST /system/northbound-publish/stop` | Disconnect and publish an offline status message |
| `GET /system/northbound-publish/status` | Running, connected, queue capacity, and whether a credential is configured |
| `GET /system/runtime-metrics` | `northbound.spool` counters: `queued`, `queued_bytes`, `dropped`, `replayed`, `oldest_age_seconds` |

**TLS.** TLS 1.2 or newer with CA and hostname verification; mutual TLS optional. Plaintext transport is refused unless the runtime profile is exactly `test` or `development`, so a production deployment must supply a CA bundle.

**Topics.** `<prefix>/{gateway}/telemetry` (batched, QoS1, not retained), `<prefix>/{gateway}/sources/{source_id}/health` (QoS1, retained), `<prefix>/{gateway}/status` (last will, QoS1, retained), `<prefix>/{gateway}/heartbeat` (QoS0, not retained, never buffered — a replayed heartbeat would misreport liveness).

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `/system/northbound-publish/status` returns 404 | The running image predates the feature; check the tag and wait for the pending build |
| Start fails with a transport error | Plaintext is refused outside the test and development runtime profiles; supply TLS material |
| Status reports running but not connected | Check broker reachability, credentials, and that the CA bundle matches the broker certificate chain |
| `queued_bytes` grows and never drains | The link is still down, or the spool limit was reached and old batches were dropped; check `dropped` and `oldest_age_seconds` |
| Messages are missing at the cloud after a broker restart | Use a persistent broker and a durable subscriber session; an in-memory broker discards messages that arrive before the subscriber re-subscribes |

### Deployment Complete

#### Quick verification — enabled once the image is published

These checks need the pending build; against `v1.6.7` step 1 already fails with HTTP 404.

1. `GET /system/northbound-publish/status` reports running, connected, and a queue capacity greater than zero.
2. A cloud subscriber on `<prefix>/{gateway}/telemetry` receives envelopes carrying `schema_version`, `message_id`, `gateway_id`, and a `samples` array.
3. Stop the broker. `northbound.spool.queued` and `queued_bytes` in `/system/runtime-metrics` grow while the link is down.
4. Restart the broker. The buffered batches replay in order, `northbound.spool.queued` returns to 0, and `dropped` has not increased.
5. Confirm the retained `<prefix>/{gateway}/status` topic flipped back to online.

#### Running the capacity soak

The upstream repository ships the `r14_capacity_soak.py` harness that produced the numbers in the solution description. To reproduce them on your own hardware, clone the upstream repository onto the target device and run:

```
uv run python scripts/r14_capacity_soak.py --profile release \
  --evidence-root log/r14-capacity-evidence --run-id release-<UTC timestamp>
```

The `release` profile runs 2,000 points for 24 h and refuses to start unless the git worktree is clean — it treats any untracked file, including macOS AppleDouble `._*` files left by a file copy, as an unfrozen source. `capacity-smoke` is the same shape at 180 s for a quick check, and the `northbound-*` profiles add cloud-broker outage injection. A run passes only when `verdict.json` reports `passed=true`, `failures=[]`, and `exit_code=0`.

#### Next steps

1. Set the spool limits from your own worst-case outage: at about 350 events/s the reference rig buffered 60.1 KB/s.
2. Give the cloud consumer a deduplication key — replay is ordered at-least-once and reuses the same `message_id`.
3. Alert on `northbound.spool.dropped` and `oldest_age_seconds`; a growing `dropped` means the spool limit is discarding data.

#### Protocol Release Status

| Protocol | Current boundary |
|----------|------------------|
| OPC UA | Source configuration, browse/manual points, live reads, and controlled writes |
| Modbus TCP | Manual points, unit scan, live reads, and controlled writes |
| BACnet/IP | Who-Is discovery, manual points, ReadProperty, and WriteProperty with priority and Null relinquish. COV subscription, BBMD/Foreign-Device registration, and MS-TP are **not** implemented |
| MQTT source | Explicit topic mappings and bounded topic observation |
| Modbus RTU/RS-485 | Configuration and transport included; requires the serial-device deployment profile and USB hardware validation |
| Northbound MQTT publish | Batched telemetry, retained health and status, heartbeat, and SQLite store-and-forward with ordered at-least-once replay. Requires the pending image tag; not in `v1.6.7` |
| Northbound topic contract | MissionPack v1 native topics; Sparkplug B is not implemented in this release |
