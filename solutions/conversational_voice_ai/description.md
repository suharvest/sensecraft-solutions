## What This Solution Does

Turn an edge device into a voice terminal that can listen, think, and speak continuously. Connect a hardware-AEC microphone array and a speaker; the device captures speech, produces a reply, and immediately stops that reply when the user starts speaking again.

This is a persistent device application, not a push-to-talk browser demo. The on-device agent owns the microphone and speaker, making it suitable for robots, kiosks, service desks, smart-home terminals, and unattended exhibits.

## Core Value

| Benefit | What it means |
|---------|---------------|
| Natural interruption | Capture stays active during playback; new speech cancels generation, drains queued audio, and starts the next turn |
| Optional open-vocabulary wake word | Require any short Chinese or English phrase before a turn; a short confirmation tone signals successful detection |
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

### Optional Wake Word

Select **Wake word required** during deployment to enable the bundled
open-vocabulary sherpa-onnx detector. Enter any short Chinese or English phrase;
the agent compiles it locally and plays a short 880 Hz tone after detection.
**Always listening** remains the default for backward-compatible hands-free use.

### Network

- First deployment downloads images and model artifacts and needs stable internet plus sufficient disk space.
- The cloud preset needs ongoing API access. Fully local presets can run offline after artifacts are cached.
- Qwen defaults use the Beijing OpenAI-compatible endpoint. Replace the base URL and model ID for another region or provider.

## Language and Device Support Matrix

The conversation language is chosen at deploy time. The deployment turns
(language, device) into exactly one speech profile before any service starts,
and refuses a pair the board cannot serve rather than substituting a model that
cannot read the language.

Language options are the RK runtime's 30-language set - the narrower of the two
available lists, since Qwen3-ASR upstream advertises 52 languages and Whisper
99. Languages are handled in three groups: Chinese, English, and the remaining
28.

| Device | Chinese | English | Other 28 languages |
|--------|---------|---------|--------------------|
| Orin Nano 8GB | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | Qwen3-ASR int4 + Matcha, pending measurement | Qwen3-ASR + Qwen3-TTS, pending measurement |
| Orin NX 16GB (cloud LLM) | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | Qwen3-ASR int4 + Matcha, pending measurement | Qwen3-ASR + Qwen3-TTS, pending measurement |
| Orin NX 16GB (fully local) | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | Qwen3-ASR int4 + Matcha, pending measurement | Qwen3-ASR + Qwen3-TTS CustomVoice, pending measurement |
| RK3576 | Qwen3-ASR W8A8 + Matcha | Qwen3-ASR W8A8 + Matcha, model capability measured 2026-09-06 via offline whole-file `/asr` (no VAD endpoint): CER 1.05% short / 9.62% long. TTS RTF 0.194. (see docs/perf/rk3576-matrix-20260906.md) | Not supported - TTS on this board is Matcha zh-en only |

The 1.05%/9.62% figures above measure what the decoder can transcribe when
given a whole clip through the offline `POST /asr` endpoint (no VAD, no
streaming). The **live conversational session** behaves differently: its
low-latency turn detection (silero VAD, 400ms silence + 2.5s minimum audio)
finalizes on the first natural pause in what it hears, so a long sentence
with a mid-utterance pause gets replied to after its first clause (measured
CER 84.06% zh / WER 63.38% en against the full reference text) — **that is
the streaming endpoint's turn-taking design, not a recognition error**;
re-testing with the decoder's own token budget and punctuation-stop setting
relaxed (`ASR_MAX_NEW_TOKENS=256`, `ASR_FINAL_STOP_ON_PUNCT=0`) produced
byte-identical transcripts, confirming the VAD endpoint — not the decoder — is
what ends the turn early. Tuning the VAD endpoint to tolerate a mid-utterance
pause in conversation is open follow-up work, not done here.
| RK3588 | Qwen3-ASR W8A8 + Matcha | Qwen3-ASR W8A8 + Matcha, pending measurement | Qwen3-ASR + Kokoro RKNN, pending measurement |
| Raspberry Pi 5 | Not supported | sherpa-onnx CPU, pending measurement | Not supported |

"Pending measurement" means the components have on-device numbers but the
end-to-end combination does not. The one measured accuracy figure in this table
is Qwen3-ASR 0.6B int4 on Orin NX: CER 0 on the golden set, streaming and
offline, 2026-07-04. Every other cell is deployable but unquantified; do not
plan around a latency or accuracy number that is not written here.

**Chinese is never served by Whisper.** Whisper's Chinese ceiling is 35-56% CER
on every board measured, so Raspberry Pi 5 - which has no Qwen3-ASR backend -
refuses Chinese instead of transcribing it badly.

## Deployment Comparison

| Preset | Conversation model | Supported devices | Best for |
|--------|--------------------|-------------------|----------|
| Cloud or compatible endpoint | Qwen API or any OpenAI-compatible model | RK3576 / RK3588 / Orin Nano / Orin NX / Raspberry Pi 5 | Fastest path to full conversation |
| Fully local conversation | RK1828 Qwen3-4B or Orin NX Qwen3.5-4B | RK3588 + RK1828 / Orin NX 16GB | Privacy, offline use, and fixed operating cost |

### Technical Stack

- Speech recognition: Qwen3-ASR
- Voice synthesis: Matcha-TTS
- Duplex control: one persistent session, continuous capture, playback cancellation, and conversation truncation
- Conversation API: OpenAI-compatible Chat Completions
