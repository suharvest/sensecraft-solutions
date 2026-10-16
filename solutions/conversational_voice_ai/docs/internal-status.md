# Internal status — Interruptible Conversational Voice AI

Internal record. Not published on the deployment page. Removed from
`description.md` / `description_zh.md` on 2026-09-07 under the
`reference-design-landing` rule "results / KPI only carry measured numbers".

## Language x device coverage: what is measured, what is not

Only the cells marked **measured** below have end-to-end numbers. Every other
cell is deployable but unquantified — the components have on-device numbers,
the end-to-end combination does not.

| Device | Chinese | English | Other 28 languages |
|--------|---------|---------|--------------------|
| Orin Nano 8GB | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | pending measurement | pending measurement |
| Orin NX 16GB (cloud LLM) | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | pending measurement | pending measurement |
| Orin NX 16GB (fully local) | Qwen3-ASR int4 + Matcha, ASR CER 0 measured | pending measurement | pending measurement |
| RK3576 | **measured 2026-09-06, re-verified 2026-09-08** (CER 1.05% short / 9.62% long, TTS RTF 0.172, V2V stop_to_final p50 1589ms) | **measured 2026-09-06** (WER 16.95% short / 63.38% long; offline-CER 1.11% short / 4.16% long, TTS RTF 0.194) | not supported |
| RK3588 | not measured | pending measurement | pending measurement |
| Raspberry Pi 5 | not supported | pending measurement | not supported |

Corrected 2026-09-08: this table previously read "Chinese: not measured" for
RK3576 while carrying the Chinese offline-ASR numbers (1.05%/9.62%) mislabeled
under the English column — both cells were actually measured on 2026-09-06
(`boundary.zh.yaml` / `boundary.en.yaml`), the English offline-ASR CER is
1.11%/4.16%, not 1.05%/9.62%. See `model-matrix/rk3576/boundary.zh.yaml`
("re-verified 2026-09-08" metrics) for the Chinese re-verification (same
corpus/methodology as 2026-09-06, run to confirm the numbers are still
current on this device) plus the new TTS RTF and V2V turn-latency numbers.

Measured accuracy sources:

- Qwen3-ASR 0.6B int4 on Orin NX: CER 0 on the golden set, streaming and
  offline, 2026-07-04.
- RK3576: `docs/perf/rk3576-matrix-20260906.md` (zh+en, 2026-09-06);
  `model-matrix/rk3576/boundary.zh.yaml` (zh re-verification, 2026-09-08).

## RK3576 streaming-vs-offline discrepancy (open follow-up)

The 1.05% / 9.62% figures come from the offline whole-clip `POST /asr`
endpoint — no VAD, no streaming.

The live conversational session behaves differently. Its low-latency turn
detection (silero VAD, 400 ms silence + 2.5 s minimum audio) finalizes on the
first natural pause, so a long sentence with a mid-utterance pause is answered
after its first clause. Against the full reference text that scores CER 84.06%
zh / WER 63.38% en. This is the streaming endpoint's turn-taking design, not a
recognition error.

Confirmed by re-test: relaxing the decoder's token budget and punctuation stop
(`ASR_MAX_NEW_TOKENS=256`, `ASR_FINAL_STOP_ON_PUNCT=0`) produced byte-identical
transcripts. The VAD endpoint, not the decoder, ends the turn early.

Open work: tune the VAD endpoint to tolerate a mid-utterance pause in
conversation. Not done.

## RK3576 reSpeaker host fix (2026-09-22, mitigation — not a root-cause fix)

Two field problems on the reComputer RK3576 devkit with the reSpeaker XVF3800
4-Mic Array (USB `2886:001a`, ALSA card id `Array`), diagnosed and the fix
verified on-device 2026-09-22. Shipped via
`assets/rk3576/respeaker/respeaker-host-fix.sh`, installed by the
`cloud_rk3576.yaml` pre-deploy actions.

### Speaker too quiet

