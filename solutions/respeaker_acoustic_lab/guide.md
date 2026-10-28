# reSpeaker Acoustic Front-End & Array Tuning Guide

This solution provides a driverless acoustic tuning environment for the reSpeaker USB microphone array family (reSpeaker Lite, reSpeaker XVF3800) directly inside Chromium-based browsers (Chrome, Edge).

---

## Preset: Acoustic Tuning Workbench {#acoustic_tuning_workbench}

## Step 1: Launch Acoustic Workbench {#audio_lab type=web_dashboard required=true config=devices/online_audio_lab.yaml}

Connect directly to hardware via WebUSB and WebAudio interfaces without installing native Python drivers or configuring host compilation tools.

### Prerequisites & Wiring

1. Connect your reSpeaker microphone array (reSpeaker Lite or reSpeaker XVF3800) to your computer using a USB Type-C data cable.
2. Open the workbench using Google Chrome or Microsoft Edge (Chromium browsers with WebUSB support).
3. On macOS, ensure browser microphone permissions are enabled in System Settings; on Linux, configure appropriate udev rules if permissions fail.

### Step-by-Step Tuning Workflow

1. **Connect USB Controller**: Click "Connect Device" at the top right, pick your reSpeaker device from the browser popup dialog, and pair.
2. **Authorize Microphone Stream**: Click "Start Capture" and allow microphone permissions to begin streaming real-time audio waveforms and dBFS meters.
3. **Analyze Acoustic Front-End (AFE)**:
   - **Noise Reduction**: Compare raw mic input against hardware DSP filtered beamforming output side by side;
   - **Echo Cancellation (AEC)**: Test barge-in performance and residual speaker feedback suppression;
   - **Direction of Arrival (DOA)**: Observe 360-degree sound source tracking and multi-channel microphone mappings;
   - **Record & Transcribe**: Record short audio clips and run on-device Whisper WASM transcription to verify recognition clarity.

### Target {#audio_lab_target type=local device_name="Local Browser" config=devices/online_audio_lab.yaml}

### Troubleshooting

| Symptom | Action |
|---|---|
| Device not shown in connection popup | Verify USB cable supports data transfer; try another USB port |
| No waveform or audio signal | Check browser address bar permissions to ensure microphone access is allowed |
| Transcription does not start | Initial run downloads a lightweight WASM model (~40MB); ensure network connectivity |
