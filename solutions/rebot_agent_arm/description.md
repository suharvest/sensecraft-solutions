## What This Solution Does

Drive a reBot B601-DM arm from the browser on your phone, tablet or computer, and let an AI agent on your computer move it through an MCP server. The camera on the gripper shows what the arm sees, finds objects (YOLO) and ArUco markers, and is calibrated to the arm with one printed marker.

Everything on the arm side is one app, rebot-teleop, on a standard reCamera with the B4 CAN base board: `armd` drives the motors and serves the web cockpit, `rebot-vision` runs the camera. No separate controller computer or camera app is needed.

## Core Value

| What you get | Details |
|---|---|
| Teleop from a browser | Joysticks, joint control and Cartesian moves at `http://<camera>:8765`; the camera also opens its own Wi-Fi hotspot, so a phone can connect without a router |
| AI agent control | `rebot-mcp` from [rebot-companion](https://github.com/Seeed-Solution/rebot-companion) runs on your computer and gives Claude Code, Claude Desktop or another MCP client 14 tools: arm state, snapshots, detection, moves, gripper, home, park, stop, E-stop |
| Vision on demand | Video, YOLO object detection on the camera's AI chip and ArUco markers with 3D pose on its CPU; detection runs only when the cockpit or the agent asks |
| Hand-eye calibration | Eye-in-hand calibration with an ArUco marker on the table; the exported JSON loads in rebot-companion |
| Demonstration recording | Joint state and commands are written to one Parquet file per episode; with gravity compensation you guide the arm by hand |
| Small runtime | Measured on the reCamera: `armd` is a 4.1 MB static binary using 3.7 MB of RAM and 7.0 % of the single core with all 7 motors torqued at 50 Hz |

## Use Cases

| Scenario | How you use it |
|---|---|
| Remote handling | Open the cockpit on a phone, watch the gripper camera and move objects with the joysticks |
| Agent experiments | Ask Claude to read the arm state, take a snapshot, detect objects and move to a position |
| Data collection | Start a recording in the cockpit, guide the arm by hand, save the episode |
| Vision calibration | Print a 4x4_50 ArUco marker, run hand-eye calibration, use the result for camera-guided picking in rebot-companion |

## Usage Notes

### Hardware

| Device | Role | Required |
|---|---|---|
| reCamera (SG2002) with the B4 CAN base board | Runs rebot-teleop (`armd`, cockpit, `rebot-vision`); the arm connects to the board's CAN port (`can0`) | ✓ |
| reBot B601-DM arm (Damiao motors) | 6 joints and a gripper, 7 motors; the camera is mounted after the last wrist joint | ✓ |
| Power supply for the arm | The B4 board takes 12–24 V DC on its J2 connector; connect the grounds of the camera and the arm supply | ✓ |
| Computer (macOS, Windows or Linux) | Runs this deployment and the AI agent server | ✓ |
| Printed ArUco marker (dictionary 4x4_50, 5 cm by default) | Hand-eye calibration | For calibration |

reCamera Pro is not supported. Without the B4 CAN board the console refuses to start the app.

### Network

- Over USB the camera is `192.168.42.1`. On the camera's Wi-Fi hotspot (`reCamera-Arm-Teleop`, default password `12345678`) it is `192.168.16.1`. The cockpit and the API have no login: change the hotspot password before using the arm outside a lab.
- The computer needs internet access during deployment to download the packages; the camera does not.

### Measured on the reCamera

Camera vision with the arm's torque off:

| | Runs on | Time per frame | Whole chip at 5 results/s |
|---|---|---|---|
| Standby (no caller) | — | — | 20–26 % |
| YOLO | AI chip (TPU) | 47 ms | 34 % |
| ArUco (640 × 360) | CPU | 37–57 ms (depends on the scene) | 53 % |
| YOLO + ArUco | TPU + CPU | — | 55 % |

### Test coverage

- Teleop, torque, gravity compensation and the figures above were measured on a reCamera with a reBot B601-DM. A 30 s hand-guided recording gave 1509 frames.
- Tap-to-grasp was tested in simulation and screenshot tests only. Keep the E-stop within reach when you use it.
- Hand-eye calibration accuracy in rebot-companion was checked on synthetic data. The cockpit reports the RMSE of your own calibration.
- The recording is a plain Parquet file with LeRobot-style column names, not a LeRobot dataset; conversion and training on it are not provided or tested.
- YOLO uses the YOLO11n model already on the camera. Without it, ArUco markers and calibration still work.
