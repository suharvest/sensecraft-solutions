## Preset: Face Recognition {#face_recognition}

SenseCAP Watcher recognizes enrolled faces and greets them. Enroll and manage faces from the panel (up to 20 people), and enable, query or delete faces by voice.

- **Devices:** SenseCAP Watcher, USB-C data cable.
- **Network:** 2.4 GHz WiFi.
- **Account:** [Xiaozhi App](https://github.com/78/xiaozhi-esp32) for device binding.

## Step 1: Flash Xiaozhi Firmware {#face_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Write the voice assistant program to the Watcher to enable voice interaction.

### Wiring

![Connect Device](gallery/watcher.svg)

1. Connect Watcher to computer via USB-C cable
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-B** on Windows, or the higher-numbered one on macOS / Linux (`...53` / `ttyACM1`)
3. Click the Flash button

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Serial port not found | Try a different USB cable or USB port |
| Wrong port picked (flash hangs or fails instantly) | Try the other CH342 port in the list |
| No serial data received | Hold BOOT button, press RESET, release BOOT, then retry |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Flash Face Recognition Firmware {#face_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

Write the face recognition program to the Watcher's AI chip.

### Wiring

![Connect Device](gallery/watcher.svg)

1. Ensure Watcher is connected to computer
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-A** on Windows, or the lower-numbered one on macOS / Linux (`...51` / `ttyACM0`) — not the same port as the previous step
3. Click the Flash button
4. After clicking Flash, press the reset button on the device to enter flash mode

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Device not responding | Unplug and reconnect the USB cable |
| Flash stuck or fails | Press the reset button and try again |
| Flash fails repeatedly | Use a different USB cable or port |
| Flash fails at 99% or restarts mid-flash | Close other apps using serial ports, reconnect USB and retry |

---

## Step 3: Configure Xiaozhi {#face_configure type=manual required=false}

Connect the Watcher to WiFi and bind it to your account using the mobile app.

### Connect to WiFi

Device will prompt for network setup on first boot. Follow voice instructions to connect to WiFi.

### Bind Xiaozhi Account

1. Open Xiaozhi App
2. Scan the QR code displayed on device
3. Complete the binding process

### Test Voice

Wake up the device by saying "Xiaozhi Xiaozhi" to test voice interaction. If it responds normally, the setup is successful.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| WiFi connection failed | Ensure using 2.4 GHz network, check password |
| QR code not showing | Restart device, wait for boot complete |

---

## Step 4: Face Database Management {#face_enroll type=serial_camera config=devices/face_enroll.yaml required=false}

Manage the face recognition database through the app interface.

### How to Use

1. Click **Connect** to start the camera preview
2. You'll see a live feed with face detection boxes
3. Use the **Face Database** panel below to manage enrolled faces

### Register a New Face

1. Click **Register** in the Face Database panel
2. Enter a name for the person
3. Click **Start Capture** — face the camera with good lighting
4. Wait for the capture to complete (5 seconds)
5. The new face will appear in the table

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Please complete Step X first" | Go back and select the correct serial port in the indicated step |
| Camera not showing | Check USB connection, try refreshing ports in Step 2 |
| Enrollment failed | Ensure good lighting, face the camera directly, try again |

### Deployment Complete

**Step 1: Enroll faces**

Enroll faces in the **Face Database** panel (see "Register a New Face" above).

**Step 2: Enable face recognition by voice**

Unplug the USB cable, wake up the device by saying **"Xiaozhi Xiaozhi"**, then say:

> "Turn on face recognition"

Once confirmed, Watcher will automatically scan for faces while idle.

**Step 3: Experience automatic recognition**

Walk in front of the Watcher; it recognizes you and greets you by name.

**Voice Commands**

| Say this | Effect |
|----------|--------|
| "Turn on face recognition" | Enable recognition (required on first use) |
| "Turn off face recognition" | Disable recognition |
| "Delete face XXX" | Remove an enrolled face |
| "Who do you know" | List all enrolled faces |
| "Turn on familiar mode" | Only alert for strangers, ignore familiar faces |
| "Turn off familiar mode" | Greet everyone |

---

## Preset: Display Cast {#display_cast}

Show Xiaozhi conversations live on a TV or large display and connect to it by voice; narrate mode switches background images based on the conversation.

- **Devices:** SenseCAP Watcher, USB-C data cable, HDMI display; the display service runs on a reComputer R1100 or a local computer.
- **Network:** all devices on the same network.

## Step 1: Flash Watcher Firmware {#display_watcher type=esp32_usb required=true config=devices/display_watcher.yaml}

Write the voice assistant program to the Watcher.

### Wiring

![Connect Device](gallery/watcher.svg)

1. Connect Watcher to your computer using USB-C cable
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-B** on Windows, or the higher-numbered one on macOS / Linux (`...53` / `ttyACM1`)
3. Click the Flash button

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Serial port not found | Try a different USB cable or USB port |
| Wrong port picked (flash hangs or fails instantly) | Try the other CH342 port in the list |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Deploy Display Service {#display_service type=docker_deploy required=true config=devices/display_service_deploy.yaml}

Start the display service that shows conversations on your screen.

### Target {#display_service_local type=local config=devices/display_service_deploy.yaml}

Deploy on your local computer; Docker must be installed and running.

### Wiring

![Architecture](gallery/architecture.svg)

1. Ensure Docker is installed and running
2. Set a display name (e.g. "Living Room Display") for mDNS discovery
3. Click Deploy button to start services

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Docker not found | Install Docker Desktop |
| Port 8765 busy | Stop other services using this port |

### Target {#display_service_remote type=remote config=devices/display_service_deploy.yaml default=true}

Deploy the display service to reComputer R1100.

### Wiring

![Architecture](gallery/architecture.svg)

1. Connect reComputer to network and HDMI display
2. Enter IP address and SSH credentials
3. Set a display name (e.g. "Meeting Room Display") for mDNS discovery
4. Click Deploy to install on remote device

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| SSH connection failed | Check IP address and credentials |
| Docker pull failed | Check network connection, retry deployment |
| Watcher can't find display | Ensure both devices on same network, check firewall |

### Deployment Complete

**Test it:**
1. Open `http://<device-ip>:8765` on display browser
2. Press `F` for fullscreen mode
3. Say "Cast to [Display Name]" to start

**Voice commands:** "Start casting", "Stop casting", "Cast status"

**Narrate Mode:** switches background images based on the conversation.

1. Click the gear icon (top-left) to open the config panel
2. Toggle "Enable Narrate Mode"
3. Enter your Xiaozhi WebSocket MCP URL to enable AI-driven image switching
4. Add trigger rules: keyword + image URL pairs for automatic background changes
5. Press `N` to toggle narrate mode, click the PiP window to resize it

## Preset: reTerminal D1001 Voice Agent {#reterminal_d1001}

Run a Xiaozhi voice agent on the reTerminal D1001: wake-word conversation with barge-in, on-screen settings, camera face wake, and a LAN push panel on port 8080 (markdown to the screen, on-screen choices, camera snapshot).

- **Devices:** reTerminal D1001, data-capable USB-C cable.
- **Network:** 2.4 GHz WiFi.
- **Account:** [Xiaozhi App](https://github.com/78/xiaozhi-esp32) for device binding.

## Step 1: Flash D1001 Firmware {#d1001_esp32 type=esp32_usb required=true config=devices/d1001_esp32.yaml}

Write the voice agent firmware to the device.

### Wiring

1. Connect the D1001 to your computer via USB-C
2. The port is picked automatically (ESP32-P4 native USB, `usbmodem*` / `ttyACM*`)
3. Click the Flash button

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| Serial port not found | Use a data-capable USB-C cable, try another port |
| Flash failed midway | Reconnect the cable and retry; avoid USB hubs |

---

## Step 2: Connect and Bind {#d1001_setup type=manual required=false}

Set up WiFi on the touch screen, then bind the device.

### Connect to WiFi

1. The device prompts for setup on first boot
2. Tap the network icon in the status bar
3. Pick your 2.4 GHz network and enter the password

### Bind Xiaozhi Account

1. Open the Xiaozhi App
2. Scan the QR code on the device
3. Complete the binding

### Test Voice

Say "Xiaozhi Xiaozhi" to wake it; repeat mid-reply to interrupt.

### Optional: Face Wake

Tap the person icon for face settings: mode (off / detect-wake / recognize-wake), confirm duration, cooldown, endpoint.

### Troubleshooting

| Symptom | Fix |
|---------|-----|
| WiFi connection failed | Ensure a 2.4 GHz network; recheck the password on screen |
| No QR code | Wait for boot to complete, or restart the device |
