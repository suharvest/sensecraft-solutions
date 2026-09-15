## Preset: A. reCamera Pro at the Door {#a_ai_camera}

**What you need**

| Device | Purpose |
|---|---|
| Linux server (Docker, no GPU needed) | Face library, management console, MQTT broker |
| reCamera Pro | Recognises faces, decides whether to unlock, drives the relay from its GPIO |
| Relay module | Dry contact into the door controller's unlock input |

## Step 1: Deploy the Face Library Server {#p1_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Brings up the library server, the broker and the console container on the cloud
or on-prem host, and writes the signing key and the first console token.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from the door. No
  GPU needed.
- **Its clock must be right.** Door devices with no working RTC take their time
  correction from this server's HTTP `Date` header, so a wrong clock here
  misdates every audit record in the installation.
- **The container image is published** (`unmanned-store-access-cloud:0.1.0-c1`,
  two-arch manifest); the compose file's default already points at it. Override
  it only if you rebuilt from source.
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

### Target {#p1_facedb_remote type=remote config=devices/cloud_facedb.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p1_facedb_local type=local config=devices/cloud_facedb.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 2: Deploy the Management Console {#p1_cloud_web type=docker_deploy required=true config=devices/cloud_web.yaml target_inherit_from=p1_cloud_facedb}

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
| Enrolled people are never recognised | The console fell back to a fake embedder because the recognition service URL was left empty. Set it and re-enrol — but see the P1 known limitation below before assuming that fixes it. |

### Target {#p1_web_remote type=remote config=devices/cloud_web.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p1_web_local type=local config=devices/cloud_web.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 3: Enrol People {#p1_register type=web_dashboard required=true config=devices/register_person.yaml}

Opens the console's person library. Enrol each person from 3 to 8 photographs;
each enrolment mints a new library version.

### Prerequisites

**Known limitation — this does not yet produce a library the door can use in
production.** The Pro camera's on-device recognizer runs
`rv1126b:scrfd500m+mbf512@fp16`. No cloud embedding service today produces
vectors in that model's space — the only embedder this console can call is the
generic `face_rec_api` (`buffalo_l`), or, if that URL is left empty,
`FakeEmbedder`. Cosine similarity between `buffalo_l` and the device's model is
approximately zero, and the device only compares the `model_tag` string, so
misconfiguring this raises no error at enrolment time — it just recognises
nobody, in the field. Enrolling through this console today verifies the
register → publish → distribute plumbing, not a face library the Pro can
actually recognise against. Fixing this needs either a cloud embedder that
reconciles to the device's model space or a device-assisted enrolment path;
neither exists yet (upstream `docs/user-guide.md` §5.1;
`evaluation/runs/2026-09-07-recamera-pro-p1/results.md` §5.1, §9.2). **This does
not affect the standard reCamera path (P5)**, which embeds on-device and does
not enrol through this cloud console.

- The admin token from Step 2.
- 3–8 photographs per person. Fewer than three is rejected: one photograph tells
  the matcher nothing about how much this face varies, and a library built that
  way fails in the field rather than at enrolment.
- The recognition service URL configured in Step 2 — this makes embeddings come
  from `face_rec_api` instead of the always-wrong `FakeEmbedder`, but does not
  by itself make the library usable in production on P1; see the known
  limitation above.

### Troubleshooting

| Issue | Solution |
|---|---|
| Enrolment refused with "fewer than three images" | By design. Supply at least three. |
| A new version appears but the door still refuses the person | Wait one poll period plus the download — 30 s by default. The device switches only after SHA and signature verify. |
| Rollback refused naming a person | The deletion barrier. Mint a new version instead; that refusal is the mechanism working. |
| `model_tag` mismatch on the device | The library was built against a different embedding model. Rebuild it against the one the door actually runs. |

## Step 4: Activate F1 Door Access from the App Center {#p1_install type=recamera_pro_app required=true config=devices/p1_recamera_pro.yaml}

f1-access is a published reCamera Pro App Center package (catalog id
`f1-access`) that combines the face-recognition app's recognition cascade with
the door logic: it drives one sysfs GPIO dry contact and publishes
`access/v1/events`. This step configures it and makes it the active appmgr
app — appmgr is single-active, so activating f1-access stops whatever app was
running before.

