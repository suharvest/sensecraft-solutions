## Preset: AI Camera Direct {#recamera}

reCamera detects people on the camera and publishes results over MQTT; a computer or reComputer R1100 runs the dashboard and keeps the history.

- **Devices:** reCamera; a computer or reComputer R1100 for the dashboard.
- **Software:** Docker on the dashboard machine, at least 2 GB free disk.
- **Network:** all devices on the same network.

## Step 1: Start Data Dashboard {#backend type=docker_deploy required=true config=devices/backend_deploy.yaml}

Start the MQTT broker, database, Grafana dashboard and video gateway. Every camera publishes here. Deployment discovers ONVIF cameras on the same subnet; if the backend and cameras are on different subnets, enter the camera addresses in the deploy form.

### Target {#backend_local type=local config=devices/backend_deploy.yaml default=true}

### Wiring

![Wiring](gallery/architecture.svg)

Make sure Docker Desktop is running.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port conflict error | Free ports 8086, 3000, 8080 and 1883 |
| Docker not available | Start Docker Desktop |
| Not enough disk | Keep at least 2 GB free |

### Target {#backend_remote type=remote config=devices/backend_deploy.yaml}

### Wiring

![Wiring](gallery/architecture.svg)

| Field | Example |
|-------|---------|
| Device IP | 192.168.1.100 or reComputer-R110x.local |
| Username | recomputer |
| Password | Current SSH password of the device (factory default 12345678; changing it is recommended) |

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection timeout | Check the network cable, test with ping |
| SSH authentication failed | Verify username and password |

---

## Step 2: Connect Camera to Dashboard {#recamera type=recamera_cpp required=true config=devices/recamera_cpp.yaml}

Install the retail analytics app on the reCamera and set the broker it publishes to. The app reports dwell state (browsing / engaged / needs assistance) and entry/exit counts.

### Wiring

1. Over USB the IP is `192.168.42.1`; over Ethernet or WiFi, find the IP in your router admin page
2. Enter the reCamera IP, the MQTT server IP (the machine from Step 1), an installation name and a camera ID
3. Cameras in one store share an installation name and use different camera IDs; the dashboard uses these to tell devices apart

This step disables Node-RED autostart; the two cannot run at the same time.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cannot connect | USB: use `192.168.42.1`; network: check router for IP |
| No data showing | Make sure Step 1 completed and camera and server are on the same network |
| Fails to start with a `device_init` assertion | Reboot the camera |

---

## Step 3: Map Heatmap to Floor Plan (Optional) {#heatmap type=manual required=false}

The heatmap shows the camera's perspective by default. Use the built-in calibration tool to show it on your store's floor plan.

### How to Do It

1. Open **http://\<server-ip\>:8080** in your browser
2. Click the **gear icon** (top-right corner) to open calibration settings
3. Pick the camera to calibrate ("All cameras" sets the default for any camera without its own calibration)
4. Upload a **camera screenshot** (left side) and your **floor plan image** (right side)
5. Click **4 reference points** on the camera view, then the same 4 spots on the floor plan; use widely spaced landmarks such as pillars, doorways or corners
6. Click **Save**; calibration applies immediately

Calibrated cameras share one floor plan. The dropdown at the top-left narrows the view to a single camera.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Heatmap doesn't align well | Open settings, click Reset, and recalibrate with different reference points |
| Calibration survives a browser change | Expected; calibration is stored on the server |

### Skip This If

You only need the camera-view heatmap.

## Step 4: Open Dashboard {#dashboard_recamera type=web_dashboard required=true config=devices/dashboard.yaml}

Click below to open the Grafana dashboard.

### Troubleshooting
| Symptom | Fix |
|---------|-----|
| Page not loading | Make sure Step 1 deployed successfully; run `docker ps` on the server to check services |
| Wrong host/port | If you deployed to a remote device, use its IP in the URL |
| No data | Make sure Step 2 completed and the MQTT server IP is the machine from Step 1 |

### Deployment Complete

- **Data Dashboard**: http://\<server-ip\>:3000, login `admin` / `admin`, traffic trends
- **Live Heatmap**: http://\<server-ip\>:8080 (calibrate via the gear icon)
- **Video gateway**: http://\<server-ip\>:1984, discovered cameras and preview

---

## Preset: reCamera Pro {#recamera_pro}

reCamera Pro runs detection, tracking, dwell states and entry/exit counting on the device; a computer or reComputer R1100 runs the dashboard.

- **Devices:** reCamera Pro; a computer or reComputer R1100 for the dashboard.
- **App:** the `retail-vision` app installed from the reCamera Pro App Center. This solution does not provide its install package.
- **Software:** Docker on the dashboard machine, at least 2 GB free disk.
- **Network:** all devices on the same network.

