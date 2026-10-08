## Preset: IP Cameras + Edge Box {#ip_camera_box}

Keep the IP cameras already in your car park and add one edge box on the same network to analyse their pictures. You draw a box around each bay in a web page; the box sends every bay's occupied / free state to your MQTT server.

| Device | Purpose |
|--------|---------|
| reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2) or reComputer RK3588 | Analyses every camera picture and decides whether each bay has a car |
| IP camera | Your existing cameras, sending an H.264 RTSP stream |
| MQTT server | Receives the bay states for guidance signs, a parking system or Home Assistant |

**What you'll get:**
- Draw and name every bay over the live camera picture in a web page
- Whenever a bay changes, an MQTT message with the latest state of every bay on that camera
- A visible signal when a camera stream drops (its bays turn `unknown`)

**Requirements:** Edge box, cameras and MQTT server on the same LAN · Internet access on the edge box during deployment · An MQTT server (for example Mosquitto)

## Step 1: Deploy Bay Detection {#deploy_occupancy type=docker_deploy required=true config=devices/jetson_occupancy.yaml}

Install the bay detection service on the edge box. Enter the camera addresses and the MQTT server; there is no config file to edit.

### Prerequisites

1. With a reComputer J30 / J40: it must be a Jetson Orin Nano or Orin NX module on JetPack 6.2. Other Jetson modules or system versions are stopped at the first deploy step.
2. With a reComputer RK3588: its system must include Rockchip's AI accelerator (RKNN), video decode (MPP) and RGA libraries.
3. Every camera's RTSP address has been opened in VLC and shows a picture.
4. You know the MQTT server's address and port, plus a username and password if it requires login.
5. Ports 8080 (slot editor) and 8099 (status check) are free on the box. If 8080 is taken, enter a different slot editor port in the form.

### Wiring

1. Mount each camera high and angled down so every bay is clearly visible and not fully hidden by the car next to it.
2. Connect the cameras and the edge box by Ethernet to the same switch or router (a PoE switch can power the cameras).
3. In each camera's web settings, set the stream you will use (the sub-stream is enough) to H.264.
4. Note each camera's RTSP address. For a Hikvision camera: `rtsp://user:password@camera-ip:554/Streaming/Channels/102` (102 is the sub-stream).
5. Fill in the camera addresses (comma-separated for several cameras), the site ID and the MQTT server, then click Deploy.

Each camera starts with one example bay, P-01 (a box in the lower middle of the picture). Delete it or drag it onto a real bay in Step 2.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Deploy stops at "UNSUPPORTED_JETSON_MODULE" | This Jetson is not an Orin Nano or Orin NX module. This solution supports reComputer J30 / J40 (Jetson Orin Nano / Orin NX) only |
| Deploy stops at "UNSUPPORTED_JETPACK" or "UNSUPPORTED_TENSORRT" | The system is not JetPack 6.2; reflash JetPack 6.2 and deploy again |
| The RK3588 check reports "missing …" | If a path is printed below it, enter that path in the matching field (for example "RKNN runtime library") and deploy again. If no path is printed, the board lacks that library: install the RKNN runtime (rknpu2), MPP, RGA, gstreamer1.0-plugins-bad and gstreamer1.0-rockchip first |
| "Not an RTSP address" | Camera addresses must start with `rtsp://`, with commas between addresses |
| Camera addresses and camera IDs do not match in number | Give one ID per address, or leave the IDs empty to number them automatically |
| Downloading the detection model fails | Make sure the edge box can reach the internet, then deploy again |
| Deploy stops at "Wait for the parking service to start" | On the box, run `docker logs edge-parking-occupancy-jetson` (RK3588: `edge-parking-occupancy-rk3588`). The usual cause is port 8080 or 8099 in use: choose another slot editor port, or stop the service holding 8099 |

### Target {#occupancy_remote type=remote device=jetson device_name="reComputer J30 / J40" config=devices/jetson_occupancy.yaml default=true}

Deploy to a reComputer J30 / J40 (Jetson Orin Nano / Orin NX, JetPack 6.2) over the network (SSH) from this computer.

### Deployment Complete

The last deploy step waits until bay detection is ready, so a successful deploy means the service is running. Open `http://<host-ip>:8080/slots/editor` in a browser (or the slot editor port you entered) and you should see the camera picture. Next, draw the bays in Step 2.

### Target {#occupancy_local type=local device=jetson device_name="reComputer J30 / J40 (this machine)" config=devices/jetson_occupancy.yaml}

Install on this machine when this app runs on the reComputer J30 / J40 itself.

### Deployment Complete

The last deploy step waits until bay detection is ready, so a successful deploy means the service is running. Open `http://127.0.0.1:8080/slots/editor` in a browser (or the slot editor port you entered) and you should see the camera picture. Next, draw the bays in Step 2.

