## What This Reference Design Is

In-store conversations are captured by a reSpeaker microphone, turned into text and stored in the retail voice backend, where they can be queried, exported and deleted. Both presets share the same capture hardware and speech service, and both require the retail voice backend.

## Two ways to deploy it

**Client Transcription and Upload**: the edge device transcribes locally, caches while offline, and uploads text to the backend when connected.

**Server Transcription with Clip + Phone**: reSpeaker Clip recordings go through SenseCraft Voice App to the platform ASR; the backend redacts and stores them.

| | On-Device Transcription | Server Stack |
|---|---|---|
| Capture | reSpeaker XVF3800 on the box | The same array, or Clip + phone app |
| Deletion | Your own cleanup of the directory | One call removes database rows, stored audio and voiceprint |
| Boards | CM4, RK3576, RK3588, J3011, J4012 or R2000 (CPU/Hailo) | Same supported ASR hosts, with Clip + phone capture |
| Deploy time | About 40 minutes | About 60 minutes |

The capture side is identical, so moving from the local preset to the stack keeps the microphone and the board.

## What you get

- **No lost records during outages**: the device keeps transcribing when the backend is unreachable and uploads when it returns.
- **Redaction before storage**: phone numbers, ID numbers, names and addresses become placeholders such as `[[PHONE]]` and `[[NAME]]`; the original text is never written.
- **Hard deletion per person**: one call by subject, device or session removes database rows, audio and voiceprint, and returns a residue count.
- **Subject export**: redacted transcripts plus an audio manifest for access and portability requests.
- **An ASR endpoint for your app**: a WebSocket that takes PCM and returns a transcript per utterance with speaker fields.
- **Three-tier access**: viewer reads, operator ingests, admin deletes and exports.

## Where it fits

- A single store or pilot site where recordings stay on the edge device and only text is uploaded.
- Intermittent uplink: a basement shop, a pop-up counter, a factory floor office.
- Stores that want to know what customers asked without keeping who asked (Server Stack preset).
- Deployments that must answer deletion requests with real deletion.
- Sites that already have a mobile app doing capture and need the pipeline behind it.

## Measured results

| Metric | Result |
|---|---|
| End of speech to final text | **861 ms p50 / 1027 ms p95** (reComputer RK3576) |
| Chinese streaming recognition error | **9.4% CER** (reComputer RK3576) |
| Data left after deleting one person's records | **0** across database, object store and local audio |
| Personal details caught by redaction | **0.98 precision / 0.95 recall** |
| Access refused without the right role | **Pass**: 401 without a credential, 403 for a role too low |

Speech figures were measured on an RK3576 board with audio fed as files; the redaction score is on a 114-sample Chinese and English written-text set; the figures apply with steady background noise **at or below 70 dB** and the speaker **within about 3 m** of the array.

### ASR concurrency reference

Recommended channels is the highest tested concurrency whose final-text p95 stayed at or below 1.5 s.

| Device | Recognizer | Recommended simultaneous channels | p50 / p95 |
|---|---|---:|---:|
| reComputer J4012 | SenseVoice (zh) | **48** | 505 / 789 ms |
| reComputer J3011 | SenseVoice (zh) | **32** | 167 / 293 ms |
| reComputer RK3576 | SenseVoice (zh) | **12** | 583 / 1067 ms |
| reComputer RK3588 | SenseVoice (zh) | **8** | 659 / 902 ms |
| reComputer R2000 | SenseVoice (zh) | **6** | 625 / 1173 ms |
| reComputer J4012 | Whisper base (en) | **16** | 584 / 1177 ms |
| reComputer J3011 | Whisper base (en) | **8** | 492 / 837 ms |
| reComputer RK3576 | Whisper base (en) | **2** | 809 / 1380 ms |
| reComputer RK3588 | Whisper base (en) | **4** | 655 / 1380 ms |
| reComputer R2000 | Whisper base (en) | **16** | 752 / 1465 ms |

English WER: J3011 **7.62%**, J4012 **7.62%**, RK3588 **7.50%**, RK3576 **8.51%**, R2000 **8.39%**; unified Chinese CER across five devices **4.82%**. Details in `docs/asr-concurrency.md`.

## Output Interfaces

| Interface | Content |
|---|---|
| Device `ws://<device-ip>:8621/asr/stream` | Streaming transcription: PCM in, text + punctuation + voiceprint embedding out |
| Device `http://<device-ip>:8090/` | Local web page: live transcript, microphone status, voiceprint registry |
| Server WebSocket 8080 `/ws?token=<operator>` | App uploads PCM, receives a transcript per utterance |
| Server HTTP 8081 `/api/v1/recordings` | Transcript ingest and query |
| Server HTTP 8081 `/api/v1/privacy/erase`, `/api/v1/privacy/export` | Delete / export by subject (admin only) |
| Server HTTP 3000 `/` | Admin console |

## Usage Notes

- Whether recording in your store is lawful, and what notice you must give, is the operator's responsibility; this is not a compliance certification.
- Voiceprint matching is local similarity clustering, not identity verification.
- On a 4 GB board, enabling both punctuation and voiceprint narrows memory margin; each can be turned off.
- The on-device transcript directory is not rotated; set a retention period and clean it up.
- Enabling audio file output keeps recordings of real people on the device; turn it off if text is enough.
- The `voice-client:c4-local` image is unpublished; a fresh board needs its own build.
- Server stack images are arm64 only; another host class needs a matching ASR image.
- The ASR endpoint token is in the URL; terminate TLS in front of it outside a trusted LAN.
- Console accounts are viewer by default; promote with the role API using an admin credential.
- Speaker identification is off by default, so subject deletion has no voiceprint to remove.
- Start a site at one or two concurrent channels and measure before scaling.

## Replaces the Smart Retail Voice Collection package

`smart_retail_voice_ai` was merged into this design on 2026-09-08: its deployment is the **On-Device Transcription** preset, and its hosted console is replaced by the **Server Stack** preset. The old id does not redirect here, so old links return 404; existing installs keep working until redeployed.

## Licensing note

The speech service ships third-party models (SenseVoice, Paraformer, CT-Transformer, CAM++, Silero VAD) under their upstream licences; confirm commercial use with those upstreams. The sensecraft stack services are Seeed's own; MySQL is GPLv2 with the FOSS exception and current MinIO releases are AGPLv3. Redaction word lists are the public-domain Hundred Family Surnames and the list of provincial-level divisions.
