# Gallery attribution

## What is in this directory

| File | Origin | Contains real face imagery |
|---|---|---|
| `console-devices-live.png` | Screenshot of the management console during a live reCamera PoE run, 2026-09-07 (`unmanned-store-access` `evaluation/runs/2026-09-07-recamera-poe-p1/media/console-devices-en-20260907.png`) | No |
| `console-persons-live.png` | Same console and run (`.../console-persons-en-20260907.png`) | No |
| `architecture.svg` | Drawn for this solution package | No |
| `ui-events.jpg` / `ui-events-en.jpg` | Screenshot of the management console, running on synthetic demo data | No |
| `ui-persons.png` | Screenshot of the management console, running on synthetic demo data | No |
| `ui-devices.jpg` / `ui-devices-en.jpg` | Screenshot of the management console, running on synthetic demo data | No |
| `ui-status.jpg` | Screenshot of the management console, running on synthetic demo data | No |

`architecture.svg` is the data path only — the cloud face library and console,
the four presets, and the relay's dry contact into the door controller's input
that they all end at — the lock and its supply stay with the door-control party.
Boxes, arrows, product names, protocol names, port numbers and pin labels; no
photograph, no captured frame, no face.

## The two console-live screenshots are from a real run

`console-devices-live.png` and `console-persons-live.png` were captured from the
management console while a reCamera PoE unit was reporting in, on 2026-09-07. The
console backend ran on a developer machine (not a store deployment); the device
heartbeat (library version, model tag) came from the real unit. The person
entries are enrolment fixtures, not photographs of identifiable people, and
no face image is visible in either screenshot.

## The ui-* screenshots are synthetic

All of them were taken against the demo server (`tools/web_demo.py`), which runs on an in-memory MQTT
broker, a `FakeRecognizer` and a `FakeEmbedder`. Consequences worth stating
plainly, because a console screenshot looks like field data:

- **The people are invented.** `p_alice`, `p_bob`, `p_carol`, `p_mallory` are
  fixture identifiers. No photograph of any person was enrolled, captured,
  stored or displayed to produce these images, and the person rows carry no
  thumbnail because the demo never had one.
- **The events are invented.** Every row comes from the scripted frames in
  `tools/verify_software_loop.py` — one allowed, one liveness failure, one
  liveness-unknown, one blacklist hit, one below-threshold, one no-face, one
  debounce. The distribution is a test matrix, not a store's traffic.
- **The scores are not accuracy figures.** `FakeRecognizer` returns 1.0 for a
  matching fixture and a near-zero cosine for a stranger. Nothing on these
  screenshots may be quoted as a recognition or liveness result.
- **The devices are invented.** `verify-loop-device` is the loop's own node;
  the offline state shown is the in-memory broker replaying a retained LWT.

They are included because the console's layout, the three-role gate, the audit
hash column and the deletion-barrier refusal are real code paths that a reader
should be able to see before deploying. They are not evidence of field
performance.

## No biometric data is committed anywhere

No face image, no embedding, no `.npz`, and no face library version is in this
package or in the upstream repository's version control. The upstream evaluation
run under `evaluation/runs/2026-09-06-c1-software/raw/` holds NDJSON logs,
manifests and timings — identifiers and hashes, never face data.

## Third-party model licences

The models are referenced through `face_rec_api`; **no weights are redistributed
with this package**.

| Artefact | `license_id` | `use_scope` | Redistributable |
|---|---|---|---|
| InsightFace `buffalo_l` — detection + embedding | `non-commercial` (code MIT, **weights and training data non-commercial**) | `non-commercial` | No |
| Silent-Face-Anti-Spoofing — passive liveness | `Apache-2.0` | `commercial` | Yes |
| P4 WE2 models (SCRFD + distilled MobileFaceNet) | `non-commercial`, inherited from InsightFace | `non-commercial` | No |
| This package and the upstream repository's own code | `Apache-2.0` | `commercial` | Yes |