## Step 1: Start the Dashboard {#backend_pro type=docker_deploy required=true config=devices/backend_deploy.yaml}

Start the MQTT broker, database, Grafana dashboard and video gateway. Skip if already deployed. Deployment discovers ONVIF cameras on the same subnet; if the backend and cameras are on different subnets, enter the camera addresses in the deploy form.

### Target {#backend_pro_local type=local config=devices/backend_deploy.yaml default=true}

### Target {#backend_pro_remote type=remote config=devices/backend_deploy.yaml}

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port conflict error | Free ports 8086, 3000, 8080 and 1883 |
| Docker not available | Local target: start Docker Desktop. Remote target: make sure the Docker service is running on the device |
| Not enough disk | Keep at least 2 GB free |

## Step 2: Configure the Camera {#recamera_pro_app type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

Enter the device's web console credentials (not SSH), an installation name, and the MQTT address of the machine from step 1. With the MQTT address empty, results stay on the camera's page and do not reach the dashboard.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Says retail-vision is not in the App Center | Install it from the device's App Center first, then re-run this step |
| No data on the dashboard | Check the MQTT address points at the machine from step 1 and both are on the same network |
| Avg Dwell tile stays empty | Expected; the Pro app does not report per-person dwell time. Other tiles are unaffected |

## Step 3: Open the Dashboard {#dashboard_pro type=web_dashboard required=true config=devices/dashboard.yaml}

Click below to open the Grafana dashboard (login `admin` / `admin`).

### Deployment Complete

- **Dashboard**: http://\<server-ip\>:3000
- **Live Heatmap**: http://\<server-ip\>:8080
- **Video gateway**: http://\<server-ip\>:1984, discovered cameras and preview

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page not loading | Make sure Step 1 deployed successfully; run `docker ps` on the server to check services |
| Wrong host/port | If you deployed to a remote device, use its IP in the URL |

---

## Preset: IP Camera + Rockchip NPU {#rk}

Keep your existing IP cameras; a reComputer RK3588 or RK3576 runs people-flow detection locally.

- **Devices:** reComputer RK3588 or RK3576; an IP camera with RTSP output. The dashboard can run on the same board or on another computer.
- **Software:** Docker on the dashboard machine, at least 2 GB free disk.
- **Network:** camera and board on the same network.

## Step 1: Start the Dashboard {#backend_rk type=docker_deploy required=true config=devices/backend_deploy.yaml}

Start the MQTT broker, database, Grafana dashboard and video gateway. Skip if already deployed. Deployment discovers ONVIF cameras on the same subnet; if the backend and cameras are on different subnets, enter the camera addresses in the deploy form.

### Target {#backend_rk_local type=local config=devices/backend_deploy.yaml default=true}

### Target {#backend_rk_remote type=remote config=devices/backend_deploy.yaml}

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port conflict error | Free ports 8086, 3000, 8080 and 1883 |
| Docker not available | Local target: start Docker Desktop. Remote target: make sure the Docker service is running on the device |
| Not enough disk | Keep at least 2 GB free |

## Step 2: Deploy the Detector {#rk_detector type=docker_deploy required=true config=devices/rk_deploy.yaml}

Deploy the detector to the board over SSH. Pick the right board model; the wrong one will not load the model. If the dashboard runs on this board, leave the MQTT address at `127.0.0.1`.

### Target {#rk_remote type=remote config=devices/rk_deploy.yaml default=true}

The board needs Docker and the NPU driver (`/usr/lib/librknnrt.so` present).

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Container fails with a librknnrt error | The NPU driver is missing; check `/usr/lib/librknnrt.so` exists |
| No data on the dashboard | Verify the camera URL with `ffprobe rtsp://...`, and check the MQTT address |
| Low frame rate with a pinned CPU | Hardware decode is not active; check the MPP libraries on the board |

## Step 3: Open the Dashboard {#dashboard_rk type=web_dashboard required=true config=devices/dashboard.yaml}

### Deployment Complete

- **Dashboard**: http://\<server-ip\>:3000, login `admin` / `admin`
- **Live Heatmap**: http://\<server-ip\>:8080
- **Video gateway**: http://\<server-ip\>:1984, discovered cameras and preview

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page not loading | Make sure Step 1 deployed successfully; run `docker ps` on the server to check services |
| Wrong host/port | If you deployed to a remote device, use its IP in the URL |

---

## Preset: IP Camera + reComputer Industrial R20 (Hailo) {#hailo}

Keep your existing IP cameras; a reComputer Industrial R20 with a Hailo-8 accelerator runs people-flow detection locally.

- **Devices:** reComputer Industrial R20 series (with Hailo-8); an IP camera with RTSP output. The dashboard can run on the same board or on another computer.
- **Software:** Docker on the dashboard machine, at least 2 GB free disk.
- **Network:** camera and board on the same network.
- **Limit:** one Hailo-8 runs one application at a time. If another Hailo app is running on the board, the detector will not start.

