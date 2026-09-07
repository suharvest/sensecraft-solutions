# Gallery attribution

| File | Source | License / notes |
|---|---|---|
| `login.png`, `app-preview.png`, `map-view.png`, `outdoor-map.png` | Re-shot 2026-09-06 after the `sensecraft-ui-kit` v0.1.2 restyle (`solution-indoor-positioning`, branch `feature/ui-kit`, sources kept at `docs/ui/*-after.png`). Playwright / chrome-headless-shell, 1280x800 viewport, admin session against the local backend seeded from `db/app.db`. | First-party. `outdoor-map.png` basemap tiles are © OpenStreetMap contributors (ODbL), <https://www.openstreetmap.org/copyright>. |
| `floorplan-registration.png` | Screenshot taken during the 2026-09-05 georeferencing run (`solution-indoor-positioning`, branch `feature/outdoor`, `evaluation/runs/2026-09-05-georef/raw/ui-04-registration-saved.png`). Headless Chrome, 1280x720 viewport. | First-party. The floor plan in the shot is a synthetic 1000x800 px test image, not a customer site. Basemap tiles are © OpenStreetMap contributors (ODbL), <https://www.openstreetmap.org/copyright>. |
| `cover.png` | Copy of `map-view.png` — the live map view, re-shot 2026-09-06 after the `sensecraft-ui-kit` v0.1.2 restyle. Set as the cover on 2026-09-07 so the card shows the product, not the architecture diagram. | First-party. Basemap tiles are © OpenStreetMap contributors (ODbL), <https://www.openstreetmap.org/copyright>. |
| `architecture.png`, `beacon.png`, `gateway.png`, `t1000.png`, `wiki-overview.jpg` | Carried over from the original package; Seeed first-party product/UI imagery. | First-party. |

## Desensitisation

The georeferencing screenshots contain no real site data: the map ("Georef Demo",
50 m x 40 m) and the uploaded floor plan were created for the evaluation run and
deleted afterwards. The device EUIs visible anywhere in this package are the
synthetic ones used by the replay traces.

## CDN

TODO: these screenshots are still referenced as repo-relative paths. Before
the hub landing page picks them up they have to be uploaded to
`https://files.seeedstudio.com/Solution/landpage_asset/indoor_positioning_ble_lorawan/`
with the usual `<name>-<hash>.png` filename, and `solution.yaml` switched to the
CDN URLs. Not done in this change.

## 2026-09-07

Gallery reordered: the floor-plan registration view leads, the remaining
console screenshots follow, the architecture diagram is last. `login.png` was
cropped from 1280 × 800 to 1270 × 723 and `floorplan-registration.png` from
1280 × 720 to 1280 × 718 to drop empty canvas; the other screenshots were
already filled to their edges and are byte-identical to before.

`cover.png`, `beacon.png`, `t1000.png`, `gateway.png` and `wiki-overview.jpg`
stay in this directory but are not referenced by `intro.gallery`: the first is a
duplicate of `map-view.png`, the next three are product photographs on a white
background, and the last is a stitched montage of the wiki page.

## Missing: a photograph of the hardware on site

There is no picture of a beacon on a wall, a tracker on a trolley or a gateway
in a corridor. All six published images are console screenshots. A site
photograph is what this page's cover should be and has to be supplied.

## 2026-09-07 (second pass) — DPR 2 panel captures, replacing `login.png`/`app-preview.png`/`map-view.png`/`outdoor-map.png`

PR #101 (`gallery/panel-screenshots-dpr2`) could not re-shoot this solution
because the console's admin password lives in
`solution-indoor-positioning/server/config/json/server_runtime_config.json`
(not `db/app.db` — that SQLite file only holds `devices_list` /
`device_groups` / `geofences` / `user_sessions`, no credential table) and
locating it was out of scope for that pass. This pass ran the stack and used
that config-file password (not recorded here or in any commit) to log in as
`admin`; `guest` login also works for read-only views since
`POST /api/login` and `GET /api/auth/check` both auto-issue a `guest` session
when no token is presented (`server/main.py`), but the beacon/config screens
need `admin`.

