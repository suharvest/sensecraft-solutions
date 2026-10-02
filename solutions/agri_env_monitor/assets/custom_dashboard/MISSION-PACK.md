# Running the Ops Dashboard on a Mission Pack (bare metal)

The `custom_dashboard` preset deploys the dashboard as a Docker container, which is the
recommended path. This note documents a **bare-metal install on a Seeed reComputer
(R1000 Series)** — the "Mission Pack" — for anyone who wants the dashboard running directly
on the device with a kiosk display, without Docker. It is exactly what was done on the
reference unit.

Use it as a reference; the Docker preset already handles all of this for you.

## What you end up with

- The bridge (`bridge.py`) running as a systemd service, serving the dashboards on HTTP
  and pushing live updates over WebSocket.
- A kiosk: the device's browser opens the ops console full-screen on boot.
- Live data from your MQTT broker.

## 1. Get the code

```bash
# on the reComputer, as the recomputer user
git clone https://github.com/biancayoung/agri-env-ops-dashboard.git
cd agri-env-ops-dashboard
```

## 2. Python environment

```bash
python3 -m venv /home/recomputer/farm-venv
/home/recomputer/farm-venv/bin/pip install -r requirements.txt
```

## 3. Pick a port — 8000 is taken

On the reComputer R1000, port **8000 is already used by a docker-proxy**, so serve the
dashboard on **8001** instead. The WebSocket port 8765 is free.

## 4. systemd service

Create `/etc/systemd/system/farm-bridge.service`:

```ini
[Unit]
Description=Agri-Env Ops Dashboard bridge
After=network.target

[Service]
Type=simple
User=recomputer
WorkingDirectory=/home/recomputer/agri-env-ops-dashboard
ExecStart=/home/recomputer/farm-venv/bin/python /home/recomputer/agri-env-ops-dashboard/bridge.py \
  --http-port 8001 --ws-port 8765 \
  --mqtt-host <your-broker> --mqtt-port 1883 \
  --mqtt-user <user> --mqtt-pass <password> \
  --mqtt-prefix <prefix> --mqtt-topic application/+/device/+/event/up
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now farm-bridge
systemctl is-active farm-bridge     # -> active
curl -s http://127.0.0.1:8001/api/health
```

> Prefer a `.env` file over putting the broker password on the `ExecStart` line:
> `ExecStart=... bridge.py --env-file /home/recomputer/agri-env-ops-dashboard/.env`
> with `chmod 600` on that file. Either way, **do not commit the password anywhere.**

## 5. Kiosk (full-screen browser on boot)

The reComputer ships with a kiosk helper at `~/bin/qv-kiosk.sh`. Point it at the dashboard:

```bash
# edit ~/bin/qv-kiosk.sh and set the URL to:
URL="http://127.0.0.1:8001/ops"
```

It is launched from the LXDE autostart. Two gotchas seen on the reference unit:

- **Stale lock**: if the kiosk does not come up, remove `/tmp/qv-kiosk.lock` and reboot
  (or re-run the script). A leftover lock from an unclean shutdown blocks the next launch.
- **Network check**: the kiosk script waits for the dashboard to answer before opening the
  browser; the bridge serves `HEAD` requests, so the check passes once the service is up.

## 6. Backups

Before changing anything on the device, back up what you replace. The reference unit keeps
these under `/home/recomputer/farm-backups/` (the original `qv-kiosk.sh`, the previous
service file, and so on).

## Verify

- `curl -s http://127.0.0.1:8001/api/health` returns JSON with per-source status.
- Open `http://<device-ip>:8001/ops` from any machine on the network; the MQTT indicator
  shows connected once the broker credentials are right.
- The kiosk display shows the same page after a reboot.

## Notes

- The dashboard is **receive-only**; it never sends commands to your devices.
- Keep the device and the broker on the same trusted network, and require broker
  authentication.
- To update the code later: `git pull` in the project directory, then
  `sudo systemctl restart farm-bridge`.
