---
name: prepare-deb-package
description: Prepare Debian packages for reCamera C++ deployment. Use when creating .deb packages for reCamera devices, configuring init scripts, or setting up binary deployment files.
allowed-tools: Read, Write, Edit, Glob, Grep, Bash
---

# Prepare Debian Packages for reCamera

Guide for creating .deb packages that deploy C++ applications to reCamera devices.

## Overview

reCamera devices run a BusyBox-based Linux system that uses:
- `opkg` for package management (not apt/dpkg)
- SysVinit for service management (not systemd)
- RISCV64 architecture (cv181x chip)

## Directory Structure

```
solutions/[solution_id]/
├── solution.yaml
├── guide.md
├── guide_zh.md
├── gallery/
├── packages/                      # Deb packages and models
│   ├── [app]-detector_x.x.x_riscv64.deb
│   └── [model].cvimodel
└── devices/
    └── recamera_[variant].yaml    # Device config
```

## Device Configuration Template

Create `devices/recamera_[variant].yaml`:

```yaml
version: "1.0"
id: recamera_yolo11
name: reCamera YOLO11 Detector
name_zh: reCamera YOLO11 检测器
type: recamera_cpp

detection:
  method: network_scan
  manual_entry: true
  requirements: []

# SSH connection config
ssh:
  port: 22
  default_user: recamera
  default_host: 192.168.42.1
  connection_timeout: 30
  command_timeout: 300

# C++ application deployment config
binary:
  # .deb package (includes init script)
  deb_package:
    path: packages/yolo11-detector_0.1.1_riscv64.deb
    name: yolo11-detector
    includes_init_script: true    # deb contains /etc/init.d/K92yolo11-detector

  # Model files (kept out of the .deb — see "Models: never ship inside the .deb" below)
  models:
    - path: packages/model.cvimodel
      target_path: /userdata/local/models
      filename: model.cvimodel

  # Service configuration
  service_name: yolo11-detector
  service_priority: 92            # K92yolo11-detector — K prefix, not S (see below)

  auto_start: true

# actions.after: write deployment-time parameters (MQTT host/port, thresholds, …)
# to /etc/<name>.conf. The init script sources this file at start, so the
# app must read it — there is no separate `mqtt_config:` block (see below).
actions:
  after:
    - name: Generate detector config
      run: |
        set -e
        cat > /etc/yolo11-detector.conf << EOF
        MQTT_HOST="{{mqtt_host}}"
        MQTT_PORT="{{mqtt_port}}"
        EOF
      sudo: true

> **Cloud materials**: `deb_package.path` and `models[].path` accept URLs (e.g., `https://cdn.example.com/package.deb`). Files are automatically downloaded and cached before deployment.
>
> **No `mqtt_config:` / `conflict_services:` blocks.** Older revisions of this skill and
> device yamls used those two top-level `binary.*` blocks. Neither exists in the shipping
> reference (`solutions/recamera_ecosystem/devices/apps/recamera_yolo11.yaml`):
> MQTT/threshold parameters go through `actions.after` writing `/etc/<name>.conf` (see
> above), and conflicting-service handling is done inside the init script itself
> (`stop_conflicting_services()`), not declared in the device yaml. In particular, never
> put `sscma-supervisor` in a stop/disable list: it is the sole boot-time orchestrator
> (`S93sscma-supervisor` runs `app_restore` to start whichever gallery app was last
> selected) — disabling it leaves the device with nothing to start at boot. See
> `recamera_yolo11.yaml:107-123` for the actual comment explaining this.

# User inputs
user_inputs:
  - id: host
    name: Device IP Address
    name_zh: 设备 IP 地址
    type: text
    default: "192.168.42.1"
    required: true
    validation:
      pattern: "^\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}$"

  - id: password
    name: SSH Password
    name_zh: SSH 密码
    type: password
    default: "recamera"
    required: true

# Deployment steps (shown to user)
steps:
  - id: connect
    name: SSH Connect
    name_zh: SSH 连接
  - id: precheck
    name: Check Device State
    name_zh: 检查设备状态
  - id: prepare
    name: Stop Conflicting Services
    name_zh: 停止冲突服务
  - id: transfer
    name: Transfer Files
    name_zh: 传输文件
  - id: install
    name: Install Package
    name_zh: 安装软件包
  - id: models
    name: Deploy Model
    name_zh: 部署模型
  - id: mqtt
    name: Configure MQTT
    name_zh: 配置 MQTT
  - id: disable
    name: Disable Conflicts
    name_zh: 禁用冲突服务
  - id: start
    name: Start Service
    name_zh: 启动服务
  - id: verify
    name: Verify
    name_zh: 验证

