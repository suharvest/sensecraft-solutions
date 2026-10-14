## What the Solution Does

Turn reSpeaker Clip recordings into speaker-labelled transcripts on your own host, with no audio sent to the cloud.

Staff or interviewers wear the reSpeaker Clip to record. When returning within range of the compute host, audio files synchronize automatically over Bluetooth (BLE) or Wi-Fi. The edge host performs Voice Activity Detection (VAD), speaker diarization, and automatic speech recognition (ASR) locally, producing transcripts with precise timestamps and speaker tags accessible via a local web interface and MQTT/HTTP APIs.

- **Automatic Audio Synchronization**: Wear the Clip and return near the host; audio transfers automatically over BLE without plugging in cables or SD cards.
- **Local Diarization and ASR**: Splits recordings by speaker and transcribes each turn on the edge host.
- **Interactive Transcripts with Timestamps**: View transcripts grouped by speaker turn, with click-to-play audio alignment from any timestamp.

## Core Value

- **Audio Never Leaves the Premises**: Raw recordings are processed and retained on site; sensitive interviews, consultations, and meetings avoid public cloud risks.
- **Dual-Platform Hardware Acceleration**: Supported on reComputer J40 Series (Jetson Orin NX, GPU TensorRT acceleration) and reComputer RK3576 Series (NPU RKNN acceleration).
- **Out-of-the-Box Management Web UI**: Review transcripts by date and device, play back audio aligned to turns, and export text files.
- **Optional AI Summarization**: Connect an OpenAI-compatible endpoint (local LLM or private API) to extract key discussion points and action items.

## Suitable Scenarios

Places where audio recordings need to become structured text without leaving the site:

- **Retail Counters and Service Desks**: Staff wear the Clip during interactions; audio syncs automatically when returning to base, letting managers review conversation notes.
- **Interviews and Internal Meetings**: Place the Clip beside the host after an interview; get a speaker-separated transcript once sync completes.
- **Consulting Rooms, Legal, and Clinic Meetings**: For compliance and privacy requirements where audio data must remain strictly on site.

## Measured Performance

Timed from WAV file upload to finished transcript on hardware:

| Metric | Typical | Device |
|---|---|---|
| 26 s two-speaker Chinese recording | done in **1.2 s**, 2 speakers separated | reComputer J40 Series (Orin NX 16GB) |
| 34 s Japanese recording | done in **1.7 s** | reComputer J40 Series (Orin NX 16GB) |
| 30 s two-speaker Chinese recording | done in **4.6 s**, 2 speakers separated | reComputer RK3576 Series (8 GB) |

## Usage Notes

- **Single Host Pairing**: Each Clip pairs with one dedicated host and cannot connect simultaneously to mobile phone apps.
- **AI Summary Configuration**: When AI summaries use a cloud endpoint, only the transcribed text is transmitted—audio files never leave the host. A local LLM can be configured for complete air-gapped operation.
- **Hardware Platform Requirements**: The precompiled TensorRT voice image targets Jetson Orin NX (JetPack 6.2, TensorRT 10.3); the RK3576 uses corresponding RKNN runtime models.

> 📖 **Engineering Reference:** Full architecture internals, measured benchmarks, and failure modes are documented in the [Engineering Wiki · Private Transcription for reSpeaker Clip](https://wiki.seeedstudio.com/solutions/clip-private-transcription/).
