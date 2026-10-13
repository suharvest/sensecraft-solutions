# Gallery attribution

## Gallery screenshots (added 2026-10-08)

Real browser screenshots of the app's `/preview` page served by a Jetson Orin Nano Super, 2026-10-08 05:07 UTC (edge-parking-vision commit 4d1d42c UI). Input is `count-synthetic-120s.mp4` (sha256 3003d5958c6863f3504c5b8510015c7135cebbfd35d4bfe1eaca5601f0e726fd): one vehicle crop moving over a flat gray background, not field video. The vehicle crop is cut from a parking-lot still whose original source is not recorded (需核实 before publishing: confirm dataset/licence or replace with first-party footage). The box comes from `/preview.json` and the frame from `/preview.jpg` (separate 1 s samples), so the box can lag the frame.

`cover-20261008.jpg` is a generated illustration, not a screenshot.

## Update 2026-10-09 (gallery v2)

`panel-preview-counting-{1,2}-20261008.jpg` were removed and replaced by `panel-counting-1-before-20261009.jpg` and `panel-counting-2-after-20261009.jpg`.

- Content: browser screenshots (Playwright Chromium, 1440 px viewport, DPR 1, cropped to page content) of the app's own `/preview` page on a Jetson Orin Nano Super, 2026-10-08 09:40 UTC, page code edge-parking-vision `d38901c` (the same page ships in `nrd-parking-{jetson,rk}:20261009`, built from `e5f9dec`). The two shots are 3 s apart and show the same vehicle (track #48) before and after crossing the line; box and frame come from the same frame.
- Input: the same synthetic clip as above, `count-synthetic-120s.mp4` (sha256 3003d595…726fd): one vehicle crop moving left→right and back every 12 s over a flat gray background. Captions say "synthetic test clip, one vehicle". The vehicle crop's original source is still not recorded (需核实: confirm the dataset/licence or replace with first-party footage).
- Processing for the gallery: PNG → JPEG quality 85, 1440 px wide, no other edits. Evidence: `acceptance-20261008/visuals/edge_parking_counting/v2/`.
