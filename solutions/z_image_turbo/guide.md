## Preset: Deploy Image Generation Service {#jetson_image_gen}

Deploy Z-Image-Turbo as an HTTP API on your Jetson Orin NX for local text-to-image and img2img generation.

| Device | Purpose |
|--------|---------|
| NVIDIA Jetson Orin NX (16GB) | Runs Z-Image-Turbo 6B model with TensorRT BF16 acceleration |

**What you'll get:**
- One-click deployment — remote via SSH or directly on the Jetson
- HTTP API at port 8000 for text-to-image and img2img
- Fully offline — no cloud dependency
- 512px generation in ~100s, 384px in ~73s

**Requirements:** Jetson Orin NX 16GB with JetPack 6, NVIDIA Docker runtime, internet access (model weights and TRT engines are auto-downloaded from HuggingFace on first deploy; falls back to hf-mirror.com if huggingface.co is blocked).

## Step 1: Deploy Image Generation Service {#deploy_service type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy the Z-Image-Turbo API container to your Jetson.

### Target {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

Deploy to your Jetson Orin NX over SSH with one click.

### Wiring

1. Ensure Jetson is on the same network and SSH is enabled
2. Fill in Jetson IP, SSH credentials, model root path, and output directory
3. Click **Deploy** — model weights and TRT engines for the chosen resolution are downloaded automatically on first run

### Deployment Complete

1. The Z-Image-Turbo API is running on your Jetson at port 8000
2. Health check available at `http://<jetson-ip>:8000/health`
3. Generated images are saved to the output directory

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP, username, password, and that SSH service is running on Jetson |
| Docker not found | Install Docker and NVIDIA Container Toolkit on Jetson |
| HuggingFace download fails | The script auto-falls back to `hf-mirror.com`; if both are blocked, configure a proxy on the Jetson or pre-populate `$MODEL_ROOT` manually |
| Download interrupted | Re-run deploy — partial files (`.part`) are discarded and only missing files are re-fetched |
| API not responding | Check container logs: `docker logs z-image-api` |
| Docker permission denied | Run `sudo usermod -aG docker <user>` and re-login |
| OOM during generation | The container auto-configures cache layers based on resolution (18 for 512, 23 for 384) |

### Target {#jetson_local type=local config=devices/jetson_deploy.yaml}

Deploy directly on your Jetson (keyboard and monitor connected).

### Wiring

1. Ensure Docker and NVIDIA Container Toolkit are installed on the Jetson
2. Click **Deploy** — model weights and TRT engines for the chosen resolution are downloaded automatically on first run

### Deployment Complete

1. The Z-Image-Turbo API is running on this device at port 8000
2. Health check available at `http://localhost:8000/health`
3. Generated images are saved to the output directory

### Troubleshooting

| Issue | Solution |
|-------|----------|
| NVIDIA runtime not found | Install NVIDIA Container Toolkit: `sudo apt install nvidia-container-toolkit && sudo systemctl restart docker` |
| HuggingFace download fails | The script auto-falls back to `hf-mirror.com`; if both are blocked, configure a proxy or pre-populate `$MODEL_ROOT` manually |
| Download interrupted | Re-run deploy — partial files (`.part`) are discarded and only missing files are re-fetched |
| API not responding | Check container logs: `docker logs z-image-api` |
| Port 8000 already in use | Stop other services using port 8000 |

## Step 2: Generate Images {#verify_api type=image_text_to_image required=false config=devices/verify_api.yaml}

Type a prompt to generate an image. Each generation takes 1-2 minutes. The generated image appears directly in the verification panel.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Health check fails | Verify the Jetson is reachable and port 8000 is not blocked by firewall |
| Generate returns error | Check container logs: `docker logs z-image-api` |
| Request timeout | Generation takes 1-2 minutes. Increase HTTP client timeout to 180s |
### Deployment Complete

Z-Image-Turbo has been deployed successfully on your Jetson.

#### API Reference

##### Health Check
```bash
curl http://<jetson-ip>:8000/health
```

##### Text-to-Image
```bash
curl -X POST http://<jetson-ip>:8000/generate_json -H 'Content-Type: application/json' -d '{"prompt": "A cute cat, photorealistic", "num_steps": 4}'
```

##### Image-to-Image
```bash
curl -X POST http://<jetson-ip>:8000/generate -F 'prompt=A cat wearing a red scarf' -F 'image=@/path/to/reference.png' -F 'num_steps=8' -F 'strength=0.65'
```

#### Validation Checklist

1. Health endpoint returns `{"success": true}`
2. Text-to-image generation returns image URL in response
3. Generated PNG files appear in the output directory
