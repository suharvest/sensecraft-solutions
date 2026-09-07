## What This Solution Does

Central HVAC plants in offices, malls and factories usually run a fixed schedule: the same setpoint whether the floor is full or empty. This solution brings the HVAC controller and an energy meter into one point model, learns a setpoint recommendation from the building's own historical data with a KNN model, and writes it back to the controller — but only after the write has been read back from the field and compared against what was sent.

It starts in observe-first mode. Nothing is written until an operator enables control, and the safety limits that bound every write are placeholders until a site engineer approves them.

## What You Get

**One point model for HVAC and energy.** The HVAC controller arrives over OPC UA, Modbus TCP/RTU or BACnet/IP. The energy meter arrives through a built-in Eastron SDM630 template (Modbus V2 register map, IEEE-754 float32 input registers) covering three-phase voltage and current, total active power in kW, total power factor, frequency and imported active energy in kWh. The template renders the same strict CSV an operator would write by hand, so a built-in template and a hand-written one are validated by the same parser and the same 256-row limit. Meter points are read-only and count against the 2,000-point registry total, not against the 50 writable points.

**Setpoint prediction from your own data.** Import a CSV or Excel export of historical operation; the KNN model learns from that building rather than from a generic curve. Predictions are visible before any of them is allowed to reach the controller.

**Writes that are read back, not assumed.** An acknowledgement from a controller is not proof that the plant moved. Every write freezes the last-known-good value, quality, timestamp and BACnet priority first, then reads the point back after a delay and compares within a tolerance. A readback whose quality is not good never counts as confirmed, whatever value it carries.

**Rollback on five triggers.** Readback mismatch, source offline, prediction disabled, operator abort, and a partially applied batch. BACnet points are released with Null at the priority they were written at; Modbus points are restored in the reverse of the order they were applied. Compensation travels the same authorised write path as the original write, so it cannot bypass the write-enable flag or the write policy.

**Alarms tied to causes, not to events.** Five alarm types — source offline, stale sample, write failed, readback mismatch, compensation failed — each identified by its cause, so repeating the same fault re-uses the open alarm instead of opening a second one. Compensation-failed is critical because the plant is left in an unknown state; the other four are warnings because the plant keeps its previous setpoint. Acknowledging an alarm records that an operator saw it; only a recovery clears it, and the recovery carries the id of the alarm it clears.

**Bounded safety limits.** Setpoint minimum and maximum, a maximum change per time window, and a mode whitelist. The shipped defaults (18–30 °C, 1 °C per 5 minutes, off/fan/cool/heat/auto) stay unapproved until a named site engineer signs them off.

## Use Cases

| Scenario | How it is used |
|----------|----------------|
| Office buildings | Predict a setpoint per zone from that building's own history, run it in observe mode through a full occupancy cycle, then enable writes on one zone first |
| Shopping malls | Register a meter per floor so power and energy sit next to the HVAC points that drive them, and compare predicted against actual before trusting either |
| Factory floors | Line the prediction up with the production schedule, keeping the rate limit tight enough that a shift change cannot swing the plant in one step |
| Retrofits on mixed plant | Bring an OPC UA chiller and a BACnet/IP air handler into the same point table and use one control path with one audit trail across both |

## How Well It Works

This is not a safety-certified control system. It is a supervisory setpoint recommender with a read-back write path; the plant's own interlocks and safety controls stay in charge, and every write stays inside limits a site engineer approves.

Numbers below come from a simulator rig, not from a building.

The load figures in the table were taken on a **development-board baseline (Raspberry Pi 5, not a package device)**. A second run on 2026-09-07 covered the **reComputer R1000's CM4 platform in a 2 GB configuration** — a reference value, not a shipping configuration, since the R1000 ships with 4 GB or 8 GB. On that platform the frozen "capacity-smoke" profile did not complete: it stopped after 90.2 s of its 180 s target with "QUEUE_BOUND_EXCEEDED". Tightening the cycle to 2 s or 1 s never reached a running state at all — the Modbus source failed all 500 of its points with "BATCH_DEADLINE_EXCEEDED". Free memory stayed above 1 GB throughout and the board never throttled, so this is a CPU and timing boundary rather than a memory one. Numbers on a 4 GB / 8 GB R1000 will be added after that re-run.

| Metric | Value | Conditions | Source |
|--------|-------|------------|--------|
| **Energy savings** | Not claimed | — | Savings depend on the building, the weather and the occupancy pattern. Run a controlled before/after study on your own site rather than planning against a published percentage |
| Control admission latency | 1.41 ms maximum | n = 2 cycles, smoke run only | **Smoke measurement.** Runtime metrics from the "northbound-smoke" rig baseline, upstream @ "f831bae". Two samples describe nothing about a loaded system |
| Prediction cycle latency | 46.27 ms maximum | n = 4 cycles, smoke run only | **Smoke measurement.** Same baseline capture, same caveat |
| Sampling throughput | 349.99 events/s against a 350.0 target (99.99%), prediction 0.939 cycle/s, peak process-group RSS 217.3 MiB | 2,000 points across 4 protocol sources, OPC UA/Modbus 5 s and BACnet 10 s, loopback only, 180 s run | Development-board baseline (Raspberry Pi 5, arm64), r14 "capacity-smoke" |

The prediction loop sleeps a fixed interval after each cycle, so its rate is "1/(1.0 + t_cycle)". At 2,000 points "t_cycle" is about 0.119 s, putting the structural ceiling near 0.894 cycle/s. Size the cycle time for your point count accordingly.

**Confirm the meter byte order at commissioning.** The SDM630 addresses follow the vendor's published Modbus protocol document and the template defaults to big-endian bytes and words. Check the order against the meter in front of you before trusting the values.

## Requirements

**Hardware**

| Item | Purpose | Required |
|---|---|---|
| reComputer R1100 (or any Docker host, x86-64 or arm64) | Runs the point model, prediction, control path and console | Yes |
| Eastron SDM630 energy meter | Power and energy points | For the meter workflow |
| USB-to-RS-485 adapter | Only if the meter is on RS-485 rather than Modbus TCP | Modbus RTU only |
| HVAC controller speaking OPC UA, Modbus or BACnet/IP | The plant being read and written | Yes for control; the built-in simulator covers a dry run |

**Data**

At least one week of historical operation as CSV or Excel, with timestamp, setpoint, measured temperature and power consumption. Import takes a few minutes.

**Software**

Docker Engine 20.10 or newer, about 1 GB free disk, and host ports 8280 (console) and 4841 (OPC UA simulator) free.

## Usage Notes

- **Observe before control.** Run predictions without writes through at least one full occupancy cycle. Enabling writes before the recommendations have been compared against what the plant actually does is how a supervisory layer causes a comfort complaint.
- **Approve the safety limits.** The shipped 18–30 °C, 1 °C per 5 minutes and five-mode whitelist are placeholders. They report as unapproved until a named engineer signs them off, and they should be replaced with the plant's own commissioned limits, not merely confirmed.
- **Confirm the meter's byte order.** Vendor defaults are not universal. Read a register with a known physical value before believing the scaled points.
- **Modbus RTU needs the serial-device profile.** The standard Docker profile attaches no host serial device. Keep production writes disabled until the exact adapter and the target controller have passed hardware-in-the-loop validation.
- **Central plant only.** This addresses central HVAC systems, not split-unit air conditioners.
- **Image tag.** The published image "missionpack-knn:v1.6.5" predates the meter template, the rollback coordinator and the alarm envelope. The image carrying them has not been built or pushed and its immutable tag is still to be assigned. Check the tag before following the commissioning steps in the deployment guide.