### Prerequisites

- f1-access installed from the device's App Center. This step activates an
  already-installed app; it does not upload or install packages.
- Nothing else is required yet — the app comes up recognising and running
  liveness. It stays **disarmed** (no pin exported, no access event published)
  until the next step gives it an access config file.

### Install f1-access from the App Center

If f1-access is not installed yet, do this on the camera's own web console
first — this deployment step cannot install it for you.

1. Log in to the camera's web console.
2. Open the **App Center**.
3. Find **F1 Door Access** and choose **Install**. Wait for it to finish; it
   is a full recognition app plus six on-device models, so first install
   takes longer than a config change.
4. Once installed, run this step to **activate** it — the App Center install
   only places the app; the camera does not switch to it on its own.

### Troubleshooting

| Issue | Solution |
|---|---|
| Activation times out before 180 s | The manifest loads six `.rknn` models; a first activation right after install can be slow while the filesystem cache is cold. Retry once before treating it as a fault. |
| `require_installed` fails | f1-access is not on this device's App Center yet. Install it there first — this step cannot install packages. |
| Another app stays active after this step | Check `GET /api/appMgr/list` for `last_exit`; `entry.cgi`'s `/model/inference` endpoint can wedge after long high load and make `activate` report a timeout. A reboot clears it. |

## Step 5: Wire the Relay and Arm the Gate {#p1_wire type=manual required=true config=devices/p1_recamera_pro_wiring.yaml}

Reach the camera as root, find and measure a free pin, wire LED then relay then
the door controller and declare the contact, write the access config and the
facedb key, and confirm the gate came up armed — not just the app active.

### Prerequisites

- The app active from the previous step, confirmed with
  `curl -s http://127.0.0.1:8130/api/appMgr/list`.
- Root SSH access to the camera. The `admin` account has no sudo, `su` is not
  setuid, and `/sys/class/gpio` is root-only.
- A meter. Measure the pin number, polarity and available drive current on your
  own unit before connecting anything to it.
- A facedb key id and secret matching the console's, from Step 2.
- The device has no NTP client. The surveyed unit's clock was about seven months
  out, and HTTPS fails on it for that reason.

### Wiring

In this order, and do not skip ahead.

1. **LED with a series resistor on the pin.** Confirm the polarity and the pulse
   width are what you configured. Nothing else is connected yet.
2. **Relay module on its own supply.** Confirm the contact clicks once per
   pulse. Match the module to the pin: two of the board's exposed lines are
   native GPIO outputs that swing 12–21 V depending on DC-IN, while a UART or
   CAN pin reconfigured as GPIO gives 3.3 V. This solution's default,
   `gpio130` (GPIO4_A2), is identified by device tree pinctrl evidence as
   one of the expansion port's UART4 M0 pins (paired with `gpio131`)
   reconfigured as GPIO — it is in the 3.3 V family, not one of the two
   native 12–21 V outputs. Confirm its exact TX/RX role, actual voltage and
   available drive current with a meter or schematic on your own unit before
   wiring. Default relay: Grove - Relay (SKU 103020005),
   SPST-NO, mechanical (non-solid-state) contact, documented for 3.3–5 V
   trigger. If the door controller's input is normally-closed and needs an
   `NC` terminal, use Grove - SPDT Relay(30A) (SKU 103020012) instead — its
   3.3 V trigger reliability is not documented by the vendor, so give its
   coil its own 5 V supply from a separate source, and still confirm on
   hardware that it pulls in reliably before relying on it (a documented
   supply voltage is not the same as a documented 3.3 V trigger level). A
   solid-state relay is not an option here: the mechanical-contact
   requirement excludes it outright, and the SSR Seeed carries is documented
   for AC loads only, with a DC load left switched on once triggered.
3. **The relay's COM/NO dry contact (COM/NC if you wired the SPDT
   alternative) into the door controller's input.** The
   lock, its power supply, and the door controller itself are supplied and
   wired by the door-control party — outside this solution's BOM. The relay
   presents only a floating, unpowered contact pair; the pin must never see
   the controller's own current.

