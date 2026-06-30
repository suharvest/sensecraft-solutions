## Preset: Tier 0 · Cloud {#trial}

Only a Watcher is needed - no host required. Inventory data and voice service are hosted on the Seeed cloud, so you can experience the full voice warehouse workflow out of the box.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant, receives voice commands |

**What you'll get:**
- Voice-controlled inventory (say "Stock in 10 boxes of apples" to record)
- Real-time inventory data in the browser

**Requirements:** Internet connection · SenseCraft account (free signup)

**Note:** Monthly subscription; data is hosted on Seeed cloud; face recognition and ERP/WMS integration are not supported.

## Step 1: Configure Watcher Device {#sensecraft type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Connect your Watcher to SenseCraft cloud platform:

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named "Watcher-XXXX" and connect
3. Your browser should pop up the setup page automatically (if not, visit http://192.168.4.1 manually)
4. Wait about 5 seconds for the WiFi scan to complete, pick a 2.4GHz network, enter the password, then tap "Connect"
5. The device reboots automatically and shows a 6-digit verification code on the screen
6. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), click "SenseCraft Watcher" in Models, select "Watcher Agent" → "Bind Device", and enter the 6-digit code to complete binding
7. Click "Create" to make a new Agent, click the ⚙ settings icon on the Agent card, select the "Inventory Manager" role template, adjust name and language as needed, then save

### Troubleshooting

| Issue | Solution |
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

| Issue | Solution |
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

