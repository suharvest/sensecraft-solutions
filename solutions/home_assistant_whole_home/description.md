## What this solution does for you

Bring the lights, curtains, air conditioner and Zigbee sensors in a home into Home Assistant and control them by speaking. Speech recognition and speech synthesis run locally on a Jetson, so voice recordings are not sent to a cloud speech service.

## Key benefits

| Benefit | Details |
|---------|---------|
| Control by voice | Say "Turn on the living room light"; Home Assistant runs it and answers out loud |
| Voice stays local | Understanding the command and generating the spoken reply both run on the reComputer J40; Home Assistant executes the command locally |
| Fast response | Median 0.12 s from the end of speech to recognized text |
| Works with Apple Home | Devices in Home Assistant appear in the Home app on iPhone and can be controlled with Siri |
| Zigbee devices without hubs | Plug in the ZBT-2 and Aqara, SONOFF and other Zigbee sensors and switches join Home Assistant directly, without each brand's hub |

## Use cases

| Scenario | How it works |
|----------|--------------|
| Living room, bedroom | Say "Turn on the living room light" or "Turn off the bedroom light" without reaching for a phone |
| Shared by the family | Family members control the same devices from the Home app or Siri on iPhone |
| Smart-home integrator handover | One host connects devices from several brands, and the voice service runs in the customer's home |

## Usage Notes

### Core hardware

| Device | Description | Required |
|--------|-------------|----------|
| ARM64 Linux host (64-bit OS, 8GB RAM) | Runs Home Assistant | ✓ Required |
| reComputer J40 Series (Jetson Orin NX 16GB) | Runs local speech recognition and speech synthesis | ✓ Required |
| Home Assistant Connect ZBT-2 | Plugs into a USB port on the Home Assistant host and connects Zigbee devices | ✓ Required |
| Home Assistant Voice Preview Edition | Voice terminal in the room: listens for commands and plays replies | ✓ Required |
| SONOFF SNZB Zigbee sensor | Reports room temperature, humidity and similar states | Optional |

### Network requirements

- The Home Assistant host, the reComputer J40 and the voice terminal are on the same local network
- The reComputer J40 needs internet access on first start to download the voice models (reserve at least 30 GB of disk); after that, speech recognition and speech synthesis run on the device
- To use the Apple Home app, the iPhone and the Home Assistant host are on the same local network

### Languages

- Chinese and English voice commands

### Xiaomi Home devices

- Home Assistant's official Xiaomi Home integration is licensed for non-commercial use only and is not installed by this solution. For personal home use you can install it yourself in Home Assistant; do not use it in a commercial delivery.

### Measured results

| Metric | Result |
|--------|--------|
| Chinese and English light on/off commands | 5 of 5 executed, all handled locally by Home Assistant |
| End of speech to recognized text | Median 0.12 s (0.11–0.95 s) |
| Text-to-speech first audio | 0.05–0.12 s |

Conditions: Home Assistant on an ARM64 Linux host with 8GB RAM, voice services on a reComputer J40 (Jetson Orin NX 16GB); input was synthesized speech audio sent to the Home Assistant voice assistant.
