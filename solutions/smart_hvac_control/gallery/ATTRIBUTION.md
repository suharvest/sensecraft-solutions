# Gallery attribution

## Current state: architecture diagram plus six running-UI captures

`intro.cover_image` and `intro.gallery[]` in `solution.yaml` reference the architecture
diagram and six PNG captures of the actual `missionpack-knn` web console, taken against a
real backend process with real (simulated) field devices behind it — not drawn, not staged
composites of unrelated screens.

| File | What it is | Referenced? | Origin |
|---|---|---|---|
| `architecture.svg` | Schematic block diagram | **Yes** — `intro.gallery[]` | Drawn for this package, first-party |
| `points-overview-running.png` | Point table, all 13 points live and reading `good` quality across both sources | **Yes** — `intro.cover_image`, `intro.gallery[]` | Screen capture, see below |
| `access-registration.png` | Access page: the SDM630 Modbus TCP source and the HVAC BACnet/IP source, both online, with point counts | **Yes** — `intro.gallery[]` | Screen capture, see below |
| `control-dispatch-readback.png` | Data-service page's command-receipts table: manual setpoint and compressor-enable writes with `protocol_acknowledged` status, requested vs. effective value and actor | **Yes** — `intro.gallery[]` | Screen capture, see below |
| `points-source-offline.png` | Point table with the SDM630 Modbus source stopped mid-capture, its ten points showing `offline` quality while the BACnet source stays `good` | **Yes** — `intro.gallery[]` | Screen capture, see below |
| `alarm-banner-source-offline.png` | Point table with the alarm banner raised: one unrecovered, unacknowledged `source-offline` warning after the SDM630 simulator took `SIGTERM` | **Yes** — `intro.gallery[]` | Screen capture, see the 2026-09-06 wiring session below |
| `control-readback-compensated.png` | Command-receipt ledger with the readback column: matched writes, one mismatched-and-compensated write showing the out-of-band value 99, and the compensation command that undid it | **Yes** — `intro.gallery[]` | Screen capture, see the 2026-09-06 wiring session below |
| `cover.svg` | Schematic cover drawing | No | Drawn for this package, first-party |
| `dashboard.svg` | Sketch of a dashboard layout | No | Drawn for this package, first-party |
| `recomputer.svg` | Schematic device outline | No | Drawn for this package, first-party |

`cover.svg`, `dashboard.svg` and `recomputer.svg` stay on disk, unreferenced, for history —
each would read as product photography or as a screenshot of a running console if it were
ever wired back in, which would present a drawing as evidence the system has been seen
working.

Licensing: the three unreferenced SVGs and `architecture.svg` are original drawings made for
this package; no third-party asset, brand mark or stock image is included. The six PNG
captures are original screen captures of this repository's own software, taken by the
packaging agent; nothing in them is a third-party asset either.

## Capture inventory (2026-09-06, spark, UTC+8)

| File | Size | Dimensions | SHA-256 | Captured at (local) |
|---|---:|---|---|---|
| `points-overview-running.png` | 152 KB | 1440x900 | `c9faa1d0750b04516edbb5af21e6980601e05914e49a052c30f4ffb603c3d7fc` | 2026-09-06 06:12 CST |
| `access-registration.png` | 64 KB | 1440x900 | `c362311d508bb4d2d7003dbd49031bc859cd5d5ad9b636fa4a01d5a71b7c18e8` | 2026-09-06 06:12 CST |
| `control-dispatch-readback.png` | 179 KB | 1440x900 | `aabe3ef80e771e8737b410de008cb0410fa3184b90d16e5ac60a2b3eb35da178` | 2026-09-06 06:12 CST |
| `points-source-offline.png` | 144 KB | 1440x900 | `b5fd6ef07d679ace77560ae595d15d67352294853623680f55bdf012d451002b` | 2026-09-06 06:13 CST (fault-injected re-capture) |

## How the four PNG captures were taken

- **Where:** the `spark` fleet device (x86_64 Linux, not a customer site), in a disposable
  `git worktree` at `~/b2-screens` off commit `d3046db` of `feature/building-energy`
  (`Solution_HVAC_SmartControl`).
- **What was actually running**, all as bare processes started by the packaging agent, none
  of it Docker: the FastAPI backend (`uvicorn app_server.main:app`) with the production
  frontend build served from it; the detachable protocol simulators from
  `tests/simulators/` — Modbus TCP running the built-in **Eastron SDM630** device profile
  (`--device-profile sdm630`) with a 24-point daily load-curve shape accelerated
  (`--profile-hours-per-second 60`) so the meter's real-time behaviour was visible inside a
  practical capture window, a BACnet/IP device exposing an analog input, a writable analog
  output and a writable binary value, and the amqtt-based MQTT broker used as the northbound
  publish target; the gateway's own built-in MQTT broker for the native data-service page.
- **What is real vs. simulated:** the web console, the point registry, the write/readback
  control path, the command-receipt ledger and every value shown are the product's real
  runtime behaviour. The *field devices* behind that runtime are the repository's own
  protocol simulators, not a physical SDM630 meter or a physical HVAC controller — this is
  disclosed in every caption on these four images and in `solution.yaml`'s per-image
  caption text.
- **Data run duration:** the SDM630 source, the BACnet source and a scripted setpoint
  dispatcher (issuing a new HVAC setpoint write roughly every 45 seconds, alternating
  20–25 °C) ran continuously for at least 15 minutes before any of the four captures were
  taken, so the command-receipt history and the meter's live readings reflect sustained
  operation rather than a cold-started single sample.
