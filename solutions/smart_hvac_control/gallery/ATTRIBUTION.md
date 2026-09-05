# Gallery attribution and open items

## Current state: one schematic diagram, no captures

This solution ships the architecture diagram as both the cover image and the only gallery
entry. Its caption states that it is a schematic diagram and not a screenshot. Nothing else
in this directory is referenced by `solution.yaml` or by either guide file.

| File | What it is | Referenced? | Origin |
|---|---|---|---|
| `architecture.svg` | Schematic block diagram | **Yes** — `intro.cover_image` and the single `intro.gallery[]` entry | Drawn for this package, first-party |
| `cover.svg` | Schematic cover drawing | No | Drawn for this package, first-party |
| `dashboard.svg` | Sketch of a dashboard layout | No | Drawn for this package, first-party |
| `recomputer.svg` | Schematic device outline | No | Drawn for this package, first-party |

None of the four is a screenshot or a photograph. `architecture.svg` is kept in use because
a block diagram labelled as a block diagram claims nothing it cannot support. The other
three would read as product photography or as a screenshot of a running console, which
would present a drawing as evidence that the system has been seen working; they were
removed from every reference for that reason and are kept only so the history is traceable.
Delete them once the captures below exist.

Licensing: all four are original drawings made for this package. No third-party asset,
brand mark or stock image is included, so no upstream licence applies. Nothing is redacted
because nothing in them came from a real site.

## TODO — four real captures, blocked

The four images this page needs, per the B2 building-energy spec §4:

1. The real device and the running home page.
2. The meter and HVAC point registration table.
3. A KNN prediction, the control write, and the field readback.
4. An offline alarm, the rollback audit trail, and spool recovery.

Blocked on a commissioning run: the meter template, the rollback coordinator and the alarm
envelope exist upstream on `feature/building-energy`, but no image carrying them has been
built, and no device has been run with a real SDM630 and a real HVAC controller. Captures
must come from that run, not from the simulator, and any site identifier, IP address,
account name or building name visible in a capture has to be redacted before it lands here.

When the captures exist, add them to `intro.gallery[]` in `solution.yaml` with CDN URLs
(`https://files.seeedstudio.com/Solution/landpage_asset/smart_hvac_control/<name>-<hash>.png`),
move `intro.cover_image` from the diagram to capture 1, give each a bilingual caption, and
record the capture date, device and image tag in this file. The architecture diagram may
stay in the gallery after that, as a diagram alongside the captures.
