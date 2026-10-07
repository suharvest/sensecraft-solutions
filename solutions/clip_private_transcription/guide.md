# Deployment Guide

> **Draft / disabled.** The compose files are reviewable contracts only; they
> fail closed until approved local images and physical evidence exist.

## Preset: RK3576 + Clip BLE (Draft) {#rk3576_ble}

## Step 1: Deploy local transcription stack {#rk3576_deploy type=docker_deploy required=true config=devices/rk3576_stack.yaml}

Provide approved local clip-pt, SLV, and Mosquitto image references, the
preloaded SenseVoice and Whisper model roots, and a config based on the reviewed
`assets/config/config.example.yaml`. Pair the Clip manually and
use one host binding only.

The compose stack starts clip-pt, separate SenseVoice and Whisper SLV services,
and Mosquitto. The LLM is a user-supplied OpenAI-compatible endpoint configured in the shared
config (`base_url`, `model_name`, `api_key`, `timeout_s`); the base URL may be a
root URL or `/v1`. It can point to a cloud service, an RK1828 service, or a Jetson
service. No local LLM runtime is started by this package. The copied profiles select `rk.asr` on port 8621 and
`rk.whisper` on port 8622; downloads are disabled. Provide the two model roots
at the paths declared by those profiles. The endpoint contract reuses the voice RD fields `base_url`, `model_name`, and
`api_key`; the user supplies the endpoint, model, and key through the application
configuration. Do not put real keys in this package. Mosquitto uses the bundled
anonymous local broker configuration. The SLV image, profiles, and model roots
must match this RK3576 runtime. They are user-provided dependencies and have
not been validated on a physical RK3576 in this package.

Before upload, replace every `REPLACE_WITH_*` value with the actual Clip
advertised name, BLE MAC address, and local label. For Wi-Fi presets, set
`sync.wifi_iface` to the actual host interface. Generate an API key locally and
put the resulting 64 hexadecimal characters in `api.key`; the shipped example
keeps this field empty so startup fails closed until it is configured:

The shared example enables `pipeline.require_gpu_diarization` for the Jetson
preset. RK3576/RK3588 deployments must set it to `false`: this contract only
accepts the Jetson CUDA CAM++ metadata, and no matching RKNN speaker backend is
claimed here. With `false`, the existing legacy CPU/empty-result behavior is
retained.

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Target {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml}

Run Docker on this RK3576 host.

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml default=true}

Connect to this RK3576 host over SSH.

## Step 2: Verify API {#rk3576_verify type=http_debug required=true config=devices/verify_clip.yaml}

Require `/healthz` HTTP 200, then run a controlled sync and inspect the
transcript schema. This does not prove physical acceptance.

## Preset: RK3588 + Clip Wi-Fi (Draft) {#rk3588_wifi}

## Step 1: Deploy local transcription stack {#rk3588_deploy type=docker_deploy required=true config=devices/rk3588_stack.yaml}

Provide the approved local clip-pt, SLV, and Mosquitto image
references, the preloaded SenseVoice and Whisper model roots, and a config based on the reviewed example. Wi-Fi sync requires a dedicated adapter and a host configuration with the
actual interface name. The Clip name and BLE MAC in `devices[]` must match the
physical unit; do not leave the example placeholders.

The compose stack starts clip-pt, separate SenseVoice and Whisper SLV services,
and Mosquitto. The LLM is a user-supplied OpenAI-compatible endpoint configured in the shared
config (`base_url`, `model_name`, `api_key`, `timeout_s`); the base URL may be a
root URL or `/v1`. It can point to a cloud service, an RK1828 service, or a Jetson
service. No local LLM runtime is started by this package. The copied profiles select `rk.asr` on port 8621 and
`rk.whisper` on port 8622; downloads are disabled. Provide the two model roots
at the paths declared by those profiles. The endpoint uses the voice RD fields `base_url`, `model_name`, and `api_key`;
supply them through application configuration and keep keys out of this package.
A cloud endpoint requires network access; a reachable RK1828 or Jetson endpoint
can support an offline local chain. The SLV image,
profile, and model root must match this RK3588 runtime; this package has no
physical RK3588 deployment evidence for that combination.

Prepare the config from `assets/config/config.example.yaml`: replace the Clip
name, BLE MAC, local label, and `sync.wifi_iface` with the actual values, then
put a locally generated 64-hex API key in `api.key`:

