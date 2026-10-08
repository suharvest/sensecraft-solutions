## Preset: IP Camera + Edge Compute Box {#ip_camera_box}

The entrance IP camera sends its picture to a reComputer next to it. The reComputer counts vehicles crossing a line in the picture and sends vehicles inside and free spaces to your MQTT server.

| Device | Purpose |
|--------|---------|
| reComputer J30 Series (Jetson Orin Nano) or reComputer RK3588 Series | Analyses the camera picture and counts vehicles in and out |
| Entrance IP camera | Films the lane and provides an RTSP stream |
| MQTT server | Receives crossing records and free spaces |

**What you'll get:**
- A record for every vehicle that crosses the line (direction, vehicle type)
- Live vehicles-inside and free-space figures
- Data ready for a parking management system, a free-space sign or Home Assistant

**Requirements:** A working camera RTSP address · An MQTT server (an existing one or a Mosquitto install) · Internet access on the device for the first deployment

## Step 1: Deploy the vehicle counting app {#deploy_counting type=docker_deploy required=true config=devices/jetson_counting.yaml}

Install the counting app on the reComputer and enter the camera, the MQTT server and where the counting line goes.

### Prerequisites

1. You have opened the camera's RTSP address in VLC on a computer and can see the entrance.
2. You know the MQTT server's IP address and port (usually 1883), and its user name and password (not needed if it accepts anonymous connections).
3. The reComputer is powered on, connected to the LAN, and can reach the internet to download the app and model.
4. Jetson: the module is an Orin Nano running JetPack 6.2. Any other module or system version stops at the first deployment check.
5. At least 1 GB of free disk space on the device.

### Wiring

1. Connect the reComputer and the camera to the same LAN with Ethernet cables (if the camera is powered by a PoE switch, plug the reComputer into the same switch).
2. Mount the camera so it looks at the lane, with vehicles moving from one side of the picture to the other and each vehicle fully in view.
3. Choose the counting line direction: "Vertical line" when vehicles move left/right in the picture, "Horizontal line" when they move up/down. The line must cross the whole lane.
4. Choose the line position (10–90): for a vertical line, the distance from the left edge of the picture in percent; for a horizontal line, from the top edge. Put it where vehicles drive through steadily and are fully visible, away from where they queue for the barrier.
5. Enter the camera address, MQTT server, site ID, entrance ID, total spaces and vehicles already inside, then click Deploy.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| UNSUPPORTED_JETSON_MODULE or UNSUPPORTED_JETPACK | This solution supports only Jetson Orin Nano with JetPack 6.2; use that device or reflash the system |
| MISSING_BOARD_LIBRARIES (RK3588) | The message lists what is missing; install the RKNN runtime, MPP/RGA, gstreamer1.0-rockchip and gstreamer1.0-plugins-bad following the board vendor's instructions, then deploy again |
| Model or app download fails | Make sure the device can reach the internet, then deploy again; parts already downloaded are reused |
| Not enough disk space | Remove unused files or images on the device so that at least 1 GB is free |
| The counting service does not start, or waiting for it times out | Run `docker logs edge-parking-counting-jetson` on the device (`edge-parking-counting-rk3588` on RK3588) to see the error |
| The log shows Address already in use | Another program on the device uses the port: for 8080, change "Counter service port"; for 8099, change "Status port" on Jetson, or stop the program using 8099 on RK3588. Then deploy again |
| An ID is rejected | Site ID and entrance ID may only contain letters, digits, - and _ |

### Target: Jetson Orin Nano (remote) {#counting_remote type=remote device=jetson device_name="Jetson" config=devices/jetson_counting.yaml default=true}

Deploy over SSH from this computer to a reComputer J30 Series (Jetson Orin Nano) on the LAN.

### Target: Jetson Orin Nano (this device) {#counting_local type=local device=jetson device_name="Jetson" config=devices/jetson_counting.yaml}

Deploy directly on the reComputer J30 Series (Jetson Orin Nano) you are using.

### Target: RK3588 (remote) {#rk3588_counting_remote type=remote device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

Deploy over SSH from this computer to a reComputer RK3588 Series on the LAN; processes about 3 frames per second.

### Target: RK3588 (this device) {#rk3588_counting_local type=local device=rk3588 device_name="RK3588" config=devices/rk3588_counting.yaml}

Deploy directly on the reComputer RK3588 Series you are using; processes about 3 frames per second.

## Step 2: Check the counting service {#verify_counting type=http_debug required=true config=devices/health_verify.yaml}

Confirm the counting service is running and receiving the camera picture.

### Wiring

1. Enter the reComputer's IP address as "Device address"; enter `127.0.0.1` if you deployed on this device.
2. Keep "Status port" at 8099 (enter your value only if you changed it in Step 1).
3. Click Check. A 200 response means the service is running.

### Deployment Complete

The counting app is running on the reComputer. When a vehicle crosses the counting line, a crossing record and the car park status are sent to your MQTT server.

#### Check the response

In the response, look at `streams`:

1. `state` is `running`: the camera picture is being received.
2. `fps`: frames processed per second. On Jetson Orin Nano it should be close to the camera frame rate; on RK3588 about 3.
3. `processed_frames` grows with every check: the picture is being analysed continuously.

#### Initial Setup

1. "Vehicles already inside" is the starting count on first start; after that, restarts and redeployments continue from the saved count.
2. "Total spaces" is used to work out free spaces; enter the actual number of spaces.
3. To reset the count when it no longer matches the car park: enter the correct "Vehicles already inside" in Step 1 and deploy again, then run the commands below on the device (on RK3588 set `C=edge-parking-counting-rk3588`; replace `gate-a` with your entrance ID):

   ```bash
   C=edge-parking-counting-jetson
   D=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/data/edge-parking"}}{{.Source}}{{end}}{{end}}' $C)
   docker stop $C
   sudo rm "$D/gate-a/occupancy.json"
   docker start $C
   ```

#### Quick Verification

1. On a computer that can reach the MQTT server, subscribe to the counting topics (replace `demo-lot` with your site ID):

   ```bash
   mosquitto_sub -h <MQTT server IP> -p 1883 -t 'demo-lot/parking/#' -v
   ```

2. Drive a vehicle in. Within a few seconds of crossing the line you receive a `.../crossing` message with `direction` `in`, and a `.../occupancy` message with `occupancy` up by 1 and `free` down by 1.
3. Drive it out. You receive a record with `direction` `out` and `occupancy` down by 1.
4. If vehicles entering are recorded as `out` and vehicles leaving as `in`, switch "Entry direction" and run Step 1 again.
5. If a vehicle crosses without a record, move the counting line to where vehicles are fully visible and drive through steadily; on RK3588, make sure vehicles stay in view for about 1 second or longer.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection failed | Check the device IP, that this computer and the device are on the same network, and that the port matches Step 1 |
| `state` stays `reconnecting` or `error` | The device cannot reach the camera: open the RTSP address in VLC on the same network and check the path, user name and password; on RK3588 also check that "Camera video format" matches the camera setting. Then run Step 1 again |
| MQTT shows as not connected in the response | Check the MQTT server address, port, user name and password, and that the device can reach port 1883 on the server, then run Step 1 again |
