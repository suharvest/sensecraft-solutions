# Deployment Guide

> **Draft / disabled.** Use only after the voice image, language licenses,
> device inventory, and physical acceptance gates are complete.

## Preset: Raspberry Pi + Jetson Voice (Draft) {#rpi_jetson}

Measured on an ARM64 Linux host (Broadcom BCM2712, 8GB; HA 2026.9.3 from this
package's compose) with
the voice endpoint on a Jetson Orin NX over Wyoming: 5 of 5 voice commands
(zh and en, "turn on/off the living room light") changed the HA entity state,
all handled by the built-in intent agent locally. STT final result 0.11–0.95 s
after the end of audio (median 0.12 s). Input was TTS-generated speech streamed
to the Assist pipeline, not a microphone, and the entities were virtual demo
lights. HomeKit pairing, Aqara/ZHA with ZBT-2, Voice PE, ESPHome, a physical
microphone/speaker, offline operation and Japanese commands are outside this
measurement: test the ones you need on your own installation before handover.

## Step 1: Deploy Home Assistant Container {#rpi_deploy type=docker_deploy required=true config=devices/ha_rpi.yaml}

Use 64-bit Raspberry Pi OS. Home Assistant listens on port 8123; if 8123 is
already used on the Pi (for example by another Home Assistant), set another
Home Assistant port before the first install. The ZBT-2
device path is optional: leave it empty to install Home Assistant before the
dongle is connected, then redeploy with the `/dev/serial/by-id/...` path.

### Target {#rpi_local type=local device=arm64_linux device_name="ARM64 Linux host (64-bit OS, 8GB RAM)" config=devices/ha_rpi.yaml}

Run Docker on this Raspberry Pi.

### Target {#rpi_remote type=remote device=arm64_linux device_name="ARM64 Linux host (64-bit OS, 8GB RAM)" config=devices/ha_rpi.yaml default=true}

Connect to this Raspberry Pi over SSH.

## Step 2: Deploy Jetson voice services {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

Runs one OpenVoiceStream service (Qwen3-ASR + Matcha TTS, profile
`jetson-edgellm-v091-matcha`, image `nrd6-ovs-jetson:20261008`) for both ASR and
TTS on port `voice_port` (default 8623), plus the Wyoming adapter
(`wyoming-slv-adapter:20261008`) that Home Assistant connects to on
`wyoming_stt_port` / `wyoming_tts_port` (default 10300 / 10200). On first start
the service downloads its models into the `jetson-models` volume (at least
30 GB free disk). Verified 2026-10-08 on an Orin NX with this compose file and
images whose config digests match the published 20261008 OVS and adapter images
(voice on 8633, Wyoming on 10301 / 10201 via the port inputs; models from an
existing volume, auto-download off): both ports answer the Wyoming `describe`
request, and TTS output fed back to STT matched 打开客厅灯, 关闭卧室的灯 and "Turn
on the living room light" (plus sentence-final punctuation); TTS
first audio 0.05–0.12 s, STT result 0.38–0.58 s after end of audio. Input was
synthetic speech, not a microphone. No license-cleared distributable voice
artifact is recorded yet.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_voice.yaml}

Run Docker on this Jetson host.

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_voice.yaml default=true}

Connect to this Jetson host over SSH.

## Step 3: Verify Home Assistant {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

Connect Home Assistant to the Jetson voice services, then run the checks:

1. In Home Assistant, go to **Settings → Devices & services → Add integration →
   Wyoming Protocol**. Enter the Jetson's IP address as host and the
   `wyoming_stt_port` from step 2 (default 10300) as port.
2. Add a second **Wyoming Protocol** integration with the same host and the
   `wyoming_tts_port` (default 10200).
3. Go to **Settings → Voice assistants**, open the Assist pipeline, and select
   the new speech-to-text and text-to-speech services.
4. Complete the ZHA, HomeKit and local voice checks.

If you later redeploy step 2 with different ports, the existing Wyoming
integrations keep the old ports: delete both and add them again.
