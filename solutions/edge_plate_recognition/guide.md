## Preset: IP Camera + Recognition Host {#ip_camera_box}

Keep your existing gate cameras and let one recognition host read plates on site. Add a reComputer R1100 Series unit when you want the barrier to open automatically.

| Device | Purpose |
|--------|---------|
| reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2) / RK3588 Series / RK3576 Series | Recognition host, pick one |
| IP camera | Films the lane, 1080p or better, with RTSP |
| reComputer R1100 Series (R1124-10) | Gate controller: checks the whitelist and sends the open signal to the barrier (optional) |
| Interposing relay | Sits between the gate controller and the barrier (optional) |

**What you'll get:**
- Live view in the browser with plate boxes and the latest reads
- One record per vehicle: plate number, confidence and a snapshot link
- The barrier opens automatically for whitelisted vehicles

**Requirements:** Camera and recognition host on the same local network · Internet access on the recognition host for the first deployment

## Step 1: Deploy Plate Recognition {#deploy_host type=docker_deploy required=true config=devices/jetson_plate.yaml}

Install the plate recognition service on the recognition host and connect it to your gate camera.

### Prerequisites

1. The camera's RTSP URL; include the username and password if the camera requires a login.
2. The camera mounted 3–8 m from the lane, with plates appearing in the lower-middle part of the image.
3. MQTT broker address: for automatic barrier opening, use the IP of the gate controller (Step 3 installs the message service on it); for logging only, use your own MQTT broker.
4. Ports 8080 (recognition preview) and 8099 (status check) are not used by another program on the recognition host. If 8080 is taken, enter a different preview port in the form.

### Deployment Complete

The last deploy step waits until plate recognition is ready, so a successful deploy means the service is running. Open `http://<host-ip>:8080/preview` (or the preview port you entered) in a browser (127.0.0.1 when deployed on this machine) and you should see the live picture; Step 2 opens it directly.

### Target {#jetson_remote type=remote device=jetson device_name="reComputer J30 / J40" config=devices/jetson_plate.yaml default=true}

Deploy from this computer over the network to a reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2).

### Wiring

1. Connect the Jetson to power and Ethernet, on the same local network as this computer and the camera
2. Enter the Jetson's IP, SSH username and password
3. Enter the camera RTSP URL and the MQTT broker address; Site ID and Camera ID can stay at their defaults
4. Click Deploy; it first checks the module and JetPack version, then downloads the recognition models and starts the service

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Module or JetPack version mismatch | Only reComputer J30 / J40 (Jetson Orin Nano / Orin NX) with JetPack 6.2 is supported; for other Jetson modules use an RK3588 or RK3576 host |
| NVIDIA container runtime missing | Run `sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker` on the Jetson, then deploy again |
| The last deploy step times out waiting for the service | Port 8099 may be taken: set "Status port" to a free port (for example 18099) and deploy again |
| No video from the camera | Open the RTSP URL in VLC first; a wrong path or wrong credentials is the most common cause |
| Model download fails | Make sure the Jetson can reach the internet, then deploy again |

### Target {#jetson_local type=local device=jetson device_name="reComputer J30 / J40" config=devices/jetson_plate.yaml}

Deploy directly on this reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2).

### Wiring

1. Connect the Jetson to Ethernet, on the same local network as the camera
2. Enter the camera RTSP URL and the MQTT broker address
3. Click Deploy

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Module or JetPack version mismatch | Only reComputer J30 / J40 (Jetson Orin Nano / Orin NX) with JetPack 6.2 is supported |
| The last deploy step times out waiting for the service | Set "Status port" to a free port and deploy again |
| No video from the camera | Open the RTSP URL in VLC and check the path and credentials |

### Target {#rk3588_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml}

Deploy from this computer over the network to a reComputer RK3588 Series; needs at least 6 GB of free disk.

### Wiring

1. Connect the RK3588 to power and Ethernet, on the same local network as this computer and the camera
2. Enter the RK3588's IP, SSH username and password
3. Enter the camera RTSP URL and the MQTT broker address; Site ID and Camera ID can stay at their defaults
4. Click Deploy; it first checks the on-board AI and video decoding components, then downloads the recognition models and starts the service

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The first deploy step reports missing components | Use the reComputer factory OS; on a self-installed OS, install the rknpu2 runtime, Rockchip MPP / RGA, `gstreamer1.0-plugins-bad` and `gstreamer1.0-rockchip` first |
| Service does not start, port 8080 or 8099 in use | Enter a free preview port in the form, or stop the program using those ports, and deploy again |
| No video from the camera | Open the RTSP URL in VLC first; a wrong path or wrong credentials is the most common cause |
| Model download fails | Make sure the device can reach the internet, then deploy again |

### Target {#rk3588_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_plate.yaml}

Deploy directly on this reComputer RK3588 Series; needs at least 6 GB of free disk.

### Wiring

1. Connect the RK3588 to Ethernet, on the same local network as the camera
2. Enter the camera RTSP URL and the MQTT broker address
3. Click Deploy

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The first deploy step reports missing components | Use the reComputer factory OS, or install the packages listed in the message first |
| Service does not start, port 8080 or 8099 in use | Enter a free preview port in the form, or stop the program using those ports, and deploy again |
| No video from the camera | Open the RTSP URL in VLC and check the path and credentials |

### Target {#rk3576_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml}

Deploy from this computer over the network to a reComputer RK3576 Series; needs at least 6 GB of free disk.

