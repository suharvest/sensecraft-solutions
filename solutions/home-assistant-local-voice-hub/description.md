## What the Solution Does

Control the lights and appliances in Home Assistant by voice, with speech recognised locally.

Manage lights, curtains, and air conditioning through natural voice commands, with all speech recognition and synthesis running on a local edge host. Recordings never leave the premises. Designed for smart-home system integrators and automation builders.

- **Direct Local Voice Control**: Say "turn on the living room light" or "close bedroom curtains"; local models process and trigger actions in milliseconds.
- **Unified Whole-Home Access**: Unifies Zigbee, Wi-Fi, and HomeKit smart devices within Home Assistant.
- **Spoken Confirmations**: Integrated local Text-to-Speech (TTS) provides spoken responses directly from the home assistant.

## Core Value

- **Voice Audio Never Leaves Home**: Speech recognition (ASR) and synthesis (TTS) run strictly on local hardware, ensuring private home conversations stay private.
- **Ultra-Low Latency Intent Parsing**: Median latency from end-of-speech to recognized command text is just 0.12 seconds, delivering immediate responsiveness.
- **Multi-Ecosystem Compatibility**: Works with Apple HomeKit Bridge, allowing family members to use the Apple Home app or Siri alongside local voice.
- **Decoupled Architecture**: Home Assistant runs on an ARM64 Linux host while speech services run on a dedicated reComputer J40 Series, connected cleanly over the Wyoming protocol.

## Suitable Scenarios

Homes and spaces where devices are managed via Home Assistant and spoken audio must never be sent to third-party cloud services:

- **Living Rooms and Bedrooms**: Hands-free voice control of lighting, climate, and blinds without reaching for smartphones or remotes.
- **Whole-Family Automation**: Family members interact seamlessly through physical wall switches, Apple Home app, or voice assistants.
- **Smart-Home Integrator Deployments**: Deliver an on-premise, turnkey smart-home solution running entirely on the homeowner's local network.

## Measured Performance

Home Assistant running on an 8 GB ARM64 Linux host, voice pipeline running on a reComputer J40 Series (Orin NX 16GB):

| Metric | Typical | Device |
|---|---|---|
| Chinese and English light commands | **5/5** carried out locally | reComputer J40 Series (J4012) |
| End of speech to recognised text | **median 0.12 s** (0.11–0.95 s) | reComputer J40 Series (J4012) |
| Spoken reply playback start | **0.05–0.12 s** | reComputer J40 Series (J4012) |

## Usage Notes

- **Protocols and Adapters**: Zigbee devices connect via the Connect ZBT-2 USB coordinator; commands are supported in Chinese and English.
- **Third-Party Integrations**: Community integrations such as Xiaomi Home require user-managed setup under their respective licenses; this package bundles only standard open components.
- **Hardware Sizing**: Recommend an ARM64 Linux host with at least 8 GB RAM for Home Assistant, and a reComputer J40 Series with at least 30 GB free storage for voice model runtime.

> 📖 **Engineering Reference:** Full architecture internals, measured benchmarks, and failure modes are documented in the [Engineering Wiki · Home Assistant Local Voice Control](https://wiki.seeedstudio.com/solutions/home-assistant-local-voice/).
