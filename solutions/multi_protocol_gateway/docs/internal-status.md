# Internal status — MissionPack Industrial Gateway

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rules "results / KPI only carry measured numbers"
and "pages use Seeed product names".

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| fleet `harvest-pi` (Raspberry Pi 5, arm64) — **not a package device** | development-board baseline (Raspberry Pi 5, not a package device) |
| fleet `seeed-pi4` (Raspberry Pi 4B, 2 GB, 4 x Cortex-A72, arm64) | reComputer R1000 CM4 platform, 2 GB configuration — **reference value, not a shipping configuration** (R1000 ships 4 GB / 8 GB) |
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

## reComputer R1000 platform run, 2026-09-07

Bench host `seeed-pi4` is a Raspberry Pi 4B with **2 GB** of RAM. It shares the
CM4-class SoC generation with the reComputer R1000, so the page calls it a
platform reference value and says in the same sentence that the R1000 ships
with 4 GB or 8 GB and has not been re-run. Do not let that qualifier be edited
out.

The failures measured there are **not** memory failures: available memory stayed
between 1041 and 1076 MB across all four profiles, swap did not grow, and the
board never throttled (60.3-65.7 C at profile end). The boundary is CPU and
timing. A 4 GB / 8 GB R1000 is therefore not expected to change the result, but
that is an inference and has not been measured.

Not done on that bench, and why: console screenshots and, for the warehouse, the
whole authenticated load matrix. Every console page redirects to a first-run
"create administrator" screen, and the operator running the bench does not
create accounts or fill in passwords. Someone with that authority has to seed
the admin and the API keys before those rows can be filled in.
