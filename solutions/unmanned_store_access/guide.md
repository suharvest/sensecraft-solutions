## Preset: On-Device — reCamera Pro {#p1_recamera_pro}

**Choosing a preset.** There is no automatic matching in this release. The app's
network discovery cannot tell a reCamera Pro from a standard reCamera, and it
cannot see whether a gateway is present at all, so the preset is chosen by hand
from this table. Find the device you have, read across to how the lock is
switched, and that is the preset.

| Door device | How the lock is switched | Preset |
|---|---|---|
| reCamera Pro | The camera's own GPIO into a relay | On-Device — reCamera Pro |
| reComputer Industrial J20 + an existing RTSP camera | The J20's opto-isolated DO into a relay | Industrial Box |
| Standard reCamera (2002 / 2002w / 2002 HQ PoE) | Events over MQTT; relay at the gateway | Standard reCamera |
| reComputer J30 / J40 / R2000 + an existing RTSP camera | Events over MQTT; relay at the gateway | MQTT Relay |
| Grove Vision AI V2 + XIAO ESP32-S3 | The XIAO's GPIO into a Grove Relay | XIAO + Grove Vision AI V2 |

Two rows are easy to get wrong. A standard reCamera is not a cheaper reCamera
Pro: it recognises on the camera but drives no lock at all, so it takes the
gateway-relay path even when the gateway is standing next to it. And the Grove
Vision AI V2 preset has no liveness model — a printed photograph opens that door
— so it is not a substitute for the others on price alone.


Recognition, liveness, the decision and the contact all live in one device at
the door. Nothing on the network sits between a face and the lock, so the door
keeps working while the network is down — the network carries library updates,
events and remote commands only.

The cost is the install. reCamera Pro is a Buildroot device with no Docker, no
dpkg and no systemd; its applications run as root under `appmgr`, so this preset
extends the camera's existing face-recognition app rather than installing a
package, and the deployment engine has no step type for that. Those steps are
manual, with the reason recorded in the device file rather than dressed up.

| Device | Purpose |
|---|---|
| Cloud / on-prem host | Face library server, management console, MQTT broker |
| reCamera Pro or reCamera PoE / HQ PoE | Camera, recognition, liveness, decision, GPIO output |
| Relay module | Switches the lock. Sized for the lock, matched to the pin's voltage |
| Lock + its own 12/24 V supply | Never powered from the camera |

**Important.** This is not a certified security or life-safety system, and no
part of it has run on hardware. Six of the seven boundary metrics are empty; the
seventh is a loopback timing on a development machine. The face embedding
weights are non-commercial (see the licensing section on the solution page).

Known weaknesses, none of them measured:

- **No recognition or liveness figure exists.** Not on this hardware, not on
  any. The default threshold is a starting point to be calibrated, not a result.
- **Backlit doorways and glass reflections** are the usual failure modes and
  have not been characterised.
- **No pin can be assumed free.** The surveyed unit had `gpio131` already
  exported and driven by another application.
- **The device clock was about seven months out with no NTP client.** HTTPS
  fails on it until that is addressed.

## Step 1: Deploy the Face Library Server {#p1_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Brings up the library server, the broker and the console container on the cloud
or on-prem host, and writes the signing key and the first console token.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from the door. No
  GPU needed.
- **Its clock must be right.** Door devices with no working RTC take their time
  correction from this server's HTTP `Date` header, so a wrong clock here
  misdates every audit record in the installation.
- **The container image has not been pushed.** The compose file names the tag it
  will have and carries the build command in its header. Build it on the host
  from the upstream repository and retag before running this step.
- A signing key: `openssl rand -hex 32`. It is required, not optional — a device
  on a plaintext library URL refuses to start without it.

### Troubleshooting

| Issue | Solution |
|---|---|
| Image pull fails | Expected until the image is pushed. Build it on the host from the upstream repository and retag it to the name in the compose file. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Library endpoint answers 404 | Correct before the first enrolment — there is no published version yet. It becomes 200 after Step 3. |
| `NTP is not synchronised` warning | Fix it now, not later. Timestamps on every device downstream depend on this host. |
| Port 8080 already in use | Change the library port in the wizard; devices are given the same value. |

## Step 2: Deploy the Management Console {#p1_cloud_web type=docker_deploy required=true config=devices/cloud_web.yaml}

Configures the three role tokens and brings the console up on the same host and
the same compose project, so it shares the library volume with the server.

### Prerequisites

- Step 1 finished and the library endpoint answering.
- Three tokens decided: admin enrols, deletes and rolls back; operator opens the
  door remotely; viewer reads only. Only the admin token is mandatory.
- A reverse proxy terminating TLS in front of the console before anyone outside
  the local network reaches it. A shared bearer token over plain HTTP is not
  authentication.

### Troubleshooting

| Issue | Solution |
|---|---|
| "The face library server is not answering" | Step 1 has not finished, or the library port differs. The step checks before touching anything. |
| Anonymous `GET /api/events` returns 200 | The token gate is not in front of the data. Stop and investigate — the step prints this check's result. |
| Console starts, person library empty | Correct before the first enrolment. |
| Enrolled people are never recognised | The console fell back to a fake embedder because the recognition service URL was left empty. Set it and re-enrol; a library built that way cannot be repaired. |

## Step 3: Enrol People {#p1_register type=web_dashboard required=true config=devices/register_person.yaml}

Opens the console's person library. Enrol each person from 3 to 8 photographs;
each enrolment mints a new library version.

### Prerequisites

- The admin token from Step 2.
- 3–8 photographs per person. Fewer than three is rejected: one photograph tells
  the matcher nothing about how much this face varies, and a library built that
  way fails in the field rather than at enrolment.
- The recognition service URL configured in Step 2, so embeddings come from the
  real model.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused with "fewer than three images" | By design. Supply at least three. |
| A new version appears but the door still refuses the person | Wait one poll period plus the download — 30 s by default. The device switches only after SHA and signature verify. |
| Rollback refused naming a person | The deletion barrier. Mint a new version instead; that refusal is the mechanism working. |
| `model_tag` mismatch on the device | The library was built against a different embedding model. Rebuild it against the one the door actually runs. |

## Step 4: Install the Door App on the Camera {#p1_install type=manual required=true config=devices/p1_recamera_pro.yaml}

Reach the camera as root, find and measure a free pin, wire LED then relay then
lock, install the app, and settle the clock question.

### Prerequisites

- Root SSH access to the camera. The `admin` account has no sudo, `su` is not
  setuid, and `/sys/class/gpio` is root-only — an app running as `admin` gets
  EACCES the moment it writes a pin.
- The existing face-recognition app running: `curl -s localhost:8125/gallery` on
  the device should return a model tag and a user list. Write the model tag
  down; the library must be built to match it.
- A meter. Pin numbers, polarity and available drive current are measured, never
  assumed.

### Wiring

In this order, and do not skip ahead.

1. **LED with a series resistor on the pin.** Confirm the polarity and the pulse
   width are what you configured. Nothing else is connected yet.
2. **Relay module on its own supply.** Confirm the contact clicks once per
   pulse. Match the module to the pin: reCamera Pro's native outputs swing
   12–21 V, while a UART or CAN pin reconfigured as GPIO gives 3.3 V.
