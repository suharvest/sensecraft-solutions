# Deployment Guide

> **Draft.** The compose files are reviewable contracts; inputs without a
> published default fail closed.

## Preset: Clip + Edge Compute Box (Draft) {#clip_edge_box}

Pick the host in the deploy step: Jetson, RK3588 or RK3576. Clip sync always
runs over BLE; Wi-Fi sync is optional and needs a dedicated host adapter. Each
target states its on-device acceptance status.

## Step 1: Deploy local transcription stack {#deploy_stack type=docker_deploy required=true config=devices/jetson_stack.yaml}

The clip-pt image defaults to the published 2026-10-08 image; on Jetson the
OVS image and ASR model bundle are published too. Provide the SLV image and
preloaded ASR model roots on RK hosts, a Mosquitto image reference, and a config based on the
reviewed `assets/config/config.example.yaml`. Pair the Clip manually and use
one host binding only.

The compose stack starts clip-pt, separate SenseVoice and Whisper SLV services,
and Mosquitto. The LLM is a user-supplied OpenAI-compatible endpoint configured in the shared
config (`base_url`, `model_name`, `api_key`, `timeout_s`); the base URL may be a
root URL or `/v1`. It can point to a cloud service, an RK1828 service, or a Jetson
service. No local LLM runtime is started by this package. The endpoint contract reuses the voice RD fields `base_url`, `model_name`, and
`api_key`; the user supplies the endpoint, model, and key through the application
configuration. Do not put real keys in this package. A cloud endpoint requires
network access; a reachable RK1828 or Jetson endpoint can support an offline
local chain. Mosquitto uses the bundled anonymous local broker configuration.

Before upload, replace every `REPLACE_WITH_*` value with the actual Clip
advertised name, BLE MAC address, and local label; do not leave the example
placeholders. For Wi-Fi sync, set `sync.wifi_iface` to the actual name of the
dedicated adapter; without one, set `sync.wifi_enabled: false` and the Clip
syncs over BLE only. Generate an API key locally and put the resulting 64
hexadecimal characters in `api.key`; the shipped example keeps this field
empty so startup fails closed until it is configured:

```bash
python3 -c 'import secrets; print(secrets.token_hex(32))'
```

**RK3576 / RK3588.** The copied profiles select `rk.asr` on port 8621 and
`rk.whisper` on port 8622; downloads are disabled. Provide the two model roots
at the paths declared by those profiles (RK3576 uses the base10 Whisper RKNN
assets, RK3588 base20). The SLV image, profiles, and model roots must match the
selected RK runtime. The shared example enables
`pipeline.require_gpu_diarization` for Jetson; RK3576/RK3588 deployments must
set it to `false`: this contract only accepts the Jetson CUDA CAM++ metadata,
and no matching RKNN speaker backend is claimed here. With `false`, the
existing legacy CPU/empty-result behavior is retained.

**Jetson.** The Jetson voice backend uses the published
`nrd6-ovs-jetson:20261008` image (pinned by digest); the CUDA runtime stays host-owned.

The two SLV services require the Jetson runtime ABI: JetPack 6.2 with
TensorRT 10.3.0 and Python 3.10. The deployment checks the host TensorRT
binding and libraries before Compose starts, then mounts the binding,
`/usr/src/tensorrt`, `/usr/local/cuda/lib64`, NVIDIA libraries, and the ARM64
system libraries read-only. The image loader path is fixed to those mounts;
missing paths or a different TensorRT version fail closed. This requirement is
separate from the device-specific model plans below and does not provide a CPU
fallback.

Provide the edited Clip config and an approved Mosquitto image. The `clip-pt`
and OVS images default to the published 2026-10-08 images (pinned by digest),
and the deployment downloads the `clip-orin-nx-r1` ASR bundle (SHA-256
checked) into `/opt/clip-private-transcription/models` on the Jetson; its plans
were built for Orin NX. A Jetson LLM
endpoint such as port 8000 may be used when it exists, but this package does
not assume or verify one. The bundle unpacks to this tree with the exact
filenames consumed by the profiles:

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

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_stack.yaml default=true}

The prebuilt TensorRT plans are for Jetson Orin NX (P3767-0000 / P3767-0001) on L4T R36.4 (JetPack 6.2) with TensorRT 10.3; the deploy step stops on any other module or JetPack version.

Connect to this Jetson host over SSH. On Orin NX (2026-10-08) the clip-pt build
now published as `clip-private-transcription:20261008` passed the HTTP-upload
path (upload, GPU diarization, SenseVoice/Whisper TensorRT ASR, LLM summary,
transcript over HTTP and MQTT) with a test compose on other ports. This
target's compose file (ASR services with a writable resolver directory, models
read-only) was not run on a device on 2026-10-08 — the Orin NX had no free
disk. Clip BLE/Wi-Fi sync needs a physical Clip; none was available.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_stack.yaml}

The prebuilt TensorRT plans are for Jetson Orin NX (P3767-0000 / P3767-0001) on L4T R36.4 (JetPack 6.2) with TensorRT 10.3; the deploy step stops on any other module or JetPack version.

Run Docker on this Jetson host. Same compose file as the SSH target: the
published clip-pt image passed the HTTP-upload path on Orin NX with a test
compose; this compose file was not run on a device on 2026-10-08. Clip
BLE/Wi-Fi sync needs a physical Clip.

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_stack.yaml}

Connect to this RK3588 host over SSH. Package acceptance blocked: on a Rock 5T
(2026-10-08) the 15 GB disk pre-check could not be met. With a rebuilt clip-pt
image started directly with Compose, the HTTP-upload path passed (SenseVoice RKNN
ASR, CPU CAM++ diarization, RK1828 LLM summary, transcript and MQTT); Whisper
was healthy but not used by any job. Clip BLE/Wi-Fi sync needs a physical
Clip; none was available.

### Target {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_stack.yaml}

Run Docker on this RK3588 host. Package acceptance blocked: the HTTP-upload
path passed on a Rock 5T only with a rebuilt clip-pt image; Clip BLE/Wi-Fi sync
needs a physical Clip.

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml}

Connect to this RK3576 host over SSH. Acceptance blocked: on the 2026-10-08 test
board the 15 GB disk pre-check could not be met, the SLV RK model roots were
absent, and SenseVoice plus Whisper did not fit together in the free RAM next
to the services already running there. Clip BLE sync needs a physical Clip.

### Target {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_stack.yaml}

Run Docker on this RK3576 host. Acceptance blocked: the disk pre-check and free RAM on the RK3576 test board
stopped an end-to-end run of the package stack.

## Step 2: Verify API {#verify_stack type=http_debug required=true config=devices/verify_clip.yaml}

Require clip-pt `/healthz` HTTP 200 on port 8631, then check SenseVoice on
8621, Whisper on 8622 (`/health` on Jetson, `/readyz` on RK), and the
Mosquitto broker on 1883. Verify the configured shared LLM endpoint with the
application-level voice RD contract (`base_url`, `model_name`, `api_key`,
`timeout_s`), then run a controlled sync and inspect the transcript schema.
Run the API, MQTT, resume, and offline checks of the documented M10 matrix only
with real Clip hardware once the physical gate is scheduled. The package does
not provide or validate a cloud provider, model, or API key, and does not
physically validate the Mosquitto image or GPU speaker-embedding artifact. The
example config leaves summary, MQTT, and diarization enabled; do not interpret
container healthchecks as full offline, summary, MQTT, diarization, or
physical Clip acceptance.
