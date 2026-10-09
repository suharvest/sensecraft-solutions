## Preset: ARM64 Linux Host + Voice Host {#rpi_jetson}

An ARM64 Linux host runs Home Assistant, and a voice host understands speech and generates the spoken replies; questions other than device control are answered by an LLM. The two devices work together on the same local network.

| Device | Purpose |
|--------|---------|
| ARM64 Linux host (64-bit OS, 8GB RAM) | Runs Home Assistant |
| Voice host (any one from the table below) | Local speech recognition and speech synthesis |
| Home Assistant Connect ZBT-2 | Connects Zigbee devices |
| Home Assistant Voice Preview Edition | Voice terminal in the room |

| Voice host | Answers questions other than device control with |
|------|------|
| reComputer J40 (Jetson Orin NX 16GB) | An LLM running on the device |
| reComputer RK3588 (16GB) + RK1828 accelerator card | An LLM running on the card |
| reComputer RK3588 (without RK1828 card) | The cloud LLM service you enter |
| reComputer J30 (Jetson Orin Nano 8GB) | The cloud LLM service you enter |
| reComputer RK3576 (8GB) | The cloud LLM service you enter |

**What you'll get:**
- Control lights and other devices by voice in Chinese or English, with a median 0.12 s from end of speech to recognized text
- Ask questions such as "Is it a good day to open the windows?" and get an answer from the LLM; device commands are still executed locally by Home Assistant
- Zigbee sensors and switches in Home Assistant
- The same devices in the Home app and Siri on iPhone

**Requirements:** Both devices on the same local network · Internet access on the voice host's first start to download the models · For a cloud LLM: the address, model name and API key of an OpenAI-compatible LLM service

## Step 1: Deploy Home Assistant {#rpi_deploy type=docker_deploy required=true config=devices/ha_rpi.yaml}

Install Home Assistant on the ARM64 Linux host.

### Prerequisites

- The host runs a 64-bit Linux OS and has at least 8 GB of free disk
- The ZBT-2 can be added later: leave "ZBT-2 device path" empty, then fill in the path and deploy again once the ZBT-2 is plugged in

### Wiring

1. Connect the ARM64 Linux host to the local network and power it on
2. Plug the ZBT-2 into a USB port on the host; run `ls /dev/serial/by-id/` on the host and enter the listed path as "ZBT-2 device path"
3. The default port is 8123; if another program on the host already uses 8123, enter a different port
4. Click Deploy

### Deployment Complete

1. Open **http://\<host-ip\>:8123** in your browser (use your port if you changed it); the first start takes a moment
2. Follow the prompts to create the administrator account

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port already in use | Enter another port in "Home Assistant port" and deploy again |
| Changed the port but Home Assistant still uses the old one | An existing Home Assistant installation keeps the port from its first install and ignores the deploy setting; keep using the original port |
| Configuration folder is not writable | On the host, run `sudo mkdir -p /opt/ha-whole-home/ha-config && sudo chown $USER /opt/ha-whole-home/ha-config`, then deploy again |
| Page does not load | Wait a few minutes and refresh; make sure your computer and the host are on the same local network |
| ZBT-2 does not appear in Home Assistant | Make sure "ZBT-2 device path" is the full path under `/dev/serial/by-id/`, then deploy again |
| Cannot connect to the host | Check the IP address, username and password, and that the host is powered on and on the network |

### Target: Local Deployment {#rpi_local type=local device=arm64_linux device_name="ARM64 Linux host (64-bit OS, 8GB RAM)" config=devices/ha_rpi.yaml}

Install on this ARM64 Linux host.

### Target: Remote Deployment {#rpi_remote type=remote device=arm64_linux device_name="ARM64 Linux host (64-bit OS, 8GB RAM)" config=devices/ha_rpi.yaml default=true}

Install on the ARM64 Linux host over the network; you need its IP address, username and password.

---

## Step 2: Deploy the voice host {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

Install the speech recognition and speech synthesis services on the voice host for Home Assistant to use. The reComputer J40 and the RK3588 with an RK1828 card also install a local LLM; the other voice hosts use the cloud LLM service you enter.

### Prerequisites

- Free disk: at least 40 GB on the reComputer J40, 20 GB on the J30, 16 GB on the RK3588 + RK1828, 10 GB on the RK3588 and RK3576
- Internet access on first start to download the models; the services are not available until the download finishes
- RK3588 + RK1828: the card is powered, its driver and firmware are installed (a `/dev/pcie-rkep-*` device exists), and no other LLM runs on the card
- Cloud LLM: the address of an OpenAI-compatible service (for example `https://api.deepseek.com`), a model name and an API key

### Wiring

1. Connect the voice host to the same local network as the Home Assistant host and power it on
2. Keep the default ports: speech-to-text 10300, text-to-speech 10200, voice service 8623, local LLM 8000 (J40) or 1828 (RK1828); change one only if it is already in use
3. For a voice host with a cloud LLM: enter the LLM API address, model name and API key; deployment checks all three first
4. Note the voice host's IP address and ports for step 3
5. Click Deploy

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Not enough disk space | Free the space listed under Prerequisites and deploy again |
| Port already in use | Choose an unused port and deploy again; the ports must be different |
| Services do not become ready for a long time | The first start downloads the models first, and the time depends on your connection; make sure the voice host can reach the internet |
| NVIDIA container runtime missing | Make sure the reComputer J40 / J30 runs a full JetPack installation that includes the NVIDIA container runtime, then retry |
| RK1828 card not found | Check the card's power, driver and firmware; without the card, choose "RK3588 (cloud LLM)" instead |
| The LLM API key is rejected | Check that the key is complete and active with the provider |
| The LLM service cannot be reached | Check the API address and that the voice host can reach the internet |
| The model is not found | Enter the model name exactly as it appears in the provider's model list |
| Cannot connect to the device | Check the IP address, username and password, and that the device is powered on and on the network |

