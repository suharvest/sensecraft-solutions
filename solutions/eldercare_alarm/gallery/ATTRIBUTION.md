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

## What is deliberately absent

No screenshot of the confirmation UI and no clip of a real alarm. Any such
asset would show a real or dataset-derived person, and the only footage
available for it today is GMDCSA-24 material carried by the upstream
`fall_detection` solution — reusing it here would need the same face-obscuring
and MIT attribution treatment. Capture first-party footage on a commissioned
site before adding one.
