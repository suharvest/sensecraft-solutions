# Internal status — Interruptible Conversational Voice AI

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rule "results / KPI only carry measured numbers".

## Language x device coverage: what is measured, what is not

Only the cells marked **measured** below have end-to-end numbers. Every other
cell is deployable but unquantified — the components have on-device numbers,
the end-to-end combination does not.

| Device | Chinese | English | Other 28 languages |
|--------|---------|---------|--------------------|
| Orin Nano 8GB | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | pending measurement | pending measurement |
| Orin NX 16GB (cloud LLM) | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | pending measurement | pending measurement |
| Orin NX 16GB (fully local) | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | pending measurement | pending measurement |
| RK3576 | **measured 2026-09-06, re-verified 2026-09-08** (CER 1.05% short / 9.62% long, TTS RTF 0.172, V2V stop_to_final p50 1837ms) | **measured 2026-09-06** (WER 16.95% short / 63.38% long; offline-CER 1.11% short / 4.16% long, TTS RTF 0.194) | not supported |
| RK3588 | not measured | pending measurement | pending measurement |
| Raspberry Pi 5 | not supported | pending measurement | not supported |

Corrected 2026-09-08: this table previously read "Chinese: not measured" for
RK3576 while carrying the Chinese offline-ASR numbers (1.05%/9.62%) mislabeled
under the English column — both cells were actually measured on 2026-09-06
(`boundary.zh.yaml` / `boundary.en.yaml`), the English offline-ASR CER is
1.11%/4.16%, not 1.05%/9.62%. See `model-matrix/rk3576/boundary.zh.yaml`
("re-verified 2026-09-08" metrics) for the Chinese re-verification (same
corpus/methodology as 2026-09-06, run to confirm the numbers are still
current on this device) plus the new TTS RTF and V2V turn-latency numbers.

Measured accuracy sources:

- Qwen3-ASR 0.6B int4 on Orin NX: CER 0 on the golden set, streaming and
  offline, 2026-07-04.
- RK3576: `docs/perf/rk3576-matrix-20260906.md` (zh+en, 2026-09-06);
  `model-matrix/rk3576/boundary.zh.yaml` (zh re-verification, 2026-09-08).

## RK3576 streaming-vs-offline discrepancy (open follow-up)

The 1.05% / 9.62% figures come from the offline whole-clip `POST /asr`
endpoint — no VAD, no streaming.

The live conversational session behaves differently. Its low-latency turn
detection (silero VAD, 400 ms silence + 2.5 s minimum audio) finalizes on the
first natural pause, so a long sentence with a mid-utterance pause is answered
after its first clause. Against the full reference text that scores CER 84.06%
zh / WER 63.38% en. This is the streaming endpoint's turn-taking design, not a
recognition error.

Confirmed by re-test: relaxing the decoder's token budget and punctuation stop
(`ASR_MAX_NEW_TOKENS=256`, `ASR_FINAL_STOP_ON_PUNCT=0`) produced byte-identical
transcripts. The VAD endpoint, not the decoder, ends the turn early.

Open work: tune the VAD endpoint to tolerate a mid-utterance pause in
conversation. Not done.