### Target: Local Deployment {#jetson_local type=local device=jetson device_name="reComputer J40 (Jetson Orin NX 16GB)" config=devices/jetson_voice.yaml}

Install on this reComputer J40; the LLM runs on the device.

### Target: Remote Deployment {#jetson_remote type=remote device=jetson device_name="reComputer J40 (Jetson Orin NX 16GB)" config=devices/jetson_voice.yaml default=true}

Install on the reComputer J40 over the network; the LLM runs on the device. You need its IP address, username and password.

### Target: RK3588 + RK1828 (local LLM) {#rk3588_rk1828_remote type=remote device=rk3588_rk1828 device_name="reComputer RK3588 (16GB) + RK1828" config=devices/rk3588_rk1828_voice.yaml}

Install on a reComputer RK3588 with an RK1828 card over the network; the LLM runs on the card. You need its IP address, username and password.

### Target: RK3588 (cloud LLM) {#rk3588_remote type=remote device=rk3588 device_name="reComputer RK3588" config=devices/rk3588_voice.yaml}

Install on a reComputer RK3588 without the card over the network; questions other than device control are answered by the cloud LLM you enter.

### Target: J30 (cloud LLM) {#j30_remote type=remote device=j30 device_name="reComputer J30 (Jetson Orin Nano 8GB)" config=devices/jetson_nano_voice.yaml}

Install on a reComputer J30 over the network; questions other than device control are answered by the cloud LLM you enter.

### Target: RK3576 (cloud LLM) {#rk3576_remote type=remote device=rk3576 device_name="reComputer RK3576 (8GB)" config=devices/rk3576_voice.yaml}

Install on a reComputer RK3576 over the network; questions other than device control are answered by the cloud LLM you enter.

---

## Step 3: Connect local voice and verify {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

Add the voice services and the LLM conversation agent to Home Assistant, then test.

### Deployment Complete

1. Open Home Assistant, go to **Settings → Devices & services → Add integration** and search for **Wyoming Protocol**; enter the voice host's IP address as host and the speech-to-text port from step 2 (default 10300) as port
2. Add a second **Wyoming Protocol** integration with the same host and the text-to-speech port (default 10200)
3. Add a **LiteLLM** integration:
   - reComputer J40 or RK3588 + RK1828: enter `http://<voice-host-ip>:<local LLM port>` (default 8000 or 1828) as the URL and leave the API key empty
   - Other voice hosts: enter the LLM API address and API key from step 2
4. In the LiteLLM integration, add a conversation agent: choose the model name from step 2 (a local LLM lists only one model), leave "Control Home Assistant" unchecked, and save
5. Go to **Settings → Voice assistants**, open the assistant and set the language to Chinese or English; choose the new LiteLLM agent as "Conversation agent" and turn on "Prefer handling commands locally"; select the two new Wyoming services for "Speech-to-text" and "Text-to-speech", and save
6. Click the conversation button at the top right and say or type "Turn on the living room light"; the light turns on and you get a reply. Then ask "Is it a good day to open the windows?" and you get an answer from the LLM

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Adding the integration fails to connect | Make sure step 2 is ready, the IP address and port are correct, and the Home Assistant host can reach the voice host |
| Adding LiteLLM fails to connect or reports an invalid key | Local LLM: wait until step 2 is ready and retry; cloud LLM: check the address and key, and that the Home Assistant host can reach the internet |
| Device commands are answered by the LLM | Turn on "Prefer handling commands locally" in the voice assistant |
| Other questions only get "I don't understand" | Choose the LiteLLM agent as the voice assistant's "Conversation agent" |
| The voice services are not listed in the voice assistant | Make sure both Wyoming Protocol integrations were added successfully |
| Voice stopped working after redeploying step 2 with different ports | Delete both Wyoming Protocol integrations and add them again with the new ports |
| The command is recognized but nothing happens | Make sure the name in the command matches the device or area name in Home Assistant |

---

# Deployment Complete

Home Assistant and the local voice services are ready.

### Initial Setup

1. **Add Zigbee devices**: go to **Settings → Devices & services → Add integration**, choose **Zigbee Home Automation** and select the ZBT-2 serial port; then click "Add device" in that integration and put the Zigbee device into pairing mode
2. **Add to Apple Home**: a HomeKit Bridge pairing QR code appears in the Home Assistant notifications; scan it with the Home app on iPhone
3. **Add the voice terminal**: follow the Home Assistant Voice Preview Edition instructions to connect it to Wi-Fi and add it to Home Assistant, then select the voice assistant configured in step 3 on its device page

### Quick Verification

- Say "Turn on the living room light" to the voice terminal; the light turns on and you hear a reply
- The same devices are visible and controllable in the Home app on iPhone
- Zigbee sensor readings update in Home Assistant
