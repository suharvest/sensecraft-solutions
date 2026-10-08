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

Use 64-bit Raspberry Pi OS. Port 8123 must be free on the Pi. The ZBT-2
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
(`wyoming-slv-adapter:20261008`, STT 10300 / TTS 10200) that Home Assistant
connects to. On first start the service downloads its models into the
`jetson-models` volume (at least 30 GB free disk). This is the layout of the
2026-10-08 Orin NX measurement above (same image, same profile); this compose
file itself was not run on a device on 2026-10-08 — the Orin NX had no free
disk. No license-cleared distributable voice artifact is recorded yet.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_voice.yaml}

Run Docker on this Jetson host.

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_voice.yaml default=true}

Connect to this Jetson host over SSH.

## Step 3: Verify Home Assistant {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

Open HA and complete the same ZHA, HomeKit, and local voice checks.
