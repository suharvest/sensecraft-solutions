# Deploy a solution

Run Step 0 in `SKILL.md` first (engine installed, solutions pulled). Examples
use `--lang en`; use `--lang zh` for a Chinese-speaking user.

## 1. Find the solution

```
sensecraft-engine solution list --json
```

Match the user's wording against `name` / `summary`. Confirm the `id` with the
user if more than one fits. `sensecraft-engine solution show <id> --lang en`
prints the full solution if you need more detail.

## 2. Read what the deployment needs

```
sensecraft-engine deploy-info <id> --lang en
```

- `presets[]` — deployment variants. If there is more than one, ask the user which
  one, then run again with `--preset <preset>`. Without `--preset` the template
  lists the steps of every preset.
- `steps[]` — each step's `device_id`, `type`, `required`, `connection_type`
  (`ssh` / `serial` / `none` / ...), `parameters`, `category` (`deploy` or
  `verify`) and `interactive`. Steps with `has_targets: true` (e.g.
  `docker_deploy`) list `targets`: `local` = this computer's Docker, `remote` =
  a device over SSH.
- Verify steps that need the user carry a ready command list:
  `counting_cli`, `face_cli`, `wizard_cli` or `robot_cli` (see `verify.md`).
- `request_template` — a ready request body. Values shaped like
  `<REQUIRED: ...>` must be filled in; everything else has a working default.

Never make up step or device IDs: the keys of `device_connections` and the
entries of `selected_devices` are exactly the ones in `request_template`.

Optional discovery, to pre-fill values:

```
sensecraft-engine device ports            # serial ports (USB devices)
sensecraft-engine device scan --timeout 5 # SSH devices on the LAN (mDNS, IPv4)
sensecraft-engine device list             # device catalog
sensecraft-engine doctor --json           # this computer: serial permission, Docker, disk, network
```

## 3. Fill in and confirm

Ask the user for every `<REQUIRED: ...>` value (device IP, username, password,
serial port, and any user inputs). Serial steps carry both `port` and
`serial_port` placeholders; fill both with the port name from `device ports`.

For `docker_deploy` steps pick the target with `"target": "<target id>"` **and
set `"target_type"` to that target's own type** (`local` / `remote`) — or
remove `target_type`. Leaving the template's type while switching `target` is
rejected. Each deploy-info target carries a `type` field: use it. On engine
builds whose targets have no `type` yet, the target id suffix (for example
`_local`, `_remote`) is only a hint; confirm the type with `validate` (§3,
dry run) before starting. Remote targets need `host`, `username`
and either `password` or `key_file`:

