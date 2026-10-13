## What this solution does for you

Conversations recorded on a reSpeaker Clip, such as meetings, consultations or counter service, normally go through the phone app and the cloud to become text. This solution syncs the recordings straight to your own reComputer (Jetson Orin NX or RK3576) and transcribes them there. Recordings stay on site; you read the transcripts on a local web page or pull them into your own system.

## Key benefits

| Benefit | Details |
|---------|---------|
| Recordings stay on site | The Clip syncs to the host over Bluetooth and transcription runs on the host; nothing is uploaded to the cloud |
| Who said what | Every segment has a timestamp and a speaker label; Chinese, English and Japanese are recognized |
| Fast | On a Jetson Orin NX, a 26 s two-speaker Chinese recording was transcribed in 1.2 s with 2 speakers separated; on an RK3576 (8 GB), a 30 s two-speaker Chinese recording took 4.6 s with 2 speakers separated |
| Connects to your system | A MQTT message announces each finished transcript; your program fetches the full text over HTTP |

## Use cases

| Scenario | How it works |
|----------|--------------|
| Store / counter service | Staff wear the Clip; recordings sync once they are back near the host and the manager reviews the day's conversations on the results page |
| Interviews and meetings | Put the Clip next to the host after the interview; once it has synced, the transcript is split by speaker |
| Privacy-sensitive settings | Clinics, legal work and internal meetings where recordings may not leave the premises |
| Business system integration | Your system pulls each finished transcript automatically into a ticket or customer record |

## Usage Notes

### Core hardware

| Device | Description | Required |
|--------|-------------|----------|
| reSpeaker Clip | Wearable recorder | ✓ Required |
| reComputer J40 (Jetson Orin NX, JetPack 6.2) or reComputer RK3576 (8 GB) | Syncs recordings, transcribes them and serves the results page | ✓ Required, one of the two |
| Jetson wireless module (Wi-Fi + Bluetooth) | The host reaches the Clip over Bluetooth; choose it together with the reComputer J40. An RK3576 host needs Bluetooth as well | ✓ Required for J40 |

- Jetson: only the Jetson Orin NX module with JetPack 6.2 is supported; other Jetson modules and JetPack versions cannot be deployed.
- RK3576: choose the 8 GB version; transcription needs about 1.6 GB of free memory, so other services on the board must leave that much free.
- Free disk: at least 15 GB on Jetson, 5 GB on RK3576.
- A Clip can be bound to this host only, not to the phone app at the same time.

### Network requirements

- The first deploy needs internet access to download the speech models (about 1.8 GB on Jetson, about 460 MB on RK3576) and runtime; transcription works offline after that.
- The Clip syncs over Bluetooth by default and needs to be within Bluetooth range of the host.
- Optional: with faster Wi-Fi sync turned on, the host joins the Clip's own hotspot to download recordings. When the host is on Ethernet, its built-in Wi-Fi is used; when the host uses Wi-Fi for its network, add a USB Wi-Fi adapter.
- Optional: AI summaries need an AI chat service that accepts the OpenAI API format. With a cloud service, transcript text is sent to it (the recordings are not); with a service on your own network, all data stays on site.
