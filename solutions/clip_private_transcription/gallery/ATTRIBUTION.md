# Gallery attribution

## Gallery screenshots (replaced 2026-10-08)

`panel-transcript-list-zh-20261008.jpg` and `panel-transcript-detail-zh-20261008.jpg` are screenshots of the clip-pt read-only result view (`GET /` on port 8631), taken 2026-10-08 10:06 UTC with headless Chromium (Playwright, device scale 2, cropped to the panel, resized to 1600 px, JPEG q85). No API key is visible.

Run: Jetson Orin NX 16GB (reComputer J40 class), packaged `assets/docker/jetson.yml` with `patches/vad.py` (openvoicestream 79dbb6d7) mounted into both OVS services, OVS image config-identical to published `nrd6-ovs-jetson:20261008` (local tag `20261007-strict-gpu-diarization-r1`, same config digest 6d8ca79e), clip-pt `20261008-schemafix-r3`, tmpfs data, summary off (no LLM endpoint on the host). Transcripts come from HTTP uploads (`POST /v1/transcribe`), not from a Clip device. Uploads run with language `auto` (this clip-pt build has no per-upload language); the three inputs below transcribe completely in `auto`. Time to transcribe = upload accepted to job `done`.

| Entry | Input | Length | Time | Speakers |
|---|---|---|---|---|
| upload-89d56468 | `zh-two-speakers-fleurs-C.wav` | 22.3 s | 0.66 s | S1 / S2 |
| upload-04e6b3a6 | `zh-two-speakers-aishell-sensevoice.wav` (detail shot) | 16.5 s | 1.19 s | S1 / S2 / S1 |
| upload-3564da1a | `zh-two-speakers-fleurs-B.wav` | 26.1 s | 1.72 s | S1 / S2 |

Detail shot, reference vs output:

| Turn | Reference | Output |
|---|---|---|
| S1 0.54-5.59 s | 而对楼市成交抑制作用最大的限购 | 而对面楼市成交抑制作用最大的限购， (extra 面) |
| S2 7.23-11.67 s | 开放时间早上9点至下午5点。 | 开放时间早上9点至下午5点， |
| S1 13.15-15.89 s | 也成为地方政府的眼中钉 | 也成为地方政府的眼中钉， |

Audio sources:

- FLEURS (Conneau et al., 2022), https://huggingface.co/datasets/google/fleurs, cmn_hans_cn dev split, CC BY 4.0. B = 1601 (female) + 1614 (male), C = 1657 (female) + 1658 (male); 0.5 s silence + utterance + 0.8 s gap + utterance + 0.5 s silence.
- AISHELL-1 (Bu et al., 2017), https://www.openslr.org/33/, Apache 2.0: BAC009S0002W0122 and BAC009S0002W0123 (speaker A).
- SenseVoice zh example clip (speaker B in the A/B/A mix), as shipped in `test_wavs/zh.wav` of the sherpa-onnx SenseVoice package and `example/zh.mp3` of FunAudioLLM/SenseVoiceSmall (Hugging Face licence field: other, FunASR model licence).

The earlier `panel-transcript-list-20261008.jpg` (English/Japanese uploads, older UI) was removed on 2026-10-08. `panel-transcript-detail-ja` was removed on 2026-10-09: its speaker split was wrong (second FLEURS source labelled S1, S2 a noise tail).

`cover-20261008.jpg` is a generated illustration, not a screenshot. It reuses the listing-card image of the hub scenario page in-person-conversation-intelligence (https://files.seeedstudio.com/Solution/landpage_asset/voicecollectionanalysis/cover-41074c7f.jpg), resized to 1600 px wide.
