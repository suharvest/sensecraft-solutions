# Gallery attribution

Three of the four photography images (`cover.webp`, `architecture.png`,
`rerouter.png`, `respeaker.jpg`) are reused, unmodified, from
`solutions/smart_retail_voice_ai/gallery/` in this repository. They were
produced for that solution, which shares the capture hardware (reSpeaker
XVF3800 on reRouter CM4 / reComputer RK3576) with this package's
edge-collector preset. No third-party material is involved and no licence
other than this repository's applies.

## cover.webp, architecture.png

Product photography of the capture hardware combination. First-party Seeed
material.

## rerouter.png, respeaker.jpg

Product photography of reRouter CM4 and reSpeaker XVF3800. First-party Seeed
material.

## voice-web-recordings.png

Screenshot of `sensecraft-voice-web`'s admin console (dashboard/recordings
view), captured 2026-09-06 from the `feature/ui-kit` branch after migrating
the app onto `@sensecraft/ui-kit` (shared theme tokens, `AppShell`, i18n).
Replaces the earlier `edge-client-asr.png`, which was a screenshot of a
different, now-superseded client from `solutions/smart_retail_voice_ai`.

Two things to keep straight when reading it:

- **It shows an empty/no-backend state.** The screenshot was taken against a
  dev server with no backend running (`No data`, stat cards all `0`), purely
  to show the shared layout, the four-state status tags and zh/en i18n
  coverage — not a real dataset. It is not evidence of redaction behavior or
  of measured accuracy/latency/throughput; those live in the measured-boundary
  table in `description.md`, and most of that table is still marked as
  pending.
- **The container image this solution deploys has not been rebuilt from the
  `feature/ui-kit` branch yet.** The screenshot reflects the frontend source,
  not necessarily what `assets/docker/*.yml` currently pulls — treat the
  admin console image tag as **pending rebuild** until `sensecraft-voice-web`
  publishes a release from that branch.

## recomputer-rk3576.jpg

Official product photography for reComputer RK3576-30 (SKU 100052518, family
`recomputer_rk3576`), downloaded 2026-09-07 from the Seeed media CDN:
<https://media-cdn.seeedstudio.com/media/catalog/product/cache/961a49e1875f8c1f40e5990d74e68365/2/-/2-rk3576.jpg>
(product page <https://www.seeedstudio.com/reComputer-RK3576-30-p-6815.html>).
First-party Seeed material.

It replaced `voice-web-recordings.png`, an admin-console screenshot that showed
an empty dataset (all counters zero, "No data" table).
