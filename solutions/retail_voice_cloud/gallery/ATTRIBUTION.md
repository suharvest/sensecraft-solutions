# Gallery attribution

All four images are reused, unmodified, from `solutions/smart_retail_voice_ai/gallery/`
in this repository. They were produced for that solution, which shares the
capture hardware (reSpeaker XVF3800 on reRouter CM4 / reComputer RK3576) with
this package's edge-collector preset. No third-party material is involved and no
licence other than this repository's applies.

## cover.webp, architecture.png

Product photography of the capture hardware combination. First-party Seeed
material.

## rerouter.png, respeaker.jpg

Product photography of reRouter CM4 and reSpeaker XVF3800. First-party Seeed
material.

## edge-client-asr.png

A screenshot of the transcript view from the earlier solution's client.

Two things to keep straight when reading it:

- **It predates this package's redaction step.** The text in the screenshot is
  whatever that client displayed at the time; it is not evidence that redaction
  ran. This package's caption describes what the current pipeline stores
  (redacted text only), and the screenshot is included to show the shape of the
  view, not the content of a redacted record.
- **It shows no measured figures.** Nothing in it should be quoted as accuracy,
  latency or throughput evidence — those live in the measured-boundary table in
  `description.md`, and most of that table is still marked as pending.

Replace this image with a screenshot taken from a deployment of this package
once one exists; at that point the caption can describe real redacted output
instead of the view's layout.