### Wiring

1. Connect the RK3576 to power and Ethernet, on the same local network as this computer and the camera
2. Enter the RK3576's IP, SSH username and password
3. Enter the camera RTSP URL and the MQTT broker address; Site ID and Camera ID can stay at their defaults
4. Click Deploy; it first checks the on-board AI and video decoding components, then downloads the recognition models and starts the service

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The first deploy step reports missing components | Use the reComputer factory OS; on a self-installed OS, install the rknpu2 runtime, Rockchip MPP / RGA, `gstreamer1.0-plugins-bad` and `gstreamer1.0-rockchip` first |
| Service does not start, port 8080 or 8099 in use | Enter a free preview port in the form, or stop the program using those ports, and deploy again |
| No video from the camera | Open the RTSP URL in VLC first; a wrong path or wrong credentials is the most common cause |
| Model download fails | Make sure the device can reach the internet, then deploy again |

### Target {#rk3576_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_plate.yaml}

Deploy directly on this reComputer RK3576 Series; needs at least 6 GB of free disk.

### Wiring

1. Connect the RK3576 to Ethernet, on the same local network as the camera
2. Enter the camera RTSP URL and the MQTT broker address
3. Click Deploy

### Troubleshooting

| Issue | Solution |
|-------|----------|
| The first deploy step reports missing components | Use the reComputer factory OS, or install the packages listed in the message first |
| Service does not start, port 8080 or 8099 in use | Enter a free preview port in the form, or stop the program using those ports, and deploy again |
| No video from the camera | Open the RTSP URL in VLC and check the path and credentials |

---

## Step 2: Watch Recognition Results {#view_host type=web_dashboard required=false config=devices/dashboard.yaml}

Open the live preview and confirm the camera image and plate recognition both work.

### Wiring

1. Confirm the recognition host IP (filled in from the host deployed in Step 1)
2. Open the preview page and check that the live camera image appears
3. Drive a vehicle into the lane, or hold a plate photo up to the camera; a box appears around the plate and the recognized number is listed beside the image

### Deployment Complete

The recognition host is now reading your gate camera.

#### Quick Verification

1. Drive a vehicle through the lane; the preview page lists its plate number
2. Subscribe to `<Site ID>/parking/#` with an MQTT client; each vehicle produces one plate record with the plate number, confidence and a snapshot link
3. For automatic barrier opening, continue with Steps 3 and 4

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not load | Wait 30 seconds after deployment and refresh; make sure the IP is the recognition host's |
| Image shows but no plate box | Plates must appear in the lower-middle part of the image (about 20% excluded on each side and 30% at the top); adjust the camera angle |
| Plate box appears but no result | A plate is reported only after several consecutive frames agree; if vehicles pass fast or plates look small, bring the camera closer |

---

## Step 3: Install the Gate Controller (optional) {#gate_host type=script required=false config=devices/gate_controller.yaml}

Install the message service and the gate service on the reComputer R1100 Series gate controller to check the whitelist and control the barrier.

### Wiring

1. Connect the gate controller to power and Ethernet, on the same local network as the recognition host and with internet access
2. Enter the gate controller's IP, SSH username and password
3. Site ID is carried over from Step 1; the Gate ID tells barriers apart in the gate records
4. Gate output line: the system name of the digital output wired to the relay; look it up in the digital output (DO) section of the reComputer R1000 Series wiki
5. Click Deploy; afterwards make sure the MQTT broker address in Step 1 is this gate controller's IP

### Troubleshooting

| Issue | Solution |
|-------|----------|
| SSH connection fails | Check the IP, username and password; ping the device |
| Gate output line is empty | Look up the line name in the wiki, fill it in and deploy again |
| Message service install fails | The gate controller needs internet access to download packages |
| Recognition host cannot reach the message service | Put both devices on the same local network and make sure port 1883 on the gate controller is not blocked by a firewall |

---

## Step 4: Wire the Barrier Gate (optional) {#wire_host type=manual required=false config=devices/gate_wiring.yaml}

Wire the gate controller's digital output through an interposing relay to the barrier's OPEN terminal, import the whitelist and test one opening.

### Wiring

1. Check the reComputer R1000 Series wiki for the digital output type and rated voltage and current, and pick a DIN-rail interposing relay with a matching coil voltage
2. Wire the gate controller's DO output to the relay coil (+) and DO common / GND to the coil (−)
3. Wire the relay's normally open (NO) contact to the barrier controller's OPEN terminal and its COM contact to the barrier's common terminal; do not wire the close terminal, closing stays with the barrier's own loop detector or radar
4. Prepare the whitelist CSV with the header `plate,label,valid_from,valid_until`, then upload it: `curl -X PUT --data-binary @whitelist.csv http://<gate-controller-ip>:8081/whitelist`
5. Fire a test opening: `curl -X POST http://<gate-controller-ip>:8081/gate/test`; the relay should close for about 0.5 s
6. Confirm the relay action with a multimeter or the relay indicator before testing with a vehicle at the barrier

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Whitelist upload returns 400 | The response names the failing line; check the header and that line's format |
| Relay does not click on the test | Check the DO wiring and the relay coil voltage; confirm the gate output line entered in Step 3 |
| Relay clicks but the barrier stays down | Make sure the NO contact goes to the barrier's OPEN terminal |
| A whitelisted vehicle does not open the barrier | Plates must match exactly: check the plate number and validity dates in the whitelist; the same plate arriving again within a short time is ignored |
