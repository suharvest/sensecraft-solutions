## What This Solution Does

**Use one reCamera as both the eyes and brain of a reBot B601-DM arm—or start with zero hardware in the 3D browser sandbox and deploy ONNX policies to the arm.**

On the camera, a single app (`rebot-teleop`) runs motor control (`armd`), the web cockpit, and camera vision (`rebot-vision`). Three presets cover the full workflow:

1. **Teleop & AI Control (`default`)**: Drive the arm from a browser, save named poses, calibrate eye-in-hand vision, and optionally connect `rebot-mcp` (24 tools) for AI agent control.
2. **Virtual Sandbox & Policy Training (`virtual_training`)**: Test tasks in the browser 3D MuJoCo sandbox with zero hardware and prepare a validated ONNX policy package (`policy.json` + `model.onnx`).
3. **Load & Run Learned Policy in reBot armd (`armd_policy`)**: Upload your policy to `armd` for browser WASM pre-flight, local simulation, or supervised physical arm execution.

## Core Value

| Feature | What you get |
|---|---|
| Browser teleop | Joysticks, 7-joint and Cartesian XYZ/RPY control, and named poses at `http://<camera>:8765`, plus a built-in Wi-Fi hotspot |
| AI agent control | Optional `rebot-mcp` server (24 tools) for state, vision, motion, pose management, and safety checks |
| 3D browser sandbox | Interactive MuJoCo simulation for testing tools, vision presets, motion parameters, and batch runs with zero hardware |
| Portable ONNX workflow | Record real episodes with `rebot-record` or train in simulation, validate with `rebot-scene`, and run in WASM, sim, or hardware |
| Vision on demand | Live video, TPU YOLO detection, and CPU ArUco 3D pose estimation—inference runs only when requested |
| Compact footprint | Measured on reCamera: `armd` is a 4.1 MB static binary using 3.7 MB RAM and 7% CPU with all 7 motors torqued at 50 Hz |

## Use Cases

- **Remote teleop & teaching**: Watch the gripper camera on a phone or tablet, jog the arm, and save named poses.
- **AI agent pick-and-place**: Connect `rebot-mcp` so an AI agent inspects detections, respects keep-out zones, and moves the arm safely.
- **Zero-hardware policy iteration**: Prototype tasks in the 3D sandbox, validate an ONNX policy locally, and pre-flight it before touching hardware.

## Usage Notes

- **Hardware (Presets 1 & 3)**: Requires a standard reCamera (SG2002) with the **B4 CAN base board** (**reCamera Pro is not supported**), a reBot B601-DM arm, and a 12–24 V DC arm supply sharing ground with the camera. Calibration uses a printed 4x4_50 ArUco marker (5 cm default).
- **Network**: Camera IP is `192.168.42.1` over USB, or `192.168.16.1` on the camera hotspot (`reCamera-Arm-Teleop`, default password `12345678`—change it outside a lab).
- **Safety**: The reBot B601-DM has no physical E-stop switch; keep someone within reach of the power cut-off during physical motion. `rebot-policy` requires `--i-am-at-the-arm` on real hardware.
- **Measured vision load on reCamera** (torque off, 5 results/s): standby 20–26% chip load; YOLO (TPU) 47 ms/frame (34% load); ArUco 640×360 (CPU) 37–57 ms/frame (53% load); YOLO + ArUco 55% load.
