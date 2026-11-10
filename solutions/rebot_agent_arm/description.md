## What this reference design does

**A single reCamera serves as the eyes and brain of the robot arm. No industrial PC needed — drive it from your phone, or let AI agents take over.**

A standard reCamera (SG2002, RISC-V) with the B4 CAN base board directly drives 7 Damiao servo motors on the reBot B601-DM arm over SocketCAN. No external industrial PC or host controller is needed.

The `armd` control daemon is a **4.1 MB** static binary with a **3.7 MB** RAM footprint, using **7.0 %** of a single CPU core while running 7 joints at 50 Hz closed-loop control. On-device TPU runs YOLOv11 target detection in **47 ms**, while the CPU calculates ArUco 3D poses in real time.

It broadcasts a Wi-Fi hotspot on boot. Connect from any phone to port 8765 to open the web cockpit with dual joysticks and Cartesian stepping. Perform eye-in-hand calibration directly in the browser using a printed A4 ArUco sheet. 14 native MCP tools provide seamless integration with Claude Desktop and Claude Code.

**Limitations:** Requires the reCamera B4 CAN base board (not supported on reCamera Pro); currently verified on reBot B601-DM (Damiao motors); tap-to-grasp is fully closed-loop in simulation, while field use requires physical emergency stop verification.
