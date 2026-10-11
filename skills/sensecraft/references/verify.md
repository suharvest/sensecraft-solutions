# Finish a `verify_required` step

The engine does not run verification steps that need a person or a browser.
When a deployment reaches one, it writes a `verify_required` event to the
deployment's log, marks that step `step_skipped` (`reason: verify_required`)
and carries on. Read the events with
`sensecraft-engine logs <deployment_id> --since <N>`.

Fields every `verify_required` event has:

| Field | Content |
|---|---|
| `device_id` / `step_id` | The step |
| `kind` | The step type (`web_dashboard`, `serial_camera`, `serial_wizard`, `robot_inspect`, `preview`, `image_predict`, ...) |
| `name`, `required` | Display name; whether the solution counts it as required |
| `url`, `endpoint`, `sample_request` | Where to check, with `{{host}}` already filled in (may be null) |
| `instructions` | What to check, in the solution's words |
| `expected_status` | `web_dashboard` only: 200 |

Steps for hardware sessions add `port` / `db_port` / `host` (filled from the
step that flashed or deployed the device; null when the connection did not
include it), `commands {...}` with the exact CLI commands, and `confirm`
(how to tell it worked). `deploy-info` lists the same commands in advance as
`counting_cli`, `face_cli`, `wizard_cli` or `robot_cli` on that step.

General rules:

- Replace `<PORT>`, `<DB_PORT>`, `<HOST>` in `commands` with the event's `port`,
  `db_port`, `host`. If one is null, take it from the connection you gave the
  step named in `port_from_device` / `db_port_from_device` /
  `host_from_device`, or ask the user (`sensecraft-engine device ports` lists
  serial ports).
- Anything a person must do with their hands — plugging a cable, connecting a
  servo, sitting in front of a camera, walking past it, standing clear of a
  robot arm — is the user's job. Say exactly what to do, then **wait for the
  user to confirm** before running the next command.
- These commands print a JSON result on stdout. Exit codes: 0 confirmed by the
  device; 1 the device did not confirm (timeout, error, read-back mismatch);
  2 bad arguments; 3 port busy or cannot be opened, or (robot) the status
  service is unreachable; 5 internal error. On 3 with `port_busy`, another
  deployment or session holds the port: wait for it, do not force it.
- At most 3 rounds per problem, as in `SKILL.md`.

## 1. Dashboards and interactive checks (`web_dashboard`, `preview`, `image_predict`, `text_chat`, `voice_chat`, ...)

- `web_dashboard`: `curl -s -o /dev/null -w "%{http_code}" <url>` must return
  `expected_status` (200). Then give the user the `url` to open.
- `endpoint` + `sample_request` present: send the sample request to the
  endpoint (`curl` with the sample body) and show the user the response.
- Otherwise follow `instructions`. When they say to run the check in the
  SenseCraft Solution app, tell the user: that check needs the desktop app.

## 2. People counting lines (`serial_camera` with `counting_cli`)

1. Ask the user where the counting lines / zones should be, in camera
   coordinates 0–1000 (0,0 top left, 1000,1000 bottom right): a line is two
   points `X1,Y1,X2,Y2`, a zone four corners. Direction: crossing from the
   right side of the line (looking from point 1 to point 2) to the left counts
   as `in`; swap the two points to reverse it.
2. Write them:
   `sensecraft-engine counting set --port <PORT> --line 0=100,500,900,500 [--roi 1=X1,Y1,...,X4,Y4] [--anchor-mode foot]`
   (`foot` for a camera tilted down from above, `center` otherwise). The result
   must have `verified: true`; `mismatches[]` lists slots that read back
   differently.
3. Start counting from zero and keep the camera running:
   `sensecraft-engine counting reset --port <PORT> --keep-running`.
4. Ask the user to walk across each line (and into each zone) and tell you when
   done.
5. `sensecraft-engine counting get --port <PORT>`: each line's `in` / `out` and
   each zone's `cur` / `entered` must have changed as expected. Show the user.

## 3. Face enrollment (`serial_camera` with `face_cli`, SenseCAP Watcher)

The Watcher has two USB serial ports: the camera (`--port`) and the face
database (`--db-port`).

1. Ask the user whose face to enroll (name: ASCII up to 31 characters, Chinese
   up to 4 characters).
2. Ask that person to sit in front of the camera, facing it, and to tell you
   when ready.
3. `sensecraft-engine face enroll --port <PORT> --db-port <DB_PORT> --name <NAME> --no-prompt`.
   Success: `stored: true`, `verified: true`. Too few samples
   (`samples_collected` below the minimum): ask for better light / a closer,
   straight-on face, then run it again.
4. `sensecraft-engine face list --db-port <DB_PORT>` and show the names to the
   user. Fix mistakes with `face rename --db-port <DB_PORT> --name OLD --new-name NEW`
   or `face delete --db-port <DB_PORT> --name NAME` (deleting needs the user's OK).
5. Ask an enrolled person to stand in front of the camera and confirm the
   device recognizes them by name.

## 4. Servo ID setup (`serial_wizard` with `wizard_cli`)

The firmware sets one servo ID at a time and prints prompts.

1. Tell the user to connect **only** the servo for the current ID (the
   event's `instructions` name them, e.g. ID 1 front wheel, 2 left rear, 3 right
   rear) and to confirm.
2. `sensecraft-engine wizard action --port <PORT> --name enter`. Pass the
   firmware's `prompt` text on to the user.
3. `step_error` set: ask the user to check the wiring, then
   `sensecraft-engine wizard action --port <PORT> --name retry`.
4. Repeat for each servo until the result has `step_done: true`
   (`wizard read --port <PORT> --until done` waits for it). Then ask the user
   to power off, connect all servos and power on again.

## 5. Robot arm check (`robot_inspect` with `robot_cli`)

Commands that move the arm need the user's OK each time.

1. `sensecraft-engine robot observe --host <HOST>`: every joint has a value.
2. Ask the user's OK, then `robot torque off --host <HOST>`; ask the user to
   turn one joint by hand; `robot observe` again — the reading must follow.
   Show the user the numbers.
3. Recording a motion: for each pose the user sets by hand, run `robot observe`
   and add the `observation` to a frame file
   (`[{"joints": {...}, "delay": 0.4}, ...]`).
4. Before `robot actions test --host <HOST> --frames <file>`, ask the user to
   stand clear of the arm and confirm. Afterwards ask whether the motion was
   right.
5. Only after the user approves it:
   `robot actions save --host <HOST> --name <name> --frames <file>`.
   `robot actions cancel --host <HOST>` stops a running motion.

## 6. Report

For each verify step tell the user: what you checked, the command result
(the relevant fields, not the whole JSON), and anything left for them to do.
