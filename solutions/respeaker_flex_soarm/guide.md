## Preset: Voice Control Your SO-ARM {#default}

Deploy a voice-controlled robotic arm in one step: a single Docker container on the Jetson handles wake word detection, speech recognition, LLM reasoning, TTS reply, and SO-ARM motor control.

| Device | Purpose |
|--------|---------|
| SO-ARM101 Follower Arm | 6-DoF robotic arm — receives `send_action` via USB serial |
| reComputer Super J4012 | Jetson Orin NX 16GB — runs the voice + arm container |
| reSpeaker Flex XVF3800 | 4-microphone array for far-field voice capture |
| Speaker | Output for the assistant's voice replies |

**What you'll get:**
- A robotic arm you control hands-free with natural language
- Wake word activation ("Hey Jarvis") — arm listens only when called
- Fully local AI: Paraformer ASR + Qwen3-4B-AWQ LLM + Matcha-TTS, all on the Jetson GPU
- A library of named poses + gesture sequences, editable as YAML without rebuilding the image
- Live joint state at `GET /observation` for integration with other solutions

**Requirements:** SO-ARM101 · Jetson Orin NX 16GB · reSpeaker Flex XVF3800 · Speaker · Internet on first boot (to pull images + warm engine)

> First deploy takes 5-10 minutes while it pulls ~10 GB of images and warms the Qwen3 TensorRT engine. Subsequent boots start in seconds.

## Step 1: Prepare the Arm (first time only) {#arm_prep type=manual required=false}

A brand-new SO-ARM kit needs three one-time setup tasks from the upstream wiki before the container can drive it. Skip this step if you've already done it on this arm.

### Wiring

On the Jetson (or any Linux host with USB to the arm), follow the upstream walkthrough for each of the three tasks. Photos + interactive prompts are all on the wiki.

