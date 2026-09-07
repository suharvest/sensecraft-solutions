## What This Reference Design Is

A reSpeaker XVF3800 microphone array feeds one 16 kHz mono stream into an edge
box in the store, and the box turns in-store speech into text. What happens to
that text is the choice this design puts in front of you: it can stay on the box
as a file, or it can go through a server stack that redacts personal data before
storage and can hard-delete a subject on request and prove it gone.

Both paths use the same capture hardware and the same speech service. They are
two presets of one design, not two products.

## Two ways to deploy it

**On-Device Transcription** — one box, one microphone, one directory of
transcripts. Capture, voice activity detection, transcription, punctuation and
optional voiceprint matching all run on the same board. No cloud account, no
upload, no database, and no outbound connection needed once images and models
are in place. Choose it for a single store or a pilot site where nobody wants
recordings leaving the premises, and where a local text file is an acceptable
artefact on its own.

**Server Stack** — one host runs the whole pipeline: an ASR endpoint, voiceprint,
a service that redacts before it stores, MySQL, MinIO and an admin console with
export and hard delete. Audio arrives from a mobile app you already ship, from a
mic array on an edge collector, or both. Choose it when someone will ask "delete
my data" and a status flag on a surviving row is not an acceptable answer, or
when several sites need one queryable record.

| | On-Device Transcription | Server Stack |
|---|---|---|
| Output | JSON files on the device | Redacted rows in MySQL, audio in MinIO, console on port 3000 |
| Capture | reSpeaker XVF3800 on the box | The same array, or your mobile app over the ASR endpoint |
| Redaction | None — the text is what was said | Typed placeholders before insert; the original is never written |
| Deletion | Whatever you script against the directory | `POST /api/v1/privacy/erase`, cascading three stores, with a residue count |
| Boards | reRouter CM4 (CPU) or reComputer RK3576 (NPU) | reComputer RK3576, or another arm64 Linux host |
| Deploy time | About 40 minutes | About 60 minutes |

The capture side is identical, so a site that starts on the local preset can move
to the stack later without changing the microphone, the board or the recognizer.

How audio reaches the server stack:

```
  mobile app (yours, outside this package)
        │  WebSocket, 16 kHz mono PCM
        ▼
  ASR endpoint  ws://<host>:8080/ws?token=<operator>
        │
        │            edge collector (reSpeaker XVF3800 + reRouter CM4 / RK3576)
        │            │  local capture, VAD, OpenVoiceStream transcription
        ▼            ▼
  transcription + voiceprint
        │  final text
        ▼
  voice-service ── PII redaction ──> MySQL (redacted text only)
        │                            MinIO (raw audio, retention-bound)
        ▼
  voice-web admin console ── query · export · hard delete
```

The mobile app is not in this package. It already exists on your side; what this
design gives it is an endpoint to point at, a token to present, and a documented
audio format.

## What you get

- **A closed loop on one device, if that is what you want.** On the local preset,
  pull the network cable and transcription keeps working. Transcripts land in a
  directory you choose; audio retention is a switch — keep the WAV segments, or
  write nothing but text.
- **Redaction before storage, not after.** On the stack preset, phone numbers, ID
  numbers, names and addresses are replaced with typed placeholders (`[[PHONE]]`,
  `[[NAME]]`) on the way into the database. The original text is never written —
  not encrypted, not written. Keyword matching runs on the redacted text, so the
  keyword table holds redacted text too.
- **Hard deletion with a residue count.** One call by subject, device or session
  removes the database rows, the objects in MinIO and the voiceprint, in that
  order — objects first, because deleting the row first loses the object path
  forever. What is left is a tombstone holding a SHA-256 of the subject, no
  original values.
- **A subject export.** Redacted transcripts as JSON plus an audio manifest, for
  answering access and portability requests. Machine-checkable, scoped, never
  "export everything".
- **An ASR endpoint you can hand to an app.** A WebSocket that takes raw PCM
  frames and answers with JSON — connection acknowledgement, voice-activity
  status, and a final transcript per utterance carrying the speaker fields.
- **Speaker labels without a cloud identity service.** The speech service emits a
  192-dim CAM++ embedding per utterance; matching against a local registry
  happens on the same device and can be turned off entirely.
- **Three-tier access on the stack.** viewer reads, operator ingests, admin
  deletes and exports. Devices get operator tokens; the admin token stays with
  operators. A route with no rule requires at least viewer, so a new endpoint
  fails closed.
- **A bounded, frozen footprint.** Container logs are capped in the compose
  files, models live in named volumes, every stack image is pinned by digest and
  there is no auto-updater. Cloud analytics is a separate profile that is off by
  default, because turning it on sends text off the box.

