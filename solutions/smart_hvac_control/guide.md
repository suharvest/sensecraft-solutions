## Preset: Standard Deployment {#default}

Deploy the HVAC setpoint prediction and control service, connect an Eastron SDM630 energy meter, and commission in observe mode. Enable writes only after readback, rollback and alarms have been verified on your own plant and an engineer has approved the safety limits.

- **Devices:** reComputer R1100 or any Docker host; Eastron SDM630 energy meter (Modbus TCP or RS-485); HVAC controller (OPC UA, Modbus or BACnet/IP) — the built-in simulator covers a dry run.
- **Software:** Docker Engine 20.10+, about 1 GB free disk, host ports 8280 and 4841 free.
- **Data:** at least one week of historical operation data as CSV or Excel.
- **Limits:** this is not a safety-certified control system; the plant's own interlocks and safety controls stay in effect. Write limits ship as placeholders (18–30 °C, 1 °C per 5 minutes, off/fan/cool/heat/auto mode whitelist) and need approval by a site engineer. No energy-saving figure is provided.

## Step 1: Deploy the HVAC Control Service {#hvac type=docker_deploy required=true config=devices/deploy.yaml}

Deploy the prediction and control service and enter the meter, control-mode, safety and alarm settings.

### Prerequisites

- The meter's transport and unit id; the OPC UA endpoint of the HVAC controller (the default address reaches the built-in simulator).
- Leave **Control Mode** at *observe*. Leave **Safety Baseline Approved By** blank until an engineer has approved the limits.

### Target {#hvac_local type=local config=devices/deploy.yaml default=true}

Deploy on the machine running SenseCraft Solution, for a dry run against the built-in simulator or when this machine can reach the plant network. Modbus RTU is not available on this target.

### Wiring

1. Put this machine on the same network as the HVAC controller and the meter or its Modbus TCP gateway.
2. Connect the meter over Modbus TCP; for RS-485 use the remote target.
3. Make sure ports 8280 and 4841 are free.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Docker not running | Start Docker Desktop or Docker Engine, then retry |
| Port 8280 in use | Free the port |
| Container exits after starting | Run `docker logs missionpack_knn`; the last lines show the failure |
| Web page not loading | Wait about 30 s for the service to start |
| Meter points read but the values are nonsense | Byte or word order mismatch; see Step 3 |

### Target {#hvac_remote type=remote config=devices/deploy.yaml}

Deploy over SSH to a reComputer R1100 or another Linux device on the plant network. Use this when the meter is on RS-485 or your workstation cannot reach the controller network.

### Wiring

1. Connect the device's Ethernet port to the controller network and note its IP address.
2. For Modbus RTU, attach the USB-to-RS-485 adapter (typically `/dev/ttyUSB0`) and use the serial-device deployment profile.
3. Match the RS-485 baud rate, parity and unit id to the meter's settings; a mismatch shows up as a timeout.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| SSH connection failed | Check the device IP, username, credentials and that sshd is running |
| Remote device has no Docker | Install Docker Engine on the device first |
| Deployment timeout | Check that the device can reach the image registry |
| Web page not loading | Open port 8280 through the device firewall |
| `/dev/ttyUSB0` missing in the container | Redeploy with the serial-device profile |

## Step 2: Open the Control Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

Open the console, create the first administrator, and check that the sources from Step 1 are online.

### Prerequisites

The service from Step 1 is healthy.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page not loading | Confirm Step 1 finished |
| Wrong host/port | If you deployed remotely, use the device IP in the URL |
| A source shows offline | Check reachability and the unit id; for RS-485, also the baud rate and wiring polarity |

## Step 3: Commission the Meter, Control Path and Alarms {#commissioning type=manual required=true verify=true config=devices/commissioning.yaml}

Register the meter, run predictions in observe mode, trigger each failure path to verify rollback and alarms, and enable writes only after all of them pass.

### Prerequisites

- The administrator account from Step 2; a view of the meter's own display; someone who operates this plant to review the recommendations.
- Run `docker inspect -f '{{.Config.Image}}' missionpack_knn` to check the image version. `v1.6.5` does not include the SDM630 template, rollback or alarms; only the observe-mode part can be completed on it.

### Turn on write-back verification

Write-back verification is off by default. Add a `rollback` section when you create the prediction run in the console:

```json
{
  "schema_version": "prediction-run.v3",
  "interval_seconds": 60,
  "rollback": { "enabled": true, "settle_seconds": 2.5 }
}
```

`settle_seconds` (0–30, default 1.0) must be longer than the source's collection interval, or readback reports a false mismatch. Only Modbus points are verified; BACnet outputs are not.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Meter template import rejected | Templates are limited to 256 rows; trim the custom template |
| Voltage and frequency look plausible but wrong | Switch the float word order in the deployment form and re-read |
| Imported energy jumps backwards | Switch word order; or check for two sources polling the same meter with different unit ids |
| A write is acknowledged but the readback never verifies | Check the point's quality; readback does not verify unless quality is good |
| A rollback itself fails | A critical compensation-failed alarm is raised. Restore the plant by hand and do not re-enable writes until the cause is found |
| The same fault opens a new alarm each time | Compare the source and point ids of the two alarms |

### Deployment Complete

#### Quick verification

1. `docker inspect -f '{{.Config.Image}}' missionpack_knn` returns the version you intend to run.
2. All ten SDM630 points read, and voltage, frequency and imported energy agree with the meter's own display.
3. Imported active energy only increases, and survives a restart of the source.
4. A full occupancy cycle of predictions has run in observe mode and the recommendations have been reviewed by the plant operator.
5. The safety limits carry an approver's name; the baseline no longer reports as unapproved.
6. One write inside the limits produced a command receipt, a readback within tolerance, and a point quality of good.
7. Source-offline, readback-mismatch and stale-sample faults each produced the expected alarm, and the first two each triggered a rollback.
8. If northbound publishing is enabled, `northbound.spool.queued` in `GET /system/runtime-metrics` is 0 with `dropped` unchanged.

#### Evidence to export

For the handover record: the image version; the meter template id and confirmed word order; the approved safety limits and approver; the command audit trail for the verified write; the rollback journal entries from the fault injection; the alarm history. Container logs (`docker logs missionpack_knn`) rotate, so copy what you need promptly.

#### Next steps

1. Enable writes on one zone only, and watch it for a full cycle before widening.
2. Set up notifications for the critical compensation-failed alarm.
3. Re-approve the safety limits whenever the plant is rebalanced.