Getting the contact backwards leaves the door controller in the wrong idle
state and looks like a working installation until somebody tests it. This
is why `relay_contact` and `fail_mode` have no default values: they record
which contact pair (`NC` or `NO`) you wired and which state (`fail_safe` or
`fail_secure`) the door controller should end up in on a power cut — set
both from what you measured on the controller, not from an assumption. Until
you have measured, both read `unverified` — legal, named in a warning on every
start, and meaning no door controller may be connected yet. This solution's
default posture is fail-safe, because trapping people inside is worse than
letting them out.

### Troubleshooting

| Issue | Solution |
|---|---|
| `EACCES` writing to `/sys/class/gpio` | You are not root over SSH. The app itself already runs as root under appmgr's supervisor; the SSH session editing appdata also needs to be root. |
| The gate refuses to arm, naming a pin | The pin is already exported with a direction or value that disagrees with the configured idle state. Find out what owns it. Do not force a takeover to make the message go away. |
| `state` in `/run/f1-access/health.json` stays `disarmed` | No access config at `/userdata/local/appdata/f1-access/face-recognition.conf`, or it failed the consistency gate. Check `app.log` for the named reason. |
| The door pulses once at boot | The active level is inverted. Fix it before reconnecting the door controller. |
| Two pulses per approach | The debounce is not in the path, or its window is shorter than the time somebody spends in frame. |
| The start-up banner keeps naming `relay_contact=unverified fail_mode=unverified` | The wiring posture has not been declared. Measure, then set both. Do not connect the door controller before that. |
| `health()["stuck_active"]` is true | The gate failed to drive the pin back to the un-actuated level, so the door may still be open. That is a site visit, not a log entry. |
| `gpio = 131` is rejected while parsing the config | It is in `KNOWN_BUSY_GPIO` — already exported by another application on hardware. |
| `pulse_ms must be 500..5000 ms` | The pulse width is outside the legal range. |

## Step 6: Check the Library Reached the Device {#p1_facedb_status type=web_dashboard required=true verify=true config=devices/network_face_database.yaml}

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
| `signature.verified` is `null` | Steady state. Verification is reported only in the window right after a sync; a real failure appears in `last_error`. |
| `configured` is `false`, `online` and `heartbeat` are `null` | Expected on this preset: P1 sets no `USA_DEVICE_ENDPOINTS` because its reload goes over the device's own loopback, and the daemon publishes sync status rather than heartbeats. Use `last_seen`. |
| `clock.valid` is `false` | Expected on a device with no NTP. The integrity boundary is the manifest signature, not the clock. |
| A person appears under `only_on_device` | Somebody enrolled locally, bypassing the cloud. The next activation overwrites it. Find out who did it and why. |
| The page is empty | `USA_DEVICE_ENDPOINTS` is `[]`, or no device has ever reported. Check the console's environment file first. |

## Step 7: Verify the Door End to End {#p1_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

An enrolled person opens the door once; a photograph does not open it at all; a
remote unlock produces a receipt; a delete cannot be rolled back.

### Prerequisites

- Steps 1–5 finished, the door controller connected, and someone enrolled in the current
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
- Record what you measured — pin, level, current, pulse width, contact, and
  door controller type — with the installation. The next person to touch it
  has no way to recover those from the software.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photograph opens the door | Liveness is not in the path. Check `/health` reports liveness loaded; the adapter is supposed to refuse to start otherwise. Take the door out of service until this is resolved. |
| Remote unlock returns a receipt but the contact never closes | The decision reached the actuator and the actuator did not act. Check the pin's health output and the wiring, not the broker. |
| A replayed command opens the door twice | The replay table is not in the path. Nothing else about the command gate can be trusted either; stop and investigate. |
| Audit verification fails | Either the log was edited or it was written by two processes. Both matter. Keep the file. |
| Events stop but the door still opens | The broker connection dropped. That is the intended behaviour — the unlock path in this preset does not go through the network — but the retained last-will should show the device as offline in the console. |

## Preset: B. Standard reCamera {#a_recamera_std}

**What you need**