3. **Lock, on a separate 12/24 V supply, through the relay contact.** A
   fail-safe magnetic lock through COM and NC; a fail-secure strike through COM
   and NO. The lock draws 300 mA–1 A and the pin must never see that current.

Getting the contact backwards on a magnetic lock leaves the door open
permanently and looks like a working installation until somebody tests it. This
is why `relay_contact` and `fail_mode` have no default values.

### Troubleshooting

| Issue | Solution |
|---|---|
| `EACCES` writing to `/sys/class/gpio` | The app is running as `admin`. It must run as root under `appmgr`. |
| The actuator refuses to start, naming a pin | The pin is already exported with a direction or value that disagrees with the configured idle state. Find out what owns it. Do not force a takeover to make the message go away. |
| `certificate is not yet valid` on the library URL | The device clock is months out and it has no NTP client. Either give it a way to correct time and use HTTPS, or move the library to a plaintext LAN URL with the signing key set. |
| The app refuses to start on a plaintext library URL | No signing key. That refusal is deliberate: on a plaintext URL the manifest signature is the whole integrity boundary. |
| The door pulses once at boot | The active level is inverted. Fix it before reconnecting the lock. |
| Two pulses per approach | The debounce is not in the path, or its window is shorter than the time somebody spends in frame. |

## Step 5: Check the Library Reached the Device {#p1_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Open the console's device page and confirm that the version you published is the
version the door device is actually matching against. Do this before putting a
face in front of the camera: a door that will not open because the library never
activated looks exactly like a door that will not open because recognition
failed, and only this page tells them apart.

### Prerequisites

