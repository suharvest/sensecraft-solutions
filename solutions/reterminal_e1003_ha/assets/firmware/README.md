# 0.2.1 plaintext-only factory resource

The reference build is committed at firmware `09b3bbb`, App `9235b5e6`, contract
14. It removes compiled `api.encryption`: USE_API_PLAINTEXT is present while
USE_API_NOISE and USE_PROVISIONING are absent. The separate developer entry
retains encryption. App encryption/key-copy controls are removed; a legacy
`encrypt_api=true` request fails before hardware access.

`manifest.json` and `esp32_usb.yaml.in` pin the actual **0.2.1** image:
1,337,072 bytes, SHA-256
`23dae64ed8b79f05a423a2748b6b3e2f1369e96b80f0d16fd03deebb62609528`.
No binary is committed and no public download URL or release exists.

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

The WCH port disappeared before selection/upload, so **0.2.1 has not been
flashed or verified on hardware**. The hardware API flag showing encryption
unsupported is still unobserved. Old key/record migration, sustained keyless
readback and new Wi-Fi setup remain pending. Prior 0.1/0.2 results remain
historical in `docs/e1003-ha-usb-checks.md`: even the successful 610-second
0.2.0 recheck was followed by RequiresEncryptionAPIError, with its initiator
unknown. It does not establish fixed plaintext behavior for the new release.

The candidate remains disabled pending public contract 14 synchronization,
compatible App distribution, a separately authorized public firmware URL and
remaining acceptance. No guessed download URL or publication is included.
