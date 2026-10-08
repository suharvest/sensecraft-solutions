## Preset: IP Camera + Edge Compute Box {#ip_camera_box}

The entrance IP camera sends its picture to a reComputer next to it. The reComputer counts vehicles crossing a line in the picture and sends vehicles inside and free spaces to your MQTT server.

| Device | Purpose |
|--------|---------|
| reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2) or reComputer RK3588 / RK3576 Series | Analyses the camera picture and counts vehicles in and out |
| Entrance IP camera | Films the lane and provides an RTSP stream |
| MQTT server | Receives crossing records and free spaces |

**What you'll get:**

- A record for every vehicle that crosses the line (direction, vehicle type)
- Live vehicles-inside and free-space figures
- Data ready for a parking management system, a free-space sign or Home Assistant

**Requirements:** A working camera RTSP address · An MQTT server (an existing one or a Mosquitto install) · Internet access on the device for the first deployment

## Step 1: Deploy the vehicle counting app {#deploy_counting type=docker_deploy required=true config=devices/jetson_counting.yaml}

Install the counting app on the reComputer and enter the camera and the MQTT server. You draw the counting line in Step 2.

### Prerequisites

1. You have opened the camera's RTSP address in VLC on a computer and can see the entrance.
2. You know the MQTT server's IP address and port (usually 1883), and its user name and password (not needed if it accepts anonymous connections).
3. The reComputer is powered on, connected to the LAN, and can reach the internet to download the app and model.
4. Jetson: a reComputer J30 / J40 (Jetson Orin Nano / Orin NX) running JetPack 6.2. Any other module or system version stops at the first deployment check.
5. At least 1 GB of free disk space on the device.

### Wiring

1. Connect the reComputer and the camera to the same LAN with Ethernet cables (if the camera is powered by a PoE switch, plug the reComputer into the same switch).
2. Mount the camera so it looks at the lane, with vehicles moving from one side of the picture to the other and each vehicle fully in view.
3. Enter the camera address, MQTT server, site ID, entrance ID and total spaces, then click Deploy.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| UNSUPPORTED_JETSON_MODULE or UNSUPPORTED_JETPACK | This solution supports only reComputer J30 / J40 (Jetson Orin Nano / Orin NX) with JetPack 6.2; use one of those or reflash the system |
| MISSING_BOARD_LIBRARIES (RK3588 / RK3576) | The message lists what is missing; install the RKNN runtime, MPP/RGA, gstreamer1.0-rockchip and gstreamer1.0-plugins-bad following the board vendor's instructions, then deploy again |
| Model or app download fails | Make sure the device can reach the internet, then deploy again; parts already downloaded are reused |
| Not enough disk space | Remove unused files or images on the device so that at least 1 GB is free |
| The counting service does not start, or waiting for it times out | Run `docker logs edge-parking-counting-jetson` on the device (`edge-parking-counting-rk3588` on RK3588, `edge-parking-counting-rk3576` on RK3576) to see the error |
| The log shows Address already in use | Another program on the device uses the port: for 8080, change "Counter service port"; for 8099, change "Status port" on Jetson, or stop the program using 8099 on RK3588 / RK3576. Then deploy again |
| An ID is rejected | Site ID and entrance ID may only contain letters, digits, - and _ |

### Deployment Complete

The last deploy step waits until the counting service is ready, so a successful deploy means it is running. Next, draw the counting line in Step 2.

### Target: reComputer J30 / J40 (remote) {#counting_remote type=remote device=jetson device_name="reComputer J30 / J40" config=devices/jetson_counting.yaml default=true}

Deploy over SSH from this computer to a reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2) on the LAN.

### Target: reComputer J30 / J40 (this device) {#counting_local type=local device=jetson device_name="reComputer J30 / J40" config=devices/jetson_counting.yaml}

Deploy directly on the reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2) you are using.

### Target: RK3588 (remote) {#rk3588_counting_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