## Where it fits

- A single store or a pilot site where nobody wants recordings leaving the
  premises — the local preset, with no database to operate.
- Environments with no reliable uplink: a basement shop, a pop-up counter, a
  factory floor office.
- Procurement rules that forbid third-party voice processing, where a local text
  file is the only acceptable artefact.
- Retail floors where staff and customers talk and the store wants to know what
  was asked for, without keeping a record of who asked — the stack preset.
- Any deployment that has to answer "delete my data" with something other than a
  status flag in a row that still exists.
- Sites that already have a mobile app doing the capture and need the pipeline
  behind it.
- A staging step before any analytics: prove the audio path and the recognition
  quality on site first, then add the stack.

## How well it works

This is not a certified transcription product, not a compliance control and not a
compliance certification. It produces text of the quality shown below, and the
redaction, deletion and export behaviour is what the code does under test;
whether either satisfies a particular regulation is a decision for whoever
operates the deployment, and it must be re-checked on the real installation.
Whether recording conversations in your store is lawful, and what notice you must
give, is your responsibility.

### Recognition — measured on the speech service both presets deploy

Every number below was measured on the OpenVoiceStream speech service under the
stated conditions. Nothing here is interpolated from a similar board.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Offline transcription latency, RK3576 | 3.0 s of audio → ~780 ms warm (RTF 0.26) | reComputer RK3576 Dev Kit, Armbian bookworm, kernel 6.1.115-vendor-seeed-rk3576, 3.9 GB RAM; SenseVoice RKNN fp16 on the NPU; "POST /asr", warm container | Existing measurement carried over from "smart_retail_voice_ai/assets/docker/docker-compose.rk3576.yml" header, 2026-08-24 |
| Memory, RK3576 | 1.71 GiB container RSS | Same run, with ASR + punctuation + speaker embedding all loaded | Same |
| Restart to healthy, RK3576 | ~25 s | Same board, model volumes already populated | Same |
| Package acceptance check, RK3576 (this deployment) | "POST /asr" on 5 short clips (3 zh + 2 en): all 5 returned ""backend":"rk:sensevoice_rknn"" and correct text; wall-clock p50 678 ms, p95 810 ms (n=5, includes HTTP overhead) | reComputer RK3576, this package's exact "docker-compose.local-rk3576.yml" + "local_rk3576.yaml" deployed via SSH, "rk3576-sensevoice" profile, container RSS 1.716 GiB confirming the row above | Real-machine packaging verification, 2026-09-06 |
| End-of-speech to final result, RK3576 (this deployment) | eos→final p50 861 ms, p95 1027 ms (n=5, same 5 clips) | "/asr/stream?vad=none&punctuate=true&speaker_embedding=true", 100 ms PCM chunks, latency measured from the client's own empty-frame EOF to the "asr_final"/"final" message — **this is the SenseVoice profile this design actually deploys**, distinct from the Paraformer streaming numbers in the two rows below | Real-machine packaging verification, 2026-09-06 |
| Streaming accuracy, RK3576 | zh CER 9.4%, en WER 34.6% | reComputer RK3576, "bench/perf/corpus" short set (5 zh + 5 en files), Paraformer hybrid RKNN encoder + RKNN decoder, "/asr/stream" realtime, 40/80/160/240/400 frame buckets — **a different profile from the SenseVoice one deployed here** | "openvoicestream/docs/perf/paraformer-rk3576-streaming-ab-20260608.md", 2026-06-08 |
| End-of-speech to final result, RK3576 | 326 ms / 347 ms (zh / en mean) | Same run, "/asr/stream" with 500 ms prepare lead | Same |
| Voiceprint embedding, RK3576 | RTF 0.09–0.13 (1 s → 125 ms, 3 s → 255 ms, 5 s → 428 ms) | reComputer RK3576, CAM++ via sherpa-onnx on the CPU, 2 threads; clustering over 10 speakers 1.45 ms | "openvoicestream/docs/specs/diarization-capability.md", 2026-06-26 |
| Voiceprint embedding, CM4 class (A72) | RTF ≈0.10 (1 s → 114 ms, 3 s → 303 ms, 5 s → 508 ms), cold load 1.66 s | reRouter CM4 series (Cortex-A72, 4 cores); CAM++ via sherpa-onnx on the CPU | Same document, 2026-06-26 |

The RK3576 rows are reference values taken on the same RK3576 platform; they
will be updated after a re-test on the reComputer unit.

**Pilot the reRouter CM4 path before rolling it out.** The RK3576 numbers above
do not carry over to the CM4's Cortex-A72 cores; measure accuracy and latency on
one store first.

