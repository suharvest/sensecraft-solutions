# Internal status — Retail Voice, Local Transcription

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rules "results / KPI only carry measured numbers"
and "pages use Seeed product names".

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| fleet `cat-remote` (RK3576 board) | reComputer RK3576 |
| fleet `seeed-pi` (Raspberry Pi 4, Cortex-A72, 4 cores) | Raspberry Pi 4 as a stand-in for the reRouter CM4 — same SoC generation |

## Row removed from the results table

**ASR accuracy and latency, CM4 — not measured.** The `asr_zh_en` row for
RPi4 / CM4 in the bench matrix is still `TBD`. The published expectation,
"2-3x slower than RPi5", is an estimate, not a measurement. Sources:
`openvoicestream/docs/perf-test-runbook.md` matrix row;
`docs/performance-comparison.md` "Devices not yet measured".

The page now says to pilot one store on the CM4 path before rolling out, which
carries the same buying advice without publishing the gap.
