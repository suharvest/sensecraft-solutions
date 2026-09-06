# Gallery attribution

## architecture.svg (cover image)

Drawn for this solution. Wordless apart from product and protocol names, which
are identical in English and Chinese, so one asset serves both guides.

It is a diagram, not a screenshot of a running system.

## offline-acceptance.svg

Drawn for this solution. Shows the offline acceptance scenario: the M2 gateway
running its built-in ChirpStack as the network server, the bridge and Home
Assistant on a local host, and no WAN link.

Same caveat: a diagram, not a screenshot.

## Pending: Home Assistant dashboard screenshot

**Both gallery images are placeholders for the screenshot that should lead this
page.** The local smoke run (2026-09-05) produced the entity set the dashboard
draws — 15 entities across 3 devices, verified through the Home Assistant REST
and WebSocket APIs — but it captured API responses and container logs only
(`evaluation/runs/2026-09-05-smoke/raw/`: `api_states_after_replay.json`,
`api_states_after_offline.json`, `ha_devices.json`, `notifications.json`,
`bridge_availability.log`, `docker_compose_ps.txt`). No screenshot was taken.

To replace these: run the stack, import
`assets/homeassistant/agri_env_dashboard.yaml`, and capture the overview view.
Any screenshot that goes on this page must come from a real run — a mock-up
would misrepresent what the dashboard shows. Until then the diagrams stand in.

## measurementId table — licence unconfirmed

`assets/config/measurements.yaml` maps SenseCAP `measurementId` values to Home
Assistant entity semantics. The `id -> physical quantity` half of that mapping
was read out of the SenseCAP decoder sources:

> https://github.com/Seeed-Solution/SenseCAP-Decoder
> commit `d0a234205fb9574dd03abd49561b60c243c0d1e3` (2026-04-09)

**That repository has no LICENSE file** and its README has no licensing section.
The only licence declaration anywhere in it is a third-party contributed file
header that reads `@license Unlicensed for internal use`
(`S2100/datacake/SenseCAP_S2100_Datacake_Decoder.js:1-8`). So the licence for
the decoder sources is **unconfirmed**.

What this package does about it:

- No decoder JavaScript is copied into this repository. Only the factual
  `id -> quantity` correspondence is used, with the decoder source file and
  line number cited on each entry in `assets/config/measurements.yaml`.
- The `device_class`, `unit_of_measurement` and `state_class` columns are not
  from the decoder at all — they were chosen against the Home Assistant sensor
  documentation.
- Presets 2 and 3 ask the operator to install the decoder into their own The
  Things Stack payload formatter or ChirpStack device-profile codec. The guide
  links the upstream repository rather than redistributing it.

**Open item:** distributing the decoder with a solution requires a licensing
decision from Seeed. Confirm it before this package ships the decoder itself
rather than linking to it.
