## Preset: Voice Control Your LeKiwi {#default}

Build a voice-controlled robot that understands natural language commands and moves in any direction — forward, backward, strafe, turn — just by speaking to it.

| Device | Purpose |
|--------|---------|
| LeKiwi Kit | 3-wheeled Kiwi-drive chassis with 3× STS3215 smart servos |
| XIAO ESP32S3 | Motor controller — receives serial commands from Raspberry Pi |
| Raspberry Pi 5 | Voice AI brain — runs wake word detection, STT, LLM, and TTS |
| reSpeaker Flex XVF3800 | 4-microphone array for far-field voice capture |

**What you'll get:**
- A robot you control hands-free with natural language
- Wake word activation ("Hey Jarvis") — robot listens only when you call it
- Groq-powered AI: Whisper (speech recognition) + Llama 3 (reasoning) + Orpheus (voice reply)
- Kiwi-drive omnidirectional movement + emergency stop

**Requirements:** LeKiwi Kit · XIAO ESP32S3 · Raspberry Pi 5 · reSpeaker Flex XVF3800 · Speaker · Groq API key (free) · Internet access on Pi

## Step 1: Assemble Hardware {#hardware type=manual required=true}

Before deploying any software, you need to physically build the robot.

### Wiring

1. **Assemble the chassis** — Follow the [LeKiwi Assembly Tutorial](https://wiki.seeedstudio.com/lerobot_lekiwi/#assembly) to build the frame and mount the wheels/servos. Don't connect the servo bus to the XIAO yet — Steps 2 and 3 flash the ID setter firmware and assign servo IDs one at a time.
2. **Connect reSpeaker Flex** — Plug the reSpeaker Flex into a USB port on the Raspberry Pi
3. **Connect XIAO ESP32S3** — Use a USB-C cable to connect the XIAO to the Raspberry Pi
4. **Connect speaker** — Plug speakers into the Raspberry Pi's audio jack or USB port

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Servo not responding | Complete Steps 2 and 3 first: flash the servo ID setter firmware, then use the serial wizard to assign IDs 1, 2, and 3 |
| Servo wiring confusion | Servo 1 = front wheel, Servo 2 = rear-left, Servo 3 = rear-right |
| USB device not detected | Try a different USB cable — some are power-only with no data lines |

## Step 2: Flash Servo ID Setter {#esp32_id type=esp32_usb required=true config=devices/esp32_id_setter.yaml}

Flash the servo ID configuration firmware to your XIAO ESP32. This firmware assigns unique IDs (1, 2, 3) to your STS3215 servos through an interactive serial console in the next step.

### Wiring

1. Plug the XIAO ESP32 into your computer via USB-C
2. Click **Deploy** to flash the firmware
3. Proceed to Step 3 to set servo IDs

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Flash fails / device not detected | Hold the BOOT button on XIAO, press RESET, then release BOOT |

## Step 3: Set Servo IDs {#servo_wizard type=serial_wizard required=true config=devices/servo_id_wizard.yaml}

Use the serial console to assign IDs to your servos one at a time. The firmware will guide you — connect each servo when prompted and press Enter.

### Wiring

1. Click **Connect** to open the serial console
2. Connect ONE servo at a time to the XIAO servo bus when prompted:
   - **FRONT wheel** → ID 1
   - **REAR-LEFT wheel** → ID 2
   - **REAR-RIGHT wheel** → ID 3
3. Use the **Send Enter** button or type in the input field and press Enter to proceed
4. After all three IDs are set, power off and reconnect all servos

### Troubleshooting

| Issue | Solution |
|-------|----------|
| No servo detected | Check servo power wiring and try the **Rescan** button |
| Multiple servos detected | Connect only ONE servo at a time to the bus |
| ID setter shows nothing | Disconnect and reconnect the XIAO USB, then click **Connect** again |

## Step 4: Flash Motor Controller {#esp32 type=esp32_usb required=true config=devices/esp32.yaml}

Flash the motor controller firmware. This handles Kiwi-drive kinematics and listens for serial commands from the Raspberry Pi.

### Wiring

1. Plug the XIAO ESP32 into your computer via USB-C
2. Click **Deploy** to flash the firmware
3. After flashing, reconnect the XIAO to the Raspberry Pi and power on the servos

### Verification

After flashing, the XIAO will boot and check for servos 1, 2, 3. The serial monitor (115200 baud) will show `Servo 1 OK`, `Servo 2 OK`, `Servo 3 OK` followed by `System ready!`.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Flash fails / device not detected | Hold the BOOT button on XIAO, press RESET, then release BOOT |
| Wrong USB port detected | Unplug other USB-serial devices and try again |
| Servos not found at boot | Check servo power. Run Steps 2-3 again if IDs aren't set |

## Step 5: Deploy Voice Brain {#voice_brain type=docker_deploy required=true config=devices/voice_brain_deploy.yaml}

Deploy the voice AI container to the Raspberry Pi on the robot (wake word + ASR + LLM + TTS all bundled in one image).

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not installed | Run `curl -fsSL https://get.docker.com \| sh` on the Pi |
| Container exits immediately | `docker logs lekiwi-voice` — usually a missing GROQ_API_KEY |
| Wake word never triggers | Make sure reSpeaker is connected before deployment. The container auto-selects the microphone; check `docker logs lekiwi-voice` for the selected input device |
| Robot not moving | Make sure the XIAO is connected to the Pi over USB-C and the motor controller firmware from Step 4 is running. The container auto-selects the ESP32 serial port |
| TTS / STT errors | GROQ_API_KEY is invalid, the Groq terms are not accepted, or the Pi cannot reach Groq |

### Target {#local type=local config=devices/voice_brain_deploy.yaml}

### Target {#raspberry_pi type=remote config=devices/voice_brain_deploy.yaml default=true}

## Step 6: Talk to Your Robot {#test type=manual verify=true required=true}

Now that everything is running, test your voice-controlled robot.

### Verification

1. Stand within ~1 metre of the robot
2. Say **"Hey Jarvis"** clearly — you should not hear a response yet (the robot is waiting for your command)
3. After the wake word, say a command like:
   - "move forward"
   - "turn left"
   - "strafe right"
   - "what can you do?"
4. The robot should respond verbally and then move

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Wake word never detected | Speak clearly within 1m of the mic. Check `docker logs lekiwi-voice` and confirm the detected microphone is the reSpeaker device |
| Robot moves wrong direction | Verify servo IDs 1, 2, 3 are assigned correctly and wheel angles are correct |
| Response is slow | Groq API latency. First request may take 2-3 seconds; subsequent ones are faster |
| Container keeps restarting | Check logs: `docker logs lekiwi-voice`. Verify GROQ_API_KEY is valid |
### Deployment Complete

Your LeKiwi robot is now voice-controlled.

#### Command Reference

| Phrase | Robot Action |
|--------|-------------|
| "move forward" / "go ahead" | Forward nudge |
| "go back" / "reverse" | Backward nudge |
| "turn left" / "rotate left" | Turn left nudge |
| "turn right" / "rotate right" | Turn right nudge |
| "strafe left" / "slide left" | Strafe left nudge |
| "strafe right" / "slide right" | Strafe right nudge |
| "keep going forward" / "continuously" | Continuous movement (until stop) |
| "stop" / "halt" / "emergency" | Emergency stop |

#### Advanced Commands

The robot also responds to:
- "what can you do?" — lists capabilities
- "increase speed" / "decrease speed" — adjusts nudge parameters
- Conversational queries — the LLM will chat naturally and reply via TTS

#### Next Steps

- Adjust nudge duration/speed by editing device settings and re-deploying
- Change TTS voice (Autumn, Tara, Leah, Dan, Mia, Zac) in device settings
- Check `docker logs lekiwi-voice` if the wake word is hard to trigger; the log shows which microphone was auto-selected
- [LeKiwi Voice GitHub](https://github.com/KasunThushara/Lekiwi-voice)
