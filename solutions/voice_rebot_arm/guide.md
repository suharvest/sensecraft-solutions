## Preset: Voice Grasping on Jetson {#default}

Deploy a voice-controlled grasping arm: say **"Hey Jarvis, grab the water bottle"** and the reBot B601-DM finds the object with its wrist RGB-D camera and picks it up. Wake word, speech recognition, LLM, object detection, grasp planning, arm control and TTS reply all run locally on the Jetson, with no online API.

| Device | Purpose |
|--------|---------|
| reBot B601-DM | 6-DoF arm with parallel gripper (0.100 m max jaw) — USB serial |
| Orbbec Gemini 2 | wrist-mounted RGB-D camera (eye-in-hand) — USB 3.0 |
| reComputer J40 series | Jetson Orin NX 16GB, runs all services |
| reSpeaker USB mic + speaker | far-field voice in, TTS reply out |

**What you'll get:**
- Voice-commanded grasping of boxes, standing (opaque) bottles, bananas, cups and oranges
- The object list is editable config, no retraining
- Live dashboard with the wrist-camera view and arm state (`:8776`)
- Cartesian observation API (`:8775/observation`) for integration with other solutions

**Before you start (hardware checklist):**
1. Arm powered on and connected — `ls /dev/ttyACM*` shows it (usually `/dev/ttyACM0`)
2. Gemini 2 on a **USB 3.0** port (blue connector — USB 2 starves the depth stream)
3. reSpeaker mic + speaker connected; note your desktop user's uid (`id -u`, usually `1000`)
4. Docker + NVIDIA runtime (standard on JetPack 6); ~10 GB free disk
5. Internet on first boot to download ~1.4 GB of container images and ~8.5 GB of models

> **China networks**: set the *HuggingFace Endpoint* input to `https://hf-mirror.com` in Step 1 — the LLM engine, speech models and grasp detector all download through it.

## Step 1: Deploy the Stack {#rebot_stack type=docker_deploy required=true config=devices/rebot_stack.yaml}

Deploy the voice, LLM, arm-control and inventory services to the Jetson.

### Services

Deployment starts three services — `rebot-arm` (arm control), `seeed-voice` (speech recognition and synthesis) and `edge-llm` (LLM) — and downloads the grasp detector.

### Troubleshooting

| Symptom | Fix |
|---|---|
| Grasp detection is slow | If the TensorRT engine fails to load, the stack switches to ONNX Runtime — same detections, slower. The first line of `docker logs voice-rebot-arm` shows which one is active. |
| SSH connection fails | Check the Jetson IP address, SSH username/password and that port `22` is reachable. |
| Arm serial device is missing | Confirm `ls /dev/ttyACM*` on the Jetson and update the Arm Serial Device field. |
| `edge-llm` stays unhealthy on first boot | The TensorRT engine is still downloading or warming up; watch `docker logs edge-llm`. |

### Target {#rebot_stack_remote type=remote device=jetson device_name="Jetson" config=devices/rebot_stack.yaml default=true}

Deploy to a Jetson over SSH. Enter the Jetson IP address and SSH credentials, then set the arm serial device, audio user id and HuggingFace endpoint below.

### Target {#rebot_stack_local type=local device=jetson device_name="Jetson (Local)" config=devices/rebot_stack.yaml}

Deploy directly on the current machine; use this only when the app or CLI is running on the Jetson itself. Fill in the arm serial device, audio user id and HuggingFace endpoint.

First boot downloads and warms up the LLM engine; on slow links `edge-llm` may take up to ~10 min to report healthy — watch `docker logs edge-llm`.

## Step 2: Open the Dashboard {#verify_dashboard type=web_dashboard verify=true required=true config=devices/verify_dashboard.yaml}

Open the dashboard and confirm the live camera feed, arm state and voice path are healthy.

### Deployment Complete