1. **[Find the USB port](https://wiki.seeedstudio.com/lerobot_so100m_new/#find-the-usb-ports)** — `lerobot-find-port` tells you which `/dev/ttyACM*` is the arm
2. **[Configure motor IDs](https://wiki.seeedstudio.com/lerobot_so100m_new/#configure-the-motors)** — factory servos are all ID 1; plug one at a time, the script re-IDs them 1–6
3. **[Calibrate](https://wiki.seeedstudio.com/lerobot_so100m_new/#calibrate)** — pose to mid-position + sweep each joint so `/observation` returns normalized -100..100 (body joints) / 0..100 (gripper)

The calibration file lands at `~/.cache/huggingface/lerobot/calibration/robots/so_follower/<arm_id>.json`. Keep `<arm_id>` consistent with `ARM_ID` in Step 2.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Only the gripper twitches when commanded | Motor IDs not assigned — redo Configure the Motors from the table above |
| `/observation` returns 1500 / 2048 instead of `-100..100` | Calibration missing — redo Calibrate. Demo still runs without it but joint values won't be normalized |
| Servo middle drifted out of range / `Magnitude exceeds 2047` | Run the mid-position tool from [Seeed_RoboController](https://github.com/Seeed-Projects/Seeed_RoboController), then redo Calibrate |
| Calibrated on a different host | Mount `~/.cache/huggingface/lerobot/calibration` into the container (`-v` same path), so the JSON is visible at runtime |

## Step 2: Deploy Voice Arm {#voice_arm type=docker_deploy required=true config=devices/voice_brain.yaml}

Deploy the voice + arm container to the Jetson. The container probes the SO-ARM serial port and microphone on first boot, writes default `actions.yaml` / `prompt.yaml` if they're missing, then starts the voice pipeline plus an HTTP server on port 8765 for `GET /observation`.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not installed | JetPack 6.x ships Docker by default. Run `docker --version` to confirm. |
| Container exits immediately | `docker logs voice-arm` — typically `seeed-voice` or `edge-llm` haven't finished health-checking yet. Wait 5-10 minutes on first boot for the Qwen3 engine warmup, then retry. |
| Wake word never triggers | Confirm the reSpeaker is plugged in **before** deployment. Check `docker logs voice-arm` for the auto-selected mic. |
| Arm not moving | Check the SO-ARM is connected over USB-C (typically `/dev/ttyACM0`). The container scans `/dev/ttyACM*` on startup; the log shows which port it bound to. |
| TTS / STT errors | Check `docker logs seeed-voice` — model download may still be in progress on first boot. |
| LLM errors / hangs | Check `docker logs edge-llm` — first boot downloads the Qwen3 TensorRT engine (~5 GB) and runs a warmup inference before becoming healthy. |

### Target {#local type=local config=devices/voice_brain.yaml}

### Target {#jetson type=remote config=devices/voice_brain.yaml default=true}

## Step 3: Verify Arm State {#verify_arm type=robot_inspect verify=true required=true config=devices/verify_arm.yaml}

Live joint state at 5 Hz plus an action recorder that grows the gesture library at runtime — no image rebuild.

### Default voice commands

Out of the box the arm understands these gestures. Say the wake word **"Hey Jarvis"** first, then the command (phrasing is flexible — the LLM matches intent, not exact words). You can edit, delete, or add to these later (see *Teach it new gestures* below).

| Gesture | Say something like… |
|---------|---------------------|
| Home / reset | "go home", "reset" |
| Ready to pick | "get ready to pick", "pick position" |
| Open gripper | "open gripper", "open the hand" |
| Close gripper | "close gripper", "grab", "hold" |
| Look up | "look up" |
| Look down | "look down" |
| Wave | "wave", "say hi" |
| Nod (yes) | "nod", "say yes" |
| Shake head (no) | "shake head", "say no" |

### Verification

1. With the arm idle, all six `*.pos` fields should show a finite number (no `NaN`).
2. Say **"Hey Jarvis, wave hello"** — values change while the arm moves.
3. (Optional) Teach a gesture: **Disable Torque** → pose by hand → name it → **Trigger phrase** (LLM uses this to decide *when* to fire) → **Observe → Add** each frame → **Enable Torque** → **Test** → **Save**, then speak it to confirm.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Panel shows the fallback message | The container isn't running yet, or port 8765 isn't reachable from the App. Confirm Step 1 finished and the Jetson IP is reachable. |
| Fields are all `NaN` | The SO-ARM serial port isn't bound. Replug USB and restart the container. |
| Joint values don't change when arm moves | Container connected to the wrong device. Check `docker logs voice-arm` for the detected port. |

### Deployment Complete

Your SO-ARM is now voice-controlled — try saying "Hey Jarvis, wave hello".

#### Teach it new gestures

To add a new gesture, scroll to the **Record Action** panel under the live-state view in Step 2:

1. **Click "Disable Torque" first** (in the Torque row above the recorder) — forcing the joints by hand while torque is engaged damages the servos
2. Pose the arm by hand → click "Observe → Add" to capture a frame
3. Repeat for additional frames, then give the action a name and write a **trigger phrase** (e.g. "high five")
4. Click "Save" — the container is recreated automatically (~30 s, wake word won't respond during that window)
5. To dry-run the gesture, click "Test Action" — it re-enables torque and plays back the frames

Next time you say the trigger phrase, the arm performs the gesture.

#### Edit defaults / change conversation style

Open **Devices → Voice Brain → ⚙ Configure** to edit two things:

- **Action library** — every gesture the arm has learned. Tweak amplitude, delete ones you don't use.
- **Conversation rules** — the system prompt that shapes how the assistant replies (e.g. make answers shorter, more polite, change persona).

Saves take about 30 seconds to apply; the wake word doesn't respond during that window.

#### Read arm state from other systems

Any program on the same LAN can pull live joint data — useful for digital twins, demo recording, remote monitoring:

```bash
curl http://<jetson-ip>:8765/observation
# {"shoulder_pan.pos":0.12, ..., "gripper.pos":0.1}
```

#### Next Steps

- Hardware build details: [SO-ARM Wiki](https://wiki.seeedstudio.com/respeaker_flex_soarm/)
- If anything misbehaves, check `docker logs voice-arm`
- Wake word too sensitive or unresponsive — tune the threshold (`WAKEWORD_THRESHOLD`) and cooldown (`WAKEWORD_COOLDOWN`) in device settings
