# Gallery attribution

| File | Source | License / notes |
|---|---|---|
| `login.png`, `app-preview.png`, `map-view.png`, `outdoor-map.png` | Re-shot 2026-09-06 after the `sensecraft-ui-kit` v0.1.2 restyle (`solution-indoor-positioning`, branch `feature/ui-kit`, sources kept at `docs/ui/*-after.png`). Playwright / chrome-headless-shell, 1280x800 viewport, admin session against the local backend seeded from `db/app.db`. | First-party. `outdoor-map.png` basemap tiles are © OpenStreetMap contributors (ODbL), <https://www.openstreetmap.org/copyright>. |
| `floorplan-registration.png` | Screenshot taken during the 2026-09-05 georeferencing run (`solution-indoor-positioning`, branch `feature/outdoor`, `evaluation/runs/2026-09-05-georef/raw/ui-04-registration-saved.png`). Headless Chrome, 1280x720 viewport. | First-party. The floor plan in the shot is a synthetic 1000x800 px test image, not a customer site. Basemap tiles are © OpenStreetMap contributors (ODbL), <https://www.openstreetmap.org/copyright>. |
| `architecture.png`, `cover.png`, `beacon.png`, `gateway.png`, `t1000.png`, `wiki-overview.jpg` | Carried over from the original package; Seeed first-party product/UI imagery. | First-party. |

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
