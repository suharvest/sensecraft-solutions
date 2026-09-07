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