post_deployment:
  open_browser: false
```

## Creating the .deb Package

### Package Structure

```
yolo11-detector_0.1.1_riscv64/
├── DEBIAN/
│   ├── control
│   └── postinst
├── usr/
│   └── local/
│       └── bin/
│           └── yolo11-detector   # The compiled binary
└── etc/
    └── init.d/
        └── K92yolo11-detector    # SysVinit script — K prefix, not S (see below)
```

> **`/usr/local/bin`, not `/usr/bin`.** `cmake/package.cmake:32` installs the target to
> `${CMAKE_INSTALL_PREFIX}/bin`, and every shipping gallery-app package (face-analysis,
> weather-classifier, fall-detection, yolo-detector, …) puts its binary under
> `/usr/local/bin/`.

### DEBIAN/control

```
Package: yolo11-detector
Version: 0.1.1
Architecture: riscv64
Maintainer: Seeed Studio <support@seeed.cc>
Description: YOLO11 object detector for reCamera
 Detects objects using YOLO11 model and publishes to MQTT.
```

### DEBIAN/postinst

```bash
#!/bin/sh
chmod +x /usr/local/bin/yolo11-detector
chmod +x /etc/init.d/K92yolo11-detector
exit 0
```

### SysVinit Script Template

Create `etc/init.d/K92yolo11-detector`. **The `K` prefix is required, not `S`**: `rcS` only
runs `/etc/init.d/S*` at boot, and all 12 official gallery apps
(depth-estimation, detection-blur, face-analysis, face-recognition, facemesh-reader,
fall-detection, fitness-trainer, ppocr-reader, qrcode-reader, retail-vision,
weather-classifier, yolo-detector — verified under
`sscma-example-sg200x/solutions/*/rootfs/etc/init.d/`) ship `K92<name>`, never `S92<name>`.
Only system services keep an `S` prefix (`S91sscma-node`, `S93sscma-supervisor`,
`S41bt-init`). A gallery app started via `S*` would autostart at boot and race
`sscma-supervisor`'s `app_restore` for VPSS/camera ownership — appMgr is single-active
(one `active_script` at a time) and is the only thing that should decide which app runs;
`solutions/face-recognition/control/postinst` explicitly does
`rm -f /etc/init.d/S92face-recognition` to enforce this. Boot autostart of *some* app is
still handled: `S93sscma-supervisor` starts and asynchronously runs `main.sh app_restore`,
which reads the last-selected app from `/userdata/local/apps/state.json` and calls that
app's `K92<name> start` directly (SysVinit's own boot sequence skips `K*` scripts, but
appMgr invokes them by path).

The `stop()` action below must also do more than kill the process: the daemon owns
`/dev/ion` and `/dev/cvi-*` (camera + TPU), and the kernel-side release of those nodes is
asynchronous — "process gone" is a necessary but not sufficient condition. `main.sh`'s
`_app_do_stop` treats `stop`'s exit code 0 as an authoritative "camera owner released"
signal and uses it to decide whether to start the next gallery app; reporting 0 while the
process is still alive (or while VPSS/ION isn't actually free) can hand the camera to two
owners at once. `app_start`/`app_stop` each run under a **15-second** timeout budget
(`_app_run_timeout 15`), so `stop()` must reach a verdict — success or failure — well
inside that window.

```bash
#!/bin/sh

NAME="yolo11-detector"
DAEMON="/usr/local/bin/yolo11-detector"
PIDFILE="/var/run/${NAME}.pid"
LOGFILE="/var/log/${NAME}.log"

# Load solution-specific config written by actions.after (see device yaml above)
[ -f /etc/${NAME}.conf ] && . /etc/${NAME}.conf

# Model and config paths
MODEL_PATH="/userdata/local/models/yolo11n_detection_cv181x_int8.cvimodel"
MQTT_HOST="${MQTT_HOST:-localhost}"
MQTT_PORT="${MQTT_PORT:-1883}"

# Existing ION / CVI device nodes. Camera and TPU sit behind these; if a
# stopped process never releases them, the next app's device_init never comes
# up. Node names are /dev/cvi-* (hyphen, not underscore) — get this wrong and
# the check silently always passes.
cvi_device_list() {
    for d in /dev/ion /dev/cvi-*; do
        [ -e "$d" ] && printf '%s ' "$d"
    done
}

# Who still holds these nodes open. Empty = nobody.
cvi_device_holders() {
    devs=$(cvi_device_list)
    [ -z "$devs" ] && return 0
    fuser $devs 2>/dev/null | tr -s ' \t' ' ' | sed 's/^ *//; s/ *$//'
}

