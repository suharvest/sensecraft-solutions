## Preset: Voice Dialog & Agent {#voice_agent}

Experience low-latency streaming voice conversation with minimal hardware (one SenseCAP Watcher and a USB-C cable): connect Watcher to 2.4 GHz Wi-Fi, link to the SenseCraft AI platform via a 6-digit code, configure custom agent personalities, and start natural conversations.

- **Hardware:** SenseCAP Watcher, USB-C data cable; optional edge computer (e.g. reComputer R1100).
- **Network:** 2.4 GHz Wi-Fi.
- **Account:** [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/) (free registration) or [Xiaozhi App](https://github.com/78/xiaozhi-esp32).

## Step 1: Flash Xiaozhi Firmware {#voice_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Flash the Xiaozhi voice controller firmware onto Watcher.

### Wiring and Flashing

![Connect Device](gallery/watcher.svg)

1. Connect Watcher to your computer via USB-C cable.
2. Select the SERIAL-B COM port (Windows) or the higher-numbered port (macOS/Linux).
3. Click the flash button to write the firmware.

---

## Step 2: Connect Watcher & Get 6-Digit Code {#voice_network type=manual required=true}

1. Power on Watcher and connect to 2.4 GHz Wi-Fi via phone AP setup (Watcher-XXXX).
2. Once connected, Watcher restarts and displays a **6-digit pairing code** on screen.

---

## Step 3: Bind to SenseCraft AI & Start Voice Dialog {#voice_agent_setup type=manual required=true}

1. Log in to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/).
2. In Models, find SenseCAP Watcher, select "Watcher Agent" -> "Bind Device", and enter the 6-digit code.
3. Click "Create" to build a new agent (e.g. Workstation Assistant or Receptionist), configuring system prompt and voice.
4. Say the wake word "Xiaozhi Xiaozhi" or speak directly to experience low-latency streaming conversation.
5. (Optional Workstation Link) In Agent Settings, scroll down to "MCP Setting" to get the WebSocket endpoint and connect business backends.

---

## Preset: Proactive Vision Wake {#vision_wake}

Add "eyes" to voice conversation: camera-based proactive visual wake-up greets you upon seeing you and initiates voice conversation, while explaining and tuning key vision detection parameters (threshold, duration, cooldown interval, and mode) over voice.

- **Hardware:** SenseCAP Watcher, USB-C data cable.
- **Network:** 2.4 GHz Wi-Fi.

## Step 1: Experience Proactive Greeting {#vision_wake_intro type=manual required=true}

1. Place the configured Watcher on your desk at face height (distance ~0.5 to 1.5 m).
2. Walk up to Watcher and pause:
   - When the camera detects a person present, Watcher switches expressions and greets you proactively (e.g. "Hello! Good to see you!"), entering conversation without requiring a wake word.

---

## Step 2: Voice Query & Parameter Adjustment {#vision_wake_params type=manual required=true}

During the conversation, ask Watcher about its vision settings:

| Say to Watcher | Action & Effect |
|---|---|
| "Query vision parameters" | Watcher reports current confidence threshold, validation duration, and cooldown interval |
| "Set detection threshold to 80" | Adjusts confidence threshold (`threshold`, 0-100); higher values prevent false triggers |
| "Set duration to 2 seconds" | Sets required presence duration (`duration`, 0-60 s) before confirming detection |
| "Set cooldown interval to 10 seconds" | Sets cooldown interval (`interval`, 0-60 s) after conversation ends before re-waking |
| "Switch to face detection mode" / "Turn off vision wake" | Sets vision mode (`mode`): 0=off, 1=person detection, 2=face recognition, 3=familiar mute |

---

## Preset: On-Device Face Recognition {#face_recognition}

Go from detecting "a person" to recognising "who they are": activate the Himax WE2 NPU to run SCRFD and MobileFaceNet on-device, recognise registered faces by name, and maintain a local database of up to 20 people in NVS.

- **Hardware:** SenseCAP Watcher, USB-C data cable.
- **Network:** 2.4 GHz Wi-Fi.
- **Privacy:** Detection, alignment, and 128D embedding extraction happen entirely on-device; no facial photos uploaded to cloud.

## Step 1: Flash Himax WE2 AI Models {#face_himax_flash type=himax_usb required=true config=devices/watcher_himax.yaml}

1. Connect Watcher and select the SERIAL-A port (the lower-numbered port on macOS/Linux).
2. Flash Himax WE2 AI models (SCRFD 500M + MobileFaceNet 128D).

---

## Step 2: Enrol Face Database {#face_enroll type=serial_camera config=devices/face_enroll.yaml required=true}

Connect via USB to manage the local face database:

1. Click **Connect** to start real-time camera preview.
2. Click **Enrol** in the Face Database panel and enter a name.
3. Face the camera in good lighting for ~5 seconds to extract the 128D embedding.
4. Up to 20 faces stored in on-device NVS.

---

## Step 3: Experience Name Greeting & Familiar Mode {#face_demo type=manual required=true}

1. **Familiar Greeting:** When enrolled person approaches, Watcher greets them by name.
2. **Stranger Alert:** When an unrecognised person approaches, Watcher notes an unknown visitor.
3. **Voice Commands:**
   - "Who do you know?": lists enrolled names.
   - "Can you recognise me?": captures live frame and tests recognition.
   - "Enable familiar mode": mutes greetings for known faces; only alerts on strangers.
