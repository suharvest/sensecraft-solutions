## What this solution does for you

Bring the lights, curtains, air conditioner and Zigbee sensors in a home into Home Assistant and control them by speaking. Speech recognition and speech synthesis run locally on the voice host, so voice recordings are not sent to a cloud speech service; questions other than device control are answered by an LLM.

## Key benefits

| Benefit | Details |
|---------|---------|
| Control by voice | Say "Turn on the living room light"; Home Assistant runs it and answers out loud |
| Voice stays local | Understanding the command and generating the spoken reply both run on the voice host; Home Assistant executes the command locally |
| Ask other questions too | Questions such as "Is it a good day to open the windows?" go to an LLM: the reComputer J40 and the RK3588 with an RK1828 card run it on the device, the other voice hosts use the cloud LLM service you enter |
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
| Voice host: reComputer J40 (Orin NX 16GB), J30 (Orin Nano 8GB), RK3588 or RK3576 (8GB), any one | Runs local speech recognition and speech synthesis; the J40 and an RK3588 (16GB) with an RK1828 card also run a local LLM | ✓ Required |
| Home Assistant Connect ZBT-2 | Plugs into a USB port on the Home Assistant host and connects Zigbee devices | ✓ Required |
| Home Assistant Voice Preview Edition | Voice terminal in the room: listens for commands and plays replies | ✓ Required |
| SONOFF SNZB Zigbee sensor | Reports room temperature, humidity and similar states | Optional |

### Network requirements

- The Home Assistant host, the voice host and the voice terminal are on the same local network
- The voice host needs internet access on first start to download the models; after that, speech recognition and speech synthesis run on the device
- With a cloud LLM, questions other than device control are sent as text to the LLM service you enter; device commands do not go through the LLM
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

| RK3588 voice host | Result |
|------|------|
| "打开客厅灯" (turn on the living room light) | Recognized as "打开客厅灯。", executed locally by Home Assistant, the light turned on |
| "今天适合开窗吗" (is it a good day to open the windows) | Recognized as "今天适合开窗吗？", answered by the LLM: 1.45 s with the RK1828 local LLM, 1.59–1.77 s with the cloud LLM |
| End of speech to recognized text | 0–0.13 s |

Conditions: Home Assistant 2026.9.3 on a separate ARM64 Linux host, voice services on an RK3588 (16GB); local LLM Qwen3-4B on the RK1828 card, cloud LLM DeepSeek; input was synthesized speech audio sent to the Home Assistant voice assistant; LLM time is from the conversation agent receiving the text to its answer.
