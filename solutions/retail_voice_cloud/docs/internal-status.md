# Internal status — Retail Voice Collection (Server Stack)

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rule "results / KPI only carry measured numbers".

## Rows removed from the results table

All five were "to be measured", pending runs on `cat-remote` (RK3576):

| Metric | Planned conditions |
|---|---|
| Transcription accuracy (WER) | Chinese and English, Common Voice CC0 subset plus authorised in-house recordings |
| Concurrent channels | 1 / 2 / 4 / 8 / 16 |
| Continuous capture duration | 1 / 10 / 60 / 240 min and 24 h |
| Speaker error rate | Depends on the voiceprint container, whose image is still pending a build |
| final → redacted → persisted latency (p50/p95/p99) | End of utterance to committed row |

## Build and coverage gaps

**The voiceprint container image has not been built.** The endpoint the
Server Stack + Mobile App preset publishes is served by that container, so the
preset cannot be completed end to end until the image exists. Until then
`speaker.identified` is always false and subject deletion has no voiceprint to
cascade to.

**No ASR image is pinned for the reRouter CM4 CPU path.** The frozen images are
arm64 only and the bundled ASR image is the RK3576 NPU build.

**Multi-collector-to-one-stack has not been verified.** The frozen compose is
one unit and each collector preset brings its own MySQL and MinIO.

**Capacity is unmeasured.** One or two concurrent channels is a working
assumption, not a measurement.

## Gallery change

`voice-web-recordings.png` was an admin-console screenshot in an empty state —
all counters zero, "No data" table. Replaced on 2026-09-07 with official
reComputer RK3576-30 product photography (SKU 100052518, family
`recomputer_rk3576`); source recorded in `gallery/ATTRIBUTION.md`.
