## Preset: Tier 0 · Cloud {#trial}

Only a SenseCAP Watcher is needed, no host. Inventory data and the voice service are hosted on the Seeed cloud.

- **Network:** the Watcher needs 2.4GHz WiFi with internet access (5GHz is not supported).
- **Account:** a SenseCraft account (free signup); the warehouse system is registered with the Watcher's device ID, with no separate admin account.
- **Limits:** monthly subscription, data hosted on the Seeed cloud, no face recognition, no ERP/WMS integration.

## Step 1: Configure Watcher Device {#sensecraft type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Connect your Watcher to SenseCraft cloud platform:

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named "Watcher-XXXX" and connect
3. Your browser should pop up the setup page automatically (if not, visit http://192.168.42.1 manually)
4. Wait about 5 seconds for the WiFi scan to complete, pick a 2.4GHz network, enter the password, then tap "Connect"
5. The device reboots automatically and shows a 6-digit verification code on the screen
6. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), click "SenseCraft Watcher" in Models, select "Watcher Agent" → "Bind Device", and enter the 6-digit code to complete binding
7. Click "Create" to make a new Agent, click the ⚙ settings icon on the Agent card, select the "Inventory Manager" role template, adjust name and language as needed, then save

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Can't find Watcher Agent | Confirm you're logged in to SenseCraft, refresh the page |

---

## Step 2: Configure Warehouse System {#cloud_warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

The warehouse system is hosted on Seeed cloud - no deployment needed. Open the cloud warehouse system to complete initial setup:

