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
