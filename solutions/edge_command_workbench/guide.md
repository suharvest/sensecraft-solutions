## Preset: RK3576 Remote {#rk3576_remote}

Deploy the local command workbench to one RK3576 Linux device over SSH. This preset is for RK3576 only; Jetson and RK3588 are not included in this package.

## Step 1: Deploy the Workbench {#deploy type=docker_remote required=true config=devices/rk3576_remote.yaml}

The deployment prepares the pinned application archive, RKNN model, and tokenizer, then starts the one-container web workbench on port 18768. The target must already have Docker and the RKNN runtime library.

### Target {#rk3576 type=remote device_name="RK3576" config=devices/rk3576_remote.yaml default=true}

The deployment uses `/home/<username>/edge-command-workbench` on the target. It skips Docker installation and Docker image pulling. The image archive is loaded only when the exact local image tag is absent. Before deployment, keep at least 4GB free, install Docker and `/usr/lib/librknnrt.so`, and expose the tested RK3576 NPU DRM nodes `/dev/dri/card1` and `/dev/dri/renderD129`.

Enter the target IP or hostname, SSH username, and SSH password. An existing compatible local voice service URL is optional. Leave it blank when voice is not needed, then click **Deploy**.

### Wiring

1. Power the RK3576 and connect it to the same network as the computer running SenseCraft Solution.
2. Connect the device's network interface and keep the physical connections stable during deployment.

### Deployment Complete

Open the verification page at `http://<device-ip>:18768`. The page is served by the deployed application. A browser can use HTTP when opened from localhost or the local network; browser microphone access for an optional voice service requires HTTPS or localhost.

#### Optional voice service

Set `VOICE_SERVICE_URL` only when a compatible local voice service already exists on the target. This solution does not automatically install a voice service.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Image archive or tokenizer checksum is missing | Complete the release manifest checksums after building the archive; the bootstrap script stops before starting Docker. |
| Docker image tag is missing after load | Confirm the archive was built for RK3576 arm64 and contains `edge-command-workbench:rk3576-0.1.0`. |
| RKNN library error | Check `/usr/lib/librknnrt.so` on the target and keep the read-only compose mount available. |
| Port 18768 is busy | Stop the service using the port, then retry after checking its ownership. |
| Dashboard does not open | Check the target IP and confirm `docker compose ps` reports the workbench container as healthy. |

## Step 2: Open the Workbench {#verify type=web_dashboard required=true config=devices/dashboard.yaml}

Open the deployed web workbench and submit a request with candidate commands. A healthy page and a JSON decision response verify that the container, model mount, tokenizer mount, and RKNN backend are reachable.

### Deployment Complete

#### HTTP check

Open `http://<device-ip>:18768/api/health` and confirm the service reports healthy. The main decision endpoint is `POST /api/decide` on port `18768`.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Health check is not ready | Wait for the model to load, then inspect `docker logs edge-command-workbench`. |
| Voice button is unavailable | Leave voice disabled or provide an existing compatible `VOICE_SERVICE_URL`; this preset does not install ASR. |

## Preset: RK3576 Kev RKLLM {#rk3576_rkllm_remote}

This preset deploys the tested Kev RKLLM path on cat-remote RK3576. The engine export capacity is 8192 tokens, while the deployment guard and metadata limit requests to 2048 tokens because the 8K configuration caused global OOM on that device. The package records the runtime, engine, head, tokenizer, and metadata as separate pinned artifacts.

## Step 1: Deploy the Kev Workbench {#deploy_rk3576_rkllm type=docker_remote required=true config=devices/rk3576_rkllm_remote.yaml}

The container selects `DECISION_BACKEND=rkllm` and `MODEL_ID=kev`. Supply a complete model directory containing `model.rkllm`, `kev_head.npz`, `tokenizer/tokenizer.json`, and the pinned runtime at `runtime/librkllmrt.so`. The image contains the C helper only when built with the pinned RKLLM 1.3.1 headers.

### Target {#rk3576_rkllm type=remote device_name="RK3576" config=devices/rk3576_rkllm_remote.yaml default=true}

Enter SSH credentials. Keep at least 3GB free for the RKLLM bootstrap; the measured fresh artifact peak is about 1.94GB with a 1GB reserve. The optional `MODEL_SERVICES_JSON` maps another model family to an already running HTTP service; the local Kev model remains the only model loaded by this container. `VOICE_SERVICE_URL` connects an existing compatible voice service and does not install ASR.

### Deployment Complete

Open `http://<device-ip>:18768`. Verification requires `/api/health` to report `model_ready: true`, `backend: "rkllm"`, and `model_id: "kev"`.

## Step 2: Open the Kev Workbench {#verify_rk3576_rkllm type=web_dashboard required=true config=devices/dashboard_rk3576_rkllm.yaml}

Submit a request with candidate commands after the health check reports a ready Kev model.

## Preset: RK3588 Kev RKLLM {#rk3588_rkllm_remote}

This preset deploys the tested 8K Kev artifact contract on Radxa RK3588. The verified deployment context is 8192 tokens; the result applies to the tested device and does not generalize to other boards with different free memory.

## Step 1: Deploy the Kev Workbench {#deploy_rk3588_rkllm type=docker_remote required=true config=devices/rk3588_rkllm_remote.yaml}

Provide the pinned engine, FP32 Q/K head, tokenizer, metadata, and RKLLM runtime directory for the target. The service does not download model weights at startup.

### Target {#rk3588_rkllm type=remote device_name="RK3588" config=devices/rk3588_rkllm_remote.yaml default=true}

Optional remote model profiles and an existing voice service can be configured through the deployment fields.

### Deployment Complete

Open `http://<device-ip>:18768` and confirm the model-ready health response before sending a decision request.

## Step 2: Open the Kev Workbench {#verify_rk3588_rkllm type=web_dashboard required=true config=devices/dashboard_rk3588_rkllm.yaml}

Submit a request with candidate commands after the health check reports a ready Kev model.

### Published artifact record

The published artifact set is pinned to Hugging Face revision [`a556792cc663c0d9cfa7095e4263d3d706b4e254`](https://huggingface.co/harvestsu/laya-multilingual-rknn-tensorrt/commit/a556792cc663c0d9cfa7095e4263d3d706b4e254) under `releases/edge-workbench-0.3.0`. The image archive is the verified d870 candidate. The 16-file list, sizes, SHA256 values, and remote verification record are in [`assets/evidence/hf-release-20261011.json`](assets/evidence/hf-release-20261011.json). A later UI source identified as `ef82` is not included in this image.

The recorded mirror check returned HTTP 308 to the Hugging Face origin; the evidence does not claim a mirror-native large-file download.
