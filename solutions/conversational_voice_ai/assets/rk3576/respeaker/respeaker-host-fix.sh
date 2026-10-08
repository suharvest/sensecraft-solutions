#!/bin/bash
# reSpeaker XVF3800 host fix for the reComputer RK3576 devkit (Seeed reSpeaker
# 4-Mic Array, USB 2886:001a, ALSA card id "Array").
#
# Two field problems this solves:
#
# 1. Speaker too quiet. ovs-agent opens /dev/snd/pcmC?D0{p,c} directly and
#    holds them exclusively, so PipeWire never creates a sink for this card
#    and the desktop volume slider has no effect on the assistant's audio.
#    The real knob is the USB Audio Class feature unit: 'PCM',0 (stereo) and
#    'PCM',1 (mono). Measured: 62% = -23 dB (bad shipped default), 85% = -9 dB,
#    100% = 0 dB. We pin 85%.
#
# 2. Mic array sometimes not on the bus after boot. A long capture stream can
#    make the vendor xHCI emit a storm of "buffer overrun" warnings, the device
#    drops, and the self-powered onboard Genesys hub chain latches a bad
#    downstream-port state. The latch survives reboots (the hubs are self-
#    powered and the DT reset line is a gpio-hog driven high once), so
#    "sometimes offline after boot" is really "still wedged from last time".
#    Only pulsing the DT usb_hub_reset line clears it. We install a boot
#    self-heal unit plus a 60 s watchdog timer that do exactly that.
#
# Idempotent: safe to re-run on every deploy. DRY_RUN=1 prints every path and
# command instead of touching the system. DT_ROOT overrides the device-tree
# root for offline testing of the reset-line detection.
set -u

DRY_RUN="${DRY_RUN:-0}"
DT_ROOT="${DT_ROOT:-/proc/device-tree}"
# Kernel-resolved GPIO view used to locate the usb_hub_reset line (override for tests).
GPIO_DEBUGFS="${GPIO_DEBUGFS:-/sys/kernel/debug/gpio}"

WARNINGS=""
installed_paths=""
enabled_units=""
HUB_BASE=""
HUB_LINE=""