| Device | Purpose |
|---|---|
| Linux server (Docker, no GPU needed) | Face library, management console, MQTT broker |
| Standard reCamera (2002 / 2002w / 2002 HQ PoE) | Recognises faces and decides whether to unlock |
| R1000 or XIAO ESP32-S3 (2002 / 2002w only) | Receives unlocks over MQTT and drives the relay; the door does not open while the broker is down |
| Relay module | Dry contact into the door controller's unlock input; on the 2002 HQ PoE the relay connects to baseboard header D1 |

## Step 1: Deploy the Face Library Server {#p5_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Same cloud host, same step as the other presets. Brings up the library server,
the broker and the console container, and writes the signing key.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from the door.
- **Its clock must be right** — door devices take their time correction from it.
- **The container image is published**; the compose file's default already
  points at it.
- A signing key: `openssl rand -hex 32`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Image pull fails | Expected until the image is pushed. Build and retag on the host. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Library endpoint answers 404 | Correct before the first enrolment. |
| `NTP is not synchronised` warning | Fix it before deploying any door. |
| Port 8080 already in use | Change the library port; devices are given the same value. |

### Target {#p5_facedb_remote type=remote config=devices/cloud_facedb.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p5_facedb_local type=local config=devices/cloud_facedb.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 2: Deploy the Management Console {#p5_cloud_web type=docker_deploy required=true config=devices/cloud_web.yaml target_inherit_from=p5_cloud_facedb}

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

### Target {#p5_web_remote type=remote config=devices/cloud_web.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p5_web_local type=local config=devices/cloud_web.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 3: Enrol People {#p5_register type=web_dashboard required=true config=devices/register_person.yaml}

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

## Step 4: Install F1 Access on the Camera {#p5_install type=recamera_cpp required=true config=devices/p5_recamera_std.yaml}

Installs the `.deb`, places the five cvimodels at `/userdata/local/models/`,
writes the face library signing key and the per-site config fields into the
seeded config file.

### Prerequisites

- The camera reachable over USB or the network, and the SSH password for the
  `recamera` user.
- The face library server reachable from the camera over plain HTTP, and its
  signing key and key ID from the cloud step.
- About 20 MB free on `/userdata`.

### Wiring

1. Connect the reCamera over USB-C, or make sure it is reachable on your network
2. Enter its IP address (USB gives it `192.168.42.1`) and the SSH password for
   the `recamera` user
3. Pick the camera variant, and fill in the device ID, actuator ID, face
   library URL, key ID, signing secret and match threshold
4. Deploy

A **2002 HQ PoE** unit drives a relay directly from the baseboard's 6-pin
header (`D1` = sysfs GPIO 490) — a second door option alongside the
gateway-relay path below. A plain **2002 / 2002w** has no such header; picking
it in step 3 sets `[gpio] enabled = false` in the config before the service's
first start, so the camera drives no relay itself and events leave over MQTT
for the gateway to act on, as in the rest of this preset. This has to be set
before the first start, not edited afterward — the deploy auto-starts the
service right after configuration, and a first start with the PoE default
tries to export a pin that is not wired to anything on a plain unit.

The gateway relay node's `set` topic must never be retained: a retained unlock
replays on every reconnect, and the door would open by itself after a power cut.

### What lands on the device

The whole recognition path — detection, embedding, a two-head texture
liveness with blink fusion, and matching — runs on the camera's own SG2002
TPU in one native process; the access agent sits beside it in the same
package and pulls the versioned face library, maps the native result stream
onto the event contract, and pins every threshold against the recognition
process's actual arguments. The package replaces the stock `face-recognition`
app rather than extending it — installing it conflicts with and removes that
app, because only one gallery app can hold the camera's VPSS at a time.

| Path | What |
|------|------|
| `/usr/share/f1-access/bin/face-recognition` | The recogniser |
| `/usr/share/f1-access/*.py` | The access agent and the payload validator |
| `/etc/init.d/K92f1-access` | Its init script, parked |
| `/userdata/local/models/*.cvimodel` | The five models, ~10.7 MB total |
| `/userdata/f1-access/face-recognition.conf` | Seeded once from the package default, then edited in place with the fields above |
| `/userdata/f1-access/facedb.key` | The face library signing secret, `0600` |

