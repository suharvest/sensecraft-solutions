## Preset: reCamera + reBot B601-DM: Teleop & AI Control {#default}

Install `rebot-teleop` on reCamera, drive and calibrate the arm from the web cockpit, and optionally install `rebot-mcp` on this computer for AI agent control.

**Requirements:** reCamera (SG2002) with B4 CAN board (not reCamera Pro) · reBot B601-DM arm + 12–24 V DC supply (common ground) · internet on this computer · printed 4x4_50 ArUco marker (5 cm) if calibrating

## Step 1: Install reBot Teleop on the Camera {#install_teleop type=recamera_console_app required=true config=devices/rebot_teleop.yaml}

Install `rebot-teleop` on reCamera (`192.168.42.1` over USB or on the same network; login `recamera` / `recamera`, or `recamera.2` on earlier firmware). If the camera is in factory Node-RED mode, accept the prompt to install the reCamera console first.

### Wiring

1. Power off both the arm supply and the camera.
2. Connect the arm's CAN wires to J2 on the B4 board: pin 5 `CAN_H` (red), pin 6 `CAN_L` (black).
3. Connect 12–24 V DC to J2 pins 1/2 and GND to pins 3/4 (share ground between camera and arm supply).
4. Power on, wait ~1 minute for boot, then click **Deploy**.

### Deployment Complete

`rebot-teleop` runs `armd` (`http://<camera>:8765`), camera vision, and the `reCamera-Arm-Teleop` Wi-Fi hotspot (`12345678`, `192.168.16.1`). Torque stays off until enabled, and activating another app in the console stops `rebot-teleop`.

### Troubleshooting

| Issue | Solution |
|---|---|
| `"missing hardware capability: can"` | Check B4 CAN board seating and reboot the camera |
| Login rejected | Use `recamera` / `recamera` (or `recamera.2` on earlier firmware) |
| Cockpit stopped after using console | Another app was activated; re-enable `rebot-teleop` on the console Applications page |

---

## Step 2: Open the Cockpit for Teleop & Calibration {#open_cockpit type=web_dashboard required=true config=devices/cockpit.yaml}

### Operator Checklist

1. Open `http://<host>:8765` on a phone, tablet, or computer and verify live video, CAN feedback, and 7-joint telemetry.
2. Press and hold the torque-enable switch, then test joint jogs or Cartesian XYZ/RPY moves.
3. Save common waypoints (`scan`, `bin_a`, `bin_b`) as named poses on `armd`.
4. *(Optional)* Run ArUco hand-eye calibration: place one printed 5 cm `4x4_50` marker flat on the table, open **Hand-Eye Cal** → set **Camera on gripper**, capture 5–9 angles, then click **Solve** and **Export JSON**.

Keep someone within reach of the arm power cut-off during physical motion.

### Troubleshooting

| Issue | Solution |
|---|---|
| Page does not load | Verify IP (`192.168.42.1` USB, `192.168.16.1` hotspot) and confirm `rebot-teleop` is active |
| No video | Wait a few seconds for `rebot-vision` to restart, or restart `rebot-teleop` in the console |
| Arm does not enable | Check the 12–24 V arm supply and J2 CAN wiring |
| High solve residual / observer mode | Keep the marker still and remove outliers; observer mode means another client holds control |

---

## Step 3: Install the AI Agent Server on This Computer {#install_mcp type=script required=false config=devices/mcp_server.yaml}

Optional: install `rebot-mcp` on this computer (automatically inherits the Step 1 IP) so an AI agent can read camera/arm state and run closed-loop tasks over 24 MCP tools.

- **Connect**: Claude Code auto-registers `rebot` (`claude mcp list`); for Claude Desktop, Cursor, or Windsurf, paste the `mcpServers` JSON printed at the end of the step log into your client config and restart.
- **Test prompt**: *"Check `describe_safety` and `get_state`, take a snapshot, and tell me what the camera sees."*
- **Safety rules**: Release control in the cockpit before asking the AI to move the arm; latched faults and E-stops can only be cleared manually in the cockpit.

### Troubleshooting

| Issue | Solution |
|---|---|
| `LEASE_BUSY` | Release control in the cockpit or close the cockpit tab |
| `ESTOP_ACTIVE` or `FAULT_ACTIVE` | Inspect the workspace and clear the fault manually in the cockpit |
| Claude Code missing `rebot` | Run `claude mcp list` and re-run this step if needed |

---

## Preset: Virtual Sandbox & Policy Training (Zero Hardware) {#virtual_training}

Test tasks in the browser 3D MuJoCo sandbox with zero hardware, then prepare and validate a local ONNX policy package ready for Preset 3.

**Requirements:** Modern WebGL/WASM browser · internet access on this computer

## Step 1: Open the reBot Cyclops 3D Virtual Sandbox {#open_sandbox type=web_dashboard required=true config=devices/cyclops_sandbox.yaml}

