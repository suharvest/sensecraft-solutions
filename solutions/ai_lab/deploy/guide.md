## Preset: Object Detection {#object_detection}

Deploy YOLO 11 object detection to your reComputer RK3576 or RK3588 with one click.

| Device | Purpose |
|--------|---------|
| reComputer RK3576 / RK3588 | Runs YOLO 11 with RKNN NPU acceleration |
| USB Camera (optional) | Real-time video detection input |

**What you'll get:**
- YOLO 11 detection API running locally on your device
- Choose from 3 model sizes: Nano (fastest), Small (balanced), Medium (most accurate)
- REST API for image/video detection + MJPEG live video feed
- Supports 80 COCO object classes out of the box

**Requirements:** RK3576 or RK3588 device with SSH access + Docker installed

## Step 1: Deploy YOLO 11 {#cv_deploy type=docker_deploy required=true config=devices/cv_rk3576_deploy.yaml}

Deploy the object detection container to your RK35xx device.

### Target {#cv_rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/cv_rk3576_deploy.yaml default=true}

Deploy to your RK3576 over SSH with one click.

### Wiring

1. Connect RK3576 to the same network as your computer
2. Plug in USB camera if you want real-time video detection
3. Select the model size (Nano recommended for beginners)
4. Fill in device IP, SSH username, and password
5. Click **Deploy**

### Deployment Complete

1. The YOLO container is running on your RK3576
2. Detection API: `http://<device-ip>:8000/api/models/yolo11/predict`
3. Live video feed: `http://<device-ip>:8000/api/video_feed` (requires camera)
4. Web preview: `http://<device-ip>:8000` (if available)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP address, username, password |
| NPU not detected | Ensure device is RK3576 with RKNPU kernel module loaded |
| No camera detected | Check USB camera is connected. Detection still works with image upload API |
| Image pull slow | Check network connection. Image is about 1-2GB |

### Target {#cv_rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/cv_rk3588_deploy.yaml}

Deploy to your RK3588 device (reComputer / ROCK 5T) over SSH.

### Wiring

1. Connect RK3588 to the same network as your computer
2. Plug in USB camera if you want real-time video detection
3. Select the model size (Nano recommended for beginners)
4. Fill in device IP, SSH username, and password
5. Click **Deploy**

### Deployment Complete

1. The YOLO container is running on your RK3588
2. Detection API: `http://<device-ip>:8000/api/models/yolo11/predict`
3. Live video feed: `http://<device-ip>:8000/api/video_feed` (requires camera)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP address, username, password |
| RK3588 platform not detected | Ensure device is RK3588-based (reComputer / ROCK 5T) |
| No camera detected | Check USB camera is connected. Detection still works with image upload API |
| Image pull slow | Check network connection. Image is about 1-2GB |

### Target {#cv_rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/cv_rk3576_deploy.yaml}

Deploy directly on the current machine (requires RK3576 device).

### Wiring

1. Ensure Docker is installed on the current machine
2. Click **Deploy** to start installation

> **Note:** First startup may take 5-10 minutes for Docker image download and model initialization.

### Deployment Complete

1. Open **http://localhost:8000** in your browser
2. You'll see the YOLO detection service running

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not installed | Install Docker: `curl -fsSL https://get.docker.com | sudo sh` |
| Port 8000 already in use | Stop existing services on that port |
| Container keeps restarting | Check logs: `docker logs ai_lab_cv` |

### Target {#cv_rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/cv_rk3588_deploy.yaml}

Deploy directly on the current machine (requires RK3588 device).

### Wiring

1. Ensure Docker is installed on the current machine
2. Click **Deploy** to start installation

> **Note:** First startup may take 5-10 minutes for Docker image download and model initialization.

### Deployment Complete

1. Open **http://localhost:8000** in your browser
2. You'll see the YOLO detection service running

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not installed | Install Docker: `curl -fsSL https://get.docker.com | sudo sh` |
| Port 8000 already in use | Stop existing services on that port |
| Container keeps restarting | Check logs: `docker logs ai_lab_cv` |


## Step 2: Try Detection {#cv_verify type=image_predict}

Verify the detection service is working.

### Mode: Image Detection {#cv_image_mode config=devices/cv_image.yaml default=true}
Upload an image to test object detection.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| No detections | Try an image with people or vehicles |
| Connection refused | Wait 15-30 seconds for service to start |

### Mode: Live Video {#cv_video_mode config=devices/cv_stream.yaml}
View live camera feed with detection bounding boxes (requires USB camera).

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Black screen | Check USB camera is connected |
| No video feed | Verify MJPEG URL is correct |
### Deployment Complete

Your AI Lab is running. The endpoint you reach depends on which preset you deployed:

| Preset | API base | Quick test |
|--------|----------|-----------|
| Object Detection | `http://<device-ip>:8000` | `curl -X POST .../api/models/yolo11/predict -F "file=@photo.jpg"` |
| LLM Chat | `http://<device-ip>:8001` | `curl .../v1/chat/completions -d '{"messages":[{"role":"user","content":"Hello"}]}'` |
| Vision Chat | `http://<device-ip>:8002` | Open `/docs` for interactive testing |

