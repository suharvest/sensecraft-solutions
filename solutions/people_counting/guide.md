## Preset: Grove Vision AI Module V2 {#grove_vision_ai_v2}

Turn a Grove Vision AI Module V2 into a standalone people counter. The module detects people, tracks them across frames, counts line crossings in both directions, and reports how many people are inside each zone — all on the module itself.

| Device | Purpose |
|--------|---------|
| Grove Vision AI Module V2 | Camera + Himax WE2 (Cortex-M55 + Ethos-U55 NPU), runs everything on device |
| USB-C data cable | Flashing and live preview |

**What you'll get:**
- Up to 4 counting lines with separate in/out totals
- Up to 4 zones with a live occupancy number
- Person detection and multi-object tracking running on the NPU
- No network and no cloud — video travels over the USB cable to the app on your own computer, nothing else

**Measured on device:** 48 ms inference per frame, about 13 fps end to end (240x240 input, Swift-YOLO Nano single-class person model, 92.6% mAP after INT8 quantization).

**Requirements:** A computer with a free USB-C port. No WiFi, no account, no server.

## Step 1: Flash Firmware and Model {#grove_himax type=himax_usb required=true config=devices/grove_himax.yaml}

Write the people counting firmware and the person detection model to the module.

### Wiring

1. Connect the Grove Vision AI Module V2 to your computer with a USB-C **data** cable (charge-only cables will not enumerate a serial port)
2. The port is usually selected for you. If not, pick the CH343 port — on macOS it looks like `/dev/cu.usbmodem*`, on Linux `/dev/ttyACM0`, on Windows a `USB-Enhanced-SERIAL CH343` COM port
3. Click **Flash**

Flashing writes two things: the firmware image, then the person detection model at flash address `0x700000`. The model file carries 16KB of appended padding — this is intentional, it works around an xmodem transfer truncation near the end of the file. Total transfer takes a couple of minutes at 921600 baud.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| No serial port listed | Use a USB-C cable that carries data, or try another USB port |
| Flash never starts | Unplug and reconnect the module, then retry |
| Flash stalls partway | Close any other program holding the serial port (serial monitor, another IDE), reconnect and retry |
| Flash finishes but the next step shows no video | Unplug and reconnect the module so the new firmware boots cleanly |

---

## Step 2: Set Up Counting Zones {#counting_panel type=serial_camera required=true config=devices/counting_panel.yaml}

Draw your counting lines and zones on the live camera view, then watch the counts update.

### How to Use

1. Click **Connect** — the module loads the person detection model and starts streaming. The first frame takes a few seconds while the model loads
2. You'll see the live 240x240 view with a box around each detected person
3. Use the **Counting** panel below the video to draw lines and zones

### Draw a Counting Line

1. Click **Add Line** in the Counting panel
2. Drag across the video where you want the boundary — a doorway, an aisle mouth, the top of a staircase
3. The line gets an **In** side and an **Out** side; swap them if the direction reads backwards
4. Walk across the line and watch the In/Out totals increment

Up to 4 lines are supported. Each keeps its own In and Out totals.

### Draw a Zone

1. Click **Add Zone** in the Counting panel
2. Drag a rectangle over the area you care about — a queue, a waiting area, a meeting table
3. The zone shows how many tracked people are inside it right now

Up to 4 zones are supported.

### Pick the Tracking Anchor

Each tracked person is reduced to a single point that the line and zone tests use. The **anchor mode** control chooses which point:

| Anchor | Suggested for |
|--------|---------------|
| Box center | Straight-on / eye-level mounting, and top-down mounting |
| Box bottom center (feet) | Tilted overhead mounting |

For a tilted overhead view, prefer the bottom-center anchor. With the box center, a person's bounding box grows as they approach the camera, which drags the center point across a nearby line and can register a crossing that never happened. The feet anchor stays put on the floor plane.

### Mounting Suggestions

These are starting points, not guarantees — the right height and angle depend on your ceiling and your traffic.

