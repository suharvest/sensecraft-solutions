---
name: prepare-docker-images
description: Prepare Docker images and compose files for solution deployment. Use when building container images, writing docker-compose.yml, configuring health checks, or setting up multi-container services.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Prepare Docker Images

Guide for preparing Docker images and deployment configuration.

## Required Deliverables

| Deliverable | Description | Location |
|-------------|-------------|----------|
| Docker images | Push to Docker Hub or private registry | Remote |
| docker-compose.yml | Service orchestration | `solutions/[id]/assets/docker/` |
| Device config | Deployment parameters | `solutions/[id]/devices/` |

## Directory Structure

```
solutions/[solution_id]/
├── solution.yaml              # Solution configuration
├── guide.md                   # English deployment guide (defines steps)
├── guide_zh.md                # Chinese deployment guide
├── gallery/                   # Images
│   └── architecture.png
├── assets/
│   └── docker/
│       └── docker-compose.yml
└── devices/
    └── [device_id].yaml       # Device config
```

## Image Naming Convention

```
[org]/[project]-[service]:version

Examples:
seeedstudio/warehouse-backend:latest
seeedstudio/warehouse-frontend:latest
seeedstudio/mcp-bridge:v1.0.0
```

## docker-compose.yml Template

```yaml
version: "3.8"

services:
  backend:
    image: seeedstudio/warehouse-backend:latest
    container_name: warehouse-backend
    restart: unless-stopped
    ports:
      - "2124:2124"
    volumes:
      - warehouse_data:/data
    environment:
      - DB_PATH=/data
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2124/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  frontend:
    image: seeedstudio/warehouse-frontend:latest
    container_name: warehouse-frontend
    restart: unless-stopped
    ports:
      - "2125:80"
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  warehouse_data:
    driver: local
```

## Device Configuration Template

Create `devices/[device_id].yaml`:

```yaml
version: "1.0"
id: recomputer
name: Local Docker Deployment
name_zh: 本地 Docker 部署
type: docker_local

detection:
  method: local
  requirements:
    - docker_installed
    - docker_running
    - docker_compose_installed

docker:
  compose_file: assets/docker/docker-compose.yml

  environment:
    DB_PATH: /opt/provisioning-station/data/warehouse
    LOG_LEVEL: INFO

  options:
    project_name: my_project
    remove_orphans: true
    build: false

  services:
    - name: backend
      port: 2124
      health_check_endpoint: /api/health
      required: true
    - name: frontend
      port: 2125
      health_check_endpoint: /
      required: true

  images:
    - name: seeedstudio/warehouse-backend:latest
      required: true
    - name: seeedstudio/warehouse-frontend:latest
      required: true

pre_checks:
  - type: docker_version
    min_version: "20.0"
  - type: port_available
    ports: [2124, 2125]
  - type: disk_space
    min_gb: 2

steps:
  - id: pull_images
    name: Pull Docker Images
    name_zh: 拉取 Docker 镜像
  - id: create_volumes
    name: Create Data Volumes
    name_zh: 创建数据卷
  - id: start_services
    name: Start Services
    name_zh: 启动服务
  - id: health_check
    name: Health Check
    name_zh: 健康检查

post_deployment:
  open_browser: true
  url: "http://localhost:2125"
```

## Build and Push Images

### Backend (Python/FastAPI)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 2124
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "2124"]
```

```bash
docker build -t seeedstudio/warehouse-backend:latest ./backend
docker push seeedstudio/warehouse-backend:latest
```

### Frontend (Nginx)

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 80
```

```bash
docker build -t seeedstudio/warehouse-frontend:latest ./frontend
docker push seeedstudio/warehouse-frontend:latest
```

### Multi-arch Build (amd64 + arm64)

```bash
docker buildx create --name mybuilder --use
docker buildx build --platform linux/amd64,linux/arm64 \
  -t seeedstudio/warehouse-backend:latest --push ./backend
```

## Health Check Endpoint

Backend must provide health endpoint:

```python
@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
```

## Update guide.md

Add deployment step in `guide.md`:

```markdown
## Step 1: Deploy Backend Services {#backend type=docker_deploy required=true config=devices/recomputer.yaml}

Deploy the backend services using Docker.

### Target: Local Deployment {#backend_local type=local config=devices/recomputer.yaml default=true}

![Architecture](gallery/architecture.png)

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 2124 busy | Stop other services using this port |
| Docker not found | Install Docker Desktop |

### Target: Remote Deployment {#backend_remote type=remote config=devices/warehouse_remote.yaml}

1. Connect target device to network
2. Enter IP address and SSH credentials
3. Click Deploy to install on remote device

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Check IP address and credentials |
| Timeout | Ensure target device is online |
```

> **Note**: Device step configuration is now defined in `guide.md` / `guide_zh.md` using markdown format. The `config_file` path points to the device YAML configuration.

## 镜像源自动加速 (Mirror Resolver)

写 compose 时**不要硬编码 mirror 前缀**。这一层由部署时的 mirror_resolver 自动处理。

- ✅ 推荐：`image: influxdb:2.7`、`image: grafana/grafana:latest`、`image: nvcr.io/nvidia/l4t-base:r36.2.0`
- ❌ 错误：`image: docker.m.daocloud.io/influxdb:2.7`（重复前缀会破坏海外设备部署）
- ❌ 错误：`image: ghcr.io/seeed/foo` 这种公共 GHCR 镜像目前**不被 daocloud 镜像**，部署到 CN 设备可能拉不下来；自建产物建议推 Docker Hub

**私有 registry 识别规则**（自动跳过重写）：image 名含 `/`，且第一段（registry host 段）含 `.` 或 `:`。

| Image | 是否被识别为私有 | 部署行为 |
|-------|----------------|---------|
| `nginx:latest` | ❌ 公共 | 加 `docker.m.daocloud.io/` 前缀 |
| `seeedstudio/foo:1` | ❌ 公共 | 加 `docker.m.daocloud.io/` 前缀 |
| `nvcr.io/nvidia/l4t-base:r36.2.0` | ✅ 私有（含 `.`） | 直接拉取 |
| `192.168.1.1:5000/internal:v1` | ✅ 私有（含 `:`） | 直接拉取 |
| `my-registry/x` | ❌ 误判为公共 | 加 mirror 前缀（会失败） |

**坑**：私有 registry 必须用 FQDN 或带端口（含 `.` 或 `:`），裸主机名（如 `my-registry/foo`）会被错误地当作 Docker Hub 用户名加 mirror 前缀。

## Local Test

```bash
cd solutions/[id]/assets/docker
docker compose up -d
docker compose ps
curl http://localhost:2124/api/health
```
