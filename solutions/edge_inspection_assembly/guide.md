## Preset: Camera + reComputer J (Orin) {#jetson}

The measured path. The runtime, the MQTT broker and the Modbus server all run
on one Jetson Orin box; a TensorRT engine is built on the device during the
first deploy, which takes about five minutes and ties the engine to that board
and that TensorRT version. Every number on the intro page was taken here.

| Device | Purpose |
|--------|---------|
| reComputer J30 / J40 | Detection, assembly comparison, dimension measurement, Modbus TCP server, MQTT broker and the web panel |
| Camera | Supplies the video of the inspection station; any RTSP or ONVIF camera works, as does a USB camera or a recorded file |

**Important.** This is a demo package, not a certified metrology or safety
product. The dimension module measures pixels against a calibration reference —
its accuracy depends on your optics, lighting and fixture, and it does not
replace a calibrated gauge in an acceptance test. The shipped model is trained
on DeepPCB, a bare-board copper-defect dataset used here to prove the chain end
to end; it is not a missing-part detector for your assemblies, and a real
station needs a model trained on your own images. Three known weaknesses to plan
around: expected-item ROIs are picture coordinates, so any camera movement
invalidates the template; a tilted part or a calibration reference at a
different working distance biases every measurement; and all camera streams
share one Modbus register bank, so per-stream results have to come from MQTT.

## Step 1: Deploy the Inspection Runtime {#deploy_jetson_assembly type=docker_deploy required=true config=devices/jetson_assembly.yaml}

Uploads the compose project and the configuration, downloads and checksums the
ONNX model, builds the TensorRT engine on the device, then starts the runtime
and its MQTT broker.

### Prerequisites

- JetPack 6.x (L4T r36.x) with the TensorRT dev packages, so that
  `/usr/src/tensorrt/bin/trtexec` exists and runs.
- Docker with the NVIDIA runtime configured, and at least 10 GB free.
- The runtime image `edge-inspection-assembly-jetson:0.1.0-dev` present on the
  device. **This tag is not published to a registry yet** — build it once on the
  board from the upstream repository (`docker build --network=host -f
  platforms/jetson/Dockerfile.slim -t edge-inspection-assembly-jetson:0.1.0-dev .`)
  or set `INSPECTION_IMAGE` to a tag the device can pull. The deploy checks for
  it before doing anything else.
- The camera reachable from the Jetson. Test an RTSP address in VLC first.
- Ports 1883, 502 and 8080 free on the host — the containers use host
  networking so the PLC can reach Modbus directly.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `Image ... is not on this device` | The runtime tag is not published yet; build it on the board or point `INSPECTION_IMAGE` at a tag you can pull |
| Engine build fails | Confirm `/usr/src/tensorrt/bin/trtexec` exists and 10 GB is free; delete a half-built `*.engine.part` from an interrupted run before retrying |
| ONNX checksum mismatch | The model file is not the one these measurements came from. Remove it and let the step download again |
| No video from the camera | Test the RTSP URL in VLC; a wrong path or wrong credentials is the most common failure |
| Container restarts every ~30 s | A file source that reached its end and exited — expected for a recorded clip without looping, not a crash |
| Deploy cannot connect | Confirm SSH is reachable and the username is right; Seeed images use `recomputer` or `nvidia` |
| Modbus port 502 refused | Another Modbus server on the host already holds it, or the container did not start — check `docker logs edge-inspection-assembly-app` |

### Target {#jetson_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_assembly.yaml default=true}

Deploy over SSH from this computer to a Jetson on the network. Use this unless
you are running the app on the Jetson itself.

### Target {#jetson_local type=local device=jetson device_name="Jetson" config=devices/jetson_assembly.yaml}

Deploy onto the machine this app is running on. Only valid when that machine is
the Jetson.

## Step 2: Set Up the Dimension Calibration {#calibrate_dimension_jetson type=manual required=false config=devices/calibrate_dimension.yaml}

Optional, and only needed if you want the dimension check. A station that only
compares against the expected-item list can skip it — the dimension section then
reports `uncalibrated` and Modbus HR 11 = 4, which is a defined state rather
than a fault.

### Prerequisites

- A calibration reference in the **same plane** as the measured surface: an
  ArUco marker (the example expects `DICT_4X4_50`, id 7, 25 mm wide) or any
  object of a known width. Measure the printed marker with a caliper — printers
  scale to fit the page.