`ovs-agent` opens `/dev/snd/pcmC?D0{p,c}` directly and holds them exclusively,
so PipeWire never creates a sink for the card and the desktop volume slider has
no effect on the assistant's audio. The real knob is the UAC feature unit
(`amixer -D hw:Array`, `'PCM',0` stereo and `'PCM',1` mono, range 0-60).
Measured: raw 37 = 62% = **-23.00 dB** (the bad shipped default state), raw 51
= 85% = -9.00 dB, raw 60 = 100% = 0.00 dB. The fix pins **85%** and re-applies
it on every USB sound-card add event (udev rule) plus after recovery.

### Mic array sometimes not on the bus after boot

Root cause chain: a long capture stream makes the vendor xHCI
(`6.1.115-vendor-seeed-rk3576`) emit a storm of
`WARN: buffer overrun event for slot N ep 2` (ep index 2 = EP 0x81 IN =
capture; 2729 lines observed within ~5 ms), the device drops ~250 ms later,
and the onboard Genesys hub chain (`1-1` -> `1-1.4`, self-powered, always-on
5 V) latches a bad downstream-port state: every later enumeration fails with
`Cannot enable. Maybe the USB cable is bad?` / `error -71` /
`unable to enumerate`.

Tested recovery matrix: warm reboot **fails**, xHCI controller rebind
**fails**, pulsing the DT `usb_hub_reset` line **works**. Because the hubs are
self-powered and the DT line is only a `gpio-hog` driven high once at boot, the
latch survives reboots — "sometimes not online after boot" is really "still
wedged from last time".

The upstream isoc fix (`906dec15b9b3`) is not in `6.1.115-vendor-seeed-rk3576`,
and RK3576's naneng-combphy has known `Cannot enable` issues, so this is a
mitigation + self-heal, not a root-cause fix.

What ships: `hub-reset.py` (auto-detects the gpio controller base and line — on
the devkit base `0x27320000`, line 19, never hardcoded; refuses to poke unless
the line is an output driven high; masked write `0xFFFF0000|value` works under
both Rockchip register semantics), `respeaker-recover.service` (boot self-heal,
up to 3 hub-reset tries) and `respeaker-watch.timer` (60 s watchdog, 2
consecutive misses, 600 s cooldown). Detection reads the kernel's resolved
`/sys/kernel/debug/gpio` first and only falls back to the device tree, because a
`gpio-hog`'s `gpios` property is controller-local `<line flags>` pairs with no
phandle — taking the second cell (the flags) instead of the first silently
points the recovery at the wrong line, where the out/high guard then refuses to
poke and the whole self-heal goes quiet. Recovery and the watchdog timer are also
started during installation, not only enabled, so a first deploy onto an already
wedged device repairs itself before the containers start. Boards without the
`usb_hub_reset` line get the volume fix only. Runtime PM
is disabled for `2886:001a` and the `05e3:0610` hub chain (observed
`usb 1-1: Failed to suspend device, error -71`).

## XVF3800 4-Mic 44mm: 48 kHz capture only (2026-10-14)

A different reSpeaker product from the array in the section above. `lsusb` is
`2886:0024 reSpeaker XVF3800 4-Mic 44mm` (the array is `2886:001a`), the ALSA
card id is `r44mm` rather than `Array`, and `/proc/asound/card3/stream0` lists
capture `Rates: 48000` only.

**Symptom.** Containers `Up (healthy)`, `/health` reports `asr: true`,
`tts: true`, `runtime_profile.verified: true`, and nothing is ever recognised.
The agent log carries 167 `Error opening RawInputStream: Invalid sample rate
[PaErrorCode -9997]` lines and never leaves the mic retry loop, then resolves
the onboard `rockchip-es8311` codec. `mic chunk loud` appears only ~110 ms after
each `input stream open` — one chunk, the stream-open transient, not speech. The
client VAD therefore never fires, the server receives no frames, and `/v2v` hits
its 90 s idle timeout on a loop.

**Root cause.** The agent asks PortAudio for `audio_input_sample_rate: 16000`.
PortAudio's ALSA backend does not insert the `plug` layer, so a device whose only
capture rate is 48000 is rejected rather than resampled.

Measured inside the agent container:

```
device=3 'reSpeaker XVF3800 4-Mic 44mm: USB Audio (hw:3,0)' in_ch=2 default_sr=48000.0
  sr=16000 -> FAIL PortAudioError: Invalid sample rate [PaErrorCode -9997]
  sr=48000 -> OPEN OK
```

