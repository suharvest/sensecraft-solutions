# Gallery attribution

## What is in this directory

| File | Origin | Contains dataset imagery |
|---|---|---|
| `architecture.svg` | Drawn for this solution | No |
| `ui-events.png` | Upstream `docs/ui/events.png`, captured from `tools/web_demo.py` | No |
| `ui-event-detail.png` | Upstream `docs/ui/event-detail.png`, same source | No |
| `ui-gallery.png` | Upstream `docs/ui/gallery.png`, same source | No |
| `ui-board.png` | Upstream `docs/ui/board.png`, same source | No |

`architecture.svg` is the data path only — camera, detector, crop, embedder,
gallery lookup, aggregation, and the outputs with their ports. Boxes, arrows,
protocol names and port numbers; no photograph, nothing traceable to any
dataset. It is near-wordless on purpose so one asset serves both the English and
the Chinese page.

The four UI screenshots come from the upstream `tools/web_demo.py`, which
populates the console with **synthetic fixtures**: generated placeholder images,
made-up SKU names and contract-shaped example events. No dataset image, no
photograph of a real product and no field result appears in any of them. Each
caption on the solution page says so, because a screenshot of a recognition
console reads as evidence unless it is labelled otherwise.

## Dataset licences

Neither training dataset permits redistribution, and both restrict what may be
done with anything trained on them. No weights and no dataset imagery ship with
this package.

**SKU-110K — academic and non-commercial only, derivative works forbidden.**
The Trax `LICENSE.txt` distributed with `SKU110K_fixed.tar.gz` grants academic
and non-commercial use, and clause (iii) forbids derivative works. The
single-class YOLOX-Tiny detector trained on it therefore inherits
`license_id: academic-only`, `use_scope: academic-only`,
`redistributable: false`. Source: https://github.com/eg4000/SKU110K_CVPR19.

**JD Products-10K — non-commercial research and education only.** The terms
read "The database can only be used for non-commercial research and educational
purposes." The DINOv2 ArcFace embedders fine-tuned on it inherit
`use_scope: non-commercial`, `redistributable: false`. The verbatim clause is
kept upstream at `data/DATASET-embed.md` §4.1. Source revision used:
`nyris/products10k-traintest-v1@aa4b0ee3498807d23909b12032e6d4bcbb495b93`.
Source: https://products-10k.github.io/.

**Grocery Store Dataset — MIT.** Used for retrieval evaluation only (81 fine
classes, commit `fc80ba9`). This is the only dataset in the set that could enter
a commercial demonstration subset.

**RPC — CC BY-NC-SA 4.0**, **Unitail-OCR — academic only**, **GroZi-120 —
licence unverified**. These appear in the upstream evaluation plan. Unverified
means unverified: they are recorded as `license_id: unverified`,
`use_scope: internal-only` rather than assumed permissive.

## Model backbones

`facebook/dinov2-base` and `facebook/dinov2-small` are Apache-2.0. The
non-commercial restriction on the fine-tuned embedders comes from the training
data, not from the backbone — a commercial deployment can keep the backbone and
must replace the fine-tuning data.

## Code

The upstream project's own code is Apache-2.0.

## Consequence for a commercial deployment

Retrain the detector and the embedder on first-party or permissively licensed
capture, then rebuild every gallery version: vectors written by one embedder are
not comparable to vectors written by another, so a model swap invalidates the
whole gallery rather than part of it. The version manifest records the model
hash and the preprocessing hash so that this is detected rather than discovered
as "nothing is recognised any more".
