# Gallery attribution

## Gallery screenshots (added 2026-10-08)

Real browser screenshot of the slot editor served by a Jetson Orin Nano Super, 2026-10-08 ~05:08 UTC (edge-parking-vision commit 4d1d42c UI). Input is `slots-occ20-empty20-400s.mp4` (sha256 9d04f612d244a492efa8d525eceef86364c506c026003a4268db90dd19182917): a parking-lot still for 20 s, black for 20 s, repeating. The still (a surface lot with an "ID:001" overlay in the lower right) has no recorded source (需核实 before publishing: confirm dataset/licence or replace with first-party footage).

`cover-20261008.jpg` is a generated illustration, not a screenshot.

## Update 2026-10-09 (gallery v2)

`panel-slot-editor-20261008.jpg` was removed and replaced by `panel-occupancy-1-mixed-20261009.jpg`. The v2 all-free shot (dark phase of the test clip, no vehicles in frame) is not used.

- Content: browser screenshot (Playwright Chromium, 1440 px viewport, DPR 1, cropped to page content) of the app's `/slots/editor` page (editor + live status, no bay selected) on a Jetson Orin Nano Super, 2026-10-08 09:57 UTC, page code edge-parking-vision `e5f9dec` (shipped in `nrd-parking-{jetson,rk}:20261009`). Bays P01, P02, P04, P06 occupied (cover 0.42 / 0.42 / 0.39 / 0.32), P03 and P05 free; occupied 4, free 2.
- Bays P01–P06 were placed for this run with `PUT /config/slots`, the same request the editor's Save button sends.
- Input: the same clip as above, `slots-occ20-empty20-400s.mp4` (sha256 9d04f612…182917). The parking-lot still still has no recorded source (需核实: confirm the dataset/licence or replace with first-party footage).
- Processing for the gallery: PNG → JPEG quality 85, 1440 px wide, no other edits. Evidence: `acceptance-20261008/visuals/edge_parking_occupancy/v2/`.
