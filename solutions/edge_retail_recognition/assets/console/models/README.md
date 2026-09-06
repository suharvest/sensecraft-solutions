# Embedding model goes here

The `server` service mounts this directory as `/models:ro`. It ships empty.

Place `dinov2b_arcface_products10k_224_b1.onnx` here (348,115,086 bytes, sha256
`01ae07d10f638a2ebeb85100325ad79765a325d1026b728b60f1ee106e76eaae`) and set
`RETAIL_EMBEDDER=onnx` in the `.env` beside `docker-compose.yml`, then
`docker compose up -d server`.

The file is not shipped with this package. Its licence is `products10k-terms`:
`use_scope: non-commercial`, `redistributable: false`, inherited from the JD
Products-10K training data — the `facebook/dinov2-base` backbone is Apache-2.0,
the restriction is not. A commercial deployment has to retrain the embedder and
rebuild every gallery version.

Without it the service starts on the placeholder `FakeEmbedder`, which hashes
image bytes into vectors. Registration succeeds and retrieval is meaningless.
Neither `GET /api/health` nor the startup log says which backend is loaded, so
there is no runtime signal — see the "Place the Embedding Model" guide step.