- The door device from the previous step is powered, on the network and running.
- At least one person enrolled, so there is a version to activate.
- A viewer token, and — for devices with an MQTT command channel — that device
  listed in the console's `USA_DEVICE_ENDPOINTS`. An empty list makes this page
  read as "no devices" rather than "not configured".

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` is behind the server's `current` | The device has not polled yet. One poll period is 30 s by default; wait, then reload. |
| `desired_version` matches, `active_version` lags | The device saw the version and could not activate it. `last_error` says why — usually a signing key id or secret that differs from the console's, a `match_threshold` that differs from `USA_MATCH_THRESHOLD`, or a manifest with no `artifacts.gallery_v2`. |
| `signature.verified` is `null` | No version has been verified yet. That is not a failed verification. |
| `clock.valid` is `false` | Expected on a device with no NTP. The integrity boundary is the manifest signature, not the clock. |
| A person appears under `only_on_device` | Somebody enrolled locally, bypassing the cloud. The next activation overwrites it. Find out who did it and why. |
| The page is empty | `USA_DEVICE_ENDPOINTS` is `[]`, or no device has ever reported. Check the console's environment file first. |

## Step 6: Verify the Door End to End {#p1_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

An enrolled person opens the door once; a photograph does not open it at all; a
remote unlock produces a receipt; a delete cannot be rolled back.

### Prerequisites

- Steps 1–4 finished, the lock connected, and someone enrolled in the current
  library version.
- A printed photograph of that same person.
- An operator token and a viewer token, to check that the role gate holds in
  both directions.

### Deployment Complete

The door is installed and the four behaviours that matter have been observed
directly rather than inferred from a container being up.

#### Quick verification

1. Reproduce the software half, which needs no hardware:
   `uv run python tools/verify_software_loop.py` from a clone of the upstream
   repository. The reference run reports 52 of 52 checks passing.
2. Stand in front of the camera as an enrolled person. Expect exactly one
   contact closure of the configured width, one allowed event in the console,
   and the audit chain one record longer.
3. Step back and forward within the debounce window. Expect a second event with
   reason `debounced` and **no** second pulse.
4. Hold the printed photograph up to the camera. Expect `liveness_failed` and no
   pulse. If the door opens, stop: check that the recognition service reports
   liveness as loaded.
5. As an operator, issue a remote unlock from the console. Expect one closure
   and a receipt reaching the executed state. Repeat as a viewer: expect a
   refusal.
6. Delete an enrolled person, then try to roll back to a version that still
   contained them. Expect a refusal naming that person, with the current version
   unchanged.
7. Run the console's audit verification. Expect the chain to verify.

#### Next steps

- Calibrate the threshold on the installed camera with positive and negative
  pairs. The shipped value is a starting point, not a result.
- Replace the bundled broker configuration. It is anonymous plaintext; an unlock
  topic that accepts anonymous publishes is not access control. Move to TLS,
  per-device identities and topic ACLs.
- Put a TLS-terminating reverse proxy in front of the console.
- Record what you measured — pin, level, current, pulse width, contact, lock
  type — with the installation. The next person to touch it has no way to
  recover those from the software.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photograph opens the door | Liveness is not in the path. Check `/health` reports liveness loaded; the adapter is supposed to refuse to start otherwise. Take the door out of service until this is resolved. |
| Remote unlock returns a receipt but the contact never closes | The decision reached the actuator and the actuator did not act. Check the pin's health output and the wiring, not the broker. |
| A replayed command opens the door twice | The replay table is not in the path. Nothing else about the command gate can be trusted either; stop and investigate. |
| Audit verification fails | Either the log was edited or it was written by two processes. Both matter. Keep the file. |
| Events stop but the door still opens | The broker connection dropped. That is the intended behaviour — the unlock path in this preset does not go through the network — but the retained last-will should show the device as offline in the console. |

## Preset: Industrial Box — reComputer Industrial J20 {#p2_industrial_box}

**Choosing a preset.** There is no automatic matching in this release. The app's
network discovery cannot tell a reCamera Pro from a standard reCamera, and it
cannot see whether a gateway is present at all, so the preset is chosen by hand
from this table. Find the device you have, read across to how the lock is
switched, and that is the preset.

| Door device | How the lock is switched | Preset |
|---|---|---|
| reCamera Pro | The camera's own GPIO into a relay | On-Device — reCamera Pro |
| reComputer Industrial J20 + an existing RTSP camera | The J20's opto-isolated DO into a relay | Industrial Box |
| Standard reCamera (2002 / 2002w / 2002 HQ PoE) | Events over MQTT; relay at the gateway | Standard reCamera |
| reComputer J30 / J40 / R2000 + an existing RTSP camera | Events over MQTT; relay at the gateway | MQTT Relay |
| Grove Vision AI V2 + XIAO ESP32-S3 | The XIAO's GPIO into a Grove Relay | XIAO + Grove Vision AI V2 |

Two rows are easy to get wrong. A standard reCamera is not a cheaper reCamera
Pro: it recognises on the camera but drives no lock at all, so it takes the
gateway-relay path even when the gateway is standing next to it. And the Grove
Vision AI V2 preset has no liveness model — a printed photograph opens that door
— so it is not a substitute for the others on price alone.


For a door that already has a camera. The J20 pulls the existing RTSP stream,
runs recognition and liveness in containers, and drives the relay from an
opto-isolated digital output. The isolation is the point: the lock's supply and
the compute's supply never share a return path.

| Device | Purpose |
|---|---|
| Cloud / on-prem host | Face library server, management console, MQTT broker |
| reComputer Industrial J20 | Recognition, liveness, decision, opto-isolated DO |
| RTSP camera at the door | Video source |
| Relay module | Switches the lock |
| Lock + its own 12/24 V supply | Never powered from the box |

**Important.** This is not a certified security or life-safety system, and no
part of it has run on hardware. Six of the seven boundary metrics are empty. The
face embedding weights are non-commercial.

Known weaknesses, none of them measured:

- **No recognition or liveness figure exists** on this or any hardware.
- **The DO pin numbers are unconfirmed.** The design spec records DO1–DO4 as
  sysfs 463/464/465/462; whether the target image exposes them that way, or
  through Jetson.GPIO instead, is open.
- **Neither container image exists.** No published digest for the recognition
  service, and this project's device image has never been built.
- **Backlit doorways and glass reflections** have not been characterised.

## Step 1: Deploy the Face Library Server {#p2_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Same cloud host, same step as the other presets. Brings up the library server,
the broker and the console container, and writes the signing key.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from the door.
- **Its clock must be right** — door devices take their time correction from it.
- **The container image has not been pushed.** Build it on the host and retag it
  to the name in the compose file first.
- A signing key: `openssl rand -hex 32`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Image pull fails | Expected until the image is pushed. Build and retag on the host. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Library endpoint answers 404 | Correct before the first enrolment. |
| `NTP is not synchronised` warning | Fix it before deploying any door. |
| Port 8080 already in use | Change the library port; devices are given the same value. |

## Step 2: Deploy the Management Console {#p2_cloud_web type=docker_deploy required=true config=devices/cloud_web.yaml}

Configures the three role tokens and brings the console up alongside the server.

### Prerequisites

- Step 1 finished and the library endpoint answering.
- Tokens decided for admin, and optionally operator and viewer.
- A TLS-terminating reverse proxy before anyone outside the local network
  reaches it.

### Troubleshooting

| Issue | Solution |
|---|---|
| "The face library server is not answering" | Step 1 has not finished, or the port differs. |
| Anonymous `GET /api/events` returns 200 | The token gate is not in front of the data. Investigate. |
| Console starts, person library empty | Correct before the first enrolment. |
| Enrolled people are never recognised | The recognition service URL was left empty and a fake embedder was used. Set it and re-enrol. |

## Step 3: Enrol People {#p2_register type=web_dashboard required=true config=devices/register_person.yaml}

Opens the console's person library. 3 to 8 photographs per person; each
enrolment mints a new version.

### Prerequisites

- The admin token from Step 2.
- 3–8 photographs per person.
- The recognition service URL configured, so embeddings come from the real model.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused with "fewer than three images" | By design. Supply at least three. |
| New version published, door still refuses the person | Wait one poll period plus download. |
| Rollback refused naming a person | The deletion barrier. Mint a new version instead. |
| `model_tag` mismatch on the device | The library was built against a different embedding model. |

## Step 4: Deploy the Access Node on the J20 {#p2_deploy type=docker_deploy required=true config=devices/p2_j20.yaml}

Uploads the stack, checks whether the DO pin is already owned by something else,
writes the measured actuator settings and the library configuration, and starts
recognition and the access node.

### Prerequisites

- Docker and the compose plugin on the J20.
- The RTSP URL tested **from the J20**, not from your laptop.
- **Both image references.** A digest-pinned recognition image — a digest, not a
  tag, because two doors on the same tag with different digests hold embeddings
  that are not comparable and the symptom is people not being recognised. And
  this project's device image, which you must build yourself.
- The four actuator settings measured on the installed hardware: sysfs number,
  active level, pulse width, relay contact, and the fail mode that matches the
  lock you actually bought.
- At least 15 GB free.

### Wiring

Same order as every other preset: LED, then relay, then lock.

1. **LED with a series resistor on the DO.** Confirm polarity and pulse width.
2. **Relay module.** Confirm the contact clicks once per pulse. The DO switches
   the relay and nothing else.
3. **Lock, on a separate 12/24 V supply, through the relay contact.** COM and NC
   for a fail-safe magnetic lock, COM and NO for a fail-secure strike.

The deploy step prints whether the chosen sysfs pin is already exported and what
its direction and value are. If something else owns it, find out what before
continuing.

### Troubleshooting

| Issue | Solution |
|---|---|
| `set FACE_REC_API_IMAGE` / `set ACCESS_NODE_IMAGE` | Neither image exists yet. Supply what you built; there is deliberately no default. |
| "gpio N is ALREADY EXPORTED" | Something else is driving that output. Confirm it is the door DO before continuing. |
| "LIVENESS IS NOT LOADED" | The recognition service came up without its liveness model. The access node will refuse to start, correctly. Fix the image, do not bypass the check. |
| The step refuses a plaintext library URL | No signing key was given. On a plaintext URL the manifest signature is the whole integrity boundary. |
| RTSP stream opens on your laptop but not on the J20 | Routing or credentials. Test from the box itself. |
| The door pulses at boot | The active level is inverted. Fix it before reconnecting the lock. |

## Step 5: Check the Library Reached the Device {#p2_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Open the console's device page and confirm that the version you published is the
version the door device is actually matching against. Do this before putting a
face in front of the camera: a door that will not open because the library never
activated looks exactly like a door that will not open because recognition
failed, and only this page tells them apart.

### Prerequisites

- The door device from the previous step is powered, on the network and running.
- At least one person enrolled, so there is a version to activate.
- A viewer token, and — for devices with an MQTT command channel — that device
  listed in the console's `USA_DEVICE_ENDPOINTS`. An empty list makes this page
  read as "no devices" rather than "not configured".

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` is behind the server's `current` | The device has not polled yet. One poll period is 30 s by default; wait, then reload. |
| `desired_version` matches, `active_version` lags | The device saw the version and could not activate it. `last_error` says why — usually a signing key id or secret that differs from the console's, a `match_threshold` that differs from `USA_MATCH_THRESHOLD`, or a manifest with no `artifacts.gallery_v2`. |
| `signature.verified` is `null` | No version has been verified yet. That is not a failed verification. |
| `clock.valid` is `false` | Expected on a device with no NTP. The integrity boundary is the manifest signature, not the clock. |
| A person appears under `only_on_device` | Somebody enrolled locally, bypassing the cloud. The next activation overwrites it. Find out who did it and why. |
| The page is empty | `USA_DEVICE_ENDPOINTS` is `[]`, or no device has ever reported. Check the console's environment file first. |

## Step 6: Verify the Door End to End {#p2_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

An enrolled person opens the door once; a photograph does not; a remote unlock
produces a receipt; a delete cannot be rolled back.

### Prerequisites

- Steps 1–4 finished, the lock connected, someone enrolled in the current
  version.
- A printed photograph of that same person.
- An operator token and a viewer token.

### Deployment Complete

The door is installed and the four behaviours that matter have been observed
directly.

#### Quick verification

1. Reproduce the software half:
   `uv run python tools/verify_software_loop.py` from a clone of the upstream
   repository. The reference run reports 52 of 52 checks passing.
2. Stand in front of the camera as an enrolled person. Expect exactly one
   contact closure, one allowed event, the audit chain one record longer.
3. Step back and forward within the debounce window. Expect `debounced` and no
   second pulse.
