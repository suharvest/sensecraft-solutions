## What this solution does

To know which bays in a car park are taken, the usual answer is a magnetic or ultrasonic sensor in every bay — each one wired, powered and maintained. This solution uses the IP cameras already on site instead: every bay a camera can see is a bay it can watch. You draw a box around each bay on a web page, the edge box keeps checking whether there is a car in each box, and it sends every bay's occupied / free state to your system for guidance signs, wayfinding or billing.

## Key benefits

| Benefit | Details |
|------|---------|
| No per-bay sensors | One camera covers every bay it can see; nothing to install or wire per bay |
| Changes reported within seconds | A bay turns occupied about 3 s after a car stops, and free about 5 s after it leaves |
| You draw the bays | Draw and name each bay over the live picture in a web page; it takes effect on save and survives restarts |
| Video stays on site | Pictures are analysed on the edge box; only bay states leave it, never video |
| A dead camera is visible | About 10 s after a camera stream drops, its bays turn `unknown` instead of repeating a stale state |

## Use cases

| Scenario | How it's used |
|------|--------|
| Underground car park guidance signs | A few cameras per level; add up free bays per level and show them at the entrance and on each level |
| Mall / office car park | Count free bays per zone and send drivers to zones that still have space |
| Reserved bays | Draw separate boxes for EV-charging or visitor bays and alert staff when one is taken |
| Bay utilisation | Log how long each bay is occupied to find peak hours and bays that sit empty |

## What you get after deployment

- **Slot editor**: open it in a browser, pick a camera, click around a bay to draw it, type its number (for example B1-023) and save.
- **Bay state messages**: one MQTT topic per camera, `<site-id>/parking/<camera-id>/slots`. Whenever any bay changes, a message lists every bay on that camera with its state (`occupied` / `free` / `unknown`) plus the occupied, free and unknown counts. Your guidance signs, parking system or Home Assistant subscribe to that topic.

## Usage Notes

### Core hardware

| Device | Role | Required |
|------|------|------|
| reComputer J30 (Jetson Orin Nano) | Runs bay detection; must be a Jetson Orin Nano module on JetPack 6.2 | Pick one |
| reComputer RK3588 | Runs bay detection on the board's built-in AI accelerator | Pick one |
| IP camera | Your existing cameras, able to send an H.264 RTSP stream | ✓ Required |
| MQTT server | Receives the bay states, for example an existing Mosquitto | ✓ Required |

Measured performance (each camera analysed at 1 frame per second):

| Edge box | Time per frame | Multiple cameras |
|------|------|------|
| reComputer J30 (Jetson Orin Nano) | about 6.5 ms | 6 cameras at once, 1 frame per second each, no dropped frames |
| reComputer RK3588 | about 37 ms | Add cameras one at a time and check each keeps updating |

### Network requirements

- Edge box, cameras and MQTT server on the same LAN; the edge box can reach each camera's RTSP address (usually port 554).
- The edge box needs internet access during deployment to download the program and the detection model; it runs offline afterwards.
- Your computer must reach port 8080 on the edge box (slot editor).

### Camera requirements

- Mount the camera high and angled down so each bay is clearly visible and not fully hidden by the car next to it.
- One box per bay. A parked car must cover roughly a third of its box to count as occupied; a large box spanning several bays, or around distant small cars, never turns occupied.
- The camera's sub-stream is enough, encoded as H.264.
