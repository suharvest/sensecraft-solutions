## Preset: Depth Estimation {#default}

Run a monocular depth model on the reCamera. An ordinary image in, relative
near/far out — no stereo pair, no depth camera.

| Device | Purpose |
|--------|---------|
| reCamera | Runs the console and the depth app; outputs the RTSP stream and MQTT data |

**What you'll get:**
- RTSP stream with a colour depth preview in the corner (red near, blue far)
- MQTT with per-frame relative depth statistics and a 3x3 proximity grid
- Home Assistant entities for near-area and near-presence

**Scene:** objects at clearly different distances. Blank walls, ceilings, glass
and sky produce a flat depth map.

## Step 1: Update the reCamera Console {#deploy_console type=recamera_cpp required=true config=devices/recamera_console.yaml}

Install console 0.5.5, which manages the camera's apps. Already current? It's skipped.

### Prerequisites

1. Connect the camera over USB, or put it on the same network as this computer.
2. Over USB the address is `192.168.42.1`; over Wi-Fi use the IP your router shows.
3. Username `recamera`, default password `recamera` (older units use `recamera.2`).
4. New devices need SSH enabled first — connect over USB, wait about two minutes for boot, open `http://192.168.42.1/#/security`, sign in, and turn on the SSH toggle.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect | USB: use `192.168.42.1`; network: check your router for the IP |
| Password rejected | Default is `recamera`; units shipped with older firmware use `recamera.2` |
| Install failed | Restart the camera and run the step again |
| Node-RED stopped working | Expected — the console takes over the camera. Switch back from the console's system settings; nothing is uninstalled |

---

## Step 2: Install the Depth Estimation App {#deploy_depth type=recamera_cpp required=true config=devices/recamera_depth.yaml}

Install the depth app and its model onto the camera. Address and password are
the same as the previous step.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Cannot connect or password rejected | Use the same address and password as Step 1 |
| Install failed | Make sure this computer is online (the package is downloaded from the cloud), restart the camera and run the step again |

---

## Step 3: Enable the App in the Console {#open_console type=web_dashboard required=true config=devices/console_dashboard.yaml}

Open the camera's console and enable Monocular Depth Estimation.

### Prerequisites

1. Sign in with the camera's account — the same password as Step 1.
2. On the **Applications** page, enable **Monocular Depth Estimation**. The camera runs one app at a time; enabling it stops whatever else was running.

### Deployment Complete

Open the app's **Debug** page for the live view, with the depth preview in the
bottom-right corner.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Wait a minute for the camera to finish starting, then refresh |
| Monocular Depth Estimation is not in the list | Run Step 2 again |
| A **Node-RED mode** banner is shown and the app cannot be enabled | Switch back to Console mode in the console |
| Picture freezes | Restart the camera |

---

## Step 4: Check the Output {#verify type=manual required=false verify=true}

### Deployment Complete

**Video stream:** open `rtsp://<camera-ip>:8554/live0` in VLC
(`rtsp://192.168.42.1:8554/live0` over USB). The depth preview is in the
bottom-right corner, red near and blue far. Stand on one side of the frame and
that side should turn red.

**MQTT data:** subscribe to `recamera/depth-estimation/results`:

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

- `near_ratio`: share of the frame that is near
- `near_present`: whether something is close to the camera
- `zones`: 3x3 grid, left to right and top to bottom, 0 far to 1 nearest in frame. In the sample above the right column is nearest

The values are relative near/far, not metres, and cannot be converted to distance.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Depth map looks flat | Point the camera at a scene with real depth; avoid blank walls, ceilings, glass and sky |
| Stream does not open | Check that the app is enabled in Step 3 |
