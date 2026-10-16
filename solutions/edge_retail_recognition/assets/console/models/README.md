# Embedding model goes here

The `server` service mounts this directory as `/models:ro`. It ships empty.

Once `console_stack` has deployed, this directory exists on the console host
at `/home/{{username}}/edge-retail-recognition/console_stack/models/` — the
same remote path the compose file and `.env` were uploaded to. Place the
model there, on the deployed host, not only in this local checkout.

Which file depends on the preset — the two models' galleries are not
interchangeable, and switching one for the other means rebuilding every
gallery version:

- **RK3588 / Jetson**: `dinov2b_arcface_products10k_224_b1.onnx`
  (348,115,086 bytes, sha256
  `01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`).
- **Raspberry Pi**: `dinov2s_arcface_products10k_224_b1_dynint8.onnx`
  (23,541,073 bytes, sha256
  `50e886aeab7b61a7eebe6ea3492b2d3ba0e74a859acedcbb9e9917b2b60454f6`).

After placing the file, set `RETAIL_EMBEDDER=onnx` in the `.env` beside
`docker-compose.yml` (override `RETAIL_EMBEDDER_ONNX` too on the Pi, since its
default points at the base filename), then `docker compose up -d server`.

Neither file is shipped with this package. Both are licensed
`products10k-terms`: `use_scope: non-commercial`, `redistributable: false`,
inherited from the JD Products-10K training data — the `facebook/dinov2-base`
and `facebook/dinov2-small` backbones are Apache-2.0, the restriction is not.
A commercial deployment has to retrain the embedder and rebuild every gallery
version.

Without a real model the service starts on the placeholder `FakeEmbedder`,
which hashes image bytes into vectors. Registration succeeds and retrieval is
meaningless. Neither `GET /api/health` nor the startup log says which backend
is loaded, so there is no runtime signal — see the "Place the Embedding
Model" guide step.
