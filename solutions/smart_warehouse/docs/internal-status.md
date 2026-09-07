# Internal status — Smart Warehouse

Internal record. Not published on the deployment page. The bench host name was
removed from `description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rule "pages use Seeed product names".

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| fleet `harvest-pi` (Raspberry Pi 5, arm64) — **not a package device** | development-board baseline (Raspberry Pi 5, not a package device) |

The load numbers on the page do **not** come from any device sold in a package.
Package-device runs on reComputer R1000 / R2000 are still to be done; the page
carries one line saying so.

Raw run data lives under `runs/2026-09-05-load/raw-harvest-pi/` in the upstream
project. The page cites those files as `raw-rpi5/` so the bench host name does
not appear; if the upstream directory is renamed, keep the two in step.

Re-test after the concurrency fixes: `evaluation/runs/2026-09-06-a2-retest/results.md`,
also run on the same Raspberry Pi 5 board.

## Guide notes still carrying the bench host

`guide.md` / `guide_zh.md` troubleshooting rows describe the 409 / 429 fixes as
"pending re-test on harvest-pi". Those are engineering notes on the guide, not
customer-facing results copy; update them when the package-device runs land.
