# Internal status — Edge Inspection: Surface Defects

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rules "results / KPI only carry measured numbers"
and "pages use Seeed product names".

## Bench hardware mapping

| Bench board | Page name |
|---|---|
| fleet `harvest-pi` (Raspberry Pi 5 + Hailo-8 M.2, 15-minute exclusive window, 2026-09-06) | reComputer R2000 (Hailo-8), family `recomputer_r20_industrial` |
| Jetson Orin NX 16GB, L4T R36.4.3 / JetPack 6.2 | reComputer Super J4012 |
| arm64 Mac, onnxruntime CPUExecutionProvider | development-machine CPU, offline baseline only |
| NVIDIA Spark GB10 workstation (VLM latency) | the shared VLM service's own workstation |

## Reproduction status

Every figure on the page is a single measurement by the original author, never
independently reproduced. All boundary files carry `reproduced_by: null`.

## Rows and sections removed from the page

**72 h soak — not available.** Started 2026-09-05T06:22:47Z, due
2026-09-08T06:22Z. Baseline at start: RSS 250.5 MiB, 10.9% CPU, 9.96 FPS,
0 dropped, Tj 62.1-62.7 C. `boundary.soak.yaml` all tiers null.

**Hailo emulator HEF comparison (`2026-09-05-m3-hef`).** Two HEF builds from
the same ONNX on the same 20 validation images (45 boxes), disjoint from the
calibration set, spread evenly across the six classes:

| Path | mAP50 | P at 0.35 | R at 0.35 | Whole-frame misses | Conditions |
|---|---:|---:|---:|---:|---|
| CPU onnxruntime (reference) | 0.7228 | 0.6429 | 0.6000 | 0 | Same ONNX, same 20 images |
| Emulator, INT8 level-0 | 0.6927 | 0.7353 | 0.5556 | 3 | `optimization_level=0`, 128 calibration images from val |
| Emulator, INT8 level-1 | 0.7266 | 0.7179 | 0.6222 | 2 | `optimization_level=1`, 1024 calibration images from train, Bias Correction |

Level-1 is the deployed default. It recovers inclusion 0.5415 to 0.6552 and
rolled-in scale 0.4048 to 0.5108, at 773 s to 1180 s compile time (all in the
optimize step). Its mAP50 lands 0.0038 above the CPU float baseline — sampling
noise on 20 images, not evidence that INT8 beats float.

What the emulator can and cannot show: it uses the fixed-point parameters from
the compiled model, so it demonstrates that the nine-tensor output assembly is
numerically equivalent to the CPU path (42 of 42 boxes matched, minimum IoU
0.9992) and it quantifies INT8 loss on that subset. It is not bit-exact with
the hardware, and its timing figures are x86 GPU timings unrelated to a
Hailo-8.

**Known gap in the on-device Hailo run.** The `compare` JSON's match-count
fields (`matched_pairs` / `a_only` / `b_only`) were not re-saved before device
cleanup. The mAP50 and score-delta numbers themselves are intact. See
`evaluation/runs/2026-09-06-rpi-hailo/results.md` §7.2 and §7.9.

**Detector track comparison is single-seed.** Each of YOLOX-Tiny, D-FINE-S and
RT-DETRv2-S has run one seed. Three seeds are needed before the
matched-precision claim (D-FINE recall 2-7 points above YOLOX, whole-frame
misses 20 vs 38) counts as settled.

**RKNN converts but is unverified on hardware.** Both ONNX files convert to
`.rknn` for RK3576 (FP16, no quantization) successfully, but 18 `GridSample`
nodes (9 per model) fall back to a custom-operator lowering with no NPU
implementation. A successful conversion does not mean that part of the graph
runs on the NPU. No RK3576 device was reachable to confirm output parity
against CPU. Unverified, not a negative result. Source:
`evaluation/runs/2026-09-06-a1-probe/results.md`.

**VLM integration test.** `evaluation/runs/2026-09-06-mvlma-stub-localhost/results.md`
is a Mac stub-backend integration test, not a real-model latency measurement.
No Orin-specific VLM latency has been measured.

## Dataset licence

The model is trained on a re-hosted copy of NEU-DET. The Roboflow page for that
copy states CC BY 4.0, but no formal licence statement has been found for the
original NEU-DET release, so the chain from the original authors to that page is
not established. Everything derived from it — the checkpoint, the ONNX, both
HEFs, the TensorRT engine, the evaluation overlays — is restricted to internal
validation until an explicit answer arrives or the dataset is replaced. No
dataset-derived image is committed to this package.
