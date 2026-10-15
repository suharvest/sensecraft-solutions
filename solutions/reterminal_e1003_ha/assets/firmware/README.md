# Historical factory resource — 0.2.1 artifact pending

The current design targets **0.2.1 plaintext-only / contract 14**, removing
compiled API encryption and all App encryption/key-copy controls. Its new
commit, size, SHA and final hardware evidence are pending.

Git does not contain the binary, and no public download URL or release exists.
`manifest.json` pins release **0.2.0**, source
`a7116ee153158505faeec225d691c0cdef85a6da`, 1,377,472 bytes, SHA-256
`45cbf1ec46d5a00e8362e6d920cd9318841c58f2a081cfae809d9e38e64ccebb`.
`esp32_usb.yaml.in` still references that **historical 0.2.0** image, not the
0.2.1 target. It is not an active candidate step. These known values must not
be relabeled as a new build. The final artifact must replace version/size/SHA
and template checksum together after the coordinating session provides them.

From the repository root, a maintainer can materialize a **historical resource review copy**:

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

The tool checks size/SHA, copies only allowlisted files and materializes the
flash-review step. It keeps `enabled: false` and never connects to hardware,
imports into the App, configures devices or publishes. End users do not run it.
It is not the unified end-user flow: the target contract 14 App checks project,
version, hardware and name, then installs only when needed in the same form.

Write the merged factory image at **0x0**, never 0x10000; do not add duplicate
bootloader/app writes. Keep 115200, the built 4 MB layout and full-chip erase
off. NVS starts at 0x3a0000, beyond this image's write range. The local actual
0.1.0→0.2.0 upgrade retained Wi-Fi and the light target without erasing NVS.
It then used the prior private key to clear encryption and confirmed keyless
readback. Other migrations and factory-blank devices are not accepted by this
single test. Earlier encrypted 0.1 evidence remains in `docs/e1003-ha-usb-checks.md`.

0.2.0 was a transitional design with optional runtime encryption. Its 610-second
keyless recheck passed, but the device later returned RequiresEncryptionAPIError;
the source of reconfiguration is unconfirmed. It cannot establish sustained
keyless behavior. The 0.2.1 reference design removes api.encryption entirely;
a separate developer entry retains encryption. Final build and upgrade evidence
are pending, including treatment of older encrypted records.

Every different build must use a different firmware `project.version`, with
matching manifest version, size and SHA. The skip decision checks identity,
not an on-device image hash. A content version bump alone is insufficient.

Distribution still needs a separately authorized public binary URL, a verified
download hash, compatible App distribution and generated public contract 14
synchronization. No URL may be invented and the candidate stays disabled.
