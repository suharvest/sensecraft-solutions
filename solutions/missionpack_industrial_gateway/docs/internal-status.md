# Internal status — MissionPack Industrial Gateway

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rules "results / KPI only carry measured numbers"
and "pages use Seeed product names".

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| fleet `harvest-pi` (Raspberry Pi 5, arm64) — **not a package device** | development-board baseline (Raspberry Pi 5, not a package device) |
| fleet `spark` (arm64 workstation) | development workstation |

The load numbers on the page do **not** come from any device sold in a package.
Package-device runs on reComputer R1000 / R2000 are still to be done; until they
land, the page says so in one line.

Upstream commits behind the runs: `b5fe4cc` (capacity smoke), `f831bae`
(northbound recovery).

## Row removed from the page

**24 h continuous run — result pending.** A 24 h `release` soak started on
`harvest-pi` at 2026-09-05T05:01:19Z and ends 2026-09-06T05:01:19Z. No verdict
read yet. 2,000 points, OPC UA/Modbus 5 s + BACnet 10 s. To be filled in once
the verdict file is read.

## Reproduction status

None of the boundary figures has been independently reproduced. Each tier was
measured on one device, single sample.

## Untested paths

All northbound measurements ran over plaintext on a single machine's loopback
under a **test** runtime profile. The production strict-TLS path and any real
network impairment (jitter, partial loss, half-open connections) are untested.
An outage in these runs is a killed broker process or container, not a degraded
link.