The init script is installed parked (`K92`, not `S92`) on purpose. Only one
application may hold the camera at a time, so starting it is the console's
job. An upgrade never overwrites an existing `face-recognition.conf` — a
reset calibrated threshold or GPIO polarity would silently change who gets in
and whether the contact idles open or closed.

Measured on hardware (`docs/SPEC.md` §14.3, `evaluation/runs/2026-09-07-recamera-poe-p1/results.md`):
cold start (power-cycled, run directly with no timeout) 7.5–9.4 s across six
runs, median 8.8 s; the same six runs through the console's own 15 s start
budget all reported `OK` at 8.4–9.4 s; `stop` 7.8–8.8 s with the camera fully
released both times. A threshold mismatch between this config and the
recognition process's actual arguments is rejected before start, in 8.4 s —
the door's pin stays at the idle level the whole time, so a rejected start
never opens the door.

### Troubleshooting

| Issue | Solution |
|---|---|
| Package install fails, camera still shows the stock face-recognition app | `opkg install --force-reinstall` should conflict/replace it; if it does not, remove `face-recognition` by hand first. |
| Service won't start, `agent.log` ends in `refusing to start, thresholds are not single-sourced` | The config and the recognition process's actual startup arguments disagree — check `device_id`/`actuator_id` and every value under `[recognition]` against what shipped, and do not hand-edit only one side. |
| The agent starts but no library version ever activates | Check `key_id` and the signing secret against the console, and `match_threshold` against `USA_MATCH_THRESHOLD`. |
| `mqtt.host` mismatch on a plain 2002/2002w | The gate compares the config's `[mqtt] host` against the recognition process's literal `-m` argument; the factory default is `localhost`, not `127.0.0.1`. |
| Version directories accumulate on the device | `[facedb] keep_versions` (default 3) bounds them after a successful activation. Rollback does not depend on them — the server republishes old content under a new version number. |

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
| `signature.verified` is `null` | No version has completed a signature check yet. That is not a failed check. |
| `clock.valid` is `false` | Expected on a device with no NTP. The integrity boundary is the manifest signature, not the clock. |
| A person appears under `only_on_device` | Somebody enrolled locally, bypassing the cloud. The next activation overwrites it. Find out who did it and why. |
| The page is empty | `USA_DEVICE_ENDPOINTS` is `[]`, or no device has ever reported. Check the console's environment file first. |

## Step 6: Verify the Door End to End {#p5_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

An enrolled person opens the door once; a photograph does not; a remote unlock
produces a receipt; a delete cannot be rolled back.

### Prerequisites

- Steps 1–4 finished, the door controller connected, someone enrolled in the current
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
- Record the DO number, level, pulse width, contact and door controller type
  with the installation.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photograph opens the door | Liveness is not in the path. Take the door out of service until resolved. |
| Receipt says executed, contact never closes | The actuator did not act. Check the relay wiring and the actuator health output. |
| A replayed command opens the door twice | The replay table is not in the path. Stop and investigate. |
| Audit verification fails | The log was edited, or two processes wrote it. Keep the file. |
| Container restarts in a loop | `docker logs usa-access-node`. A refusal to start on a bad actuator or library configuration looks the same as a crash and is not one. |

## Preset: C. AI Host with Your Existing Cameras {#b_ai_host}

**What you need**

| Device | Purpose |
|---|---|
| Linux server (Docker, no GPU needed) | Face library, management console, MQTT broker |
| reComputer J20 / J30 / J40 / R1000 | Pulls the door camera's RTSP stream, recognises faces and decides whether to unlock |
| Existing RTSP camera at the door | Video source |
| R1000 or XIAO ESP32-S3 (host away from the door only) | Receives unlocks over MQTT and drives the relay; the door does not open while the broker is down |
| Relay module | Dry contact into the door controller's unlock input |

## Step 1: Deploy the Face Library Server {#p2_cloud_facedb type=docker_deploy required=true config=devices/cloud_facedb.yaml}

Same cloud host, same step as the other presets. Brings up the library server,
the broker and the console container, and writes the signing key.

### Prerequisites

- A Linux host with Docker and the compose plugin, reachable from the door.
- **Its clock must be right** — door devices take their time correction from it.
- **The container image is published**; the compose file's default already
  points at it.