- A known-good part to confirm the result against.
- The runtime already deployed, so the self-check can run inside its image.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `check_aruco.py` exits non-zero | This OpenCV build has no `aruco` module; rebuild the image with `opencv-contrib-python-headless`. The pinned `opencv-python-headless==4.10.0.84` does carry it — ArUco moved into the main `objdetect` module in OpenCV 4.7, so `contrib` is not required |
| `status: uncalibrated` | The reference was not detected — check `calibration.roi` bounds it, and that `aruco_dict` and `aruco_id` match the marker you printed |
| `status: not_found` | No contour large enough inside the measurement ROI; usually low contrast or a window drawn around the wrong feature |
| Measurement is consistently off by a few percent | The reference is not in the plane of the part, or the printed marker is not the width configured in `ref_object_width_mm` |
| Everything reads NG at nominal size | `tolerance_mm` is tighter than the station's own measurement error; measure a known-good part and set the tolerance above that spread |

## Step 3: Watch the Verdicts {#preview_assembly_jetson type=web_dashboard required=false config=devices/preview_assembly.yaml}

Opens the runtime's own panel on port 8080 — live counters, recent events and an
MJPEG preview with detection boxes and the assembly ROIs drawn in.

### Deployment Complete

The station is running. It publishes one MQTT event per frame, keeps the Modbus
registers and coils current, and serves the panel locally.

#### Quick verification

1. Open `http://<jetson-ip>:8080/healthz` and confirm `frames_processed` is
   increasing and `mqtt_rejected` stays at 0.
2. Subscribe to the results:
   `mosquitto_sub -h <jetson-ip> -t '<station-name>/inspection/#' -C 5`.
   Each event must carry an `assembly` section (`expected_count`,
   `matched_count`, `missing_count`, `missing[]`) and a `dimension` section
   (`calibrated`, `mm_per_pixel`, `measurements[]`), plus `verdict_reasons`.
3. Take one expected part off the fixture. `missing_count` rises,
   `verdict_reasons` gains `missing`, and `verdict` becomes `NG` even when
   `defect_count` is 0.
4. Watch the coil flip with a Modbus client on port 502, unit 1: Coil 0 = NG and
   Coil 1 = OK are mutually exclusive, and HR 8 tracks the missing count you
   just created.

#### Configuring the expected-item list

`assembly` and `dimension` are configured **per source** — the ROIs are picture
coordinates, so each camera carries its own block under `sources[]` in
`config/config.json` (a top-level block is only a fallback). The shipped example
holds six items generated from one DeepPCB frame:

```json
{
  "stream_id": "line1-pcb",
  "uri": "rtsp://admin:password@192.168.1.64:554/Streaming/Channels/101",
  "kind": "rtsp",
  "fps": 10,
  "assembly": {
    "expected": [
      {"class": "open", "roi": [0.29328, 0.34656, 0.42078, 0.43156],
       "min_count": 1, "label": "slot00-open"},
      {"class": "mousebite", "roi": [0.36469, 0.45766, 0.44469, 0.52516],
       "min_count": 1, "label": "slot01-mousebite"}
    ],
    "match_distance": 0.12,
    "min_score": 0.25,
    "report_extra": false
  }
}
```

One entry per part slot. `class` must be one of the model's `classes`; `roi` is
`[x1, y1, x2, y2]` normalised to 0–1 in this camera's framing; `min_count` is how
many instances that slot expects; `label` is what the operator sees in the
`missing[]` list. `match_distance` is the largest normalised centre distance
still counted as a match, `min_score` drops low-confidence detections before
matching, and `report_extra` decides whether detections outside every expected
ROI are reported as `extra` (and therefore, with `ng_on_extra`, can fail a
board).

The dimension block sits on whichever source sees the calibration reference:

```json
"dimension": {
  "calibration": {"detect": "aruco", "aruco_dict": "DICT_4X4_50", "aruco_id": 7,
                  "ref_object_width_mm": 25.0,
                  "roi": [0.020695, 0.320312, 0.245305, 0.679688]},
  "measurements": [
    {"name": "gauge-block", "roi": [0.401906, 0.2375, 0.894094, 0.7625],
     "nominal_width_mm": 60.0, "nominal_height_mm": 40.0, "tolerance_mm": 1.0}
  ]
}
```

`calibration.roi` bounds the reference and yields `mm_per_pixel`; each
measurement has its own ROI, nominal size and tolerance. Set
`ref_object_width_mm` to the width you measured with a caliper, not the width
you asked the printer for.