**Stack**: `docker compose up -d` from
`~/project/solution-indoor-positioning/docker-compose.yml`
(`seeedcloud/sensecraft-indoor-positioning:latest`, ports 5173/8022, `./db`
and `./server/config/json` bind-mounted). The mounted
`server/config/json/dashboard_config.json` already had 5 maps / 49 beacons
registered from prior work, but `./uploads` (the floor-plan background image
volume) was empty, so all 5 backgrounds 404'd. Copied the repo's own
synthetic 1000x800 test image
(`evaluation/runs/2026-09-05-georef/raw/georef_floorplan.png` — same one
`floorplan-registration.png` already uses, not a customer floor plan) to all
5 expected filenames (`10_5_Floor.png`, `10_Floor.png`,
`9_Floor__A_Area.png`, `9_Floor__B_Area.png`, `111_818408.png`) so every map
renders instead of showing a broken image. `db/devices_list` had 2 real
tracker rows already (`2CF7F1C0530004AD`, `2CF7F1C052800001`, no beacon or
group data). To get a live position: started a local
`eclipse-mosquitto:2` broker on 1883, pointed
`server_runtime_config.json.chirpStackMqtt` at it
(`host.docker.internal:1883`, `sensecapOpenStream.enabled=false` so no real
device traffic mixes in) and ran the repo's own
`evaluation/replay_chirpstack.py --trace
evaluation/traces/mixed_indoor_outdoor.jsonl --loop 3 --speed 20` — a GNSS/BLE
trace the repo ships for its own capacity/latency evaluation, not synthetic
data invented for this screenshot. `server_runtime_config.json` was restored
from a backup after the run.

**Method**: Playwright, `channel="chrome"`, 1600x1000 viewport,
`device_scale_factor=2` (3200x2000 capture), JPEG quality 90. Language
switched via `localStorage.setItem('app-locale', 'zh'|'en')` (the app's own
`vue-i18n` key, same mechanism as its `LanguageSwitcher.vue`) before each
capture, not two separate deployments.

| File | What it shows | Size |
|---|---|---|
| `map-panel-zh-20260907.jpg` | Map Dashboard, zh, "10 Floor" map selected (17 beacons, the busiest of the 5) — beacon dots plotted inside two labelled room outlines, header counters 5 maps / 49 beacons / 2 trackers, WebSocket connected | 3200x2000 |
| `map-panel-en-20260907.jpg` | Same view after switching the language selector to English, no page reload | 3200x2000 |
| `beacon-list-zh-20260907.jpg` | Configuration → 信标 (Beacons) tab for the "10 Floor" map: a 17-row table with each beacon's real UUID, major/minor, X/Y, TxPower and MAC, edit/delete actions per row | 3200x2000 |
| `beacon-list-en-20260907.jpg` | Same table in English. Note: the "Beacon List & Management" heading and helper text under this tab are hard-coded English strings in the frontend — they render in English even when the zh capture's `app-locale` is `zh`. Not fixed here (out of scope), left as-is. | 3200x2000 |

No cropping was needed: at this viewport both pages already fill top-to-bottom
with real UI (nav bar to table/map-preview edge); there is no dead browser
chrome or empty canvas margin to trim. `cover_image` now points at
`map-panel-zh-20260907.jpg` so the card shows the floor plan with its beacon
markers rather than the architecture diagram.

**What's real, what's not**: the beacon layout (49 beacons across 5 maps),
their UUID/major/minor/MAC values, and the floor dimensions are genuine
config-file content carried over from earlier work on this package — not
invented for this screenshot. The floor-plan *image* itself (grid + two
coloured room outlines) is the repo's synthetic georeferencing test asset,
reused across all 5 maps because the real per-floor background PNGs are not
in this checkout. The tracker `2CF7F1C0530004AD` position shown in the header
counters came from a real replay of the repo's own evaluation trace over a
local MQTT broker — it did not land on the "10 Floor" indoor map (the trace
carries WGS84 lon/lat, so it surfaces on the outdoor OSM view instead, not
captured this pass), which is why the Map Dashboard panel here still reads
"trackers (0)" for that specific floor.

## Not done this pass

- No outdoor/OSM tracker view was captured (the replayed trace's live dot
  renders there, not on the indoor floor plan — see above).
- `login.png` sign-in screen was not re-shot; not requested this pass.
- CDN upload (see "## CDN" above) is still outstanding for every image in
  this gallery, old and new.