1. Click **Open in Browser** to launch the paired 3D sandbox tab (no hardware needed).
2. Pick a tool, vision preset, motion parameters, and safety settings in the bottom deck, then click **Run Test** to observe the physics simulation and diagnostics.
3. Keep the tab open so an AI assistant (or `solution-cli page`) can adjust parameters, run batch tests, and export configurations alongside you.

### Troubleshooting

| Issue | Solution |
|---|---|
| Sandbox tab opens without pairing | Re-open from the deployment card or run `solution-cli page pair` |
| 3D canvas stays blank or slow | Enable hardware WebGL acceleration and close other heavy WebGL tabs |

---

## Step 2: Set Up the Local Policy Training Workspace {#train_policy type=script required=true config=devices/policy_training.yaml}

1. Enter `policy_id` (default `pcb_demo`) and deploy — this creates `~/.sensecraft/rebot-policies/<policy_id>` with a starter template (existing `policy.json` and `model.onnx` are never overwritten).
2. Put your trained `policy.json` + `model.onnx` in that folder (or collect demonstrations with `rebot-record`; to test Preset 3 end-to-end first, use the starter template directly).
3. Verify the package before Preset 3:
   ```bash
   rebot-scene validate ~/.sensecraft/rebot-policies/<policy_id>
   ```

### Troubleshooting

| Issue | Solution |
|---|---|
| `uv tool install` fails | Check internet access to GitHub/PyPI, or install `uv` manually and re-run |
| `rebot-scene validate` fails | Ensure `policy.json` input/output shapes and names match `model.onnx` |

---

## Preset: Load & Run Learned Policy in reBot armd {#armd_policy}

Upload a validated ONNX policy package (`policy.json` + `model.onnx`) to `armd`, preview it in browser WASM or local simulation, or run it on the physical arm under supervision.

**Requirements:** Policy folder in `~/.sensecraft/rebot-policies/<policy_id>` (from Preset 2) · running `armd` on reCamera or local `armd --follower sim` (`127.0.0.1`)

## Step 1: Install or Verify reBot Teleop (armd) on the Camera {#ensure_armd type=recamera_console_app required=false config=devices/rebot_teleop.yaml}

Skip this step if `rebot-teleop` is already installed on reCamera or when targeting local `armd --follower sim` (`127.0.0.1`).

### Troubleshooting

| Issue | Solution |
|---|---|
| Targeting local simulator | Skip this step and set `host` to `127.0.0.1` in Step 2 |
| `can0` missing | Verify B4 CAN board seating and reboot the camera |

---

## Step 2: Upload & Activate the ONNX Policy in armd {#load_policy type=script required=true config=devices/armd_policy_loader.yaml}

Set the 3 inputs (`host`: `192.168.42.1` USB, `192.168.16.1` hotspot, or `127.0.0.1` local sim; `policy_id`: default `pcb_demo`; `sandbox_mode`: `wasm` browser pre-flight, `sim` real-time sim, or `upload_only`) and deploy to upload and activate the policy on `armd`.

- **Run on local simulator** (`armd --follower sim`):
  ```bash
  rebot-policy --armd 127.0.0.1 --policy onnx:$HOME/.sensecraft/rebot-policies/<policy_id> --fps 30 --max-seconds 15
  ```
- **Run on physical arm** (release cockpit control first, and stand with power cut-off within reach before passing `--i-am-at-the-arm`):
  ```bash
  rebot-policy --armd <host> --policy onnx:$HOME/.sensecraft/rebot-policies/<policy_id> --fps 30 --max-seconds 15 --i-am-at-the-arm
  ```

### Troubleshooting

| Issue | Solution |
|---|---|
| Connection refused on port `8765` | Confirm `rebot-teleop` (or local `armd`) is running at `<host>:8765` |
| Upload rejects policy | Run `rebot-scene validate ~/.sensecraft/rebot-policies/<policy_id>` and fix schema mismatches |
| `rebot-policy` stops with `LEASE_BUSY` | Release control or close the web cockpit tab before starting `rebot-policy` |

---

## Step 3: Open the Policy Cockpit & Monitor Safety {#open_policy_cockpit type=web_dashboard required=true config=devices/cockpit_policy.yaml}

1. Open `http://<host>:8765/` for live arm telemetry, fault status, and the software E-stop button.
2. If you chose `wasm` mode, open `http://<host>:8765/?sim=wasm` to run browser simulation pre-flight.
3. Seeing **observer mode** while `rebot-policy` runs is normal—the policy runner holds control, while the cockpit **E-stop** button remains active. On physical hardware, keep someone within reach of the power cut-off.

### Troubleshooting

| Issue | Solution |
|---|---|
| `?sim=wasm` missing runtime assets | Check `rebot-scene status --armd-url http://<host>:8765` and confirm WASM assets are present |
| Run stops on `FAULT_ACTIVE` or `FOLLOWING_ERROR` | Stop motion, check for physical obstructions, and clear the fault in the cockpit |
