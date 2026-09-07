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

## cover.png / access-runtime.png

Both are real screenshots of the **Access** page (`Configure industrial
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

`cover.png` is a tighter crop of the same page (no top app-bar/login chrome);
`access-runtime.png` is the full-chrome capture. Neither is a mock-up or a
hand-drawn illustration.

## live-points.png

Real screenshot of the **点位总表 / Point Table** page (zh-CN, `EN` toggle
visible), showing one live point (`opcua-hvac-main` → `ahu-01` →
`pt:opcua-hvac-main:ahu-01:supply.temp`, value 21.5 °C, quality `良好`/Good,
timestamp 2026/8/18 12:50:58) sourced from the same OPC UA simulator source as
above.

## data-service.png

Real screenshot of the **统一数据服务 / Data Service** page: embedded MQTT
broker status (`内置 (amqtt)`, running, TLS disabled, "control security:
remote control disabled" banner), gateway ID `hvac-edge-01`, and the MQTT
topic contract table (`missionpack/v1/{gateway}/command/{command_id}` etc.).
The page explicitly and honestly states `Sparkplug 等级: not-implemented`,
matching `solution.yaml`'s own "not Sparkplug B compatible" disclosure — this
is the product's real status readout, not a mocked-up claim.

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
