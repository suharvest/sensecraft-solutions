# Validation notes

This package has an offline schema validation result and a real RK3576 browser observation. It is not marked `hardware` verified in `solution.yaml`.

## Covered

- `solutionctl validate solutions/edge_command_workbench --spec-dir spec --check-urls` passed.
- The deployed application was exercised on `cat-remote` RK3576 with the RKNN backend in three real command-ranking scenarios.
- The browser's default example successfully started a decision and selected the conveyor speed reduction action. The observed total latency for that request was `359.917 ms`.
- The native browser screenshot was copied without resizing or image generation from `/tmp/edge-workbench-rk3576-ui.jpg` to `gallery/workbench.jpg`.
- Six native browser screenshots were copied to `gallery/demo/`; `gallery/demo/command-selection.gif` is a 1280×662, 8-second key-step edit from four screenshots with 1/1/3/3-second holds. It is not a live recording or model-timing measurement.
- The final archive and Docker config digest are recorded in `assets/artifacts.json`. A legacy cat container image ID differed while the saved image config digest matched; the verifier checks archive/config/tag identity instead of requiring the legacy image ID.
- The tested unprivileged runtime uses `systempaths=unconfined`, `/dev/dri` including the NPU `card1` node, read-only device-tree binds, and read-only RKNN runtime mounts at both `/usr/lib/librknnrt.so` and `/opt/rknn/librknnrt.so`; no `privileged` mode is used. The isolated 18769 test reached `model_ready:true` and returned the conveyor speed decision in 398.3068 ms.
- The core SDK smoke log records three real three-option requests with inference times 387.5598 ms, 339.4597 ms, and 336.0978 ms; these are observations for that container run, not an accuracy or full-speed RK3576 claim. Source: `/tmp/laya-container-cat-smoke.txt`.
- The single-pass archive verifier accepted the 83,497,492-byte Spark archive and a live `docker save` stream with the pinned tag/config SHA. It rejected a wrong tag and a wrong config SHA. The Spark command output and failure outputs are recorded in `/tmp/edge-workbench-final-validation.txt`; no archive was uploaded.
- The five approved release files were uploaded and verified under [`releases/edge-workbench-0.1.0`](https://huggingface.co/harvestsu/laya-multilingual-rknn-tensorrt/tree/main/releases/edge-workbench-0.1.0) at repository commit `a26f490de585f1c6d00c9424372d65636446e61a`. The remote verification record is `/tmp/edge-workbench-hf-verification.json`; it reports exact five-file contents, matching large-file LFS SHA/size, and matching small-file downloads.

## Not covered

- Browser voice recording was not tested.
- The complete engine download-and-deploy chain was not rerun; the cat validation host had approximately 522MB free and was below the 4GB deployment precheck.
- This record does not claim release readiness, a completed HF upload, or a model accuracy result.

Screenshot source SHA256: `07add8c05cf81c4f45b851e3d568e5e3e2971b436e3c141850f4b968bfceb2e7`.
