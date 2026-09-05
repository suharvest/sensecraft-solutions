# Gallery attribution and open items

## Current state: no product imagery

This solution ships **no** cover image and **no** gallery entries. `solution.yaml` and both
guide files reference none of the files in this directory.

Four SVG files remain on disk:

| File | What it is | Origin |
|---|---|---|
| `cover.svg` | Schematic cover drawing | Drawn for this package, first-party, no third-party material |
| `dashboard.svg` | Schematic sketch of a dashboard layout | Drawn for this package, first-party |
| `architecture.svg` | Schematic block diagram | Drawn for this package, first-party |
| `recomputer.svg` | Schematic device outline | Drawn for this package, first-party |

None of them is a screenshot or a photograph. They were previously used as the cover, the
gallery images and the guide wiring images, which presented drawings as evidence of a
running system. They were removed from every reference for that reason and are kept only so
the history is traceable; delete them once the captures below exist.

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

When the captures exist, restore `intro.cover_image` and `intro.gallery[]` in
`solution.yaml` with CDN URLs (`https://files.seeedstudio.com/Solution/landpage_asset/smart_hvac_control/<name>-<hash>.png`),
give each a bilingual caption, and record the capture date, device and image tag in this
file.
