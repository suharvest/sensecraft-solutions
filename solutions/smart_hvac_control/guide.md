HVAC setpoint optimization with a KNN model over a unified point model, an Eastron SDM630 energy meter, verified write-and-readback control, rollback, and alarms.

## Preset: Standard Deployment {#default}

Deploy the prediction service, register the energy meter, and commission control in observe-first mode. Writes stay off until readback, rollback and alarms have each been exercised on your own plant and the safety limits have been approved by a named engineer.

| Device | Purpose |
|--------|---------|
| reComputer R1100 (or any Docker host) | Runs the point model, prediction, control path and web console |
| Eastron SDM630 energy meter | Supplies power and energy points over Modbus TCP or RS-485 |
| HVAC controller (OPC UA, Modbus or BACnet/IP) | The plant being read and written; the built-in simulator covers a dry run |

**What you'll get:**
- Setpoint recommendations learned from this building's own historical data
- Meter and HVAC points in one table, with the SDM630 register map as a built-in template
- Writes that only count as applied after a field readback matches within tolerance
- Rollback on five triggers, and alarms identified by cause rather than by event

**Important.** This is not a safety-certified control system. The plant's own interlocks and safety controls stay in charge. Every write is bounded by limits that ship as **placeholders** — 18–30 °C, 1 °C per 5 minutes, and an off/fan/cool/heat/auto mode whitelist — and the runtime reports the baseline as unapproved until a named site engineer signs it off. **No energy-saving figure is claimed anywhere in this package**: no baseline comparison, weather or occupancy normalisation, or defined measurement period exists yet.

**Requirements:** Docker Engine 20.10+ · about 1 GB free disk · host ports 8280 and 4841 free · at least one week of historical operation data as CSV or Excel

## Step 1: Deploy the HVAC Control Service {#hvac type=docker_deploy required=true config=devices/deploy.yaml}

Deploy the prediction and control service and enter the meter, control-mode, safety and alarm settings.

### Prerequisites

Docker running on the target, the meter's transport and unit id to hand, and the OPC UA endpoint of the HVAC controller — or the default address, which reaches the built-in simulator.

Leave **Control Mode** at *observe*. Leave **Safety Baseline Approved By** blank until an engineer has actually approved the limits; a blank field is what keeps the baseline reporting as unapproved.

### Target {#hvac_local type=local config=devices/deploy.yaml default=true}

Deploy on the machine running SenseCraft Solution. Use this for a dry run against the built-in simulator, or when the plant network is reachable from this machine.

### Wiring

A real running-console capture is in `gallery/`; a capture of the physical wiring is not available yet — see `gallery/ATTRIBUTION.md`. Wire it as follows:

1. Put this machine on the same network as the HVAC controller and the meter or its Modbus TCP gateway.
2. Modbus RTU is not available on this target: the standard Docker profile attaches no host serial device. Use Modbus TCP here, or the remote target with the serial-device profile.
3. Keep ports 8280 and 4841 free, or free them before deploying.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not running | Start Docker Desktop or Docker Engine, then retry |
| Port 8280 in use | Free the port or change the host port mapping in the compose file |
| Container exits after starting | `docker logs missionpack_knn` — the last lines carry the startup failure |
| Web page not loading | Wait for the health check at `/api/v1/health`; startup allows 30 s |
| Meter points read but the values are nonsense | Byte or word order mismatch, not a wiring fault — see Step 3 |

### Target {#hvac_remote type=remote config=devices/deploy.yaml}

Deploy over SSH to a reComputer R1100 or another Linux device on the plant network. Use this when the meter is on RS-485 or when the controller network is not reachable from your workstation.

### Wiring

Real captures of the device and its connections are not available yet — see `gallery/ATTRIBUTION.md`. Wire it as follows:

1. Connect the device's Ethernet interface to the controller network and record its IP address.
2. For Modbus RTU, attach the USB-to-RS-485 adapter, note the device path (typically `/dev/ttyUSB0`), and use the serial-device deployment profile — the standard profile does not pass a host serial device into the container.
3. Match the RS-485 baud rate, parity and unit id to what the meter is configured for; a mismatch reads as a timeout, not as an error message.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Check the device IP, username, credentials and that sshd is running |
| Remote device has no Docker | Install Docker Engine on the device first |
| Deployment timeout | Check that the device can reach the image registry |
| Web page not loading | Open port 8280 through the device firewall |
| `/dev/ttyUSB0` missing in the container | The standard profile does not attach serial devices; redeploy with the serial-device profile |

## Step 2: Open the Control Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Open the console, create the first administrator, and check that the sources from Step 1 are online.

### Prerequisites

