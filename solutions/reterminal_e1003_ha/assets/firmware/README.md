# Factory image resource

The binary is deliberately absent from Git. There is no public download URL
and no release has been created. `manifest.json` pins the exact local artifact;
`esp32_usb.yaml.in` is the deployment configuration to review, not an active
device configuration in the source candidate.

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

The tool checks size and SHA-256 before creating output, copies only the
allowlisted solution files and the supplied factory image, and replaces the
first review step with the real `esp32_usb` configuration. It keeps
`enabled: false`. It does not connect to hardware, import into App, configure
Wi-Fi or keys, or publish anything. End users will not run this authoring tool.

The factory image goes at **0x0**, never 0x10000. It contains the bootloader,
partition table, initial OTA data and app; do not add a second bootloader/app
write. The pinned image uses a 4 MB layout on a panel with 32 MB physical flash.
The NVS partition lies beyond this merged image's write range. Keep the
`erase` substep **false** for normal USB updates. Same-image, same-partition
retention was verified in the firmware project and the local App USB test;
cross-version migration remains unverified. Evidence is recorded in the content
repository at `docs/e1003-ha-usb-checks.md`.

For eventual distribution, a maintainer must separately authorize publication,
upload the reviewed binary, verify its downloaded hash, replace the local
resource reference with that real URL, synchronize the public contract for the
native App configuration step, and complete the remaining acceptance before
enabling this technical demo. Do not generate a URL from a guessed release tag.

The unified App flow (contract 12) loads this canonical manifest using the
solution ID, checks the device's project/version/hardware/name, and installs
only if needed before applying settings. Users do not choose between flashing
and configuration presets. The authoring tool above remains an isolated
flash-review utility, not that unified end-user flow. A matching hardware probe
selected skip; the new installation branch and complete flow still need
hardware acceptance.

Each different firmware build must have a different firmware `project.version`
and matching `firmware_version`, size and SHA in this manifest. The skip decision
uses device identity/version, not an on-device image hash. Never replace the
pinned image with a different build carrying the same project/version; changing
only the solution content version does not distinguish firmware builds.