`arecord -D hw:N,0 -r 16000` does **not** fail here: it prints `rate is not
accurate (requested = 16000Hz, got = 48000Hz)` and records anyway. Only
PortAudio refuses, so arecord cannot be used to decide whether a rate is
supported.

**Fix.** openvoicestream `fb82854` (`fix(audio)`): try the configured rate
first, and on rejection retry once at the rate the device declares, resample
back to `input_sr` inside the capture callback, and scale the callback
blocksize with the device rate so the 100 ms / 1600-frame downstream framing is
unchanged. Devices that accept 16 kHz are unaffected — the fallback only runs
after a rejected open.

Verified on the reComputer RK3576 devkit end to end (client VAD →
Qwen3-ASR → dialogue turn, `voxedge tool loop: ttft=0.705s`), and the
non-48k path unchanged: `input stream open: device=rockchip-es8388
sr=16000 chunk=1600` on cat-remote, no resample, no fallback.

**Interaction with the section above.** That one assumes the agent wins
`/dev/snd` and holds it exclusively. The reverse also occurs: a GNOME Settings
window holding a level meter keeps the XVF3800 capture stream open through
WirePlumber, the agent then gets `PaErrorCode -9985` and falls back to the
onboard codec. `wpctl status` → `Streams:` names the holder; closing it releases
the device. Do not fix that with a `node.disabled` rule — WirePlumber only holds
the device while a client asks for a stream.

## Upgrading a device that carries a stale copy of these assets (2026-10-14)

**Symptom.** Changing `SPEECH_IMAGE` / `AGENT_IMAGE` on an already-deployed
device and running `docker compose up -d` makes the speech container
crash-loop (`Exited (3)`) and the agent never connects to 8621, so the
assistant goes silent. The log names both gates:

```
[ERROR] RK profile contract INVALID: RK profile 'rk3576-default' does not
        satisfy rk-qwen3-true-streaming-matcha-v1:
        mismatches=ASR_FINAL_STOP_ON_PUNCT,VAD_ENDPOINT_SILENCE_MS
[ERROR] RK artifact runtime contract mismatch for selected artifact set.
        Details: ASR_FINAL_STOP_ON_PUNCT: got '1', expected '0'
```

**Root cause.** The device's `docker-compose.rk3576.yml` is an old copy of
`assets/docker/docker-compose.rk3576.yml`, predating `0dbcfd5`. It pins
`ASR_FINAL_STOP_ON_PUNCT: "1"` and `VAD_ENDPOINT_SILENCE_MS: "400"` — values
that matched `configs/profiles/rk3576-default.json` when the file was written
and stopped matching after `a3b0132` and `ca3cf95` (both measured fixes:
`a3b0132` — 400 ms endpointing cut a 6.33 s clip carrying a 1.5 s mid-sentence
pause down to its first 2.00 s; `ca3cf95` — with the final-decode punctuation
stop on, two English sentences scored 57.1% / 60.0% WER against 0.0% / 0.0%
with it off, same corpus and method on cat-remote, the stop toggled inside one
process). Two
independent gates reject them, the second being the artifact set's own
`runtime_contract` — i.e. the shipped models were validated with `0`.

The current template has already removed these keys; its compose comment records
the same `got '1', expected '0'` failure on cat-remote on 2026-09-08.

**Verified on cat-remote, 2026-10-14.** Same image, same config: with the two
keys → `Exited (3)`; with them removed → `Application startup complete` and
`/health` 200. So the same image starts or dies purely on whether the compose
still pins those two values.

**What to do.** Patching the image tag alone on a device with a stale asset copy
produces this crash. Refresh the copy first —
`sensecraft-engine content update`, or a reconfigure from the solution — then
redeploy. Editing the two values in place (`"0"` / `"1500"`) is not a fix: it
re-pins what the profile owns and the next profile revision reinstates the same
class of failure. Remove the keys and let the resolved profile supply them.

**Open.** The devkit used for this diagnosis was hand-patched (both keys
commented out, image tags in `voice-assistant.env`) rather than refreshed from
the solution, so its assets are still the August copy. It should be brought back
onto the shipped path with a content update plus redeploy.
