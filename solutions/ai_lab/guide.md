## Preset: Object Detection {#object_detection}

Deploy YOLO 11 object detection to a reComputer RK3576 or RK3588, with an image detection REST API and an MJPEG live video feed covering the 80 COCO object classes.

- **Devices:** reComputer RK3576 or RK3588; a USB camera for live video detection (optional).
- **Software:** Docker installed on the device, reachable over SSH.
- **Models:** choose Nano, Small or Medium at deployment.

## Step 1: Deploy YOLO 11 {#cv_deploy type=docker_deploy required=true config=devices/cv_rk3576_deploy.yaml}

Deploy the object detection container to the device.

### Target {#cv_rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/cv_rk3576_deploy.yaml default=true}

Deploy to the RK3576 over SSH.

### Wiring

1. Connect the RK3576 to the same network as your computer
2. Plug in a USB camera for live video detection
3. Select the model size (start with Nano)
4. Fill in device IP, SSH username, and password
5. Click **Deploy**

### Deployment Complete

1. Detection API: `http://<device-ip>:8000/api/models/yolo11/predict`
2. Live video feed: `http://<device-ip>:8000/api/video_feed` (requires camera)

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| SSH connection failed | Verify IP address, username, password |
| NPU not detected | Ensure device is RK3576 with RKNPU kernel module loaded |
| No camera detected | Check USB camera is connected. Detection still works with image upload API |
| Image pull slow | Check the network. Image is about 1-2GB |

### Target {#cv_rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/cv_rk3588_deploy.yaml}

Deploy to a reComputer RK3588 series device over SSH.

### Wiring

1. Connect the RK3588 to the same network as your computer
2. Plug in a USB camera for live video detection
3. Select the model size (start with Nano)
4. Fill in device IP, SSH username, and password
5. Click **Deploy**

### Deployment Complete

1. Detection API: `http://<device-ip>:8000/api/models/yolo11/predict`
2. Live video feed: `http://<device-ip>:8000/api/video_feed` (requires camera)

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| SSH connection failed | Verify IP address, username, password |
| RK3588 platform not detected | Ensure device is a reComputer RK3588 series unit |
| No camera detected | Check USB camera is connected. Detection still works with image upload API |
| Image pull slow | Check the network. Image is about 1-2GB |

### Target {#cv_rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/cv_rk3576_deploy.yaml}

Deploy on this machine. It must be an RK3576 device with Docker installed. First startup takes 5-10 minutes.

### Wiring

1. Confirm Docker is installed
2. Click **Deploy**

### Deployment Complete

Open **http://localhost:8000**; the detection service is running.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Docker not installed | Install Docker: `curl -fsSL https://get.docker.com \| sudo sh` |
| Port 8000 already in use | Stop existing services on that port |
| Container keeps restarting | Run `docker logs ai_lab_cv` |

### Target {#cv_rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/cv_rk3588_deploy.yaml}

Deploy on this machine. It must be an RK3588 device with Docker installed. First startup takes 5-10 minutes.

### Wiring

1. Confirm Docker is installed
2. Click **Deploy**

### Deployment Complete

Open **http://localhost:8000**; the detection service is running.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Docker not installed | Install Docker: `curl -fsSL https://get.docker.com \| sudo sh` |
| Port 8000 already in use | Stop existing services on that port |
| Container keeps restarting | Run `docker logs ai_lab_cv` |


## Step 2: Try Detection {#cv_verify type=image_predict}

Verify the detection service is working.

### Mode: Image Detection {#cv_image_mode config=devices/cv_image.yaml default=true}
Upload an image to test object detection.

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| No detections | Use an image with people or vehicles |
| Connection refused | Wait 15-30 seconds for service to start |

### Mode: Live Video {#cv_video_mode config=devices/cv_stream.yaml}
View live camera feed with detection bounding boxes (requires USB camera).

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| Black screen | Check USB camera is connected |
| No video feed | Verify MJPEG URL is correct |
### Deployment Complete

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

Deploy the DeepSeek-R1 large language model to a reComputer RK3576, with an OpenAI-compatible chat API running on the device.

- **Devices:** reComputer RK3576; 7B variants need 8GB+ RAM.
- **Software:** Docker installed on the device, reachable over SSH.
- **Models:** choose from 5 variants (1.5B/7B, different quantizations) at deployment.

## Step 1: Deploy DeepSeek-R1 {#llm_deploy type=docker_deploy required=true config=devices/llm_rk3576_deploy.yaml}

