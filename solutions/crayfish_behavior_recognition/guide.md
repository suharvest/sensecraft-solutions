# Deployment Guide: Aquaculture Crayfish Behavior & Fighting Recognition

Deploy real-time edge AI crayfish fight/harassment detection, sex classification, and cannibalism risk monitoring on Seeed reCamera.

---

## Preset: reCamera Pro {#recamera_pro}

Autonomous 4-stage funnel vision pipeline running entirely on reCamera Pro (RV1126B 3 TOPS NPU), with 8-frame temporal verification mosaic and multi-frame sex voting.

## Step 1: Deploy Crayfish Behavior App {#deploy_recamera_pro_crayfish type=recamera_pro_app required=true config=devices/recamera_pro.yaml}

The deployer inspects App Center on the reCamera Pro. It automatically downloads and uploads the official signed package (`crayfish-fight-v0.1.2-core.tar.gz`), installs, and activates it.

### Target {#recamera_pro_device type=remote device_name="reCamera Pro" config=devices/recamera_pro.yaml}

---

## Preset: reCamera 2002 {#recamera_2002}

Ultra-compact RISC-V edge camera running native SG2002 TPU BF16 models for crayfish detection and cascaded behavior alerts.

## Step 1: Deploy Crayfish Detector {#deploy_recamera_2002_crayfish type=recamera_app required=true config=devices/recamera_2002.yaml}

Installs native `crayfish_det_cv181x_bf16.cvimodel` and `crayfish_behavior_cv181x_bf16.cvimodel` alongside the C++ inference and alert daemon.

### Target {#recamera_2002_device type=remote device_name="reCamera 2002" config=devices/recamera_2002.yaml}
