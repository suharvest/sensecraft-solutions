## What This Solution Does

This solution provides an out-of-the-box acoustic front-end (AFE) tuning workbench for engineering teams developing voice AI agents, interactive hardware, and conference terminals:
- **Zero-Driver Browser-Native Control**: Leverages WebUSB and WebAudio to establish direct communication with hardware from Chromium browsers, eliminating Python, device driver installations, and environment configuration;
- **Full Acoustic Pipeline Visualization**: Visualizes ambient noise floors (dBFS), real-time side-by-side DSP waveform comparisons, speaker echo cancellation (AEC) metrics, and sound Direction of Arrival (DOA) tracking;
- **On-Device Transcription Verification**: Integrates an on-device lightweight Whisper engine running entirely within WebAssembly to transcribe test speech locally without streaming audio to the cloud.

---

## Key Benefits & Technical Specifications

| Dimension | Specification & Highlights |
|---|---|
| **Protocol & Interface** | Native WebUSB control pipe (VID: `0x2886`) paired with WebAudio capture stream; zero proprietary software required |
| **Supported Hardware** | reSpeaker Lite (dual-mic linear array with hardware DSP), reSpeaker XVF3800 (4-mic circular far-field array) |
| **Waveform & Meters** | Side-by-side visualization comparing raw microphone audio against beamformed, noise-reduced output |
| **Echo Suppression Testing**| Simulates terminal speaker playback to measure Acoustic Echo Cancellation (AEC) and evaluate barge-in stability |
| **Sound Direction Tracking**| Dynamic 360-degree Direction of Arrival (DOA) polar radar display tracking speaker orientation in real time |
| **Local Verification** | WASM-accelerated on-device Whisper model performing client-side ASR evaluation with complete privacy |

---

## Suitable Scenarios

- **Pre-Deployment Site Surveys**: Measure background ambient noise and echo decay metrics on site before deploying production voice appliances;
- **Hardware Selection & Benchmarking**: Compare dual-mic (reSpeaker Lite) and 4-mic (reSpeaker XVF3800) arrays across near-field, far-field, and reverberant rooms;
- **Echo & Barge-In Optimization**: Diagnose self-awakening or voice cutting during playback, and calibrate speaker reference signal gain and delay matching;
- **Educational Acoustic Demonstrations**: Engineering labs and academic institutions demonstrating beamforming, spatial filtering, and DOA concepts.

---

## Measured Benchmarks & Usage Notes

- **Browser Requirements**: Chromium-based browsers supporting WebUSB are required (Google Chrome 89+ or Microsoft Edge 89+); Safari and Firefox do not support WebUSB device communication;
- **Security Context**: The page must run under a secure context (HTTPS or `http://localhost` / `http://127.0.0.1`) for microphone and USB device permissions to be granted;
- **Operating System Permissions**: On macOS, verify microphone access is permitted in System Settings -> Privacy & Security; on Linux, configure udev rules with `MODE="0666"` for non-root USB access;
- **Local Model Caching**: The initial click on "Record & Transcribe" downloads a ~40MB WebAssembly model into browser IndexedDB; subsequent sessions load immediately from local cache.