warn() { WARNINGS="${WARNINGS}${1}
"; echo "WARN: $1" >&2; }

run() {
    if [ "$DRY_RUN" = 1 ]; then
        echo "[dry-run] $*"
    else
        "$@"
    fi
}

# install_file <tmp-file> <dest> <mode>
# Only rewrite when the content actually differs, so a re-run does not
# invalidate units/rules that systemd/udev already have loaded.
install_file() {
    local src="$1" dest="$2" mode="$3"
    if [ -f "$dest" ] && cmp -s "$src" "$dest"; then
        echo "unchanged: $dest"
    else
        if [ "$DRY_RUN" = 1 ]; then
            echo "[dry-run] install -m $mode $src $dest"
        else
            install -m "$mode" "$src" "$dest" || { echo "ERROR: cannot install $dest" >&2; exit 1; }
            echo "installed: $dest"
        fi
    fi
    installed_paths="${installed_paths}${dest}
"
}

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
if [ "$(id -u)" != 0 ] && [ "$DRY_RUN" != 1 ]; then
    echo "ERROR: must run as root (sudo)" >&2
    exit 1
fi

if ! command -v amixer >/dev/null 2>&1; then
    warn "amixer (alsa-utils) not found - the mixer part is skipped; install alsa-utils and re-run"
    HAVE_MIXER=0
else
    HAVE_MIXER=1
fi

STAGE="$(mktemp -d)"
# KEEP_STAGE=1 keeps the staged files (used to bash -n the generated scripts in CI).
trap 'if [ -n "${KEEP_STAGE:-}" ]; then echo "stage kept: $STAGE"; else rm -rf "$STAGE"; fi' EXIT

# ---------------------------------------------------------------------------
# Runtime file: respeaker-volume.sh
# ---------------------------------------------------------------------------
cat > "$STAGE/respeaker-volume.sh" <<'EOF'
#!/bin/bash
# reSpeaker XVF3800 (USB 2886:001a, ALSA card id "Array") playback level.
#
# Why a script: the voice agent (ovs-agent) opens /dev/snd/pcmC?D0{p,c} directly
# and holds it exclusively, so PipeWire can never create a sink for this card and
# the desktop volume slider has no effect on the assistant's audio.  The UAC
# feature unit ('PCM',0 / 'PCM',1) is the real knob.
#
# Use the card *id* "hw:Array", never an index: the index moves around with
# enumeration order, and when the device is absent `amixer -c 3` fails with the
# misleading "Invalid card number" while `-D hw:Array` is simply "no such card"
# and starts working the moment the device re-enumerates.
#
# Override with RESPEAKER_VOLUME (e.g. "90%") if the pinned 85% is not right.
LEVEL="${RESPEAKER_VOLUME:-85%}"
CARD="hw:Array"

for _ in $(seq 1 30); do
    if amixer -q -D "$CARD" sset "PCM",0 "$LEVEL" unmute >/dev/null 2>&1; then
        amixer -q -D "$CARD" sset "PCM",1 "$LEVEL" unmute >/dev/null 2>&1
        sleep 5          # let wireplumber / the voice agent settle
        amixer -q -D "$CARD" sset "PCM",0 "$LEVEL" unmute >/dev/null 2>&1
        amixer -q -D "$CARD" sset "PCM",1 "$LEVEL" unmute >/dev/null 2>&1
        echo "reSpeaker mixer -> $LEVEL ($(amixer -D "$CARD" | grep -m1 'Front Left' | sed 's/^ *//'))"
        exit 0
    fi
    sleep 1
done

echo 'reSpeaker card "Array" did not show up within 30s'
exit 1
EOF

# ---------------------------------------------------------------------------
# udev rules
# ---------------------------------------------------------------------------
cat > "$STAGE/89-respeaker-volume.rules" <<'EOF'
# reSpeaker XVF3800 -> (re)apply the mixer level on every enumeration
ACTION=="add", SUBSYSTEM=="sound", ATTRS{idVendor}=="2886", ATTRS{idProduct}=="001a", TAG+="systemd", ENV{SYSTEMD_WANTS}+="respeaker-volume.service"
EOF

cat > "$STAGE/90-usb-no-autosuspend.rules" <<'EOF'
# Keep runtime PM away from the reSpeaker XVF3800 and its hub chain: the chain has
# shown "Failed to suspend device, error -71" and suspend/resume churn on a bus that
# already drops this device under load.
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{idVendor}=="2886", ATTR{idProduct}=="001a", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{idVendor}=="05e3", ATTR{idProduct}=="0610", ATTR{power/control}="on"
EOF

# ---------------------------------------------------------------------------
# respeaker-volume.service (udev-triggered, so no [Install] section)
# ---------------------------------------------------------------------------
cat > "$STAGE/respeaker-volume.service" <<'EOF'
[Unit]
Description=Set reSpeaker XVF3800 mixer level (85%%) and unmute
After=sound.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/respeaker-volume.sh
EOF

# ---------------------------------------------------------------------------
# Locate the usb_hub_reset line and its GPIO controller base.
#
# Only the reComputer RK3576 devkit has this line; other RK3576 boards get a
# clear message and the volume part only.
#
# Primary source is the kernel's own resolved view in /sys/kernel/debug/gpio,
# because the device-tree gpio-hog "gpios" property is easy to misread: per the
# DT binding it stores controller-local <line flags> pairs ("an integer multiple
# of the number of cells specified in its parent node (#gpio-cells)"), i.e. no
# phandle, so the second cell is the *flags*, not the line. Parsing the resolved
# view removes that ambiguity; the DT parse is only a fallback.
# ---------------------------------------------------------------------------
cat > "$STAGE/detect-hub-line.py" <<'PY'
#!/usr/bin/env python3
"""Print "<base> <line> <source>" for the usb_hub_reset gpio-hog, or nothing."""
import os
import re
import struct
import sys

DT_ROOT = sys.argv[1] if len(sys.argv) > 1 else "/proc/device-tree"
DEBUGFS = sys.argv[2] if len(sys.argv) > 2 else "/sys/kernel/debug/gpio"

CHIP = re.compile(r"GPIOs\s+(\d+)-(\d+),\s*parent:\s*platform/([0-9a-fA-F]+)\.")
# Indented <gpio-N ... > row whose label is the hog's line name. The kernel
# renders it as "(consumer |line-name )"; match the name without requiring the
# pipe so an older/newer rendering cannot silently hide the line.
HOG = re.compile(r"^\s*gpio-(\d+)\b.*usb_hub_reset")


def from_debugfs():
    """Kernel-resolved view: unambiguous line number and controller base."""
    try:
        with open(DEBUGFS) as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    start = None
    base = None
    for line in lines:
        if not line[:1].isspace():
            match = CHIP.search(line)
            if match:
                start = int(match.group(1))
                base = "0x" + match.group(3).lower()
            continue
        match = HOG.match(line)
        if not match or start is None or base is None:
            continue
        if "out hi" not in line:
            print("usb_hub_reset is not driven high in %s - skipping" % DEBUGFS,
                  file=sys.stderr)
            return None
        return base, int(match.group(1)) - start, "debugfs"
    return None


def from_dt():
    """Fallback: controller-local (line, flags) pairs; tolerate a phandle form."""
    pattern = os.path.join(DT_ROOT, "pinctrl", "gpio@*", "usb-hub-reset-hog")
    for hog in sorted(__import__("glob").glob(pattern)):
        try:
            name = open(os.path.join(hog, "line-name"), "rb").read()
        except OSError:
            continue
        if name.decode(errors="ignore").strip("\0").strip() != "usb_hub_reset":
            continue
        node = os.path.basename(os.path.dirname(hog))
        if "@" not in node:
            continue
        base = "0x" + node.split("@", 1)[1]
        try:
            data = open(os.path.join(hog, "gpios"), "rb").read()
        except OSError:
            continue
        cells = struct.unpack(">%dI" % (len(data) // 4), data) if data else ()
        if len(cells) >= 2 and len(cells) % 2 == 0:
            return base, cells[0], "dt-pairs"
        if len(cells) >= 3 and len(cells) % 3 == 0:
            return base, cells[1], "dt-phandle"
    return None


found = from_debugfs() or from_dt()
if found:
    print("%s %d %s" % found)
PY

BOARD_HAS_HUB_LINE=0
HAVE_PYTHON=1
if ! command -v python3 >/dev/null 2>&1; then
    warn "python3 not found - the USB recovery watchdog is skipped"
    HAVE_PYTHON=0
fi

HUB_SOURCE=none
if [ "$HAVE_PYTHON" = 1 ] && HUB_DETECT="$(python3 "$STAGE/detect-hub-line.py" "$DT_ROOT" "$GPIO_DEBUGFS")" \
   && [ -n "$HUB_DETECT" ]; then
    HUB_BASE="$(echo "$HUB_DETECT" | cut -d' ' -f1)"
    HUB_LINE="$(echo "$HUB_DETECT" | cut -d' ' -f2)"
    HUB_SOURCE="$(echo "$HUB_DETECT" | cut -d' ' -f3)"
    case "$HUB_BASE:$HUB_LINE" in
        0x*:[0-9]*) BOARD_HAS_HUB_LINE=1 ;;
        *) warn "unusable usb_hub_reset detection (\"$HUB_DETECT\") - skipping the watchdog" ;;
    esac
else
    [ "$HAVE_PYTHON" = 1 ] && echo "this board has no usb_hub_reset line - the USB recovery watchdog is skipped"
fi

# ---------------------------------------------------------------------------
# Hub recovery runtime files (only when the board has the reset line)
# ---------------------------------------------------------------------------
if [ "$BOARD_HAS_HUB_LINE" = 1 ]; then
    cat > "$STAGE/hub-reset.py" <<EOF
#!/usr/bin/env python3
"""Pulse the RK3576 devkit usb_hub_reset line (auto-detected base/line).

The onboard Genesys hub chain occasionally latches a bad downstream-port state:
ports then report "Cannot enable. Maybe the USB cable is bad?" / error -71 and the
reSpeaker never comes back.  Neither a warm reboot nor an xhci controller rebind
clears it -- only asserting the hub RESET_N does.  The latch even survives
reboots because the hubs are self-powered and the DT line is a gpio-hog driven
high once at boot, so libgpiod/sysfs cannot drive it; poke the GPIO data
register through /dev/mem instead.

The write uses the masked form 0xFFFF0000|value, which works under both the
direct-write and the write-masked Rockchip register semantics.
"""
import argparse
import mmap
import os
import struct
import sys
import time

DEFAULT_BASE = int("${HUB_BASE}", 16)
DEFAULT_LINE = int("${HUB_LINE}")

def regs(line):
    # DW GPIO: DR/DDR at 0x0000/0x0008 for bits 0-15, 0x0004/0x000C for 16-31.
    if line < 16:
        return 0x0000, 0x0008, line
    return 0x0004, 0x000C, line - 16

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=lambda s: int(s, 0), default=DEFAULT_BASE)
    ap.add_argument("--line", type=lambda s: int(s, 0), default=DEFAULT_LINE)
    args = ap.parse_args()
    dr_off, ddr_off, bit = regs(args.line)

    fd = os.open("/dev/mem", os.O_RDWR | os.O_SYNC)
    mem = mmap.mmap(fd, 0x1000, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE,
                    offset=args.base)

    def rd(off):
        return struct.unpack("<I", mem[off:off + 4])[0]

    def wr(off, val):
        mem[off:off + 4] = struct.pack("<I", val)

    ddr, dr = rd(ddr_off), rd(dr_off)
    print("DDR=0x%08x DR=0x%08x" % (ddr, dr), flush=True)
    # Safety: only pulse a line that is already an output driven high (that is
    # the idle state the gpio-hog left it in). Never reconfigure random pins.
    if not (ddr & (1 << bit)):
        sys.exit("abort: gpio line is not configured as an output")
    if not (dr & (1 << bit)):
        sys.exit("abort: gpio line is not high, refusing to poke")

    def wr_half(bit_set):
        # The write mask deliberately covers the whole 16-bit half: that form
        # is correct under both the direct-write and the write-masked Rockchip
        # register semantics (a single-bit mask would silently fail or write
        # zeros on a direct-write IP). Because the mask is the whole half, the
        # value half must be fresh: re-read DR here so pins that another
        # driver changed during our sleep are written back with their current
        # level, not the stale pre-sleep snapshot. Only the instant of this
        # 32-bit store itself can be lost to a concurrent writer.
        cur = rd(dr_off) & 0xFFFF
        if bit_set:
            cur |= (1 << bit)
        else:
            cur &= ~(1 << bit)
        wr(dr_off, 0xFFFF0000 | cur)

    wr_half(False)                 # assert RESET_N (drive the hog's line low)
    time.sleep(1.5)
    wr_half(True)                  # release RESET_N (back to the hog's high)
    time.sleep(0.5)
    print("final DR=0x%08x" % rd(dr_off), flush=True)

