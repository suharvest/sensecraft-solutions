## Preset: ARM64 Linux Host + Jetson Orin NX Voice {#rpi_jetson}

An ARM64 Linux host runs Home Assistant, and a reComputer J40 understands speech and generates the spoken replies. The two devices work together on the same local network.

| Device | Purpose |
|--------|---------|
| ARM64 Linux host (64-bit OS, 8GB RAM) | Runs Home Assistant |
| reComputer J40 Series (Jetson Orin NX 16GB) | Local speech recognition and speech synthesis |
| Home Assistant Connect ZBT-2 | Connects Zigbee devices |
| Home Assistant Voice Preview Edition | Voice terminal in the room |

**What you'll get:**
- Control lights and other devices by voice in Chinese or English, with a median 0.12 s from end of speech to recognized text
- Zigbee sensors and switches in Home Assistant
- The same devices in the Home app and Siri on iPhone

**Requirements:** Both devices on the same local network · At least 30 GB free disk on the reComputer J40, and internet access on first start to download the voice models

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
| Home Assistant was installed by an earlier version of this solution and starts with a new, empty configuration after redeploying | Earlier versions stored the configuration in `/opt/ha-whole-home/ha-config`; it now lives in `~/ha-whole-home/ha-config` and is not moved automatically. On the host, run `docker stop $(docker ps -q --filter label=com.docker.compose.project=ha_whole_home_rpi)`, then `mkdir -p ~/ha-whole-home && sudo cp -a /opt/ha-whole-home/ha-config/. ~/ha-whole-home/ha-config/`, then deploy again |
| Page does not load | Wait a few minutes and refresh; make sure your computer and the host are on the same local network |
| ZBT-2 does not appear in Home Assistant | Make sure "ZBT-2 device path" is the full path under `/dev/serial/by-id/`, then deploy again |
| Cannot connect to the host | Check the IP address, username and password, and that the host is powered on and on the network |

### Target: Local Deployment {#rpi_local type=local device=arm64_linux device_name="ARM64 Linux host (64-bit OS, 8GB RAM)" config=devices/ha_rpi.yaml}

Install on this ARM64 Linux host.

### Target: Remote Deployment {#rpi_remote type=remote device=arm64_linux device_name="ARM64 Linux host (64-bit OS, 8GB RAM)" config=devices/ha_rpi.yaml default=true}

Install on the ARM64 Linux host over the network; you need its IP address, username and password.

---

## Step 2: Deploy Jetson voice services {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

Install the speech recognition and speech synthesis services on the reComputer J40 for Home Assistant to use.

### Prerequisites

- reComputer J40 (Jetson Orin NX 16GB) with at least 30 GB of free disk
- Internet access on first start to download the voice models; the services are not available until the download finishes

### Wiring

1. Connect the reComputer J40 to the same local network as the Home Assistant host and power it on
2. Keep the default ports: speech-to-text 10300, text-to-speech 10200, voice service 8623; change one only if it is already in use
3. Note the reComputer J40's IP address and these two ports for step 3
4. Click Deploy

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Not enough disk space | Free at least 30 GB and deploy again |
| Port already in use | Choose an unused port and deploy again; the three ports must be different |
| Services do not become ready for a long time | The first start downloads the voice models first, and the time depends on your connection; make sure the reComputer J40 can reach the internet |
| NVIDIA container runtime missing | Make sure the reComputer J40 runs a full JetPack installation that includes the NVIDIA container runtime, then retry |
| Cannot connect to the device | Check the IP address, username and password, and that the device is powered on and on the network |

### Target: Local Deployment {#jetson_local type=local device=jetson device_name="reComputer J40 (Jetson Orin NX 16GB)" config=devices/jetson_voice.yaml}

Install on this reComputer J40.

### Target: Remote Deployment {#jetson_remote type=remote device=jetson device_name="reComputer J40 (Jetson Orin NX 16GB)" config=devices/jetson_voice.yaml default=true}

Install on the reComputer J40 over the network; you need its IP address, username and password.

---

## Step 3: Connect local voice and verify {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

Add the voice services to Home Assistant, then test with one sentence.

### Deployment Complete

1. Open Home Assistant, go to **Settings → Devices & services → Add integration** and search for **Wyoming Protocol**; enter the reComputer J40's IP address as host and the speech-to-text port from step 2 (default 10300) as port
2. Add a second **Wyoming Protocol** integration with the same host and the text-to-speech port (default 10200)
3. Go to **Settings → Voice assistants**, open the assistant, set the language to Chinese or English, select the two new services for "Speech-to-text" and "Text-to-speech", and save
4. Click the conversation button at the top right and say or type "Turn on the living room light"; the light turns on and you get a reply

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Adding the integration fails to connect | Make sure step 2 is ready, the IP address and port are correct, and the Home Assistant host can reach the reComputer J40 |
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
