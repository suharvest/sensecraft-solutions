# 0.2.1 plaintext-only factory resource

The reference build at firmware `09b3bbb` compiles out API encryption.
The solution enables one-click USB installation with firmware downloaded directly from Seeed CDN.

`manifest.json` and `esp32_usb.yaml.in` pin the actual **0.2.1** image:
1,337,056 bytes, SHA-256
`472fea16c509b46ecb04d6636a8d8acbc05756ce02157d20fd40eaf483401291`.
Published to CDN: `https://sensecraft-statics.seeed.cc/solution-app/reterminal_e1003_ha/assets/firmware/firmware.factory.bin`.

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

Final 0.2.1 hardware upload and device acceptance remain unverified. Packaging
is only an integrity check of the USB payload; it does not supply native App
configuration. See the [single integration note](../../../../docs/e1003-ha-usb-candidate.md)
for current software checks, acceptance limits and release dependencies.
