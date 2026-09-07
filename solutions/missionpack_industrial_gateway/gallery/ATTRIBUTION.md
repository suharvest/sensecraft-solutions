# Gallery attribution

Source project: `Seeed-Solution/Solution_HVAC_SmartControl` (GitHub), pulled to
Mac at `~/project/Solution_HVAC_SmartControl`; the console app identifies
itself in its own UI as "MissionPack Edge Control" / "MissionPack 边缘控制"
(`frontend/console`, React + antd on `@sensecraft/ui-kit`, and a legacy Vue
shell under `frontend/src`). This is the same codebase that backs the
`smart_hvac_control` solution's prediction-plugin layer; this gallery covers
the underlying multi-protocol gateway (OPC UA / Modbus TCP+RTU / BACnet/IP /
MQTT) core, not the KNN prediction feature.

Files created 2026-08-18 (per directory mtimes); confirmed on this local
review 2026-09-07.

## cover.png

A real screenshot of the **Access** page (`Configure industrial
protocol sources and stage discovered devices`), taken against a running
instance of the console. The one configured source shown, `HVAC OPC UA 模拟站`
(source ID `opcua-hvac-main`, protocol `opcua`, state `enabled`/`Online`,
timestamp 8/18/2026), is connected to the project's **built-in OPC UA
simulator** rather than a real field controller — the repo carries a
dedicated protocol-simulator lane (commit history includes "set default to
simulated and add password for direct mode", "add the Eastron SDM630 V2 point
template and simulator device profile"), which the gateway supports as a
first-class, documented mode for demos and testing without hardware. The
display name and source ID are operator-entered free text, not hardcoded
fixture strings, so they do not appear via grep in the source tree — that is
expected of a real running instance, not evidence the strings are made up.

`cover.png` is a tighter crop of that page with no top app-bar chrome. It is
not a mock-up or a hand-drawn illustration. It is kept only as the `demo.mp4`
thumbnail; the page cover moved to the console overview below.

## demo.mp4

26.4-second screen recording (H.264/MP4, 502 KB), same console instance and
capture date as the screenshots above. Not independently frame-verified
beyond confirming it is a real video container (not a placeholder file); it
is used as the gallery video with `cover.png` as its thumbnail per
`solution.yaml`.

## architecture.svg

Drawn for this solution to illustrate the OPC UA / Modbus TCP+RTU / BACnet/IP
/ MQTT → unified point model → MQTT data service flow described in
`guide.md`/`guide_zh.md` §"Connection architecture". Schematic only — no
screenshot content, no third-party dataset or licence involved.

## What is deliberately absent

No screenshot against a real (non-simulated) field controller — Modbus TCP,
Modbus RTU, or BACnet/IP sources are documented and tested (`145` protocol
tests per the project's own test suite) but no gallery image currently shows
one configured live. No hardware-in-the-loop photo (reComputer R1000/R1100 or
reTerminal DM chassis, USB-to-RS-485 adapter, wired field device). Replace or
extend this gallery with those once a commissioned site or bench setup is
available.

## 2026-09-07 — console screenshots re-captured

`live-points.png`, `access-runtime.png` and `data-service.png` are gone. They
were 1280 x 800 captures of a one-source instance (a single live point in the
point table), cropped to their tables afterwards rather than re-taken.

The `console-*.jpg` files replace them. They come from the console dashboard
branch (`Solution_HVAC_SmartControl`, `feature/building-energy`, e54dfb1;
capture set at `docs/console-react/dashboard-2026-09-07/`) run against the
**e2e fixture site** — 4 protocols, 13 devices, 120 points, with two sources
deliberately offline so the offline path is visible. It is a fixture, not a
commissioned site: the values are generated, and the alarms and quality flags
are what the fixture seeds.

Captured with Playwright + Chrome at `deviceScaleFactor: 2`, full page. Cropped
to content and saved as JPEG quality 90; nothing inside the frame was altered
or scaled.

| File | Before | After |
|---|---|---|
| `cover-console-overview-zh.jpg` | 3200 x 2790 | 3200 x 1810 (KPI row, both trend charts, protocol table) |
| `console-overview-zh.jpg` | 3200 x 2790 | 3200 x 2760 |
| `console-overview-en.jpg` | 3200 x 2790 | 3200 x 2760 |
| `console-topology-zh.jpg` | 3200 x 2646 | 2480 x 2646 (blank right margin removed) |
| `console-topology-en.jpg` | 3200 x 2646 | 2480 x 2646 |

The cover is now `cover-console-overview-zh.jpg`. `cover.png` stays as the
`demo.mp4` thumbnail; `demo.mp4` itself is unchanged and still shows the older
UI.

## Missing: a photograph of the gateway installed

No picture exists of the reComputer R or reTerminal DM in a cabinet, on a DIN
rail or wired to a meter. Every image on this page is a console screenshot, and
the cover should be a photograph of the hardware on site. It has to be supplied.
