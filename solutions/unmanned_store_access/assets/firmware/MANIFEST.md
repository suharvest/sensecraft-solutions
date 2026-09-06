# P4 firmware manifest

**No binary is in this directory and none has been uploaded to a CDN.** This
file records what has to be built, where it will live, and what has to be
measured before any of it may be flashed onto a door.

## Source

| Segment | Repository | Branch | Head at packaging time |
|---|---|---|---|
| XIAO ESP32-S3 application | `xiaozhi-esp32` | `feature/door-access-xiao-grove` | `8760bd0` |
| Himax WE2 firmware + models | `grove-vision-face-embedding` / SSCMA | — | not selected yet |

The ESP32 branch adds 3043 lines across 25 files: a new board
`main/boards/xiao-esp32s3-grove-door/`, and `main/face/` carrying the FDB1
library format, cosine matching, the access policy, the door actuator, the
event contract and the HTTP library sync. It has never been built for the
target; the only compilation done so far is a host-side unit-test shim
(`main/face/host_test/shim.cc`).

## Flash layout (from `partitions_xiao_door.csv`)

8 MB flash, ESP32-S3 with PSRAM.

| Partition | Type | Offset | Size |
|---|---|---|---|
| `nvs` | data/nvs | `0x9000` | `0x6000` |
| `otadata` | data/ota | `0xf000` | `0x2000` |
| `phy_init` | data/phy | `0x11000` | `0x1000` |
| `ota_0` | app | `0x20000` | `0x330000` |
| `ota_1` | app | (follows) | `0x330000` |
| `facedb0` | data/`0x40` | `0x680000` | `0x40000` |
| `facedb1` | data/`0x40` | `0x6c0000` | `0x40000` |
| `assets` | data/spiffs | `0x700000` | `0x100000` |

Two library slots rather than one: a download always targets the inactive slot,
and the active pointer in NVS flips only after the body sha256 verifies. A
power cut mid-download therefore cannot damage the library that is currently
opening the door. At roughly 296 bytes per record (32-byte person id, 128
fp16 values, 8 bytes of flags) a 256 KB slot holds about 880 people — that
figure is arithmetic from the record layout, not a measurement, and the real
ceiling also depends on match latency growing with library size, which has not
been measured either.

## Destination, once built

The packaging convention for firmware and models is:

```
https://sensecraft-statics.seeed.cc/solution-app/unmanned_store_access/assets/firmware/<name>-<sha8>.bin
https://sensecraft-statics.seeed.cc/solution-app/unmanned_store_access/assets/models/<name>.tflite
```

Multi-segment ESP32 flashing uses bare file names per segment, following the
D1001 preset convention: bootloader at `0x2000`, partition table at `0x8000`,
ota_data at the offset the built table reports, and the application at
`0x20000`. Every segment carries its own sha256, and `devices/p4_xiao_door.yaml`
must name that sha256 next to the URL in the same change that uploads it.

## Before any of this reaches a door

Four things are unresolved and all four are in the design spec as blockers:

1. **The matching threshold.** Three different values are recorded across the
   source repositories — 0.4 in the Watcher code, 0.5 in its feature guide,
   0.30 suggested by `grove-vision-face-embedding`. They cannot all be right.
   Sweep positive and negative pairs on the assembled hardware and set it from
   that; copying any of the three is not acceptable.
2. **The model flash address.** `0x400000` and `0x510000` both appear in the
   source repositories. Confirm against the built partition table.
3. **The WE2 reset line.** The Watcher board drives it from an IO expander. On
   a discrete XIAO + Grove Vision AI V2 build it is a hand-wired connection on
   D2 (`GPIO_NUM_3`), and the WE2 flasher requires the ESP32 to hold it
   asserted. Nobody has flashed a WE2 through this path yet.
4. **There is no liveness model for the WE2.** Not in this project, not in the
   Watcher firmware, not in `grove-vision-face-embedding`. The policy compensates
   by refusing everything except an allowlisted person inside a schedule, and
   the events carry `liveness.passed: null`. That is a mitigation, not a fix.
