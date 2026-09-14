## What it does

A camera watches a checkout belt or a shelf and recognises the SKU of every product in the frame. The checkout lane outputs an item list, counting each product once; the shelf reports each slot as ok, empty, wrong SKU or unknown. A new SKU is registered from 3 to 8 photos, with no model retraining.

## What you get

- **Read a whole basket at checkout**: SKUs and quantities without scanning item by item.
- **Shelf out-of-stock and misplacement reports**: no one has to walk the aisle.
- **Register new products by photo**: 3–8 photos per SKU, no retraining; the product library is versioned and can be rolled back.
- **Management UI**: register products, browse recognition events, and view checkout/shelf dashboards.
- **Results pushed live over MQTT** for your own systems.

## Where it fits

- Checkout lanes that should read a basket at once instead of scanning item by item
- Shelves that should report out-of-stock and misplacement automatically
- Stores that rotate SKUs weekly

Not for legal metrology, legally binding prices or loss prevention.

## Measured results

| Metric | Result |
|---|---|
| Dropped frames in checkout replay (reComputer J40) | **0 in 2956 frames** |
| Product recognition accuracy (DINOv2-base, 8 photos per SKU) | **top-1 84.67% / top-5 96.66%** |
| Effect of photo count (DINOv2-small) | 8 photos **top-1 79.11%**, 1 photo **top-1 51.11%** |
| Shelf frame to result (reComputer RK3588, 20 SKUs) | **p50 924 ms / p95 1153 ms** |

Dropped frames and latency were measured on recorded video replay.

## Output Interfaces

| Interface | Content |
|---|---|
| MQTT "retail/v1/events" | One message per frame: position, SKU and similarity of every product |
| HTTP "/v1/gallery/*" | Product registration, library versions and rollback |
| HTTP "/api/*" | Event list, event detail and checkout/shelf dashboard data |

## Deployment Comparison

| Preset | Speed | Notes |
|---|---|---|
| reComputer J40 (Jetson Orin NX) | Detection p50 5.18 ms, recognition p50 4.23 ms | 2956-frame checkout replay, 0 drops |
| reComputer J30 (Jetson Orin Nano) | Detection p50 5.88 ms, recognition p50 5.06 ms | 6726-frame replay, 0 drops |
| reComputer RK3588 series | Detection p50 56.7 ms (INT8 26.0 ms), recognition on CPU | Shelf replay p50 924 ms |
| reComputer RK3576 | Detection p50 51.05 ms, recognition p50 56.38 ms | Detection and recognition both on the NPU |
| reComputer R2000 (Hailo-8) | Detection p50 9.04 ms, recognition 91.95 ms per item (CPU) | A five-item basket takes about half a second |

## Usage Notes

- **Register at least 3 photos per SKU**; fewer is rejected. Front, back and side under two lighting conditions is recommended.
- **Estimate latency by items per frame**: on the Hailo-8 path a shelf frame takes ~14 s, so shelf scenarios need frame decimation or per-slot sampling.
- New product-library versions ship with a deployment; devices do not pull them automatically yet.
- Two container images are built on the management host at deploy time.
- The bundled MQTT broker is anonymous and plaintext; add accounts and TLS before going into a store.
- Changing the embedding model requires rebuilding the product library; the old library cannot be used.
- The models are fine-tuned on studio product photos; test with images of your own shelves before going live.

## Licensing note

The project code and the DINOv2 backbones are Apache-2.0, but **neither bundled model weight may be used commercially**: the detector weights are trained on SKU-110K (academic and non-commercial use only), and the embedder weights are fine-tuned on JD Products-10K (non-commercial research and education only). Commercial deployment requires retraining both models on self-collected or permissively licensed data and rebuilding every library version. See "gallery/ATTRIBUTION.md".
