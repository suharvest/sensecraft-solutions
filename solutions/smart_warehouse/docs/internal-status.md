# Internal status — Smart Warehouse

Internal record. Not published on the deployment page. The bench host name was
removed from `description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rule "pages use Seeed product names".

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| fleet `harvest-pi` (Raspberry Pi 5, arm64) — **not a package device** | development-board baseline (Raspberry Pi 5, not a package device) |
| fleet `seeed-pi4` (Raspberry Pi 4B, 2 GB, 4 x Cortex-A72, arm64) | reComputer R1000 CM4 platform, 2 GB configuration — **reference value, not a shipping configuration** (R1000 ships 4 GB / 8 GB) |

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
