---
name: prepare-himax-firmware
description: Prepare Himax WE2 firmware and AI models for SenseCAP Watcher deployment. Use when setting up xmodem flashing, configuring AI model addresses, or adding Himax device support to a solution.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Prepare Himax WE2 Firmware

Guide for preparing Himax WE2 firmware and AI models for SenseCAP Watcher devices.

## Overview

SenseCAP Watcher uses a dual-chip architecture:
- **ESP32-S3**: Main controller, WiFi/BLE connectivity
- **Himax WE2**: AI accelerator chip for vision tasks

This skill covers flashing firmware and AI models to the Himax WE2 chip.

## Key Concepts

### USB Interfaces

Watcher exposes two USB serial interfaces:
| Interface | Pattern (macOS) | Pattern (Linux) | VID:PID | Purpose |
|-----------|----------------|-----------------|---------|---------|
| Himax WE2 | `/dev/cu.usbmodem*` | `/dev/ttyACM*` | 0x1A86:0x55D2 | Firmware flashing |
| ESP32-S3 | `/dev/cu.wchusbserial*` | `/dev/ttyUSB*` | 0x1A86:0x55D2 | Serial monitor |

### ESP32 Reset Hold

**Critical**: During Himax flashing, the ESP32 must be held in reset state. Otherwise, the ESP32 firmware will detect Himax anomalies and reset it, causing flashing to fail.

The deployer automatically handles this by:
1. Opening ESP32 serial port
2. Setting DTR=False (holds EN pin low = reset state)
3. Flashing Himax
4. Releasing DTR to allow normal boot

## Directory Structure

```
solutions/[solution_id]/
├── solution.yaml
├── guide.md
├── guide_zh.md
├── gallery/
├── assets/
│   ├── watcher_firmware/
│   │   └── firmware.img            # Base firmware
│   └── models/
│       ├── model1.tflite           # AI model 1
│       └── model2.tflite           # AI model 2
└── devices/
    └── watcher_himax.yaml          # Device config
```

## Device Configuration Template

Create `devices/watcher_himax.yaml`:

```yaml
version: "1.0"
id: watcher_himax
name: Himax WE2 Face Recognition
name_zh: Himax WE2 人脸识别
type: himax_usb

detection:
  method: usb_serial
  # Watcher Himax WE2 USB identifiers (WCH chip)
  usb_vendor_id: "0x1a86"
  usb_product_id: "0x55d2"
  fallback_ports:
    - "/dev/cu.usbmodem*"
    - "/dev/tty.usbmodem*"
    - "/dev/ttyACM*"

firmware:
  source:
    path: assets/watcher_firmware/firmware.img  # Local path or URL

  flash_config:
    baudrate: 921600
    timeout: 60
    protocol: xmodem                  # xmodem (128B) or xmodem1k (1024B)
    requires_esp32_reset_hold: true   # Critical for SenseCAP Watcher

    # Multi-model configuration
    models:
      - id: face_detection
        name: Face Detection (SCRFD)
        name_zh: 人脸检测模型 (SCRFD)
        path: assets/models/scrfd.tflite
        flash_address: "0x400000"     # Flash memory address
        offset: "0x0"
        required: true
        default: true
        description: Core face detection model
        description_zh: 核心人脸检测模型
        size_hint: "512KB"

      - id: face_embedding
        name: Face Embedding
        name_zh: 人脸特征模型
        path: assets/models/ghostfacenet.tflite
        flash_address: "0x510000"
        offset: "0x0"
        required: true
        default: true
        description: Face recognition embedding model
        description_zh: 人脸识别特征提取模型
        size_hint: "800KB"

user_inputs:
  - id: serial_port
    name: Serial Port
    name_zh: 串口
    type: serial_port
    required: true
    description: Select the USB port for Himax WE2 (usbmodem)
    description_zh: 选择 Himax WE2 的串口（usbmodem 开头）
    auto_detect: true

  - id: model_selection
    name: Models to Flash
    name_zh: 选择要烧录的模型
    type: model_select
    required: false
    description: Select AI models to flash
    description_zh: 选择要烧录的 AI 模型

steps:
  - id: detect
    name: Detect Device
    name_zh: 检测设备
  - id: flash
    name: Flash Firmware & Models
    name_zh: 烧录固件和模型
  - id: verify
    name: Verify
    name_zh: 验证

post_deployment:
  reset_device: false
  wait_for_ready: 5
```

> **Cloud materials**: All `path` fields (firmware, models) accept URLs. Remote files are automatically downloaded and cached before deployment.

## Xmodem Protocol

### Flash Sequence

1. **Enter bootloader**: Send `1\r` repeatedly until "Send data using the xmodem protocol"
2. **Prepare**: `sleep(1)`, `flushInput()`, send `1\r` again
3. **Send base firmware**: xmodem transfer (library handles 'C' handshake)
4. **For each AI model**:
   - Wait for reboot prompt, send `n\r` to continue
   - Send preamble packet with flash address
   - Wait for reboot prompt, send `n\r`
   - Send model file via xmodem
5. **Reboot**: Send `y\r` to confirm reboot

### Preamble Format

For multi-model flashing, each model needs a preamble packet:

```
Offset  Size  Content
0x00    2     Magic header: 0xC0, 0x5A
0x02    4     Flash address (little-endian)
0x06    4     Offset (little-endian)
0x0A    2     Magic footer: 0x5A, 0xC0
0x0C    N     Padding (0xFF) to packet size (128 or 1024 bytes)
```

## Model Flash Address Map

Common flash address layout for Watcher:

| Address | Size | Content |
|---------|------|---------|
| 0x000000 | 4MB | Base firmware |
| 0x400000 | 1MB | Model slot 1 |
| 0x510000 | 1MB | Model slot 2 |
| 0x600000 | 1MB | Model slot 3 |
| 0x700000 | 2MB | Model slot 4 (larger) |

## Update guide.md

Add deployment step:

```markdown
## Step 1: Flash Watcher AI Firmware {#flash_himax type=himax_usb required=true config=devices/watcher_himax.yaml}

Flash face recognition firmware and AI models to SenseCAP Watcher.

### Wiring

![Connect Watcher](gallery/watcher_connect.png)

1. Connect Watcher to computer via USB-C cable
2. Wait for port auto-detection (usbmodem)
3. Select AI models to flash (optional)
4. Click Deploy button
5. **Important**: Do NOT disconnect during flashing

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Port not detected | Try different USB cable (data cable, not charge-only) |
| Flashing timeout | Ensure Watcher is powered on, try reconnecting |
| "ESP32 port not found" | Normal on some systems - flashing may be less stable |
| Models not flashing | Check model files exist in assets/models/ |
```

## Testing

### Check USB Connection

```bash
# macOS
system_profiler SPUSBDataType | grep -A 5 "Watcher"

# Linux
lsusb | grep "1a86:55d2"

# List serial ports
python3 -c "import serial.tools.list_ports; [print(p.device, p.description) for p in serial.tools.list_ports.comports()]"
```

### Manual Xmodem Flash

```bash
# Install dependencies
pip install xmodem pyserial

# Use the project's flash script (if available)
cd ~/project/grove_vision_2/sscma-example-we2/xmodem
uv run python flash_watcher.py --firmware --models
```

## Reference Solutions

- `solutions/smart_space_assistant/devices/watcher_himax.yaml` - Face recognition example

## Dependencies

Required Python packages:
- `xmodem` - Xmodem protocol implementation
- `pyserial` - Serial port communication

These are included in the project's dependencies.