4. Hold the printed photograph up. Expect `liveness_failed` and no pulse.
5. As an operator, issue a remote unlock. Expect one closure and an executed
   receipt. Repeat as a viewer: expect a refusal.
6. Delete an enrolled person, then try to roll back to a version that contained
   them. Expect a refusal naming that person.
7. Run the console's audit verification. Expect the chain to verify.

#### Next steps

- Calibrate the threshold on the installed camera.
- Replace the bundled broker configuration with TLS, per-device identities and
  topic ACLs.
- Put a TLS-terminating reverse proxy in front of the console.
- Record the DO number, level, pulse width, contact and lock type with the
  installation.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photograph opens the door | Liveness is not in the path. Take the door out of service until resolved. |
| Receipt says executed, contact never closes | The actuator did not act. Check the DO wiring and the actuator health output. |
| A replayed command opens the door twice | The replay table is not in the path. Stop and investigate. |
| Audit verification fails | The log was edited, or two processes wrote it. Keep the file. |
| Container restarts in a loop | `docker logs usa-access-node`. A refusal to start on a bad actuator or library configuration looks the same as a crash and is not one. |

## Preset: MQTT Relay — Compute Away From the Door {#p3_mqtt_relay}

**Choosing a preset.** There is no automatic matching in this release. The app's
network discovery cannot tell a reCamera Pro from a standard reCamera, and it
cannot see whether a gateway is present at all, so the preset is chosen by hand
from this table. Find the device you have, read across to how the lock is
switched, and that is the preset.

| Door device | How the lock is switched | Preset |
|---|---|---|
| reCamera Pro | The camera's own GPIO into a relay | On-Device — reCamera Pro |
| reComputer Industrial J20 + an existing RTSP camera | The J20's opto-isolated DO into a relay | Industrial Box |
| Standard reCamera (2002 / 2002w / 2002 HQ PoE) | Events over MQTT; relay at the gateway | Standard reCamera |
| reComputer J30 / J40 / R2000 + an existing RTSP camera | Events over MQTT; relay at the gateway | MQTT Relay |
| Grove Vision AI V2 + XIAO ESP32-S3 | The XIAO's GPIO into a Grove Relay | XIAO + Grove Vision AI V2 |

Two rows are easy to get wrong. A standard reCamera is not a cheaper reCamera
Pro: it recognises on the camera but drives no lock at all, so it takes the
gateway-relay path even when the gateway is standing next to it. And the Grove
Vision AI V2 preset has no liveness model — a printed photograph opens that door
— so it is not a substitute for the others on price alone.


For when the box that can run recognition is nowhere near the door, or when one
box serves several doors. Recognition runs on a J30/J40/R2000 or a standard
reCamera; the unlock travels over MQTT to a relay node — an R1000 writing a
Modbus point, or a XIAO ESP32 driving a Grove Relay.

The trade is explicit: the broker is on the unlock path, so its availability is
the door's availability. That is why this preset carries its own latency
boundary rather than sharing the direct one.

| Device | Purpose |
|---|---|
| Cloud / on-prem host | Face library server, management console, MQTT broker |
| reComputer J30 / J40 / R2000 or a standard reCamera | Recognition, liveness, decision |
| RTSP camera at the door | Video source |
| SenseCAP R1000 or XIAO ESP32-S3 | Closes the contact, at the door |
| Relay module | Switches the lock |
| Lock + its own 12/24 V supply | Never powered from the relay node |

**Important.** This is not a certified security or life-safety system, and no
part of it has run on hardware. Six of the seven boundary metrics are empty. The
face embedding weights are non-commercial.

Known weaknesses, none of them measured:

- **No recognition or liveness figure exists** on this or any hardware.
- **The broker is a single point of failure for the door**, unlike the other
  presets. Neither its latency contribution nor its failure behaviour has been
  measured.
- **Neither container image exists.**
- **The relay node's `set` topic must never be retained.** A retained unlock
  replays on every reconnect, and the door would open by itself after a power
  cut.

## Step 1: Deploy the Face Library Server {#p3_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Same cloud host, same step as the other presets.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from both the
  access host and the relay node.
- **Its clock must be right.**
- **The container image has not been pushed.** Build and retag on the host.
- A signing key: `openssl rand -hex 32`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Image pull fails | Expected until the image is pushed. Build and retag on the host. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Library endpoint answers 404 | Correct before the first enrolment. |
| `NTP is not synchronised` warning | Fix it before deploying any door. |
| Relay node cannot reach the broker | In this preset that means the door cannot open. Fix routing before going further. |

## Step 2: Deploy the Management Console {#p3_cloud_web type=docker_deploy required=true config=devices/cloud_web.yaml}

Configures the three role tokens and brings the console up alongside the server.

### Prerequisites

- Step 1 finished and the library endpoint answering.
- Tokens decided for admin, and optionally operator and viewer.
- A TLS-terminating reverse proxy before external exposure.

### Troubleshooting

| Issue | Solution |
|---|---|
| "The face library server is not answering" | Step 1 has not finished, or the port differs. |
| Anonymous `GET /api/events` returns 200 | The token gate is not in front of the data. |
| Console starts, person library empty | Correct before the first enrolment. |
| Enrolled people are never recognised | A fake embedder was used. Set the recognition service URL and re-enrol. |

## Step 3: Enrol People {#p3_register type=web_dashboard required=true config=devices/register_person.yaml}

Opens the console's person library. 3 to 8 photographs per person.

### Prerequisites

- The admin token from Step 2.
- 3–8 photographs per person.
- The recognition service URL configured.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused with "fewer than three images" | By design. |
| New version published, door still refuses the person | Wait one poll period plus download. |
| Rollback refused naming a person | The deletion barrier. Mint a new version. |
| `model_tag` mismatch on the device | Built against a different embedding model. |

## Step 4: Deploy the Access Host and Point It at a Relay {#p3_deploy type=docker_deploy required=true config=devices/p3_mqtt_relay.yaml}

Checks the broker is reachable, uploads the stack, writes the relay backend and
the library configuration, and confirms the relay node's retained state is on
the broker.

### Prerequisites

- Docker and the compose plugin on the access host.
- **The broker reachable from the access host.** The step fails here rather than
  at the door, because in this preset an unreachable broker means an
  unopenable door.
- The RTSP URL tested from the access host.
- **Both image references**, neither of which exists yet.
- The relay node already on the broker, with an id that is unique across the
  site.
- The relay contact and fail mode that match the lock — recorded here even
  though the contact is elsewhere, because the relay firmware does not know what
  kind of lock is on the other side of it and must not.

### Wiring

The wiring is at the relay node, not at the access host, which has no door
connections at all.

1. **LED with a series resistor on the relay node's output.** Confirm polarity
   and pulse width.
2. **Relay module.** Confirm the contact closes once per `set` message.
3. **Lock, on a separate 12/24 V supply, through the relay contact.** COM and NC
   for a fail-safe magnetic lock, COM and NO for a fail-secure strike.

The pulse is ended by the relay's own firmware timer, so a dropped packet cannot
leave the door standing open.

### Troubleshooting

