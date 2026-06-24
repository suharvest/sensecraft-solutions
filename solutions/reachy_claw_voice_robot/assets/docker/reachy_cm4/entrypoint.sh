#!/bin/sh
# Reachy Voice entrypoint (+ daemon-readiness wait).
#
# The Reachy Mini USB sound card resets its PCM playback mixer to -23dB on every
# host reboot (inaudible). It exposes TWO PCM controls ('PCM',0 and 'PCM',1) —
# the SECOND one holds the -23dB attenuation, so both must be raised (plain
# `sset PCM` only touches the first → speaker stays quiet). Find the card by
# name (index moves: hw:0 vs hw:2) and set both before starting.
#
# SPEAKER VOLUME: lower 'PCM',1 below 100% to reduce loudness (on this card
# 85% ~= -9dB). Keep 'PCM',0 at 100%.
CARD=$(awk '/Reachy Mini Audio/{print $1; exit}' /proc/asound/cards 2>/dev/null)
if [ -n "$CARD" ]; then
    amixer -c "$CARD" sset "'PCM',0" 100% unmute >/dev/null 2>&1
    amixer -c "$CARD" sset "'PCM',1" 100% unmute >/dev/null 2>&1
    amixer -c "$CARD" sset PCM 100% unmute >/dev/null 2>&1
    echo "entrypoint: card $CARD PCM mixer set"
else
    echo "entrypoint: Reachy USB card not found in /proc/asound/cards (continuing)"
fi

# Wait for the reachy-daemon before starting, so a cold boot (daemon still
# initialising / waking the robot) does not crash-race the SDK connection and
# require a manual restart. host network -> daemon on :38001.
DAEMON_PORT="${REACHY_DAEMON_PORT:-38001}"
python3 - "$DAEMON_PORT" <<'PY'
import socket, sys, time
port = int(sys.argv[1])
deadline = time.monotonic() + 120          # cap the wait at 2 min
while time.monotonic() < deadline:
    try:
        socket.create_connection(("localhost", port), 2).close()
        print(f"entrypoint: reachy-daemon reachable on :{port}")
        break
    except OSError:
        print(f"entrypoint: waiting for reachy-daemon on :{port} ...")
        time.sleep(2)
else:
    print("entrypoint: daemon wait timed out (120s), starting anyway")
PY
# Extra grace so the daemon finishes waking the robot (HTTP up precedes the
# robot-connection by ~1-2s; the SDK connect needs the robot ready).
sleep 5

exec python3 -m reachy_voice.main
