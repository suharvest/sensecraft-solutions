# Gallery attribution

## What is in this directory

| File | Origin | Contains dataset imagery |
|---|---|---|
| `recomputer-rk3588.png` | Official Seeed Studio product photo, reComputer RK3588-30 (SKU 100071234), fetched from `https://media-cdn.seeedstudio.com/media/catalog/product/cache/961a49e1875f8c1f40e5990d74e68365/3/5/3588_26_.png` (product page: https://www.seeedstudio.com/reComputer-RK3588-30-p-6817.html) | No |
| `architecture.svg` | Drawn for this solution | No |
| `ui-events.jpg` / `ui-events-en.jpg` | Captured from `tools/web_demo.py`, 2026-09-07 | No |
| `ui-event-detail.jpg` | Same source and session | No |
| `ui-gallery.jpg` | Same source and session | No |
| `ui-board.jpg` / `ui-board-en.jpg` | Same source and session | No |

`recomputer-rk3588.png` is the cover image and first gallery entry. The four
`ui-*.png` shots are synthetic fixtures from `tools/web_demo.py` — made-up SKU
names, generated placeholder images and contract-shaped example events, not a
real recognition run — so none of them is used as the cover; the official
product photo of the reComputer RK3588 this solution's detector numbers were
measured on is used instead.

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

## Shelf and checkout frames from the RK3588 run (2026-09-07)

Three files added 2026-09-07 come from this solution's own device runs in the
`edge-retail-recognition` working tree. They are the runtime's own detector,
tracker and shelf state machine drawing on their own inputs — no separate
rendering path.

| File | Source | Board | Note |
|---|---|---|---|
| `shelf-ok-rk3588-20260907.jpg` | `evaluation/runs/2026-09-07-runtime-rk3588-r4-shelf-b3/media/shelf-ok.png` | Radxa Rock 5B (RK3588) | 20 slots, window 45, 0/20 mismatches. PNG 1280 × 746 → JPEG 1280 × 746 |
| `shelf-wrong-sku-rk3588-20260907.jpg` | same run, `shelf-wrong_sku.png` | same | one slot confirmed `wrong_sku`. PNG 1280 × 746 → JPEG 1280 × 746 |
| `checkout-tracks-rk3588-20260907.gif` | `evaluation/runs/2026-09-07-runtime-rk3588-r5/media/checkout-tracks.gif` | same | copied unchanged |

The GIF's own caveat travels with it: the overlay tool runs the detector and the
tracker but not the embedder, so the instance numbers on screen are kinematic
instances and are looser than the counts the runtime settles on. Item counts
should be read from the run's `raw/score.checkout.json`, not from the frames.

The products in all three files are photographs from the **Grocery Store
Dataset** by Klasson, Zhang and Kjellström — <https://github.com/marcusklasson/GroceryStoreDataset>,
MIT licence (<https://github.com/marcusklasson/GroceryStoreDataset/blob/master/LICENSE>),
which permits commercial use and redistribution. The shelf scenes were composed
from it by `tools/make_shelf_grocery_sim.py`; the licence and its terms are
recorded upstream in `evaluation/data/README.md`.

The detector was trained on **SKU-110K** (<https://github.com/eg4000/SKU110K_CVPR19>)
and the embedder on **Products-10K** (<https://products-10k.github.io/>); neither
dataset's images appear in this gallery.

## 2026-09-07 — console panels re-captured at DPR 2

The four `ui-*.png` files are gone. They were the upstream `docs/ui/*.png`
captures at a 1280 x 800 viewport.

Their replacements come from the same demo server — `uv run python
tools/web_demo.py --port 8089` in `edge-retail-recognition`, Playwright + Chrome,
the demo admin token in `localStorage` — at a **1600 x 1000 viewport with
`deviceScaleFactor: 2`**, so every capture is 3200 x 2000 before cropping.
Cropped to content and saved as JPEG quality 90; nothing inside the frame was
altered or scaled.

| File | Before | After |
|---|---|---|
| `ui-board.jpg` | 3200 x 2000 | 3183 x 1359 |
| `ui-board-en.jpg` | 3200 x 2000 | 3183 x 1359 |
| `ui-events.jpg` | 3200 x 2000 | 3183 x 1663 |
| `ui-events-en.jpg` | 3200 x 2000 | 3183 x 1783 |
| `ui-event-detail.jpg` | 3200 x 2000 | 3183 x 1160 |
| `ui-gallery.jpg` | 3200 x 2000 | 3183 x 1663 |

The data behind them is unchanged and still synthetic: an in-memory MQTT
transport, a `FakeEmbedder` and deterministic-noise registration images. The
SKUs, similarity scores, top-2 margins and slot verdicts on these pages are
fixtures and must not be read as measurements. The RK3588 frames and the
checkout GIF above are the real ones.