### Target {#rk3588_occupancy_remote type=remote device=rk3588 device_name="reComputer RK3588" config=devices/rk3588_occupancy.yaml}

Deploy to a reComputer RK3588 over the network (SSH) from this computer.

### Deployment Complete

The last deploy step waits until bay detection is ready, so a successful deploy means the service is running. Open `http://<host-ip>:8080/slots/editor` in a browser (or the slot editor port you entered) and you should see the camera picture. Next, draw the bays in Step 2.

### Target {#rk3588_occupancy_local type=local device=rk3588 device_name="reComputer RK3588 (this machine)" config=devices/rk3588_occupancy.yaml}

Install on this machine when this app runs on the reComputer RK3588 itself.

### Deployment Complete

The last deploy step waits until bay detection is ready, so a successful deploy means the service is running. Open `http://127.0.0.1:8080/slots/editor` in a browser (or the slot editor port you entered) and you should see the camera picture. Next, draw the bays in Step 2.

## Step 2: Draw the Parking Bays {#draw_slots type=web_dashboard required=true config=devices/slot_editor.yaml}

Draw a box around every bay on each camera's picture and give it a bay number.

### Wiring

1. Open the slot editor (`http://<edge-box-ip>:8080/slots/editor`, or the port you entered when deploying) and pick a camera in the 流 (Stream) list. If no picture shows, click 刷新快照 (Refresh snapshot).
2. Deal with the example bay P-01 first: click inside it to select it and click 删除选中 (Delete selected), or drag its four corners onto a real bay, type its number in the id box and click 重命名选中 (Rename selected).
3. Type the bay number in the id box (for example B1-023), click 新车位 (New slot), click the bay's four corners on the picture in order, then click 闭合多边形 (Close polygon) — or click the first corner again.
4. Repeat Step 3 for every bay this camera can see.
5. Click 保存 (Save). The message 已保存并即时生效 (saved and applied) means it is done; the bays are kept across restarts.
6. Switch to the next camera in the 流 (Stream) list and repeat.

When drawing:

- One box per bay. A four-sided shape along the bay lines is enough; the shape must be convex (no corner pointing inwards).
- A parked car must cover roughly a third of its box in the picture to count as occupied. A box spanning several bays, or around distant small cars, never turns occupied.
- If a bay is mostly hidden by cars in front, draw it on a camera with a better angle.

### Deployment Complete

Bay detection is running and every bay you drew reports its state.

#### Initial Setup

1. Make sure the example bay P-01 has been deleted or turned into a real bay on every camera.
2. Subscribe your guidance signs, parking system or Home Assistant to `<site-id>/parking/<camera-id>/slots`. The camera ID is the one you entered when deploying; if you left it empty they are `cam-01`, `cam-02`, …

#### Quick Verification

1. On a computer that can reach the MQTT server, run `mosquitto_sub -h <mqtt-server-ip> -t '<site-id>/parking/+/slots' -v`
2. Every camera sends messages, with `stream_ok` set to `true`.
3. Drive a car into a bay you drew: about 3 s later that bay turns `occupied`; about 5 s after it leaves it turns back to `free`.

#### Reading the Bay States

Each message covers one camera and carries the current state of every bay on it:

| Field | Meaning |
|-------|---------|
| `camera_id` | Camera ID |
| `slots` | One entry per bay: `id` is the bay number, `state` is `occupied`, `free` or `unknown` |
| `occupied` / `free` / `unknown` | Number of occupied, free and unknown bays on this camera |
| `changed` | Bays whose state changed in this message; empty when the message comes from a stream dropping, recovering or a bay-list update |
| `stream_ok` | Whether the camera picture is fine. About 10 s after the stream drops it becomes `false` and the bays turn `unknown` |

Add up `free` across all cameras to get the free bays for the whole car park.

#### Next Steps

- Adjust bays at any time in the slot editor; changes apply on save.
- To add cameras, run Step 1 again and append the new camera's address at the end (if you entered camera IDs, keep the existing IDs for the existing cameras). Bays you have drawn are kept.

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Page does not open | Check the port matches the slot editor port from the deploy step and that this computer can reach the edge box |
| Picture is black or fails to load | That camera has no picture yet: wait a few seconds and click 刷新快照 (Refresh snapshot); if it persists, check the camera's RTSP address |
| One camera's bays stay `unknown` | The box cannot reach that camera: open its RTSP address in VLC on the same network and check the address, username, password and encoding (must be H.264) |
| "非凸" (not convex) after closing the polygon | One corner points inwards; click 撤销顶点 (Undo vertex) and click that corner again |
| "请先在 id 框输入车位名" (enter a bay name first) | Type the bay number in the id box before closing the polygon |
| "id 重复" (duplicate id) | Bay numbers must be unique on one camera; choose another |
| A car is parked but the bay stays `free` | The box is too large or the car too far away to cover a third of it; tighten the box to a single bay |
