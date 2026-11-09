## Preset: reCamera + reBot B601-DM {#default}

Install the arm runtime on the reCamera, optionally the AI agent server on this computer and a camera app, then check teleop and run hand-eye calibration in the cockpit.

| Device | Purpose |
|--------|---------|
| reCamera (SG2002) with the B4 CAN base board | Runs the arm runtime, the web cockpit and the camera app |
| reBot B601-DM arm | Connected to the B4 board's CAN port |
| This computer | Runs the deployment and, optionally, the AI agent server |

**What you'll get:**
- Arm teleop from a phone, tablet or computer browser at `http://<camera>:8765`
- An MCP server that lets an AI agent on this computer read and move the arm
- Hand-eye calibration with an ArUco marker, or object detection boxes on the video

**Requirements:** reCamera with the B4 CAN base board (not reCamera Pro) · arm power supply · internet on this computer during deployment · printed ArUco marker, dictionary 4x4_50, for calibration

## Step 1: Install reBot Arm Teleop {#install_teleop type=recamera_console_app required=true config=devices/rebot_teleop.yaml}

Install the arm runtime and the web cockpit on the camera.

### Prerequisites

1. The camera is connected over USB (`192.168.42.1`) or is on the same network as this computer.
2. Login is `recamera` / `recamera` (`recamera.2` on earlier firmware).
3. If the camera is still in factory Node-RED mode, the deployment offers to install the reCamera console first. Accept it; the app is installed right after.

### Wiring

1. Power off the arm supply and the camera.
2. Connect the arm's CAN wires to J2 on the B4 board: pin 5 `CAN_H` (red), pin 6 `CAN_L` (black).
3. Connect 12–24 V DC to J2 pins 1/2 and ground to pins 3/4; the camera and the arm supply share ground.
4. Power on, wait about one minute for the camera to boot, then click **Deploy**.

### Deployment Complete

The arm runtime is running and the cockpit is at `http://<camera>:8765`. The camera also starts a Wi-Fi hotspot `reCamera-Arm-Teleop` (default password `12345678`, camera address `192.168.16.1`) for phones. The arm stays without torque until you enable it in the cockpit.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "missing hardware capability: can" | The camera has no B4 CAN board, or `can0` did not come up. Check the board and reboot the camera |
| "'rebot-teleop' is not in the catalog" | This computer cannot reach `sensecraft-statics.seeed.cc`, or the catalog is older than this solution. Check the network and deploy again |
| Login rejected | Use the camera account: `recamera` / `recamera` (or `recamera.2`) |
| Not enough storage | Uninstall an unused app on the console's Applications page |

---

## Step 2: Install the AI Agent Server on This Computer (Optional) {#install_mcp type=script required=false config=devices/mcp_server.yaml}

Install `rebot-mcp` on this computer so an AI agent can control the arm.

### Prerequisites

1. This computer has internet access. The step installs [uv](https://docs.astral.sh/uv/) with its official installer if it is missing; uv downloads its own Python.
2. Enter the camera address the agent should use: `192.168.42.1` over USB, `192.168.16.1` on the arm's hotspot.

### Deployment Complete

`rebot-mcp` is installed as a uv tool. If the Claude Code CLI (`claude`) is installed, the server is registered for your user as `rebot`. For Claude Desktop, Cursor and other clients, the step log prints an `mcpServers` entry to paste into the client's MCP configuration.

What the agent can do (14 tools): read the arm state, take camera snapshots (plain or with detection boxes), read detections, move to a pose or by an offset, open and close the gripper, home, park, enable torque, stop, E-stop, and take or release control.

Safety defaults:
- The agent cannot clear an E-stop or a fault; a person clears it in the cockpit (`--allow-clear-fault` is not set).
- The agent cannot take control away from the cockpit (`--allow-preempt` is not set).
- `armd` on the camera enforces the workspace box, speed caps and a lease watchdog that parks the arm when the controlling client stops responding.

To install by hand, run `uv tool install "rebot-companion[agent] @ https://github.com/Seeed-Solution/rebot-companion/archive/refs/heads/main.zip"`, then `claude mcp add --scope user rebot -- rebot-mcp --armd http://192.168.42.1:8765 --camera-ws ws://192.168.42.1:8001/`.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| uv install fails | Install uv by hand from [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/), then deploy this step again |
| Agent reports `LEASE_BUSY` | The cockpit holds control. Release it in the cockpit, or let the agent call `take_control` after the cockpit is closed |
| Agent reports `CAMERA_UNAVAILABLE` | No camera app is running; install one in Step 3 |
| Claude Code does not list `rebot` | Run `claude mcp list`; if missing, run the manual command above |

---

## Step 3: Install a Camera App (Optional) {#install_camera_app type=recamera_console_app required=false config=devices/camera_app.yaml}

Pick ArUco markers for hand-eye calibration, or YOLO for object detection.

### Prerequisites

1. Step 1 is done.
2. The camera runs one camera app at a time. ArUco markers are needed for hand-eye calibration in Step 4; YOLO adds detection boxes and tap-to-grasp in the cockpit.

### Deployment Complete

Activating a camera app stops the arm runtime, because the console runs one gallery app at a time and the arm app was the active one. Restart the camera once: open the console at `http://<camera>/`, go to **System** and click **Reboot**. After the reboot both the arm runtime and the camera app start.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cockpit does not load after this step | Reboot the camera as described above |
| Dropdown shows only the two apps | That is expected; other apps are in the console's **Install from cloud** list |
| App does not start | Check its status on the console's Applications page and deploy again |

---

## Step 4: Check Teleop and Calibrate {#open_cockpit type=web_dashboard required=true config=devices/cockpit.yaml}

Open the cockpit, move the arm, and run hand-eye calibration.

### Deployment Complete

#### Check teleop

1. Open `http://<camera>:8765` on a phone, tablet or this computer.
2. The status panel shows the CAN bus feedback and the joint table updates.
3. Press and hold the torque switch to enable the arm, then jog J1 a few degrees with the joint buttons or joysticks.
4. With a camera app running, the gripper camera video is shown.

#### Hand-eye calibration (ArUco markers)

1. Print an ArUco marker from dictionary 4x4_50 and fix it flat on the table.
2. Open **Hand-Eye Cal** and choose eye-in-hand (camera on the gripper).
3. Move the arm so the marker is in view from different angles and capture 9 or more poses. Keep only one marker in view.
4. Click **Solve**, check the reported RMSE, and export the JSON. rebot-companion loads it with `HandEyeCalibration.load_result`.

#### Detection overlay (YOLO)

1. Turn on **Detect**; boxes and labels appear on the video.
2. Tap-to-grasp is tested in simulation only; keep a hand on the E-stop if you try it.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not load | Check the address (`192.168.42.1` over USB, `192.168.16.1` on the hotspot); if you installed a camera app, reboot the camera |
| No video | No camera app is running; do Step 3 |
| Cockpit shows observer mode | Another client (for example the AI agent) holds control; confirm the takeover in the cockpit or stop the agent |
| Arm does not enable | Check the arm power supply and the CAN wiring on J2 |
| E-stop or fault shown | Clear it in the cockpit after checking the arm |
