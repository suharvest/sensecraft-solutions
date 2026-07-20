# Weather Classification — build artifact notes

Both build artifacts are complete and wired into `devices/recamera_weather.yaml`.

## Artifacts

- `weather-classifier_0.1.0_riscv64.deb` — hosted at
  `https://files.seeedstudio.com/Solution/landpage_asset/recamera-ecosystem/weather-classifier_0.1.0_riscv64-7e53a545.deb`
  (not committed to this repo; sha256
  `d7ea50ac3c16309d3c230f1a32a6894b1cda1f28451e43a83980434b7e199f7f`). Cross-compiled
  against reCamera-OS SDK 0.2.2 (matches the test device's firmware date) from
  [`Love4yzp/weather_classification_recamera`](https://github.com/Love4yzp/weather_classification_recamera)
  — a fork of the upstream demo with the RTSP+MQTT patch applied and committed directly
  (`main.cpp`, `main/mqtt_publisher.h/.cpp`, `main/rtsp_demo.h/.c`), replacing the
  earlier prose patch doc that used to live in this directory. To rebuild: clone that fork
  and cross-compile as-is, no patch to apply by hand.
- `weather_mobilenetv3_small_bf16.cvimodel` — hosted at
  `https://files.seeedstudio.com/Solution/models/weather_mobilenetv3_small_bf16.cvimodel`
  (not committed to this repo — referenced by URL in `devices/recamera_weather.yaml`,
  sha256 `1b33bf4097c7b5a1543d845c1a71568dedcdf8458c8d88deb7f0ef504e65965c`). Verified to be
  byte-identical (same checksum) to the model file used in the real-hardware test below.

## Validation

**End-to-end on real hardware** (`recamera@10.8.0.194`, firmware 0.2.2, 2026-07-20):
- `opkg install` of the `.deb` succeeds; `S92weather-classifier` starts/stops cleanly via
  the init script; `opkg remove` leaves the device in its original state.
- RTSP confirmed decodable via `ffprobe`: H.264, 1280x720, 15fps, at
  `rtsp://<device-ip>:8554/live0`.
- MQTT confirmed publishing valid JSON to `recamera/weather/results` at ~9fps end-to-end,
  matching the schema already wired into `preview/draw_weather.js` and
  `devices/preview_weather.yaml` exactly — no changes needed on the preview side.
- `binary.conflict_services.stop` (node-red/sscma-node/sscma-supervisor) and the
  `devices/restore_defaults.yaml` rollback step were both exercised live.
- **Cross-preset conflict handling**: downloaded and inspected the actual remotely-hosted
  `.deb`s for `face-analysis` and `yolo-detector` (`sensecraft-statics.seeed.cc/.../packages/`)
  to check how they avoid the app store's presets fighting over the camera. Found a real,
  working mechanism baked into *each app's own init script* (not the device YAML): a
  `stop_conflicting_services()` shell function, called at the top of every `start()`, that
  stops node-red/sscma-node/sscma-supervisor **and** every other known sibling preset binary
  by init-script-name glob (`face-analysis detection-blur ppocr-reader retail-vision
  yolo8-detector yolo11-detector yolo11s-detector yolo26-detector yolo-detector`, plus
  `facemesh-reader` in face-analysis's copy). `S92weather-classifier`'s init script now
  carries the identical pattern (weather-classifier didn't exist when the older presets
  were built, so it's the only name missing from *their* lists — fixing that would require
  releasing updated `.deb`s for those other presets, out of scope here). Verified live on
  real hardware: stood up a stub process under a sibling app's exact init-script name
  (`S92ppocr-reader`, plain `sleep 600`) and confirmed `weather-classifier restart` killed
  it via its own `stop_conflicting_services()`, while `weather-classifier` itself stayed
  healthy (RTSP+MQTT still up) throughout.

- **The primary conflict-resolution mechanism actually lives in the SenseCraft Solution app's
  own deploy engine**, not the init script — confirmed via
  `~/Library/Application Support/com.seeedstudio.sensecraft-solution/logs/provisioning-station.log`
  during a real API-driven deploy: `provisioning_station.deployers.recamera_cpp_deployer`
  probes device state generically (`Device state: mode=cpp,
  cpp_services=['/etc/init.d/S92weather-classifier'], ...`) by scanning `/etc/init.d/S9*`
  directly, then stops+disables whatever it finds — with zero need for the newly-deployed
  package to know the old one's name, or vice versa. Verified both directions live:
  deploying `face_analysis` while `weather-classifier` was running cleanly stopped it (and
  vice versa) purely through this engine-side probe, no init-script involvement. The
  `stop_conflicting_services()` in `S92weather-classifier` (see above) is a secondary,
  belt-and-suspenders layer that only matters for paths that bypass the app (direct SSH,
  reboot) — it's there for parity with the other presets' init scripts, not because it's
  load-bearing when deployed through the app.

Built with `dpkg-deb -Zgzip` — the default zstd compression on modern `dpkg-deb` is **not**
readable by this device's `opkg`; always rebuild with `-Zgzip` if regenerating this package.
`S92weather-classifier` now matches the other presets' real init scripts structurally too
(confirmed by diffing against the actual downloaded `face-analysis`/`ppocr-reader` `.deb`s):
binary at `/usr/local/bin/weather-classifier` (not `/usr/bin/`), `start-stop-daemon` for
start/stop instead of a hand-rolled `& echo $!`, a `ps aux` fallback in `status()` for when
the pidfile is stale, and loading `/etc/recamera.conf` (global) before
`/etc/weather-classifier.conf` (solution-specific override) — plus a `prerm` that
`pkill -f weather-classifier` on removal, matching `face-analysis`'s.

## Reference

- Source: [`Love4yzp/weather_classification_recamera`](https://github.com/Love4yzp/weather_classification_recamera)
  (fork of `yyling0101-a11y/weather_classification_recamera`), commit `992c23e` — this is
  the actual patched source, not a prose description of it. `cvi_rtsp` only provides the
  low-level `CVI_RTSP_*` API, not the `initRtsp`/`deinitRtsp`/`fpStreamingSendToRtsp`
  wrapper functions — those were vendored from `sscma-example-sg200x`'s own
  `solutions/video_demo/main/rtsp_demo.c` (verified byte-for-byte reusable).
- Toolchain: `sophgo/host-tools` repo, `gcc/riscv64-linux-musl-x86_64` directory
  (Xuantie-900 gcc 10.2.0, Toolchain V2.6.1 B-20220906 — confirmed to exactly match the
  test device's `/proc/version` toolchain string). SDK libs/headers: reCamera-OS release
  `0.2.2` (`sg2002_reCamera_0.2.2_emmc_sdk.tar.gz`), picked to match the device's firmware
  build date (2026-01-07) rather than the newer 0.2.4 release, to avoid ABI mismatch.
- Runtime requires `LD_LIBRARY_PATH` including `/mnt/system/lib` and `/mnt/system/usr/lib`
  (same as `sscma-node`'s own init script) — already baked into the `.deb`'s
  `S92weather-classifier` init script.

## License note

The upstream demo repo (https://github.com/yyling0101-a11y/weather_classification_recamera)
has no LICENSE file (all rights reserved by default), and neither does the fork above.
Confirm reuse rights with the author before shipping the ported binary or the fork's source
publicly, if not already an internal/authorized resource.
