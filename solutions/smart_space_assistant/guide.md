## Preset: Face Recognition {#face_recognition}

Add face recognition to your Xiaozhi, letting it recognize family and friends.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | AI voice assistant with camera |
| USB-C data cable | For firmware flashing |

**What you'll get:**
- Automatic greeting when recognized face appears
- Enroll and manage faces from the web panel (up to 20 people)
- Voice control to enable, query, and delete faces

**Requirements:** WiFi network · [Xiaozhi App](https://github.com/78/xiaozhi-esp32) for device binding

## Step 1: Flash Xiaozhi Firmware {#face_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Write the voice assistant program to the Watcher to enable voice interaction.

### Wiring

![Connect Device](gallery/watcher.svg)

1. Connect Watcher to computer via USB-C cable
2. Select the serial port above (choose one starting with wchusbserial)
3. Click the Flash button

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Serial port not found | Try a different USB cable or USB port |
| No serial data received | Hold BOOT button, press RESET, release BOOT, then retry |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Flash Face Recognition Firmware {#face_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

Write the face recognition program to the Watcher's AI chip.

### Wiring

![Connect Device](gallery/watcher.svg)

1. Ensure Watcher is connected to computer
2. Select the serial port above (choose one starting with usbmodem)
3. Click the Flash button
4. After clicking Flash, press the reset button on the device to enter flash mode

### Troubleshooting

| Problem | Solution |
|---------|----------|
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

| Problem | Solution |
|---------|----------|
| WiFi connection failed | Ensure using 2.4GHz network, check password |
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

| Problem | Solution |
|---------|----------|
| "Please complete Step X first" | Go back and select the correct serial port in the indicated step |
| Camera not showing | Check USB connection, try refreshing ports in Step 2 |
| Enrollment failed | Ensure good lighting, face the camera directly, try again |

### Deployment Complete

Face recognition is ready! Let's try it out.

**Step 1: Enroll faces from the panel above**

Use the **Face Database** panel to enroll family or colleagues (see "Register a New Face" above).

**Step 2: Enable face recognition by voice**

Unplug the USB cable, wake up the device by saying **"Xiaozhi Xiaozhi"**, then say:

> "Turn on face recognition"

Once confirmed, Watcher will automatically scan for faces while idle.

**Step 3: Experience automatic recognition**

Walk in front of the Watcher — it will recognize you and greet you by name!

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

Cast Xiaozhi conversations to TV or large display, ideal for exhibition halls, meeting rooms and multi-person scenarios.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | AI voice assistant |
| reComputer R1100 | Edge computing device, runs display service |
| HDMI Display | Shows cast content |

**What you'll get:**
- Real-time conversation display on big screen
- Fullscreen mode for presentations
- mDNS auto-discovery - connect by voice command
- Narrate mode - AI controls background images for storytelling & guided tours

**Requirements:** All devices on same network

## Step 1: Flash Watcher Firmware {#display_watcher type=esp32_usb required=true config=devices/display_watcher.yaml}

Write the voice assistant program to the Watcher for display casting.

### Wiring

![Connect Device](gallery/watcher.svg)

1. Connect Watcher to your computer using USB-C cable
2. Select the serial port above
3. If not detected, try a different USB port or cable

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Serial port not found | Try a different USB cable or USB port |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Deploy Display Service {#display_service type=docker_deploy required=true config=devices/display_service_deploy.yaml}

Start the display service that shows conversations on your screen.

### Target {#display_service_local type=local config=devices/display_service_deploy.yaml}

Deploy the display service on your local computer.

### Wiring

![Architecture](gallery/architecture.svg)

1. Ensure Docker is installed and running
2. Set a display name (e.g. "Living Room Display") for mDNS discovery
3. Click Deploy button to start services

### Troubleshooting

| Problem | Solution |
|---------|----------|
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

| Problem | Solution |
|---------|----------|
| SSH connection failed | Check IP address and credentials |
| Docker pull failed | Check network connection, retry deployment |
| Watcher can't find display | Ensure both devices on same network, check firewall |

### Deployment Complete

Display cast is ready!

**Test it:**
1. Open `http://<device-ip>:8765` on display browser
2. Press `F` for fullscreen mode
3. Say "Cast to [Display Name]" to start

**Voice commands:** "Start casting", "Stop casting", "Cast status"

**Narrate Mode (New):**
The display now supports a narrate mode where AI can control background images — ideal for presentations, storytelling, and guided tours.

1. Click the gear icon (top-left) to open the config panel
2. Toggle "Enable Narrate Mode"
3. Enter your Xiaozhi WebSocket MCP URL to enable AI-driven image switching
4. Add trigger rules: keyword + image URL pairs for automatic background changes
5. Press `N` to toggle narrate mode, click the PiP window to resize it
