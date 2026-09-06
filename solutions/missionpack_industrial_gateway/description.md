## What This Solution Helps You Do

For building, energy, and equipment-management integrators, the expensive part is often not the dashboard. It is rebuilding controller drivers, point mappings, and data conversions at every customer site. This solution brings OPC UA, Modbus, BACnet/IP, and MQTT into one point model, so upstream systems integrate with one MQTT read/write interface.

Site differences become configuration: add a controller, discover or enter points manually, verify data quality, and expose selected data to an energy platform, SCADA, cloud service, or customer application. Integrators no longer need a separate protocol-conversion layer for every project.

The solution is designed first for the reComputer R1000/R1100 Series and reTerminal DM Series, including on-device touch operation on reTerminal DM.

The prediction workflow remains available as an optional plugin. Multi-protocol access, unified point management, and data service work independently without training a model.

## Key Benefits

| Benefit | What it means on site |
|---------|-----------------------|
| Integrate several field protocols once | OPC UA, Modbus TCP/RTU, BACnet/IP, and MQTT share one point model instead of separate upstream adapters |
| Turn site differences into configuration | Browse OPC UA, scan Modbus units, use BACnet Who-Is, or observe MQTT topics; enter points manually whenever discovery is incomplete |
| Read and control through one interface | The embedded broker publishes versioned data, presence, command, and receipt topics, so integrators maintain one northbound contract |
| Verify and trace every control result | Check permissions and data quality before a write, then inspect effective value, device readback, and command receipt |
| Reuse the integration across projects | New deployments mainly change controllers and point mappings instead of rebuilding the protocol bridge beneath each application |

## Use Cases

| Scenario | How it is used |
|----------|----------------|
| Building energy solution delivery | Bring BACnet/IP air handlers and Modbus meters into one point model, then feed an energy dashboard or customer platform |
| HVAC retrofit | Keep an OPC UA controller while adding MQTT sensors; upstream control continues through the same interface |
| Multi-vendor equipment integration | Resolve protocol and addressing differences on a reComputer R1000/R1100 or reTerminal DM, then expose one contract to the customer system |
| Controlled optimization | Add the prediction plugin above the unified points, import CSV data, select inputs and outputs, and trace every control result |

## Measured Boundaries

These numbers come from a synthetic four-protocol simulator rig on one device each, not from a customer site. They bound the software on that specific hardware and workload; they are not a performance warranty and do not extrapolate to other devices. None of them has been independently reproduced.

| Metric | Value | Conditions | Source |
|--------|-------|------------|--------|
| Refresh cycle — stable tier | 349.99 events/s (99.99% of the 350.0 target), prediction 0.939 cycle/s, peak process-group RSS 217.3 MiB, 1-minute CPU peak 22.1%, 0 failed-sample deltas | 2,000 points across 4 sources (500 each), OPC UA/Modbus 5 s + BACnet 10 s, 180 s run, loopback only | harvest-pi (Raspberry Pi 5, arm64), r14 `capacity-smoke`, upstream @ `b5fe4cc`; this run, single sample |
| Refresh cycle — degrading tier | Ran the full 900 s at 718.9 events/s (99.1%), but prediction dropped to 0.872 cycle/s and the gate failed (`PREDICTION_CYCLE_RATE_LOW`) | Same 2,000 points, tightened to OPC UA/Modbus 2 s + BACnet 4 s | Same device and rig, non-frozen boundary-finding profile |
| Refresh cycle — failure tier | `PREDICTION_WRITE_CHAIN_TIMEOUT` at 148.2 s, well short of the 900 s target; 2 Modbus input points were already missing in the first warm-up cycle | Same 2,000 points, tightened to OPC UA/Modbus 1 s + BACnet 2 s | Same device and rig |
| Point-count ceiling | 2,000 points (50 of them writable) | Product registry design ceiling, enforced in code | Design limit, **not** a measured device ceiling — the 4,000/8,000-point attempts were rejected by a 500-points-per-source simulator guard before reaching the device |
| Northbound spool growth during an outage | 60.1 KB/s queued-bytes growth; 18.33 MB / 325 batches at peak; spool drained to zero after reconnect | 300 s cloud-broker outage at ~350 events/s, spool limits 512 MB / 86400 s, 1,800 s run | spark (arm64), `northbound-recovery`, upstream @ `f831bae` |
| Broker restart to first replayed message | 1.2–2.2 s | Same runs; measured as restart-to-first-replay, which is an upper bound on CONNACK-to-first-replay | Same rig |
| Replay completeness | 1.000 against a persistent broker with a durable subscriber session; 0.9839 against a purely in-memory broker | Same 300 s outage. All 58 messages missing in the in-memory case arrived 0.496–1.058 s after broker restart, before the test subscriber's SUBACK at 1.069 s — a harness observation blind window, not gateway loss | Same rig, broker-side acknowledgement journal, message-id set intersection |
| 24 h continuous run | **Result pending.** A 24 h `release` soak started on harvest-pi at 2026-09-05T05:01:19Z and ends 2026-09-06T05:01:19Z; no verdict yet | 2,000 points, OPC UA/Modbus 5 s + BACnet 10 s | harvest-pi; to be filled in once the verdict file is read |

Open issues carried by these runs:

- The prediction loop sleeps a fixed interval *after* each cycle, so its rate is `1/(1.0 + t_cycle)`. At 2,000 points `t_cycle` is about 0.119 s, putting the structural ceiling near 0.894 cycle/s — below the 0.90 gate. This reproduced on all four round-3 runs including the control run with no outage injected. Either the loop or the gate has to change; it is not yet fixed.
- All northbound measurements ran over plaintext on a single machine's loopback under a test runtime profile. The production strict-TLS path and any real network impairment (jitter, partial loss, half-open connections) are untested.
- An outage is a killed broker process or container, not a degraded link.

## Usage Notes

### Core Hardware

| Device | Purpose | Required |
|--------|---------|----------|
| reComputer R1000 Series | Runs multi-protocol access, the unified point model, MQTT data service, and web console | Choose one |
| reComputer R1100 Series | Runs multi-protocol access, the unified point model, MQTT data service, and web console | Choose one |
| reTerminal DM Series | Runs the same services and provides an on-device touch display for setup and operations | Choose one |
| USB-to-RS-485 adapter | Connects a Modbus RTU bus | Only for Modbus RTU |

### Network and Protocol Boundaries

- The data-hub device must be able to reach each Ethernet protocol network. BACnet broadcasts may require the correct network interface and subnet configuration.
- OPC UA browsing, BACnet Who-Is, Modbus TCP unit scanning, and MQTT topic observation create candidates. A user must confirm candidates before they become managed points.
- Modbus RTU configuration and transport are included, but the standard Docker profile does not attach a host serial device. Use the serial-device installer/profile, and keep production writes disabled until the exact USB-to-RS-485 adapter and target controller pass hardware-in-the-loop validation.
- The remote Linux target uses host networking so BACnet/IP broadcast discovery can reach the physical subnet. Docker Desktop's bridged local target may require manual BACnet addressing.
- Deployment runs a network-isolated, one-shot volume ownership migration before the non-root data service starts. This preserves data created by earlier root-based images while keeping the long-running service unprivileged.
- The northbound service uses the native **MissionPack v1 MQTT topic contract**. It is inspired by industrial lifecycle messaging but is **not Sparkplug B compatible** in this release.
- Plain MQTT is telemetry-only. Enable TLS and an authorized control identity before allowing remote commands.
