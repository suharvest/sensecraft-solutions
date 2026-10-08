# Deployment Guide

> **Draft / disabled.** Use only after the voice image, language licenses,
> device inventory, and physical acceptance gates are complete.

## Preset: RK3588 Single Box (Draft) {#rk_single_box}

## Step 1: Deploy HA and RK voice {#rk_deploy type=docker_deploy required=true config=devices/rk_voice.yaml}

Fill the approved voice image digest. The `/dev/serial/by-id/...` path for
ZBT-2 is optional; leave it empty to install before the dongle is connected. The compose also mounts the reviewed HA package and sentences;
the installation must be completed on the target host before using this draft.

### Target {#rk_local type=local device=rk3588 device_name="RK3588" config=devices/rk_voice.yaml}

Run Docker on this RK3588 host.

### Target {#rk_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk_voice.yaml default=true}

Connect to this RK3588 host over SSH.

## Step 2: Verify Home Assistant {#rk_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

Open the dashboard, pair ZBT-2 in ZHA, add HomeKit Bridge, and run a local
voice command with Voice PE. This verify step is not a claim of passing.

## Preset: Raspberry Pi + Jetson Voice (Draft) {#rpi_jetson}

Measured on a Raspberry Pi 5 (HA 2026.9.3 from this package's compose) with
the voice endpoint on a Jetson Orin NX over Wyoming: 5 of 5 voice commands
(zh and en, "turn on/off the living room light") changed the HA entity state,
all handled by the built-in intent agent locally. STT final result 0.11–0.95 s
after the end of audio (median 0.12 s). Input was TTS-generated speech streamed
to the Assist pipeline, not a microphone, and the entities were virtual demo
lights. Not verified: HomeKit pairing, Aqara/ZHA with ZBT-2, Voice PE, ESPHome,
physical microphone/speaker, offline operation, Japanese.

## Step 1: Deploy Home Assistant Container {#rpi_deploy type=docker_deploy required=true config=devices/ha_rpi.yaml}

Use 64-bit Raspberry Pi OS. Port 8123 must be free on the Pi. The ZBT-2
device path is optional: leave it empty to install Home Assistant before the
dongle is connected, then redeploy with the `/dev/serial/by-id/...` path.

### Target {#rpi_local type=local device=rpi device_name="Raspberry Pi" config=devices/ha_rpi.yaml}

Run Docker on this Raspberry Pi.

### Target {#rpi_remote type=remote device=rpi device_name="Raspberry Pi" config=devices/ha_rpi.yaml default=true}

Connect to this Raspberry Pi over SSH.

## Step 2: Deploy Jetson voice services {#jetson_deploy type=docker_deploy required=true config=devices/jetson_voice.yaml}

Provide approved ASR/TTS image and digest values. The current record has no
verified TTS E2E and no license-cleared distributable voice artifact. The
2026-10-08 measurement above used a different voice service on the Jetson (one
OpenVoiceStream container with Qwen3-ASR and Matcha TTS plus the Wyoming
adapter); this step's split ASR/TTS compose was not exercised.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_voice.yaml}

Run Docker on this Jetson host.

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_voice.yaml default=true}

Connect to this Jetson host over SSH.

## Step 3: Verify Home Assistant {#rpi_verify type=web_dashboard required=true config=devices/verify_ha.yaml}

Open HA and complete the same ZHA, HomeKit, and local voice checks.