| Issue | Solution |
|---|---|
| "Cannot reach the MQTT broker" | The step stops here on purpose. In this preset the broker is on the unlock path. |
| "No retained state from relay" | The relay node has never connected to this broker. Check its network and its id. |
| Unlock accepted, contact never closes | Subscribe to `access/v1/relay/<id>/state` and read `result`. `duplicate`, `expired` and `rejected` each mean something different. |
| The door opens by itself after a power cut | The `set` topic was published retained. It must never be. |
| Pulse width rejected | The command range is 500–5000 ms. The relay firmware's own wire format allows 100–10000 ms; they are different constraints and the narrower one governs. |
| "LIVENESS IS NOT LOADED" | The recognition service came up without its liveness model. Fix the image. |

## Step 5: Check the Library Reached the Device {#p3_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Open the console's device page and confirm that the version you published is the
version the door device is actually matching against. Do this before putting a
face in front of the camera: a door that will not open because the library never
activated looks exactly like a door that will not open because recognition
failed, and only this page tells them apart.

### Prerequisites

- The door device from the previous step is powered, on the network and running.
- At least one person enrolled, so there is a version to activate.
- A viewer token, and — for devices with an MQTT command channel — that device
  listed in the console's `USA_DEVICE_ENDPOINTS`. An empty list makes this page
  read as "no devices" rather than "not configured".

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` is behind the server's `current` | The device has not polled yet. One poll period is 30 s by default; wait, then reload. |
| `desired_version` matches, `active_version` lags | The device saw the version and could not activate it. `last_error` says why — usually a signing key id or secret that differs from the console's, a `match_threshold` that differs from `USA_MATCH_THRESHOLD`, or a manifest with no `artifacts.gallery_v2`. |
| `signature.verified` is `null` | No version has been verified yet. That is not a failed verification. |
| `clock.valid` is `false` | Expected on a device with no NTP. The integrity boundary is the manifest signature, not the clock. |
| A person appears under `only_on_device` | Somebody enrolled locally, bypassing the cloud. The next activation overwrites it. Find out who did it and why. |
| The page is empty | `USA_DEVICE_ENDPOINTS` is `[]`, or no device has ever reported. Check the console's environment file first. |

## Step 6: Verify the Door End to End {#p3_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

An enrolled person opens the door once; a photograph does not; a remote unlock
produces a receipt; a delete cannot be rolled back.

### Prerequisites

- Steps 1–4 finished, the lock connected at the relay node, someone enrolled.
- A printed photograph of that same person.
- An operator token and a viewer token.

### Deployment Complete

The door is installed and the four behaviours that matter have been observed
directly.

#### Quick verification

1. Reproduce the software half:
   `uv run python tools/verify_software_loop.py` from a clone of the upstream
   repository. The reference run reports 52 of 52 checks passing.
2. Stand in front of the camera as an enrolled person. Expect one contact
   closure, one allowed event, the audit chain one record longer.
3. Step back and forward within the debounce window. Expect `debounced` and no
   second pulse.
4. Hold the printed photograph up. Expect `liveness_failed` and no pulse.
5. As an operator, issue a remote unlock. Expect one closure and an executed
   receipt. Repeat as a viewer: expect a refusal.
6. Delete an enrolled person, then try to roll back to a version that contained
   them. Expect a refusal naming that person.
7. Disconnect the broker briefly and confirm the door **stops opening** — in
   this preset that is the expected behaviour, and knowing it is what tells you
   whether you chose the right preset for this door.

#### Next steps

- Calibrate the threshold on the installed camera.
- Replace the bundled broker configuration with TLS, per-device identities and
  topic ACLs. In this preset that broker is on the unlock path, so it deserves
  the same care as the door itself.
- Consider a second broker or a local fallback if the door cannot tolerate
  broker downtime. If it cannot, P1 or P2 is the better preset.
- Record the relay id, contact, pulse width and lock type with the installation.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photograph opens the door | Liveness is not in the path. Take the door out of service. |
| Receipt executed, contact never closes | Read `access/v1/relay/<id>/state`. The relay reports why. |
| The door opens twice for one approach | Either the debounce or the relay's duplicate-id table is not in the path. |
| Audit verification fails | The log was edited, or two processes wrote it. Keep the file. |
| Latency feels high | There is no measured figure for this path. Do not compare it against the direct-path expectation; the extra hop is the whole point of this preset. |

## Preset: Standard reCamera — On-Camera Loop, Gateway Relay {#p5_recamera_std}

**Choosing a preset.** There is no automatic matching in this release. The app's
network discovery cannot tell a reCamera Pro from a standard reCamera, and it
cannot see whether a gateway is present at all, so the preset is chosen by hand
from this table. Find the device you have, read across to how the lock is
switched, and that is the preset.

| Door device | How the lock is switched | Preset |
|---|---|---|
| reCamera Pro | The camera's own GPIO into a relay | On-Device — reCamera Pro |
| reComputer Industrial J20 + an existing RTSP camera | The J20's opto-isolated DO into a relay | Industrial Box |
| Standard reCamera (2002 / 2002w / 2002 HQ PoE) | Events over MQTT; relay at the gateway | Standard reCamera |
| reComputer J30 / J40 / R2000 + an existing RTSP camera | Events over MQTT; relay at the gateway | MQTT Relay |
| Grove Vision AI V2 + XIAO ESP32-S3 | The XIAO's GPIO into a Grove Relay | XIAO + Grove Vision AI V2 |

Two rows are easy to get wrong. A standard reCamera is not a cheaper reCamera
Pro: it recognises on the camera but drives no lock at all, so it takes the
gateway-relay path even when the gateway is standing next to it. And the Grove
Vision AI V2 preset has no liveness model — a printed photograph opens that door
— so it is not a substitute for the others on price alone.

The camera already does the recognition. An App Center application on the
standard reCamera runs detection, embedding, a two-head texture liveness with
blink fusion and cosine matching in one native process on the device, so this
preset installs no recognition container and pulls no video off the camera. It
adds a small standard-library daemon for the three things the camera does not do
by itself: pull the versioned face library, map the camera's native result
stream onto the event contract, and hold every threshold in one file.

The camera drives no lock. Events leave over MQTT and the relay is at the
gateway — an R1000 writing a Modbus point, or a XIAO ESP32 driving a Grove
Relay.

| Device | Purpose |
|---|---|
| Cloud / on-prem host | Face library server, management console, MQTT broker |
| Standard reCamera (2002 / 2002w / 2002 HQ PoE) | Recognition, liveness, decision — all on the camera |
| SenseCAP R1000 or XIAO ESP32-S3 | Closes the contact, at the door |
| Relay module | Switches the lock |
| Lock + its own 12/24 V supply | Never powered from the relay node |

**Important.** This is not a certified security or life-safety system. The
library path has been exercised on a real unit; the door path has not. The face
embedding weights are non-commercial.

What is verified and what is not, stated separately because they are usually
conflated:

- **Verified on hardware** (second probe run, standard reCamera at
  192.168.42.1): library pull, per-file SHA, manifest signature, atomic switch,
  gallery write and `op:reload` ack; resume after an interrupted download;
  rejection of a version whose manifest does not verify; the threshold
  consistency gate refusing to start when the config and the running recognition
  process disagree. Full activation measured p50 491.6 ms and p95 507.8 ms over
  20 runs on a 2-person, 16.5 KB library; the `op:reload` round trip measured
  p50 100.0 ms over 25 runs.
- **Not verified, and not to be presented as if it were**: any recognition or
  liveness figure — nobody stood in front of the lens during either probe run
  and all 220 sampled frames read `face_count: 0`; the recognition-to-relay
  latency, because no relay has been wired; and the thresholds, which are the
  device's shipped values carrying `calibration = pending`.
- **The relay node's `set` topic must never be retained.** A retained unlock
  replays on every reconnect, and the door would open by itself after a power
  cut.

## Step 1: Deploy the Face Library Server {#p5_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Same cloud host, same step as the other presets.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from both the
  access host and the relay node.
- **Its clock must be right.**
- **The container image has not been pushed.** Build and retag on the host.
- A signing key: `openssl rand -hex 32`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Image pull fails | Expected until the image is pushed. Build and retag on the host. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Library endpoint answers 404 | Correct before the first enrolment. |
| `NTP is not synchronised` warning | Fix it before deploying any door. |
| Relay node cannot reach the broker | In this preset that means the door cannot open. Fix routing before going further. |

## Step 2: Deploy the Management Console {#p5_cloud_web type=docker_deploy required=true config=devices/cloud_web.yaml}

Configures the three role tokens and brings the console up alongside the server.

### Prerequisites

- Step 1 finished and the library endpoint answering.
- Tokens decided for admin, and optionally operator and viewer.
- A TLS-terminating reverse proxy before external exposure.

### Troubleshooting

| Issue | Solution |
|---|---|
| "The face library server is not answering" | Step 1 has not finished, or the port differs. |
| Anonymous `GET /api/events` returns 200 | The token gate is not in front of the data. |
| Console starts, person library empty | Correct before the first enrolment. |
| Enrolled people are never recognised | A fake embedder was used. Set the recognition service URL and re-enrol. |

## Step 3: Enrol People {#p5_register type=web_dashboard required=true config=devices/register_person.yaml}

Opens the console's person library. 3 to 8 photographs per person.

### Prerequisites

- The admin token from Step 2.
- 3–8 photographs per person.
- The recognition service URL configured.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused with "fewer than three images" | By design. |
| New version published, door still refuses the person | Wait one poll period plus download. |
| Rollback refused naming a person | The deletion barrier. Mint a new version. |
| `model_tag` mismatch on the device | Built against a different embedding model. |

## Step 4: Install the Access Agent on the Camera {#p5_install type=manual required=true config=devices/p5_recamera_std.yaml}

Copy six files onto the camera as root, fill in one config file, run one
synchronisation in the foreground, then leave it resident.

### Prerequisites

- Root SSH access to the camera. Root is required, not preferred:
  `/userdata/local/face-gallery/` is `root:root 0700` and the daemon writes
  there.
- The App Center `face-recognition` application present and startable.
- The face library server reachable from the camera over plain HTTP, and the
  signing key from the cloud step.
- A clone of the upstream repository, for `platforms/recamera-std/` and
  `contracts/validate_payload.py`.

### Wiring

- The camera is not wired to the lock. Nothing on it carries lock current.
- The relay lives at the gateway node, on the lock's own 12/24 V supply.
- Fail-safe magnetic lock: COM and NC. Fail-secure strike: COM and NO. Confirm
  with an LED before the lock goes on.
- Getting events off the camera needs an MQTT listener beyond the default
  loopback-only one. That is a site networking decision, and the daemon does not
  make it for you — it does not edit `/etc/mosquitto/mosquitto.conf`.

### Troubleshooting

| Issue | Solution |
|---|---|
| `RuntimeArgsMismatch: face-recognition is not running` | Start the recognition application first. An access daemon with no recogniser cannot make decisions, so it stops rather than guessing. |
| `mqtt.mqtt_host='127.0.0.1' but face-recognition runs -m 'localhost'` | The gate compares command-line strings literally. Write `localhost`. This is the one that catches people on a factory device. |
| `PermissionError` writing the gallery | The daemon is not running as root. |
| The daemon starts but no version ever activates | Check `key_id` and the secret against the console, and `match_threshold` against `USA_MATCH_THRESHOLD`. |
| Version directories accumulate on the device | `[facedb] keep_versions` (default 3) bounds them after a successful activation. Rollback does not depend on them — the server republishes old content under a new version number. |
| You want to change a threshold | Change it in the config file **and** in the recognition process's start arguments. Changing one alone makes the daemon refuse to start, which is the point. |

## Step 5: Check the Library Reached the Device {#p5_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Open the console's device page and confirm that the version you published is the
version the door device is actually matching against. Do this before putting a
face in front of the camera: a door that will not open because the library never
activated looks exactly like a door that will not open because recognition
failed, and only this page tells them apart.

### Prerequisites

- The door device from the previous step is powered, on the network and running.
- At least one person enrolled, so there is a version to activate.
- A viewer token, and — for devices with an MQTT command channel — that device
  listed in the console's `USA_DEVICE_ENDPOINTS`. An empty list makes this page
  read as "no devices" rather than "not configured".

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` is behind the server's `current` | The device has not polled yet. One poll period is 30 s by default; wait, then reload. |
| `desired_version` matches, `active_version` lags | The device saw the version and could not activate it. `last_error` says why — usually a signing key id or secret that differs from the console's, a `match_threshold` that differs from `USA_MATCH_THRESHOLD`, or a manifest with no `artifacts.gallery_v2`. |
| `signature.verified` is `null` | No version has been verified yet. That is not a failed verification. |
| `clock.valid` is `false` | Expected on a device with no NTP. The integrity boundary is the manifest signature, not the clock. |
| A person appears under `only_on_device` | Somebody enrolled locally, bypassing the cloud. The next activation overwrites it. Find out who did it and why. |
| The page is empty | `USA_DEVICE_ENDPOINTS` is `[]`, or no device has ever reported. Check the console's environment file first. |