1. Visit [Warehouse System](https://warehouse.seeed.cn/) in your browser
2. Click "Login" in the top right → "Watcher device users can self-register"
3. Ask your Watcher "What is your device ID?" — Watcher will reply with an ID string
4. Enter the device ID in the registration form, complete registration and log in
5. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page won't load | Check network connection and try again |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then re-initialize |

---

## Step 3: Connect to Agent {#cloud_mcp_bridge type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Open warehouse system at [https://warehouse.seeed.cn/](https://warehouse.seeed.cn/)
2. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
3. Log into [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), in the ⚙ settings page scroll to the bottom, click "MCP Setting" → "Get MCP Endpoint" → "Copy Endpoint URL"
4. Paste the copied endpoint URL in the Endpoint field
5. Click "Save and Start"
6. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 4: Demo & Testing {#demo type=manual verify=true required=true}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands. To see the resulting inventory records, visit the SenseCraft platform at [sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/) after speaking.

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Watcher not responding | Confirm the Agent is connected (status shows Connected) |
| Inventory not updated | Refresh the SenseCraft page to see latest data |
| Cannot see records | Confirm your Watcher is bound to your SenseCraft account |
| Stock-in/stock-out fails while the network or service is down | Requests made during the outage are not replayed; repeat them after recovery. Keep the server and Watchers on the same wired LAN where possible, and put the server on UPS power |

### Deployment Complete

Your SenseCraft trial is ready!

**Access points:**
- SenseCraft Platform: [sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/)

Try saying "Stock in 10 boxes of apples" to test voice inventory management.

#### Acceptance checklist

1. **Agent connected** — on the SenseCraft platform, the Agent card shows "Connected" for its MCP Endpoint status.
2. **Voice stock-in echoes back** — say "Stock in 10 boxes of apples" to the Watcher; it replies confirming the item and new total within a few seconds.
3. **The record shows up** — reload [warehouse.seeed.cn](https://warehouse.seeed.cn/) and confirm the stock-in appears in today's records.
4. **A query works** — say "How many apples left?" and confirm the count matches what you just stocked in.

---

## Preset: Tier 1 · Basic {#sensecraft_cloud}

Voice AI runs on the [SenseCraft](https://sensecraft.seeed.cc/ai/) cloud service; you deploy only the warehouse system and connect the Watcher to the SenseCraft platform.

- **Peripherals:** SenseCAP Watcher (2.4GHz WiFi only), USB-C data cable (for flashing firmware).
- **Network:** internet access; during setup the Watcher, warehouse server and this computer are on the same LAN.
- **Account:** a [SenseCraft account](https://sensecraft.seeed.cc/ai/) (free); the warehouse admin account is created on first visit.
- **Limits:** high-accuracy face recognition is not supported.

## Step 1: Update Xiaozhi Firmware {#warehouse_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Write the voice assistant program to the Watcher to enable voice interaction.

### Wiring

![Connect Device](gallery/watcher_usb.png)

1. Connect Watcher to computer via USB-C cable
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-B** on Windows, or the higher-numbered one on macOS / Linux (`...53` / `ttyACM1`)
3. Click the Flash button

### Troubleshooting

| Symptom | Action |
|---------|----------|
| Serial port not found | Try a different USB cable or USB port |
| Wrong port picked (flash hangs or fails instantly) | Try the other CH342 port in the list |
| No serial data received | Hold BOOT button, press RESET, release BOOT, then retry |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Update Vision Detection Firmware {#warehouse_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

Write the vision detection program to the Watcher's AI chip.

### Wiring

![Connect Device](gallery/watcher_usb.png)

1. Keep the Watcher connected to your computer via the USB-C cable (same as the previous step)
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-A** on Windows, or the lower-numbered one on macOS / Linux (`...51` / `ttyACM0`) — not the same port as the previous step
3. Click the Flash button
4. After clicking Flash, press the reset button on the device to enter flash mode

### Troubleshooting

| Symptom | Action |
|---------|----------|
| Device not responding | Unplug and reconnect the USB cable |
| Flash stuck or fails | Press the reset button and try again |
| Flash fails repeatedly | Use a different USB cable or port |
| Flash fails at 99% or restarts mid-flash | Close other apps using serial ports, reconnect USB and retry |

---

## Step 3: Configure Watcher Device {#watcher_setup type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Pair the Watcher over WiFi, bind it to SenseCraft cloud, then create an "Inventory Manager" agent and copy its MCP endpoint URL (you'll need it in Step 6).

### Wiring

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named "Watcher-XXXX" and connect
3. Your browser should pop up the setup page automatically (if not, visit http://192.168.42.1 manually)
4. Wait about 5 seconds for the WiFi scan to complete, pick a 2.4GHz network, enter the password, then tap "Connect"
5. The device reboots automatically and shows a 6-digit verification code on the screen
6. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), click "SenseCraft Watcher" in Models, select "Watcher Agent" → "Bind Device", and enter the 6-digit code to complete binding
7. Click "Create" to make a new Agent, click the ⚙ settings icon on the Agent card, select the "Inventory Manager" role template, adjust name and language as needed, then save
8. Say "Enable face recognition mode" to the Watcher to switch it to face recognition detection
9. In the ⚙ settings page, scroll to the bottom, click "MCP Setting" → "Get MCP Endpoint" → "Copy Endpoint URL"

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Can't find Watcher Agent | Confirm you're logged in to SenseCraft, refresh the page |

---

## Step 4: Warehouse System {#warehouse type=docker_deploy required=true config=devices/warehouse_deploy.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Deployment Complete

Once the service is up, open `http://<server-ip>:2125` in a browser for the next step.

### Target {#warehouse_local type=local config=devices/warehouse_deploy.yaml}

Run the warehouse system on this computer. Needs at least 2 GB of free disk.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target {#warehouse_remote type=remote config=devices/warehouse_deploy.yaml default=true}

Deploy to a reComputer R1100 series device (4 GB memory and up). Needs at least 2 GB of free disk.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect R1100 series device to power and ethernet, ensure it's on the same network as your computer
2. Enter IP address `reComputer-R110x.local` (or check your router)
3. Enter username `recomputer`, password `12345678`
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Connection timeout | Check ethernet cable, test with ping reComputer-R110x.local |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 5: Configure Warehouse System {#warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 6: Connect to Agent {#mcp_bridge type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
2. Paste the endpoint URL copied from MCP Setting in Step 3
3. Click "Save and Start"
4. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 7: Demo & Testing {#voice_demo_test type=manual required=false}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands:

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

Check the warehouse web interface to see inventory changes after speaking.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |
| Stock-in/stock-out fails while the network or service is down | Requests made during the outage are not replayed; repeat them after recovery. Keep the server and Watchers on the same wired LAN where possible, and put the server on UPS power |

---

## Step 8: Test Face Recognition {#face_test type=manual required=false}

Configure face recognition in the warehouse system and verify it works:

1. Open your browser and visit `http://server-ip:2125`, go to "System Settings" → "Face Recognition"
2. Follow the on-page instructions to enroll the faces you want to recognize
3. Make sure you've said "Enable face recognition mode" to the Watcher (see Step 3)
4. Face the Watcher camera - successful recognitions appear in the warehouse system records

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Face not detected | Confirm the vision detection firmware is flashed and face recognition mode is enabled |
| Inaccurate recognition | Re-enroll well-lit, front-facing photos in "System Settings → Face Recognition" |

## Step 9: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The warehouse management dashboard is now live. Click below to open it in your browser.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your voice-controlled warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- SenseCraft Platform: [sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/)

#### Acceptance checklist

1. **Health endpoint responds** — `curl -f http://<server-ip>:2125/health` returns success.
2. **Admin login works** — log in to `http://<server-ip>:2125` with the administrator account created in Step 5.
3. **Voice stock-in echoes back** — say "Stock in 10 boxes of apples" to the Watcher; it replies confirming the item and new total.
4. **A query works** — say "How many apples left?" and the reply matches the warehouse dashboard.

Try saying "Stock in 10 boxes of apples" to test voice inventory management.

---

## Step 10: Flash the reTerminal D1001 (D1001 option) {#d1001_flash_sensecraft_cloud type=esp32_usb required=false config=devices/d1001_voice_terminal.yaml}

Only for the reTerminal D1001 voice terminal. Skip this step and the next one if you picked the SenseCAP Watcher. If you picked the D1001, skip this preset's Watcher steps instead — the Xiaozhi firmware step, the Himax vision firmware step and the Watcher setup step; the D1001 carries its camera on the same chip and needs no separate vision firmware.

### Wiring

1. Connect the D1001 to your computer with a USB-C data cable
2. The port is picked automatically (ESP32-P4 native USB, `usbmodem*` / `ttyACM*`)
3. Click Flash and wait for all six segments to finish

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Serial port not found | Use a data-capable USB-C cable, try another USB port |
| Flash failed midway | Reconnect the cable and retry; avoid USB hubs |

---

## Step 11: Set Up the D1001 and Link It (D1001 option) {#d1001_setup_sensecraft_cloud type=manual required=false}

Wi-Fi is set on the D1001's touch screen, not through a phone hotspot — that is the main difference from the Watcher. Everything after that (agent, MCP endpoint, warehouse system) is the same.

### Wiring

1. Power on the D1001 and tap the network icon in the status bar
2. Pick a **2.4GHz** network, enter the password on screen, and wait for the IP address to appear
3. Once it is online the device shows its activation code. Bind it in the console of the Xiaozhi service the firmware points at (`https://api.tenclass.net/xiaozhi/ota/` by default — the SenseCraft "Watcher Agent" binding form is Watcher-only), and give its agent the "Inventory Manager" role
4. Copy that agent's MCP endpoint URL
5. In the warehouse system, go to "Agent Configuration" → "Add Agent", paste the URL in the Endpoint field, then click "Save and Start"
6. Click "MCP Endpoint" on the agent card and refresh — **Connected** means success

### Verify

Say "Xiaozhi Xiaozhi" to wake the device, then "Stock in 10 boxes of apples". The screen reports the stock-in and the dashboard count rises by 10.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| WiFi connection failed | 2.4GHz only; re-enter the password on the screen |
| No activation code | Wait for the boot to finish, or restart the device |
| Status stays Disconnected | Check the endpoint URL was copied in full, with no stray spaces |

---

## Preset: Tier 2A · Advanced (Single Site) {#private_cloud}

Tier 1 plus local high-accuracy face recognition (with liveness detection): voice AI runs on the [SenseCraft](https://sensecraft.seeed.cc/ai/) cloud service, while face recognition inference runs on your local device — inventory and face data stay on your network.

- **Peripherals:** SenseCAP Watcher (2.4GHz WiFi only), USB-C data cable (for flashing firmware).
- **Network:** internet access; the Watcher, warehouse server and this computer are on the same LAN.
- **Account:** a [SenseCraft account](https://sensecraft.seeed.cc/ai/) (free); the warehouse admin account is created on first visit.

## Step 1: Update Xiaozhi Firmware {#warehouse_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Write the voice assistant program to the Watcher to enable voice interaction.

### Wiring

![Connect Device](gallery/watcher_usb.png)

1. Connect Watcher to computer via USB-C cable
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-B** on Windows, or the higher-numbered one on macOS / Linux (`...53` / `ttyACM1`)
3. Click the Flash button

### Troubleshooting

| Symptom | Action |
|---------|----------|
| Serial port not found | Try a different USB cable or USB port |
| Wrong port picked (flash hangs or fails instantly) | Try the other CH342 port in the list |
| No serial data received | Hold BOOT button, press RESET, release BOOT, then retry |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Update Vision Detection Firmware {#warehouse_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

Write the vision detection program to the Watcher's AI chip.

### Wiring

![Connect Device](gallery/watcher_usb.png)

1. Keep the Watcher connected to your computer via the USB-C cable (same as the previous step)
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-A** on Windows, or the lower-numbered one on macOS / Linux (`...51` / `ttyACM0`) — not the same port as the previous step
3. Click the Flash button
4. After clicking Flash, press the reset button on the device to enter flash mode

### Troubleshooting

| Symptom | Action |
|---------|----------|
| Device not responding | Unplug and reconnect the USB cable |
| Flash stuck or fails | Press the reset button and try again |
| Flash fails repeatedly | Use a different USB cable or port |
| Flash fails at 99% or restarts mid-flash | Close other apps using serial ports, reconnect USB and retry |

---

## Step 3: Configure Watcher Device {#watcher_config type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Connect your Watcher to SenseCraft cloud platform:

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named "Watcher-XXXX" and connect
3. Your browser should pop up the setup page automatically (if not, visit http://192.168.42.1 manually)
4. Wait about 5 seconds for the WiFi scan to complete, pick a 2.4GHz network, enter the password, then tap "Connect"
5. The device reboots automatically and shows a 6-digit verification code on the screen
6. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), click "SenseCraft Watcher" in Models, select "Watcher Agent" → "Bind Device", and enter the 6-digit code to complete binding
7. Click "Create" to make a new Agent, click the ⚙ settings icon on the Agent card, select the "Inventory Manager" role template, adjust name and language as needed, then save
8. Say "Enable face recognition mode" to the Watcher to switch it to face recognition detection
9. In the ⚙ settings page, scroll to the bottom, click "MCP Setting" → "Get MCP Endpoint" → "Copy Endpoint URL" (you'll need it in Step 6)

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Can't find Watcher Agent | Confirm you're logged in to SenseCraft, refresh the page |

---

## Step 4: Warehouse System {#warehouse_2a type=docker_deploy required=true config=devices/warehouse_face_hailo_deploy.yaml}

Deploy the warehouse system together with the high-accuracy face recognition service. The face recognition image matching the device model is pre-selected; you can also switch it manually.

### Target {#warehouse_2a_hailo_remote type=remote device=hailo device_name="Hailo-8" config=devices/warehouse_face_hailo_deploy.yaml default=true}

Deploy to a device with a Hailo-8 accelerator (reComputer Industrial R21 series, 4 GB memory and up; or Raspberry Pi + Hailo-8). Needs at least 4 GB of free disk.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect the device to power and ethernet, ensure it's on the same network as your computer
2. Enter the device IP address (or check your router)
3. Enter the SSH username and password
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Connection timeout | Check ethernet cable, ping the device IP |
| Face service won't start | Confirm the Hailo driver is installed (`ls /dev/hailo0` should exist) |
| Face service restarts in a loop with `HAILO_INVALID_DRIVER_VERSION` | The host needs the HailoRT **4.21.0** driver (the Raspberry Pi repo's `hailo-all` only ships 4.20.0). Check: `modinfo -F version hailo_pci`. Install: `curl -sfL https://raw.githubusercontent.com/blakeblackshear/frigate/dev/docker/hailo8l/user_installation.sh \| sudo bash` then **reboot the device** |

### Target {#warehouse_2a_jetson_remote type=remote device=jetson device_name="Jetson" config=devices/warehouse_face_jetson_deploy.yaml}

Deploy to a Jetson device (Orin series). Needs at least 4 GB of free disk.

### Wiring

1. Connect the Jetson to power and ethernet, ensure it's on the same network as your computer
2. Enter the device IP address and SSH credentials
3. Click Deploy and wait for installation to complete

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Connection timeout | Check ethernet cable, ping the device IP |
| Face service won't start | Confirm JetPack is installed and the model engines are in place |

### Target {#warehouse_2a_hailo_local type=local device=hailo device_name="Hailo-8" config=devices/warehouse_face_hailo_deploy.yaml}

Run directly on this machine (a device with Hailo-8). Needs at least 4 GB of free disk.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target {#warehouse_2a_jetson_local type=local device=jetson device_name="Jetson" config=devices/warehouse_face_jetson_deploy.yaml}

Run directly on this machine (a Jetson device). Needs at least 4 GB of free disk.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

---

## Step 5: Configure Warehouse System {#warehouse_config_private_cloud type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 6: Connect to Agent {#agent_config type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Open your browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
3. Paste the endpoint URL copied from MCP Setting in Step 3
4. Click "Save and Start"
5. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 7: Demo & Testing {#demo_private_cloud type=manual required=false}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands:

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

Check the warehouse web interface to see inventory changes after speaking.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |
| Stock-in/stock-out fails while the network or service is down | Requests made during the outage are not replayed; repeat them after recovery. Keep the server and Watchers on the same wired LAN where possible, and put the server on UPS power |

## Step 8: Test Face Recognition {#face_test_2a type=manual required=false}

Configure face recognition in the warehouse system and verify it works (this tier is high-accuracy, with liveness detection):

1. Open your browser and visit `http://server-ip:2125`, go to "System Settings" → "Face Recognition"
2. Follow the on-page instructions to enroll the faces you want to recognize
3. Make sure you've said "Enable face recognition mode" to the Watcher (see Step 3)
4. Face the Watcher camera - successful recognitions appear in the warehouse system records; holding up a photo should be rejected by liveness detection

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Face not detected | Confirm the vision detection firmware is flashed and face recognition mode is enabled |
| Face service not responding | Check `http://server-ip:8001/health` and confirm the face-rec container started in the deploy step |
| Inaccurate recognition | Re-enroll well-lit, front-facing photos in "System Settings → Face Recognition" |

## Step 9: Open Dashboard {#dashboard_private_cloud type=web_dashboard required=true config=devices/dashboard.yaml}

The warehouse management dashboard is now live. Click below to open it in your browser.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your private cloud warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- Face Recognition Service: http://\<server-ip\>:8001/health

Inventory and face data stay on your network. Try saying "How many apples left?" to test.

#### Acceptance checklist

1. **Both health endpoints respond** — `curl -f http://<server-ip>:2125/health` and `curl -f http://<server-ip>:8001/health` both return success.
2. **Voice stock-in echoes back** — say "Stock in 10 boxes of apples" to the Watcher; it replies confirming the item and new total.
3. **A query works** — say "How many apples left?" and the reply matches the warehouse dashboard.
4. **Face recognition fires** — after enrolling a face (Step 8), face the Watcher camera and confirm a recognition record appears in the warehouse system.

---

## Step 10: Flash the reTerminal D1001 (D1001 option) {#d1001_flash_private_cloud type=esp32_usb required=false config=devices/d1001_voice_terminal.yaml}

Only for the reTerminal D1001 voice terminal. Skip this step and the next one if you picked the SenseCAP Watcher. If you picked the D1001, skip this preset's Watcher steps instead — the Xiaozhi firmware step, the Himax vision firmware step and the Watcher setup step; the D1001 carries its camera on the same chip and needs no separate vision firmware.

### Wiring

1. Connect the D1001 to your computer with a USB-C data cable
2. The port is picked automatically (ESP32-P4 native USB, `usbmodem*` / `ttyACM*`)
3. Click Flash and wait for all six segments to finish

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Serial port not found | Use a data-capable USB-C cable, try another USB port |
| Flash failed midway | Reconnect the cable and retry; avoid USB hubs |

---

## Step 11: Set Up the D1001 and Link It (D1001 option) {#d1001_setup_private_cloud type=manual required=false}

Wi-Fi is set on the D1001's touch screen, not through a phone hotspot — that is the main difference from the Watcher. Everything after that (agent, MCP endpoint, warehouse system) is the same.

### Wiring

1. Power on the D1001 and tap the network icon in the status bar
2. Pick a **2.4GHz** network, enter the password on screen, and wait for the IP address to appear
3. Once it is online the device shows its activation code. Bind it in the console of the Xiaozhi service the firmware points at (`https://api.tenclass.net/xiaozhi/ota/` by default — the SenseCraft "Watcher Agent" binding form is Watcher-only), and give its agent the "Inventory Manager" role
4. Copy that agent's MCP endpoint URL
5. In the warehouse system, go to "Agent Configuration" → "Add Agent", paste the URL in the Endpoint field, then click "Save and Start"
6. Click "MCP Endpoint" on the agent card and refresh — **Connected** means success

### Verify

Say "Xiaozhi Xiaozhi" to wake the device, then "Stock in 10 boxes of apples". The screen reports the stock-in and the dashboard count rises by 10.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| WiFi connection failed | 2.4GHz only; re-enter the password on the screen |
| No activation code | Wait for the boot to finish, or restart the device |
| Status stays Disconnected | Check the endpoint URL was copied in full, with no stray spaces |

---

## Preset: Tier 2B · Advanced (Multi Site) {#private_cloud_multi}

One reComputer J40 series device (Jetson Orin NX 16GB) runs the warehouse system, face recognition (with liveness detection) and the local speech service. Speech recognition and synthesis stay on your network; only the LLM call goes to a cloud API (DeepSeek, Qwen, etc.). Up to three Watchers share the same server, one per site.

- **Peripherals:** SenseCAP Watcher × 1–3 (2.4GHz WiFi only), USB-C data cable (for flashing firmware).
- **Network:** internet access for the LLM call; each site's Watcher must reach the J40.
- **API key:** the Voice AI Service step asks for an LLM API Key generated in the console of the OpenAI-compatible provider you use (e.g. DeepSeek, Alibaba Cloud Model Studio); it is not issued by Seeed.

## Step 1: Update Xiaozhi Firmware {#warehouse_esp32_2b type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Write the voice assistant program to the Watcher to enable voice interaction. In this tier speech recognition and synthesis run on your own server, so the firmware needs to point at it (you'll bind it in Step 7).

### Wiring

![Connect Device](gallery/watcher_usb.png)

1. Connect Watcher to computer via USB-C cable
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-B** on Windows, or the higher-numbered one on macOS / Linux (`...53` / `ttyACM1`)
3. Click the Flash button

### Troubleshooting

| Symptom | Action |
|---------|----------|
| Serial port not found | Try a different USB cable or USB port |
| Wrong port picked (flash hangs or fails instantly) | Try the other CH342 port in the list |
| No serial data received | Hold BOOT button, press RESET, release BOOT, then retry |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Update Vision Detection Firmware {#warehouse_himax_2b type=himax_usb required=true config=devices/watcher_himax.yaml}

Write the vision detection program to the Watcher's AI chip, used for face recognition and object detection.

### Wiring

![Connect Device](gallery/watcher_usb.png)

1. Keep the Watcher connected to your computer via the USB-C cable (same as the previous step)
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-A** on Windows, or the lower-numbered one on macOS / Linux (`...51` / `ttyACM0`) — not the same port as the previous step
3. Click the Flash button
4. After clicking Flash, press the reset button on the device to enter flash mode

### Troubleshooting

| Symptom | Action |
|---------|----------|
| Device not responding | Unplug and reconnect the USB cable |
| Flash stuck or fails | Press the reset button and try again |
| Flash fails repeatedly | Use a different USB cable or port |
| Flash fails at 99% or restarts mid-flash | Close other apps using serial ports, reconnect USB and retry |

---

## Step 3: Warehouse System + Face Recognition {#warehouse_2b type=docker_deploy required=true config=devices/warehouse_face_jetson_deploy.yaml}

Deploy the inventory management service together with the high-accuracy face recognition service on the J40 series device.

### Target {#warehouse_2b_remote type=remote config=devices/warehouse_face_jetson_deploy.yaml default=true}

Deploy to the reComputer J40 series. Needs at least 4 GB of free disk.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect the J40 series device to power and ethernet, ensure it's on the same network as your computer
2. Check your router for the J40 series device's IP address and enter it
3. Enter username `recomputer`, password `12345678`
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Connection timeout | Check ethernet cable, verify IP address is correct |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |
| Face service won't start | Confirm JetPack is installed on the J40 series device |
| Face service takes minutes on first start | On a JetPack version other than 6.2 the first start rebuilds the inference engines; this happens once |

### Target {#warehouse_2b_local type=local config=devices/warehouse_face_jetson_deploy.yaml}

Run directly on this machine — only applicable when it is the J40 series device itself. Needs at least 4 GB of free disk.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Port in use | Check if ports 2125 and 8001 are used by another service |
| Docker not running | Start Docker and retry |

---

## Step 4: Configure Warehouse System {#warehouse_config_private_cloud_multi type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 5: Speech Service {#voice_stack_private_cloud_multi type=docker_deploy required=true config=devices/ovs_voice_deploy.yaml}

Deploy OpenVoiceStream on the J40 series device to provide speech recognition, synthesis and voiceprint; the voice AI service in the next step connects to it.

### Target {#voice_stack_local type=local config=devices/ovs_voice_deploy.yaml}

Deploy directly on this machine — only applicable when it is the J40 series device itself. Needs at least 15 GB of free disk; models download automatically.

### Target {#voice_stack_remote type=remote config=devices/ovs_voice_deploy.yaml default=true}

Deploy to the reComputer J40 series (the same device as Step 3). Needs at least 15 GB of free disk.

### Wiring

1. Connect the J40 series device to power and ethernet
2. Enter the J40 series device's IP address and SSH credentials (the same device as Step 3)
3. Click Deploy and wait for the models to download and the service to start

The service listens on **8621** and admits up to **3 concurrent voice sessions**, one per Watcher; a 4th is rejected. **Note this machine's LAN IP — the next step asks for it as the Voice Service Address.**

> Even when the voice service and the next step land on the same machine, do **not** use `127.0.0.1`.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| First deploy seems stuck | The first start downloads ~5GB of models; this can take 10+ minutes |
| Not enough disk space | This step needs at least 15GB free |
| NVIDIA runtime unavailable | Install nvidia-container-toolkit and restart Docker |
| Deploy aborts with a container-name conflict | The device already has a hand-installed voice service or the other tier's voice step; they cannot coexist. `docker rm -f` the existing containers as instructed and retry |
| Deployed but 8621 unreachable | Models are still loading; ready when `curl localhost:8621/readyz` returns 200 |
| A Watcher gets `4429 too_many_sessions` | All 3 sessions are busy; check for a Watcher stuck in an open session |

---

## Step 6: Voice AI Service {#voice_service_private_cloud_multi type=docker_deploy required=true config=devices/xiaozhi_console_deploy.yaml}

![Model configuration](gallery/console-tts-list.jpg)

Deploy the voice AI service and its management console, which give the Watcher its voice interaction capability. Select "**Private Cloud**" mode and fill in:

- **Voice Service Address**: the **J40 series device's** LAN IP from the previous step, port 8621 — **not** `127.0.0.1`
- **LLM API URL / model name / API key**: your cloud LLM (DeepSeek, Qwen, etc.)

Addresses and the MCP endpoint are configured automatically.


### Target {#voice_local type=local config=devices/xiaozhi_console_deploy.yaml}

Deploy on this machine. Needs at least 6 GB of free disk.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target {#voice_remote type=remote config=devices/xiaozhi_console_deploy.yaml default=true}

Deploy to the J40 series device. Needs at least 6 GB of free disk.

### Wiring

1. Enter the J40 series device's IP address and SSH credentials
2. Click Deploy and wait for installation to complete

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Image pull failed | Check network connection, or configure Docker mirror |
| Port in use | Check if ports 18000, 18002, 18003, 18004 are used by other services |
| API call failed | Verify API key is correct and has sufficient balance |

---

## Step 7: Connect Watcher to Your Local Server {#watcher_config_private_cloud_multi type=manual required=true}

Put the Watcher on WiFi and point it at the local voice server you just deployed.

> Speech recognition and synthesis both run locally, so the Watcher does **not** need to be bound to the SenseCraft cloud platform.

### Wiring

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named `Watcher-XXXX` and connect
3. Your browser should pop up the setup page automatically (if not, visit `http://192.168.42.1` manually)
4. **Don't join WiFi yet** — tap "**Advanced Options**" at the top of the page and enter this OTA address:

   ```
   http://<J40 series device IP>:18002/xiaozhi/ota/
   ```

   Tap Save. This is what decides which server the device talks to — skip it and the Watcher falls back to the default public server.
5. Go back to the setup page, wait about 5 seconds for the WiFi scan to finish, pick a **2.4GHz** network, enter the password, then tap "Connect"
6. The device reboots automatically once connected
7. Open `http://<J40 series device IP>:18002/xiaozhi/ota/` in a browser to verify — "OTA interface is running" means the server side is ready

> **Enabling face recognition**: after Wi-Fi setup, say "**开启人脸识别模式**" to the Watcher, then enrol photos under Settings → Face Recognition in the warehouse system. Without saying it, the Watcher sends no frames.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| OTA page reports "not running" | Log in to the console and check that `server.websocket` is set under "Parameter Management" |
| Nothing happens after the reboot | Make sure the OTA address uses the **server IP**, not localhost, and that the device and server are on the same network |
| Want to go back to the default server | Re-enter setup mode and clear the OTA address under Advanced Options |

---

## Step 8: Create an Agent and Link It to the Warehouse {#agent_config_private_cloud_multi type=manual required=true}

Create an agent in the management console, then paste its MCP endpoint into the warehouse system so voice commands can drive inventory.
> **To change the addresses entered during deployment**: edit the base URL (red box)
> under Model Configuration → Text-to-Speech → OpenVoiceStream → Edit.
>
> ![Model fields](gallery/console-ovs-form-annotated.png)
>
> - 🔴 **Base URL**: voice service address, format `http://<device IP>:8621`
> - 🔵 **Voice**: fetched from the device automatically once the base URL is set — no manual entry
> - 🔵 **API Key**: only needed when the voice service has `OVS_API_KEYS` enabled; leave blank otherwise


### Wiring

**A. Log in to the console**

1. Open `http://<J40 series device IP>:18002` in your browser
2. Username `admin`, initial password `Seeed@2026`
3. ⚠️ **Change the password immediately after your first login** (account menu in the top right → Change Password)

   ![Change password](gallery/console-change-password.jpg)

**B. Configure the cloud LLM**

4. Go to "Model Configuration → Large Language Model", find the model you entered during deployment, and confirm the API URL, model name and key are correct

**C. Create the agent**

5. Click "New Agent" and pick the "**Warehouse Assistant**" role template — it ships with warehouse-specific prompts and the local voice models already selected
6. Save, open the agent's "Role Configuration" page, and switch "Primary LLM" to the cloud model you just verified
7. To change the voice: open the "OVS Speaker" dropdown — it pulls the available voices from the voice service in real time

**D. Copy the MCP endpoint**

8. On the Role Configuration page, click the "**Edit Functions**" button
9. Find "MCP Endpoint" in the dialog and copy this agent's dedicated URL

   > Every agent gets a different URL, so don't mix them up across sites.

**E. Add it to the warehouse system**

10. Open `http://<J40 series device IP>:2125` in your browser
11. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
12. Paste the endpoint URL you just copied into the Endpoint field
13. Click "Save and Start"
14. Click "MCP Endpoint" on the agent card and refresh — **Connected** means success

> **Multi-site tip**: one agent per Watcher — just repeat C through E. Each agent has its own MCP endpoint URL.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Console won't open | The first start runs database migrations; wait 1-2 minutes and retry |
| Forgot the admin password | Redeploy the voice AI service with "clear data" checked to reset it to the default |
| No "Warehouse Assistant" role template | You're not on this solution's image — check that the voice AI service deployed successfully |
| MCP endpoint is empty | Check that `server.mcp_endpoint` is set under "Parameter Management" in the console |
| Status stays Disconnected | Check the endpoint URL was copied in full (token included, no stray spaces) |
| LLM doesn't respond | Verify the API key is valid and the account has credit |

---

## Step 9: Demo & Testing {#demo_private_cloud_multi type=manual required=false}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands:

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

Check the warehouse web interface to see inventory changes after speaking.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |
| Stock-in/stock-out fails while the network or service is down | Requests made during the outage are not replayed; repeat them after recovery. Keep the server and Watchers on the same wired LAN where possible, and put the server on UPS power |

## Step 10: Open Dashboard {#dashboard_private_cloud_multi type=web_dashboard required=true config=devices/dashboard.yaml}

The warehouse management dashboard is now live. Click below to open it in your browser.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your multi-site private cloud warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- Console: http://\<server-ip\>:18002

Your data stays on your network. Try saying "How many apples left?" to test.

#### Acceptance checklist

1. **Health endpoints respond** — `curl -f http://<server-ip>:2125/health` (warehouse) and `curl -f http://<server-ip>:8621/readyz` (speech service) both return success.
2. **Each site's Watcher is connected** — its Agent card on the console shows "Connected" for the MCP Endpoint.
3. **Voice stock-in echoes back, per site** — say "Stock in 10 boxes of apples" on each Watcher; each replies confirming the item and total for its own site.
4. **A query works** — say "How many apples left?" on one Watcher and confirm the count is scoped to that site, not mixed with another.

---

## Preset: Tier 3 · Premium {#edge_computing}

Everything runs locally, including the LLM and TTS, with face recognition supported. Suited to air-gapped sites or strict data-compliance requirements.

- **Peripherals:** SenseCAP Watcher (2.4GHz WiFi only), USB-C data cable (for flashing firmware).
- **Network:** internet access on first deploy to pull images and models; no internet needed afterwards.
- **API key:** not needed.

## Step 1: Update Xiaozhi Firmware {#warehouse_esp32_t3 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Write the voice assistant program to the Watcher to enable voice interaction. In this tier all speech processing runs on your own server, so the firmware needs to point at it (you'll bind it in Step 7).

### Wiring

![Connect Device](gallery/watcher_usb.png)

1. Connect Watcher to computer via USB-C cable
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-B** on Windows, or the higher-numbered one on macOS / Linux (`...53` / `ttyACM1`)
3. Click the Flash button

### Troubleshooting

| Symptom | Action |
|---------|----------|
| Serial port not found | Try a different USB cable or USB port |
| Wrong port picked (flash hangs or fails instantly) | Try the other CH342 port in the list |
| No serial data received | Hold BOOT button, press RESET, release BOOT, then retry |
| Flash failed | Unplug and reconnect the device |

---

## Step 2: Update Vision Detection Firmware {#warehouse_himax_t3 type=himax_usb required=true config=devices/watcher_himax.yaml}

Write the vision detection program to the Watcher's AI chip, used for face recognition and object detection.

### Wiring

![Connect Device](gallery/watcher_usb.png)

1. Keep the Watcher connected to your computer via the USB-C cable (same as the previous step)
2. The port is usually selected for you; if not, pick the COM port containing **SERIAL-A** on Windows, or the lower-numbered one on macOS / Linux (`...51` / `ttyACM0`) — not the same port as the previous step
3. Click the Flash button
4. After clicking Flash, press the reset button on the device to enter flash mode

### Troubleshooting

| Symptom | Action |
|---------|----------|
| Device not responding | Unplug and reconnect the USB cable |
| Flash stuck or fails | Press the reset button and try again |
| Flash fails repeatedly | Use a different USB cable or port |
| Flash fails at 99% or restarts mid-flash | Close other apps using serial ports, reconnect USB and retry |

---

## Step 3: Warehouse System {#warehouse_t3 type=docker_deploy required=true config=devices/warehouse_face_hailo_deploy.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Target {#warehouse_t3_local type=local config=devices/warehouse_face_hailo_deploy.yaml}

Run the warehouse system on this computer. Needs at least 4 GB of free disk.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target {#warehouse_t3_remote type=remote config=devices/warehouse_face_hailo_deploy.yaml default=true}

Deploy to a reComputer Industrial R21 series device (Hailo-8, 4 GB memory and up). Needs at least 4 GB of free disk.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect Industrial R21 series device to power and ethernet, ensure it's on the same network as your computer
2. Enter IP address `reComputer-R110x.local` (or check your router)
3. Enter username `recomputer`, password `12345678`
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Connection timeout | Check ethernet cable, test with ping reComputer-R110x.local |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 4: Configure Warehouse System {#warehouse_config_edge_computing type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 5: Voice AI Stack {#jetson_ai type=docker_deploy required=true config=devices/ovs_jetson_deploy.yaml}

Deploy OpenVoiceStream (speech recognition + synthesis + voiceprint) and EdgeLLM (Qwen3.5-4B) on the Jetson. The next step's voice service connects to both.

### Target {#jetson_ai_local type=local config=devices/ovs_jetson_deploy.yaml}

Deploy directly on this Jetson. Needs at least 25 GB of free disk; models download automatically.

### Target {#jetson_remote type=remote config=devices/ovs_jetson_deploy.yaml default=true}

Deploy to the reComputer J50 series. Needs at least 25 GB of free disk.

### Wiring

1. Connect Jetson (reComputer J50 series) to power and ethernet
2. Enter Jetson IP address and SSH credentials
3. Click Deploy and wait for the models to download and services to start

Two containers come up: voice service on **8621**, LLM on **8000**. **Note this Jetson's IP — the next step needs it.**

### Troubleshooting

| Symptom | Action |
|-------|----------|
| SSH connection failed | Confirm Jetson is powered on, verify IP address |
| First deploy seems stuck | The first start downloads ~10GB of models and inference engines; this can take 10+ minutes |
| Not enough disk space | This step needs at least 25GB free |
| NVIDIA runtime unavailable | Install nvidia-container-toolkit on the Jetson and restart Docker |
| Deploy aborts with a container-name conflict | The device already has a hand-installed voice service; they cannot coexist. `docker rm -f` the existing containers as instructed and retry; models are not re-downloaded |

---
## Step 6: Voice AI Service {#voice_service_edge_computing type=docker_deploy required=true config=devices/xiaozhi_console_deploy.yaml}

![Model configuration](gallery/console-tts-list.jpg)

Deploy the voice AI service and its management console on the Industrial R21 series device. Select "**Edge Computing**" mode and fill in two addresses:

- **Voice Service Address**: LAN IP of the Jetson running OpenVoiceStream from the previous step, port 8621 (not `127.0.0.1`)
- **Local LLM Address**: the same Jetson's LAN IP, port 8000 (leave empty if co-located)

Model addresses, the device access address and the MCP endpoint are then configured automatically.


### Target {#voice_local type=local config=devices/xiaozhi_console_deploy.yaml}

Deploy on this machine. Needs at least 6 GB of free disk.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target {#voice_remote type=remote config=devices/xiaozhi_console_deploy.yaml default=true}

Deploy to the Industrial R21 series device. Needs at least 6 GB of free disk.

### Wiring

1. Enter the Industrial R21 series device's IP address and SSH credentials
2. Click Deploy and wait for installation to complete

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Cannot connect to Jetson | Check if Industrial R21 series device and Jetson are on the same network |
| Response is slow | Confirm Jetson service is running, visit `http://Jetson-IP:8000/v1/models` to check |

---

## Step 7: Connect Watcher to Your Local Server {#watcher_config_edge_computing type=manual required=true}

Put the Watcher on WiFi and point it at the local voice server you just deployed instead of the cloud.

> This tier runs entirely on your LAN, so the Watcher does **not** need to be bound to the SenseCraft cloud platform.

### Wiring

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named `Watcher-XXXX` and connect
3. Your browser should pop up the setup page automatically (if not, visit `http://192.168.42.1` manually)
4. **Don't join WiFi yet** — tap "**Advanced Options**" at the top of the page and enter the OTA address shown after the previous deployment step:

   ```
   http://<Voice Server IP>:18002/xiaozhi/ota/
   ```

   Tap Save. This is what decides which server the device talks to — skip it and the Watcher falls back to the default public server.
5. Go back to the setup page, wait about 5 seconds for the WiFi scan to finish, pick a **2.4GHz** network, enter the password, then tap "Connect"
6. The device reboots automatically once connected
7. Open `http://<Voice Server IP>:18002/xiaozhi/ota/` in a browser to verify — "OTA interface is running" means the server side is ready

> **Enabling face recognition**: after Wi-Fi setup, say "**开启人脸识别模式**" to the Watcher, then enrol photos under Settings → Face Recognition in the warehouse system. Without saying it, the Watcher sends no frames.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| OTA page reports "not running" | Log in to the console and check that `server.websocket` is set under "Parameter Management" |
| Nothing happens after the reboot | Make sure the OTA address uses the **server IP**, not localhost, and that the device and server are on the same network |
| Want to go back to the default server | Re-enter setup mode and clear the OTA address under Advanced Options |

---

## Step 8: Create an Agent and Link It to the Warehouse {#agent_config_edge_computing type=manual required=true}

Create an agent in the management console, then paste its MCP endpoint into the warehouse system so voice commands can drive inventory.
> **To change the addresses entered during deployment**: edit the base URL (red box)
> under Model Configuration → Text-to-Speech → OpenVoiceStream → Edit.
>
> ![Model fields](gallery/console-ovs-form-annotated.png)
>
> - 🔴 **Base URL**: voice service address, format `http://<device IP>:8621`
> - 🔵 **Voice**: fetched from the device automatically once the base URL is set — no manual entry
> - 🔵 **API Key**: only needed when the voice service has `OVS_API_KEYS` enabled; leave blank otherwise


### Wiring

**A. Log in to the console**

1. Open `http://<Voice Server IP>:18002` in your browser
2. Username `admin`, initial password `Seeed@2026`
3. ⚠️ **Change the password immediately after your first login** (account menu in the top right → Change Password)

   ![Change password](gallery/console-change-password.jpg)

**B. Create the agent**

4. Click "New Agent" and pick the "**Warehouse Assistant**" role template — it ships with warehouse-specific prompts and already has the local speech recognition, speech synthesis and LLM selected
5. Save, then open the agent's "Role Configuration" page
6. To change the voice: open the "OVS Speaker" dropdown — it pulls the available voices from the voice server in real time

**C. Copy the MCP endpoint**

7. On the Role Configuration page, click the "**Edit Functions**" button
8. Find "MCP Endpoint" in the dialog and copy this agent's dedicated URL

   > Every agent gets a different URL, so make sure you copy the right one.

**D. Add it to the warehouse system**

9. Open `http://<Warehouse Server IP>:2125` in your browser
10. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
11. Paste the endpoint URL you just copied into the Endpoint field
12. Click "Save and Start"
13. Click "MCP Endpoint" on the agent card and refresh — **Connected** means success

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Console won't open | The first start runs database migrations; wait 1-2 minutes and retry |
| Forgot the admin password | Redeploy the voice AI service with "clear data" checked to reset it to the default |
| No "Warehouse Assistant" role template | You're not on this solution's image — check that the voice AI service deployed successfully |
| MCP endpoint is empty | Check that `server.mcp_endpoint` is set under "Parameter Management" in the console |
| Status stays Disconnected | Check the endpoint URL was copied in full (token included, no stray spaces), and that the warehouse system can reach the voice server |
| Voice dropdown comes up empty | Check that the address under "Model Configuration → Text-to-Speech" points at the real voice service device |

---

## Step 9: Demo & Testing {#demo_edge_computing type=manual required=false}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands:

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

Check the warehouse web interface to see inventory changes after speaking.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |
| Stock-in/stock-out fails while the network or service is down | Requests made during the outage are not replayed; repeat them after recovery. Keep the server and Watchers on the same wired LAN where possible, and put the server on UPS power |

## Step 10: Open Dashboard {#dashboard_edge_computing type=web_dashboard required=true config=devices/dashboard.yaml}

The warehouse management dashboard is now live. Click below to open it in your browser.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your fully offline warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- Console: http://\<server-ip\>:18002
- LLM endpoint: http://\<jetson-ip\>:8000/v1/models

100% offline operation - no internet required after deployment.

#### Acceptance checklist

1. **All three health endpoints respond** — `curl -f http://<server-ip>:2125/health` (warehouse, on the Industrial R21 series device), `curl -f http://<jetson-ip>:8621/readyz` (speech, on the J50 series device), and `curl -f http://<jetson-ip>:8000/v1/models` (LLM, on the J50 series device) all return success.
2. **It survives disconnection** — unplug the internet uplink at your router or gateway (leave the Industrial R21 series device and J50 series device connected to each other and to the Watcher over LAN); the Watcher must still be reachable over the local network.
3. **Voice stock-in echoes back, offline** — with the uplink still disconnected, say "Stock in 10 boxes of apples" and confirm the Watcher replies.
4. **A query works offline** — say "How many apples left?" and confirm the reply matches the dashboard, still disconnected.

## Step 11: Flash the reTerminal D1001 (D1001 option) {#d1001_flash_edge_computing type=esp32_usb required=false config=devices/d1001_voice_terminal.yaml}

Only for the reTerminal D1001 voice terminal. Skip this step and the next one if you picked the SenseCAP Watcher. If you picked the D1001, skip this preset's Watcher steps instead — the Xiaozhi firmware step, the Himax vision firmware step and the Watcher setup step; the D1001 carries its camera on the same chip and needs no separate vision firmware.

### Wiring

1. Connect the D1001 to your computer with a USB-C data cable
2. The port is picked automatically (ESP32-P4 native USB, `usbmodem*` / `ttyACM*`)
3. Click Flash and wait for all six segments to finish

### Troubleshooting

| Symptom | Action |
|-------|----------|
| Serial port not found | Use a data-capable USB-C cable, try another USB port |
| Flash failed midway | Reconnect the cable and retry; avoid USB hubs |

---

## Step 12: Point the D1001 at Your Local Server (D1001 option) {#d1001_setup_edge_computing type=manual required=false}

The D1001 ships pointing at the public Xiaozhi service, so it needs the same OTA-address override the Watcher gets — entered on the provisioning page, which the D1001 reaches through the boot button instead of a scroll button.

### Wiring

1. Power the device on and click the boot button while it is still starting up — it enters Wi-Fi provisioning mode and broadcasts a setup hotspot
2. Connect your phone to that hotspot; the setup page opens automatically (otherwise visit `http://192.168.4.1`)
3. **Don't join WiFi yet** — open "**Advanced Options**", enter the OTA address of the voice service you deployed, and Save:

   ```
   http://<Voice Server IP>:18002/xiaozhi/ota/
   ```

4. Go back to the setup page, pick a **2.4GHz** network, enter the password, and connect
5. In the console at `http://<Voice Server IP>:18002`, create the agent from the "Warehouse Assistant" role template, then copy its MCP endpoint under "Edit Functions"
6. In the warehouse system, go to "Agent Configuration" → "Add Agent", paste the URL in the Endpoint field, then click "Save and Start"
7. Click "MCP Endpoint" on the agent card and refresh — **Connected** means success

> Wi-Fi can also be set on the touch screen (network icon in the status bar), but the OTA address can only be entered on the provisioning page, so use the boot-button route the first time.

### Verify

Say "Xiaozhi Xiaozhi" to wake the device, then "Stock in 10 boxes of apples". The screen reports the stock-in and the dashboard count rises by 10.

### Troubleshooting

| Symptom | Action |
|-------|----------|
| No setup hotspot appears | The click must land while the device is starting up; power-cycle and try again |
| WiFi connection failed | 2.4GHz only; re-enter the password |
| Nothing happens after the reboot | Make sure the OTA address uses the **server IP**, not localhost, and that device and server share a network |
| Status stays Disconnected | Check the endpoint URL was copied in full, with no stray spaces |

---
