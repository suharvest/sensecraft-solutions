# Gallery attribution

## Gallery screenshots (replaced 2026-10-09)

`panel-transcript-list-zh-20261009.jpg` and `panel-transcript-detail-zh-20261009.jpg` are screenshots of the clip-pt result view (`GET /` on port 8631), taken 2026-10-08 10:41 UTC with headless Chromium (Playwright, device scale 2, cropped to the panel, resized to 1600 px, JPEG q85). No API key is visible.

Run: Jetson Orin NX 16GB (reComputer J40 class), packaged `assets/docker/jetson.yml` with published `nrd6-ovs-jetson:20261009` (sha256:b33427b3), clip-pt `clip-private-transcription:20261009` (suharvest/clip-private-transcription e73a8ba; the run used the local build that was pushed as that tag), tmpfs data, summary off (no LLM endpoint on the host). Transcripts come from HTTP uploads (`POST /v1/transcribe`), not from a Clip device. The config sets the Clip's recording language to `zh`, as the deploy form does when 录音语言 = 中文; uploads without a `language` field use it (`transcript.language` = `zh`). Time to transcribe = upload accepted to job `done`.

| Entry | Input | Length | Time | Speakers |
|---|---|---|---|---|
| upload-89d56468 | `zh-two-speakers-fleurs-C.wav` | 22.3 s | 0.66 s | S1 / S2 |
| upload-69ed71d7 | `zh-two-speakers-aishell.wav` (detail shot) | 16.0 s | 1.19 s | S1 / S2 / S1 |
| upload-3564da1a | `zh-two-speakers-fleurs-B.wav` | 26.1 s | 1.22 s | S1 / S2 |

Detail shot, reference vs output:

| Turn | Source | Reference | Output |
|---|---|---|---|
| S1 0.54-5.59 s | BAC009S0002W0122 | 而对楼市成交抑制作用最大的限购 | 而对面楼市成交抑制作用最大的限购， (extra 面) |
| S2 7.04-11.19 s | BAC009S0003W0134 | 任何一个企业的创新之路都绕不开它 | 任何一个企业的创新之路都绕不开它， |
| S1 12.70-15.44 s | BAC009S0002W0123 | 也成为地方政府的眼中钉 | 也成为地方政府的眼中钉， |

Audio sources:

- FLEURS (Conneau et al., 2022), https://huggingface.co/datasets/google/fleurs, cmn_hans_cn dev split, CC BY 4.0. B = 1601 (female) + 1614 (male), C = 1657 (female) + 1658 (male); 0.5 s silence + utterance + 0.8 s gap + utterance + 0.5 s silence.
- AISHELL-1 (Bu et al., 2017), https://www.openslr.org/33/ (files from the Hugging Face mirror AISHELL/AISHELL-1, `data_aishell/wav/S0002.tar.gz`, `S0003.tar.gz`, `data_aishell/transcript/aishell_transcript_v0.8.txt`), Apache 2.0. A/B/A mix: speaker S0002 utterance BAC009S0002W0122, speaker S0003 utterance BAC009S0003W0134, speaker S0002 utterance BAC009S0002W0123, joined with 0.5 s silence (16.0 s, sha256 69ed71d7).

The A/B/A detail recording used until 2026-10-09 (upload-04e6b3a6) had the SenseVoice zh example clip (`example/zh.mp3` of FunAudioLLM/SenseVoiceSmall, Hugging Face licence field: other) as its middle turn; it was replaced by the AISHELL-1 S0003 utterance above.

The earlier `panel-transcript-list-20261008.jpg` (English/Japanese uploads, older UI) was removed on 2026-10-08. `panel-transcript-detail-ja` was removed on 2026-10-09: its speaker split was wrong (second FLEURS source labelled S1, S2 a noise tail).

`cover-20261008.jpg` is a generated illustration, not a screenshot. It reuses the listing-card image of the hub scenario page in-person-conversation-intelligence (https://files.seeedstudio.com/Solution/landpage_asset/voicecollectionanalysis/cover-41074c7f.jpg), resized to 1600 px wide.