if __name__ == "__main__":
    main()
EOF

    cat > "$STAGE/respeaker-recover.sh" <<'EOF'
#!/bin/bash
# Boot-time self-heal for the reSpeaker XVF3800.
#
# If the device is not enumerated (wedge hub port / unplugged), pulse the devkit
# usb_hub_reset line and wait for it to come back; then apply the mixer level.
# Completely harmless when the device is simply unplugged: it just logs and exits.
TRIES="${TRIES:-3}"
VOLUME=/usr/local/sbin/respeaker-volume.sh
ID="${RESPEAKER_ID:-2886:001a}"
USB_SYSFS="${USB_SYSFS:-/sys/bus/usb/devices}"   # overridable for off-device testing

# Scan sysfs instead of calling lsusb: usbutils is not guaranteed to be
# installed, and a missing lsusb makes every presence check report "absent",
# which would pulse a perfectly healthy bus on every boot.
present() {
    local d="${USB_SYSFS%/}" vid="${ID%%:*}" pid="${ID##*:}"
    for d in "$d"/*/; do
        [ -f "$d/idVendor" ] || continue
        [ "$(cat "$d/idVendor")" = "$vid" ] || continue
        [ "$(cat "$d/idProduct" 2>/dev/null)" = "$pid" ] || continue
        return 0
    done
    return 1
}

for i in $(seq 1 "$TRIES"); do
    if present; then
        echo "reSpeaker already present (attempt $i)"
        exec "$VOLUME"
    fi
    echo "attempt $i: reSpeaker missing -> pulsing usb_hub_reset"
    /usr/local/sbin/hub-reset.py || exit 1
    for _ in $(seq 1 10); do
        sleep 1
        present && break
    done
done

if present; then
    exec "$VOLUME"
fi
echo "reSpeaker still missing after $TRIES hub resets - check the cable / USB port"
exit 1
EOF

    cat > "$STAGE/respeaker-watch.sh" <<'EOF'
#!/bin/bash
# Runtime watchdog: if the reSpeaker XVF3800 disappears from the USB bus, pulse the
# devkit usb_hub_reset line to un-wedge the hub port and re-apply the mixer level.
# Rate limited, log-only when it can't help. Runs from respeaker-watch.timer (60s).
ID="${RESPEAKER_ID:-2886:001a}"
DRY_RUN="${DRY_RUN:-0}"
USB_SYSFS="${USB_SYSFS:-/sys/bus/usb/devices}"   # overridable for off-device testing
MISS=/run/respeaker-watch.miss
LAST=/run/respeaker-watch.lastreset
MIN_MISS="${MIN_MISS:-2}"          # consecutive misses (~2 * 60s) before acting
COOLDOWN="${COOLDOWN:-600}"        # at most one hub reset per 10 min

# Scan sysfs instead of calling lsusb: usbutils is not guaranteed to be
# installed, and a missing lsusb makes every presence check report "absent",
# which would make this watchdog pulse a healthy bus every cooldown.
present() {
    local d="${USB_SYSFS%/}" vid="${ID%%:*}" pid="${ID##*:}"
    for d in "$d"/*/; do
        [ -f "$d/idVendor" ] || continue
        [ "$(cat "$d/idVendor")" = "$vid" ] || continue
        [ "$(cat "$d/idProduct" 2>/dev/null)" = "$pid" ] || continue
        return 0
    done
    return 1
}
log() { echo "$*"; }

