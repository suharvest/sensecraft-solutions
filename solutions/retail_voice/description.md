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

| What the store gets | Typical | Device |
|---|---|---|
| End of speech to the final text | **861 ms p50 / 1027 ms p95** | reComputer RK3576 |
| Chinese recognition error, streaming | **9.4% CER** | reComputer RK3576 |
| Data left behind after deleting one person's records | **0** across the database, the object store and local audio | Server Stack preset |
| Personal details caught by redaction | **0.98 precision / 0.95 recall** | Server Stack preset |
| Access refused without the right role | **Pass** — 401 without a credential, 403 for a role that is too low | Server Stack preset |

Conditions: the speech figures come from the `cat-remote` RK3576 board running
this package's exact local RK3576 compose file with the SenseVoice profile,
2026-09-06; the streaming accuracy figure is the Paraformer profile on the same
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

The CM4-class speech figures, concurrency, continuous-capture duration and the
XVF3800 capture path have not been measured on this package. Measure them on
your own site; one or two concurrent channels is a working assumption.

Full conditions, the gold-set composition and the per-run detail are in the
engineering wiki.

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
