# Internal status — Supermarket Product Recognition

Internal record. Not published on the deployment page. Removed from
`description.md`, `description_zh.md` and the `solution.yaml` header comment on
2026-09-07 under the `reference-design-landing` rules "results / KPI only carry
measured numbers" and "pages use Seeed product names".

## Bench hardware mapping

| Bench board | Page name |
|---|---|
| Radxa ROCK 5T (librknnrt 2.3.2, driver 0.9.8) | reComputer RK3588 series |
| Raspberry Pi 5 + Hailo-8 (M.2) | reComputer R2000 (Hailo-8), family `recomputer_r20_industrial` |

## Verification status (from the removed `solution.yaml` header)

Nothing in this package carries `verified: [hardware]`. Parts of it have run on
hardware — the RK3588 detector on a Radxa ROCK 5T, the Hailo-8 detector and the
CPU embedder on a Raspberry Pi 5 — and those numbers are on the page with their
source paths. What has never been run is this package: no preset has been
deployed through the engine, and the device-side pipeline that would join
detection, embedding, gallery lookup and MQTT into one process does not exist
upstream yet. The console stack is the only container stack, and neither of its
images has been pushed.

Every boundary file carries `reproduced_by: null`.

## What has not been measured, and what does not exist

**The embedder does not run on either NPU.** Two Hailo DFC quantisation attempts
were made (`evaluation/runs/2026-09-06-embed-hailo/`) and neither produced a
usable figure:

- The o2 attempt collapsed — every image maps to an identical vector.
- The default attempt lost 20 to 44 points against the fp32 baseline. That
  number is not a conclusion about DFC quantisation: the calibration set fed to
  the optimise stage cannot be shown from the record to have been raw 0-255
  pixels rather than an already-normalised array, in which case the `.alls`
  normalisation ran twice and part of the gap has nothing to do with
  quantisation. The upstream default has been corrected and a dimension check
  added; the default tier has to be re-run under the corrected pipeline before
  anything can be concluded from it.

**RKNN conversion of the embedder was never attempted.**

**No Jetson figure of any kind**, and no TensorRT backend in the repository —
`platforms/` holds console, hailo and rknn only.

**OCR reranking is specified and not implemented.**

**No end-to-end number.** No counting accuracy, no shelf-slot accuracy, no
72-hour run, because the process that would join detection, embedding, lookup
and publishing into one device-side service does not exist yet.

**Detection accuracy sits below the project's own stable threshold.** SKU-110K
test: 640² preset 52.84 mAP50-95, 1280² preset 56.32, against a stable threshold
of 60. Both boundaries sit in the failure tier.

**Hailo die temperature and power draw** could not be read on the Raspberry Pi 5
platform and are recorded as unavailable rather than estimated.

**Gallery UI screenshots** in `gallery/` are synthetic fixtures, not a real
recognition run.

## Evaluation run paths

- `evaluation/runs/2026-09-06-det-hef/` — Hailo-8 detector latency and parity
- `evaluation/runs/2026-09-06-det-rk3588-radxa/` — RKNN parity and latency
- `evaluation/runs/2026-09-06-embed-small/` — CPU embedder latency and retrieval
- `evaluation/runs/2026-09-06-embed-ft/` — retrieval accuracy
- `evaluation/runs/2026-09-06-det-sku110k/` — detection accuracy
- `evaluation/runs/2026-09-06-embed-hailo/` — failed Hailo embedder quantisation
