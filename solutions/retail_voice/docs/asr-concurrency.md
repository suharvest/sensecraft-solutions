# ASR concurrency evidence

This note records the source for the capacity table in the retail voice descriptions.
The handoff is `seeed-solutions-hub@802b8a1/docs/reports/handoff-asr-concurrency-2026-09-09.md`.
Raw benchmark outputs are in `openvoicestream@1d44ef5/bench/asr_bench/results/`.

## Scope and method

- Metric: audio-end to `is_final`; recommendation is the highest tested level with p95 ≤ 1.5 s.
- SenseVoice zh: the unified cross-device comparison uses the same 100-item AISHELL-1 subset (aggregate CER 4.82%); the separate RK 172-frame run reports 4.74% and is not substituted into the unified figure.
- Whisper base en: fixed 72-item LibriSpeech test-clean subset on Jetson/RK; fixed 100-item ≤4 s subset on R2000.
- Runs used the repaired client (`?vad=none`, all final messages collected) where the cited matrix says so; boards were idle with non-ASR containers stopped unless the source says otherwise.
- The benchmark mounted OpenVoiceStream/voxedge main-branch changes over frozen images. It does not establish that the current solution images ship those changes.

## Source files

| Device/model | Source result |
|---|---|
| J4012 | `openvoicestream@1d44ef5:bench/asr_bench/results/concurrency-orin-nx-ceiling.md` |
| J3011 | `openvoicestream@1d44ef5:bench/asr_bench/results/concurrency-orin-nano-ceiling.md` |
| RK3576 SenseVoice | `openvoicestream@1d44ef5:bench/asr_bench/results/concurrency-cat-remote-t172.md` |
| RK3588 SenseVoice | `openvoicestream@1d44ef5:bench/asr_bench/results/concurrency-radxa-t172.md` and `concurrency-radxa-ceiling.md` |
| R2000 SenseVoice/Whisper | `openvoicestream@1d44ef5:bench/asr_bench/results/concurrency-harvest-pi-ceiling.md` |
| RK3576/RK3588 Whisper | `openvoicestream@1d44ef5:bench/asr_bench/results/concurrency-cat-remote-ceiling.md` and `concurrency-radxa-ceiling.md` |

The RK172-frame results are retained as a separate run family. RK3588's c=12
run had client errors, while the corrected post-fix verification provides a
clean c=1 reference; the description therefore reports the observed c=8
capacity and its c=12 boundary without presenting it as a universal hardware
limit.
