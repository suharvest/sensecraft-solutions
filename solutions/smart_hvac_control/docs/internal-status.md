# Internal status — Smart HVAC Control

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rules "results / KPI only carry measured numbers"
and "pages use Seeed product names".

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| fleet `harvest-pi` (Raspberry Pi 5, arm64) — **not a package device** | development-board baseline (Raspberry Pi 5, not a package device) |

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
