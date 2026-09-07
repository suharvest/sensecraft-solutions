# Internal status — Smart HVAC Control

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rules "results / KPI only carry measured numbers"
and "pages use Seeed product names".

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| fleet `harvest-pi` (Raspberry Pi 5, arm64) — **not a package device** | development-board baseline (Raspberry Pi 5, not a package device) |
| fleet `seeed-pi4` (Raspberry Pi 4B, 2 GB, 4 x Cortex-A72, arm64) | reComputer R1000 CM4 platform, 2 GB configuration — **reference value, not a shipping configuration** (R1000 ships 4 GB / 8 GB) |

The load numbers on the page do **not** come from any device sold in a package.
Package-device runs on reComputer R1000 / R2000 are still to be done.

Upstream commits behind the runs: `b5fe4cc` (capacity smoke), `f831bae`
(northbound smoke baseline).

## Rows removed from the page

**24 h continuous run — result pending.** A 24 h `release` soak started on
`harvest-pi` at 2026-09-05T05:01:19Z and ends 2026-09-06T05:01:19Z. The verdict
is not in. No 7-day or 30-day run has been started.

**Meter accuracy and byte order — not verified against hardware.** The SDM630
addresses follow the vendor's published Modbus protocol document and the
template defaults to big-endian bytes and words. Kept on the page as a
commissioning instruction rather than a test-status row.

**Rollback and alarms in a running cycle — not measured end to end.** The
rollback coordinator and the alarm envelope have their own acceptance tests, but
they are not yet wired into the prediction cycle upstream.

**Energy savings — not measured.** No baseline comparison, no weather or
occupancy normalisation, and no defined measurement period exist yet. Any
percentage would be invented. The page now says savings are site-dependent
instead.

## Reproduction status

Every figure is a single sample unless stated; none is independently reproduced.
The control-admission (n=2) and prediction-cycle (n=4) latencies are smoke runs
and describe nothing about a loaded system.

## Known-open defect

The prediction loop sleeps a fixed interval after each cycle, so its rate is
`1/(1.0 + t_cycle)`. At 2,000 points `t_cycle` is about 0.119 s, putting the
structural ceiling near 0.894 cycle/s — below the 0.90 gate the soak harness
enforces. This reproduced on every round-3 run including one with no fault
injected. Either the loop or the gate has to change; neither has.

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
