# reSpeaker Audio Lab

This directory contains a browser experiment for real reSpeaker USB audio, XVF3800 control parameters, DOA polling, and local Whisper Tiny transcription. It is a local experiment page; it is not a release package and does not include a `solution.yaml`.

## Run locally

From the repository root, start a static HTTP server:

```bash
python3 -m http.server 8080 --directory solutions/respeaker_audio_lab/assets/web
```

Open <http://localhost:8080/> in a WebUSB-capable browser. `localhost` is a secure context for browser permissions. A deployed HTTPS origin can be used instead; opening `index.html` directly with `file://` is unsupported.

The page requests two separate permissions. Use **Connect USB control** for the device-recipient control channel, then **Authorize microphone** and select the same reSpeaker in the audio input list. The browser and operating system may show separate USB and microphone prompts. The page does not claim an audio interface, detach a kernel driver, or guess an interface number.

## Device boundaries

- XVF3800, Flex, and the legacy XVF3000 (`2886:0018`) are identified by USB VID/PID and then capability-probed. Parameters are enabled only after a successful read. Firmware variants can expose different channel routing and controls; the page does not infer a channel map from the model name. On macOS, an XVF3000 with firmware value `16` was physically checked on 2026-09-10: USB reads returned firmware `16`, DOA, and the legacy controls; an independent libusb readback confirmed `MIN_NS` after a browser change from `.15` to `.16` was restored to `.15`.
- The same XVF3000 appeared to the browser as a system 6-channel, 16 kHz device, while `getUserMedia` exposed at most two channels in this check. The browser capture ran at 48 kHz in `AudioContext`, and both exposed channels produced real levels. This does not verify six-channel browser capture or the original/processed channel map.
- reSpeaker Lite is treated as USB audio only. Its documented I2C configuration path is outside this page. Switching Lite between USB and I2S firmware requires the device firmware workflow and is not performed here.
- Unknown products and firmware fail closed until a valid firmware probe supports a capability. USB audio may still be usable when USB control is unavailable.
- DOA is a device report, not a distance estimate. Physical microphone placement, channel mapping, firmware version, and output routing still require on-device checks.
- Hardware validation remains incomplete. XVF3000 USB control and the two browser-exposed audio channels were checked on one macOS setup; Flex, XVF3800, Lite, other firmware variants, six-channel browser capture, and channel mapping still require physical verification.

The UI keeps the live signal as the primary view. Noise controls sit below the spectrum, gain and high-pass controls sit with the channel monitor, AEC controls sit in the AEC section, and the complete parameter list is available from a secondary dialog.

## Local transcription

The first **transcription** downloads and caches the quantized `onnx-community/whisper-tiny` model from [ModelScope](https://modelscope.cn/models/onnx-community/whisper-tiny) and the Transformers.js/WASM runtime from their configured package/model sources. The quantized model is approximately 41 MB, plus runtime and tokenizer assets; actual download size depends on the browser cache and asset revisions. The first transcription therefore needs an Internet connection; later use depends on the browser cache. Audio processing remains in the browser; the page does not upload recordings.

For AEC, route reference playback through reSpeaker to a speaker and verify that the firmware feeds this playback to its echo-reference path. Headphones are suitable for ordinary recording playback. A transcription difference is not an audio-quality score.

## Verification and release work

Run `node --test solutions/respeaker_audio_lab/assets/web/tests/*.test.mjs`. These are software tests with deterministic fixtures, not physical-device certification.

The browser page was checked at desktop and mobile widths. All files under `assets/web/` must be deployed together as one HTTPS static site and shared as its site URL; `localhost` is for development and `file://` cannot be used directly. Each person must grant USB and microphone permissions in their own browser. Tiny inference can be retried if model or runtime downloads fail.

Pending: physical tests for each USB firmware and OS/browser combination; validated channel maps; then a SenseCraft solution manifest and end-to-end verification. No firmware is flashed or content published by this prototype.

Protocol references: [Flex host control](https://github.com/respeaker/reSpeaker_Flex/blob/main/python_control/xvf_host.py), [Lite firmware](https://github.com/respeaker/ReSpeaker_Lite), [Tiny model on ModelScope](https://modelscope.cn/models/onnx-community/whisper-tiny).
