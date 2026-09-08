# Gallery attribution

## What is in this directory

| File | Origin | Contains real face imagery |
|---|---|---|
| `cover-recognition.jpg` | A frame of a Pexels-licensed stock clip, overlaid with the verdicts a reCamera Pro returned for that frame (`unmanned-store-access` `evaluation/runs/2026-09-07-recamera-pro-app/media/cover/cover.jpg`) | Yes — two stock-footage actors |
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

No embedding, no `.npz`, and no face library version is in this package or in the
upstream repository's version control. The upstream evaluation run under
`evaluation/runs/2026-09-06-c1-software/raw/` holds NDJSON logs, manifests and
timings — identifiers and hashes, never face data.

`cover-recognition.jpg` is the one file here that shows faces, and they belong to
stock-footage actors under the Pexels License, not to anyone enrolled in a
deployment. The template that produced its verdicts was averaged from other
frames of the same clip, lived only in the process that scored the frames, and
was never written to the device's face library — see the cover section below.

## Third-party model licences

The models are referenced through `face_rec_api`; **no weights are redistributed
with this package**.

| Artefact | `license_id` | `use_scope` | Redistributable |
|---|---|---|---|
| InsightFace `buffalo_l` — detection + embedding | `non-commercial` (code MIT, **weights and training data non-commercial**) | `non-commercial` | No |
| Silent-Face-Anti-Spoofing — passive liveness | `Apache-2.0` | `commercial` | Yes |
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
under `https://files.seeedstudio.com/Solution/landpage_asset/<id>/<name>-<hash>.<ext>`;
`solution.yaml` references these seven files by their local paths instead. When
the gallery is published, upload all seven and switch `intro.cover_image` and
every `intro.gallery[].src` in the same change.

Neither container image
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
the frame rather than an empty panel. The event list is a **full-page** capture so
that all ten rows and the pager are in the frame instead of being cut at the
viewport edge; that is why its source height exceeds 2000. Cropped to content and saved as JPEG
quality 90; nothing inside the frame was altered or scaled.

| File | Before | After |
|---|---|---|
| `ui-events.jpg` | 3200 x 2314 (full page) | 3183 x 2250 |
| `ui-events-en.jpg` | 3200 x 2398 (full page) | 3183 x 2352 |
| `ui-devices.jpg` | 3200 x 2000 | 3183 x 1660 |
| `ui-devices-en.jpg` | 3200 x 2000 | 3183 x 1660 |
| `ui-status.jpg` | 3200 x 2000 | 3183 x 1197 |

`ui-status.jpg` is new: the device-status page was not in the gallery before.

`ui-persons.png`, `console-devices-live.png` and `console-persons-live.png` were
**not** touched. The two `console-*-live` images come from a real reCamera PoE
run and cannot be reproduced from the demo server; the person library is being
re-shot separately, with the enrolment photographs.

## Cover: reserved
## Cover: the verdicts are real, the footage is stock

`cover-recognition.jpg` is frame 17 of a 250-frame run in which a reCamera Pro
scored a stock clip through the deployed face pipeline. Every box, label and
cosine on the image is that device's output for that frame.

| | |
|---|---|
| Footage | Pexels video 4435043, <https://www.pexels.com/video/man-woman-walking-office-4435043/> |
| Author | Edmond Dantès |
| Licence | Pexels License — free for commercial use, attribution not required |
| Source spec | 3840 × 2160, 25 fps, 10.0 s, MD5 `f7ea86f4ff7cb40fc44c91e4ace40322` |
| Recognition | `recamera-pro-root` (reCamera Pro, RV1126B), `model_tag rv1126b:scrfd500m+mbf512@fp16` |
| Pipeline | letterbox 640 → `scrfd500m_640_fp16.rknn` → `scrfd.decode` → five-point align to 112 → `arcface_mbf_fp16.rknn` → cosine |
| Run | 250 frames in 51.8 s, offline from JPGs; script `tools/recamera_pro_cover/run_offline.py` in the upstream repository |

The gallery it matched against was temporary: the 512-D template was averaged
from 18 chips of the same person in frames 205–225, held in the scoring
process's memory, and never written to `/userdata/local/face-gallery/`, whose
only file and its timestamp were unchanged after the run. Frame 17 is outside
205–225 and did not contribute to the template, so the cosine printed on the
cover comes from a frame the template was not built from — the frame and the
template still come from the same clip, same actors, and same lighting, not a
separate test sample. `EMP-042` is a label invented for this clip and matches no
employee. At threshold 0.38 the matched person scored 0.486–0.951 across the
clip and the unenrolled person −0.047–0.123; the two ranges do not overlap and
no frame was misclassified. Per-frame output: `evaluation/runs/2026-09-07-recamera-pro-app/media/cover/raw/offline-run.json`.

What this cover does **not** show: a person standing at a real door, a live
camera stream, a liveness verdict, or a relay firing. Recognition ran on JPG
frames, so it exercises detection, alignment, embedding and matching on the
target NPU and nothing downstream of them. The recognise-to-unlock path end to
end is still unexercised — the 2026-09-07 runs
(`evaluation/runs/2026-09-07-recamera-poe-p1/`, `-recamera-pro-app/`) record why.

The only identity enrolled in those runs is `poe-20260907-a`, whose enrolment
image is `image_T1.jpg` from MiniVision's Silent-Face-Anti-Spoofing repository
(Apache-2.0), a public sample rather than a photograph of a person who exists.