### Privacy pipeline — measured on the stack preset

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Deletion residue (database, object store, local audio) | 0 | Subject-scope deletion, checked against SHA-256 manifests taken before and after, across all three stores | C4 hardening, "delete_proof.sh" integration test on its own MySQL 8.0 + MinIO — not a field installation |
| Rows before / after deletion | 22 → 4 | The 4 remaining rows are the PII-free tombstone and audit entries; no row holds subject data | Same run as above |
| Deletion latency | 14 ms | Single subject, small seeded dataset, all services on one host | Same run as above; not a load figure |
| PII redaction precision | 0.98 | 114-sample gold set: Chinese and English, overlapping entities, deliberate false-positive traps | "tools/pii_eval.py" driving the same Go implementation the service uses |
| PII redaction recall | 0.95 | Same gold set. Two samples are known misses kept in the set on purpose to keep the gap visible | Same run |
| Auth enforcement | Pass | 401 without a credential, 403 for a role that is too low, per-route role matrix, legacy role-less token degraded to viewer | Unit tests in "internal/middleware" (asr-service) and "api/server/middleware" (voice-service) |

These figures come from the code's own test rig on a development machine, not
from a store. Deletion latency is not a throughput number, and redaction
precision is a score on a 114-sample set, not a guarantee that no personal data
survives.

### Site boundaries — both presets

Two boundaries that are not performance numbers but decide whether a site will
work at all:

- **Background noise at or below 70 dB**, i.e. the level of normal conversation.
  Above that the array's noise suppression stops separating the speaker from the
  room, and word error rises before any of the numbers above apply.
- **Speaker within about 3 m** of the array. This is the coverage the XVF3800
  beamformer holds in a store; further out, transcription degrades regardless of
  the compute board.

### Privacy statement — stack preset

What the pipeline does and does not protect.

- **Original transcripts are never stored.** The configuration option exists
  ("privacy.store_original_text") and defaults to false; turning it on would put
  original text in a store the deletion flow was not extended to cover.
- **Audio is not redacted.** Only text is. Raw audio is kept on the host for a
  retention window — 24 hours by default, shortenable at deploy time to 6 or 1 —
  and is covered by the deletion flow. The audio itself is not redacted: v1
  does no bleeping and no segment removal.
- **Exports carry the manifest, not the audio**, for the same reason.
- **Low-confidence entities are flagged, not masked.** Redaction masks above a
  0.85 confidence threshold and marks the rest for review, which is why recall
  is 0.95 and not higher. Counts land in "pii_masked_count" and
  "pii_review_count"; the matched spans do not, because storing them would put
  the location of the personal data back in the database.
- **Turning on the cloud-analytics profile sends text off the host.** The text
  is redacted, but "nothing leaves the premises" stops being true.

### Known limitations

- **Numbers spoken as a continuous string come back as Chinese numeral words.**
  The ASR does not apply inverse text normalization to an isolated digit run,
  even with "recognition.use_inverse_text_normalization" on: "13812345678"
  spoken in one breath transcribes as "幺三八幺二三四五六七八", not as Arabic
  digits. Every phone-number regex in the redactor matches Arabic digits, so
  before this was handled such a line was stored with the number in the clear
  and "pii_masked_count: 0".
  A dedicated rule ("cn_mobile_spoken") now masks the 11-character Chinese
  numeral mobile-number pattern, including the 幺 reading used when people read
  a number out. **What is still not covered:** ID card numbers, landline
  numbers and any other numeric identifier read out as Chinese numeral words.
  If those matter for the deployment, verify with your own recordings before
  relying on redaction, and treat the raw audio retention window as the control
  that actually bounds the exposure.
- **The redaction score in the table is a text-level score.** It is measured on
  written text, not on ASR output. Transcription errors move entity boundaries
  and can drop a match that the same rule would catch in clean text.

## Output Interfaces

**On-Device Transcription**

| Interface | Where | What it carries |
|---|---|---|
| Transcript files | "<output-dir>/cache/asr/<id>.json" on the device | One JSON per finalized utterance: text, timestamps, language, speaker label when voiceprint is on |
| Audio segments | "<output-dir>/voice/*.wav" | 16 kHz mono WAV, written only while file output is enabled |
| Streaming ASR | "ws://<device-ip>:8621/asr/stream" | PCM in, transcript + punctuation + 192-dim embedding out |
| Offline ASR | "POST http://<device-ip>:8621/asr" | Whole-file transcription; used by the acceptance check |
| Local web page | "http://<device-ip>:8090/" | Live transcript, microphone status, voiceprint registry |

Nothing in this table leaves the device. There is no upstream endpoint configured
and no credential to configure.

