# Retail Voice — Local Transcription

## What it does

A reSpeaker XVF3800 microphone array feeds one 16 kHz mono stream into a small edge box in the store. The box runs speech recognition itself and writes one JSON file per finished sentence into a directory on its own disk. There is no cloud account, no upload, and no outbound connection needed after the images and models are in place.

## What you get

- **Closed loop on one device.** Capture, voice activity detection, transcription, punctuation and optional voiceprint matching all run in the same box. Pull the network cable and transcription keeps working.
- **Data stays where it was recorded.** Transcripts land in a directory you choose. Audio retention is a switch: keep the WAV segments, or write nothing but text.
- **Two hardware points.** reRouter CM4 for the cheapest CPU-only install; reComputer RK3576 when you want the NPU to carry speech recognition and leave the CPU free.
- **Speaker labels without a cloud identity service.** The speech service emits a 192-dim CAM++ embedding per utterance; matching against a local registry happens on the same device and can be turned off entirely.
- **Bounded footprint.** Container logs are capped in the compose files, models live in named volumes, and the transcript directory is the only thing that grows with use.

## Where it fits

- A single store or a pilot site where nobody wants recordings leaving the premises.
- Environments with no reliable uplink — a basement shop, a pop-up counter, a factory floor office.
- Procurement rules that forbid third-party voice processing, where a local text file is the only acceptable artefact.
- A staging step before any cloud analytics: prove the audio path and the recognition quality on site first.

## How well it works

This is not a certified transcription product and not a compliance control. It produces text of the quality shown below and nothing about that text is legally authoritative. Whether recording conversations in your store is lawful, and what notice you must give, is your responsibility.

Every number below was measured on the OpenVoiceStream speech service — the same component this solution deploys — under the stated conditions. Nothing here is interpolated from a similar board.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Offline transcription latency, RK3576 | 3.0 s of audio → ~780 ms warm (RTF 0.26) | reComputer RK3576 Dev Kit, Armbian bookworm, kernel 6.1.115-vendor-seeed-rk3576, 3.9 GB RAM; SenseVoice RKNN fp16 on the NPU; `POST /asr`, warm container | Existing measurement carried over from `smart_retail_voice_ai/assets/docker/docker-compose.rk3576.yml` header, 2026-08-24 |
| Memory, RK3576 | 1.71 GiB container RSS | Same run, with ASR + punctuation + speaker embedding all loaded | Same |
| Restart to healthy, RK3576 | ~25 s | Same board, model volumes already populated | Same |
| Package acceptance check, RK3576 (this deployment) | `POST /asr` on 5 short clips (3 zh + 2 en): all 5 returned `"backend":"rk:sensevoice_rknn"` and correct text; wall-clock p50 678 ms, p95 810 ms (n=5, includes HTTP overhead) | `cat-remote` RK3576 board, this package's exact `docker-compose.rk3576.yml` + `local_rk3576.yaml` deployed via SSH, `rk3576-sensevoice` profile, container RSS 1.716 GiB confirming the row above | Real-machine packaging verification, 2026-09-06 |
| End-of-speech to final result, RK3576 (this deployment) | eos→final p50 861 ms, p95 1027 ms (n=5, same 5 clips) | `/asr/stream?vad=none&punctuate=true&speaker_embedding=true`, 100 ms PCM chunks, latency measured from the client's own empty-frame EOF to the `asr_final`/`final` message — **this is the SenseVoice profile this solution actually deploys**, distinct from the Paraformer streaming numbers in the two rows below | Real-machine packaging verification, 2026-09-06 |
| Streaming accuracy, RK3576 | zh CER 9.4%, en WER 34.6% | `cat-remote` RK3576, `bench/perf/corpus` short set (5 zh + 5 en files), Paraformer hybrid RKNN encoder + RKNN decoder, `/asr/stream` realtime, 40/80/160/240/400 frame buckets — **a different profile from the SenseVoice one deployed here** | `openvoicestream/docs/perf/paraformer-rk3576-streaming-ab-20260608.md`, 2026-06-08 |
| End-of-speech to final result, RK3576 | 326 ms / 347 ms (zh / en mean) | Same run, `/asr/stream` with 500 ms prepare lead | Same |
| Voiceprint embedding, RK3576 | RTF 0.09–0.13 (1 s → 125 ms, 3 s → 255 ms, 5 s → 428 ms) | `cat-remote`, CAM++ via sherpa-onnx on the CPU, 2 threads; clustering over 10 speakers 1.45 ms | `openvoicestream/docs/specs/diarization-capability.md`, 2026-06-26 |
| Voiceprint embedding, CM4 class (A72) | RTF ≈0.10 (1 s → 114 ms, 3 s → 303 ms, 5 s → 508 ms), cold load 1.66 s | `seeed-pi`, Raspberry Pi 4 (Cortex-A72, 4 cores) — the same SoC generation as the CM4 in the reRouter; CAM++ via sherpa-onnx on the CPU | Same document, 2026-06-26 |
| **ASR accuracy and latency, CM4** | **not measured** | The `asr_zh_en` row for RPi4 / CM4 in the bench matrix is still `TBD`. The published expectation, "2–3× slower than RPi5", is an estimate, not a measurement | `openvoicestream/docs/perf-test-runbook.md` matrix row; `docs/performance-comparison.md` "Devices not yet measured" |