- A signing key: `openssl rand -hex 32`.

### Troubleshooting

| Issue | Solution |
|---|---|
| Image pull fails | Expected until the image is pushed. Build and retag on the host. |
| `docker compose` not found | Install `docker-compose-plugin`. |
| Library endpoint answers 404 | Correct before the first enrolment. |
| `NTP is not synchronised` warning | Fix it before deploying any door. |
| Port 8080 already in use | Change the library port; devices are given the same value. |

### Target {#p2_facedb_remote type=remote config=devices/cloud_facedb.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p2_facedb_local type=local config=devices/cloud_facedb.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

## Step 2: Deploy the Management Console {#p2_cloud_web type=docker_deploy required=true config=devices/cloud_web.yaml target_inherit_from=p2_cloud_facedb}

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

### Target {#p2_web_remote type=remote config=devices/cloud_web.yaml default=true}

Deploy to a Linux server the door devices can reach.

### Target {#p2_web_local type=local config=devices/cloud_web.yaml}

Deploy to this computer. The door devices must be able to reach its IP.

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

## Step 4: Deploy the Access Node {#p2_deploy type=docker_deploy required=true config=devices/p2_j20.yaml}

Starts recognition and the access node on the host. Pick the target that matches your host and relay wiring.

### Prerequisites

- Docker and the compose plugin on the host.
- The RTSP URL tested from the host, not from your laptop.
- Outbound access to `sensecraft-statics.seeed.cc`: the step downloads the face
  model weights (about 32 MB) to `/opt/usa/models` and checks each SHA-256. The
  recognition container builds its TensorRT engines on first start; on a
  reComputer J40 `/health` answered 214 s after the container started. Later
  starts reuse the cached engines.
- At least 15 GB free.
- Actuator settings measured on the installed hardware: pin, active level, pulse
  width, relay contact (`NO` / `NC`) and the door state after power loss
  (`fail_safe` / `fail_secure`).

### Troubleshooting

| Issue | Solution |
|---|---|
| `access-node` container restarts, `docker logs` says `config error:` | The config gate refused a value. Run `docker compose exec access-node access-node check-config` to see which one; the four wiring fields and the placeholder strings are the usual causes. |
| `access-node` stays `unhealthy` but the logs show no error | `/readyz` is the healthcheck, and it is red whenever a face cannot open the door. `docker compose exec access-node access-node healthcheck` prints which of the four gates is down: face-rec-api, camera, face database, or the pin lock. |
| "LIVENESS IS NOT LOADED" | The recognition service came up without its liveness model. The access node will refuse to start, correctly. Fix the image, do not bypass the check. |
| RTSP stream opens on your laptop but not on the J20 | Routing or credentials. Test from the box itself. |
| The step refuses a plaintext library URL | No signing key was given. On a plaintext URL the manifest signature is the whole integrity boundary. |
| The door pulses at boot | The active level is inverted. Fix it before reconnecting the door controller. |

### Target {#p2_j20 type=remote device=recomputer_j20 device_name="reComputer J20" config=devices/p2_j20.yaml default=true}

The relay connects to the J20's opto-isolated DO. Set **GPIO Interface = sysfs**
and enter the sysfs number. The design spec records DO1–DO4 as sysfs
463/464/465/462; measure which number moves which terminal on this box before
wiring a lock. The deploy prints whether the chosen pin is already in use.

### Wiring

1. **LED with a series resistor on the pin first.** Confirm polarity and pulse width.
2. **Relay module.** Confirm the contact clicks once per pulse.
3. **The relay's COM/NO dry contact into the door controller's unlock input.**

### Troubleshooting

| Issue | Solution |
|---|---|
| "gpio N is ALREADY EXPORTED" | Something else is driving that output. Confirm it is the door DO before continuing. |

### Target {#p2_jetson type=remote device=recomputer_j40 device_name="reComputer J30 / J40" config=devices/p2_j20.yaml}

The relay connects to the 40-pin header.

