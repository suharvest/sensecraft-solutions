# Internal status — Retail Voice

Internal record. Not published on the deployment page. The rows below were
removed from `description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rules "results / KPI only carry measured numbers"
and "pages use Seeed product names".

The on-device and server-stack packages were merged into this one on
2026-09-07; this file merges both internal records.

## Bench hardware mapping

| Bench host | Page name |
|---|---|
| fleet `cat-remote` (RK3576 board) | reComputer RK3576 |
| fleet `seeed-pi` (Raspberry Pi 4, Cortex-A72, 4 cores) | Raspberry Pi 4 as a stand-in for the reRouter CM4 — same SoC generation |

## Rows removed from the results table — local_transcribe preset

**ASR accuracy and latency, CM4 — not measured.** The `asr_zh_en` row for
RPi4 / CM4 in the bench matrix is still `TBD`. The published expectation,
"2-3x slower than RPi5", is an estimate, not a measurement. Sources:
`openvoicestream/docs/perf-test-runbook.md` matrix row;
`docs/performance-comparison.md` "Devices not yet measured".

The page now says to pilot one store on the CM4 path before rolling out, which
carries the same buying advice without publishing the gap.

## Rows removed from the results table — cloud_stack preset

All five were "to be measured", pending runs on `cat-remote` (RK3576):

| Metric | Planned conditions |
|---|---|
| Transcription accuracy (WER) | Chinese and English, Common Voice CC0 subset plus authorised in-house recordings |
| Concurrent channels | 1 / 2 / 4 / 8 / 16 |
| Continuous capture duration | 1 / 10 / 60 / 240 min and 24 h |
| Speaker error rate | Depends on the voiceprint container, whose image is still pending a build |
| final → redacted → persisted latency (p50/p95/p99) | End of utterance to committed row |

## Build and coverage gaps

**The voiceprint container image has not been built.** The ASR endpoint the
`cloud_stack` preset publishes for a mobile app is served by that container, so
that capture path cannot be completed end to end until the image exists. Until
then `speaker.identified` is always false and subject deletion has no voiceprint
to cascade to.

**No ASR image is pinned for the reRouter CM4 CPU path** on the `cloud_stack`
preset. The frozen images are arm64 only and the bundled ASR image is the
RK3576 NPU build.

**Multi-collector-to-one-stack has not been verified.** The frozen compose is
one unit and each collector deployment brings its own MySQL and MinIO.

**Capacity is unmeasured.** One or two concurrent channels is a working
assumption, not a measurement.

**The `voice-client:c4-local` image is unpublished** on the `local_transcribe`
preset. `sensecraft-voice-client:ovs-20260901b` was confirmed to work as a
drop-in on `cat-remote` (2026-09-06) but is not on any registry.

**The 2026-09-06 RK3576 packaging verification did not exercise the microphone
path.** No physical XVF3800 was attached; all 5 acceptance clips went in as
files. Everything downstream of "PCM arrives at the speech service" is
confirmed on real hardware; the array's beamforming/AEC and the client's ALSA
capture were not.

## Gallery changes

`voice-web-recordings.png` was an admin-console screenshot in an empty state —
all counters zero, "No data" table. Replaced on 2026-09-07 with official
reComputer RK3576-30 product photography (SKU 100052518, family
`recomputer_rk3576`); source recorded in `gallery/ATTRIBUTION.md`.

On 2026-09-07 the cover became `architecture.png` — despite the name, a
flat-lay photograph of the actual kit — under the rule that a cover shows a real
object rather than a rendered scene. `cover.webp`, the in-store counter scene,
does not read as a photograph at full size and is no longer referenced by
`intro.cover_image` or `intro.gallery`; the file stays in the directory.

Still missing from the gallery: a photograph of the kit installed at a counter,
and a console screenshot showing real transcripts.

## 2026-09-08 — smart_retail_voice_ai retired into this package

`solutions/smart_retail_voice_ai/` was deleted and its id added to
`solutions/.deprecated.json`. The gallery, the reRouter firmware step and the
capture hardware had already been carried over on 2026-09-07 when this package
was created. This pass moved the rest and recorded what was deliberately not
moved.

Carried over in this pass:

| From the old package | Where it landed |
|---|---|
| `links.wiki` (en/zh) and `links.purchase` | `intro.links` in `solution.yaml` |
| `chmod -R 666 /dev/snd/*` deploy step | `devices/local_rerouter.yaml`, `remote_overrides.actions.before` |
| The reRouter reboot note — corrected: the old package recommended a reboot, the `chmod` does not need one, and it is not persistent across one | `guide.md` / `guide_zh.md`, Step 2, reRouter target |
| Troubleshooting rows: page not loading right after reboot, record button unresponsive while models load | `guide.md` / `guide_zh.md`, Step 3 |
| `tags: rerouter, npu` | `intro.tags` |

Deliberately not carried over:

- **`deployment.post_deployment.autostart`** (kiosk browser to
  `http://localhost:8090` on every boot). `PostDeployment` is a solution-level
  field with no per-preset form (`spec/solution.schema.json`), and the two
  presets here serve different ports — 8090 on the store box, 3000 for the
  stack console — so one global URL would be wrong for one of them. In the old
  package it was also inert on its own default target: autostart writes a
  `~/.config/autostart/*.desktop` entry and is skipped on headless hosts, and
  the reRouter runs OpenWrt with no desktop session. Both local targets still
  open the client page at deploy time through the device-level
  `post_deployment.open_browser` / `url`.
- **`watchtower`.** The old compose ran it to pull new images automatically. A
  store box must not silently swap its own image; this was already recorded in
  the header of `assets/docker/docker-compose.local-cm4.yml`.
- **The reSpeaker USB control-transfer step** (pyusb `ctrl_transfer` calls run
  inside `sensecraft-voice-client:v0.4`). It is not carried over because the
  step runs inside an image this package does not pull. **Open item, not a
  closed decision:** the calls include `AUDIO_MGR_OP_R 8 0`, which selects
  which channel the array sends over USB, so it sits on the capture path and
  not only on playback. Nobody has checked on this hardware whether the
  XVF3800's factory channel selection is already what the capture client
  wants. If a deployment records silence or the wrong channel while `arecord
  -l` shows the array, this is the first thing to re-test.
- **The local (on-your-own-computer) deploy target** the old package offered
  for the same step, "deploy voice services on your local computer" with the
  array plugged into that computer's USB. Both of the images the
  `local_transcribe` preset deploys are `linux/arm64` only, and so were the
  old package's — `docker manifest inspect --verbose` on 2026-09-08 returns
  `arm64` for `sensecraft-asr-server:v0.1`,
  `sensecraft-voice-client:v0.4` and `seeed-local-voice:rpi-20260721`. On top
  of that the capture container bind-mounts `/dev/snd`, which the Docker
  Desktop Linux VM on macOS and Windows does not expose, so the laptop-plus-
  USB-microphone path the old guide described could not have captured audio
  there. The supported route to the same result is the SSH target to the arm64
  board. A `type=local` target for an operator whose own machine *is* the
  store box (what `cloud_stack` offers as `stack_local`) has not been added
  here because it has not been tried on either board.
- **The hosted console at `test-voice-web.seeed.cn`** and the guide sections
  that documented it (dashboard, AI analysis, store/user management, keyword
  and prompt settings). The `cloud_stack` preset replaces it with a console you
  host yourself. What that console does not yet cover, relative to the hosted
  one: cross-store aggregation and the LLM analysis view.
- **The old package's published image line** (`sensecraft-asr-server:v0.1` +
  `sensecraft-voice-client:v0.4` + the 460 MB `models.zip`). Those tags exist
  in the registry, and the `local_transcribe` preset's `voice-client:c4-local`
  tag still does not (see "Build and coverage gaps" above). Deleting the old
  package removes the only path in this repository built entirely from
  published images — the gap is in the image build, not in the page.
