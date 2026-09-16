## Preset: A. reCamera Pro at the Door {#a_ai_camera}

The reCamera Pro recognises faces, decides whether to unlock, and drives the relay from its GPIO.

- **Server:** A Linux server with Docker (no GPU needed) for the face library, management console and MQTT broker.
- **Peripherals:** A relay module with a dry contact into the door controller's unlock input.

## Step 1: Deploy the Face Library and Console {#p1_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Starts the face library, MQTT broker and management console on one server.

### Prerequisites

- A Linux server with Docker and the compose plugin, reachable from the door devices. No GPU needed.
- Server clock synchronised by NTP; door devices take their time from it.
- Ports 8080 (face library), 8088 (console) and 1883 (MQTT) free on the server.
- Set **Door Device** to reCamera Pro for this preset.
- The signing key and admin token are generated automatically; find them under "Auto-generated secrets" at the bottom of this step. Sign in to the console with the admin token.

### Troubleshooting

| Issue | Solution |
|---|---|
| `docker compose` not found | Install `docker-compose-plugin` on the server. |
| `NTP is not synchronised` warning | Run `sudo timedatectl set-ntp true` on the server. |
| Port 8080 in use | Change Face Library Port, and use the same port in later Face Library URLs. |
| Port 8088 in use | Free port 8088; the console pages in later steps open on it. |
| Face library answers 404 | Normal before the first enrolment. |
| Console does not come up | Run `docker logs usa-web` on the server. |

### Target {#p1_facedb_remote type=remote config=devices/cloud_facedb.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p1_facedb_local type=local config=devices/cloud_facedb.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 2: Enrol People {#p1_register type=web_dashboard required=true config=devices/register_person.yaml}

Enrol each person with 3 to 8 photos in the console's Person Library.

### Prerequisites

- The admin token from Step 1.
- 3 to 8 clear, front-facing photos per person.
- Recognition Service URL filled in Step 1; without it enrolled people are not recognised.
- Known limitation: people enrolled here are not yet recognised by the reCamera Pro's on-device model. On this preset the step tests enrolment and delivery only.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused: fewer than three images | Upload at least 3 photos. |
| Door still refuses a newly enrolled person | Wait 30 s for the device to fetch the new version, then try again. |
| Rollback refused, naming a person | That person was deleted. Enrol or edit to publish a new version instead. |
| `model_tag` mismatch on the device | Point Recognition Service URL at the door device's recognition service, redeploy Step 1 and enrol again. |

## Step 3: Wire the Relay {#p1_wire type=manual required=true config=devices/p1_recamera_pro_wiring.yaml}

Connect the relay to the camera and the door controller.

### Wiring

![reCamera Pro relay wiring](gallery/wiring-recamera-pro.svg)

1. With a multimeter, confirm which header pin is GPIO 130 and that it outputs 3.3 V.
2. Camera GPIO 130 → relay SIG, 3.3 V → VCC, GND → GND. To test first, connect an LED with a series resistor between GPIO 130 and GND instead.
3. Relay COM and NO to the door controller's unlock input (COM and NC for a fail-safe magnetic lock).

### Troubleshooting

| Issue | Solution |
|---|---|
| GPIO 130 is used by another program | Use a free GPIO and enter its number in the next step. |

## Step 4: Activate and Configure F1 Door Access {#p1_install type=recamera_pro_app required=true config=devices/p1_recamera_pro.yaml}

Starts F1 Door Access on the camera and writes the door settings; any other app running on the camera is stopped.

### Prerequisites

Install F1 Door Access (0.1.5 or later) on the camera first:

1. Log in to the camera's web console and open the **App Center**.
2. Find **F1 Door Access**, choose **Install**, and wait for it to finish.

The server IP, port, match threshold and signing key are filled in from Step 1. Enter the door name, GPIO number, relay contact and the door state on power loss.

### Troubleshooting

| Issue | Solution |
|---|---|
| The app is reported as not installed | Install F1 Door Access from the App Center as described above. |
| `unknown parameter` | F1 Door Access is older than 0.1.5. Update it in the App Center and deploy again. |
| Activation times out | The first activation right after install is slow; retry once. |
| `npu.direct is busy` | Stop the other running app in the App Center, then deploy again. |
| The door opens once at power-up | The relay contact is set the wrong way; correct it and deploy again. |

## Step 5: Check the Library Reached the Device {#p1_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Check on the console's Devices page that the door device uses the version you just published.