Deploy over SSH from this computer to a reComputer RK3588 Series on the LAN; processes about 3 frames per second.

### Target: RK3588 (this device) {#rk3588_counting_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

Deploy directly on the reComputer RK3588 Series you are using; processes about 3 frames per second.

### Target: RK3576 (remote) {#rk3576_counting_remote type=remote device=rk3576 device_name="RK3576" config=devices/rk3576_counting.yaml}

Deploy over SSH from this computer to a reComputer RK3576 Series on the LAN; measured at 30 frames per second.

### Target: RK3576 (this device) {#rk3576_counting_local type=local device=rk3576 device_name="RK3576" config=devices/rk3576_counting.yaml}

Deploy directly on the reComputer RK3576 Series you are using; measured at 30 frames per second.

## Step 2: Draw the counting line {#draw_line type=web_dashboard required=false config=devices/counting_editor.yaml}

Open the counting line page, draw the line across the lane, check the in/out sides and enter the vehicles already inside.

### Wiring

1. The device IP and counter service port are carried over from Step 1 (127.0.0.1 for a deployment on this device). Open the page; it shows the live camera picture.
2. Press and drag on the picture to draw a line across the whole lane; drag the dot at either end to fine-tune it. Put the line where vehicles drive through steadily and are fully visible, away from where they queue for the barrier.
3. Check the "进 IN" and "出 OUT" labels on either side of the line: IN must be the side a vehicle is on after it has entered the car park. If they are reversed, click "Swap in/out".
4. Click "Save". The line applies immediately and is kept across restarts and redeployments.
5. Under "Vehicles inside now", enter the number of vehicles parked inside right now and click "Set".

### Deployment Complete

The counting line is active. When a vehicle crosses it, a crossing record and the car park status are sent to your MQTT server.

#### Initial Setup

1. If the count of vehicles inside no longer matches the car park, enter the correct number under "Vehicles inside now" on this page at any time and click "Set".
2. "Total spaces" is used to work out free spaces and is entered in Step 1. To change it, enter the new value in Step 1 and deploy again; the saved counting line is kept.

#### Quick Verification

1. Keep the page open and drive a vehicle in. It is boxed, and after it crosses the line "In" goes up by 1, "Inside" up by 1 and "Free" down by 1.
2. Drive it out. "Out" goes up by 1 and "Inside" down by 1.
3. If entering vehicles are counted as leaving, click "Swap in/out", then "Save".
4. On a computer that can reach the MQTT server, subscribe to the counting topics (replace `demo-lot` with your site ID). Within a few seconds of a crossing you receive a `.../crossing` message (`direction` `in` or `out`) and a `.../occupancy` message:

   ```bash
   mosquitto_sub -h <MQTT server IP> -p 1883 -t 'demo-lot/parking/#' -v
   ```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Check that the IP is the counting device's address, the port matches "Counter service port" in Step 1, and this computer is on the same network |
| Page opens but shows no picture | The device cannot reach the camera: open the RTSP address in VLC on the same network and check the path, user name and password; on RK3588 / RK3576 also check that "Camera video format" matches the camera setting. Then deploy again |
| A vehicle crosses but the counts do not change | Move the line to where vehicles are fully visible and drive through steadily, then click "Save"; the line must cross the whole lane. On RK3588, make sure vehicles stay in view for about 1 second or longer |
| Entries and exits are swapped | Click "Swap in/out", then "Save" |
| "Line too short" | The drag was too short; drag a longer line on the picture |
| "Save failed" after clicking Save | Reload the page and draw the line again; if it still fails, run `docker logs edge-parking-counting-jetson` on the device (`edge-parking-counting-rk3588` on RK3588, `edge-parking-counting-rk3576` on RK3576) to see the error |
| No MQTT messages arrive | Check the MQTT server address, port, user name and password, and that the device can reach port 1883 on the server, then deploy again |