Which reasons can fail a board is configurable: `rules.ng_on_defect`,
`ng_on_missing`, `ng_on_extra` and `ng_on_dimension` switch the four
independently.

#### Reading the outputs

Modbus TCP, unit 1, port 502:

| Register | Meaning |
|---|---|
| Coil 0 / Coil 1 | NG / OK, mutually exclusive |
| HR 0 / HR 1 | Primary defect class id / defect count |
| HR 2–5 | Primary bbox cx, cy, w, h, normalised x10000 |
| HR 6–7 | Heartbeat, Unix seconds as a uint32 high/low word |
| HR 8 / HR 9 | Missing count / extra count |
| HR 10 | Primary measurement in millimetres x100 (long edge) |
| HR 11 | Tolerance code: 0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated |

HR 0–7 are bit-identical to the surface-inspection contract v1, so an existing
PLC program that reads them keeps working. `HR 10 = 0` does not mean "measured
0 mm" — read HR 11 first. Registers are written before the coil flips, under one
lock.

MQTT, `<station-name>/inspection/<stream-id>/results`, schema `2.0.0`:

```json
{"type": "assembly_inspection_result", "version": "2.0.0",
 "stream_id": "line1-pcb", "frame_id": 10423, "verdict": "NG",
 "verdict_reasons": ["missing", "dimension_out_of_tolerance"],
 "defect_count": 0,
 "assembly": {"enabled": true, "expected_count": 3, "matched_count": 2,
              "missing_count": 1, "extra_count": 1,
              "missing": [{"label": "C7-cap", "class_name": "copper",
                           "roi": [0.62, 0.10, 0.78, 0.28],
                           "min_count": 1, "expected": 1, "found": 0}]},
 "dimension": {"enabled": true, "calibrated": true, "mm_per_pixel": 0.052083,
               "out_of_tolerance_count": 1,
               "measurements": [{"name": "board_edge", "status": "oversize",
                                 "status_code": 2, "measured_long_mm": 60.42,
                                 "nominal_long_mm": 60.0, "tolerance_mm": 0.3,
                                 "deviation_mm": 0.42}]}}
```

Both sections are always present, with `enabled: false` when the module is off
for that source, so a consumer never has to test for their existence. In v2,
`verdict = NG` no longer implies `defect_count > 0`.

#### Next steps

- Replace the example expected list with your own slots, and retrain the model
  on your own images — the shipped weights find PCB copper defects, not your
  parts.
- Point `mqtt.host` at your own broker once you have one with credentials; the
  bundled mosquitto is anonymous and local by design.
- Add cameras by appending to `sources[]`, each with its own `assembly` or
  `dimension` block. Eight streams at 10 fps was the last stable point measured
  on an Orin NX 16GB, with MQTT and Modbus disabled during that test — budget
  fewer with the full I/O path in place.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The panel does not open | Confirm port 8080 is reachable from this computer; the containers use host networking, so a host firewall is the usual cause |
| Panel loads but the preview is black | The source has not connected yet; check `/healthz` for a rising `frames_processed`, then the container logs for the camera URI |
| The coil and the registers disagree | The write side is atomic; a reader that issues two Modbus requests can land between verdicts — seen at ~20 verdicts/s in testing. Poll the registers first and treat the coil as the trigger |
| Everything is NG the moment the line starts | The expected list is still the shipped example. Rebuild it for your station before drawing any conclusion |
| `dimension.enabled` is false in every event | That source has no `dimension` block; the calibration camera is a separate source in the shipped configuration |

## Preset: Camera + Raspberry Pi 5 with Hailo-8 {#hailo}

Same runtime, INT8 model, less power. The HEF is compiled off-device and
downloaded during the deploy, so there is no build step on the board. Accuracy
was checked in the Hailo emulator against the CPU baseline; throughput, latency
and stream capacity on the board itself have not been measured.

| Device | Purpose |
|--------|---------|
| Raspberry Pi 5 + Hailo-8 (M.2) | Detection on the accelerator, assembly comparison and dimension measurement on the CPU, Modbus TCP server, MQTT broker and the web panel |
| Camera | Supplies the video of the inspection station; any RTSP or ONVIF camera works, as does a USB camera or a recorded file |

