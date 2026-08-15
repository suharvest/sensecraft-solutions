## What This Solution Does

Turn an edge device into a voice terminal that can listen, think, and speak continuously. Connect a hardware-AEC microphone array and a speaker; the device captures speech, produces a reply, and immediately stops that reply when the user starts speaking again.

This is a persistent device application, not a push-to-talk browser demo. The on-device agent owns the microphone and speaker, making it suitable for robots, kiosks, service desks, smart-home terminals, and unattended exhibits.

## Core Value

| Benefit | What it means |
|---------|---------------|
| Natural interruption | Capture stays active during playback; new speech cancels generation, drains queued audio, and starts the next turn |
| Pluggable conversation layer | Use Qwen API or another OpenAI-compatible endpoint, or keep the model local on supported hardware |
| One experience across four platforms | RK3576, RK3588, Orin Nano, and Orin NX share the same duplex protocol and agent behavior |
| Local audio processing | Qwen3-ASR and Matcha-TTS run on the device; the fully local preset also keeps conversation text on-device |

## Where It Fits

| Scenario | Example |
|----------|---------|
| Service desk or exhibit | A visitor interrupts an irrelevant answer and immediately asks a clearer question |
| Robot voice front end | Feed continuous conversation into robot actions or business tools without changing the speech layer |
| Smart-home terminal | Far-field speech remains usable while hardware AEC suppresses the terminal's own speaker output |
| Product prototyping | Validate with a cloud model first, then move to RK1828 or Orin NX local inference |

## Usage Notes

### Required Hardware

| Device | Purpose | Required |
|--------|---------|----------|
| RK3576, RK3588, Orin Nano, or Orin NX | Runs speech recognition, synthesis, and the resident voice agent | Choose one |
| reSpeaker XVF3800 or equivalent AEC array | Exposes a capture channel with echo already removed | Yes |
| USB or analog speaker | Plays replies | Yes |
| RK1828 / RM182X | Runs local Qwen3-4B with an RK3588 host | RK local preset only |

### AEC and Barge-in Boundaries

- Software does not replace acoustic echo cancellation. A basic USB microphone may re-capture speaker output and cause false interruptions or an echo loop.
- The validated reSpeaker XVF3800 2-channel and 6-channel firmware layouts are detected automatically. Unknown microphones default to the first capture channel and need an acoustic check.
- Muting the microphone during playback is not recommended: it prevents echo, but it also makes barge-in impossible.

### Network

- First deployment downloads images and model artifacts and needs stable internet plus sufficient disk space.
- The cloud preset needs ongoing API access. Fully local presets can run offline after artifacts are cached.
- Qwen defaults use the Beijing OpenAI-compatible endpoint. Replace the base URL and model ID for another region or provider.

## Deployment Comparison

| Preset | Conversation model | Supported devices | Best for |
|--------|--------------------|-------------------|----------|
| Cloud or compatible endpoint | Qwen API or any OpenAI-compatible model | RK3576 / RK3588 / Orin Nano / Orin NX | Fastest path to full conversation |
| Fully local conversation | RK1828 Qwen3-4B or Orin NX Qwen3.5-4B | RK3588 + RK1828 / Orin NX 16GB | Privacy, offline use, and fixed operating cost |

### Technical Stack

- Speech recognition: Qwen3-ASR
- Voice synthesis: Matcha-TTS
- Duplex control: one persistent session, continuous capture, playback cancellation, and conversation truncation
- Conversation API: OpenAI-compatible Chat Completions
