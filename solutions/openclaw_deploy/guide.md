## Preset: OpenClaw AI Compute Gateway {#openclaw_basic}

Deploy OpenClaw AI messaging gateway, with optional local AI model powered by your device's GPU.

| Device | Purpose |
|--------|---------|
| reComputer Jetson | Runs OpenClaw gateway and local AI model with GPU acceleration |

**What you'll get:**
- AI chatbot gateway supporting 20+ messaging platforms
- Optional local AI model running on device GPU — no data leaves your network
- Web management interface for configuration

**Requirements:** Docker installed · Internet access (for first-time image download)

## Step 1: Deploy OpenClaw {#deploy_openclaw type=docker_deploy required=true config=devices/openclaw_deploy.yaml}

Deploy the OpenClaw AI gateway. If local AI model is enabled, it will be started and configured automatically.


### Deployment Complete

OpenClaw AI gateway is deployed. Follow the "Deployment Complete" instructions in the step above to log in, then start using it.

#### Try a Conversation

1. Click **Chat** in the left sidebar and send a message to verify AI is responding
2. If local AI model is enabled, it's already configured — no extra setup needed

#### Connect Messaging Platforms

1. Click **Channels** in the left sidebar to add your messaging platform (WeChat, Telegram, Discord, etc.)
2. Follow the on-screen instructions to authorize the platform
3. Send a test message through the connected platform

#### Next Steps