The container from Step 1 must be healthy.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page not loading | Confirm Step 1 finished and the health check passes |
| Wrong host/port | Update the URL with the device IP if you deployed remotely |
| A source shows offline | Check reachability, the unit id, and — for RS-485 — the baud rate and wiring polarity |

## Step 3: Commission the Meter, Control Path and Alarms {#commissioning type=manual required=true verify=true config=devices/commissioning.yaml}

Register the meter, run predictions in observe mode, exercise the failure paths on purpose, and only then enable writes. This is the step that decides whether the deployment is trustworthy; do not shorten it.

### Prerequisites

An administrator session from Step 2, physical access to the meter's display, and someone who operates this plant available to judge whether the recommendations make sense.

**Image tag first.** `docker inspect -f '{{.Config.Image}}' missionpack_knn`. The published tag `missionpack-knn:v1.6.5` **does not** carry the SDM630 template, the rollback coordinator or the alarm envelope. The image that does has not been built or pushed, and its immutable tag is **to be assigned**. On v1.6.5, the observe-mode substeps still apply; the meter, rollback and alarm substeps cannot be completed.

### Turn on write-back verification

Write-back verification is off unless the prediction-run configuration asks for it: a config
without a `rollback` section migrates to `enabled: false` rather than silently gaining a new
write path. This package ships no prediction-run config template — the run configuration is
created in the console, not through a deployment variable — so set the section explicitly
when you start the run:

```json
{
  "schema_version": "prediction-run.v3",
  "interval_seconds": 60,
  "rollback": { "enabled": true, "settle_seconds": 2.5 }
}
```

`settle_seconds` (0–30, default 1.0) is how long the gateway waits after a batch before it
reads the points back. It must be longer than the source's collection interval, or the
readback sees the value from before the write and reports a mismatch that never happened.
The readback and compensation run after the batch, not inside it, so this delay does not
enter the cycle latency; the next batch does wait for the previous one to reach a terminal
state, which is what keeps at most one write in flight per point.

Only points on Modbus are verified. A BACnet output is skipped, because the production cycle
supplies no write priority for it and a compensation would not know which priority to
relinquish.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Meter template import rejected | The template renders a strict CSV bounded at 256 rows; a customised template that exceeds it is refused by the same parser |
| Voltage and frequency look plausible but wrong | Float word order. Switch it in the deployment form and re-read before changing anything else |
| Imported energy jumps backwards | Word order again, or two sources polling the same meter with different unit ids |
| A write is acknowledged but the readback never verifies | Check the point's quality first — a readback whose quality is not good never verifies, regardless of value |
| A rollback itself fails | This raises a critical compensation-failed alarm. The plant is in an unknown state; restore it by hand and do not re-enable writes until the cause is understood |
| The same fault opens a new alarm each time | Alarms are keyed by cause; if you see duplicates, the cause fields differ — compare the source and point ids |

### Deployment Complete

**Reminder.** Not a safety-certified control system. Known weaknesses: the rollback coordinator and the alarm envelope are wired into the prediction cycle upstream but have only been exercised against protocol simulators, so verify both on your own plant; the meter's byte and word order is a vendor default, not a measured fact; and no energy-saving figure has been measured.

#### Quick verification

1. `docker inspect -f '{{.Config.Image}}' missionpack_knn` returns the tag you intend to run.
2. All ten SDM630 points read, and voltage, frequency and imported energy agree with the meter's own display.
3. Imported active energy only increases, and survives a restart of the source.
4. A full occupancy cycle of predictions has run in observe mode and the recommendations have been reviewed by whoever operates the plant.
5. The safety limits carry an approver's name; the baseline no longer reports as unapproved.
6. One write inside the limits produced a command receipt, a delayed readback within tolerance, and a point quality of good.
7. Source-offline, readback-mismatch and stale-sample faults each produced the expected alarm, and the first two each produced a rollback: BACnet released with Null at the original priority, Modbus restored in reverse order.
8. `northbound.spool.queued` in `GET /system/runtime-metrics` is 0 with `dropped` unchanged, if northbound publishing is enabled.

#### Evidence to export

For the handover record: the image tag; the meter template id and confirmed word order; the approved safety limits and the approver's name; the command audit trail for the verified write; the rollback journal entries from the fault injection; the alarm history with its acknowledgements. Container logs rotate at 10 MB with 4 backups (`docker logs missionpack_knn`), so copy anything you need before it ages away.

#### Next steps

1. Enable writes on one zone only, and watch it for a full cycle before widening.
2. Alert on the critical compensation-failed alarm; it is the only one that means the plant is in an unknown state.
3. Re-approve the safety limits whenever the plant is rebalanced — a commissioned limit that no longer matches the plant is worse than a placeholder, because it looks approved.