if present; then
    rm -f "$MISS"
    exit 0
fi

n=$(( $(cat "$MISS" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$MISS"
log "reSpeaker $ID missing (miss $n/$MIN_MISS)"
[ "$n" -lt "$MIN_MISS" ] && exit 0

now=$(date +%s)
last=$(cat "$LAST" 2>/dev/null || echo 0)
if [ $(( now - last )) -lt "$COOLDOWN" ]; then
    log "cooldown active ($(( now - last ))s since last reset), skipping"
    exit 0
fi
echo "$now" > "$LAST"

if [ "$DRY_RUN" = 1 ]; then
    log "DRY_RUN: would pulse usb_hub_reset now"
    exit 0
fi

log "pulsing usb_hub_reset"
/usr/local/sbin/hub-reset.py || exit 1
for _ in $(seq 1 12); do
    sleep 1
    present && break
done
if present; then
    log "reSpeaker recovered from the bus"
    rm -f "$MISS"
    /usr/local/sbin/respeaker-volume.sh
else
    log "still missing after hub reset - check cable / USB port"
fi
exit 0
EOF

    cat > "$STAGE/respeaker-recover.service" <<'EOF'
[Unit]
Description=Recover reSpeaker XVF3800 USB audio at boot (hub reset + mixer level)
After=multi-user.target

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 15
ExecStart=/usr/local/sbin/respeaker-recover.sh
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
EOF

    cat > "$STAGE/respeaker-watch.service" <<'EOF'
[Unit]
Description=Watchdog for the reSpeaker XVF3800 USB audio device

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/respeaker-watch.sh
EOF

    cat > "$STAGE/respeaker-watch.timer" <<'EOF'
[Unit]
Description=Periodically check the reSpeaker XVF3800 on the USB bus

[Timer]
OnBootSec=3min
OnUnitActiveSec=60s
AccuracySec=5s

[Install]
WantedBy=timers.target
EOF
fi

# ---------------------------------------------------------------------------
# Install everything (idempotent: content compare, rewrite only on change)
# ---------------------------------------------------------------------------
CHANGED=0
install_if_changed() {  # <staged-file> <dest> <mode>
    if ! { [ -f "$2" ] && cmp -s "$1" "$2"; }; then CHANGED=1; fi
    install_file "$1" "$2" "$3"
}

if [ "$HAVE_MIXER" = 1 ]; then
    install_if_changed "$STAGE/respeaker-volume.sh" /usr/local/sbin/respeaker-volume.sh 0755
    install_if_changed "$STAGE/89-respeaker-volume.rules" /etc/udev/rules.d/89-respeaker-volume.rules 0644
    install_if_changed "$STAGE/90-usb-no-autosuspend.rules" /etc/udev/rules.d/90-usb-no-autosuspend.rules 0644
    install_if_changed "$STAGE/respeaker-volume.service" /etc/systemd/system/respeaker-volume.service 0644
else
    echo "skipped mixer files (amixer missing)"
fi

if [ "$BOARD_HAS_HUB_LINE" = 1 ]; then
    install_if_changed "$STAGE/hub-reset.py" /usr/local/sbin/hub-reset.py 0755
    install_if_changed "$STAGE/respeaker-recover.sh" /usr/local/sbin/respeaker-recover.sh 0755
    install_if_changed "$STAGE/respeaker-watch.sh" /usr/local/sbin/respeaker-watch.sh 0755
    install_if_changed "$STAGE/respeaker-recover.service" /etc/systemd/system/respeaker-recover.service 0644
    install_if_changed "$STAGE/respeaker-watch.service" /etc/systemd/system/respeaker-watch.service 0644
    install_if_changed "$STAGE/respeaker-watch.timer" /etc/systemd/system/respeaker-watch.timer 0644
    run systemctl enable respeaker-recover.service respeaker-watch.timer
    enabled_units="respeaker-recover.service respeaker-watch.timer"
fi

# ---------------------------------------------------------------------------
# Reload + trigger for current hardware + apply once now
# ---------------------------------------------------------------------------
if [ "$DRY_RUN" = 1 ]; then
    echo "[dry-run] systemctl daemon-reload"
    echo "[dry-run] udevadm control --reload-rules"
    echo "[dry-run] udevadm trigger --subsystem-match=usb --action=add"
    echo "[dry-run] udevadm trigger --subsystem-match=sound --action=add"
    if [ "$BOARD_HAS_HUB_LINE" = 1 ]; then
        echo "[dry-run] systemctl start respeaker-recover.service"
        echo "[dry-run] systemctl start respeaker-watch.timer"
    fi
    echo "[dry-run] /usr/local/sbin/respeaker-volume.sh"
else
    systemctl daemon-reload
    udevadm control --reload-rules
    # Re-play add events so the rules fire for hardware that is already present.
    udevadm trigger --subsystem-match=usb --action=add
    udevadm trigger --subsystem-match=sound --action=add
    if [ "$BOARD_HAS_HUB_LINE" = 1 ]; then
        # Start them now, not only at the next boot: this is the deploy where the
        # device may already be wedged. recover.service pulses the hub and then
        # applies the mixer level; it is a oneshot bounded by TimeoutStartSec=180.
        systemctl start respeaker-recover.service || warn "respeaker-recover.service failed to start"
        systemctl start respeaker-watch.timer || warn "respeaker-watch.timer failed to start"
    fi
    if [ "$HAVE_MIXER" = 1 ]; then
        /usr/local/sbin/respeaker-volume.sh || warn "volume script failed (device absent?)"
    fi
fi

# ---------------------------------------------------------------------------
# Summary (plain key=value for the deploy log)
# ---------------------------------------------------------------------------
# Presence via sysfs, for the same reason as the runtime scripts: no lsusb
# dependency. USB_SYSFS is overridable for off-device testing.
usb_present() {
    local d="${USB_SYSFS:-/sys/bus/usb/devices}"
    d="${d%/}"
    for d in "$d"/*/; do
        [ -f "$d/idVendor" ] || continue
        [ "$(cat "$d/idVendor")" = 2886 ] || continue
        [ "$(cat "$d/idProduct" 2>/dev/null)" = 001a ] || continue
        return 0
    done
    return 1
}

SPEAKER_LEVEL="device-not-present"
REPEAKER_PRESENT=false
usb_present && REPEAKER_PRESENT=true
if [ "$DRY_RUN" = 1 ]; then
    SPEAKER_LEVEL="dry-run"
elif [ "$HAVE_MIXER" = 1 ] && line="$(amixer -D hw:Array 2>/dev/null | grep -m1 'Front Left')"; then
    SPEAKER_LEVEL="$(echo "$line" | sed 's/^ *//;s/  */ /g')"
fi

echo ""
echo "==== respeaker host fix summary ===="
echo "dry_run=$DRY_RUN"
echo "board_has_usb_hub_reset=$BOARD_HAS_HUB_LINE"
if [ "$BOARD_HAS_HUB_LINE" = 1 ]; then
    echo "hub_reset_base=$HUB_BASE"
    echo "hub_reset_line=$HUB_LINE"
    echo "hub_reset_source=$HUB_SOURCE"
else
    echo "hub_reset_base=none"
    echo "hub_reset_line=none"
    echo "hub_reset_source=none"
fi
printf '%s' "$installed_paths" | sed '/^$/d' | sed 's/^/installed=/'
echo "speaker_level=$SPEAKER_LEVEL"
echo "reSpeaker_present=$REPEAKER_PRESENT"
echo "enabled_units=${enabled_units:-none}"
[ -z "$WARNINGS" ] || printf '%s' "$WARNINGS" | sed '/^$/d' | sed 's/^/warning=/'
echo "==================================="
exit 0
