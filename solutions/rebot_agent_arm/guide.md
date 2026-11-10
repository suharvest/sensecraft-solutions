## Preset: reCamera + reBot B601-DM {#default}

Install the reBot Teleop app on the reCamera, install the AI agent server (MCP) on this computer, then open the cockpit, move the arm and run hand-eye calibration with an ArUco marker.

| Device | Purpose |
|--------|---------|
| reCamera (SG2002) with the B4 CAN base board | Runs the arm runtime, the web cockpit and the camera vision (one app: rebot-teleop) |
| reBot B601-DM arm | Connected to the B4 board's CAN port |
| This computer | Runs the deployment and the AI agent server |

**What you'll get:**
- Arm teleop from a phone, tablet or computer browser at `http://<camera>:8765`
- Camera video, YOLO object detection and ArUco markers in the same app
- An MCP server that lets an AI agent on this computer read, look through the camera and move the arm
- Hand-eye calibration with an ArUco marker

**Requirements:** reCamera with the B4 CAN base board (not reCamera Pro) · arm power supply · internet on this computer during deployment · printed ArUco marker, dictionary 4x4_50 (5 cm by default), for calibration

## Step 1: Install reBot Teleop on the Camera {#install_teleop type=recamera_console_app required=true config=devices/rebot_teleop.yaml}

Install the rebot-teleop app: arm control, web cockpit and camera vision.

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

rebot-teleop is the active app. It runs `armd` (cockpit at `http://<camera>:8765`) and `rebot-vision` (video at `ws://<camera>:8001/`, YOLO and ArUco on request). The camera also starts a Wi-Fi hotspot `reCamera-Arm-Teleop` (default password `12345678`, camera address `192.168.16.1`) for phones. The arm stays without torque until you enable it in the cockpit.

The app includes the camera vision, so no other camera app is needed. Activating another app in the reCamera console stops rebot-teleop.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "missing hardware capability: can" | The camera has no B4 CAN board, or `can0` did not come up. Check the board and reboot the camera |
| "'rebot-teleop' is not in the catalog" | This computer cannot reach `sensecraft-statics.seeed.cc`, or the catalog is older than this solution. Check the network and deploy again |
| Login rejected | Use the camera account: `recamera` / `recamera` (or `recamera.2`) |
| Not enough storage | Uninstall an unused app on the console's Applications page |
| Cockpit stopped after using the console | Another app was activated. Activate rebot-teleop again on the console's Applications page |

---

## Step 2: Install the AI Agent Server on This Computer {#install_mcp type=script required=true config=devices/mcp_server.yaml}