# "Process gone" != "driver has released VPSS/VENC/ION" (kernel-side release
# is async), so poll for the real criterion after the process disappears.
wait_devices_released() {
    budget=$1
    i=0
    limit=$((budget * 2))
    while [ $i -lt $limit ]; do
        [ -z "$(cvi_device_holders)" ] && return 0
        sleep 0.5
        i=$((i + 1))
    done
    [ -z "$(cvi_device_holders)" ] && return 0
    echo "$NAME: camera/ION still held after ${budget}s"
    return 1
}

start() {
    echo "Starting $NAME..."
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "$NAME already running"
        return 0
    fi

    $DAEMON \
        --model "$MODEL_PATH" \
        --mqtt-host "$MQTT_HOST" \
        --mqtt-port "$MQTT_PORT" \
        > "$LOGFILE" 2>&1 &

    echo $! > "$PIDFILE"
    echo "$NAME started (PID: $(cat $PIDFILE))"
}

stop() {
    echo "Stopping $NAME..."
    if [ ! -f "$PIDFILE" ]; then
        echo "$NAME is not running"
        return 0
    fi
    PID=$(cat "$PIDFILE" 2>/dev/null)
    [ -z "$PID" ] && { rm -f "$PIDFILE"; echo "$NAME is not running"; return 0; }

    # Send TERM, then wait for the process to actually exit — releasing
    # VPSS/camera (stopStream, RTSP/VENC deinit) can take seconds. Reporting
    # OK before it's gone lets the next app start while this one still owns
    # the camera -> VPSS collision / kernel oops.
    kill "$PID" 2>/dev/null
    i=0
    while [ $i -lt 16 ]; do            # up to ~8s graceful (16 x 0.5s)
        [ -d "/proc/$PID" ] || break
        sleep 0.5
        i=$((i + 1))
    done
    if [ -d "/proc/$PID" ]; then
        kill -KILL "$PID" 2>/dev/null
        j=0
        while [ $j -lt 6 ]; do          # up to ~3s after KILL
            [ -d "/proc/$PID" ] || break
            sleep 0.5
            j=$((j + 1))
        done
    fi
    if [ -d "/proc/$PID" ]; then
        echo "$NAME failed to stop (PID $PID still alive)"
        return 1
    fi
    rm -f "$PIDFILE"

    # Process gone is only necessary; the device nodes are what actually get
    # handed to the next app. Total stop() budget must stay well under the
    # app_stop 15s timeout — the process-exit wait above already used most of it.
    wait_devices_released 5 || return 1
    echo "$NAME stopped"
    return 0
}

