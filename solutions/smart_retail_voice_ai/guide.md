## Preset: Standard Deployment {#default}

Deploy an edge-based voice collection and analysis system for your retail store.

| Device | Purpose |
|--------|---------|
| reRouter CM4 | Edge computing device, runs voice services |
| reSpeaker XVF3800 | 4-mic array for capturing store conversations |

**What you'll get:**
- Real-time voice transcription from store conversations
- Speaker recognition - identify who is speaking
- [SenseCraft Voice](https://test-voice-web.seeed.cn/) cloud platform for multi-store analytics
- Privacy-first design - audio processing happens on-device

**Requirements:** USB-C data cable · Network cables

## Step 1: Flash OpenWrt Firmware {#firmware type=manual required=false}

Write the operating system to the reRouter, then connect it to your network. **Skip this step** if your reRouter was purchased after November 2025 — it already has the correct firmware.

| Device | Connection | Notes |
|--------|------------|-------|
| reRouter CM4 | Remove case to access the board | Required for entering boot mode |
| USB-C cable | Connect reRouter to computer | For eMMC flashing |
| Computer | Install rpiboot tool first | Otherwise the eMMC won't be recognized |

**Prerequisites:**

- Install **rpiboot** tool — the computer cannot recognize the eMMC without it
  - **Windows:** Download and run [rpiboot installer](https://github.com/raspberrypi/usbboot/raw/master/win32/rpiboot_setup.exe)
  - **Mac/Linux:** Build from source — `git clone --depth=1 https://github.com/raspberrypi/usbboot && cd usbboot && make`

**Flashing Steps:**

1. Remove the reRouter case to access the CM4 board
2. Connect the jumper between the **Boot** and **GND** pins on the board to enter boot mode (see image below)

   ![Boot mode](gallery/boot-mode.png)

3. Connect reRouter to computer via USB-C, then run **rpiboot** — the eMMC will appear as a USB drive
4. Download firmware (you **must** use the links below to ensure the default IP is `192.168.49.1`):
   - [Global](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/OpenWRT-24.10.3-RPi-4-Factory.img.gz) | [China](https://files.seeedstudio.com/wiki/solution/ai-sound/reRouter-firmware-backup/OpenWRT-24.10.3-RPi-4-Factory-Chinese.img.gz)
5. Flash the firmware using either tool:
   - [Raspberry Pi Imager](https://www.raspberrypi.com/software/) — select "Use custom" and choose the firmware
   - [balenaEtcher](https://etcher.balena.io/) — select firmware file and target drive, click "Flash"
6. After flashing, remove the Boot-GND jumper, reassemble the case, connect cables and power on

> For detailed flashing instructions, see [reRouter Flashing Guide](https://wiki.seeedstudio.com/OpenWrt-Getting-Started/#initial-setup).

**First Connection:**

1. Connect computer to reRouter's **LAN port** with network cable
2. Connect **WAN port** to your router with another network cable
3. Wait 1-2 minutes for boot
4. Visit `http://192.168.49.1` in browser (this is the default OpenWrt LAN IP)
5. Login: username `root`, password empty

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot access 192.168.49.1 | 1) Make sure cable is in the **LAN** port; 2) Make sure you flashed the firmware from the links above (other firmware may use a different IP) |
| Page loads slowly | Wait 2 minutes for the system to fully boot |
| rpiboot doesn't detect the device | Make sure the Boot-GND jumper is connected; try a different USB-C cable |
| Flashing failed | Format the storage device and try again |
| Login failed | Password is empty, just click login |

---

## Step 2: Deploy Voice Services {#voice_services type=docker_deploy required=true config=devices/voice_services_deploy.yaml}

Start the voice recognition and analysis services on the device.

### Target {#voice_services_local type=local config=devices/voice_services_deploy.yaml}

Deploy voice services on your local computer.

### Wiring

| Device | Connection | Notes |
|--------|------------|-------|
| reSpeaker XVF3800 | USB to computer | Make sure it's a data cable, not just a charging cable |
| Computer | Docker Desktop installed | Download for Windows/Mac |

1. Make sure Docker Desktop is installed and running
2. Confirm reSpeaker XVF3800 is connected via USB
3. Verify at least 2GB free disk space and port 8090 is available
4. Check reSpeaker is recognized: **Windows** Device Manager > Sound controllers; **Mac** System Preferences > Sound > Input; **Linux** run `arecord -l`

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker not running | Start the Docker Desktop application |
| Port 8090 is occupied | Close the program using that port, or modify the configuration to use a different port |
| Microphone device not found | Unplug and replug USB, verify it appears in Device Manager |
| Container startup failed | Check Docker logs: `docker logs sensecraft-voice-client` |

### Target {#voice_services_remote type=remote config=devices/voice_services_deploy.yaml default=true}

Deploy voice services to a remote device (reRouter, Raspberry Pi, etc.).

### Wiring

![Wiring](gallery/wan_lan.png)

| Device | Connection | Notes |
|--------|------------|-------|
| reSpeaker XVF3800 | USB to reRouter | Audio settings are configured automatically during deployment |
| reRouter CM4 | WAN port to router | Internet required for downloading container images |
| reRouter CM4 | LAN port to computer | For SSH access and deployment |
| Computer | Same network as reRouter | For running remote deployment |

1. Confirm reRouter WAN port is connected to router and has internet
2. Connect computer to reRouter LAN port
3. Default SSH: IP `192.168.49.1`, user `root`, no password
4. Plug reSpeaker XVF3800 into reRouter USB port

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection refused | Make sure the cable is plugged into the LAN port and the IP is correct |
| Authentication failed | OpenWrt default password is empty, just press Enter |
| Image download timeout | Check the WAN port network connection, make sure you can access the internet |
| Container startup failed | SSH in and run `docker logs sensecraft-voice-client` to view error messages |
| Microphone not found | Run `arecord -l` to verify reSpeaker is recognized |
| "Health check failed" warning in logs | Normal during startup - the voice client starts before the ASR server is ready. Wait 30 seconds and check again |

---

## Step 3: User Onboarding Guide {#user_guide type=manual required=false}

Verify your system is working and connect it to the cloud platform.

**Step 1: Open Edge Client and Start Recording**

1. Open **http://\<device-ip\>:8090** in your browser (default: `http://192.168.49.1:8090`)

   ![Edge Client ASR](gallery/edge-client-asr.png)

2. Click the **Record** button — speak near the reSpeaker and watch transcribed text appear in real time
3. Navigate to the **Device Status** page in the sidebar

   ![Device Status](gallery/edge-client-device.png)

4. The upstream server address is pre-configured — your device will auto-register to the cloud platform once it can reach the server

**Step 2: Find Your Device on the Cloud Platform**

1. Open **https://test-voice-web.seeed.cn/**
2. Go to **Store Management** — locate your device by its IP address or MAC address

   ![Device Management](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/cloud/device-management.png)

3. Click your device to take control — all transcribed voice records are now available under **Record Management**

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Edge client not loading | Wait 2 minutes after reboot for services to fully start |
| No transcription appearing | SSH in and run `arecord -l` to verify reSpeaker is recognized |
| Device not showing in cloud platform | Check the upstream server address on the Device Status page |
| Recording button unresponsive | Refresh the page — ASR server may still be initializing (takes ~60s) |
### Deployment Complete

Voice AI system is ready!

#### Verify Deployment

After deployment, confirm all services are running:

```bash
# Check container status — all three should show "Up"
docker ps

# Check voice client initialization logs
docker logs sensecraft-voice-client
```

Then reboot the device to ensure all settings and audio permissions take effect:

```bash
reboot
```

Wait 2 minutes after reboot before proceeding.

#### Service Access

| Service | URL | Purpose |
|---------|-----|---------|
| Edge Client | http://\<device-ip\>:8090 | Real-time transcription, speaker management, device settings |
| OpenWrt Admin | http://\<device-ip\> | Network configuration, system management |
| SenseCraft Voice | https://test-voice-web.seeed.cn/ | Cloud platform — multi-store analytics, AI analysis, data export |

---

#### Edge Client (http://\<device-ip\>:8090)

The edge client runs locally on the reRouter and provides three modules:

##### Voice ASR

![Voice ASR](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/edge/voice-asr.png)

Shows the real-time operational status of the on-device ASR service. Speak near the reSpeaker and watch transcription appear instantly — use this to verify audio input is working and recognition accuracy meets your needs.

##### Voiceprint Recognition

![Voiceprint Recognition](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/edge/voiceprint-recognition.png)

Register speaker voiceprints so the system can automatically identify who is speaking in recordings. The system builds unique voiceprints from audio samples — once registered, speakers are labeled automatically in all future transcriptions.

##### Device Status & Configuration

![Device Status](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/edge/device-status-configuration.png)

View reRouter operating status and adjust core parameters:

- **Network settings** — configure Wi-Fi connection
- **Upstream server address** — the address for syncing data to the cloud platform (pre-configured, change only if using a private deployment)

---

#### Cloud Platform (https://test-voice-web.seeed.cn/)

Connect your edge device to the SenseCraft Voice cloud platform for multi-store analytics. Your device will auto-register once the upstream server address is set in the Edge Client.

##### Dashboard

![Dashboard](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/cloud/main-page-dashboard.png)

Operational overview with store filtering — switch between stores and see charts update instantly. Monitors daily collection trends by hour and surfaces keyword hotspot analysis showing which keywords triggered most frequently and from which devices.

##### Record Management

![Record Management](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/cloud/record-management.png)

Search and filter voice records by device name, store name, location, or MAC address. Two viewing modes:
- **Conversation Mode** — review transcribed dialogues
- **Timeline Mode** — play back original audio alongside transcription

Export records in three formats: Markdown, Plain Text (.txt), or original audio files.

##### AI Analysis

![AI Analysis](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/cloud/ai-analysis.png)

Submit filtered voice records to AI for custom processing. The analysis history is stored chronologically so you can review previous sessions. Only one AI prompt is active at a time — configure which prompt to use in Backend Settings.

##### Store Management

![Store Management](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/cloud/device-management.png)

Organize your deployment in a three-level hierarchy: **Store → Location → Device**. Group devices logically to simplify large-scale management — filter records by any level of this hierarchy.

##### Backend Settings

Configure the system's detection and processing behavior:

**Keyword Settings**

![Keyword Settings](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/cloud/keywords-backend-management.png)

Define custom keywords and synonyms for event detection. Assign a color to each keyword for visual highlighting on the dashboard. Supports batch add, edit, and delete.

**AI Prompt Settings**

![AI Prompts](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/cloud/system-prompt-editing.png)

Create custom prompts that control how the AI processes and summarizes voice records. Only one prompt can be active at a time — enable/disable as needed for different analysis tasks.

**User Management**

![User Management](https://files.seeedstudio.com/wiki/solution/ai-sound/sensecraft-voice/cloud/user-management.png)

Control who can access the cloud platform and manage their permissions.

---

#### Next Steps

- [View Wiki Documentation](https://wiki.seeedstudio.com/cn/solutions/smart-retail-voice-ai-solution-1/)
- [SenseCraft Voice Platform](https://test-voice-web.seeed.cn/)
- [Purchase Hardware](https://www.seeedstudio.com.cn/solutions/voicecollectionanalysis-zh-hans)
