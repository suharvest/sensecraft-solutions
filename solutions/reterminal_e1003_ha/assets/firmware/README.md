# E1003 factory firmware

Built from `esphome-reterminal-e1003-workspace` commit `8cdaf01` (`e1003-dashboard.yaml`).
`manifest.json` and `esp32_usb.yaml.in` pin the image:
1,366,816 bytes, SHA-256
`d9b58f0ecec316f8855c4ae609160bc56d7597d4d032fe950c5bf766cc51bdb0`.
Published to CDN: `https://sensecraft-statics.seeed.cc/solution-app/reterminal_e1003_ha/assets/firmware/8cdaf01/firmware.factory.bin`.
Each build goes to its own commit-named path; the previous 0.2.1 image stays at the unversioned path.

From the repository root, a maintainer can materialize a **local review copy**:

```bash
python3 scripts/stage_e1003_candidate.py \
  --firmware /absolute/path/to/firmware.factory.bin \
  --output /private/tmp/e1003-review/solutions/reterminal_e1003_ha
uv run --package sensecraft-solutionctl solutionctl validate \
  /private/tmp/e1003-review/solutions/reterminal_e1003_ha --spec-dir spec
uv run --package sensecraft-solutionctl solutionctl steps \
  /private/tmp/e1003-review/solutions/reterminal_e1003_ha --lang zh
uv run --package sensecraft-solutionctl solutionctl export reterminal_e1003_ha \
  --solutions-dir /private/tmp/e1003-review/solutions \
  --output-dir /private/tmp/e1003-review/packages
```

The tool checks size/SHA, copies allowlisted content and materializes the
flash-review step while preserving `enabled:false`. It never opens a device,
imports into the App or publishes. End users do not run it. Packaging validates
artifact integrity and references; it does not prove hardware acceptance.

Keep 115200, merged factory offset **0x0**, the built 4 MB layout and full-chip
erase off. NVS starts at 0x3a0000, beyond this image's range. Do not add duplicate
bootloader/app writes or erase NVS to bypass a migration issue. Different
builds must use different firmware project.version values and synchronized
manifest version/size/SHA; changing only content version is insufficient.

Hardware upload and device acceptance of this image remain unverified. Packaging
is only an integrity check of the USB payload; it does not supply native App
configuration. See the [single integration note](../../../../docs/e1003-ha-usb-candidate.md)
for current software checks, acceptance limits and release dependencies.

## Indicator panel firmware

Built from `sensecap-indicator-ha` branch `indicator-ha-native-api`, commit `dca0063`, with ESP-IDF 5.5.4. `devices/indicator_usb.yaml` pins the three images (CDN path `.../firmware/indicator/dca0063/`):

- `bootloader.bin` — offset 0x0, sha256 `2cb25580670bb09714d8683ec54dd6e7270e8b8c4fe8fe072738b0771d86bab9`
- `partition-table.bin` — offset 0x8000, sha256 `a7dfdccd649702098427a73dbc716db3ff9e51753271738f1d9d1f9ba0a5c67d`
- `indicator_ha.bin` — offset 0x10000, sha256 `6b99f3baf7fb8d3bcf9787794a4ac0484f82a259c219e180cc7bfb91d49f567a`

Flash settings: 460800 baud, dio / 8MB / 80m, no full-chip erase. Hardware flashing of this build is unverified. The ESP32-S3 is flashed through the Indicator's CH340 USB-UART (VID:PID `1a86:7523`, read from a real unit; the RP2040 coprocessor enumerates separately as `2886:0050`).
