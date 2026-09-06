# Gallery attribution

## What is in this directory

| File | Origin | Contains real face imagery |
|---|---|---|
| `architecture.svg` | Drawn for this solution package | No |
| `ui-events.png` | Screenshot of the management console, running on synthetic demo data | No |
| `ui-persons.png` | Screenshot of the management console, running on synthetic demo data | No |
| `ui-devices.png` | Screenshot of the management console, running on synthetic demo data | No |

`architecture.svg` is the data path only — the cloud face library and console,
the four presets, and the relay and independently powered lock they all end at.
Boxes, arrows, product names, protocol names, port numbers and pin labels; no
photograph, no captured frame, no face.

## The three screenshots are synthetic

All three were taken from `tools/screenshot_ui.py` in the upstream repository
against the demo server (`tools/web_demo.py`), which runs on an in-memory MQTT
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
`solution.yaml` references these four files by their local paths instead. When
the gallery is published, upload all four and switch `intro.cover_image` and
every `intro.gallery[].src` in the same change.

`assets/firmware/` carries a manifest only — no binary. Neither container image
named in `assets/cloud/docker-compose.yml` or `assets/edge/docker-compose.yml`
has been pushed; both files say so at the top.