**Important.** This is a demo package, not a certified metrology or safety
product; the dimension module does not replace a calibrated gauge, and the
shipped model is trained on the DeepPCB bare-board defect dataset rather than on
assembly images. On this board add one more caveat: **nothing here has been run
on a Raspberry Pi yet.** The image cross-builds for arm64 and the HEF loads in
the emulator, but the first on-board run is yours. The same three weaknesses
apply — picture-coordinate ROIs, calibration plane sensitivity, and one shared
Modbus register bank across streams.

## Step 1: Deploy the Inspection Runtime {#deploy_hailo_assembly type=docker_deploy required=true config=devices/hailo_assembly.yaml}

Checks the Hailo runtime, uploads the compose project and the configuration,
downloads and checksums the HEF, then starts the runtime and its MQTT broker.

### Prerequisites

Three of these fail late and confusingly if they are wrong, so the deploy checks
them first:

- **Python minor versions must match.** The compose file mounts the host's
  `hailo_platform` package into the container; its `_pyhailort.cpython-3XX-*.so`
  only imports under the same minor version. Compare `python3 --version` on the
  host with `docker run --rm <image> python3 -V`.
- **HailoRT must be 4.21.x**, and the driver, the user-space library and the
  Python bindings must all be that same version — the HEF was compiled by
  Dataflow Compiler 3.31.0, which pairs with HailoRT 4.21.0. Hold both packages
  (`apt-mark hold hailort hailort-pcie-driver`); holding only the driver lets an
  upgrade move the user-space library out from under it.
- **`hailo_pci` needs `force_desc_page_size=4096`.** The Pi 5 kernel uses 16 KB
  pages and the Hailo-8's maximum descriptor page is 4 KB. Without it `VDevice()`
  and `hailortcli fw-control identify` both succeed and `configure(hef)` is where
  it breaks.
- The runtime image `edge-inspection-assembly-rpi-hailo:0.1.0-dev` present on the
  device. **This tag is not published to a registry yet** — it has been
  cross-built for arm64 but never pushed. Build it on the board, or load it from
  an exported tar, or set `INSPECTION_IMAGE`.
- At least 4 GB free, `/dev/hailo0` present, and ports 1883, 502 and 8080 free.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `No /dev/hailo0` | The accelerator is not seated or the driver is not loaded; check `lspci` and `dmesg` for the PCIe link |
| `libhailort.so.4.21.0 not found` | This HEF is ABI-locked to HailoRT 4.21.x. Install that version across driver, library and bindings rather than changing the mount |
| Import of `hailo_platform` fails in the container | Host and image Python minor versions differ; rebuild the image on a matching base, or install HailoRT inside the image instead of mounting the host's |
| `configure(hef)` crashes after a clean identify | `force_desc_page_size=4096` is missing from `/etc/modprobe.d/`; add it and reboot |
| `Image ... is not on this device` | The runtime tag is not published yet; build or load it on the board |
| HEF checksum mismatch | The file is not the one this solution was evaluated with; delete it and let the step fetch again |
| No video from the camera | Test the RTSP URL in VLC first |

### Target {#hailo_remote type=remote device=hailo device_name="Raspberry Pi 5" config=devices/hailo_assembly.yaml default=true}

Deploy over SSH from this computer to a Raspberry Pi on the network.

### Target {#hailo_local type=local device=hailo device_name="Raspberry Pi 5" config=devices/hailo_assembly.yaml}

Deploy onto the machine this app is running on. Only valid when that machine is
the Raspberry Pi.

## Step 2: Set Up the Dimension Calibration {#calibrate_dimension_hailo type=manual required=false config=devices/calibrate_dimension.yaml}

Identical to the Jetson preset, with one substitution: the self-check runs
inside `edge-inspection-assembly-rpi-hailo:0.1.0-dev`. Skip this step if the
station only needs the missing-part check.

### Prerequisites

- A calibration reference in the **same plane** as the measured surface: an
  ArUco marker (`DICT_4X4_50`, id 7, 25 mm wide in the example) or any object of
  a known width, its printed size confirmed with a caliper.
- A known-good part to confirm the result against.
- The runtime already deployed, so the self-check can run inside its image.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| `check_aruco.py` exits non-zero | This OpenCV build has no `aruco` module; rebuild with `opencv-contrib-python-headless`. The pinned `opencv-python-headless==4.10.0.84` does carry it — ArUco lives in the main `objdetect` module since OpenCV 4.7, so `contrib` is not required |
| `status: uncalibrated` | The reference was not detected — check `calibration.roi`, `aruco_dict` and `aruco_id` |
| `status: not_found` | No contour large enough inside the measurement ROI; usually low contrast or the wrong window |
| Measurement is consistently off by a few percent | The reference is not in the plane of the part, or its real width differs from `ref_object_width_mm` |
| Everything reads NG at nominal size | `tolerance_mm` is tighter than the station's own measurement error |

