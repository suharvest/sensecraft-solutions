# Internal status — Supermarket Product Recognition

Internal record. Not published on the deployment page. Removed from
`description.md`, `description_zh.md` and the `solution.yaml` header comment on
2026-09-07 under the `reference-design-landing` rules "results / KPI only carry
measured numbers" and "pages use Seeed product names".

**This file is a snapshot, not a live status.** The implementation lives in a
separate repository, `edge-retail-recognition`, and moves independently of this
package. Check its `git log` and `evaluation/runs/` before quoting anything
below. Last refreshed **2026-09-20** against `1a4b5ed`; the 2026-09-07 version
of this file had gone two weeks stale and was still saying the device-side
pipeline did not exist.

## Bench hardware mapping

| Bench board | Page name |
|---|---|
| Radxa ROCK 5T (librknnrt 2.3.2, driver 0.9.8) | reComputer RK3588 series |
| Raspberry Pi 5 + Hailo-8 (M.2) | reComputer R2000 (Hailo-8), family `recomputer_r20_industrial` |

## Verification status (from the removed `solution.yaml` header)

Nothing in this package carries `verified: [hardware]`, and every boundary file
carries `reproduced_by: null` — no number here has been reproduced by anyone
other than the person who first measured it. Independent reproduction, not
implementation, is now the main thing between this package and a verified
preset.

The device-side pipeline exists. `core-py/core_retail/runtime/__main__.py` is the
common entry point; `platforms/{jetson,rk3588,pi-hailo}/runtime.py` each build
their own backend and call into it. Checkout replay has run end to end on
RK3588 and Orin Nano — 6726 frames, zero dropped frames, zero detection or
embedding errors, 84 events all published.

Both container images are on the registry: `edge-retail-console-server:0.2.0`
and `edge-retail-console-web:0.1.0`, the server manifest carrying amd64 and
arm64.

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

**RKNN conversion of the embedder succeeded, with parity.** RK3588: top-1
identical to the CPU-small reference over 704 shelf crops, 0.00 pp apart
(541/704 both ways). RK3576: 76.28 % against 76.99 %, -0.71 pp, agreeing on
99.29 % of crops. An earlier 10 pp gap was measured on N=20 and is superseded by
the N=704 rerun.

**The TensorRT backend exists and has run on two Jetson boards.** Orin NX 16 GB:
detection and embedding within 0.241 pp of the CPU reference, 198 s of checkout
with zero dropped frames. Orin Nano 8 GB (J30): within 0.2012 pp, 6726 frames,
zero drops.

**OCR reranking is specified and not implemented.**

**No accuracy number for either scenario.** Replay pass rates and latency exist
— RK3588 console end to end at 924 ms p50 / 1153 ms p95, identity rejection and
reconnect both passing — but nothing measures what the user actually sees:
**counting accuracy** at the checkout (items over- or under-counted per basket)
and **shelf-slot accuracy** (empty and misplaced slots called correctly). Those
two are the acceptance metrics; neither has been run. No 72-hour run either.

**The detection threshold is miscalibrated, not the detector.** SKU-110K test:
640² preset 52.84 mAP50-95, 1280² preset 56.32, against a failure tier of
anything under 60. That 60 is a generic boundary value from
`evaluation/README.md` (≥75 stable, 60–75 degrading, <60 failure), applied
unchanged to every metric — it was not set from this dataset. Published results
on SKU-110K reach 58.0 (DenseDet, Cascade R-CNN + ResNeXt-101) and 58.7
(arXiv 2007.11946), so the tier sits above the public state of the art and no
model passes it. A YOLOX-tiny at 56.32 is 2.4 points off that mark.

The same run records **mAP50 88.26** at 640²: the boxes are found, they are not
tight. For this pipeline the box is a crop fed to the embedder, so loose boxes
risk pulling in the neighbouring product and mis-identifying the SKU — a
recognition error, not a miss. How large that risk is can only come from the
counting and shelf-slot numbers above; it does not follow from mAP50-95.

Seven places quote the 60: `evaluation/README.md:34` and the SKU-110K boundary
file in `edge-retail-recognition`, this file, `devices/verify_recognition.yaml`
(English and Chinese), and `wiki/{en,zh-CN,ja}.md:265` in the hub.

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
- `evaluation/runs/2026-09-07-jetson-trt/` — Orin NX TensorRT parity and checkout
- `evaluation/runs/2026-09-08-orin-nano-acceptance/` — Orin Nano 8GB acceptance
- `evaluation/runs/2026-09-08-rk3588-console-acceptance-020/` — RK3588 end to end, RKNN parity at N=704
- `evaluation/runs/2026-09-08-rk3576-acceptance/` — RK3576 rerun on the same crops
