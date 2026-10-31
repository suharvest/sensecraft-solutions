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

## Step 3: Bind to SenseCraft AI & Start Voice Dialog {#voice_agent_setup type=manual required=true verify=true}

1. Log in to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/).
2. In Models, find SenseCAP Watcher, select "Watcher Agent" -> "Bind Device", and enter the 6-digit code.
3. Click "Create" to build a new agent (e.g. Workstation Assistant or Receptionist), configuring system prompt and voice.
4. Say the wake word "Xiaozhi Xiaozhi" or speak directly to experience low-latency streaming conversation.
5. (Optional Workstation Link) In Agent Settings, scroll down to "MCP Setting" to get the WebSocket endpoint and connect business backends.

---

## Preset: Proactive Vision Wake {#vision_wake}

Add "eyes" to voice conversation: camera-based proactive visual wake-up greets you upon seeing you and initiates voice conversation, while explaining and tuning key vision detection parameters (threshold, duration, cooldown interval, and mode) over voice.

### Prerequisites

- SenseCAP Watcher already flashed with Xiaozhi firmware, connected to 2.4 GHz Wi-Fi, and paired with SenseCraft AI / Xiaozhi platform (completed via Preset 1: Voice Dialog & Agent). Active voice interaction is required for spoken parameter tuning and proactive greetings.

## Step 1: Enable Face Detection and Experience Proactive Greeting {#vision_wake_intro type=manual required=true verify=true}

1. Confirm vision detection mode: say to Watcher "Enable face detection" or "Set vision mode to 1" (`self.vision.mode: 1`). Watcher confirms entering on-device person/face detection mode.
2. Place the configured Watcher on your desk at face height (distance ~0.5 to 1.5 m).
3. Walk up to Watcher and pause for longer than the validation duration (default 3 s):
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

### Prerequisites

- SenseCAP Watcher connected to computer via USB-C data cable.
- Watcher already flashed with Xiaozhi firmware, connected to 2.4 GHz Wi-Fi, and paired with SenseCraft AI / Xiaozhi platform (completed via Preset 1: Voice Dialog & Agent). Active voice dialog is required for named greeting responses and recognition queries.

## Step 1: Flash Himax WE2 AI Models {#face_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

1. Connect Watcher and select the SERIAL-A port (the lower-numbered port on macOS/Linux, e.g. `ttyACM0`).
2. Flash Himax WE2 AI models (SCRFD 500M + MobileFaceNet 128D).

---

## Step 2: Connect ESP32 Main Controller {#face_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Face database embeddings are stored in ESP32-S3 local NVS flash:
1. Select the SERIAL-B port (the ESP32-S3 serial port).
2. If already flashed in stage 1, select the port to connect; if not, flash the Xiaozhi firmware.

---

## Step 3: Enrol Face Database {#face_enroll type=serial_camera config=devices/face_enroll.yaml required=true}

Connect via USB to manage the local face database:

1. Click **Connect** to start real-time camera preview (reads from Himax port).
2. Click **Enrol** in the Face Database panel (reads/writes NVS via ESP32 port) and enter a name.
3. Face the camera in good lighting for ~5 seconds to extract the 128D embedding.
4. Up to 20 faces stored in on-device NVS.

---

## Step 4: Switch to Face Recognition Mode & Greet {#face_demo type=manual required=true}

Disconnect USB cable; Watcher runs standalone:

1. **Enable Recognition Mode**: Say to Watcher "Enable face recognition" or "Set vision mode to 2" (`self.vision.mode: 2`).
2. **Familiar Greeting:** When an enrolled person approaches, Watcher extracts features locally and greets them by name (e.g. "Hello, John!").
3. **Stranger Alert:** When an unrecognised person approaches, Watcher notes an unknown visitor.
4. **Voice Commands:**
   - "Who do you know?": lists enrolled names.
   - "Can you recognise me?": captures live frame and tests recognition.
   - "Enable familiar mode": mutes greetings for known faces (`mode: 3`); only alerts on strangers.

---

## Preset: reTerminal D1001 Touch Agent {#d1001_touch_agent}

Deploy a desktop voice agent on the reTerminal D1001 equipped with an ESP32-P4 processor and an 8-inch capacitive touch screen. Supports on-screen touch Wi-Fi configuration, proactive visual greeting via the onboard camera, and local HTTP notification card push.

- **Hardware:** reTerminal D1001, USB-C data cable, Type-C power supply (5V/3A recommended).
- **Network:** 2.4 GHz Wi-Fi.
- **Account:** [Xiaozhi Console](https://xiaozhi.me) or [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/) (free registration).

## Step 1: Flash D1001 Firmware {#d1001_flash type=esp32_usb required=true config=devices/d1001_esp32.yaml}

Flash the Xiaozhi voice and edge vision firmware onto the reTerminal D1001.

### Wiring and Flashing

1. Connect the reTerminal D1001 to your computer via USB-C cable.
2. Select the automatically detected serial port (ESP32-P4 native USB-Serial-JTAG: `/dev/cu.usbmodem*` on macOS, `/dev/ttyACM*` on Linux, USB JTAG/serial port on Windows).
3. Click the flash button to write the multi-partition firmware.

### Troubleshooting

| Symptom | Solution |
|---|---|
| Serial port not found | Ensure you are using a data-capable USB-C cable and direct USB port (avoid hubs) |
| Flashing interrupted or failed | Unplug and reconnect the USB-C cable, then retry flashing |

---

## Step 2: Touch Network Setup & Device Binding {#d1001_touch_setup type=manual required=true verify=true}

1. **On-Screen Touch Wi-Fi Setup**: After flashing, the device restarts. On initial boot without network configuration, the system automatically displays the Wi-Fi list, or tap the network icon in the top-left corner of the screen to open it. Select your 2.4 GHz Wi-Fi network and enter the password using the on-screen soft keyboard to connect.
2. **Platform Access & Binding**: Once connected, the screen displays a **6-digit pairing code**. Log in to the [Xiaozhi Console](https://xiaozhi.me) or [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/), enter the 6-digit verification code under device management to complete binding, and start voice conversations.
3. **Visual Proactive Greeting & Card Push**:
   - **Mode 1 Edge Vision Greeting**: While the device is idle, the onboard camera detects human presence locally using the esp-dl face detection model and automatically triggers a proactive voice greeting to start a conversation. A cooldown period is included to avoid repeated interruptions within a short window.
   - **Local Card Push**: Once the device connects to Wi-Fi, its local IP (e.g. `192.168.x.x`) is displayed in the top-left corner of the screen. Supports pushing cards over port 8080 on the same local network. Minimal verification command:
     ```bash
     curl -X POST http://<DEVICE_IP>:8080/panel/markdown \
       -H "Content-Type: application/json" \
       -d '{"text":"# Hello, D1001\nConnected to LAN!"}'
     ```