status() {
    if [ -f "$PIDFILE" ] && kill -0 $(cat "$PIDFILE") 2>/dev/null; then
        echo "$NAME is running (PID: $(cat $PIDFILE))"
    else
        echo "$NAME is not running"
        return 1
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0
```

> **Reference implementation**: `edge-waste-sorting/platforms/cvi/waste-sorting/rootfs/etc/init.d/K92waste-sorting`
> has the full production version of this pattern (dynamic conflicting-service enumeration,
> a shared `RELEASE_BUDGET` across both `stop_conflicting_services()` and the post-stop
> device-release wait, and a ready-file based start criterion). The template above is a
> minimal illustration of the same "wait for exit, then verify device release, only then
> return 0" contract — do not ship the old `kill; rm pidfile; killall; return 0` pattern
> shown in earlier revisions of this skill, which never verified the camera was actually
> free and could report success while it was still held.

### Build Commands

```bash
# Set permissions
chmod +x yolo11-detector_0.1.1_riscv64/DEBIAN/postinst
chmod +x yolo11-detector_0.1.1_riscv64/etc/init.d/K92yolo11-detector

# Build package
dpkg-deb --build yolo11-detector_0.1.1_riscv64
```

> **macOS note**: `dpkg-deb` is not bundled with macOS. Install it first: `brew install dpkg`.

## Service Priority Reference

| Priority | Service | Prefix |
|----------|---------|--------|
| 03 | node-red | `S` (system, autostarts) |
| 41 | bt-init | `S` (system, autostarts) |
| 91 | sscma-node | `S` (system, autostarts) |
| 92 | gallery apps (yolo-detector, face-analysis, depth-estimation, …) | `K` (appMgr-managed, never autostarts) |
| 93 | sscma-supervisor | `S` (system, boot orchestrator — never stop/disable it) |

## Deployment Flow

1. **Pre-check**: Detect current device state (Node-RED/C++/Clean) — supervisor and `opkg`
   must both be present; otherwise refuse (do not fall back to a self-written `S92` script,
   since that creates two competing answers for "who owns boot").
2. **Transfer**: Upload the `.deb` and model files to `/userdata` on the device (the
   supervisor installer only operates on files under `/userdata`).
3. **Install**: run the supervisor's own installer, `main.sh app_install`, which internally
   does `_app_run_timeout 120 opkg install --force-reinstall "$deb"`
   (`solutions/supervisor/rootfs/usr/share/supervisor/scripts/main.sh:1484`) — do not call
   `opkg install` directly against a path under `/tmp`; that bypasses the market
   registration `app_install` also performs.
4. **Deploy models**: Copy to `/userdata/local/models/` (models are never bundled inside
   the `.deb` — see below).
5. **Configure**: `actions.after` writes deployment-time parameters (MQTT host/port,
   thresholds, …) to `/etc/<name>.conf`, which the init script sources at start.
6. **Start service**: appMgr calls the `K92<name>` init script's `start` action.
7. **Verify**: Check service status.

## Update guide.md

Add deployment step:

```markdown
## Step 2: Deploy YOLO Detector {#deploy_yolo type=recamera_cpp required=true config=devices/recamera_yolo11.yaml}

Deploy the YOLO11 object detector to reCamera.

### Wiring

![Connect reCamera](gallery/recamera_connect.png)

1. Connect reCamera to computer via USB or ensure on same network
2. Enter reCamera IP address (default: 192.168.42.1 for USB)
3. Enter SSH password (default: recamera)
4. Click Deploy button

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Check IP and password, try 'recamera' or 'recamera.2' |
| Package install failed | Device may have incompatible version, contact support |
| Service won't start | Check logs: `cat /var/log/yolo11-detector.log` |
```

## Testing on Device

```bash
# SSH into reCamera
ssh recamera@192.168.42.1

# Check installed packages
opkg list-installed | grep yolo

# Check service status
/etc/init.d/K92yolo11-detector status

# View logs
cat /var/log/yolo11-detector.log

# Check MQTT output
mosquitto_sub -h localhost -t "sscma/v0/#" -v
```

## Packaging Discipline: One App, One K Script, One Process

- **One gallery app = one `K92<name>` init script = one set of processes it starts and
  stops itself, tracked by its own pidfile(s).** appMgr is single-active (one
  `active_script` in `/userdata/local/apps/state.json` at a time); a script that calls
  another app's init script, or kills by process-name pattern instead of its own pidfile,
  breaks that accounting and can hand the camera to two apps at once. See
  `unmanned-store-access-deb/docs/SPEC.md:408-450` (§14.3, "一个受管应用，两个进程") for a
  worked example of a single `K92<name>` script that owns two of its own cooperating
  processes.
- **Each package must be self-contained and mutually exclusive with any package it
  overlaps with.** Two apps that both want the camera/VPSS cannot coexist; declare
  `Conflicts: <other-package>` and `Replaces: <other-package>` in `DEBIAN/control` for any
  same-class package, and re-check with `opkg list-installed` in `preinst` since not all
  `opkg` versions enforce `Conflicts` consistently
  (`unmanned-store-access-deb/docs/SPEC.md:346-364`, §14.1).
- **Models are never bundled inside the `.deb`.** They are declared in the device yaml's
  `binary.models[]` and deployed to `/userdata/local/models` as a separate transfer step,
  the same way `recamera_yolo11.yaml:30-55` does it. Two independent reasons: (1) `/`'s
  root filesystem has very little headroom on reCamera (root partition observed at ~92%
  full), and (2) **`opkg` deletes files an upgraded/removed package owns** — if a model
  ships inside the `.deb`, an upgrade or `opkg remove` of that package deletes the model
  file even if another package (or a re-flash) still needs it. Confirmed in practice:
  `edge-waste-sorting-deb/evaluation/runs/2026-09-07-recamera-deb/results.md` §8.1 moved
  a bundled `.cvimodel` out of the package (8.67 MB) specifically to fix this, shrinking
  the `.deb` from 6,646,894 B to 345,974 B.

## Reference Solutions

- `solutions/recamera_ecosystem/` — see `devices/apps/recamera_yolo11.yaml` (`type: recamera_cpp`, ships a `.cvimodel` + `binary.deb_package.path`, YOLO11/YOLO26/YOLO8 variants).
  - **Note**: in the real solution the `.deb` and `.cvimodel` are served from a **CDN URL** (e.g. `https://sensecraft-statics.seeed.cc/.../yolo-detector_0.1.1_riscv64.deb`) rather than committed under `packages/`. Both `deb_package.path` and `models[].path` accept URLs — files are downloaded and cached before deployment (the `packages/` layout shown above is just the local-files alternative).
