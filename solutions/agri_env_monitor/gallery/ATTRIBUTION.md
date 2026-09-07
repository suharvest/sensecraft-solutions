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

## 2026-09-07 real local run — screenshots replace the placeholders above

Ran the actual `agri-env-monitor` stack (upstream project at
`~/project/agri-env-monitor`, not yet merged into this package) on the local
Mac: `docker compose -p agri-env up -d --build` from `deploy/docker-compose.yml`
brings up `agri-env-homeassistant` (`ghcr.io/home-assistant/home-assistant:stable`,
pinned digest per that repo's compose comment), `agri-env-mosquitto`
(`eclipse-mosquitto:2.0.20`) and `agri-env-bridge` (local build,
`agri-env-bridge:0.1.0`) on ports 18123/18883 (8123/1883 were already used by
other local containers). HA onboarding was reset (removed
`.storage/{auth,auth_provider.homeassistant,onboarding,http.auth}` inside the
container's `ha-config` volume, since the account created during the
2026-09-05 smoke run had no recorded password) and redone fresh with a new
admin account; MQTT integration was added by hand through the UI after the
scripted `tools/ha_bootstrap.py` MQTT flow step failed (`Invalid flow
specified`) — onboarding/user/core_config/integration steps all completed
via the script, only the MQTT config-entry flow needed the manual fallback.
Data is `tools/replay.py --source all` publishing the repo's own
`tests/fixtures/{sensecap_cloud_uplink,ttn_uplink,chirpstack_uplink}.json`
messages over MQTT to the bridge — the same fixture used in the
2026-09-05 smoke run, not synthetic invented values. The bridge decodes them
into HA MQTT-discovery sensors under `sensor.sensecap_<eui>_<measurement>`.

A "农业环境监测" dashboard was created in this HA instance from
`assets/homeassistant/agri_env_dashboard.yaml` (raw YAML config editor,
pasted verbatim) — three views: 总览 (overview cards), 趋势 (history-graph
cards), 告警 (automation list). `assets/homeassistant/automations.yaml` was
installed via `docker cp` into `/config/automations.yaml` and reloaded through
the automation reload API, giving the four threshold automations
(`agri_env_soil_moisture_low/recovered`, `agri_env_air_temperature_high/
recovered`) real entities to render.

- `ha-overview-local-20260907.jpg` — 总览 tab after a fresh `replay.py --source
  all` run: real decoded values for all three fixture devices (SenseCAP
  `2CF7F1C0000000AA/BB/CC`) — air temp/humidity/CO2, soil temp/moisture/EC,
  hourly rainfall, and per-device battery. Not a mock-up; every number came
  through the bridge from the MQTT payload the fixture defines. macOS host:
  Apple M4 (arm64), Docker Desktop 28.0.4.
- `ha-history-graph-local-20260907.jpg` — 趋势 tab, `history-graph` cards for
  air temp/humidity (24h), soil (24h) and rainfall (7d), captured right after
  a replay so the legend shows live current values (38.5 °C / 59.9% / 612 ppm
  etc.) rather than "不可用". The graph lines themselves are flat/short because
  this is a single replay burst, not a real multi-hour deployment — the
  legend values are the evidence, not the sparkline shape.
  技术页 wiki 缺图预留位可直接复用这张替换后续真实长时段曲线。
- `ha-alert-triggered-local-20260907.jpg` — HA notification panel (bell icon)
  showing "空气温度过高: SenseCAP 2CF7F1C0000000AA Temperature 当前 38.5°C，
  高于阈值 35°C" — the `agri_env_air_temperature_high` automation actually
  fired because the fixture's replayed AA temperature value (38.5 °C, the same
  value documented in the 2026-09-05 smoke run's manual boundary test) is
  above the 35 °C threshold configured in `automations.yaml`. This is a real
  automation trigger, not a staged notification.
- `agri-env-refresh-local-20260907.gif` — two frames captured via
  `claude-in-chrome`'s `gif_creator`: before frame shows all five 总览 cards
  as "不可用" (bridge's `BRIDGE_UNAVAILABLE_AFTER=60` watchdog had marked the
  fixture devices offline since the previous replay), after frame — taken
  ~2s after a fresh `tools/replay.py --source all` call — shows the same
  cards populated with live values. Demonstrates the bridge→MQTT→HA discovery
  pipeline actually refreshing state, not a scripted animation.

All four files are real software output from a locally-run stack; no image
was hand-drawn or mocked. Source data is the repo's `tests/fixtures/*.json`
MQTT payload fixtures (three synthetic-but-fixed demo device EUIs — the same
convention as the 2026-09-05 smoke run, not live sensors). Licence: none of
these HA UI screenshots contain third-party dataset content; HA and Mosquitto
are Apache-2.0 / EPL, screenshotted as running software, not redistributed.