Deploy the LLM container to the RK3576.

### Target {#llm_rk3576_remote type=remote config=devices/llm_rk3576_deploy.yaml default=true}

Deploy to the RK3576 over SSH.

### Wiring

1. Connect the RK3576 to the same network as your computer
2. Select the model variant
3. Fill in device IP, SSH username, and password
4. Click **Deploy**

### Deployment Complete

Chat API: `http://<device-ip>:8001/v1/chat/completions`. Connect with any OpenAI-compatible client.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| SSH connection failed | Verify IP address, username, password |
| NPU not detected | Ensure device is RK3576 with RKNPU kernel module loaded |
| Out of memory (7B model) | 7B variants require 8GB+ RAM. Try a 1.5B variant instead |
| Image pull slow | Check the network. Image size is 1-4GB depending on variant |

### Target {#llm_rk3576_local type=local config=devices/llm_rk3576_deploy.yaml}

Deploy on this machine. It must be an RK3576 device with Docker installed. First startup takes 10-20 minutes.

### Wiring

1. Confirm Docker is installed
2. Click **Deploy**

### Deployment Complete

Chat API: `http://localhost:8001/v1/chat/completions`. Connect with any OpenAI-compatible client.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Docker not installed | Install Docker: `curl -fsSL https://get.docker.com \| sudo sh` |
| Port 8001 already in use | Stop existing services on that port |
| NPU not detected | Ensure device is RK3576 with RKNPU kernel module loaded |
| Container keeps restarting | Run `docker logs ai_lab_llm` |
| Insufficient memory | LLM models require at least 8GB RAM |


## Step 2: Try Chat {#llm_verify type=text_chat required=false config=devices/llm_chat.yaml}

Test the LLM by sending a message.

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| Connection refused | Wait 30-60 seconds for model to load |
| Timeout | 7B models take longer. Wait up to 2 minutes |
| Empty response | Check container logs: `docker logs ai_lab_llm` |
### Deployment Complete

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

Deploy the Qwen2.5-VL vision-language model to a reComputer RK3576, with an OpenAI-compatible vision API on the device for image captioning and visual Q&A.

- **Devices:** reComputer RK3576 with 8GB+ RAM.
- **Software:** Docker installed on the device, reachable over SSH.

## Step 1: Deploy Qwen2.5-VL {#vlm_deploy type=docker_deploy required=true config=devices/vlm_rk3576_deploy.yaml}

Deploy the vision-language model container to the RK3576.

### Target {#vlm_rk3576_remote type=remote config=devices/vlm_rk3576_deploy.yaml default=true}

Deploy to the RK3576 over SSH.

### Wiring

1. Connect the RK3576 to the same network as your computer
2. Fill in device IP, SSH username, and password
3. Click **Deploy**

### Deployment Complete

1. Vision chat API: `http://<device-ip>:8002/v1/chat/completions`
2. API docs: `http://<device-ip>:8002/docs`

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| SSH connection failed | Verify IP address, username, password |
| NPU not detected | Ensure device is RK3576 with RKNPU kernel module loaded |
| Out of memory | VLM requires 8GB+ RAM. Close other services to free memory |
| Image pull slow | Check the network. Image is about 3GB |

### Target {#vlm_rk3576_local type=local config=devices/vlm_rk3576_deploy.yaml}

Deploy on this machine. It must be an RK3576 device with Docker installed. First startup takes 10-20 minutes.

### Wiring

1. Confirm Docker is installed
2. Click **Deploy**

### Deployment Complete

Open **http://localhost:8002**; the vision chat interface is shown.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Docker not installed | Install Docker: `curl -fsSL https://get.docker.com \| sudo sh` |
| Port 8002 already in use | Stop existing services on that port |
| Container keeps restarting | Run `docker logs ai_lab_vlm` |
| Insufficient memory | VLM models require at least 8GB RAM |

## Step 2: Try Vision Chat {#vlm_verify type=image_text_chat}

Test the VLM by sending an image or text.

### Mode: Image Understanding {#vlm_vision_mode config=devices/vlm_chat.yaml default=true}
Upload an image and ask a question about it.

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| Connection refused | Wait 60-120 seconds for model to load |
| Timeout | VLM model is large, initial load takes time |

### Mode: Text Chat {#vlm_text_mode config=devices/vlm_text.yaml}
Chat with the model using text only.

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| Empty response | Check container logs: `docker logs ai_lab_vlm` |
### Deployment Complete

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
