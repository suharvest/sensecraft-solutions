## What This Solution Does

Drive a reBot B601-DM arm from the browser on your phone, tablet or computer, and let an AI agent on your computer move it through an MCP server. The camera on the gripper shows what the arm sees, and the same page records joint data while you guide the arm by hand.

The arm runtime (`armd`) and the web cockpit run on a standard reCamera with the B4 CAN base board. No separate controller computer is needed for teleop.

## Core Value

| What you get | Details |
|---|---|
| Teleop from a browser | Joysticks, joint buttons and Cartesian moves at `http://<camera>:8765`; the camera also opens its own Wi-Fi hotspot, so a phone can connect without a router |
| AI agent control | `rebot-mcp` from [rebot-companion](https://github.com/Seeed-Solution/rebot-companion) gives an agent 14 tools by default: arm state, snapshots, detections, moves, gripper, stop |
| Hand-eye calibration | Eye-in-hand calibration with an ArUco marker on the table; the exported JSON loads in rebot-companion |
| Demonstration recording | Joint state and commands are written to a Parquet file per episode |
| Small runtime | Measured on the reCamera: 4.1 MB static binary, 3.7 MB RAM, 7.0 % of one core with all 7 motors torqued at 50 Hz |

## Use Cases

| Scenario | How you use it |
|---|---|
| Remote handling | Open the cockpit on a phone, watch the gripper camera and move objects with the joysticks |
| Agent experiments | Ask Claude Code or another MCP client to read the arm state, take a snapshot and move to a position |
| Data collection | Start a recording in the cockpit, guide the arm, save the episode |
| Vision calibration | Print a 4x4_50 ArUco marker, run hand-eye calibration, use the result for camera-guided picking in rebot-companion |

## Usage Notes

### Hardware

| Device | Role | Required |
|---|---|---|
| reCamera (SG2002) with the B4 CAN base board | Runs `armd`, the cockpit and the camera app; the arm connects to the board's CAN port (`can0`) | ✓ |
| reBot B601-DM arm (Damiao motors) | 6 joints and a gripper; the camera is mounted after the last wrist joint | ✓ |
| Power supply for the arm | The B4 board takes 12–24 V DC on its J2 connector; connect the grounds of the camera and the arm supply | ✓ |
| Computer (macOS, Windows or Linux) | Runs this deployment; also runs the AI agent server if you install it | ✓ |
| Printed ArUco marker (dictionary 4x4_50) | Hand-eye calibration | For calibration |

reCamera Pro is not supported. Without the B4 CAN board the console refuses to start the arm app.

### Network

- Over USB the camera is `192.168.42.1`. On the camera's Wi-Fi hotspot (`reCamera-Arm-Teleop`, default password `12345678`) it is `192.168.16.1`. Change the hotspot password before using the arm outside a lab.
- The computer needs internet access during deployment to download the packages; the camera does not.

### Test coverage

- Teleop, torque and the figures above were measured on a reCamera with a reBot B601-DM.
- Hand-guiding (gravity compensation) and tap-to-grasp were tested in simulation and screenshot tests. Keep the E-stop within reach when you use them.
- Hand-eye calibration accuracy in rebot-companion was checked on synthetic data. The cockpit reports the RMSE of your own calibration.
- The console runs one camera app at a time: ArUco markers or YOLO object detection.