### Prerequisites

- The door device is powered on and online.
- At least one person enrolled.

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` behind the server's `current` | Wait 30 s and reload the page. |
| `active_version` behind `desired_version` | Read `last_error`. Usually the match threshold differs from Step 1; redeploy the device step with the same value. |
| `signature.verified` is `null` | Normal. Signature failures appear in `last_error`. |
| `clock.valid` is `false` | Normal on devices without NTP. |
| A person listed under `only_on_device` | Someone enrolled on the device directly; the next version overwrites it. |
| The page is empty | No device has reported yet. Check the door device is online. |

## Step 6: Verify the Door {#p1_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

Test the door: an enrolled person opens it, a photo does not, remote unlock works.

### Prerequisites

- The door controller connected and at least one person enrolled.
- A printed photo of that person.
- The admin token from Step 1.

### Deployment Complete

1. Stand in front of the camera as an enrolled person: the relay clicks once and the console shows an allowed event.
2. Step back and forward right away: the console shows `debounced` and the relay does not click again.
3. Hold up the printed photo: the console shows `liveness_failed` and the relay does not click.
4. On the console's Devices page, click unlock: the relay clicks once and the receipt shows `executed`.
5. Delete a person: within 30 s the door no longer opens for them, and rolling back to a version that still contains them is refused.
6. Before real use: switch the MQTT broker to TLS with per-device accounts, and put the console behind HTTPS.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photo opens the door | Take the door out of service and check the recognition service `/health` reports liveness `loaded`. |
| Receipt says `executed` but the relay does not click | Check the relay wiring and the pin set on the device. |
| Relay clicks twice per approach | Increase the debounce window on the device, then test again. |
| Audit verification fails | Keep the log file and check whether two processes write to it. |
| Events stop but the door still opens | The camera unlocks locally; check its connection to the MQTT broker on port 1883. |

## Preset: B. reCamera PoE {#a_recamera_poe}

A reCamera 2002 HQ PoE recognises faces, decides whether to unlock, and drives the relay from its own baseboard header. The unlock path does not go over the network.

- **Server:** A Linux server with Docker (no GPU needed) for the face library, management console and MQTT broker.
- **Camera:** reCamera 2002 HQ PoE, powered over PoE.
- **Peripherals:** A Grove Relay (SKU 103020005, SPST-NO, 3.3-5 V trigger) on baseboard header D1, with a dry contact into the door controller's unlock input. For a normally-closed controller input, use the Grove SPDT Relay 30A (SKU 103020012) instead.

## Step 1: Deploy the Face Library and Console {#p6_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Starts the face library, MQTT broker and management console on one server.

### Prerequisites

- A Linux server with Docker and the compose plugin, reachable from the door devices. No GPU needed.
- Server clock synchronised by NTP; door devices take their time from it.
- Ports 8080 (face library), 8088 (console) and 1883 (MQTT) free on the server.
- Set **Door Device** to standard reCamera for this preset.
- The signing key and admin token are generated automatically; find them under "Auto-generated secrets" at the bottom of this step. Sign in to the console with the admin token.

### Troubleshooting

| Issue | Solution |
|---|---|
| `docker compose` not found | Install `docker-compose-plugin` on the server. |
| `NTP is not synchronised` warning | Run `sudo timedatectl set-ntp true` on the server. |
| Port 8080 in use | Change Face Library Port, and use the same port in later Face Library URLs. |
| Port 8088 in use | Free port 8088; the console pages in later steps open on it. |
| Face library answers 404 | Normal before the first enrolment. |
| Console does not come up | Run `docker logs usa-web` on the server. |

### Target {#p6_facedb_remote type=remote config=devices/cloud_facedb.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p6_facedb_local type=local config=devices/cloud_facedb.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 2: Enrol People {#p6_register type=web_dashboard required=true config=devices/register_person.yaml}

Enrol each person with 3 to 8 photos in the console's Person Library.

### Prerequisites

- The admin token from Step 1.
- 3 to 8 clear, front-facing photos per person.
- Recognition Service URL filled in Step 1; without it enrolled people are not recognised.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused: fewer than three images | Upload at least 3 photos. |
| Door still refuses a newly enrolled person | Wait 30 s for the device to fetch the new version, then try again. |
| Rollback refused, naming a person | That person was deleted. Enrol or edit to publish a new version instead. |
| `model_tag` mismatch on the device | Point Recognition Service URL at the door device's recognition service, redeploy Step 1 and enrol again. |

## Step 3: Install F1 Access on the Camera {#p6_install type=recamera_cpp required=true config=devices/p6_recamera_poe.yaml}

Installs the door access app on the reCamera PoE and writes its face library settings.

### Prerequisites

- The camera on USB-C (IP `192.168.42.1`) or on your network, and the `recamera` SSH password.
- The camera can reach `http://<server IP>:8080`.
- About 20 MB free on `/userdata`.