#### Object Detection — Image Upload

```bash
curl -X POST http://<device-ip>:8000/api/models/yolo11/predict \
  -F "file=@photo.jpg" \
  -F "conf=0.5"
```

#### Object Detection — Live Video Feed

Open in browser: `http://<device-ip>:8000/api/video_feed`

#### LLM Chat — Quick Call

```bash
curl http://<device-ip>:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "rkllm-model", "messages": [{"role": "user", "content": "Hello!"}], "max_tokens": 256}'
```

#### Vision Chat — Image + Question

```bash
curl -X POST http://<device-ip>:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rkllm-vision",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}}
      ]
    }],
    "max_tokens": 256
  }'
```

#### Python (OpenAI client) — works for LLM Chat and Vision Chat

```python
import openai
client = openai.OpenAI(base_url="http://<device-ip>:8001/v1", api_key="dummy")
response = client.chat.completions.create(
    model="rkllm-model",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=256
)
print(response.choices[0].message.content)
```

## Preset: LLM Chat {#llm_chat}

Deploy DeepSeek-R1 large language model to your reComputer RK3576 with one click.

| Device | Purpose |
|--------|---------|
| reComputer RK3576 | Runs DeepSeek-R1 LLM with NPU acceleration |

**What you'll get:**
- OpenAI-compatible chat API running locally on your device
- Choose from 5 model variants (1.5B/7B, different quantizations)
- No cloud dependency — all inference runs on-device

**Requirements:** RK3576 device with SSH access + Docker installed

## Step 1: Deploy DeepSeek-R1 {#llm_deploy type=docker_deploy required=true config=devices/llm_rk3576_deploy.yaml}

Deploy the LLM container to your RK3576 device.

### Target {#llm_rk3576_remote type=remote config=devices/llm_rk3576_deploy.yaml default=true}

Deploy to your RK3576 over SSH with one click.

### Wiring

1. Connect RK3576 to the same network as your computer
2. Select the model variant you want to run
3. Fill in device IP, SSH username, and password
4. Click **Deploy**

### Deployment Complete

1. The LLM container is running on your RK3576
2. Chat API is available at `http://<device-ip>:8001/v1/chat/completions`
3. Use any OpenAI-compatible client to connect

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP address, username, password |
| NPU not detected | Ensure device is RK3576 with RKNPU kernel module loaded |
| Out of memory (7B model) | 7B variants require 8GB+ RAM. Try a 1.5B variant instead |
| Image pull slow | Check network connection. Image size is 1-4GB depending on variant |

### Target {#llm_rk3576_local type=local config=devices/llm_rk3576_deploy.yaml}

Deploy directly on the current machine (requires RK3576 device).

### Wiring

1. Ensure Docker is installed on the current machine
2. Click **Deploy** to start installation

> **Note:** First startup may take 10-20 minutes for Docker image download and LLM model initialization.

### Deployment Complete

1. Chat API is available at `http://localhost:8001/v1/chat/completions`
2. Use any OpenAI-compatible client to interact with the model

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not installed | Install Docker: `curl -fsSL https://get.docker.com \| sudo sh` |
| Port 8001 already in use | Stop existing services on that port |
| NPU not detected | Ensure device is RK3576 with RKNPU kernel module loaded |
| Container keeps restarting | Check logs: `docker logs ai_lab_llm` |
| Insufficient memory | LLM models require at least 8GB RAM |


## Step 2: Try Chat {#llm_verify type=text_chat required=false config=devices/llm_chat.yaml}

Test the LLM by sending a message.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Connection refused | Wait 30-60 seconds for model to load |
| Timeout | 7B models take longer. Wait up to 2 minutes |
| Empty response | Check container logs: `docker logs ai_lab_llm` |
### Deployment Complete

Your AI Lab is running. The endpoint you reach depends on which preset you deployed:

| Preset | API base | Quick test |
|--------|----------|-----------|
| Object Detection | `http://<device-ip>:8000` | `curl -X POST .../api/models/yolo11/predict -F "file=@photo.jpg"` |
| LLM Chat | `http://<device-ip>:8001` | `curl .../v1/chat/completions -d '{"messages":[{"role":"user","content":"Hello"}]}'` |
| Vision Chat | `http://<device-ip>:8002` | Open `/docs` for interactive testing |

#### Object Detection — Image Upload

```bash
curl -X POST http://<device-ip>:8000/api/models/yolo11/predict \
  -F "file=@photo.jpg" \
  -F "conf=0.5"
```

#### Object Detection — Live Video Feed

Open in browser: `http://<device-ip>:8000/api/video_feed`

#### LLM Chat — Quick Call

```bash
curl http://<device-ip>:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "rkllm-model", "messages": [{"role": "user", "content": "Hello!"}], "max_tokens": 256}'
```

