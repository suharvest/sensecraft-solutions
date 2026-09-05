# Retail Voice Collection (Server Stack)

## What it does

Audio comes in, redacted transcripts come out, and everything that came in can
be deleted on request and proven gone.

The package is the server side of that sentence. It deploys one frozen Docker
stack — speech recognition, voiceprint, a service that redacts and stores, a
MySQL database, a MinIO object store and an admin console — and publishes an ASR
endpoint for audio to arrive on.

Audio reaches it two ways:

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
package gives it is an endpoint to point at, a token to present, and a documented
audio format.

## What you get

- **An ASR endpoint you can hand to an app.** A WebSocket that takes raw PCM
  frames and answers with JSON — connection acknowledgement, voice-activity
  status, and a final transcript per utterance carrying the speaker fields.
- **Redaction before storage, not after.** Phone numbers, ID numbers, names and
  addresses are replaced with typed placeholders (`[[PHONE]]`, `[[NAME]]`) on
  the way into the database. The original text is never written — not encrypted,
  not written. Keyword matching runs on the redacted text, so the keyword table
  holds redacted text too.
- **Hard deletion with a residue count.** One call by subject, device or session
  removes the database rows, the objects in MinIO and the voiceprint, in that
  order — objects first, because deleting the row first loses the object path
  forever. What is left is a tombstone holding a SHA-256 of the subject, no
  original values.
- **A subject export.** Redacted transcripts as JSON plus an audio manifest, for
  answering access and portability requests. Machine-checkable, scoped, never
  "export everything".
- **Three-tier access.** viewer reads, operator ingests, admin deletes and
  exports. Devices get operator tokens; the admin token stays with operators.
  A route with no rule requires at least viewer, so a new endpoint fails closed.
- **A frozen stack.** Every image pinned by digest, no auto-updater. Cloud
  analytics is a separate profile that is off by default, because turning it on
  sends text off the box.

## Where it fits

- Retail floors where staff and customers talk and the store wants to know what
  was asked for, without keeping a record of who asked.
- Any deployment that has to answer "delete my data" with something other than a
  status flag in a row that still exists.
- Sites that already have a mobile app doing the capture and need the pipeline
  behind it.
- Pilots where the audio must stay on the premises: the default configuration
  sends nothing off the host.

## How well it works

**This is not a compliance certification.** The redaction, deletion and export
behaviour below is what the code does under test; whether that satisfies a
particular regulation is a decision for whoever operates the deployment, and it
must be re-checked on the real installation.

| Metric | Value | Conditions | Source |
|---|---|---|---|
| Deletion residue (database, object store, local audio) | 0 | Subject-scope deletion, checked against SHA-256 manifests taken before and after, across all three stores | C4 hardening, `delete_proof.sh` integration test on its own MySQL 8.0 + MinIO — not a field installation |
| Rows before / after deletion | 22 → 4 | The 4 remaining rows are the PII-free tombstone and audit entries; no row holds subject data | Same run as above |
| Deletion latency | 14 ms | Single subject, small seeded dataset, all services on one host | Same run as above; not a load figure |
| PII redaction precision | 0.98 | 114-sample gold set: Chinese and English, overlapping entities, deliberate false-positive traps | `tools/pii_eval.py` driving the same Go implementation the service uses |
| PII redaction recall | 0.95 | Same gold set. Two samples are known misses kept in the set on purpose to keep the gap visible | Same run |
| Auth enforcement | Pass | 401 without a credential, 403 for a role that is too low, per-route role matrix, legacy role-less token degraded to viewer | Unit tests in `internal/middleware` (asr-service) and `api/server/middleware` (voice-service) |
| Transcription accuracy (WER) | To be measured | Chinese and English, Common Voice CC0 subset plus authorised in-house recordings | Pending on cat-remote (RK3576) |
| Concurrent channels | To be measured | 1 / 2 / 4 / 8 / 16 | Pending on cat-remote |
| Continuous capture duration | To be measured | 1 / 10 / 60 / 240 min and 24 h | Pending on cat-remote |
| Speaker error rate | To be measured | Depends on the voiceprint container, whose image is still pending a build | Pending |
| final → redacted → persisted latency (p50/p95/p99) | To be measured | End of utterance to committed row | Pending on cat-remote |

The measured rows come from the hardening work on the code, on a developer
machine. Nothing in the table is a figure from a store. Do not quote the
deletion latency as throughput, and do not quote redaction precision as a
guarantee that no personal data survives — it is a score on a 114-sample set.

### Privacy statement

Read this before writing any customer-facing copy about the deployment.

- **Original transcripts are never stored.** The configuration option exists
  (`privacy.store_original_text`) and defaults to false; turning it on would put
  original text in a store the deletion flow was not extended to cover.
