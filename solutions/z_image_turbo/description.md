## What This Capability Does

Z-Image-Turbo turns text descriptions into photorealistic images on your Jetson Orin NX — no cloud, no subscription, no internet required. Send a text prompt, get back a PNG. Upload a reference image with a prompt, and it edits the image intelligently.

All computation stays on your device. The model is packaged as a simple HTTP API you can call from any application.

## Integration Scenarios

| Scenario | How to integrate |
|----------|-----------------|
| Creative tools and applications | Call the API from your web app, desktop tool, or automation pipeline to add on-device image generation |
| Privacy-sensitive workflows | Run generation in healthcare, legal, or enterprise environments where images cannot leave the device |
| Interactive installations | Power offline image generation in kiosks, photo booths, or art installations without cloud dependency |
| Model research and benchmarking | Use as a local 6B-parameter diffusion transformer for latency measurement and pipeline experimentation |

## Technical Specs

| Spec | Value |
|------|-------|
| Model | Z-Image-Turbo (6B parameters) |
| Hardware | Jetson Orin NX 16GB, JetPack 6 |
| Runtime | TensorRT BF16, no PyTorch |
| 384px text-to-image | ~73 seconds (4 steps) |
| 512px text-to-image | ~100 seconds (4 steps) |
| Max cached layers | 18 (512px) / 23 (384px) |
| API concurrency | 1 request at a time (queued) |
| Docker image size | ~428 MB |

## Usage Notes

- **Hardware required**: Jetson Orin NX 16GB. Orin Nano 8GB is not validated.
- **Pre-requisites**: Model weights (~20GB) and TRT engines (~12GB per resolution) must be downloaded from Hugging Face before deployment.
- **Generation is not real-time**: Each image takes 1-2 minutes depending on resolution and step count.
- **API is single-worker**: Only one generation runs at a time to stay within GPU memory limits.