#### Vision Chat — Image + Question

```bash
curl -X POST http://<device-ip>:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rkllm-vision",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}}
      ]
    }],
    "max_tokens": 256
  }'
```

#### Python (OpenAI client) — works for LLM Chat and Vision Chat

```python
import openai
client = openai.OpenAI(base_url="http://<device-ip>:8001/v1", api_key="dummy")
response = client.chat.completions.create(
    model="rkllm-model",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=256
)
print(response.choices[0].message.content)
```

## Preset: Vision Chat {#vlm_chat}

Deploy Qwen2.5-VL vision-language model to your reComputer RK3576 with one click.

| Device | Purpose |
|--------|---------|
| reComputer RK3576 | Runs Qwen2.5-VL with NPU acceleration |

**What you'll get:**
- Multimodal AI that understands both images and text
- OpenAI-compatible vision API running locally
- Image captioning, visual Q&A, and more — all on-device
- Interactive API documentation at `/docs`

**Requirements:** RK3576 device (8GB+ RAM) with SSH access + Docker installed

## Step 1: Deploy Qwen2.5-VL {#vlm_deploy type=docker_deploy required=true config=devices/vlm_rk3576_deploy.yaml}

Deploy the vision-language model container to your RK3576 device.

### Target {#vlm_rk3576_remote type=remote config=devices/vlm_rk3576_deploy.yaml default=true}

Deploy to your RK3576 over SSH with one click.

### Wiring

1. Connect RK3576 to the same network as your computer
2. Fill in device IP, SSH username, and password
3. Click **Deploy**

### Deployment Complete

1. The VLM container is running on your RK3576
2. Vision chat API: `http://<device-ip>:8002/v1/chat/completions`
3. API docs: `http://<device-ip>:8002/docs`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify IP address, username, password |
| NPU not detected | Ensure device is RK3576 with RKNPU kernel module loaded |
| Out of memory | VLM requires 8GB+ RAM. Close other services to free memory |
| Image pull slow | Check network connection. Image is about 3GB |

### Target {#vlm_rk3576_local type=local config=devices/vlm_rk3576_deploy.yaml}

Deploy directly on the current machine (requires RK3576 device).

### Wiring

1. Ensure Docker is installed on the current machine
2. Click **Deploy** to start installation

> **Note:** First startup may take 10-20 minutes for Docker image download and VLM model initialization.

### Deployment Complete

1. Open **http://localhost:8002** in your browser
2. You'll see the vision-language chat interface ready for interaction

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not installed | Install Docker: `curl -fsSL https://get.docker.com | sudo sh` |
| Port 8002 already in use | Stop existing services on that port |
| Container keeps restarting | Check logs: `docker logs ai_lab_vlm` |
| Insufficient memory | VLM models require at least 8GB RAM |

## Step 2: Try Vision Chat {#vlm_verify type=image_text_chat}

Test the VLM by sending an image or text.

### Mode: Image Understanding {#vlm_vision_mode config=devices/vlm_chat.yaml default=true}
Upload an image and ask a question about it.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Connection refused | Wait 60-120 seconds for model to load |
| Timeout | VLM model is large, initial load takes time |

### Mode: Text Chat {#vlm_text_mode config=devices/vlm_text.yaml}
Chat with the model using text only.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Empty response | Check container logs: `docker logs ai_lab_vlm` |
### Deployment Complete

Your AI Lab is running. The endpoint you reach depends on which preset you deployed:

| Preset | API base | Quick test |
|--------|----------|-----------|
| Object Detection | `http://<device-ip>:8000` | `curl -X POST .../api/models/yolo11/predict -F "file=@photo.jpg"` |
| LLM Chat | `http://<device-ip>:8001` | `curl .../v1/chat/completions -d '{"messages":[{"role":"user","content":"Hello"}]}'` |
| Vision Chat | `http://<device-ip>:8002` | Open `/docs` for interactive testing |

#### Object Detection — Image Upload

```bash
curl -X POST http://<device-ip>:8000/api/models/yolo11/predict \
  -F "file=@photo.jpg" \
  -F "conf=0.5"
```

#### Object Detection — Live Video Feed

Open in browser: `http://<device-ip>:8000/api/video_feed`

#### LLM Chat — Quick Call

```bash
curl http://<device-ip>:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "rkllm-model", "messages": [{"role": "user", "content": "Hello!"}], "max_tokens": 256}'
```

#### Vision Chat — Image + Question

```bash
curl -X POST http://<device-ip>:8002/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "rkllm-vision",
    "messages": [{
      "role": "user",
      "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "https://example.com/photo.jpg"}}
      ]
    }],
    "max_tokens": 256
  }'
```

#### Python (OpenAI client) — works for LLM Chat and Vision Chat

```python
import openai
client = openai.OpenAI(base_url="http://<device-ip>:8001/v1", api_key="dummy")
response = client.chat.completions.create(
    model="rkllm-model",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=256
)
print(response.choices[0].message.content)
```