- [OpenClaw Documentation](https://github.com/nicepkg/openclaw)
- Add more AI providers in Settings > Models
- Connect additional messaging platforms

### Target {#local type=local config=devices/openclaw_deploy.yaml default=true}

Deploy on your reComputer Jetson device (running this software locally on the Jetson).

### Wiring

1. Ensure Docker is installed and running
2. Optionally check **Enable Local AI Model** and select a model
3. Click **Deploy** to start services

### Deployment Complete

1. Copy the **Gateway Token** shown in the deployment log
2. Open **http://localhost:18789** in your browser
3. Go to the **Overview** page (left sidebar → **Overview** under "Control")
4. In the **Gateway Access** section, paste the token into the **Gateway Token** field
5. Click **Connect** to authenticate
6. Connect your first messaging channel (WeChat, Telegram, Discord, etc.)
7. If local AI model is enabled, it's already configured — select it when creating an agent

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 18789 already in use | Stop the service occupying port 18789, or check if OpenClaw is already running |
| Docker not found | Install Docker Desktop and ensure it is running |
| Model download slow | Large models take time; check your internet connection |
| OpenClaw container keeps restarting | Check logs: `docker logs openclaw-gateway` |

### Target {#jetson_remote type=remote config=devices/openclaw_deploy.yaml}

Deploy to a reComputer Jetson device over SSH, with GPU-accelerated local AI model.

### Wiring

1. Connect reComputer Jetson to the same network as your deployment machine
2. Enter Jetson IP address, SSH username, and password
3. Optionally check **Enable Local AI Model** and select a model
4. Click **Deploy** to start services

> Resource requirements: OpenClaw only needs 12GB disk + 4GB RAM; with Ollama needs 20GB disk + 8GB RAM.

### Deployment Complete

1. Copy the **Gateway Token** shown in the deployment log
2. OpenClaw requires localhost access. **Option A**: Connect a display to the Jetson, open a browser, and visit `http://localhost:18789`; **Option B**: On your computer, run `ssh -L 18789:localhost:18789 <username>@<jetson-ip>`, then open `http://localhost:18789` in your local browser
3. Go to the **Overview** page (left sidebar → **Overview** under "Control")
4. In the **Gateway Access** section, paste the token into the **Gateway Token** field
5. Click **Connect** to authenticate
6. Connect your first messaging channel
7. If local AI model is enabled, it's already configured with GPU acceleration — select it when creating an agent

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify Jetson IP, username, password, and that SSH service is running |
| NVIDIA runtime not detected | Ensure NVIDIA container runtime is installed: `nvidia-smi` should work |
| Docker Compose unavailable | Install it: `sudo apt-get install -y docker-compose-plugin` |
| Model download slow | First download gets the full model; subsequent runs use cache |
| Not enough disk space | OpenClaw only needs at least 12GB free disk; enabling Ollama raises that to 20GB. Check with `df -h /` |
| Not enough system memory | OpenClaw only needs at least 4GB RAM; enabling Ollama raises that to 8GB. Check with `awk '/^MemTotal:/ {print int(($2 + 1048575) / 1048576) "GB"}' /proc/meminfo` |
| Port 11434 already in use | The deployer prefers its own Docker-managed Ollama runtime. It will try to stop a native Ollama first; if the port is still occupied, stop the other Ollama service/process on the Jetson and retry |

## Preset: OpenClaw Gateway {#openclaw_recomputer_r}

Deploy OpenClaw AI messaging gateway on reComputer R series. Lightweight deployment — gateway only, no local AI model needed.

| Device | Purpose |
|--------|---------|
| reComputer R1100 / R2000 | Runs OpenClaw gateway services |

**What you'll get:**
- Chat with AI across 20+ messaging platforms (WeChat, Telegram, Discord, etc.)
- Manage all channels from a single web interface
- Connect cloud AI providers (OpenAI, Claude, etc.) for conversations

**Requirements:** Docker installed · Internet access (for first-time image download)

## Step 1: Deploy OpenClaw {#deploy_openclaw_r type=docker_deploy required=true config=devices/recomputer_r_deploy.yaml}

Deploy the OpenClaw AI gateway on your reComputer R.


### Deployment Complete

OpenClaw AI gateway is deployed. Follow the "Deployment Complete" instructions in the step above to log in, then start using it.

#### Try a Conversation

1. Click **Chat** in the left sidebar and send a message to verify AI is responding
2. If local AI model is enabled, it's already configured — no extra setup needed

#### Connect Messaging Platforms

1. Click **Channels** in the left sidebar to add your messaging platform (WeChat, Telegram, Discord, etc.)
2. Follow the on-screen instructions to authorize the platform
3. Send a test message through the connected platform

#### Next Steps

- [OpenClaw Documentation](https://github.com/nicepkg/openclaw)
- Add more AI providers in Settings > Models
- Connect additional messaging platforms

### Target {#r_local type=local config=devices/recomputer_r_deploy.yaml default=true}

Deploy on the machine you're currently using.

### Wiring

1. Ensure Docker is installed and running
2. Click **Deploy** to start services

### Deployment Complete

1. Copy the **Gateway Token** shown in the deployment log
2. Open **http://localhost:18789** in your browser
3. Go to the **Overview** page (left sidebar → **Overview** under "Control")
4. In the **Gateway Access** section, paste the token into the **Gateway Token** field
5. Click **Connect** to authenticate
6. Connect your first messaging channel (WeChat, Telegram, Discord, etc.)

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 18789 already in use | Stop the service occupying port 18789, or check if OpenClaw is already running |
| Docker not found | Install Docker Desktop and ensure it is running |
| OpenClaw container keeps restarting | Check logs: `docker logs openclaw-gateway` |

### Target {#r_remote type=remote config=devices/recomputer_r_deploy.yaml}

Deploy to a reComputer R device over SSH.

### Wiring

1. Connect reComputer R to the same network as your deployment machine
2. Enter device IP address, SSH username, and password
3. Click **Deploy** to start services

### Deployment Complete

1. Copy the **Gateway Token** shown in the deployment log
2. OpenClaw requires localhost access. **Option A**: Connect a display to the device, open a browser, and visit `http://localhost:18789`; **Option B**: On your computer, run `ssh -L 18789:localhost:18789 <username>@<device-ip>`, then open `http://localhost:18789` in your local browser
3. Go to the **Overview** page (left sidebar → **Overview** under "Control")
4. In the **Gateway Access** section, paste the token into the **Gateway Token** field
5. Click **Connect** to authenticate
6. Connect your first messaging channel

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Verify device IP, username, password, and that SSH service is running |
| Docker Compose unavailable | Install it: `sudo apt-get install -y docker-compose-plugin` |
| Not enough disk space | Need at least 4GB free; check with `df -h /` |
| OpenClaw container keeps restarting | Check logs: `docker logs openclaw-gateway` |