Two boundaries that are not performance numbers but decide whether a site will work at all:

- **Background noise at or below 70 dB**, i.e. the level of normal conversation. Above that the array's noise suppression stops separating the speaker from the room, and word error rises before any of the numbers above apply.
- **Speaker within about 3 m** of the array. This is the coverage the XVF3800 beamformer holds in a store; further out, transcription degrades regardless of the compute board.

## Output Interfaces

| Interface | Where | What it carries |
|---|---|---|
| Transcript files | `<output-dir>/cache/asr/<id>.json` on the device | One JSON per finalized utterance: text, timestamps, language, speaker label when voiceprint is on |
| Audio segments | `<output-dir>/voice/*.wav` | 16 kHz mono WAV, written only while file output is enabled |
| Streaming ASR | `ws://<device-ip>:8621/asr/stream` | PCM in, transcript + punctuation + 192-dim embedding out |
| Offline ASR | `POST http://<device-ip>:8621/asr` | Whole-file transcription; used by the acceptance check |
| Local web page | `http://<device-ip>:8090/` | Live transcript, microphone status, voiceprint registry |

Nothing in this table leaves the device. There is no upstream endpoint configured and no credential to configure.

## Deployment Comparison

**reRouter CM4 (CPU).** The cheapest way to put local transcription in a store. Paraformer streaming ASR on four Cortex-A72 cores, Chinese and English, no accelerator. Choose it when budget dominates and the site records one speaker area. Its ASR speed and accuracy have not been measured on this SoC — plan a pilot before committing a fleet.

**reComputer RK3576 (NPU).** SenseVoice runs on the 6 TOPS NPU, so the CPU stays free for punctuation, voiceprint embedding and the capture client at the same time. Measured offline RTF 0.26 with everything loaded in 1.71 GiB. Choose it when you want the numbers in the table above rather than an estimate, or when you intend to enable both punctuation and voiceprint.

Both presets deploy the same two containers and produce the same files in the same layout. Moving between them changes the image tag and the profile, not the output format.

## Usage Notes

- **The whole stack is a single point of failure.** One box, one microphone. If it is off, nothing is captured, and there is no server-side gap detection to tell you.
- **The transcript directory grows without bound.** Nothing rotates it. Decide a retention period and enforce it with a cron job or an operator routine before the deployment runs for months.
- **Audio retention is a deliberate choice.** Leaving WAV output on makes review possible and makes the deployment hold recordings of real people. Turn it off if text is enough.
- **Voiceprint matching is local and heuristic.** It clusters similar voices against a registry with a fixed threshold; it is not identity verification and should never be used as one.
- **Punctuation and voiceprint each load their own model.** On a 4 GB board, enabling both narrows the margin; the device inputs let you turn either off.
- **No cloud path is included.** If a store later needs multi-site dashboards, export, or hard deletion workflows, that is a different package — this one has no upstream to point at.
- **RK3576 packaging verification (2026-09-06) tested the SenseVoice recognizer and pipeline, not the reSpeaker XVF3800 mic capture path.** The check ran on a board without a physical XVF3800 attached, so all 5 acceptance clips went in as files (`POST /asr` and `/asr/stream`), not through a live microphone. Everything downstream of "PCM audio arrives at the speech service" is confirmed on real hardware; the array's beamforming/AEC and the client's ALSA capture were not exercised in this run.
- **The `voice-client:c4-local` image is still unpublished.** The RK3576 troubleshooting table names one device-local substitute tag found to work (`sensecraft-voice-client:ovs-20260901b`), but that tag is not on any registry — a fresh board still needs its own build or a copy of that tag.

## Licensing note

The speech service ships third-party models — SenseVoice and Paraformer for recognition, CT-Transformer for punctuation, CAM++ for speaker embedding, Silero VAD for endpointing. Each carries its own upstream licence, and commercial use is between you and those upstreams; this package neither grants nor extends any right to them. The models download at first start from the mirror selected during deployment.
