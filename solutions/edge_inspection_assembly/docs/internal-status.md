# Internal status — Edge Inspection: Assembly

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rules "results / KPI only carry measured numbers"
and "pages use Seeed product names".

## Rows removed from the results table

**Hailo INT8 (HEF) accuracy — emulator, not a device.** mAP50 0.9924, identical
on all three paths. 20 val images / 118 boxes; CPU onnxruntime, Hailo emulator
`SDK_NATIVE`, and emulator `SDK_QUANTIZED` (optimization level 1 + Bias
Correction) return the same mAP50 / P / R / FP / FN. Per-box: CPU vs native
120/120 matched; CPU vs quantized 119/120. M3a run, 2026-09-05, in the Hailo
Dataflow Compiler emulator on x86. Superseded on-page by the on-device
reComputer R2000 numbers.

**72 h soak — in progress at packaging time.** Single stream, looped 300 s
video, 10 fps. Baseline over the first samples: RSS 256-259 MiB, 0 dropped
frames, tj 61-62 C, 0 restarts. M4 run; the three tiers in `boundary.soak.yaml`
are null until it finishes.

**Reproduction status.** All five boundary files record `reproduced_by: null`:
single measurements by the author, on one device each.

**Not measured on the Hailo path.** Multi-stream capacity. The multi-stream
sweep is Orin-only.

## Bench hardware mapping

| Bench board | Page name |
|---|---|
| fleet `harvest-pi` (Raspberry Pi 5 + Hailo-8 M.2, 15-minute exclusive window, 2026-09-06) | reComputer R2000 (Hailo-8), family `recomputer_r20_industrial` |
| fleet `orin-nano` (Orin NX 16GB engineering kit, JetPack 6.2 / TRT 10.3) | reComputer J40 series |

Raw run data: `evaluation/runs/2026-09-06-rpi-hailo/results.md`,
`evaluation/runs/2026-09-05-m3-hef/`.