- **Audio is not redacted.** Only text is. Raw audio is kept on the host for a
  retention window — 24 hours by default, shortenable at deploy time to 6 or 1 —
  and is covered by the deletion flow. The page must never claim "the audio is
  redacted", because it is not: v1 does no bleeping or segment removal.
- **Exports carry the manifest, not the audio**, for the same reason.
- **Low-confidence entities are flagged, not masked.** Redaction masks above a
  0.85 confidence threshold and marks the rest for review, which is why recall
  is 0.95 and not higher. Counts land in `pii_masked_count` and
  `pii_review_count`; the matched spans do not, because storing them would put
  the location of the personal data back in the database.
- **Turning on the cloud-analytics profile sends text off the host.** The text
  is redacted, but "nothing leaves the premises" stops being true.

### Known limitations

- **Numbers spoken as a continuous string come back as Chinese numeral words.**
  The ASR does not apply inverse text normalization to an isolated digit run,
  even with `recognition.use_inverse_text_normalization` on: "13812345678"
  spoken in one breath transcribes as "幺三八幺二三四五六七八", not as Arabic
  digits. Every phone-number regex in the redactor matches Arabic digits, so
  before this was handled such a line was stored with the number in the clear
  and `pii_masked_count: 0`.
  A dedicated rule (`cn_mobile_spoken`) now masks the 11-character Chinese
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

| Interface | Port | Path | Content |
|---|---|---|---|
| WebSocket | 8080 | `/ws?token=<operator>` | Client sends raw PCM binary frames (16 kHz, mono, signed 16-bit little-endian, ≤ 2 MiB per message). Server sends JSON: `connection` on connect, `vad` on speech/silence transitions, `final` per utterance, `error` on failure. |
| HTTP | 8081 | `/api/v1/recordings` | Transcript ingest (operator) and query (viewer). Text is redacted before insert. |
| HTTP | 8081 | `/api/v1/privacy/erase` | Hard delete by subject / device / session, cascading MySQL, MinIO and the voiceprint. Admin only. |
| HTTP | 8081 | `/api/v1/privacy/export` | Subject export: redacted transcripts plus audio manifest. Admin only. |
| HTTP | 3000 | `/` | Admin console — recordings, keywords, devices, export and delete. |
| HTTP | 8621 | `/health` | OpenVoiceStream health, used by the orchestration probe. |

## Deployment Comparison

**Server Stack + Mobile App** — one host runs everything and the capture is
somebody else's problem: your app records and uploads. Choose it when the app
already exists and the store has no dedicated microphone hardware. The endpoint
this preset publishes is served by the voiceprint container, whose image is
still pending a build, so this preset cannot be completed end to end until that
image exists.

**Server Stack + Edge Collector** — a mic array on an edge box captures and
transcribes locally through OpenVoiceStream, then reports into the same stack.
Choose it for fixed positions — a counter, a service desk — and when nobody is
holding a phone. It does not depend on the voiceprint image. On RK3576 the ASR
runs on the NPU; on reRouter CM4 it runs on the CPU and this package pins no
image for that path, so you have to supply one.

## Usage Notes

- **Capacity is unmeasured.** Treat one or two concurrent channels as the
  working assumption until the boundary runs on cat-remote are done. Do not size
  a site from this page.
- **The stack host is arm64.** The frozen images are arm64 only and the bundled
  ASR image is the RK3576 NPU build. Another host class needs a matching ASR
  image, which this package has not verified.
- **Speaker identification is off.** The container that provides it is not
  started by default; until its image is built, `speaker.identified` is always
  false and subject deletion has no voiceprint to cascade to.
- **The token is in the URL.** Browser WebSocket clients cannot set headers, so
  the ASR endpoint accepts `?token=`. On anything but a trusted LAN, terminate
  TLS in front of it.
- **A console account is viewer by default,** and there is no API to promote it.
  Deleting and exporting from the console needs an admin-role account, which is
  set in the `users` table directly. Until then, use the admin API token.
- **One deployment, one database.** The collector presets bring their own MySQL
  and MinIO because the frozen compose is one unit; pointing several collectors
  at one shared stack changes the reporting address and is not verified here.
- **The delete-proof script does not run against your deployment.** It stands up
  its own MySQL and MinIO to prove the deletion path, which is what makes it
  reproducible — and also what makes it evidence about the code, not about your
  site's data.

## Licensing note

The services in this stack are Seeed's own (`sensecraft-asr-service`,
`sensecraft-voice-client`, `sensecraft-voice-service`, `sensecraft-voice-web`)
plus OpenVoiceStream for recognition. MySQL and MinIO are pulled as upstream
images under their own licences — MySQL under GPLv2 with the FOSS exception, and
MinIO's current releases under AGPLv3, which is worth reading before the object
store is embedded in a commercial product. Redaction uses no third-party model:
the name and address word lists are the public-domain Hundred Family Surnames
and the list of provincial-level divisions.