## Step 3: Watch the Verdicts {#preview_assembly_hailo type=web_dashboard required=false config=devices/preview_assembly.yaml}

Opens the runtime's own panel on port 8080 — the same page as on the Jetson
preset, served by the same code.

### Deployment Complete

The station is running on the Hailo-8. It publishes one MQTT event per frame,
keeps the Modbus registers and coils current, and serves the panel locally.

#### Quick verification

1. Open `http://<pi-ip>:8080/healthz` and confirm `frames_processed` is
   increasing and `mqtt_rejected` stays at 0.
2. Subscribe to the results:
   `mosquitto_sub -h <pi-ip> -t '<station-name>/inspection/#' -C 5`.
   Each event must carry an `assembly` section and a `dimension` section, plus
   `verdict_reasons`.
3. Take one expected part off the fixture. `missing_count` rises,
   `verdict_reasons` gains `missing`, and `verdict` becomes `NG` even when
   `defect_count` is 0.
4. Watch the coil flip with a Modbus client on port 502, unit 1, and confirm
   HR 8 tracks the missing count you just created.
5. Record what this board actually does — frames per second at your resolution,
   and the panel's `inference_ms_avg`. No on-device numbers exist for this
   preset yet, and yours will be the first.

#### Configuring the expected-item list

Identical to the Jetson preset: `assembly` and `dimension` live per source under
`sources[]` in `config/config.json`, because the ROIs are picture coordinates.
One `expected[]` entry per part slot with `class`, `roi` (`[x1, y1, x2, y2]`
normalised to 0–1), `min_count` and `label`; `match_distance`, `min_score` and
`report_extra` control the matching. The `dimension` block carries
`calibration` (`detect: aruco`, `aruco_dict`, `aruco_id`,
`ref_object_width_mm`, `roi`) and `measurements[]` (`roi`,
`nominal_width_mm`, `nominal_height_mm`, `tolerance_mm`). `rules.ng_on_defect`,
`ng_on_missing`, `ng_on_extra` and `ng_on_dimension` decide which reasons fail a
board. Only the `model` section differs from the Jetson configuration: a `.hef`
path and `accelerator: hailo`.

#### Reading the outputs

The register map and the MQTT schema are the same on both presets:

| Register | Meaning |
|---|---|
| Coil 0 / Coil 1 | NG / OK, mutually exclusive |
| HR 0 / HR 1 | Primary defect class id / defect count |
| HR 2–5 | Primary bbox cx, cy, w, h, normalised x10000 |
| HR 6–7 | Heartbeat, Unix seconds as a uint32 high/low word |
| HR 8 / HR 9 | Missing count / extra count |
| HR 10 | Primary measurement in millimetres x100 (long edge) |
| HR 11 | Tolerance code: 0 ok / 1 undersize / 2 oversize / 3 not_found / 4 uncalibrated |

`HR 10 = 0` does not mean "measured 0 mm" — read HR 11 first. MQTT publishes
schema `2.0.0` on `<station-name>/inspection/<stream-id>/results`, with the
`assembly` and `dimension` sections always present and `verdict = NG` no longer
implying `defect_count > 0`.

#### Next steps

- Replace the example expected list with your own slots and retrain on your own
  images.
- Point `mqtt.host` at a broker with credentials; the bundled mosquitto is
  anonymous and local.
- Before adding streams, measure one. The multi-stream figures on the intro page
  are from the Jetson preset and do not transfer to this board.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The panel does not open | Confirm port 8080 is reachable; host networking means a host firewall is the usual cause |
| Panel loads but the preview is black | The source has not connected; check `/healthz` for a rising `frames_processed`, then the container logs |
| The coil and the registers disagree | The write side is atomic; a reader issuing two Modbus requests can land between verdicts. Poll the registers first and treat the coil as the trigger |
| Frame rate is far below the Jetson figures | Expected — those numbers are from an Orin NX with a TensorRT engine. Measure this board and use its own number |
| Everything is NG the moment the line starts | The expected list is still the shipped example; rebuild it for your station |