### Wiring

![reCamera 2002 HQ PoE relay wiring](gallery/wiring-recamera-2002-poe.svg)

You need: a Grove Relay (SKU 103020005), its 4-wire Grove cable, jumper wires (the header is not a Grove socket, so the far end of the cable breaks out into single wires), a 3.3-5 V supply, and a multimeter.

Header pinout ([vendor wiki](https://wiki.seeedstudio.com/reCamera_hq_poe_hardware_and_specs/)): **GND, GPIO488, GPIO487, TX, GPIO490, RX**. The three IO ports are D1 = GPIO490, CLK = GPIO487, SMD = GPIO488; this solution uses D1.

1. **The header has no supply pin.** Power the relay's VCC separately: a 5 V USB charger, or the door side's existing 12 V stepped down to 5 V, with its ground tied to the header GND. A GPIO drives 3.3 V logic levels, while the Grove Relay draws 100 mA, so the GPIO carries SIG only. This route needs no XIAO.
2. **The levels are undocumented.** Measure GPIO490's high level with a multimeter before connecting the relay.
3. **Connect three wires**, leaving the relay's NC wire unconnected: header GPIO490 → relay **SIG**, the external 3.3-5 V → **VCC**, header GND → **GND** (the external supply's ground lands here too).
4. **Test with an LED first.** Put an LED with a series resistor between GPIO490 and GND, deploy, and check that it lights once for the configured pulse width. Then swap in the relay.
5. **Confirm one click per pulse.** If the relay does not click, go back to step 2 and re-check the level.
6. **Connect the door controller.** Relay **COM** and **NO** go to its unlock input; neither terminal carries any voltage of ours. A lock that opens on power loss needs a normally-closed contact, which the Grove Relay does not have — use the Grove SPDT Relay 30A (SKU 103020012) and wire COM and NC.
7. In the form, fill Device ID and Actuator ID. Face Library URL, Match Threshold and the signing key are carried over from Step 1; change the URL only if the camera reaches the server at a different address. Then deploy.

### Troubleshooting

| Issue | Solution |
|---|---|
| The stock face-recognition app is still on the camera | Remove `face-recognition` on the camera, then deploy again. |
| `agent.log` ends with `thresholds are not single-sourced` | Deploy this step again; do not hand-edit `/userdata/f1-access/face-recognition.conf`. |
| No library version ever activates | Check the camera reaches Face Library URL; if Match Threshold was changed away from the Step 1 value, set it back and deploy again. |
| The door opens once at start-up | The active level is wrong. Fix it before connecting the door controller. |
| The relay never clicks | Check D1 is on the header pin you wired, and that `[gpio] enabled = true` in `/userdata/f1-access/face-recognition.conf`. |

## Step 4: Check the Library Reached the Device {#p6_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Check on the console's Devices page that the door device uses the version you just published.

### Prerequisites

- The camera is powered on and online.
- At least one person enrolled.
- The camera listed in Device Control Endpoints in Step 1.

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` behind the server's `current` | Wait 30 s and reload the page. |
| `active_version` behind `desired_version` | Read `last_error`. Usually the match threshold differs from Step 1; redeploy the device step with the same value. |
| `signature.verified` is `null` | Normal. Signature failures appear in `last_error`. |
| `clock.valid` is `false` | Normal on devices without NTP. |
| A person listed under `only_on_device` | Someone enrolled on the device directly; the next version overwrites it. |
| The page is empty | Fill Device Control Endpoints in Step 1 and redeploy it. |

## Step 5: Verify the Door {#p6_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

Test the door: an enrolled person opens it, a photo does not, remote unlock works.

### Prerequisites

- The door controller connected and at least one person enrolled.
- A printed photo of that person.
- The admin token from Step 1.

### Deployment Complete

1. Stand in front of the camera as an enrolled person: the relay clicks once and the console shows an allowed event.
2. Step back and forward right away: the console shows `debounced` and the relay does not click again.
3. Hold up the printed photo: the console shows `liveness_failed` and the relay does not click.
4. On the console's Devices page, click unlock: the relay clicks once and the receipt shows `executed`.
5. Delete a person: within 30 s the door no longer opens for them, and rolling back to a version that still contains them is refused.
6. Unplug the server and stand in front of the camera: the door still opens.
7. Before real use: switch the MQTT broker to TLS with per-device accounts, and put the console behind HTTPS.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photo opens the door | Take the door out of service and check the recognition service `/health` reports liveness `loaded`. |
| Receipt says `executed` but the relay does not click | Check the header D1 wiring and the relay's trigger level. |
| Relay clicks twice per approach | Increase the debounce window on the device, then test again. |
| Audit verification fails | Keep the log file and check whether two processes write to it. |
| No events in the console | Check the camera can reach the server on port 1883. |

## Preset: C. Standard reCamera (2002 / 2002w) {#a_recamera_std}

A reCamera 2002 or 2002w recognises faces and decides whether to unlock. The camera has no usable header, so the unlock goes over MQTT to a relay node.

- **Server:** A Linux server with Docker (no GPU needed) for the face library, management console and MQTT broker.
- **Camera:** reCamera 2002 or 2002w.
- **Relay node:** An R1000 or XIAO ESP32-S3 on the same MQTT broker, with a relay module whose dry contact goes into the door controller's unlock input. The door does not open while the broker is down.

## Step 1: Deploy the Face Library and Console {#p5_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Starts the face library, MQTT broker and management console on one server.

### Prerequisites

- A Linux server with Docker and the compose plugin, reachable from the door devices. No GPU needed.
- Server clock synchronised by NTP; door devices take their time from it.
- Ports 8080 (face library), 8088 (console) and 1883 (MQTT) free on the server.
- Set **Door Device** to standard reCamera for this preset.
- The signing key and admin token are generated automatically; find them under "Auto-generated secrets" at the bottom of this step. Sign in to the console with the admin token.

### Troubleshooting

| Issue | Solution |
|---|---|
| `docker compose` not found | Install `docker-compose-plugin` on the server. |
| `NTP is not synchronised` warning | Run `sudo timedatectl set-ntp true` on the server. |
| Port 8080 in use | Change Face Library Port, and use the same port in later Face Library URLs. |
| Port 8088 in use | Free port 8088; the console pages in later steps open on it. |
| Face library answers 404 | Normal before the first enrolment. |
| Console does not come up | Run `docker logs usa-web` on the server. |

### Target {#p5_facedb_remote type=remote config=devices/cloud_facedb.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p5_facedb_local type=local config=devices/cloud_facedb.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 2: Enrol People {#p5_register type=web_dashboard required=true config=devices/register_person.yaml}

Enrol each person with 3 to 8 photos in the console's Person Library.

### Prerequisites

- The admin token from Step 1.
- 3 to 8 clear, front-facing photos per person.
- Recognition Service URL filled in Step 1; without it enrolled people are not recognised.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused: fewer than three images | Upload at least 3 photos. |
| Door still refuses a newly enrolled person | Wait 30 s for the device to fetch the new version, then try again. |
| Rollback refused, naming a person | That person was deleted. Enrol or edit to publish a new version instead. |
| `model_tag` mismatch on the device | Point Recognition Service URL at the door device's recognition service, redeploy Step 1 and enrol again. |

## Step 3: Install F1 Access on the Camera {#p5_install type=recamera_cpp required=true config=devices/p5_recamera_std.yaml}

Installs the door access app on the reCamera and writes its face library settings.

### Prerequisites

- The camera on USB-C (IP `192.168.42.1`) or on your network, and the `recamera` SSH password.
- The camera can reach `http://<server IP>:8080`.
- About 20 MB free on `/userdata`.
- An R1000 or XIAO ESP32-S3 relay node connected to the same MQTT broker, and the Relay ID set on it.

### Wiring

![XIAO ESP32-S3 relay wiring](gallery/wiring-xiao-relay.svg)

1. The camera has no usable header. Wire the relay to the relay node: XIAO ESP32-S3 relay firmware GPIO → relay SIG, 3V3 → VCC, GND → GND; on an R1000, wire the relay to the output behind its Modbus Point ID.
2. Connect relay COM and NO to the door controller's unlock input (use COM and NC for a lock that opens on power loss).
3. In the form, fill Device ID and set Actuator ID to the Relay ID configured on the relay node. Face Library URL, Match Threshold and the signing key are carried over from Step 1; change the URL only if the camera reaches the server at a different address. Then deploy.

### Troubleshooting

| Issue | Solution |
|---|---|
| The stock face-recognition app is still on the camera | Remove `face-recognition` on the camera, then deploy again. |
| `agent.log` ends with `thresholds are not single-sourced` | Deploy this step again; do not hand-edit `/userdata/f1-access/face-recognition.conf`. |
| No library version ever activates | Check the camera reaches Face Library URL; if Match Threshold was changed away from the Step 1 value, set it back and deploy again. |
| `mqtt.host` mismatch | Set `[mqtt] host = localhost` in `/userdata/f1-access/face-recognition.conf`. |
| Unlock sent but the relay does not click | Check the relay node is connected to the broker and its Relay ID matches Actuator ID. |

## Step 4: Check the Library Reached the Device {#p5_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Check on the console's Devices page that the door device uses the version you just published.

### Prerequisites

- The camera is powered on and online.
- At least one person enrolled.
- The camera listed in Device Control Endpoints in Step 1.

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` behind the server's `current` | Wait 30 s and reload the page. |
| `active_version` behind `desired_version` | Read `last_error`. Usually the match threshold differs from Step 1; redeploy the device step with the same value. |
| `signature.verified` is `null` | Normal. Signature failures appear in `last_error`. |
| `clock.valid` is `false` | Normal on devices without NTP. |
| A person listed under `only_on_device` | Someone enrolled on the device directly; the next version overwrites it. |
| The page is empty | Fill Device Control Endpoints in Step 1 and redeploy it. |

## Step 5: Verify the Door {#p5_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

Test the door: an enrolled person opens it, a photo does not, remote unlock works.

### Prerequisites

- The door controller connected and at least one person enrolled.
- A printed photo of that person.
- The admin token from Step 1.

### Deployment Complete

1. Stand in front of the camera as an enrolled person: the relay clicks once and the console shows an allowed event.
2. Step back and forward right away: the console shows `debounced` and the relay does not click again.
3. Hold up the printed photo: the console shows `liveness_failed` and the relay does not click.
4. On the console's Devices page, click unlock: the relay clicks once and the receipt shows `executed`.
5. Delete a person: within 30 s the door no longer opens for them, and rolling back to a version that still contains them is refused.
6. Before real use: switch the MQTT broker to TLS with per-device accounts, and put the console behind HTTPS.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photo opens the door | Take the door out of service and check the recognition service `/health` reports liveness `loaded`. |
| Receipt says `executed` but the relay does not click | Check the relay wiring and the pin set on the relay node. |
| Relay clicks twice per approach | Increase the debounce window on the device, then test again. |
| Audit verification fails | Keep the log file and check whether two processes write to it. |
| No events in the console | Check the camera can reach the server on port 1883. |

## Preset: D. AI Host with Your Existing Cameras {#b_ai_host}

The AI host pulls the stream from the existing RTSP camera at the door, recognises faces and decides whether to unlock.

- **Server:** A Linux server with Docker (no GPU needed) for the face library, management console and MQTT broker.
- **Camera:** The existing RTSP camera at the door.
- **Peripherals:** A relay module with a dry contact into the door controller's unlock input.

## Step 1: Deploy the Face Library and Console {#p2_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Starts the face library, MQTT broker and management console on one server.

### Prerequisites

- A Linux server with Docker and the compose plugin, reachable from the door devices. No GPU needed.
- Server clock synchronised by NTP; door devices take their time from it.
- Ports 8080 (face library), 8088 (console) and 1883 (MQTT) free on the server.
- Set **Door Device** to AI host for this preset.
- The signing key and admin token are generated automatically; find them under "Auto-generated secrets" at the bottom of this step. Sign in to the console with the admin token.

### Troubleshooting

| Issue | Solution |
|---|---|
| `docker compose` not found | Install `docker-compose-plugin` on the server. |
| `NTP is not synchronised` warning | Run `sudo timedatectl set-ntp true` on the server. |
| Port 8080 in use | Change Face Library Port, and use the same port in later Face Library URLs. |
| Port 8088 in use | Free port 8088; the console pages in later steps open on it. |
| Face library answers 404 | Normal before the first enrolment. |
| Console does not come up | Run `docker logs usa-web` on the server. |

### Target {#p2_facedb_remote type=remote config=devices/cloud_facedb.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p2_facedb_local type=local config=devices/cloud_facedb.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 2: Enrol People {#p2_register type=web_dashboard required=true config=devices/register_person.yaml}

Enrol each person with 3 to 8 photos in the console's Person Library.

### Prerequisites

- The admin token from Step 1.
- 3 to 8 clear, front-facing photos per person.
- Recognition Service URL filled in Step 1; without it enrolled people are not recognised.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused: fewer than three images | Upload at least 3 photos. |
| Door still refuses a newly enrolled person | Wait 30 s for the device to fetch the new version, then try again. |
| Rollback refused, naming a person | That person was deleted. Enrol or edit to publish a new version instead. |
| `model_tag` mismatch on the device | Point Recognition Service URL at the door device's recognition service, redeploy Step 1 and enrol again. |

## Step 3: Deploy the Access Node {#p2_deploy type=docker_deploy required=true config=devices/p2_j20.yaml}

Starts recognition and the access node on the host. Pick the target that matches your host and relay wiring.

### Prerequisites

- Docker and the compose plugin on the host.
- The camera's RTSP URL, tested from the host itself.
- Access to `sensecraft-statics.seeed.cc` to download about 32 MB of model files.
- At least 15 GB free disk. The first start takes about 4 minutes (measured on a reComputer J40).
- The door lock type: opens on power loss (fail-safe) or stays locked (fail-secure).

### Troubleshooting

| Issue | Solution |
|---|---|
| `access-node` restarts and the log shows `config error:` | Run `docker compose exec access-node access-node check-config` to see the rejected field. |
| `access-node` stays `unhealthy` | Run `docker compose exec access-node access-node healthcheck` to see which part is down. |
| `LIVENESS IS NOT LOADED` | Check the model download finished, then deploy again. |
| RTSP plays on your laptop but not on the host | Check the host's route to the camera and the RTSP credentials. |
| Plaintext library URL refused | Deploy Step 1 first so the signing key exists, then deploy this step again. |
| The door opens once at start-up | Active Level is inverted. Change it before connecting the door controller. |

### Target {#p2_j20 type=remote device=recomputer_j20 device_name="reComputer J20" config=devices/p2_j20.yaml default=true}

The relay connects to the J20's DO output. Set **GPIO Interface = sysfs** and enter the DO's sysfs number.

### Wiring

![AI host relay wiring](gallery/wiring-host-relay.svg)

1. With a multimeter, confirm which sysfs number drives which DO terminal (DO1–DO4 are expected at 463/464/465/462) and the DO output type.
2. Wire the DO terminal → relay SIG, and power the relay's VCC and GND.
3. Connect relay COM and NO to the door controller's unlock input (use COM and NC for a lock that opens on power loss).
4. In the form, set GPIO Interface `sysfs`, DO sysfs GPIO Number, Active Level, Relay Contact and Fail Mode.

### Troubleshooting

| Issue | Solution |
|---|---|
| `gpio N is ALREADY EXPORTED` | Another program uses that output. Choose another DO or stop that program. |

### Target {#p2_jetson type=remote device=recomputer_j40 device_name="reComputer J30 / J40" config=devices/p2_j20.yaml}

The relay connects to the 40-pin header. Set **GPIO Interface = libgpiod**, **GPIO Chip = gpiochip0**, and the line offset from this table:

| Header pin | Name | `gpiochip0` line |
|---|---|---|
| 7  | GPIO09    | 144 |
| 11 | UART1_RTS | 112 |
| 12 | I2S0_SCLK | 50  |
| 13 | SPI1_SCK  | 122 |
| 15 | GPIO12    | 85  |
| 16 | SPI1_CS1  | 126 |
| 18 | SPI1_CS0  | 125 |
| 22 | SPI1_MISO | 123 |
| 29 | GPIO01    | 105 |
| 31 | GPIO11    | 106 |
| 32 | GPIO07    | 41  |
| 33 | GPIO13    | 43  |
| 35 | I2S0_FS   | 53  |
| 36 | UART1_CTS | 113 |
| 37 | SPI1_MOSI | 124 |
| 38 | I2S0_SDIN | 52  |
| 40 | I2S0_SDOUT| 51  |

Pins 1/17 are 3V3, 2/4 are 5V, and 6/9/14/20/25/30/34/39 are GND.

### Wiring

![AI host relay wiring](gallery/wiring-host-relay.svg)

1. Run `gpioinfo` on the host and pick a line from the table that is not marked `[used]`.
2. Wire pin 31 (line 106) → relay SIG, pin 1 (3V3) → VCC, pin 6 (GND) → GND. To test first, connect an LED with a resistor between pin 31 and GND instead.
3. Connect relay COM and NO to the door controller's unlock input (use COM and NC for a lock that opens on power loss).
4. In the form, set GPIO Interface `libgpiod`, GPIO Chip `gpiochip0`, GPIO Line Offset `106`, Active Level, Relay Contact and Fail Mode.

### Troubleshooting

| Issue | Solution |
|---|---|
| `/dev/gpiochip0 does not exist on this box` | Run `gpioinfo` and enter the chip name it lists. |

### Target {#p3_mqtt_relay type=remote device=mqtt_relay device_name="MQTT Relay" config=devices/p3_mqtt_relay.yaml}

Choose this when the host is not at the door or serves several doors. Unlocks go over MQTT to a relay node; the door does not open while the broker is down.

### Prerequisites

- The MQTT broker (Step 1 server, port 1883) reachable from the host.
- The relay node running and connected to the broker, with a Relay ID unique on the site.

### Wiring

![XIAO ESP32-S3 relay wiring](gallery/wiring-xiao-relay.svg)

1. XIAO ESP32-S3: wire the relay firmware's GPIO → relay SIG, 3V3 → VCC, GND → GND; confirm the GPIO with a multimeter before wiring.
2. reComputer R1000: wire the relay to the output behind the Modbus Point ID you enter in the form.
3. Connect relay COM and NO to the door controller's unlock input (use COM and NC for a lock that opens on power loss).
4. In the form, set Relay Backend, Relay ID, Relay Contact and Fail Mode.

### Troubleshooting

| Issue | Solution |
|---|---|
| `Cannot reach the MQTT broker` | Check the host can reach the server on port 1883. |
| `No retained state from relay` | The relay node has not connected to the broker. Check its network and Relay ID. |
| Unlock accepted, relay does not click | Subscribe to `access/v1/relay/<id>/state` and read `result` (`duplicate`, `expired` or `rejected`). |
| The door opens by itself after a power cut | Something publishes to `access/v1/relay/<id>/set` with retain on. Turn retain off. |
| Pulse width rejected | Use 500–5000 ms. |

## Step 4: Check the Library Reached the Device {#p2_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Check on the console's Devices page that the door device uses the version you just published.

### Prerequisites

- The door device is powered on and online.
- At least one person enrolled.

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` behind the server's `current` | Wait 30 s and reload the page. |
| `active_version` behind `desired_version` | Read `last_error`. Usually the match threshold differs from Step 1; redeploy the device step with the same value. |
| `signature.verified` is `null` | Normal. Signature failures appear in `last_error`. |
| `clock.valid` is `false` | Normal on devices without NTP. |
| A person listed under `only_on_device` | Someone enrolled on the device directly; the next version overwrites it. |
| The page is empty | No device has reported yet. Check the door device is online. |

## Step 5: Verify the Door {#p2_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

Test the door: an enrolled person opens it, a photo does not, remote unlock works.

### Prerequisites

- The door controller connected and at least one person enrolled.
- A printed photo of that person.
- The admin token from Step 1.

### Deployment Complete

1. Stand in front of the camera as an enrolled person: the relay clicks once and the console shows an allowed event.
2. Step back and forward right away: the console shows `debounced` and the relay does not click again.
3. Hold up the printed photo: the console shows `liveness_failed` and the relay does not click.
4. On the console's Devices page, click unlock: the relay clicks once and the receipt shows `executed`.
5. Delete a person: within 30 s the door no longer opens for them, and rolling back to a version that still contains them is refused.
6. Before real use: switch the MQTT broker to TLS with per-device accounts, and put the console behind HTTPS.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photo opens the door | Take the door out of service and check the recognition service `/health` reports liveness `loaded`. |
| Receipt says `executed` but the relay does not click | Check the relay wiring and the pin set on the device. |
| Relay clicks twice per approach | Increase the debounce window on the device, then test again. |
| Audit verification fails | Keep the log file and check whether two processes write to it. |
| Container restarts in a loop | Run `docker logs usa-access-node` to see the rejected setting. |