| Issue | Solution |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 4: Demo & Testing {#demo type=manual verify=true required=true}

![Voice Stock-in Demo](gallery/xiaozhi-stock-in.png)

Try these voice commands — the conversation itself is your verification that the trial is working. To see the resulting inventory records, visit the SenseCraft platform at [sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/) after speaking.

| Say this | Watcher will |
|----------|--------------|
| "How many apples left?" | Query apple inventory count |
| "Stock in 10 boxes of apples" | Add 10 boxes of apples to inventory |
| "Stock out 5 boxes of bananas" | Remove 5 boxes of bananas from inventory |
| "What came in today?" | List today's stock-in records |

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Watcher not responding | Confirm the Agent is connected (status shows Connected) |
| Inventory not updated | Refresh the SenseCraft page to see latest data |
| Cannot see records | Confirm your Watcher is bound to your SenseCraft account |

### Deployment Complete

Your SenseCraft trial is ready!

**Access points:**
- SenseCraft Platform: [sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/)

Try saying "Stock in 10 boxes of apples" to test voice inventory management.

---

## Preset: Tier 1 · Basic {#sensecraft_cloud}

Use [SenseCraft](https://sensecraft.seeed.cc/ai/) cloud service for voice AI. Simplest setup - just deploy the warehouse system and connect your Watcher to SenseCraft platform.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant, receives voice commands |
| reComputer R1125-10 | Runs warehouse management system |
| USB-C data cable | Flash Watcher firmware |

**What you'll get:**
- Voice-controlled inventory management (stock in/out by speaking)
- Real-time inventory dashboard
- Works with SenseCAP Watcher out of the box

❌ High-accuracy face recognition not supported

**Requirements:** Internet connection · [SenseCraft account](https://sensecraft.seeed.cc/ai/) (free)

## Step 1: Warehouse System {#warehouse type=docker_deploy required=true config=devices/warehouse_deploy.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Target {#warehouse_local type=local config=devices/warehouse_deploy.yaml}

Run the warehouse system on this computer.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target {#warehouse_remote type=remote config=devices/warehouse_deploy.yaml default=true}

Deploy to reComputer R1125-10 edge device.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect R1125-10 to power and ethernet, ensure it's on the same network as your computer
2. Enter IP address `reComputer-R110x.local` (or check your router)
3. Enter username `recomputer`, password `12345678`
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check ethernet cable, test with ping reComputer-R110x.local |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 2: Configure Warehouse System {#warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 3: Update Xiaozhi Firmware {#warehouse_esp32 type=esp32_usb required=true config=devices/watcher_esp32.yaml}

Write the face-recognition-capable voice assistant program to the Watcher.

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

## Step 4: Flash Face Recognition Firmware {#warehouse_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

Write the face recognition program to the Watcher's AI chip (includes face detection, face embedding, and person detection models).

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

## Step 5: Configure Watcher Device {#sensecraft type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Connect your Watcher to SenseCraft cloud platform:

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named "Watcher-XXXX" and connect
3. Your browser should pop up the setup page automatically (if not, visit http://192.168.4.1 manually)
4. Wait about 5 seconds for the WiFi scan to complete, pick a 2.4GHz network, enter the password, then tap "Connect"
5. The device reboots automatically and shows a 6-digit verification code on the screen
6. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), click "SenseCraft Watcher" in Models, select "Watcher Agent" → "Bind Device", and enter the 6-digit code to complete binding
7. Click "Create" to make a new Agent, click the ⚙ settings icon on the Agent card, select the "Inventory Manager" role template, adjust name and language as needed, then save
8. In the ⚙ settings page, scroll to the bottom, click "MCP Setting" → "Get MCP Endpoint" → "Copy Endpoint URL"

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Can't find Watcher Agent | Confirm you're logged in to SenseCraft, refresh the page |

---

## Step 6: Connect to Agent {#mcp_bridge type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Open your browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
3. Paste the endpoint URL copied from MCP Setting in the previous step
4. Click "Save and Start"
5. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 7: Demo & Testing {#demo type=manual required=false}

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

| Issue | Solution |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |

## Step 8: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The warehouse management dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your voice-controlled warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- SenseCraft Platform: [sensecraft.seeed.cc](https://sensecraft.seeed.cc/ai/)

Try saying "Stock in 10 boxes of apples" to test voice inventory management.

---

## Preset: Tier 2A · Advanced (Single Site) {#private_cloud}

Self-host the voice AI server while using cloud APIs (DeepSeek, OpenAI, etc.) for LLM and TTS. Your data stays on your network - only API calls go to the cloud.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant, receives voice commands |
| reComputer R2135-12 | Runs warehouse system + voice AI service |

**What you'll get:**
- Full control over your data - inventory stays on your network
- Flexible AI model choices (DeepSeek, GPT-4, Qwen, etc.)
- Customize voice assistant prompts and behavior

✅ Face recognition supported

**Requirements:** Internet connection · LLM API keys required

## Step 1: Warehouse System {#warehouse_2a type=docker_deploy required=true config=devices/warehouse_deploy.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Target {#warehouse_2a_local type=local config=devices/warehouse_deploy.yaml}

Run the warehouse system on this computer.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target {#warehouse_2a_remote type=remote config=devices/warehouse_deploy.yaml default=true}

Deploy to reComputer R2135-12 edge device.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect R2135-12 to power and ethernet, ensure it's on the same network as your computer
2. Enter IP address `reComputer-R110x.local` (or check your router)
3. Enter username `recomputer`, password `12345678`
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check ethernet cable, test with ping reComputer-R110x.local |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 2: Configure Warehouse System {#warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 3: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi_deploy.yaml}

Deploy the voice AI service to enable voice interaction with Watcher. Select "Private Cloud" mode and fill in your LLM API details.

### Target {#voice_local type=local config=devices/xiaozhi_deploy.yaml}

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target {#voice_remote type=remote config=devices/xiaozhi_deploy.yaml default=true}

### Wiring

1. Enter R2135-12 IP address and SSH credentials
2. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Image pull failed | Check network connection, or configure Docker mirror |
| Port in use | Check if ports 18000, 18003, 18004 are used by other services |
| API call failed | Verify API key is correct and has sufficient balance |

---

## Step 4: Configure Watcher Device {#watcher_config type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Connect your Watcher to SenseCraft cloud platform:

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named "Watcher-XXXX" and connect
3. Your browser should pop up the setup page automatically (if not, visit http://192.168.4.1 manually)
4. Wait about 5 seconds for the WiFi scan to complete, pick a 2.4GHz network, enter the password, then tap "Connect"
5. The device reboots automatically and shows a 6-digit verification code on the screen
6. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), click "SenseCraft Watcher" in Models, select "Watcher Agent" → "Bind Device", and enter the 6-digit code to complete binding
7. Click "Create" to make a new Agent, click the ⚙ settings icon on the Agent card, select the "Inventory Manager" role template, adjust name and language as needed, then save
8. In the ⚙ settings page, scroll to the bottom, click "MCP Setting" → "Get MCP Endpoint" → "Copy Endpoint URL"

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Can't find Watcher Agent | Confirm you're logged in to SenseCraft, refresh the page |

---

## Step 5: Connect to Agent {#agent_config type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Open your browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
3. Paste the endpoint URL copied from MCP Setting in the previous step
4. Click "Save and Start"
5. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 6: Demo & Testing {#demo type=manual required=false}

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

| Issue | Solution |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |

## Step 7: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The warehouse management dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your private cloud warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- Voice Service Console: http://\<server-ip\>:18003

Your data stays on your network. Try saying "How many apples left?" to test.

---

## Preset: Tier 2B · Advanced (Multi Site) {#private_cloud_multi}

Self-host the voice AI server while using cloud APIs (DeepSeek, OpenAI, etc.) for LLM and TTS. Supports concurrent voice processing across multiple sites. Your data stays on your network - only API calls go to the cloud.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant, receives voice commands |
| reComputer Super J4012 | Runs warehouse system + voice AI service, supports multi-channel concurrent voice processing |

**What you'll get:**
- Full control over your data - inventory stays on your network
- Flexible AI model choices (DeepSeek, GPT-4, Qwen, etc.)
- Customize voice assistant prompts and behavior

✅ Face recognition supported

**Requirements:** Internet connection · LLM API keys required

## Step 1: Warehouse System {#warehouse_2b type=docker_deploy required=true config=devices/warehouse_deploy.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Target {#warehouse_2b_local type=local config=devices/warehouse_deploy.yaml}

Run the warehouse system on this computer.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target {#warehouse_2b_remote type=remote config=devices/warehouse_deploy.yaml default=true}

Deploy to reComputer Super J4012 edge device.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect J4012 to power and ethernet, ensure it's on the same network as your computer
2. Check your router for J4012's IP address and enter it
3. Enter username `recomputer`, password `12345678`
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check ethernet cable, verify IP address is correct |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 2: Configure Warehouse System {#warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 3: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi_deploy.yaml}

Deploy the voice AI service to enable voice interaction with Watcher. Select "Private Cloud" mode and fill in your LLM API details.

### Target {#voice_local type=local config=devices/xiaozhi_deploy.yaml}

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target {#voice_remote type=remote config=devices/xiaozhi_deploy.yaml default=true}

### Wiring

1. Enter J4012 IP address and SSH credentials
2. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Image pull failed | Check network connection, or configure Docker mirror |
| Port in use | Check if ports 18000, 18003, 18004 are used by other services |
| API call failed | Verify API key is correct and has sufficient balance |

---

## Step 4: Configure Watcher Device {#watcher_config type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Connect your Watcher to SenseCraft cloud platform:

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named "Watcher-XXXX" and connect
3. Your browser should pop up the setup page automatically (if not, visit http://192.168.4.1 manually)
4. Wait about 5 seconds for the WiFi scan to complete, pick a 2.4GHz network, enter the password, then tap "Connect"
5. The device reboots automatically and shows a 6-digit verification code on the screen
6. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), click "SenseCraft Watcher" in Models, select "Watcher Agent" → "Bind Device", and enter the 6-digit code to complete binding
7. Click "Create" to make a new Agent, click the ⚙ settings icon on the Agent card, select the "Inventory Manager" role template, adjust name and language as needed, then save
8. In the ⚙ settings page, scroll to the bottom, click "MCP Setting" → "Get MCP Endpoint" → "Copy Endpoint URL"

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Can't find Watcher Agent | Confirm you're logged in to SenseCraft, refresh the page |

---

## Step 5: Connect to Agent {#agent_config type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Open your browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
3. Paste the endpoint URL copied from MCP Setting in the previous step
4. Click "Save and Start"
5. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 6: Demo & Testing {#demo type=manual required=false}

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

| Issue | Solution |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |

## Step 7: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The warehouse management dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your multi-site private cloud warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- Voice Service Console: http://\<server-ip\>:18003

Your data stays on your network. Try saying "How many apples left?" to test.

---

## Preset: Tier 3 · Premium {#edge_computing}

Run everything locally including LLM and TTS - no internet required after deployment. Ideal for air-gapped environments or strict data compliance.

| Device | Purpose |
|--------|---------|
| SenseCAP Watcher | Voice assistant, receives voice commands |
| reComputer R2135-12 | Runs warehouse system + voice AI service |
| reComputer Robotics J5011 | Runs local LLM and TTS, fully offline |

**What you'll get:**
- 100% offline operation - works without internet
- All data stays within your local network
- Local LLM inference at ~16 tokens/sec

✅ Face recognition supported

**Requirements:** reComputer Robotics J5011 · Internet needed for initial deployment only

## Step 1: Warehouse System {#warehouse_t3 type=docker_deploy required=true config=devices/warehouse_deploy.yaml}

Deploy the inventory management service with voice control and web dashboard.

### Target {#warehouse_t3_local type=local config=devices/warehouse_deploy.yaml}

Run the warehouse system on this computer.

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port in use | Check if port 2125 is used by another service |
| Docker not running | Start Docker Desktop and retry |

### Target {#warehouse_t3_remote type=remote config=devices/warehouse_deploy.yaml default=true}

Deploy to reComputer R2135-12 edge device.

### Wiring

![Wiring](gallery/R1100_connected.png)

1. Connect R2135-12 to power and ethernet, ensure it's on the same network as your computer
2. Enter IP address `reComputer-R110x.local` (or check your router)
3. Enter username `recomputer`, password `12345678`
4. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection timeout | Check ethernet cable, test with ping reComputer-R110x.local |
| SSH auth failed | Verify credentials, first-time setup requires monitor connection |

---

## Step 2: Configure Warehouse System {#warehouse_config type=manual required=true}

![Setup Demo](gallery/setup_warehous.gif)

After deployment, open the warehouse system to complete initial setup:

1. Open browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. First visit will show "Set Administrator" dialog, fill in details and confirm
3. Click "Inventory List" on the left to import existing inventory ([Download Excel Template](https://files.seeedstudio.com/Solution/landpage_asset/smart-warehouse-management/warehouse_import-9e6e51d1.xlsx))

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page won't load | Wait 30 seconds for services to start |
| Import failed | Check if Excel format matches the template |
| Forgot admin password | Go to "Device Management", delete this app (check "Delete data"), then redeploy |

---

## Step 3: Jetson Local AI {#jetson_ai type=docker_deploy required=true config=devices/llm_jetson_deploy.yaml}

Deploy local LLM and TTS services on the Jetson device.

### Target {#local type=local config=devices/llm_jetson_deploy.yaml default=true}

Deploy directly on this Jetson (the same device running SenseCraft Solution). First place `mlc-qwen3-fs.tar.gz` and `models-backup.tar.gz` in the solution's `dist/` folder.

### Target {#jetson_remote type=remote config=devices/llm_jetson_deploy.yaml}

### Wiring

1. Connect Jetson (reComputer Robotics J5011) to power and ethernet
2. Enter Jetson IP address and SSH credentials
3. Select model (Qwen3-8B recommended, requires ~4.3GB VRAM)
4. Choose deployment method (offline package recommended)
5. Click Deploy and wait for image import and service startup

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Confirm Jetson is powered on, verify IP address |
| Insufficient VRAM | Choose smaller model (Qwen3-4B ~2.5GB, Qwen3-1.7B ~1.2GB) |
| Deployment takes long | Offline package is large (~5GB), please be patient |

---

## Step 4: Voice AI Service {#voice_service type=docker_deploy required=true config=devices/xiaozhi_deploy.yaml}

Deploy voice AI service on R2135-12, connecting to Jetson for inference. Select "Edge Computing" mode and enter the Jetson IP address (auto-filled if Jetson was deployed in previous step).

### Target {#voice_local type=local config=devices/xiaozhi_deploy.yaml}

### Wiring

1. Ensure Docker is installed and running
2. Click Deploy button to start services

### Target {#voice_remote type=remote config=devices/xiaozhi_deploy.yaml default=true}

### Wiring

1. Enter R2135-12 IP address and SSH credentials
2. Click Deploy and wait for installation to complete

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect to Jetson | Check if R2135-12 and Jetson are on the same network |
| Response is slow | Confirm Jetson service is running, visit `http://Jetson-IP:8000/health` to check |

---

## Step 5: Configure Watcher Device {#watcher_config type=manual required=true}

![Agent Setup](gallery/configure_agent.gif)

Connect your Watcher to SenseCraft cloud platform:

1. Power on Watcher: press and hold the top-right scroll button for 5 seconds, then release
2. On your phone, search for the WiFi hotspot named "Watcher-XXXX" and connect
3. Your browser should pop up the setup page automatically (if not, visit http://192.168.4.1 manually)
4. Wait about 5 seconds for the WiFi scan to complete, pick a 2.4GHz network, enter the password, then tap "Connect"
5. The device reboots automatically and shows a 6-digit verification code on the screen
6. Login to [SenseCraft AI Platform](https://sensecraft.seeed.cc/ai/device/local/37/), click "SenseCraft Watcher" in Models, select "Watcher Agent" → "Bind Device", and enter the 6-digit code to complete binding
7. Click "Create" to make a new Agent, click the ⚙ settings icon on the Agent card, select the "Inventory Manager" role template, adjust name and language as needed, then save
8. In the ⚙ settings page, scroll to the bottom, click "MCP Setting" → "Get MCP Endpoint" → "Copy Endpoint URL"

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't find hotspot | Make sure phone WiFi is enabled, move closer to Watcher |
| WiFi setup failed | Watcher only supports 2.4GHz WiFi, check if your router has 2.4GHz enabled |
| Can't find Watcher Agent | Confirm you're logged in to SenseCraft, refresh the page |

---

## Step 6: Connect to Agent {#agent_config type=manual required=true}

![MCP Endpoint](gallery/mcp-endpoint.png)

Add an agent in the warehouse system to let Watcher control inventory:

1. Open your browser and visit `http://server-ip:2125` (use `localhost` for local deployment)
2. Go to "Agent Configuration" on the left sidebar, click "Add Agent", fill in the name
3. Paste the endpoint URL copied from MCP Setting in the previous step
4. Click "Save and Start"
5. Click "MCP Endpoint" on the agent card, refresh status - "Connected" means success

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check endpoint URL is copied completely, no extra spaces |
| Status stays Disconnected | Confirm Watcher is properly bound to SenseCraft platform |

---

## Step 7: Demo & Testing {#demo type=manual required=false}

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

| Issue | Solution |
|-------|----------|
| Watcher not responding | Ensure agent is connected (status shows Connected) |
| Inventory not updated | Refresh the web page to see latest data |

## Step 8: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The warehouse management dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |

### Deployment Complete

Your fully offline warehouse system is ready!

**Access points:**
- Warehouse System: http://\<server-ip\>:2125
- Voice Service Console: http://\<server-ip\>:18003
- LLM Health Check: http://\<jetson-ip\>:8000/health

100% offline operation - no internet required after deployment.