**Server Stack**

| Interface | Port | Path | Content |
|---|---|---|---|
| WebSocket | 8080 | "/ws?token=<operator>" | Client sends raw PCM binary frames (16 kHz, mono, signed 16-bit little-endian, ≤ 2 MiB per message). Server sends JSON: "connection" on connect, "vad" on speech/silence transitions, "final" per utterance, "error" on failure. |
| HTTP | 8081 | "/api/v1/recordings" | Transcript ingest (operator) and query (viewer). Text is redacted before insert. |
| HTTP | 8081 | "/api/v1/privacy/erase" | Hard delete by subject / device / session, cascading MySQL, MinIO and the voiceprint. Admin only. |
| HTTP | 8081 | "/api/v1/privacy/export" | Subject export: redacted transcripts plus audio manifest. Admin only. |
| HTTP | 3000 | "/" | Admin console — recordings, keywords, devices, export and delete. |
| HTTP | 8621 | "/health" | OpenVoiceStream health, used by the orchestration probe. |

## Usage Notes

### Both presets

- **The capture side is a single point of failure.** One box, one microphone. If
  it is off, nothing is captured.
- **Voiceprint matching is local and heuristic.** It clusters similar voices
  against a registry with a fixed threshold; it is not identity verification and
  should never be used as one.
- **Punctuation and voiceprint each load their own model.** On a 4 GB board,
  enabling both narrows the margin; the device inputs let you turn either off.
- **The RK3576 packaging verification (2026-09-06) tested the SenseVoice
  recognizer and pipeline, not the reSpeaker XVF3800 mic capture path.** The
  check ran on a board without a physical XVF3800 attached, so all 5 acceptance
  clips went in as files ("POST /asr" and "/asr/stream"), not through a live
  microphone. Everything downstream of "PCM audio arrives at the speech service"
  is confirmed on real hardware; the array's beamforming/AEC and the client's
  ALSA capture were not exercised in this run.

### On-Device Transcription

- **The transcript directory grows without bound.** Nothing rotates it. Decide a
  retention period and enforce it with a cron job or an operator routine before
  the deployment runs for months.
- **Audio retention is a deliberate choice.** Leaving WAV output on makes review
  possible and makes the deployment hold recordings of real people. Turn it off
  if text is enough.
- **There is no server-side gap detection.** If the box is off, nothing tells
  you.
- **The "voice-client:c4-local" image is still unpublished.** The RK3576
  troubleshooting table names one device-local substitute tag found to work
  ("sensecraft-voice-client:ovs-20260901b"), but that tag is not on any registry
  — a fresh board still needs its own build or a copy of that tag.

### Server Stack

- **Size a site from your own pilot.** Treat one or two concurrent channels as
  the working assumption and measure on your own installation before scaling.
- **The stack host is arm64.** The frozen images are arm64 only and the bundled
  ASR image is the RK3576 NPU build. Another host class needs a matching ASR
  image, which you supply.
- **Speaker identification is off by default.** The container that provides it
  is not started, so "speaker.identified" stays false and subject deletion has
  no voiceprint to cascade to.
- **The token is in the URL.** Browser WebSocket clients cannot set headers, so
  the ASR endpoint accepts "?token=". On anything but a trusted LAN, terminate
  TLS in front of it.
- **A console account is viewer by default.** Promote it with the role API using
  an admin credential; until then, use the admin API token.
- **One deployment, one database.** An edge collector brings its own MySQL and
  MinIO because the frozen compose is one unit; pointing several collectors at
  one shared stack changes the reporting address, so re-test that layout.
- **The delete-proof script does not run against your deployment.** It stands up
  its own MySQL and MinIO to prove the deletion path, which is what makes it
  reproducible — and also what makes it evidence about the code, not about your
  site's data.

## Licensing note

The speech service ships third-party models — SenseVoice and Paraformer for
recognition, CT-Transformer for punctuation, CAM++ for speaker embedding, Silero
VAD for endpointing. Each carries its own upstream licence, and commercial use is
between you and those upstreams; this package neither grants nor extends any
right to them. The models download at first start from the mirror selected during
deployment.

The stack services are Seeed's own ("sensecraft-asr-service",
"sensecraft-voice-client", "sensecraft-voice-service", "sensecraft-voice-web").
MySQL and MinIO are pulled as upstream images under their own licences — MySQL
under GPLv2 with the FOSS exception, and MinIO's current releases under AGPLv3,
which is worth reading before the object store is embedded in a commercial
product. Redaction uses no third-party model: the name and address word lists are
the public-domain Hundred Family Surnames and the list of provincial-level
divisions.
