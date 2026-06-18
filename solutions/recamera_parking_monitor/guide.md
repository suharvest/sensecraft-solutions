## Preset: Parking Monitor {#default}

Real-time parking slot detection using reCamera's built-in AI. Just connect your camera and deploy — no external server needed.

| Device | Purpose |
|--------|---------|
| reCamera | Detects cars and free parking slots |

**What you'll get:**
- Real-time parking slot status (free / occupied)
- Visual dashboard with color-coded indicators
- Adjustable detection sensitivity

**Requirements:** reCamera connected via USB or network

## Step 1: Deploy to reCamera {#deploy_flow type=recamera_nodered required=true config=devices/recamera.yaml}

Deploy the parking detection flow and AI model to your reCamera.

### Wiring

1. Connect reCamera to your computer via USB-C cable
2. Enter the reCamera IP address and SSH password
3. Click Deploy to install the parking detection flow

### Deployment Complete

1. Open **http://\<reCamera-IP\>:1880/dashboard/preview** in your browser
2. You should see the live camera feed with detection overlays
3. Enter parking slot labels (e.g. `A1,A2,A3`) in the text input field

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection failed | Check USB cable connection; try both passwords: `recamera` and `recamera.2` |
| No camera feed / black screen | The camera service needs ~90 seconds to restart after deployment; wait and refresh the page |
| Model download failed | Ensure reCamera has internet access (WiFi or via USB sharing) |
| Detection not accurate | Adjust Confidence and IoU sliders on the dashboard |

---

## Step 2: Configure Slot Labels {#verify_dashboard type=manual required=false}

Once the dashboard is open (next step), set up the parking slots for your scene:

1. Enter slot labels in the text field (e.g. `A1,A2,A3` — one label per detected slot, left to right)
2. Adjust **Confidence** and **IoU** sliders for your environment

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Monitoring Slots: None" | Enter slot labels in the text input field on the dashboard |
| Slots flicker between free/occupied | Increase the Confidence threshold; the stabilization algorithm needs 15 frames to confirm |
| Wrong slot assignment | Slot labels map left-to-right by position — reorder your labels to match camera view |

## Step 3: Open Dashboard {#dashboard type=web_dashboard required=true config=devices/dashboard.yaml}

The parking monitor dashboard is now live. Click below to open it in your browser.

### Troubleshooting
| Issue | Solution |
|-------|----------|
| Page not loading | Make sure the previous deployment step finished successfully and the service is healthy. |
| Wrong host/port | Update the URL with your device's IP if you deployed to a remote machine. |
### Deployment Complete

Your AI parking monitor is now running.

#### Quick Verification

- Open **http://\<reCamera-IP\>:1880/dashboard/preview**
- Green circles = free slots, Red circles = occupied
- Status panel shows slot counts in real time

#### Tips

- Mount reCamera facing the parking slots at a slight angle (front-facing view works best)
- Current design is optimized for 3 adjacent parking slots
- The system uses multi-frame validation to avoid false triggers from shadows or temporary obstructions

#### Next Steps

- [View Wiki Documentation](https://wiki.seeedstudio.com/cn/ai_parking_slot_monitoring_demo_with_recamera/)
- [Report Issues](https://github.com/Seeed-Studio/wiki-documents/issues)