## Step 6: Verify the Door End to End {#p5_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

An enrolled person opens the door once; a photograph does not; a remote unlock
produces a receipt; a delete cannot be rolled back.

### Prerequisites

- Steps 1–4 finished, the lock connected at the relay node, someone enrolled.
- A printed photograph of that same person.
- An operator token and a viewer token.

### Deployment Complete

The door is installed and the four behaviours that matter have been observed
directly.

#### Quick verification

1. Reproduce the software half:
   `uv run python tools/verify_software_loop.py` from a clone of the upstream
   repository. The reference run reports 52 of 52 checks passing.
2. Stand in front of the camera as an enrolled person. Expect one contact
   closure, one allowed event, the audit chain one record longer.
3. Step back and forward within the debounce window. Expect `debounced` and no
   second pulse.
4. Hold the printed photograph up. Expect `liveness_failed` and no pulse.
5. As an operator, issue a remote unlock. Expect one closure and an executed
   receipt. Repeat as a viewer: expect a refusal.
6. Delete an enrolled person, then try to roll back to a version that contained
   them. Expect a refusal naming that person.
7. Disconnect the broker briefly and confirm the door **stops opening** — in
   this preset that is the expected behaviour, and knowing it is what tells you
   whether you chose the right preset for this door.

#### Next steps

