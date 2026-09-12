## What This Reference Design Is

A reSpeaker XVF3800 microphone array feeds one 16 kHz mono stream into an edge
box in the store. Both presets require the retail voice backend: the client
transcription path transcribes on the device and uploads text, while the server
transcription path sends Clip recordings through the phone and gateway to the
platform ASR before storage.

Both paths use the same capture hardware and the same speech service. They are
two presets of one design, not two products.

## Two ways to deploy it

**Client Transcription and Upload** — the required retail backend runs its
database, object store, service and console. The selected edge device captures
and transcribes locally, keeps an offline cache, and uploads finalized text to
that backend. Audio can remain on the device according to its retention policy;
the backend connection is required for the retail record.

**Server Transcription with Clip + Phone** — the required retail backend runs
MySQL, MinIO, voice-service, the console and capture gateway. Clip recordings
go through SenseCraft Voice App to the platform ASR, then the backend redacts
and stores the resulting record.

| | On-Device Transcription | Server Stack |
|---|---|---|
| Output | Backend records plus an offline JSON cache | Redacted rows in MySQL, audio in MinIO, console on port 3000 |
| Capture | reSpeaker XVF3800 on the box | The same array, or your mobile app over the ASR endpoint |
| Redaction | Backend redaction before insert | Typed placeholders before insert; the original is never written |
| Deletion | Whatever you script against the directory | `POST /api/v1/privacy/erase`, cascading three stores, with a residue count |
| Boards | CM4, RK3576, RK3588, J3011, J4012 or R2000 (CPU/Hailo) | Same supported ASR hosts, with Clip + phone capture |
| Deploy time | About 40 minutes | About 60 minutes |

The capture side is identical, so a site that starts on the local preset can move
to the stack later without changing the microphone, the board or the recognizer.

How audio reaches the server stack:

