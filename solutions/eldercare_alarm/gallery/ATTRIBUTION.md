# Gallery attribution

Both files in this directory are **local references**, not CDN URLs.
`solution.yaml` points at `gallery/<file>.svg` relative paths so the package
validates and previews offline.

## CDN upload — pending

Nothing here has been uploaded yet. Before this solution goes live on the
landing page, each asset has to move to
`https://files.seeedstudio.com/Solution/landpage_asset/eldercare-alarm/<name>-<hash>.svg`
and the `intro.cover_image` / `intro.gallery[].src` values in `solution.yaml`
have to be rewritten to those URLs. Until that happens the paths below are the
source of truth.

| File | Target CDN path | Status |
|---|---|---|
| `eldercare-alarm-architecture.svg` | `.../eldercare-alarm/architecture-<hash>.svg` | not uploaded |
| `eldercare-alarm-state-machine.svg` | `.../eldercare-alarm/state-machine-<hash>.svg` | not uploaded |
| `eldercare-alarm-console-zh.png` | `.../eldercare-alarm/console-zh-<hash>.png` | not uploaded |
| `eldercare-alarm-console-en.png` | `.../eldercare-alarm/console-en-<hash>.png` | not uploaded (referenced from ATTRIBUTION only, not yet in solution.yaml gallery) |

## eldercare-alarm-architecture.svg

Drawn for this solution from the event flow in the upstream project's README
(`eldercare-alarm/README.md`, section 1). It is a schematic, not a screenshot —
no camera footage, no person, no dataset material, so no third-party licence
applies and there is nothing to de-identify. Wordless except for field and
component names that are identical in both languages, so one file serves the
English and the Chinese page.

## eldercare-alarm-state-machine.svg

Drawn for this solution from the transitions implemented in
`eldercare/statemachine`, with the default windows from
`eldercare-alarm/config.example.yaml` (`evidence_sec: 5.0`,
`confirm_window_sec: 60.0`, `notify_deadline_sec: 5.0`,
`retry_interval_sec: 30.0`). Same situation as above: schematic only.

## eldercare-alarm-console-zh.png / eldercare-alarm-console-en.png

Screenshots of the rebuilt confirmation UI (`eldercare-alarm/eldercare/web/ui`,
a React + antd app on `@sensecraft/ui-kit`; see
`seeed-solutions-hub/docs/reports/ui-consistency-audit-2026-09-06.md` §4 for
the migration this replaced the old single-page HTML with). Taken with
Playwright at 1280×800 against `uv run python -m eldercare` fed by
`evaluation/replay/replayer.py --scenario fall` (synthetic bbox/track data,
no camera, no dataset frames, no real or simulated person imagery) — so unlike
the fall-detection solution's GMDCSA-24 clips, there is no face to obscure and
no third-party licence to carry. Only `eldercare-alarm-console-zh.png` is
wired into `solution.yaml`'s gallery today; the English capture sits here for
whoever adds an English-locale gallery slot later.

## What is deliberately absent

No clip of a real alarm end to end (detector → alarm → notification) on live
camera footage. That would show a real or dataset-derived person, and the
only footage available for it today is GMDCSA-24 material carried by the
upstream `fall_detection` solution — reusing it here would need the same
face-obscuring and MIT attribution treatment. Capture first-party footage on
a commissioned site before adding one.
