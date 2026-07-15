#!/bin/sh
# Self-healing supervisor for the lean sheep-counter stack on the reCamera.
#
# Why: the stock sscma-node (NPU inference daemon) crashes periodically on this unit and the
# stock S91 init does not respawn it; and when sscma-node restarts, the counter's graph is gone.
# This loop keeps sscma-node up AND re-kicks the counter so it rebuilds its graph after every
# (re)start. Launched at boot by /etc/init.d/S85sscma-keepalive (PID-1 managed, so it persists).
export LD_LIBRARY_PATH=/lib:/usr/lib:/usr/lib64:/mnt/system/lib:/mnt/system/usr/lib:/mnt/system/usr/lib/3rd

# clear any stray inference daemon first
for p in $(ps | grep "/usr/local/bin/[s]scma-node" | awk '{print $1}'); do kill -9 "$p" 2>/dev/null; done
sleep 1

# Ensure NPU device is world-accessible (debugging as non-root, hot-plugged TPU)
chmod 666 /dev/cvi-tpu0 2>/dev/null

while true; do
    /usr/local/bin/sscma-node --start >>/var/log/sscma-node.log 2>&1 &
    SSCMA_PID=$!
    sleep 4                                                   # let the daemon come up
    /etc/init.d/S99sheep-counter restart >/dev/null 2>&1      # (re)build the counter's graph on the fresh daemon
    wait "$SSCMA_PID"                                         # block until sscma-node exits/crashes
    sleep 2                                                   # then loop -> restart both
done