- Calibrate the threshold on the installed camera.
- Replace the bundled broker configuration with TLS, per-device identities and
  topic ACLs. In this preset that broker is on the unlock path, so it deserves
  the same care as the door itself.
- Consider a second broker or a local fallback if the door cannot tolerate
  broker downtime. If it cannot, P1 or P2 is the better preset.
- Record the relay id, contact, pulse width and lock type with the installation.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photograph opens the door | Liveness is not in the path. Take the door out of service. |
| Receipt executed, contact never closes | Read `access/v1/relay/<id>/state`. The relay reports why. |
| The door opens twice for one approach | Either the debounce or the relay's duplicate-id table is not in the path. |
| Audit verification fails | The log was edited, or two processes wrote it. Keep the file. |
| Latency feels high | There is no measured figure for this path. Do not compare it against the direct-path expectation; the extra hop is the whole point of this preset. |

## Preset: XIAO + Grove Vision AI V2 — No Liveness {#p4_xiao_grove}

**Choosing a preset.** There is no automatic matching in this release. The app's
network discovery cannot tell a reCamera Pro from a standard reCamera, and it
cannot see whether a gateway is present at all, so the preset is chosen by hand
from this table. Find the device you have, read across to how the lock is
switched, and that is the preset.

| Door device | How the lock is switched | Preset |
|---|---|---|
| reCamera Pro | The camera's own GPIO into a relay | On-Device — reCamera Pro |
| reComputer Industrial J20 + an existing RTSP camera | The J20's opto-isolated DO into a relay | Industrial Box |
| Standard reCamera (2002 / 2002w / 2002 HQ PoE) | Events over MQTT; relay at the gateway | Standard reCamera |
| reComputer J30 / J40 / R2000 + an existing RTSP camera | Events over MQTT; relay at the gateway | MQTT Relay |
| Grove Vision AI V2 + XIAO ESP32-S3 | The XIAO's GPIO into a Grove Relay | XIAO + Grove Vision AI V2 |

Two rows are easy to get wrong. A standard reCamera is not a cheaper reCamera
Pro: it recognises on the camera but drives no lock at all, so it takes the
gateway-relay path even when the gateway is standing next to it. And the Grove
Vision AI V2 preset has no liveness model — a printed photograph opens that door
— so it is not a substitute for the others on price alone.


The cheapest door. A Grove Vision AI V2 detects and embeds; a XIAO ESP32-S3
matches against a library held in its own flash and drives a Grove Relay. It
pulls the same versioned library over the same two HTTP endpoints as every other
preset.

It has **no liveness model**, and none exists for this chip in any of the source
repositories. The policy is deliberately weakened in exchange: an allowlisted
person, inside a schedule, single-shot. Do not put this on a door where somebody
holding up a printed photograph would matter.

| Device | Purpose |
|---|---|
| Cloud / on-prem host | Face library server, management console, MQTT broker |
| Grove Vision AI V2 (Himax WE2) | Detection and 128-d embedding |
| XIAO ESP32-S3 (PSRAM variant) | Matching, policy, library sync, relay output |
| Grove Relay | Switches the lock |
| Lock + its own 12/24 V supply | Never powered from the XIAO |

**Important.** This is not a certified security or life-safety system. **The
firmware has not been built** — it exists as source on a branch, and the flash
steps point at labelled stubs rather than at binaries. Six of the seven boundary
metrics are empty. The WE2 model weights are non-commercial.

Known weaknesses, all of them structural rather than measured:

- **No liveness at all.** A printed photograph is not distinguishable from a
  person on this hardware. This is the defining limitation of the preset.
- **The matching threshold is unresolved.** Three different values appear across
  the source repositories and they cannot all be right. It must be swept on the
  assembled hardware.
- **The model flash address is unresolved** — two different addresses appear in
  the sources.
- **Match latency grows with library size** and has never been measured. The
  ~880-person slot capacity is arithmetic from the record layout, not a limit
  anybody has reached.
- **The WE2 reset line is hand-wired** on a discrete build; nobody has flashed a
  WE2 through this path yet.

## Step 1: Deploy the Face Library Server {#p4_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Same cloud host, same step as the other presets. The XIAO polls the same two
endpoints as everything else.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from the XIAO's
  Wi-Fi network.
- **Its clock must be right.** The XIAO has no RTC at all.
- **The container image has not been pushed.** Build and retag on the host.
- A signing key: `openssl rand -hex 32`. On this preset it is not a hardening
  option — with no RTC the XIAO cannot validate a TLS certificate, so the
  manifest signature is the entire integrity boundary.

### Troubleshooting

| Issue | Solution |
|---|---|
| Image pull fails | Expected until the image is pushed. Build and retag on the host. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Library endpoint answers 404 | Correct before the first enrolment. |
| The XIAO cannot reach the host | It is a 2.4 GHz-only radio. Check the SSID band before checking anything else. |
| `NTP is not synchronised` warning | Fix it. The XIAO takes its time entirely from this host. |

## Step 2: Deploy the Management Console {#p4_cloud_web type=docker_deploy required=true config=devices/cloud_web.yaml}

Configures the three role tokens and brings the console up alongside the server.

### Prerequisites

- Step 1 finished and the library endpoint answering.
- Tokens decided for admin, and optionally operator and viewer.
- A TLS-terminating reverse proxy before external exposure.

### Troubleshooting

| Issue | Solution |
|---|---|
| "The face library server is not answering" | Step 1 has not finished, or the port differs. |
| Anonymous `GET /api/events` returns 200 | The token gate is not in front of the data. |
| Console starts, person library empty | Correct before the first enrolment. |
| Enrolled people are never recognised | The library was built for a different model tag than the WE2 reports. |

## Step 3: Enrol People {#p4_register type=web_dashboard required=true config=devices/register_person.yaml}

Opens the console's person library. On this preset the allowlist is the entire
policy, so who is in it carries more weight than on the others.

### Prerequisites

- The admin token from Step 2.
- 3–8 photographs per person.
- **A library built for the WE2's model tag.** Embeddings from the server-side
  backbone are not comparable with the WE2's; the `model_tag` guard rejects a
  mismatch at load rather than letting it show up as "nobody is recognised".

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused with "fewer than three images" | By design. |
| The XIAO rejects the new version at load | `model_tag` mismatch. The library must be built for the WE2 backbone. |
| A version downloads but never activates | The sha256 did not verify. The controller keeps the previous slot, which is the intended behaviour. |
| Rollback refused naming a person | The deletion barrier. Mint a new version. |

## Step 4: Flash the Grove Vision AI V2 {#p4_flash_we2 type=himax_usb required=true config=devices/p4_grove_we2.yaml}

Flashes the WE2 firmware and the detection plus embedding model over xmodem.
Flash this module before the XIAO — the XIAO's application probes the vision
link at startup.

### Prerequisites

- **The firmware does not exist.** This step points at labelled stub files, so
  it fails immediately and visibly rather than flashing something
  plausible-looking. `assets/firmware/MANIFEST.md` records the source, the flash
  layout and the four blockers.
- The Grove Vision AI V2 on USB. It uses a WCH CH343 bridge; the product id is
  `0x55d3`, not the Watcher's `0x55d2`.