```
  reSpeaker Clip → SenseCraft Voice App
        │  multipart audio upload
        ▼
  capture gateway → OpenVoiceStream ASR
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

- **A local transcription path with an offline cache.** The device keeps working
  through a temporary backend outage and retries finalized text when connected.
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

- A single store or a pilot site where recordings should remain on the edge
  device while finalized text is sent to the required retail backend.
- Environments with intermittent uplink: a basement shop, a pop-up counter, a
  factory floor office. The device cache retains records for retry.
- Procurement rules that require the ASR audio path to stay on the edge device;
  the backend receives finalized text for the retail record.
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

| What the store gets | Typical | Device |
|---|---|---|
| End of speech to the final text | **861 ms p50 / 1027 ms p95** | reComputer RK3576 |
| Chinese recognition error, streaming | **9.4% CER** | reComputer RK3576 |
| Data left behind after deleting one person's records | **0** across the database, the object store and local audio | Server Stack preset |
| Personal details caught by redaction | **0.98 precision / 0.95 recall** | Server Stack preset |
| Access refused without the right role | **Pass** — 401 without a credential, 403 for a role that is too low | Server Stack preset |

Conditions: the speech figures come from the `cat-remote` RK3576 board running
the local RK3576 compose file with the SenseVoice profile, 2026-09-06, on
image `seeed-local-voice:rk-20260803b`. That compose now defaults to
`rk-20260909`, which has not been benchmarked with this package; the streaming accuracy figure is the Paraformer profile on the same
board, 2026-06-08. The privacy figures come from an integration run on its own
MySQL 8.0 and MinIO, with SHA-256 manifests compared before and after in all
three stores, on a developer machine rather than a store. The redaction score is
a 114-sample gold set in Chinese and English.

Two caveats that survive the numbers: the redaction score is a **text-level**
score measured on written text, not on transcription output — recognition errors
move entity boundaries; and the deletion proof stands up **its own** stores,
which is what makes it reproducible and also what makes it evidence about the
code rather than about your site's data.

Two boundaries that are not performance numbers but decide whether a site works
at all: **steady background noise at or below 70 dB**, and the **speaker within
about 3 m** of the array. Above or beyond those, word error rises before any
number in this table applies.

Measure the CM4-class speech figures, concurrency, continuous-capture duration
and the XVF3800 capture path on your own site; one or two concurrent channels is
a working starting point.

Full conditions, the gold-set composition and the per-run detail are in the
engineering wiki.

### ASR concurrency reference

The following is a capacity reference for choosing an edge board. “Recommended”
is the highest tested concurrency whose final-text p95 stayed at or below 1.5 s;
latency is measured from audio end to the `is_final` message. These are benchmark
results from the OpenVoiceStream main-branch harness, with non-ASR containers
stopped on idle boards. They are not a claim that the currently bundled solution
images already contain the benchmarked voxedge, profile, or model revisions.

| Device family | Recognizer | Recommended simultaneous channels | p50 / p95 at recommendation | Boundary observed |
|---|---|---:|---:|---|
| reComputer J4012 | SenseVoice (zh) | 48 | 505 / 789 ms | c=48 was the highest tested level; no error |
| reComputer J3011 | SenseVoice (zh) | 32 | 167 / 293 ms | c=48 → 768 / 2932 ms |
| reComputer RK3576 | SenseVoice (zh) | 12 | 583 / 1067 ms | c=12 was the highest valid tested level |
| reComputer RK3588 | SenseVoice (zh) | 8 | 659 / 902 ms | c=12 had 15 client errors |
| reComputer R2000 | SenseVoice (zh) | 6 | 625 / 1173 ms | idle-board c=8 repeats: 1265–1556 ms |
| reComputer J4012 | Whisper base (en) | 16 | 584 / 1177 ms | c=24 → 893 / 2195 ms |
| reComputer J3011 | Whisper base (en) | 8 | 492 / 837 ms | c=16 → 884 / 1710 ms |
| reComputer RK3576 | Whisper base (en) | 2 | 809 / 1380 ms | c=4 → 880 / 1681 ms |
| reComputer RK3588 | Whisper base (en) | 4 | 655 / 1380 ms | c=8 → 886 / 2083 ms |
| reComputer R2000 | Whisper base (en) | 16 | 752 / 1465 ms | c=16 was the highest tested level; 0 errors |

Accuracy was evaluated separately on the same 100-item, ≤4 s English corpus:
J3011 7.62% WER, J4012 7.62%, RK3588 7.50%, RK3576 8.51% and R2000 8.39%.
The unified Chinese comparison used the same 100-item AISHELL-1 subset across
five devices and had aggregate CER 4.82%. The RK 172-frame run is a separate
windowed-decode result (aggregate CER 4.74%), so it is not the unified figure.
The English concurrency
figures used 72 LibriSpeech test-clean items on Jetson/RK and 100 items (≤4 s)
on R2000. The full matrices, source revisions and image/profile prerequisites
are recorded in `docs/asr-concurrency.md`.

## Output Interfaces

**On-Device Transcription**

| Interface | Where | What it carries |
|---|---|---|
| Transcript files | "<output-dir>/cache/asr/<id>.json" on the device | One JSON per finalized utterance: text, timestamps, language, speaker label when voiceprint is on |
| Audio segments | "<output-dir>/voice/*.wav" | 16 kHz mono WAV, written only while file output is enabled |
| Streaming ASR | "ws://<device-ip>:8621/asr/stream" | PCM in, transcript + punctuation + 192-dim embedding out |
| Offline ASR | "POST http://<device-ip>:8621/asr" | Whole-file transcription; used by the acceptance check |
| Local web page | "http://<device-ip>:8090/" | Live transcript, microphone status, voiceprint registry |

The cache is local, but finalized records are uploaded to the required retail
backend. Configure its origin and operator key in the device deployment.

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

## Replaces the Smart Retail Voice Collection package

`smart_retail_voice_ai` covered the same topic with the same capture hardware —
a reRouter CM4 and a reSpeaker XVF3800 — and reported to a hosted console. It
was merged into this design on 2026-09-08 and its directory deleted. Its
deployment is the **On-Device Transcription** preset here, extended with the
reComputer RK3576 NPU path; its reporting path is superseded by the **Server
Stack** preset, which runs the console, the database and the object store on a
host you own instead of on `test-voice-web.seeed.cn`.

The old id is **not** an alias for this one. `replaces:` in `solution.yaml` is
not a field the spec defines — it is absent from `spec/solution.schema.json` and
from every model in `packages/`, so it is silently dropped on load and resolves
nothing. The id is listed in `solutions/.deprecated.json`, which the manifest
generator copies into the manifest's `deprecated` array; that marks it retired,
it does not redirect it.

So anything still holding `smart_retail_voice_ai` — a bookmark, a link, a pinned
deployment reference — gets a 404 from the moment the directory is deleted until
whoever consumes the manifest is pointed at `retail_voice`. There is no
migration path between the two packages: an existing install keeps working until
it is redeployed.

## Scope of the Numbers

- **reComputer RK3576 figures** — taken on the exact compose file this package ships. The 5 acceptance clips were fed as files: the board had no physical array attached, so the array's beamforming and AEC and the client's ALSA capture are not in these numbers.
- **CM4 ASR speed and accuracy** — the upstream bench matrix row for RPi4 / CM4 (`asr_zh_en`, `openvoicestream/docs/perf-test-runbook.md`) is the reference; run the first CM4 site as a pilot.
- **The PII score** — text-level, taken on written text with `tools/pii_eval.py` driving the same Go implementation the service uses, not on ASR output.

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