- Password: `"password": "<the user's password>"`.
- SSH key: `"key_file": "~/.ssh/id_ed25519"` and no `password` field. The key
  must be a regular file inside `~/.ssh` (or the engine's data directory); a
  relative path is resolved under `~/.ssh`; other locations are refused.

Add `"auto_replace_containers": true` (or the `--replace-existing` flag) only if
the user agrees to replace existing containers with the same name.

Write the filled body to `./.sensecraft-work/body.json` in the current working
directory, not `/tmp` (a file keeps the password out of the process list and
avoids shell quoting problems, notably in PowerShell):

```json
{
  "solution_id": "<id>",
  "preset_id": "<preset>",
  "selected_devices": ["<step_id>"],
  "device_connections": {
    "<step_id>": {"target": "<target_id>", "target_type": "remote",
                  "host": "192.168.1.50", "username": "<user>",
                  "password": "<password>"}
  }
}
```

Show the user the body with the password as `<REDACTED>` before starting.

Before a remote deploy, run the dry run (no changes on any device):

```
sensecraft-engine validate --params ./.sensecraft-work/body.json
```

It reports parameter errors and previews which verify steps will need the user
(`verify_required`). It also lists, per device, the side effects the deployment
will cause on the target (`side_effects`: for example Docker installation,
Docker daemon restart, writes to `/etc/docker/daemon.json`, replacing
containers). Read that list and tell the user what it contains. If the user
forbade Docker restarts or daemon.json changes, or `side_effects` lists one of
them and the user has not agreed, stop and ask before starting. Builds without
a `side_effects` field: assume a remote Docker deploy may write
`/etc/docker/daemon.json` and ask when the user restricted that.

Before the deploy, save the target's current Docker daemon config so changes
can be shown and restored:

```
ssh <user>@<ip> cat /etc/docker/daemon.json > ./.sensecraft-work/daemon.json.before
```

(a missing file is fine: note that it did not exist). After the deploy, `cat`
it again and show the user any difference; restoring it is a change on the
device and needs the user's OK.

## 4. Start and follow

```
sensecraft-engine deploy --params ./.sensecraft-work/body.json --yes --detach --lang en
```

`--detach` prints `{"deployment_id": "...", "log": "..."}` and returns. Keep the
`deployment_id`. Exit code 2 here means a parameter is missing: the
`missing[]` list names it (`preset_id`, `device_connections.<id>.<key>`).
Exit code 3 with a 409 means the device is busy with another deployment.

Follow progress in one of two ways:

- **Poll** (works with any agent's command timeout): every 3–5 seconds run
  `sensecraft-engine status <deployment_id> --json`. `status` is `running`
  while in progress and ends as `completed`, `failed`, `cancelled` or
  `interrupted`; each device and step has its own `status` and `message`.
  Exit code: 0 while running or completed, 1 for failed / cancelled /
  interrupted.
- **Event stream:** `sensecraft-engine logs <deployment_id> --since <N>`
  prints NDJSON events (`{seq, type, ...}`) with `seq > N` and exits; add
  `--follow` to keep streaming until the deployment ends (run it in the
  background if your command timeout is short). Remember the last `seq` and
  pass it as `--since` next time, so you never read the same events twice.

Event types to act on:

| `type` | Meaning |
|---|---|
| `log` | `level`, `message`; `error`-level lines are evidence for `diagnose.md` |
| `step_skipped` with `reason: verify_required` | The step needs the user — the `verify_required` event before it has the details |
| `verify_required` | Go to `verify.md` with this event |
| `device_completed` | One device finished |
| `deployment_completed` | Last event; `status` is the final result |

Read the JSON directly instead of grepping it (no interpreter, see `SKILL.md`
rule 5). Delete `./.sensecraft-work/` afterwards (`body.json` holds a
password).

Without `--detach`, `deploy --json` streams the same events on stdout and ends
with one `{"type": "result", "deployment_id", "status", "devices"}` line; the
exit code is the deployment's result. Ctrl-C or a killed agent command only
detaches: the deployment keeps running in the engine instance; continue with
`status` / `logs`.

If `--detach` prints `"backend": "python"`, the desktop app's backend is
running this deployment: `logs` then has `log` and `deployment_completed`
events only, no `verify_required`. Do the guide's verify steps with the user
as described in `verify.md` §1.

## 5. Verify

`completed` is not enough. Check the result is actually usable:

- `verify_required` events: handle each one with `verify.md`.
- Docker steps: on the target the solution's containers are `Up` and, if they
  define a health check, `(healthy)`:
  `sensecraft-engine docker ps --json` (this computer) or
  `SC_SSH_PASSWORD=<password> sensecraft-engine docker ps --host <ip> --username <user> --json`
  (remote; `--password-stdin` reads the password from stdin instead). With an
  SSH key, on engines that have `--key-file`:
  `sensecraft-engine docker ps --host <ip> --username <user> --key-file ~/.ssh/id_ed25519 --json`
  (same path rules as `key_file` in §3). Engines without `--key-file` accept
  a password only; with a key-only device use `ssh <user>@<ip> docker ps`.
- Services with a port: `curl -s -o /dev/null -w "%{http_code}" http://<host>:<port>/`
  returns 2xx/3xx.
- Stay running: `completed` can precede a crash loop. Run `docker ps` once,
  wait about 60 seconds, then run it again and read the container restart
  count (`docker inspect -f '{{.Name}} {{.RestartCount}} {{.State.Status}}' <container>`
  over SSH, or the `Restarting` / `Up Less than a second` status in `docker ps`).
  The counts must stay 0 and the verify endpoint (the step's `url`, or the
  port check above) must still answer after the wait. If a container restarts
  or the endpoint stops answering, report a crash loop, not success, and go to
  `diagnose.md`.
- Tell the user the URL to open and anything the guide says to do next.

## 6. If anything failed

Go straight to `diagnose.md` with the `deployment_id`. Do not stop to ask.

To retry after a fix, send the same body again — same `preset_id` and
`device_connections` — with `selected_devices` listing only the device(s) that
failed (or `--device <step_id>` for one device); the others are already done.
Leaving manual steps in is harmless (they are skipped).

Two kinds of failure, two policies:

- **Transient registry or network errors** (image pull answered 401 / 429 /
  500 / 502 / 503 / 504, `TLS handshake timeout`, `i/o timeout`,
  `connection reset`, a mirror that flaps): retry the same body without
  asking, up to 5 times, waiting 15, 30, 60, 120, 240 seconds between tries.
  These retries do not count as fix rounds. If the engine log shows the
  mirror changing between tries, that is the same transient case. After the
  5th failure, stop and report the error text, the waits and the registry host.
- **Deterministic failures** (bad parameter or credentials, port taken, disk
  full, missing file, a container that exits on start, the same error with the
  same text after a fix): stop retrying blindly. First retry after a fix
  without asking; later retries need the user's OK; at most 3 rounds, then
  report.

If you cannot tell which kind it is, treat the second occurrence of the same
error after a wait as deterministic.

## Cancel

Only with the user's OK: `sensecraft-engine cancel <deployment_id>`. Then check
`status` until it is `cancelled`, and tell the user which steps had already run:
the device may be half-configured.