**J30 / J40 (JetPack 6, Tegra 5.15, libgpiod).** These kernels do not export
`/sys/class/gpio` at all — `ls /sys/class/gpio` returns *No such file or
directory*, so there is no sysfs number to fill in. The door goes through
`/dev/gpiochipN` instead: set **GPIO Interface = libgpiod**, **GPIO Chip =
gpiochip0**, and a **line offset**. On a reComputer J40 Series the whole 40-pin
header is on `gpiochip0`; `gpiochip1` is the AON controller and `gpiochip2` is
carrier-board I/O, and neither reaches the header.

Header pin to line offset on the J401 carrier, cross-checked against NVIDIA's
own pin table on the box
(`/usr/lib/python3/dist-packages/Jetson/GPIO/gpio_pin_data.py`) and the
[Seeed J401 40-pin table](https://wiki.seeedstudio.com/J401_carrierboard_Hardware_Interfaces_Usage/):

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

Pins 1/17 are 3V3, 2/4 are 5V, and 6/9/14/20/25/30/34/39 are GND — the relay
module needs one of each on top of the signal line.

Run `gpioinfo` on the box before choosing: it prints every line with its name
and its current consumer, and a line marked `[used]` belongs to something else.
On the box checked here all seventeen header lines above were free.

### Wiring

1. **LED with a series resistor on the pin first.** Confirm polarity and pulse width.
2. **Relay module.** Confirm the contact clicks once per pulse.
3. **The relay's COM/NO dry contact into the door controller's unlock input.**

### Target {#p3_mqtt_relay type=remote device=mqtt_relay device_name="MQTT Relay" config=devices/p3_mqtt_relay.yaml}

Choose this when the host is not at the door or serves several doors. Unlocks
travel over MQTT to a relay node (R1000 or XIAO ESP32-S3); the door does not open
while the broker is down.

### Prerequisites

- The broker reachable from the host; the deploy checks this first.
- The relay node already connected to the broker, with an id unique across the site.

### Wiring

The wiring is at the relay node; the host has no door connection.

1. **LED with a series resistor on the relay node's output first.** Confirm polarity and pulse width.
2. **Relay module.** Confirm the contact closes once per `set` message.
3. **The relay's COM/NO dry contact into the door controller's unlock input.**

### Troubleshooting

| Issue | Solution |
|---|---|
| "Cannot reach the MQTT broker" | The step stops here on purpose. In this preset the broker is on the unlock path. |
| "No retained state from relay" | The relay node has never connected to this broker. Check its network and its id. |
| Unlock accepted, contact never closes | Subscribe to `access/v1/relay/<id>/state` and read `result`. `duplicate`, `expired` and `rejected` each mean something different. |
| The door opens by itself after a power cut | The `set` topic was published retained. It must never be. |
| Pulse width rejected | The command range is 500–5000 ms. The relay firmware's own wire format allows 100–10000 ms; they are different constraints and the narrower one governs. |

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
| `signature.verified` is `null` | No version has completed a signature check yet. That is not a failed check. |
| `clock.valid` is `false` | Expected on a device with no NTP. The integrity boundary is the manifest signature, not the clock. |
| A person appears under `only_on_device` | Somebody enrolled locally, bypassing the cloud. The next activation overwrites it. Find out who did it and why. |
| The page is empty | `USA_DEVICE_ENDPOINTS` is `[]`, or no device has ever reported. Check the console's environment file first. |

## Step 6: Verify the Door End to End {#p2_verify type=manual required=true verify=true config=devices/remote_unlock.yaml}

An enrolled person opens the door once; a photograph does not; a remote unlock
produces a receipt; a delete cannot be rolled back.

### Prerequisites

- Steps 1–4 finished, the door controller connected, someone enrolled in the current
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
- Record the DO number, level, pulse width, contact and door controller type
  with the installation.

### Troubleshooting

| Issue | Solution |
|---|---|
| A photograph opens the door | Liveness is not in the path. Take the door out of service until resolved. |
| Receipt says executed, contact never closes | The actuator did not act. Check the DO wiring and the actuator health output. |
| A replayed command opens the door twice | The replay table is not in the path. Stop and investigate. |
| Audit verification fails | The log was edited, or two processes wrote it. Keep the file. |
| Container restarts in a loop | `docker logs usa-access-node`. A refusal to start on a bad actuator or library configuration looks the same as a crash and is not one. |