Enter the same Jetson IP address used in Step 1 for remote deployment, or `localhost` for local deployment. The dashboard URL is `http://<jetson>:8776`.

- Camera frames are refreshing: perception is up
- State JSON is present: the serial link is up

Then the end-to-end voice test — say near the mic:

> **"Hey Jarvis, wave"**

The arm waves and the speaker confirms. Voice + LLM + arm control all work now. Grasping needs one more step: calibration.

### Troubleshooting

| Symptom | Fix |
|---|---|
| No camera image | Gemini 2 on a USB 2 port, or another process holds the camera — replug into USB 3.0, restart the `rebot-arm` container |
| No voice response | `docker logs voice-rebot-arm \| grep -i wake`; check the audio uid input matches `id -u` |
| `edge-llm` unhealthy for long | Engine still downloading/warming — normal on first boot |
| Disk slowly fills with `tegra-xusb: buffer overrun` kernel logs | JetPack driver logs; harmless but can take gigabytes over weeks. Filter those lines: `echo ':msg, contains, "buffer overrun event for slot" stop' \| sudo tee /etc/rsyslog.d/30-tegra-xusb-spam.conf && sudo systemctl restart rsyslog` |

## Step 3: Hand-Eye Calibration — unlocks grasping {#handeye type=manual required=false}

Finish one-time hand-eye calibration before using grasp commands.

### Prerequisites

Each unit needs its own calibration. Until `/opt/rebot-models/hand_eye.npz` exists, grasp commands detect objects but do not move the arm. One-time, ~30 minutes:

1. Download and print the [official ArUco calibration PDF](https://raw.githubusercontent.com/Seeed-Projects/reBot-DevArm-Grasp/main/aruco100x100.pdf) (DICT_4X4_50, ID 0, nominal 100 mm), then **measure the printed black outer square with a ruler** — printers rescale. A 1 mm error in that value corresponds to about a 1 cm grasp offset.
2. Tape the board flat on the table ~65 cm in front of the arm base.
3. Follow the collection + solve procedure in the [repository RUNBOOK §3.2](https://github.com/suharvest/openvoicestream/blob/main/agent/ovs_agent/apps/voice_rebot_arm/RUNBOOK.md) — the arm sweeps ~16 poses over the board, then solves the transform (target mean error < 5 mm).
4. Copy the resulting `hand_eye.npz` to `/opt/rebot-models/` and restart the `rebot-arm` container.

### First grasp

Place a small cardboard box (each face under 9.5 cm) about 25–30 cm in front of the arm, roughly centered, and say:

> **"Hey Jarvis, grab the box"**

The arm scans, announces what it found, grasps, lifts and carries it home. Then try a cup, a banana, an orange, then an opaque bottle (standing).

**Known-good placements**: straight ahead or moderately left/right of center. **Use opaque objects** — the depth camera cannot see transparent bottles.

### Troubleshooting

| Symptom | Fix |
|---|---|
| "I couldn't find the …" occasionally | Detection confidence is marginal at some angles — repeat the command; move the object toward the center |
| "The box is too big for me to grip" | Every visible face exceeds the 0.100 m jaw — expected; use a smaller object or turn a narrow face toward the arm |
| First attempt fails, retry works | Occasional; retry the command |
| Grasp lands centimeters off | Recalibrate — and re-measure the printed marker size (step 1 above) |
| Arm joints fault (`status_code=12`) | The stack clears this latched fault automatically at startup; if it persists after a container restart, power-cycle the arm |
| Arm was power-cycled and now ignores commands | Run `docker restart voice-rebot-arm`; a changed `/dev/ttyACM*` number is picked up automatically. |
| Detection is slow | The stack fell back to ONNX Runtime. Check the first line of `docker logs voice-rebot-arm`, then `docker logs voice-rebot-arm-model-init-1` for the reason |
| Restarting the stack re-downloads several GB | Do not use `docker compose down -v` (it deletes the model data); use `down` or `restart` |