- **Tilted overhead** (camera angled down at the walking path) is the usual choice. It keeps people's bodies visible in a familiar pose, which is what the detector was trained on. Pair it with the feet anchor.
- **Straight down** (camera pointing at the floor) minimizes people occluding each other, which helps in dense traffic. The trade-off: the model was trained on conventional viewpoints, so detection recall from directly overhead may drop. Test it in your own space before committing.
- Keep the counting line away from the frame edge, so a person is tracked for a few frames on both sides of it.
- Even, consistent lighting matters more than bright lighting. Strong backlight from a window or doorway behind the subject is the common failure case.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "Please complete Step 1 first" | Go back to Step 1 and select the serial port |
| Video stays black | Reconnect the USB cable, then click Connect again |
| No detection boxes at all | Check that Step 1 flashed the model successfully; re-flash if unsure |
| Counts jump up and down as someone walks toward the camera | Switch the anchor to box bottom center (feet) |
| The same person is counted twice | Move the counting line further from the frame edge so the track is stable on both sides |
| In and Out are reversed | Flip the line direction in the Counting panel |

### Deployment Complete

The module is counting. Everything below runs on the module itself — the app is only showing you what it reports.

**Try it:**
1. Walk across a counting line in one direction, then the other — In and Out should each increment once
2. Stand inside a zone and watch the occupancy number
3. Have a second person join you to see multi-target tracking

**Where the data goes:** counting events and per-frame detections come out of the USB serial port as SSCMA JSON, so you can pipe them into your own script, dashboard, or gateway. The live preview shares that same USB serial link — the module sends a JPEG with each result so the app can draw your lines and zones over the real scene. Everything stays between the module and this computer: nothing is uploaded, and no image reaches a network or a cloud service.

---

## Step 3: Optional — Add XIAO ESP32-S3 for Wireless Wi-Fi & MQTT Reporting {#xiao_wifi type=manual required=false}

Add a **Seeed Studio XIAO ESP32-S3 (Pre-Soldered)** when the counter must run without a host PC and report counts over Wi-Fi or MQTT.

### Wiring

1. Disconnect USB power from the Grove Vision AI Module V2.
2. Align and insert the **XIAO ESP32-S3 (Pre-Soldered version)** into the female pin headers on the back of the Grove Vision AI Module V2.
3. **Check orientation**: The Type-C connector on the XIAO must face the same direction as the Type-C connector on the Grove Vision AI V2. The boards communicate directly over onboard UART pins.

### Deployment Complete

Once the wireless bridge firmware is flashed onto the XIAO, configure Wi-Fi and MQTT without needing an IDE or serial drivers:

1. **Connect to Setup AP**: On first boot or when disconnected, the XIAO broadcasts an open Wi-Fi network named `XIAO-Counter-XXXX`.
2. **Open Web Portal**: Connect your phone or laptop to `XIAO-Counter-XXXX`. A captive portal will pop up automatically (or open your browser to `http://192.168.4.1`).
3. **Select Wi-Fi**: Scan for nearby 2.4GHz networks, choose your site Wi-Fi, and enter the password.
4. **Configure MQTT / Endpoint**:
   - **Broker IP / Host**: Enter your MQTT server address (e.g. Home Assistant IP, port `1883`).
   - **Topic Prefix**: Defaults to `people_counter`; events publish to `people_counter/{device_id}/events`.
   - **Credentials**: Enter username/password if authentication is enabled; optional Home Assistant discovery toggle.
5. **Save & Connect**: Click "Save & Reboot". Configuration is encrypted to internal flash, the setup AP shuts down, and the XIAO connects to site Wi-Fi.

- **Sample MQTT Event Message** (published whenever a line crossing occurs or zone occupancy changes):
  ```json
  {
    "device_id": "xiao_esp32s3_a1b2",
    "timestamp": 1789881234,
    "line_crossings": [
      { "line_id": 1, "in": 42, "out": 35 }
    ],
    "zones": [
      { "zone_id": 1, "occupancy": 3 }
    ],
    "status": "online"
  }
  ```
If site Wi-Fi drops, the Grove Vision AI V2 keeps counting locally. The XIAO retries in the background and publishes the latest aggregate counts after the connection returns, without blocking vision inference.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| Setup AP `XIAO-Counter-XXXX` does not appear | Check the XIAO orientation and ensure the Grove Vision AI module has power |
| Captive portal does not open automatically | Open a browser manually and navigate to `http://192.168.4.1` |
| Cannot connect to site Wi-Fi | Verify the 2.4GHz Wi-Fi SSID and password |
| MQTT broker does not receive events | Verify the broker IP address, port, and authentication credentials |
