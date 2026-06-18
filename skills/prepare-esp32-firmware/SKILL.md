---
name: prepare-esp32-firmware
description: Prepare ESP32 firmware files for solution deployment. Use when setting up firmware flashing, configuring esptool parameters, or adding ESP32/ESP32-S3/ESP32-C3 device support to a solution.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Prepare ESP32 Firmware

Guide for preparing ESP32 device firmware and configuration files.

## Required Files

| File | Description | Required |
|------|-------------|----------|
| `firmware.bin` | Main firmware binary | Yes |
| `bootloader.bin` | Bootloader (first flash) | Optional |
| `partition-table.bin` | Partition table | Optional |

## Directory Structure

```
solutions/[solution_id]/
├── solution.yaml              # Solution configuration
├── guide.md                   # English deployment guide (defines steps)
├── guide_zh.md                # Chinese deployment guide
├── gallery/                   # Images
│   └── watcher_connect.png
├── assets/
│   └── watcher_firmware/      # Firmware files
│       ├── firmware.bin
│       ├── bootloader.bin     # optional
│       └── partition-table.bin # optional
└── devices/
    └── [device_id].yaml       # Device config
```

## Device Configuration Template

Create `devices/[device_id].yaml`:

```yaml
version: "1.0"
id: watcher
name: SenseCAP Watcher
name_zh: SenseCAP Watcher
type: esp32_usb

detection:
  method: usb_serial
  # Watcher uses WCH USB-UART chip
  usb_vendor_id: "0x1a86"
  usb_product_id: "0x55d2"
  fallback_ports:
    - /dev/tty.wchusbserial*
    - /dev/cu.wchusbserial*
    - /dev/ttyUSB*
    - /dev/ttyACM*

firmware:
  source:
    path: assets/watcher_firmware/firmware.bin  # Local path or URL

  flash_config:
    chip: esp32s3              # esp32/esp32s2/esp32s3/esp32c3
    baud_rate: 921600
    flash_mode: dio
    flash_freq: 80m
    flash_size: 16MB
    partitions:
      - name: app
        offset: "0x10000"
        file: firmware.bin

steps:
  - id: detect
    name: Detect Device
    name_zh: 检测设备
    optional: false
    default: true

  - id: erase
    name: Erase Flash (Optional)
    name_zh: 擦除闪存 (可选)
    optional: true
    default: false

  - id: flash
    name: Flash Firmware
    name_zh: 烧录固件
    optional: false
    default: true

  - id: verify
    name: Verify
    name_zh: 验证
    optional: false
    default: true

post_deployment:
  reset_device: true
  wait_for_ready: 5
```

> **Cloud materials**: All `path` and `file` fields accept URLs (e.g., `https://cdn.example.com/firmware.bin`). Remote files are automatically downloaded and cached before deployment.

## Common Chip Configurations

### ESP32-S3 (SenseCAP Watcher)
```yaml
chip: esp32s3
baud_rate: 921600
flash_mode: dio
flash_freq: 80m
flash_size: 16MB
```

### ESP32-C3 (XIAO)
```yaml
chip: esp32c3
baud_rate: 460800
flash_mode: dio
flash_freq: 40m
flash_size: 4MB
```

### ESP32 (Classic)
```yaml
chip: esp32
baud_rate: 460800
flash_mode: dio
flash_freq: 40m
flash_size: 4MB
```

## Common USB VID/PID

| Device | VID | PID | Notes |
|--------|-----|-----|-------|
| WCH USB-UART (Watcher) | 0x1a86 | 0x55d2 | SenseCAP Watcher uses WCH chip |
| CP210x | 0x10c4 | 0xea60 | Silicon Labs USB-UART |
| CH340 | 0x1a86 | 0x7523 | Common USB-UART chip |
| FTDI | 0x0403 | 0x6001 | FTDI USB-UART |
| ESP32-S3 USB | 0x303a | 0x1001 | Native USB mode |

## Get USB VID/PID

```bash
# Linux/macOS
lsusb
# macOS
system_profiler SPUSBDataType
```

## Update guide.md

Add deployment step in `guide.md`:

```markdown
## Step 1: Flash Watcher Firmware {#flash_watcher type=esp32_usb required=true config=devices/watcher.yaml}

Flash the firmware to SenseCAP Watcher device.

### Wiring

![Connect Watcher](gallery/watcher_connect.png)

1. Connect Watcher to computer via USB-C cable
2. Select the serial port
3. Click Deploy button

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Serial port not found | Try a different USB cable or port |
| Flash failed | Unplug and replug the device, then try again |
```

> **Note**: Device step configuration is now defined in `guide.md` / `guide_zh.md` using markdown format. The `config_file` path points to the device YAML configuration.

## Manual Test

```bash
esptool.py --port /dev/ttyUSB0 --chip esp32s3 \
  --baud 921600 write_flash \
  --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x10000 firmware.bin
```