- **Capture 4's fault:** the SDM630 Modbus TCP simulator process was stopped
  (`SIGTERM`) immediately before this capture and left down long enough for the gateway's
  existing poll-and-quality-degrade path (5 s poll interval) to mark its ten points
  `offline`; the HVAC BACnet source was left running throughout, which is why it still
  reads `good` in the same screenshot. This exercises the point table's pre-existing
  stale/offline quality states (B2 §3's UI text explicitly reuses this mechanism); it is
  **not** a capture of the new alarm-envelope banner (`frontend/src/shell/alarmBanner.js`)
  or of the control-rollback coordinator (`app_server/services/control_rollback.py`) —
  as of commit `d3046db`, neither is wired into the live sampling or
  prediction cycle yet (see `Solution_HVAC_SmartControl/docs/building-energy-impl-notes.md`,
  §2 "Not wired into the prediction cycle yet" and §3 "Raising them ... is left to the
  cycle-wiring step"), so no screenshot in this package shows a live alarm banner or a live
  rollback event. Capture 3's writes are manual, operator-confirmed commands with a verified
  field readback — real write-and-readback, not a rollback demonstration.
- **No site data:** every host, IP address and identifier visible (`127.0.0.1`, the
  `sdm630-meter` / `hvac-bacnet` source ids, the `b2-admin` demo account) is local-loopback
  or a name created for this capture session. Nothing about a real building, customer or
  network is present, so no redaction was required.
- **Reproduce it:** `tests/simulators/README.md` documents the simulator CLI;
  `tests/simulators/protocols/sdm630.py` is the SDM630 device profile;
  `app_server/adapters/meter_point_templates.py` is the built-in register template
  (`eastron_sdm630_v2`) whose CSV was resolved and fed through the same
  `/api/v1/sources/{id}/discoveries` candidate/confirm flow the console's own Access page
  wizard uses.

Full transcript (commands run, `docker ps` before/after, raw `solutionctl validate` output,
and the original PNGs alongside the ones committed here) is in
`Solution_HVAC_SmartControl/evaluation/runs/2026-09-06-b2-screens/` on the Mac working copy.

## Capture inventory addendum (2026-09-06, spark, UTC+8) — wiring session

| File | Size | Dimensions | SHA-256 | Captured at (local) |
|---|---:|---|---|---|
| `alarm-banner-source-offline.png` | 151 KB | 1440x900 | `c54aeda665b2bfac404ff7f8ffd2e59cf757edc2aa4dced88221300c03f9102a` | 2026-09-06 08:09 CST |
| `control-readback-compensated.png` | 135 KB | 1440x900 | `2d23357c933c55fdc7834f1022bfba29f0bb867cf37c6307be5da510ea5aab8b` | 2026-09-06 08:08 CST |

### How these two were taken

- **Where:** the same `spark` fleet device, in the same disposable `git worktree`
  `~/b2-screens`, this time at commit `4b30192` of `feature/building-energy`
  (`Solution_HVAC_SmartControl`) — the commit that gives the receipts table its
  readback column. Bare processes started by the packaging agent, no Docker; the
  five containers in `docker ps` before and after were identical and untouched.
- **What was running:** the FastAPI backend (`uvicorn app_server.main:app`, port
  18280, `MISSIONPACK_DATA_DIR` pointed at a throwaway directory) with the
  production frontend build served from it; two Modbus TCP simulators from
  `tests/simulators/` — the **Eastron SDM630** device profile on port 15020
  (`--profile-hours-per-second 60`) and a plain writable device on port 15023
  standing in for the HVAC control register.
- **Why a Modbus control register and not the BACnet setpoint:** compensation
  targets are only built for points whose adapter can be restored, and the
  production cycle supplies no BACnet write priority to
  `build_rollback_targets()`, so BACnet points are skipped
  (`app_server/services/prediction_rollback_bridge.py`). A writable Modbus
  holding register is therefore the only shape that exercises a real
  compensation end to end.
- **`control-readback-compensated.png`:** a prediction run with
  `rollback: {enabled: true, settle_seconds: 2.5}` wrote its output to the
  holding register; the register was then changed out of band to `99` by a
  separate Modbus client before the settle window expired. The gateway read the
  point back, found the mismatch, restored the frozen pre-write value, and wrote
  a `mismatch-compensated` readback event against the original command. Both the
  original write and the compensation are visible in the ledger, the latter
  issued by `plugin:prediction:rollback`. Earlier rows in the same capture show
  `verified` writes from cycles nobody interfered with — the two verdicts appear
  side by side because both really happened.
- **`alarm-banner-source-offline.png`:** the SDM630 simulator process was sent
  `SIGTERM`; the source went `offline`, the health/alarm bridge raised one
  `source-offline` alarm, and the shell's 5-second poll of `GET /api/health/latest`
  put it in the banner. Unlike `points-source-offline.png` (an earlier capture of
  the pre-existing per-point quality state only), this one **is** the alarm
  envelope path.
- **What is real vs. simulated:** identical to the first four captures — the
  console, the point registry, the write/readback/compensate path, the durable
  command ledger and the alarm register are the product's real runtime; the field
  devices are this repository's protocol simulators. Every caption says so.
- **No site data:** every host and identifier visible (`127.0.0.1`, the
  `sdm630-meter` / `hvac-ctrl` source ids, the `b2-admin` demo account) is
  local-loopback or created for this session.

Transcript for these two (driver scripts, raw receipts, health payloads, pytest
output) is in `Solution_HVAC_SmartControl/evaluation/runs/2026-09-06-b2-wire-e2e/`.