InsightFace's own statement, quoted verbatim from the upstream project README /
model zoo:

```
The code of InsightFace is released under the MIT License. There is no
limitation for both academic and commercial usage.

The training data containing the annotation (and models trained with these
data) are available for non-commercial research purposes only.
```

`buffalo_l` is a model trained with that data, so it is usable for
**non-commercial research purposes only**. A commercial deployment must swap in
a commercially licensed backbone and **rebuild every face library version** —
embeddings are not comparable across models, so old versions become dead weight
rather than merely stale. Full text upstream in `MODEL_LICENSE.md` and `NOTICE`.

Silent-Face-Anti-Spoofing is MiniVision Technology's, Apache License 2.0, used
unmodified through `face_rec_api`. Apache-2.0 permits commercial use and
redistribution provided the copyright and licence notices are retained and
changes are marked.

## CDN

**Nothing has been uploaded.** The packaging convention is CDN-hosted images
under `https://files.seeedstudio.com/Solution/landpage_asset/<id>/<name>-<hash>.png`;
`solution.yaml` references these six files by their local paths instead. When
the gallery is published, upload all six and switch `intro.cover_image` and
every `intro.gallery[].src` in the same change.

`assets/firmware/` carries a manifest only — no binary. Neither container image
named in `assets/cloud/docker-compose.yml` or `assets/edge/docker-compose.yml`
has been pushed; both files say so at the top.

## 2026-09-07

`console-devices-live.png` (1568 × 764 → 1568 × 375) and
`console-persons-live.png` (1568 × 764 → 1568 × 420) were cropped to their
tables. The architecture diagram moved from third place to last.

## 2026-09-07 — console panels re-captured at DPR 2

`ui-events.png` and `ui-devices.png` are gone. Both were 1280 x 800 CSS captures
from the upstream `tools/screenshot_ui.py`.

Their replacements were taken the same way — `uv run python tools/web_demo.py
--port 8088` in `unmanned-store-access`, Playwright + Chrome, the demo admin
token in `localStorage` — but at a **1600 x 1000 viewport with
`deviceScaleFactor: 2`**, so every capture is 3200 x 2000 before cropping. The
device page was captured after issuing one unlock, so the command receipt is in
the frame rather than an empty panel. Cropped to content and saved as JPEG
quality 90; nothing inside the frame was altered or scaled.

| File | Before | After |
|---|---|---|
| `ui-events.jpg` | 3200 x 2000 | 3183 x 2000 (right page edge trimmed) |
| `ui-events-en.jpg` | 3200 x 2000 | 3183 x 2000 |
| `ui-devices.jpg` | 3200 x 2000 | 3183 x 1660 |
| `ui-devices-en.jpg` | 3200 x 2000 | 3183 x 1660 |
| `ui-status.jpg` | 3200 x 2000 | 3183 x 1197 |

`ui-status.jpg` is new: the device-status page was not in the gallery before.

`ui-persons.png`, `console-devices-live.png` and `console-persons-live.png` were
**not** touched. The two `console-*-live` images come from a real reCamera PoE
run and cannot be reproduced from the demo server; the person library is being
re-shot separately, with the enrolment photographs.

## Cover: reserved

The cover on this page has to be a frame from a reCamera Pro showing a person
at the door and the recognition verdict the device returned. No such frame
exists yet: both 2026-09-07 device runs
(`evaluation/runs/2026-09-07-recamera-poe-p1/`, `-recamera-pro-app/`) record
that the recognise-to-unlock path was never exercised end to end, because
nobody stood in front of the lens and the network had neither a facedb service
nor a broker. Their media are typeset renders of terminal output, not
screenshots, and are not published here. Until that frame is captured, the
device-status console screenshot stands in as the cover.

Nothing on this page contains a face: the only enrolled identity in the runs is
`poe-20260907-a`, whose enrolment image is `image_T1.jpg` from MiniVision's
Silent-Face-Anti-Spoofing repository (Apache-2.0), a public sample rather than a
photograph of a person who exists.