## Step 1: Start the Dashboard {#backend_hailo type=docker_deploy required=true config=devices/backend_deploy.yaml}

Start the MQTT broker, database, Grafana dashboard and video gateway. Skip if already deployed. Deployment discovers ONVIF cameras on the same subnet; if the backend and cameras are on different subnets, enter the camera addresses in the deploy form.

### Target {#backend_hailo_local type=local config=devices/backend_deploy.yaml default=true}

### Target {#backend_hailo_remote type=remote config=devices/backend_deploy.yaml}

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port conflict error | Free ports 8086, 3000, 8080 and 1883 |
| Docker not available | Local target: start Docker Desktop. Remote target: make sure the Docker service is running on the device |
| Not enough disk | Keep at least 2 GB free |

## Step 2: Deploy the Detector {#hailo_detector type=docker_deploy required=true config=devices/hailo_deploy.yaml}

Deploy the detector over SSH. The Hailo runtime version is checked first; a mismatch stops the deployment and shows the installed version.

### Target {#hailo_remote type=remote config=devices/hailo_deploy.yaml default=true}

The board needs Docker and HailoRT **4.21** (driver, user library and GStreamer plugin on the same version).

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| `HAILO_OUT_OF_PHYSICAL_DEVICES` | Another application holds the accelerator; stop it first |
| Deploy reports a libhailort version mismatch | Move the board to HailoRT 4.21, changing driver and user library together |
| `/dev/hailo0` missing | The accelerator is not seated, or the `hailo_pci` driver is not loaded |
| No data on the dashboard | Verify the camera URL with `ffprobe rtsp://...`, and check the MQTT address |

## Step 3: Open the Dashboard {#dashboard_hailo type=web_dashboard required=true config=devices/dashboard.yaml}

### Deployment Complete

- **Dashboard**: http://\<server-ip\>:3000, login `admin` / `admin`
- **Live Heatmap**: http://\<server-ip\>:8080
- **Video gateway**: http://\<server-ip\>:1984, discovered cameras and preview

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page not loading | Make sure Step 1 deployed successfully; run `docker ps` on the server to check services |
| Wrong host/port | If you deployed to a remote device, use its IP in the URL |

## Preset: Upgrade Existing Cameras {#jetson}

Keep your existing IP cameras; an NVIDIA Jetson runs people-flow detection locally.

- **Devices:** NVIDIA Jetson (Orin series); an IP camera with RTSP output. The dashboard can run on the same Jetson or on another computer.
- **Software:** Docker on the dashboard machine, at least 2 GB free disk.
- **Network:** camera and Jetson on the same network.

## Step 1: Start the Dashboard {#backend_jetson type=docker_deploy required=true config=devices/backend_deploy.yaml}

Start the MQTT broker, database, Grafana dashboard and video gateway. Skip if already deployed. Deployment discovers ONVIF cameras on the same subnet; if the backend and cameras are on different subnets, enter the camera addresses in the deploy form.

### Target {#backend_jetson_local type=local config=devices/backend_deploy.yaml default=true}

### Target {#backend_jetson_remote type=remote config=devices/backend_deploy.yaml}

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Port conflict error | Free ports 8086, 3000, 8080 and 1883 |
| Docker not available | Local target: start Docker Desktop. Remote target: make sure the Docker service is running on the device |
| Not enough disk | Keep at least 2 GB free |

## Step 2: Deploy the Detector {#jetson_deploy type=docker_deploy required=true config=devices/jetson_deploy.yaml}

Deploy the detector to the Jetson over SSH. The first deployment builds a TensorRT engine, which takes 2-5 minutes; later deployments reuse it.

### Target {#jetson_remote type=remote config=devices/jetson_deploy.yaml default=true}

The Jetson needs JetPack 6.x, Docker and the NVIDIA runtime.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Connection timeout | Check the network, verify the Jetson IP with `ping` |
| NVIDIA runtime error | Run `nvidia-smi` on the Jetson to confirm the GPU is available |
| No data | Verify the RTSP URL with `ffprobe rtsp://...`, and check the MQTT address |
| Slow first start | TensorRT engine build, first time only, 2-5 minutes |

## Step 3: Open the Dashboard {#dashboard_jetson type=web_dashboard required=true config=devices/dashboard.yaml}

### Deployment Complete

- **Dashboard**: http://\<server-ip\>:3000, login `admin` / `admin`
- **Live Heatmap**: http://\<server-ip\>:8080
- **Video gateway**: http://\<server-ip\>:1984, discovered cameras and preview

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Page not loading | Make sure Step 1 deployed successfully; run `docker ps` on the server to check services |
| Wrong host/port | If you deployed to a remote device, use its IP in the URL |

---
