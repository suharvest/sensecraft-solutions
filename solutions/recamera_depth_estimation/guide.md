## Preset: Depth Estimation {#default}

Run a monocular depth model on the reCamera's own TPU. One ordinary image in, a
dense relative depth map out — no stereo pair, no depth camera.

| Device | Purpose |
|--------|---------|
| reCamera | Runs the depth model and streams the result |

**What you'll get:**
- RTSP stream with a colour depth preview in the corner
- MQTT with per-frame percentiles, near-area ratio and a 3x3 proximity grid
- Home Assistant entities for near-area and near-presence

**Requirements:** a reCamera reachable over USB or the network, and a scene with
objects at clearly different distances. A blank wall or ceiling produces a flat,
uninformative map — that is this model's known weak case, not a fault.

## Step 1: Install the app and model {#deploy type=recamera_cpp required=true config=devices/recamera_depth.yaml}

Installs the `.deb` and places the depth model at `/userdata/local/models/`.

### Wiring

1. Connect the reCamera over USB-C, or make sure it is reachable on your network
2. Enter its IP address (USB gives it `192.168.42.1`) and the SSH password for
   the `recamera` user
3. Deploy

### What lands on the device

| Path | What |
|------|------|
| `/usr/local/bin/depth-estimation` | The application |
| `/etc/init.d/K92depth-estimation` | Its init script, parked |
| `/userdata/local/models/fastdepth_224_bf16.cvimodel` | The model, 2.9 MB |

The init script is installed parked (`K92`, not `S92`) on purpose. Only one
application may hold the camera at a time, so starting it is the console's job.

## Step 2: Start it from the console {#start type=manual required=true}

Open the camera's console in a browser and enable **Monocular Depth Estimation**
in the app gallery.

If a **Node-RED mode** banner is shown, switch back to Console mode first. In
Node-RED mode gallery apps are stopped and disabled. Node-RED is also watched by
a supervisor script that restarts it, so stopping it by hand does not stick —
and a revived Node-RED will contend with the app for the camera.

## Step 3: Check the output {#verify type=manual required=false verify=true}

### The stream

Open `rtsp://<camera-ip>:8554/live0` in VLC or any VMS. The depth preview sits
in the bottom-right corner: red is near, blue is far.

### The numbers

Subscribe to `recamera/depth-estimation/results`:

```json
{
  "depth": {
    "unit": "relative",
    "smaller_is_nearer": true,
    "p02": 0.949, "p50": 1.531, "p98": 2.672,
    "near_ratio": 0.346,
    "near_present": true,
    "zones": [0.49, 0.27, 1.00,
              0.74, 0.78, 0.98,
              0.77, 0.80, 0.96]
  }
}
```

`zones` is the 3x3 grid in reading order, each cell 0 (far) to 1 (nearest in
frame). In the sample above the right column is nearest.

### Sanity-check it once

Stand near one side of the frame and confirm that side reads nearer. If the
whole map looks flat, look at the scene before the model — large untextured
surfaces genuinely do not give it enough to work with.

**Do not convert these numbers into distances.** They are relative ordering and
have no metric meaning.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| App exits right after starting | The model file is missing or at another path. Check `/userdata/local/models/`. |
| Stream stalls, log shows `get chn frame fail` | The VPSS pipeline wedged. Restarting the app does not clear it — reboot the camera. The usual trigger is two things holding the camera at once, most often Node-RED coming back. |
| Depth map looks flat | Point the camera at a scene with real depth. Blank walls, ceilings, glass and sky are the documented weak cases. |
| App not in the gallery | The console only scans `/userdata/local/apps/`. Re-run the deployment. |