Set `pipeline.require_gpu_diarization: false` for this RK3588 preset. The
strict response contract currently covers Jetson CUDA CAM++ only; no RKNN
speaker backend is claimed. The default legacy behavior remains available.

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Target {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_stack.yaml}

Run Docker on this RK3588 host.

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_stack.yaml default=true}

Connect to this RK3588 host over SSH.

## Step 2: Verify API {#rk3588_verify type=http_debug required=true config=devices/verify_clip.yaml}

Run the API, MQTT, resume, and offline checks only after the physical gate is
scheduled.

## Preset: Jetson + Clip Wi-Fi (Draft) {#jetson_wifi}

## Step 1: Deploy local transcription stack {#jetson_deploy type=docker_deploy required=true config=devices/jetson_stack.yaml}

The Jetson voice backend and CUDA runtime require approved artifacts; no
registry digest is implied here.

Provide the approved local `clip-pt` image, approved private OVS image, edited
Clip config, existing absolute ASR bundle directory on the selected Jetson (for
example `/opt/models/clip-asr`), and approved Mosquitto image. The LLM remains an
user-supplied endpoint using the voice RD fields `base_url`, `model_name`, and
`api_key`; these are application configuration values, not Jetson files. Do not
put real keys in this package. A Jetson endpoint such as port 8000 may be used
when it exists, but this package does not assume or verify one. Before
deployment, create this tree with the exact filenames consumed by the profiles:

```text
/opt/models/clip-asr/
├── sensevoice-trt/
│   ├── sense-voice-encoder.scaled.fixed.onnx
│   ├── am.mvn
│   ├── embedding.npy
│   ├── chn_jpn_yue_eng_ko_spectok.bpe.model
│   └── sensevoice.plan
├── whisper/
│   ├── encoder/jetson/enc_base_30s_bf16.plan
│   ├── mel_80_filters.txt
│   └── vocab_en.txt
├── plans/
│   ├── prefill_fp16.plan
│   └── step_fp16.plan
└── speaker/
    └── campplus.plan
```

The directory is mounted read-only at `/models`. The Whisper BF16 encoder plan
and TensorRT decoder plans must match the selected Jetson model and runtime; an
NX plan is device-specific and must not be treated as portable to another
Jetson. The shipped profiles are mounted explicitly; the SenseVoice and Whisper
services listen on host ports 8621 and 8622 and each uses one serialized GPU
execution context.

The example also requires the approved offline CAM++ plan at
`/models/speaker/campplus.plan`. `OVS_SPEAKER_EMB_BACKEND=jetson_trt` is a
strict selection: a missing, incompatible, or failed plan returns an error
instead of using the CPU speaker model. GPU provenance covers the CAM++ neural
forward; VAD, fbank, and clustering remain CPU work.

The compose contract keeps model downloads disabled. It starts two ASR-only
services from the same private OVS image and requires both checks: `/readyz`
must accept requests (backend readiness, session capacity, and GPU watchdog
state), then `/health` must report `{"asr": true}` with `asr_backend` equal to
`sensevoice_trt` or `whisper-tensorrt`. `/readyz` can be temporarily not ready
when session capacity is full; this healthcheck does not itself restart a
container.

Prepare the config from `assets/config/config.example.yaml`: replace the Clip
name, BLE MAC, local label, and `sync.wifi_iface` with the actual values, then
put a locally generated 64-hex API key in `api.key`:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_stack.yaml}

Run Docker on this Jetson host.

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_stack.yaml default=true}

Connect to this Jetson host over SSH.

## Step 2: Verify API {#jetson_verify type=http_debug required=true config=devices/verify_clip.yaml}

Check Clip `/healthz`, SenseVoice `/health` on 8621, Whisper `/health` on
8622, and the Mosquitto broker on 1883. Verify the configured shared LLM endpoint
with the application-level voice RD contract (`base_url`, `model_name`, `api_key`, `timeout_s`)
before running the documented M10 matrix with real Clip hardware. The package
does not provide or validate a cloud provider, model, or API key, and does not
physically validate the Mosquitto image or GPU speaker-embedding artifact. The example config leaves summary, MQTT, and
diarization enabled; do not interpret container healthchecks as full offline,
summary, MQTT, diarization, or physical Clip acceptance.