Install `rebot-mcp` from [rebot-companion](https://github.com/Seeed-Solution/rebot-companion) and connect it to Claude Code or Claude Desktop.

### Prerequisites

1. This computer has internet access. The step installs [uv](https://docs.astral.sh/uv/) with its official installer if it is missing; uv downloads its own Python. git is not needed.
2. Enter the camera address the agent should use: `192.168.42.1` over USB, `192.168.16.1` on the arm's hotspot.

### Deployment Complete

`rebot-mcp` is installed as a uv tool. The server runs on this computer and reaches the arm over the network; nothing extra is installed on the camera.

- **Claude Code**: if the `claude` CLI is installed, the server is registered for your user as `rebot`. Check with `claude mcp list`.
- **Claude Desktop**: copy the `mcpServers` entry printed at the end of the step log into `claude_desktop_config.json` (Claude Desktop: **Settings → Developer → Edit Config**), then restart Claude Desktop. Cursor, Windsurf and other clients that use `mcpServers` take the same entry.

Tools available to the agent (14): `get_state`, `snapshot`, `snapshot_annotated`, `detect` (pipelines `yolo`, `aruco` or both), `move_to`, `move_relative`, `gripper`, `home`, `park`, `stop`, `e_stop`, `enable`, `take_control`, `release_control`.

Safety defaults:
- The agent cannot clear an E-stop or a fault; a person clears it in the cockpit. `clear_fault` is listed only when the server starts with `--allow-clear-fault`.
- The agent cannot take control away from the cockpit. A forced takeover is available only with `--allow-preempt`.
- `armd` on the camera enforces the workspace box, speed caps and a lease watchdog that parks the arm when the controlling client stops responding.

#### Install by hand

Same commands as the rebot-companion README:

```bash
git clone https://github.com/Seeed-Solution/rebot-companion
cd rebot-companion
uv sync --extra agent
claude mcp add rebot -- uv run --directory /path/to/rebot-companion --extra agent rebot-mcp \
  --armd http://192.168.42.1:8765
```

For Claude Desktop, add to `mcpServers`:

```json
{
  "mcpServers": {
    "rebot": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/rebot-companion", "--extra", "agent",
               "rebot-mcp", "--armd", "http://192.168.42.1:8765"]
    }
  }
}
```

The camera stream defaults to `ws://192.168.42.1:8001/`; add `--camera-ws ws://<camera>:8001/` when the camera has another address.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| uv install fails | Install uv by hand from [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/), then deploy this step again |
| Agent reports `LEASE_BUSY` | The cockpit holds control. Release it in the cockpit, or let the agent call `take_control` after the cockpit is closed |
| Agent reports `CAMERA_UNAVAILABLE` or `DETECTOR_UNAVAILABLE` | rebot-teleop is not the active app on the camera. Activate it on the console's Applications page |
| Agent reports `ESTOP_ACTIVE` or `FAULT_ACTIVE` | Check the arm, then clear it in the cockpit |
| Claude Code does not list `rebot` | Run `claude mcp list`; if missing, run the manual command above |
| Claude Desktop shows no `rebot` tools | Check that the JSON is valid and the `command` path exists, then restart Claude Desktop |

---

## Step 3: Open the Cockpit and Calibrate {#open_cockpit type=web_dashboard required=true config=devices/cockpit.yaml}

Open the cockpit, move the arm, and run hand-eye calibration with an ArUco marker.

### Deployment Complete

#### Check teleop

1. Open `http://<camera>:8765` on a phone, tablet or this computer.
2. The camera video is shown, and in expert mode the link status shows the CAN feedback and the joint table updates.
3. Press and hold the torque switch to enable the arm, then jog J1 a few degrees with the joysticks.

#### Hand-eye calibration (ArUco marker)

1. Print an ArUco marker from dictionary 4x4_50 (5 cm by default) and fix it flat on the table.
2. Open **Hand-Eye Cal** and set **Camera mounting** to **Camera on gripper**.
3. Move the arm so the marker is in view from different angles and capture poses: at least 5, 9 recommended. Keep only one marker in view.
4. Click **Solve**, check the reported RMSE, and click **Export JSON**. rebot-companion loads it with `HandEyeCalibration.load_result`.

#### Detection overlay

1. Turn on detection and choose YOLO, ArUco or both; boxes and markers appear on the video.
2. Tap-to-grasp is tested in simulation only; keep a hand on the E-stop if you try it.

#### Try the agent

Ask Claude: "Read the arm state, take a snapshot and tell me what the camera sees." Close the cockpit or release control first so the agent can take the lease for moves.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not load | Check the address (`192.168.42.1` over USB, `192.168.16.1` on the hotspot) and that rebot-teleop is the active app in the console |
| No video | rebot-vision restarts on its own; wait a few seconds. If it stays black, restart rebot-teleop from the console's Applications page |
| YOLO shown as unavailable | The YOLO11n model is not on the camera; the app uses the model already on the device. ArUco and calibration still work |
| Cockpit shows observer mode | Another client (for example the AI agent) holds control; confirm the takeover in the cockpit or stop the agent |
| Arm does not enable | Check the arm power supply and the CAN wiring on J2 |
| E-stop or fault shown | Clear it in the cockpit after checking the arm |
| Solve reports a high residual | Keep the marker fixed and the arm still at each capture, remove the highlighted poses and solve again |