- **The WE2 reset line wired.** On a discrete build it is a hand-wired
  connection to the XIAO's D2 (GPIO3); the Watcher board drives it from an IO
  expander that this build does not have, and the flasher needs the ESP32 to
  hold it asserted.

### Wiring

Between the two modules, before either is flashed:

| XIAO pin | Signal | To |
|---|---|---|
| D6 / GPIO43 | UART TX at 921600 | WE2 RX |
| D7 / GPIO44 | UART RX at 921600 | WE2 TX |
| D2 / GPIO3 | WE2 reset, active low | WE2 reset |

D6 and D7 are the ESP32-S3's default UART0 pins. They are free only because the
XIAO console runs over native USB; switching the console back to UART0 collides
with them and the vision link stops answering.

### Troubleshooting

| Issue | Solution |
|---|---|
| The step fails on a missing or invalid firmware file | Expected. Nothing has been built. Build it, upload it, and replace the stub reference and its sha256 in one change. |
| Serial port not found | Check the product id — `0x55d3` for Grove Vision AI V2, `0x55d2` for the Watcher. |
| xmodem transfer stalls near the end | A known truncation pattern on this transport; upstream packages pad the model file to work around it. |
| The model address in the sources disagrees with the partition table | Two addresses appear in the sources. Trust the built partition table, not either document. |

## Step 5: Flash the XIAO ESP32-S3 {#p4_flash_xiao type=esp32_usb required=true config=devices/p4_xiao_door.yaml}

Flashes the bootloader, the partition table and the application in separate
segments, and configures Wi-Fi, the library URL, the signing key, the model tag
and the relay settings.

### Prerequisites

- **The firmware does not exist.** Same as the previous step: labelled stubs, an
  immediate failure, and the manifest recording what has to be built.
- Step 4 finished, so the vision link answers.
- The Wi-Fi credentials, on 2.4 GHz.
- The library URL, the signing key and the model tag from the cloud steps.

### Wiring

| XIAO pin | Signal |
|---|---|
| D0 / GPIO1 | Relay output. The board's default is active high, fail-secure — normally-open wiring, so losing power leaves the lock engaged |
| D1 / GPIO2 | Optional request-to-exit button, to ground, internal pull-up |
| GPIO21 | On-board status LED, active low |

The two library slots at `0x680000` and `0x6c0000` are **not** flashed. They are
filled at runtime by the HTTP sync: a download always targets the inactive slot
and the active pointer flips only after the sha256 verifies, so a power cut
mid-download cannot damage the library that is currently opening the door.
Flashing a library image would defeat that and would bake a face library into a
distributable artefact.

Change the wiring and the `relay_contact` setting together, never one alone.

### Troubleshooting

| Issue | Solution |
|---|---|
| The step fails on a missing or invalid firmware file | Expected. Nothing has been built. |
| Serial port not found | The XIAO uses native USB-Serial-JTAG, vendor `0x303a`. |
| The vision link reports unavailable at startup | Flash the Grove Vision AI V2 first, and check the three UART and reset connections. |
| The library never activates | Check the model tag and the signing key. A mismatch on either is rejected at load, deliberately. |
| The relay pulses at boot | The active level is inverted for the module you fitted. Fix it before connecting the lock. |

## Step 6: Check the Library Reached the Device {#p4_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

Open the console's device page and confirm that the version you published is the
version the door device is actually matching against. Do this before putting a
face in front of the camera: a door that will not open because the library never
activated looks exactly like a door that will not open because recognition
failed, and only this page tells them apart.

### Prerequisites

- The door device from the previous step is powered, on the network and running.
- At least one person enrolled, so there is a version to activate.
- A viewer token, and — for devices with an MQTT command channel — that device
  listed in the console's `USA_DEVICE_ENDPOINTS`. An empty list makes this page
  read as "no devices" rather than "not configured".

### Troubleshooting

| Issue | Solution |
|---|---|
| `desired_version` is behind the server's `current` | The device has not polled yet. One poll period is 30 s by default; wait, then reload. |
| `desired_version` matches, `active_version` lags | The device saw the version and could not activate it. `last_error` says why — usually a signing key id or secret that differs from the console's, a `match_threshold` that differs from `USA_MATCH_THRESHOLD`, or a manifest with no `artifacts.gallery_v2`. |
| `signature.verified` is `null` | No version has been verified yet. That is not a failed verification. |
| `clock.valid` is `false` | Expected on a device with no NTP. The integrity boundary is the manifest signature, not the clock. |
| A person appears under `only_on_device` | Somebody enrolled locally, bypassing the cloud. The next activation overwrites it. Find out who did it and why. |
| The page is empty | `USA_DEVICE_ENDPOINTS` is `[]`, or no device has ever reported. Check the console's environment file first. |

## Step 7: Verify the Door End to End {#p4_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

An allowlisted person opens the door once, a delete cannot be rolled back, and —
on this preset specifically — you confirm for yourself that a photograph *does*
open it, so that nobody discovers that later.

### Prerequisites

- Steps 1–5 finished, the lock connected, someone allowlisted in the current
  version.
- A printed photograph of that same person, to demonstrate the known limitation
  rather than to test a defence that does not exist.
- Somewhere to record that this door has no liveness, so the next person to
  audit the site does not have to rediscover it.

### Deployment Complete

The door is installed and its behaviour, including what it cannot do, has been
observed directly.

#### Quick verification

1. Reproduce the software half:
   `uv run python tools/verify_software_loop.py` from a clone of the upstream
   repository. The reference run reports 52 of 52 checks passing. It covers the
   library, policy and audit behaviour this preset shares with the others; it
   does not cover this firmware, which does not exist.
2. Stand in front of the camera as an allowlisted person. Expect one contact
   closure of the configured width.
3. Present someone who is not allowlisted. Expect no closure.
4. Present an allowlisted person outside the schedule. Expect no closure — on
   this preset the schedule is doing work the liveness check does elsewhere.
5. **Hold the printed photograph up. Expect the door to open.** That is the
   known limitation, not a fault to be filed. If this outcome is unacceptable
   for this door, this is the wrong preset.
6. Delete an allowlisted person, then confirm the XIAO stops admitting them
   within one poll period, and that rolling back to a version containing them is
   refused.
7. Power-cycle the controller mid-download if you can arrange it, and confirm the
   previously active library still opens the door.

#### Next steps

- Sweep positive and negative pairs on the assembled hardware and set the
  threshold from that. Do not copy any of the three values in the source
  repositories.
- Measure match latency against a library the size you actually intend to run.
  The ~880-person figure is arithmetic, not a tested limit.
- Record, with the installation and wherever the site's access controls are
  documented, that this door has no liveness check.
- Record the relay pin, contact, pulse width and lock type.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photograph opens the door | Expected on this preset. There is no liveness model for this chip. If it matters, move the door to P1, P2 or P3. |
| Nobody is recognised after a library update | `model_tag` mismatch, or the library was built with the server-side backbone. Embeddings do not cross models. |
| The door stops responding after a library download | The download targets the inactive slot and the pointer only flips on a verified sha256. If it stopped, look at the sync log, not at the slot. |
| Matching gets slower as the library grows | Expected and unmeasured. Match time scales with the number of records. |
| The controller reconnects but the door opened by itself | Something published the relay `set` topic retained. It must never be. |
